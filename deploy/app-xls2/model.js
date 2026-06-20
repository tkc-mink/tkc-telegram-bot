/* ============================================================
   model.js — XL2 core: cell grid, formula engine, cipher, storage
   ============================================================ */
(function () {
  // ---- Cipher (กฎ A: แทนเลขซ้ำได้ครั้งเดียว ไม่มี AA) ----
  var C1 = ['X','T','N','S','F','V','L','C','B','K'];   // ทุน/COGS
  var C2 = ['O','I','Z','M','D','E','H','Y','P','R'];   // ขายส่ง
  function encode(numStr, map) {
    var s = String(numStr == null ? '' : numStr).replace(/[^0-9]/g, '');
    if (!s) return '';
    var out = '', prev = null, lastA = false;
    for (var i = 0; i < s.length; i++) {
      var ch = s[i];
      if (ch === prev && !lastA) { out += 'A'; lastA = true; }
      else { out += map[+ch]; lastA = false; }
      prev = ch;
    }
    return out;
  }

  // ---- A1 refs ----
  function colName(c) { var s = ''; c++; while (c > 0) { var m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = (c - 1 - m) / 26; } return s; }
  function colIdx(name) { var n = 0; for (var i = 0; i < name.length; i++) n = n * 26 + (name.charCodeAt(i) - 64); return n - 1; }
  function refStr(r, c) { return colName(c) + (r + 1); }

  function num(v) { var n = parseFloat(String(v).replace(/,/g, '')); return isNaN(n) ? 0 : n; }
  function isNumeric(v) { return v !== '' && v != null && /^-?[\d,]*\.?\d+$/.test(String(v).trim()); }

  // ---- Sheet ----
  function newSheet(nR, nC) {
    return {
      nR: nR, nC: nC,
      cells: {},                 // "r,c" -> {v,f,t,s}
      merges: [],                // {r,c,rs,cs,auto?}
      colW: [], rowH: [],
      rowKind: [], rowGid: [],
      adminRows: {}, adminCols: {}, secretCols: {},
      meta: {}
    };
  }
  function cellAt(sh, r, c) { return sh.cells[r + ',' + c] || null; }
  function ensure(sh, r, c) { var k = r + ',' + c; if (!sh.cells[k]) sh.cells[k] = { v: '', f: null, t: 'auto', s: {} }; return sh.cells[k]; }

  // ---- Formula engine ----
  // grammar: expr=term((+|-|&)term)* ; term=factor((*|/)factor)* ; factor=num|"str"|ref|FN(args)|(expr)|-factor
  function tokenize(src) {
    var toks = [], i = 0;
    while (i < src.length) {
      var ch = src[i];
      if (ch === ' ') { i++; continue; }
      if ('+-*/()&,:'.indexOf(ch) >= 0) { toks.push({ t: ch }); i++; continue; }
      if (ch === '"') { var j = src.indexOf('"', i + 1); if (j < 0) j = src.length; toks.push({ t: 'str', v: src.slice(i + 1, j) }); i = j + 1; continue; }
      var m = /^\$?[A-Za-z]+\$?\d+/.exec(src.slice(i));
      if (m && !/^[A-Za-z]+\(/.test(src.slice(i))) { toks.push({ t: 'ref', v: m[0].replace(/\$/g, '').toUpperCase() }); i += m[0].length; continue; }
      m = /^[A-Za-z\u0E00-\u0E7F_][A-Za-z0-9\u0E00-\u0E7F_]*/.exec(src.slice(i));
      if (m) { toks.push({ t: 'name', v: m[0].toUpperCase() }); i += m[0].length; continue; }
      m = /^\d*\.?\d+/.exec(src.slice(i));
      if (m) { toks.push({ t: 'num', v: parseFloat(m[0]) }); i += m[0].length; continue; }
      i++; // skip unknown
    }
    return toks;
  }

  function evalFormula(sh, src, visiting) {
    var toks = tokenize(src), p = 0;
    function peek() { return toks[p] || { t: 'end' }; }
    function eat() { return toks[p++] || { t: 'end' }; }
    function refVal(refS) {
      var m = /^([A-Z]+)(\d+)$/.exec(refS); if (!m) return '#ERR';
      var r = +m[2] - 1, c = colIdx(m[1]);
      return evalCell(sh, r, c, visiting);
    }
    function rangeVals(a, b) {
      var m1 = /^([A-Z]+)(\d+)$/.exec(a), m2 = /^([A-Z]+)(\d+)$/.exec(b);
      if (!m1 || !m2) return [];
      var r1 = Math.min(+m1[2], +m2[2]) - 1, r2 = Math.max(+m1[2], +m2[2]) - 1;
      var c1 = Math.min(colIdx(m1[1]), colIdx(m2[1])), c2 = Math.max(colIdx(m1[1]), colIdx(m2[1]));
      var out = [];
      for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) out.push(evalCell(sh, r, c, visiting));
      return out;
    }
    function factor() {
      var t = peek();
      if (t.t === 'num') { eat(); return t.v; }
      if (t.t === 'str') { eat(); return t.v; }
      if (t.t === '-') { eat(); return -num(factor()); }
      if (t.t === '(') { eat(); var v = expr(); if (peek().t === ')') eat(); return v; }
      if (t.t === 'ref') {
        eat();
        if (peek().t === ':') { eat(); var t2 = eat(); return rangeVals(t.v, t2.v); }
        return refVal(t.v);
      }
      if (t.t === 'name') {
        eat();
        var fn = t.v, args = [];
        if (peek().t === '(') {
          eat();
          while (peek().t !== ')' && peek().t !== 'end') {
            args.push(expr());
            if (peek().t === ',') eat();
          }
          if (peek().t === ')') eat();
        }
        return callFn(fn, args);
      }
      eat(); return '#ERR';
    }
    function flat(a) { var o = []; (Array.isArray(a) ? a : [a]).forEach(function (x) { o = o.concat(Array.isArray(x) ? flat(x) : [x]); }); return o; }
    function callFn(fn, args) {
      var vals = flat(args);
      if (fn === 'SUM') { var s = 0; vals.forEach(function (v) { s += num(v); }); return s; }
      if (fn === 'MIN') { return vals.length ? Math.min.apply(null, vals.map(num)) : 0; }
      if (fn === 'MAX') { return vals.length ? Math.max.apply(null, vals.map(num)) : 0; }
      if (fn === 'AVERAGE') { if (!vals.length) return 0; var s2 = 0; vals.forEach(function (v) { s2 += num(v); }); return s2 / vals.length; }
      if (fn === 'COGS') { var v0 = vals[0]; return (v0 === '' || v0 == null) ? '' : encode(v0, C1); }
      if (fn === 'DEALER') { var v1 = vals[0]; return (v1 === '' || v1 == null) ? '' : encode(v1, C2); }
      if (fn === 'DB') {
        var db = window.TIRE_DB || {};
        var code = String(args[0] == null ? '' : args[0]), field = String(args[1] == null ? '' : args[1]);
        var rec = db[code];
        return rec && rec[field] != null ? rec[field] : '';
      }
      return '#ERR';
    }
    function term() {
      var v = factor();
      while (peek().t === '*' || peek().t === '/') {
        var op = eat().t, v2 = factor();
        v = op === '*' ? num(v) * num(v2) : (num(v2) === 0 ? '#DIV/0' : num(v) / num(v2));
        if (v === '#DIV/0') return v;
      }
      return v;
    }
    function expr() {
      var v = term();
      while (peek().t === '+' || peek().t === '-' || peek().t === '&') {
        var op = eat().t, v2 = term();
        if (op === '&') v = String(v == null ? '' : v) + String(v2 == null ? '' : v2);
        else if (op === '+') v = num(v) + num(v2);
        else v = num(v) - num(v2);
      }
      return v;
    }
    var out = expr();
    return out;
  }

  function evalCell(sh, r, c, visiting) {
    var cell = cellAt(sh, r, c);
    if (!cell) return '';
    if (!cell.f) return cell.v;
    var key = r + ',' + c;
    visiting = visiting || {};
    if (visiting[key]) return '#วน!';
    visiting[key] = 1;
    var out;
    try { out = evalFormula(sh, cell.f.replace(/^=/, ''), visiting); }
    catch (e) { out = '#ERR'; }
    delete visiting[key];
    if (Array.isArray(out)) out = out[0];
    return out == null ? '' : out;
  }

  // display string (with format type + thousands)
  function display(sh, r, c) {
    var cell = cellAt(sh, r, c);
    if (!cell) return '';
    var v = cell.f ? evalCell(sh, r, c) : cell.v;
    if (v === '' || v == null) return '';
    var t = cell.t || 'auto';
    if (t === 'text') return String(v);
    if (typeof v === 'number' || (t !== 'text' && isNumeric(v))) {
      var n = typeof v === 'number' ? v : num(v);
      if (t === 'num' || t === 'auto') {
        var isInt = Math.abs(n - Math.round(n)) < 1e-9;
        return isInt ? Math.round(n).toLocaleString('en-US') : n.toLocaleString('en-US', { maximumFractionDigits: 2 });
      }
    }
    return String(v);
  }

  // ---- ref adjust (สำหรับ fill copy + แทรก/ลบแถว) ----
  function shiftFormula(f, dr, dc) {
    return f.replace(/(\$?)([A-Z]+)(\$?)(\d+)/g, function (m, d1, cn, d2, rn) {
      var c = colIdx(cn), r = +rn - 1;
      if (!d1) c += dc;
      if (!d2) r += dr;
      if (c < 0 || r < 0) return '#REF!';
      return d1 + colName(c) + d2 + (r + 1);
    });
  }
  function adjustFormulasRows(sh, at, delta) {  // at = row index ที่แทรก/ลบ
    Object.keys(sh.cells).forEach(function (k) {
      var cell = sh.cells[k];
      if (!cell.f) return;
      cell.f = cell.f.replace(/(\$?)([A-Z]+)(\$?)(\d+)/g, function (m, d1, cn, d2, rn) {
        var r = +rn - 1;
        if (delta > 0 && r >= at) r += delta;
        else if (delta < 0) {
          if (r >= at && r < at - delta) return '#REF!';
          if (r >= at - delta) r += delta;
        }
        return d1 + cn + d2 + (r + 1);
      });
    });
  }

  // ---- row ops ----
  function remapKeyed(obj, at, delta) {
    var out = {};
    Object.keys(obj).forEach(function (k) {
      var r = +k;
      if (delta > 0) { out[r >= at ? r + delta : r] = obj[k]; }
      else { if (r >= at && r < at - delta) return; out[r >= at - delta ? r + delta : r] = obj[k]; }
    });
    return out;
  }
  function insertRow(sh, at, kind, gid) {
    var newCells = {};
    Object.keys(sh.cells).forEach(function (k) {
      var p = k.split(','), r = +p[0], c = +p[1];
      newCells[(r >= at ? r + 1 : r) + ',' + c] = sh.cells[k];
    });
    sh.cells = newCells;
    sh.rowH.splice(at, 0, 24);
    sh.rowKind.splice(at, 0, kind || 'data');
    sh.rowGid.splice(at, 0, gid != null ? gid : null);
    sh.merges.forEach(function (mg) {
      if (mg.r >= at) mg.r++;
      else if (mg.r + mg.rs > at) mg.rs++;
    });
    sh.adminRows = remapKeyed(sh.adminRows, at, 1);
    sh.nR++;
    adjustFormulasRows(sh, at, 1);
  }
  function deleteRowRange(sh, at, count) {
    var newCells = {};
    Object.keys(sh.cells).forEach(function (k) {
      var p = k.split(','), r = +p[0], c = +p[1];
      if (r >= at && r < at + count) return;
      newCells[(r >= at + count ? r - count : r) + ',' + c] = sh.cells[k];
    });
    sh.cells = newCells;
    sh.rowH.splice(at, count);
    sh.rowKind.splice(at, count);
    sh.rowGid.splice(at, count);
    sh.merges = sh.merges.filter(function (mg) {
      var end = mg.r + mg.rs;
      if (mg.r >= at && end <= at + count) return false;
      if (mg.r >= at + count) { mg.r -= count; return true; }
      if (mg.r < at && end > at) { mg.rs -= Math.min(end, at + count) - at; return mg.rs > 0; }
      if (mg.r >= at) { var cut = at + count - mg.r; mg.r = at; mg.rs -= cut; return mg.rs > 0; }
      return true;
    });
    sh.adminRows = remapKeyed(sh.adminRows, at, -count);
    sh.nR -= count;
    adjustFormulasRows(sh, at, -count);
  }

  // ---- merges ----
  function mergeAt(sh, r, c) {
    for (var i = 0; i < sh.merges.length; i++) {
      var m = sh.merges[i];
      if (r >= m.r && r < m.r + m.rs && c >= m.c && c < m.c + m.cs) return m;
    }
    return null;
  }
  function addMerge(sh, r, c, rs, cs, auto) {
    // ลบ merge เดิมที่ทับซ้อน
    sh.merges = sh.merges.filter(function (m) {
      return !(m.r < r + rs && r < m.r + m.rs && m.c < c + cs && c < m.c + m.cs);
    });
    if (rs > 1 || cs > 1) sh.merges.push({ r: r, c: c, rs: rs, cs: cs, auto: !!auto });
  }
  function unmergeRange(sh, r1, c1, r2, c2) {
    sh.merges = sh.merges.filter(function (m) {
      return !(m.r <= r2 && r1 <= m.r + m.rs - 1 && m.c <= c2 && c1 <= m.c + m.cs - 1);
    });
  }
  // rebuild size-column merges (col 0) ตาม rowGid
  function rebuildSizeMerges(sh) {
    sh.merges = sh.merges.filter(function (m) { return !(m.auto && m.c === 0); });
    var r = 0;
    while (r < sh.nR) {
      if (sh.rowKind[r] === 'data' && sh.rowGid[r] != null) {
        var g = sh.rowGid[r], start = r, n = 0;
        while (r < sh.nR && sh.rowKind[r] === 'data' && sh.rowGid[r] === g) { n++; r++; }
        if (n > 1) sh.merges.push({ r: start, c: 0, rs: n, cs: 1, auto: true });
      } else r++;
    }
  }

  // ---- storage ----
  var LS = window.localStorage;
  function loadJSON(k, d) { try { return JSON.parse(LS.getItem(k) || 'null') || d; } catch (e) { return d; } }
  var store = {
    loadCurrent: function () { return loadJSON('xl2_current', null); },
    saveCurrent: function (sh) { LS.setItem('xl2_current', JSON.stringify(sh)); },
    loadVersions: function () { return loadJSON('xl2_versions', []); },
    saveVersions: function (v) { LS.setItem('xl2_versions', JSON.stringify(v)); },
    loadVersion: function (id) { return loadJSON('xl2_v_' + id, null); },
    saveVersionDoc: function (id, sh) { LS.setItem('xl2_v_' + id, JSON.stringify(sh)); },
    deleteVersion: function (id) { LS.removeItem('xl2_v_' + id); store.saveVersions(store.loadVersions().filter(function (x) { return x.id !== id; })); }
  };

  window.XL2 = {
    C1: C1, C2: C2, encode: encode, cogs: function (n) { return encode(n, C1); }, dealer: function (n) { return encode(n, C2); },
    colName: colName, colIdx: colIdx, refStr: refStr, num: num, isNumeric: isNumeric,
    newSheet: newSheet, cellAt: cellAt, ensure: ensure,
    evalCell: evalCell, evalFormula: evalFormula, display: display,
    shiftFormula: shiftFormula, insertRow: insertRow, deleteRowRange: deleteRowRange,
    mergeAt: mergeAt, addMerge: addMerge, unmergeRange: unmergeRange, rebuildSizeMerges: rebuildSizeMerges,
    store: store
  };
})();
