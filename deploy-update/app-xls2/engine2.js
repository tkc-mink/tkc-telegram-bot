/* ============================================================
   engine2.js — formula engine + cipher + A1 utils + palettes
   exposes window.XL2
   ============================================================ */
(function () {
  // ---- Cipher (A = ซ้ำตัวก่อนหน้า ใช้ติดกันครั้งเดียว ไม่มี AA) ----
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
  function decode(code, map) {
    var inv = {}; map.forEach(function (l, d) { inv[l] = d; });
    var s = String(code || '').toUpperCase(), out = '', prev = null;
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (c === 'A') { out += (prev == null ? '' : prev); }
      else if (inv[c] != null) { out += inv[c]; prev = String(inv[c]); }
    }
    return out;
  }
  var cogs = function (n) { return encode(n, C1); };
  var dealer = function (n) { return encode(n, C2); };

  // ---- A1 utils ----
  function colName(c) { var s = ''; c = c + 1; while (c > 0) { var m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = Math.floor((c - 1) / 26); } return s; }
  function colIndex(name) { var n = 0, u = name.toUpperCase(); for (var i = 0; i < u.length; i++) n = n * 26 + (u.charCodeAt(i) - 64); return n - 1; }
  function refStr(r, c) { return colName(c) + (r + 1); }
  function parseRefToken(tok) {
    var m = /^(\$?)([A-Za-z]{1,3})(\$?)([0-9]+)$/.exec(tok);
    if (!m) return null;
    return { r: +m[4] - 1, c: colIndex(m[2]), absC: m[1] === '$', absR: m[3] === '$' };
  }

  // ---- numbers ----
  function toN(v) {
    if (typeof v === 'number') return v;
    if (v === '' || v == null) return 0;
    var s = String(v).replace(/,/g, '').trim();
    if (!s) return 0;                      // ช่องมีแต่ช่องว่าง/เว้นวรรค = 0 (เหมือน Excel)
    var n = +s;
    if (isNaN(n)) throw 'NaN';
    return n;
  }
  function isNumeric(v) {
    if (typeof v === 'number') return isFinite(v);
    if (v === '' || v == null) return false;
    return isFinite(+String(v).replace(/,/g, ''));
  }
  function fmtNum(n) {
    if (!isFinite(n)) return '#ERR';
    var neg = n < 0, a = Math.abs(n);
    var s = (Math.round(a * 100) / 100);
    var str = (s % 1 === 0) ? s.toLocaleString('en-US') : s.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    return (neg ? '-' : '') + str;
  }

  // ---- formula evaluator ----
  // supports: + - * / % & ( ) comparisons, "strings", refs A1, ranges A1:B9,
  // SUM AVG MIN MAX COUNT ROUND ABS IF COGS DEALER DB
  function evaluate(src, getRef) {
    var s = String(src || ''); if (s.charAt(0) === '=') s = s.slice(1);
    var pos = 0;
    function skip() { while (pos < s.length && s[pos] === ' ') pos++; }
    function parseCmp() {
      var v = parseAdd();
      for (;;) {
        skip(); var op = null;
        if (s.substr(pos, 2) === '<>') op = '<>';
        else if (s.substr(pos, 2) === '<=') op = '<=';
        else if (s.substr(pos, 2) === '>=') op = '>=';
        else if (s[pos] === '=' ) op = '=';
        else if (s[pos] === '<') op = '<';
        else if (s[pos] === '>') op = '>';
        if (!op) break;
        pos += op.length;
        var r = parseAdd(), a, b;
        try { a = toN(v); b = toN(r); } catch (e) { a = String(v); b = String(r); }
        v = (op === '=' ? a === b : op === '<>' ? a !== b : op === '<' ? a < b : op === '>' ? a > b : op === '<=' ? a <= b : a >= b) ? 1 : 0;
      }
      return v;
    }
    function parseAdd() {
      var v = parseMul();
      for (;;) {
        skip(); var ch = s[pos];
        if (ch === '+' || ch === '-' || ch === '&') {
          pos++; var r = parseMul();
          if (ch === '&') v = String(v == null ? '' : v) + String(r == null ? '' : r);
          else v = (ch === '+') ? toN(v) + toN(r) : toN(v) - toN(r);
        } else break;
      }
      return v;
    }
    function parseMul() {
      var v = parseUn();
      for (;;) {
        skip(); var ch = s[pos];
        if (ch === '*' || ch === '/') { pos++; var r = parseUn(); v = (ch === '*') ? toN(v) * toN(r) : toN(v) / toN(r); }
        else break;
      }
      return v;
    }
    function parseUn() {
      skip();
      if (s[pos] === '-') { pos++; return -toN(parseUn()); }
      if (s[pos] === '+') { pos++; return toN(parseUn()); }
      var v = parsePrim(); skip();
      if (s[pos] === '%') { pos++; v = toN(v) / 100; }
      return v;
    }
    function refVals(t1, t2) {
      var a = parseRefToken(t1.replace(/\$/g, '$')), b = parseRefToken(t2);
      a = parseRefToken(t1); b = parseRefToken(t2);
      var out = [];
      for (var r = Math.min(a.r, b.r); r <= Math.max(a.r, b.r); r++)
        for (var c = Math.min(a.c, b.c); c <= Math.max(a.c, b.c); c++) out.push(getRef(r, c));
      return out;
    }
    function parseArg() {
      skip();
      var m = /^(\$?[A-Za-z]{1,3}\$?[0-9]+)\s*:\s*(\$?[A-Za-z]{1,3}\$?[0-9]+)/.exec(s.slice(pos));
      if (m) { pos += m[0].length; return { range: refVals(m[1], m[2]) }; }
      return parseCmp();
    }
    function flat(args) {
      var out = [];
      args.forEach(function (a) { if (a && a.range) out = out.concat(a.range); else out.push(a); });
      return out;
    }
    function nums(args) { return flat(args).filter(function (v) { return isNumeric(v); }).map(function (v) { return toN(v); }); }
    function callFn(name, args) {
      switch (name) {
        case 'SUM': return nums(args).reduce(function (a, b) { return a + b; }, 0);
        case 'AVG': case 'AVERAGE': { var n = nums(args); return n.length ? n.reduce(function (a, b) { return a + b; }, 0) / n.length : 0; }
        case 'MIN': { var n = nums(args); return n.length ? Math.min.apply(null, n) : 0; }
        case 'MAX': { var n = nums(args); return n.length ? Math.max.apply(null, n) : 0; }
        case 'COUNT': return nums(args).length;
        case 'COUNTA': return flat(args).filter(function (v) { return v !== '' && v != null; }).length;
        case 'ROUND': { var p = Math.pow(10, args[1] ? toN(args[1]) : 0); return Math.round(toN(args[0]) * p) / p; }
        case 'ABS': return Math.abs(toN(args[0]));
        case 'IF': { var c; try { c = toN(args[0]) !== 0; } catch (e) { c = !!args[0]; } return c ? args[1] : (args.length > 2 ? args[2] : ''); }
        case 'COGS': return cogs(flat([args[0]])[0]);
        case 'DEALER': return dealer(flat([args[0]])[0]);
        case 'DB': return dbLookup(String(flat([args[0]])[0] || ''), String(flat([args[1]])[0] || ''));
        default: throw 'fn';
      }
    }
    function parsePrim() {
      skip(); var ch = s[pos];
      if (ch === undefined) throw 'eof';
      if ((ch >= '0' && ch <= '9') || ch === '.') {
        var m = /^[0-9]*\.?[0-9]+/.exec(s.slice(pos)); pos += m[0].length; return parseFloat(m[0]);
      }
      if (ch === '"') { var e = s.indexOf('"', pos + 1); var str = s.slice(pos + 1, e < 0 ? s.length : e); pos = (e < 0 ? s.length : e + 1); return str; }
      if (ch === '(') { pos++; var v = parseCmp(); skip(); if (s[pos] === ')') pos++; return v; }
      // range?
      var rg = /^(\$?[A-Za-z]{1,3}\$?[0-9]+)\s*:\s*(\$?[A-Za-z]{1,3}\$?[0-9]+)/.exec(s.slice(pos));
      if (rg) { pos += rg[0].length; var vals = refVals(rg[1], rg[2]); return vals.length ? toN(vals[0]) : 0; }
      // ref?
      var rm = /^\$?[A-Za-z]{1,3}\$?[0-9]+(?![A-Za-z0-9_(])/.exec(s.slice(pos));
      if (rm) { pos += rm[0].length; var rc = parseRefToken(rm[0]); return getRef(rc.r, rc.c); }
      // function
      var fm = /^[A-Za-z\u0E00-\u0E7F_][A-Za-z0-9_\.\u0E00-\u0E7F]*/.exec(s.slice(pos));
      if (fm) {
        var after = pos + fm[0].length, t = after;
        while (s[t] === ' ') t++;
        if (s[t] === '(') {
          var name = fm[0].toUpperCase(); pos = t + 1; var args = [];
          skip();
          if (s[pos] === ')') { pos++; }
          else {
            for (;;) { args.push(parseArg()); skip(); if (s[pos] === ',') { pos++; continue; } if (s[pos] === ')') { pos++; break; } throw 'arg'; }
          }
          return callFn(name, args);
        }
      }
      throw 'tok';
    }
    var out = parseCmp();
    skip();
    if (pos < s.length) throw 'trail';
    return out;
  }

  // ---- formula ref rewriting ----
  var REF_RE = /(\$?)([A-Za-z]{1,3})(\$?)([0-9]+)(?![A-Za-z0-9_(])/g;
  function remapFormula(f, fn) {
    return f.replace(REF_RE, function (all, d1, L, d2, R) {
      var r = +R - 1, c = colIndex(L);
      var out = fn(r, c);
      if (out === null) return '#REF!';
      return d1 + colName(out[1]) + d2 + (out[0] + 1);
    });
  }
  function shiftFormula(f, dr, dc) {
    return f.replace(REF_RE, function (all, d1, L, d2, R) {
      var r = +R - 1, c = colIndex(L);
      if (d2 !== '$') r += dr;
      if (d1 !== '$') c += dc;
      if (r < 0 || c < 0) return '#REF!';
      return d1 + colName(c) + d2 + (r + 1);
    });
  }

  // ---- mock database (จะเชื่อม server จริงภายหลัง) ----
  // ชื่อยี่ห้อเต็ม ↔ อักษรย่อ (OTANI → OT)
  var BRAND_FULL = { OT: 'OTANI', BS: 'BRIDGESTONE', MC: 'MAXXIS', DL: 'DUNLOP', YK: 'YOKOHAMA', DS: 'DEESTONE', KR: 'KENDA RADIAL', KT: 'KENETICA', RX: 'ROADX', MI: 'MICHELIN', GY: 'GOODYEAR', TY: 'TOYO', HK: 'HANKOOK' };
  var BRAND_ABBR = {}; Object.keys(BRAND_FULL).forEach(function (a) { BRAND_ABBR[BRAND_FULL[a].toUpperCase()] = a; });
  function brandAbbr(b) { var u = String(b || '').toUpperCase().trim(); return BRAND_ABBR[u] || u; }
  function brandFull(b) { var u = String(b || '').toUpperCase().trim(); return BRAND_FULL[u] || b; }

  var DBmap = null, DBkeys = [], DBlist = [];
  function buildDb() {
    DBmap = {}; DBkeys = []; DBlist = [];
    var src = window.PICKUP01;
    if (!src) return;
    src.rows.forEach(function (r, i) {
      var k = (r.size + '|' + r.brand + '|' + r.model).toUpperCase();
      var code = 'TKC-' + String(1001 + i);   // รหัสสินค้า (mock — จะใช้รหัสจริงจาก server ภายหลัง)
      var name = r.size + ' ' + brandFull(r.brand) + ' ' + r.model;
      DBmap[k] = { 'ทุน': r.cost, 'ราคา': r.retail, 'B': r.priceB, 'A': r.priceA, 'S': r.priceS, 'DOT': r.dot,
        'ยี่ห้อ': brandAbbr(r.brand), 'ยี่ห้อเต็ม': brandFull(r.brand), 'รุ่น': r.model, 'รหัส': code, 'ชื่อ': name };
      DBkeys.push(r.size + '|' + r.brand + '|' + r.model);
      DBlist.push({ key: r.size + '|' + r.brand + '|' + r.model, code: code, name: name });
    });
  }
  function dbList() { if (!DBmap) buildDb(); return DBlist; }
  function dbInfo(key) {
    if (!DBmap) buildDb();
    var k = String(key || '').toUpperCase().trim();
    var hit = DBlist.find(function (x) { return x.key.toUpperCase() === k; });
    return hit || { key: key, code: '', name: key };
  }
  function dbLookup(code, field) {
    if (!DBmap) buildDb();
    var rec = DBmap[String(code).toUpperCase().trim()];
    if (!rec) return '#N/A';
    var v = rec[field] != null ? rec[field] : rec[String(field).toUpperCase()];
    return v == null ? '#N/A' : v;
  }
  function dbKeys() { if (!DBmap) buildDb(); return DBkeys; }

  // ---- palettes ----
  var PALETTE = [
    { n: 'ไม่มีสี', c: null },
    { n: 'เหลือง', c: 'FFFF00' }, { n: 'เหลืองอ่อน', c: 'FFFF99' }, { n: 'ครีม', c: 'FFFFCC' },
    { n: 'ส้ม', c: 'FF9900' }, { n: 'ส้มอ่อน', c: 'FDE9D9' }, { n: 'พีช', c: 'FFCC99' },
    { n: 'เขียว', c: '92D050' }, { n: 'เขียวอ่อน', c: 'CCFFCC' }, { n: 'มิ้นต์', c: 'CCFF99' },
    { n: 'ฟ้า', c: '00B0F0' }, { n: 'ฟ้าอ่อน', c: 'CCFFFF' }, { n: 'ฟ้าน้ำเงิน', c: '00FFFF' },
    { n: 'ชมพู', c: 'FF99CC' }, { n: 'ชมพูอ่อน', c: 'FFCCFF' }, { n: 'ม่วงอ่อน', c: 'E5DFEC' },
    { n: 'เทา', c: 'D8D8D8' }, { n: 'เทาเข้ม', c: 'BFBFBF' }, { n: 'แดง', c: 'FF6666' }
  ];
  var FONT_PALETTE = [
    { n: 'ค่าเริ่มต้น', c: null },
    { n: 'ดำ', c: '000000' }, { n: 'เทา', c: '808080' }, { n: 'ขาว', c: 'FFFFFF' },
    { n: 'แดง', c: 'FF0000' }, { n: 'แดงเข้ม', c: 'C00000' }, { n: 'ส้ม', c: 'FF6600' },
    { n: 'ทอง', c: 'BF8F00' }, { n: 'เขียว', c: '008000' }, { n: 'เขียวสด', c: '00B050' },
    { n: 'ฟ้า', c: '00B0F0' }, { n: 'น้ำเงิน', c: '0000FF' }, { n: 'ม่วง', c: '7030A0' },
    { n: 'ชมพูบานเย็น', c: 'FF00FF' }, { n: 'ชมพู', c: 'FF33CC' }
  ];

  // ---- storage ----
  var LS = window.localStorage;
  function loadJSON(k, d) { try { return JSON.parse(LS.getItem(k) || JSON.stringify(d)); } catch (e) { return d; } }
  // หลายหมวด (sheet) — แต่ละหมวดมีเอกสารของตัวเอง
  function curSheet() { return LS.getItem('xls2_cur_sheet') || ''; }
  var store = {
    sheetsList: function () { return loadJSON('xls2_sheets', []); },
    saveSheets: function (s) { LS.setItem('xls2_sheets', JSON.stringify(s)); },
    curSheet: curSheet,
    setCurSheet: function (id) { LS.setItem('xls2_cur_sheet', id); },
    deleteSheetDoc: function (id) { LS.removeItem('xls2_sheet_' + id); },
    saveSheetDoc: function (id, doc) { LS.setItem('xls2_sheet_' + id, JSON.stringify(doc)); },
    loadSheetDoc: function (id) { return loadJSON('xls2_sheet_' + id, null); },
    loadCurrent: function () {
      var id = curSheet();
      if (id) { var d = loadJSON('xls2_sheet_' + id, null); if (d) return d; }
      return loadJSON('xls2_current', null);   // legacy
    },
    saveCurrent: function (doc) {
      var id = curSheet();
      if (id) LS.setItem('xls2_sheet_' + id, JSON.stringify(doc));
      else LS.setItem('xls2_current', JSON.stringify(doc));
    },
    loadVersions: function () { return loadJSON('xls2_versions', []); },
    saveVersions: function (v) { LS.setItem('xls2_versions', JSON.stringify(v)); },
    loadVersion: function (id) { return loadJSON('xls2_v_' + id, null); },
    saveVersionDoc: function (id, doc) { LS.setItem('xls2_v_' + id, JSON.stringify(doc)); },
    deleteVersion: function (id) { LS.removeItem('xls2_v_' + id); store.saveVersions(store.loadVersions().filter(function (x) { return x.id !== id; })); }
  };

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  window.XL2 = {
    C1: C1, C2: C2, cogs: cogs, dealer: dealer, encode: encode, decode: decode,
    colName: colName, colIndex: colIndex, refStr: refStr, parseRefToken: parseRefToken,
    toN: toN, isNumeric: isNumeric, fmtNum: fmtNum,
    evaluate: evaluate, remapFormula: remapFormula, shiftFormula: shiftFormula,
    dbLookup: dbLookup, dbKeys: dbKeys, dbList: dbList, dbInfo: dbInfo, brandAbbr: brandAbbr, brandFull: brandFull,
    PALETTE: PALETTE, FONT_PALETTE: FONT_PALETTE, store: store, esc: esc
  };
})();
