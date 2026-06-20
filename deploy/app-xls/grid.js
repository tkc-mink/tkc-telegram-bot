/* ============================================================
   grid.js — the spreadsheet: render + Excel-like interaction
   depends on window.XLS (engine.js) and window.PICKUP01 (data)
   exposes window.Grid
   ============================================================ */
(function () {
  var XLS = window.XLS, COLS = XLS.COLS, num = XLS.num, fmt = XLS.fmt;

  // ---------- state ----------
  var doc = null;            // { meta, rows, colors, name }
  var view = { secret:false, zoom:1, mode:'admin' };   // mode: admin | user
  var sel = { r:0, c:0, ar:0, ac:0 };   // active (r,c) + anchor (ar,ac)
  var editing = null;        // { r, c }
  var undoStack = [], redoStack = [];
  var clip = null;           // { vals:[[...]], rows, cols }
  var rootEl, inputEl, statusEl, fhEl, ctxEl;
  var cover = {};            // merged-cell coverage map: "r:c" -> [anchorR, anchorC]
  var resize = null;         // active col/row resize drag
  var filling = null;        // active fill-handle drag

  // ---------- helpers ----------
  function deepRows() { return JSON.parse(JSON.stringify(doc.rows)); }
  function snapshot() { return { rows: deepRows(), colors: JSON.parse(JSON.stringify(doc.colors || {})), fontColors: JSON.parse(JSON.stringify(doc.fontColors || {})), fontStyles: JSON.parse(JSON.stringify(doc.fontStyles || {})), adminRows: JSON.parse(JSON.stringify(doc.adminRows || {})), adminCols: JSON.parse(JSON.stringify(doc.adminCols || {})), merges: JSON.parse(JSON.stringify(doc.merges || {})), formats: JSON.parse(JSON.stringify(doc.formats || {})), headerLabels: JSON.parse(JSON.stringify(doc.headerLabels || {})) }; }
  function pushUndo() {
    undoStack.push(snapshot());
    if (undoStack.length > 60) undoStack.shift();
    redoStack.length = 0;
  }
  function restore(s) { doc.rows = s.rows; doc.colors = s.colors; doc.fontColors = s.fontColors || {}; doc.fontStyles = s.fontStyles || {}; doc.adminRows = s.adminRows || {}; doc.adminCols = s.adminCols || {}; doc.merges = s.merges || {}; doc.formats = s.formats || {}; doc.headerLabels = s.headerLabels || {}; }
  function persist() { try { XLS.store.saveCurrent(doc); } catch (e) {} markDirty(); }

  var dirty = false;
  function markDirty() { dirty = true; var b = document.getElementById('saveState'); if (b) b.textContent = '● ยังไม่บันทึก'; }
  function markClean() { dirty = false; var b = document.getElementById('saveState'); if (b) b.textContent = '✓ บันทึกแล้ว'; }

  function groupLeader(ri) {
    var g = doc.rows[ri].gid;
    var i = ri; while (i > 0 && doc.rows[i - 1].gid === g) i--;
    return i;
  }
  function groupCount(ri) {
    var lead = groupLeader(ri), g = doc.rows[lead].gid, n = 1;
    while (lead + n < doc.rows.length && doc.rows[lead + n].gid === g) n++;
    return n;
  }

  // ---------- admin/user visibility ----------
  function isRowHidden(ri) { return view.mode === 'user' && doc.adminRows && doc.adminRows[doc.rows[ri].id]; }
  function isColHidden(ci) { return view.mode === 'user' && doc.adminCols && doc.adminCols[COLS[ci].k]; }
  function visCols() { var a = []; for (var i = 0; i < COLS.length; i++) if (!isColHidden(i)) a.push(i); return a; }
  function visLeader(ri) {
    var lead = groupLeader(ri);
    for (var j = lead; j <= ri; j++) { if (!isRowHidden(j)) return j; }
    return ri;
  }
  function visSpan(ri) {
    var lead = groupLeader(ri), g = doc.rows[lead].gid, n = 0;
    for (var j = lead; j < doc.rows.length && doc.rows[j].gid === g; j++) { if (!isRowHidden(j)) n++; }
    return Math.max(1, n);
  }
  function stepRow(r, dir) { var n = r + dir; while (n >= 0 && n < doc.rows.length && isRowHidden(n)) n += dir; return (n < 0 || n >= doc.rows.length) ? r : n; }
  function stepCol(c, dir) { var n = c + dir; while (n >= 0 && n < COLS.length && isColHidden(n)) n += dir; return (n < 0 || n >= COLS.length) ? c : n; }

  function cellDisplay(ri, ci) {
    var row = doc.rows[ri], col = COLS[ci];
    var v = (col.t === 'calc' || col.t === 'cipher') ? XLS.compute(col, row) : row[col.k];
    if (view.secret && col.secret) return '•••';
    var fo = doc.formats && doc.formats[ri + ':' + col.k];   // รูปแบบที่ผู้ใช้กำหนด (คลิกขวา)
    if (fo === 'txt') return v == null ? '' : String(v);
    if (fo === 'num') return fmt(v);
    if (col.t === 'int') return fmt(v);
    if (col.t === 'calc') { var n = num(v); return n ? (n > 0 ? '+' + fmt(n) : fmt(n)) : (v === '' ? '' : '0'); }
    return v == null ? '' : String(v);
  }

  // ---------- merged-cell coverage ----------
  function buildCover() {
    cover = {};
    if (!doc || !doc.merges) return;
    Object.keys(doc.merges).forEach(function (k) {
      var p = k.split(':'), ar = +p[0], ac = +p[1], m = doc.merges[k];
      if (ar >= doc.rows.length || ac >= COLS.length) { delete doc.merges[k]; return; }
      for (var r = ar; r < Math.min(ar + m.rs, doc.rows.length); r++)
        for (var c = ac; c < Math.min(ac + m.cs, COLS.length); c++) {
          if (r === ar && c === ac) continue;
          cover[r + ':' + c] = [ar, ac];
        }
    });
  }
  function anchorOf(r, c) {
    var rr = normSize(r, c);
    var cv = cover[rr + ':' + c];
    return cv ? [cv[0], cv[1]] : [rr, c];
  }

  // ---------- render ----------
  function render() {
    buildCover();
    var rows = doc.rows, html = '';
    var vc = visCols(), isAdmin = (view.mode === 'admin');
    html += '<table class="xl' + (isAdmin ? '' : ' usermode') + '" style="font-size:' + (10 * view.zoom) + 'px">';
    html += '<colgroup>';
    html += '<col style="width:' + Math.round(26 * view.zoom) + 'px">';   // row-number gutter
    vc.forEach(function (ci) { var wpx = (doc.colW && doc.colW[COLS[ci].k]) || COLS[ci].w; html += '<col data-ci="' + ci + '" style="width:' + Math.round(wpx * view.zoom) + 'px">'; });
    html += '</colgroup>';
    var TOT = vc.length + 1;

    // A-B-C column letters (เหมือน Excel)
    html += '<tr class="r-abc" style="height:' + Math.round(17 * view.zoom) + 'px"><th class="abc-corner"></th>';
    vc.forEach(function (ci) { html += '<th class="abc" data-hc="' + ci + '" title="คอลัมน์ ' + String.fromCharCode(65 + ci) + ' — คลิก/ลากเพื่อเลือกทั้งคอลัมน์">' + String.fromCharCode(65 + ci) + '</th>'; });
    html += '</tr>';

    // Title band (ดับเบิ้ลคลิกแก้ไขได้) — ชีตต่อเนื่อง ไม่มีเลขหน้า
    var titleText = doc.meta.titleText || ('ราคา' + doc.meta.title + ' ประจำเดือน ' + doc.meta.month + ' (ชั่วคราว)');
    html += '<tr class="r-title" style="height:' + (28 * view.zoom) + 'px">';
    html += '<td class="title-cell editable-band" data-mk="title" colspan="' + TOT + '" title="ดับเบิ้ลคลิกเพื่อแก้ข้อความ">' + esc(titleText) + '</td></tr>';
    // Category band
    html += '<tr class="r-cat" style="height:' + (26 * view.zoom) + 'px"><td colspan="' + TOT + '" class="cat-cell editable-band" data-mk="cat" title="ดับเบิ้ลคลิกเพื่อแก้ข้อความ">' + esc(doc.meta.category) + '</td></tr>';
    // user-view banner
    if (!isAdmin) html += '<tr class="r-uview"><td colspan="' + TOT + '" class="uview-cell">👁️ มุมมองผู้ใช้ — แถว/คอลัมน์ที่ติด 🔒 ถูกซ่อน · อ่านอย่างเดียว</td></tr>';

    var lastRim = null, rowNo = 0;
    for (var ri = 0; ri < rows.length; ri++) {
      if (isRowHidden(ri)) continue;
      var row = rows[ri];
      if (row.rim !== lastRim) {
        lastRim = row.rim;
        html += sectionHeaderHTML(row, vc, ri);
        html += columnHeaderHTML(vc);
      }
      rowNo++;
      html += rowHTML(ri, vc, rowNo);
    }
    html += '</table>';
    rootEl.innerHTML = html;
    if (inputEl) rootEl.appendChild(inputEl);   // keep overlay after re-render
    if (fhEl) rootEl.appendChild(fhEl);         // fill handle overlay
    paintSelection();
    updateStatus();
  }

  function sectionHeaderHTML(row, vc, sri) {
    function cnt(a, b) { var n = 0; vc.forEach(function (ci) { if (ci >= a && ci <= b) n++; }); return n; }
    var h = '<tr class="r-sect" style="height:' + (20 * view.zoom) + 'px">';
    h += '<td class="gut"></td>';
    var z1 = cnt(0, 1), z2 = cnt(2, 5), z3 = cnt(6, 12), z4 = cnt(13, 21), z5 = cnt(22, 22);
    var dealerText = doc.dealerLabel || 'Dealer (ราคาส่ง · รหัสลับ)';
    if (z1) h += '<td class="sect-rim editable-band" data-mk="rim" data-sri="' + sri + '" colspan="' + z1 + '" title="ดับเบิ้ลคลิกเพื่อแก้ข้อความ">' + esc(row.rim) + '</td>';
    if (z2) h += '<td class="sect-series editable-band" data-mk="series" data-sri="' + sri + '" colspan="' + z2 + '" title="ดับเบิ้ลคลิกเพื่อแก้ข้อความ">' + esc(row.series || '') + '</td>';
    if (z3) h += '<td colspan="' + z3 + '"></td>';
    if (z4) h += '<td class="sect-dealer editable-band" data-mk="dealer" colspan="' + z4 + '" title="ดับเบิ้ลคลิกเพื่อแก้ข้อความ">' + esc(dealerText) + '</td>';
    if (z5) h += '<td colspan="' + z5 + '"></td>';
    h += '</tr>';
    return h;
  }

  // ชื่อหัวคอลัมน์ (แก้ได้ เก็บ override ใน doc.headerLabels)
  function hdr(c) {
    var o = doc.headerLabels && doc.headerLabels[c.k];
    return { L: (o && o.L != null) ? o.L : c.L, sub: (o && o.sub != null) ? o.sub : (c.sub || '') };
  }

  function columnHeaderHTML(vc) {
    var isAdmin = (view.mode === 'admin');
    var abcOff = 'top:' + Math.round(17 * view.zoom) + 'px;';
    var h = '<tr class="r-head" style="height:' + (26 * view.zoom) + 'px">';
    h += '<th class="gut-h" style="' + abcOff + '">#</th>';
    vc.forEach(function (ci) {
      var c = COLS[ci];
      var locked = doc.adminCols && doc.adminCols[c.k];
      var hd = hdr(c);
      h += '<th class="' + (c.cls || '') + (isAdmin && locked ? ' adm-h' : '') + '" data-hc="' + ci + '" style="' + abcOff + '" title="' + esc(hd.L + (hd.sub ? ' — ' + hd.sub : '') + (locked ? ' · เฉพาะแอดมิน' : '') + ' · ดับเบิลคลิกแก้ชื่อได้') + '">' +
           '<div class="hl">' + (isAdmin && locked ? '🔒 ' : '') + esc(hd.L) + '</div>' + (hd.sub ? '<div class="hs">' + esc(hd.sub) + '</div>' : '') + (isAdmin ? '<span class="rz-c" data-rz="' + ci + '" title="ลากปรับความกว้าง · ดับเบิลคลิกพอดีข้อความ"></span>' : '') + '</th>';
    });
    h += '</tr>';
    return h;
  }

  function rowHTML(ri, vc, rowNo) {
    var row = doc.rows[ri];
    var isAdmin = (view.mode === 'admin');
    var rowLocked = doc.adminRows && doc.adminRows[row.id];
    var rh = (doc.rowH && doc.rowH[row.id]) || 18;
    var h = '<tr class="r-data' + (isAdmin && rowLocked ? ' rlocked' : '') + '" data-r="' + ri + '" style="height:' + Math.round(rh * view.zoom) + 'px">';
    h += '<td class="gut' + (isAdmin && rowLocked ? ' glock' : '') + '" data-gr="' + ri + '" title="' + (isAdmin && rowLocked ? 'แถวนี้เห็นเฉพาะแอดมิน' : 'คลิกเลือกทั้งแถว · ลากขอบล่างปรับความสูง') + '">' + (isAdmin && rowLocked ? '🔒' : rowNo) + (isAdmin ? '<span class="rz-r" data-rzr="' + ri + '"></span>' : '') + '</td>';
    for (var vi = 0; vi < vc.length; vi++) {
      var ci = vc[vi], col = COLS[ci];
      if (cover[ri + ':' + ci]) continue;   // ถูกคลุมโดยช่องผสาน
      if (col.k === 'size') {
        if (visLeader(ri) !== ri) continue; // merged
        var span = visSpan(ri);
        var adm = isAdmin && (rowLocked || (doc.adminCols && doc.adminCols[col.k]));
        var sfill = doc.colors && doc.colors[ri + ':size'];
        var sfc = doc.fontColors && doc.fontColors[ri + ':size'];
        h += '<td class="cell c-size' + (adm ? ' adm' : '') + '" data-r="' + ri + '" data-c="' + ci + '" rowspan="' + span + '"' + (sfill ? ' style="background:#' + sfill + '"' : '') + '>' +
             '<div class="sz-main"' + (sfc ? ' style="color:#' + sfc + '"' : '') + '>' + esc(row.size) + '</div>' +
             (row.diameter ? '<div class="sz-dia">' + esc(row.diameter) + '</div>' : '') + '</td>';
        continue;
      }
      h += tdHTML(ri, ci, row, col);
    }
    h += '</tr>';
    return h;
  }

  function tdHTML(ri, ci, row, col) {
    var disp = cellDisplay(ri, ci);
    var cls = 'cell ' + (col.cls || '');
    if (!col.ed) cls += ' ro';
    if (col.t === 'cipher') cls += ' ciph';
    if (view.mode === 'admin' && ((doc.adminRows && doc.adminRows[row.id]) || (doc.adminCols && doc.adminCols[col.k]))) cls += ' adm';
    var styles = '';
    // user fill override
    var fkey = ri + ':' + col.k, ufill = doc.colors && doc.colors[fkey];
    if (ufill) styles += 'background:#' + ufill + ';';
    else if (col.k === 'brand' && row.fill) styles += 'background:#' + row.fill + ';';
    // text colors (faithful)
    if (col.k === 'brand' && row.brandColor) styles += 'color:#' + row.brandColor + ';';
    if (col.k === 'model') styles += 'color:#0000FF;';
    if (col.k === 'warranty' && row.warrantyColor) styles += 'color:#' + row.warrantyColor + ';';
    if (col.k === 'retail') styles += 'color:#C00000;font-weight:700;';
    if (col.k === 'cost') styles += 'font-weight:700;';
    if (col.t === 'calc') { var n = num(XLS.compute(col, row)); if (n < 0) styles += 'color:#C00000;'; }
    // user font-color override (wins over defaults)
    var ufc = doc.fontColors && doc.fontColors[fkey];
    if (ufc) styles += 'color:#' + ufc + ';';
    // user font-style override (หนา/เอียง/ขีดเส้นใต้/ขนาด)
    var ufs = doc.fontStyles && doc.fontStyles[fkey];
    if (ufs) {
      if (ufs.b) styles += 'font-weight:700;';
      if (ufs.i) styles += 'font-style:italic;';
      if (ufs.u) styles += 'text-decoration:underline;';
      if (ufs.sz) styles += 'font-size:' + (ufs.sz * view.zoom) + 'px;';
    }
    // user merge (anchor cell spans)
    var spanAttr = '';
    var mg = doc.merges && doc.merges[ri + ':' + ci];
    if (mg) {
      var mrs = 0, mcs = 0, mr2 = Math.min(ri + mg.rs, doc.rows.length), mc2 = Math.min(ci + mg.cs, COLS.length);
      for (var mr = ri; mr < mr2; mr++) if (!isRowHidden(mr)) mrs++;
      for (var mc = ci; mc < mc2; mc++) if (!isColHidden(mc)) mcs++;
      spanAttr = ' rowspan="' + Math.max(1, mrs) + '" colspan="' + Math.max(1, mcs) + '"';
      cls += ' mgd';
    }
    return '<td class="' + cls + '"' + spanAttr + ' data-r="' + ri + '" data-c="' + ci + '"' + (styles ? ' style="' + styles + '"' : '') + '>' +
           '<span class="cv">' + esc(disp) + '</span></td>';
  }

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  // ---------- selection ----------
  function cellEl(r, c) { return rootEl.querySelector('td[data-r="' + r + '"][data-c="' + c + '"]'); }

  function normSize(r, c) { // map size column to group leader
    if (COLS[c].k === 'size') return groupLeader(r);
    return r;
  }

  function paintSelection() {
    rootEl.querySelectorAll('.cell.sel, .cell.active').forEach(function (e) { e.classList.remove('sel', 'active'); });
    rootEl.querySelectorAll('th.abc.on, td.gut.on').forEach(function (e) { e.classList.remove('on'); });
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    // ไฮไลต์หัวคอลัมน์ A-B-C และเลขแถว ตามช่วงที่เลือก (เหมือน Excel)
    for (var cc = c1; cc <= c2; cc++) {
      var ath = rootEl.querySelector('th.abc[data-hc="' + cc + '"]');
      if (ath) ath.classList.add('on');
    }
    for (var rr2 = r1; rr2 <= r2; rr2++) {
      var gtd = rootEl.querySelector('td.gut[data-gr="' + rr2 + '"]');
      if (gtd) gtd.classList.add('on');
    }
    var maxR = 0, maxB = 0;
    for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) {
      var p = anchorOf(r, c); var el = cellEl(p[0], p[1]);
      if (el) {
        el.classList.add('sel');
        var rgt = el.offsetLeft + el.offsetWidth, bot = el.offsetTop + el.offsetHeight;
        if (rgt > maxR) maxR = rgt;
        if (bot > maxB) maxB = bot;
      }
    }
    var ap = anchorOf(sel.r, sel.c);
    var ae = cellEl(ap[0], ap[1]);
    if (ae) { ae.classList.add('active'); }
    if (fhEl) {   // จุดลากเติม (fill handle) มุมขวาล่างของช่วงที่เลือก
      if (view.mode === 'admin' && maxR && !editing) {
        fhEl.style.display = 'block';
        fhEl.style.left = (maxR - 5) + 'px';
        fhEl.style.top = (maxB - 5) + 'px';
      } else fhEl.style.display = 'none';
    }
    updateStatus();
  }

  function setActive(r, c, keepAnchor) {
    r = Math.max(0, Math.min(doc.rows.length - 1, r));
    c = Math.max(0, Math.min(COLS.length - 1, c));
    var cv = cover[normSize(r, c) + ':' + c];
    if (cv && !keepAnchor) { r = cv[0]; c = cv[1]; }
    sel.r = r; sel.c = c;
    if (!keepAnchor) { sel.ar = r; sel.ac = c; }
    paintSelection();
    var el = cellEl(normSize(r, c), c);
    if (el && el.scrollIntoView) {
      var rect = el.getBoundingClientRect(), pr = rootEl.getBoundingClientRect();
      if (rect.bottom > pr.bottom - 4) rootEl.scrollTop += rect.bottom - pr.bottom + 24;
      if (rect.top < pr.top + 70) rootEl.scrollTop -= (pr.top + 70 - rect.top);
      if (rect.right > pr.right - 4) rootEl.scrollLeft += rect.right - pr.right + 24;
      if (rect.left < pr.left + 4) rootEl.scrollLeft -= (pr.left + 4 - rect.left);
    }
  }

  function updateStatus() {
    if (!statusEl) return;
    var col = COLS[sel.c], row = doc.rows[normSize(sel.r, sel.c)];
    var ref = String.fromCharCode(65 + sel.c) + (sel.r + 1);
    var hd = hdr(col);
    var info = hd.L + (hd.sub ? ' · ' + hd.sub : '');
    if (col.t === 'cipher') info += ' · รหัสลับอัตโนมัติ';
    else if (col.t === 'calc') info += ' · สูตรอัตโนมัติ';
    else if (!col.ed) info += ' · อ่านอย่างเดียว';
    statusEl.innerHTML = '<b>' + esc(ref) + '</b> &nbsp; ' + esc(info) +
      ' &nbsp;|&nbsp; ' + esc(row ? (row.brand + ' ' + row.model) : '') +
      ' &nbsp;|&nbsp; ' + doc.rows.length + ' รายการ';
  }

  // ---------- editing ----------
  function startEdit(initial) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var r = normSize(sel.r, sel.c), c = sel.c, col = COLS[c];
    if (!col.ed) { flash(); return; }
    editing = { r:r, c:c };
    var el = cellEl(r, c); if (!el) return;
    var rect = el.getBoundingClientRect(), pr = rootEl.getBoundingClientRect();
    inputEl.style.display = 'block';
    inputEl.style.left = (el.offsetLeft) + 'px';
    inputEl.style.top = (el.offsetTop) + 'px';
    inputEl.style.width = (el.offsetWidth - 1) + 'px';
    inputEl.style.height = (el.offsetHeight - 1) + 'px';
    inputEl.style.textAlign = col.a;
    inputEl.style.fontSize = (10 * view.zoom) + 'px';
    var cur = col.k === 'size' ? (doc.rows[r].size + (doc.rows[r].diameter ? ' ' + doc.rows[r].diameter : '')) : doc.rows[r][col.k];
    inputEl.value = (initial != null) ? initial : (cur == null ? '' : cur);
    inputEl.dataset.r = r; inputEl.dataset.c = c;
    inputEl.focus();
    if (initial == null) inputEl.select();
  }

  function commitEdit(move) {
    if (!editing) return;
    var r = editing.r, c = editing.c, col = COLS[c];
    var val = inputEl.value;
    var old = (col.k === 'size') ? (doc.rows[r].size + (doc.rows[r].diameter ? ' ' + doc.rows[r].diameter : '')) : doc.rows[r][col.k];
    if (String(old) !== String(val)) {
      pushUndo();
      var fmtOv = doc.formats && doc.formats[r + ':' + col.k];
      if (fmtOv === 'txt') { /* เก็บตามที่พิมพ์ */ }
      else if (fmtOv === 'num') val = String(num(val) || (val === '' ? '' : 0));
      else if (col.t === 'int') val = String(num(val) || (val === '' ? '' : 0));
      if (col.k === 'size') { // apply to whole group — แยกส่วน "( … cm )" เป็นเส้นผ่าศูนย์กลาง (ลบ/แก้ได้ในช่องเดียว)
        var dm = val.match(/\(\s*[\d.]+\s*cm\s*\)\s*$/i);
        var dia = dm ? dm[0].trim() : '';
        var szOnly = (dm ? val.slice(0, dm.index) : val).trim();
        var g = doc.rows[r].gid;
        doc.rows.forEach(function (rw) { if (rw.gid === g) { rw.size = szOnly; rw.diameter = dia; } });
      } else {
        doc.rows[r][col.k] = val;
      }
      persist();
    }
    editing = null;
    inputEl.style.display = 'none';
    render();
    if (move === 'down') setActive(sel.r + (col.k === 'size' ? groupCount(r) : 1), sel.c);
    else if (move === 'right') setActive(sel.r, nextEditable(sel.c, 1));
    else if (move === 'up') setActive(sel.r - 1, sel.c);
    else setActive(sel.r, sel.c);
    rootEl.focus();
  }
  function cancelEdit() { editing = null; editingMeta = null; inputEl.style.display = 'none'; rootEl.focus(); }

  // ---------- band/meta text editing (หัวตาราง/แถบ section แก้ได้ทั้งหมด) ----------
  var editingMeta = null;   // { mk, sri }
  function metaValue(mk, sri) {
    if (mk === 'title') return doc.meta.titleText || ('ราคา' + doc.meta.title + ' ประจำเดือน ' + doc.meta.month + ' (ชั่วคราว)');
    if (mk === 'page') return doc.meta.pageText || ('หน้า ' + doc.meta.sheet);
    if (mk === 'cat') return doc.meta.category;
    if (mk === 'rim') return doc.rows[sri].rim;
    if (mk === 'series') return doc.rows[sri].series || '';
    if (mk === 'dealer') return doc.dealerLabel || 'Dealer (ราคาส่ง · รหัสลับ)';
    return '';
  }
  function startMetaEdit(el) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    if (editing) commitEdit();
    var mk = el.dataset.mk, sri = el.dataset.sri != null ? +el.dataset.sri : null;
    editingMeta = { mk: mk, sri: sri };
    inputEl.style.display = 'block';
    inputEl.style.left = el.offsetLeft + 'px';
    inputEl.style.top = el.offsetTop + 'px';
    inputEl.style.width = (el.offsetWidth - 1) + 'px';
    inputEl.style.height = (el.offsetHeight - 1) + 'px';
    inputEl.style.textAlign = 'center';
    inputEl.style.fontSize = Math.round(13 * view.zoom) + 'px';
    inputEl.value = metaValue(mk, sri);
    inputEl.focus(); inputEl.select();
  }
  function commitMetaEdit() {
    if (!editingMeta) return;
    var mk = editingMeta.mk, sri = editingMeta.sri, val = inputEl.value;
    if (String(metaValue(mk, sri)) !== String(val)) {
      pushUndo();
      if (mk === 'title') doc.meta.titleText = val;
      else if (mk === 'page') doc.meta.pageText = val;
      else if (mk === 'cat') doc.meta.category = val;
      else if (mk === 'dealer') doc.dealerLabel = val;
      else if (mk === 'rim' || mk === 'series') {
        var old = doc.rows[sri].rim;
        for (var i = sri; i < doc.rows.length && doc.rows[i].rim === old; i++) {
          if (mk === 'rim') doc.rows[i].rim = val; else doc.rows[i].series = val;
        }
      }
      persist();
    }
    editingMeta = null;
    inputEl.style.display = 'none';
    render();
    rootEl.focus();
  }

  function nextEditable(c, dir) {
    var n = c + dir;
    while (n >= 0 && n < COLS.length && !COLS[n].ed) n += dir;
    if (n < 0 || n >= COLS.length) return c;
    return n;
  }

  function flash() { var el = cellEl(normSize(sel.r, sel.c), sel.c); if (el) { el.classList.add('flash'); setTimeout(function () { el.classList.remove('flash'); }, 180); } }

  // ---------- clipboard ----------
  function doCopy(cut) {
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    var vals = [], tsv = [];
    for (var r = r1; r <= r2; r++) {
      var rowv = [], line = [];
      for (var c = c1; c <= c2; c++) {
        var rr = normSize(r, c), col = COLS[c];
        var raw = (col.t === 'calc' || col.t === 'cipher') ? XLS.compute(col, doc.rows[rr]) : (col.k === 'size' ? doc.rows[rr].size : doc.rows[rr][col.k]);
        rowv.push(raw == null ? '' : String(raw)); line.push(raw == null ? '' : String(raw));
      }
      vals.push(rowv); tsv.push(line.join('\t'));
    }
    clip = { vals: vals };
    try { navigator.clipboard && navigator.clipboard.writeText(tsv.join('\n')); } catch (e) {}
    if (cut) doDelete();
    toast(cut ? 'ตัดแล้ว' : 'คัดลอกแล้ว ' + vals.length + '×' + vals[0].length);
  }
  function doPaste() {
    if (!clip) return;
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    pushUndo();
    var sr = Math.min(sel.r, sel.ar), sc = Math.min(sel.c, sel.ac);
    for (var i = 0; i < clip.vals.length; i++) {
      for (var j = 0; j < clip.vals[i].length; j++) {
        var r = sr + i, c = sc + j;
        if (r >= doc.rows.length || c >= COLS.length) continue;
        var col = COLS[c]; if (!col.ed) continue;
        var rr = normSize(r, c), v = clip.vals[i][j];
        if (col.t === 'int') v = String(num(v) || (v === '' ? '' : 0));
        if (col.k === 'size') { var g = doc.rows[rr].gid; doc.rows.forEach(function (rw) { if (rw.gid === g) rw.size = v; }); }
        else doc.rows[rr][col.k] = v;
      }
    }
    persist(); render(); paintSelection(); toast('วางแล้ว');
  }
  function doDelete() {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    pushUndo();
    for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) {
      var col = COLS[c]; if (!col.ed) continue; var rr = normSize(r, c);
      if (col.k === 'size') { var g = doc.rows[rr].gid; doc.rows.forEach(function (rw) { if (rw.gid === g) rw.size = ''; }); }
      else doc.rows[rr][col.k] = '';
    }
    persist(); render();
  }

  // ---------- undo/redo ----------
  function undo() { if (!undoStack.length) return; redoStack.push(snapshot()); restore(undoStack.pop()); persist(); render(); toast('ย้อนกลับ'); }
  function redo() { if (!redoStack.length) return; undoStack.push(snapshot()); restore(redoStack.pop()); persist(); render(); toast('ทำซ้ำ'); }

  // ---------- row ops ----------
  function addRow() {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    pushUndo();
    var ri = normSize(sel.r, sel.c), src = doc.rows[ri];
    var nr = { id:'r' + Date.now(), rim:src.rim, series:src.series, size:src.size, gid:src.gid,
      ply:src.ply, brand:'', brandColor:null, model:'', dot:src.dot, side:src.side,
      cost:'', retail:'', sFlag:'-', dt:'-', warranty:'', warrantyColor:null,
      priceB:'', priceA:'', priceS:'', note:'', diameter:'', fill:null };
    doc.rows.splice(ri + 1, 0, nr);
    persist(); render(); setActive(sel.r + 1, COLKEYIDX('brand')); toast('เพิ่มแถวใหม่');
  }
  function deleteRows() {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    if (r2 - r1 + 1 >= doc.rows.length) { toast('ลบทั้งหมดไม่ได้'); return; }
    pushUndo();
    doc.rows.splice(r1, r2 - r1 + 1);
    persist(); render(); setActive(Math.min(r1, doc.rows.length - 1), sel.c); toast('ลบแล้ว');
  }
  function moveRow(dir) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var ri = normSize(sel.r, sel.c), ni = ri + dir;
    if (ni < 0 || ni >= doc.rows.length) return;
    pushUndo();
    var tmp = doc.rows[ri]; doc.rows[ri] = doc.rows[ni]; doc.rows[ni] = tmp;
    // keep gid continuity to the destination neighbourhood
    doc.rows[ri].gid = doc.rows[ni].gid; // moved-away keeps local
    persist(); render(); setActive(sel.r + dir, sel.c);
  }
  function COLKEYIDX(k) { return XLS.COLKEY[k].idx; }

  // ---------- fill / font color ----------
  function applyFill(hex) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    pushUndo();
    doc.colors = doc.colors || {};
    for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) {
      var rr = normSize(r, c), key = rr + ':' + COLS[c].k;
      if (hex) doc.colors[key] = hex; else delete doc.colors[key];
    }
    persist(); render(); paintSelection();
  }

  function applyFontColor(hex) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    pushUndo();
    doc.fontColors = doc.fontColors || {};
    for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) {
      var rr = normSize(r, c), key = rr + ':' + COLS[c].k;
      if (hex) doc.fontColors[key] = hex; else delete doc.fontColors[key];
    }
    persist(); render(); paintSelection();
  }

  // ---------- secret toggle / zoom / view mode ----------
  function toggleSecret() { view.secret = !view.secret; render(); paintSelection(); return view.secret; }
  function setZoom(z) { view.zoom = Math.max(0.6, Math.min(1.8, z)); render(); paintSelection(); }
  function setMode(m) {
    if (editing) cancelEdit();
    view.mode = (m === 'user') ? 'user' : 'admin';
    if (view.mode === 'user') {
      if (isColHidden(sel.c)) { sel.c = stepCol(sel.c, 1) === sel.c ? stepCol(sel.c, -1) : stepCol(sel.c, 1); sel.ac = sel.c; }
      if (isRowHidden(sel.r)) { sel.r = stepRow(sel.r, 1) === sel.r ? stepRow(sel.r, -1) : stepRow(sel.r, 1); sel.ar = sel.r; }
    }
    render();
    return view.mode;
  }

  // ---------- admin-only marking ----------
  function toggleLockRows() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    doc.adminRows = doc.adminRows || {};
    var all = true;
    for (var r = r1; r <= r2; r++) if (!doc.adminRows[doc.rows[r].id]) { all = false; break; }
    for (var r2i = r1; r2i <= r2; r2i++) {
      var id = doc.rows[r2i].id;
      if (all) delete doc.adminRows[id]; else doc.adminRows[id] = 1;
    }
    persist(); render();
    toast(all ? 'ยกเลิกซ่อนแถว — ผู้ใช้เห็นแล้ว' : '🔒 ซ่อนแถวจากผู้ใช้แล้ว (เฉพาะแอดมิน)');
  }
  function toggleLockCols() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    doc.adminCols = doc.adminCols || {};
    var all = true;
    for (var c = c1; c <= c2; c++) if (!doc.adminCols[COLS[c].k]) { all = false; break; }
    for (var ci = c1; ci <= c2; ci++) {
      var k = COLS[ci].k;
      if (all) delete doc.adminCols[k]; else doc.adminCols[k] = 1;
    }
    persist(); render();
    toast(all ? 'ยกเลิกซ่อนคอลัมน์ — ผู้ใช้เห็นแล้ว' : '🔒 ซ่อนคอลัมน์จากผู้ใช้แล้ว (เฉพาะแอดมิน)');
  }

  // ---------- merge cells ----------
  function hasMergeIn(r1, r2, c1, c2) {
    var m = doc.merges || {}, ks = Object.keys(m);
    for (var i = 0; i < ks.length; i++) {
      var p = ks[i].split(':'), ar = +p[0], ac = +p[1], g = m[ks[i]];
      if (ar <= r2 && ar + g.rs - 1 >= r1 && ac <= c2 && ac + g.cs - 1 >= c1) return true;
    }
    return false;
  }
  function toggleMerge() {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    doc.merges = doc.merges || {};
    var hit = [];
    Object.keys(doc.merges).forEach(function (k) {
      var p = k.split(':'), ar = +p[0], ac = +p[1], m = doc.merges[k];
      if (ar <= r2 && ar + m.rs - 1 >= r1 && ac <= c2 && ac + m.cs - 1 >= c1) hit.push(k);
    });
    if (hit.length) {   // มีช่องผสานในช่วง → ยกเลิก
      pushUndo();
      hit.forEach(function (k) { delete doc.merges[k]; });
      persist(); render(); toast('ยกเลิกผสานช่องแล้ว');
      return;
    }
    if (r1 === r2 && c1 === c2) { toast('เลือกช่วงหลายช่องก่อนผสาน'); return; }
    if (c1 === 0) { toast('ผสานรวมคอลัมน์ขนาดไม่ได้ (มีการผสานตามกลุ่มอยู่แล้ว)'); return; }
    pushUndo();
    doc.merges[r1 + ':' + c1] = { rs: r2 - r1 + 1, cs: c2 - c1 + 1 };
    persist(); render(); setActive(r1, c1); toast('ผสานช่องแล้ว — แสดงค่าของช่องบนซ้าย');
  }

  // ---------- cell format (คลิกขวา) ----------
  function setFormat(t) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    pushUndo();
    doc.formats = doc.formats || {};
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) {
      var col = COLS[c];
      if (col.t === 'calc' || col.t === 'cipher') continue;
      var key = normSize(r, c) + ':' + col.k;
      if (t === 'auto') delete doc.formats[key]; else doc.formats[key] = t;
    }
    persist(); render();
    toast(t === 'num' ? 'กำหนดเป็นตัวเลขแล้ว (มีจุลภาค)' : t === 'txt' ? 'กำหนดเป็นข้อความแล้ว' : 'คืนรูปแบบอัตโนมัติตามคอลัมน์');
  }

  // ---------- clear user styles ----------
  function clearStyles() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) {
      var key = normSize(r, c) + ':' + COLS[c].k;
      if (doc.colors) delete doc.colors[key];
      if (doc.fontColors) delete doc.fontColors[key];
    }
    persist(); render(); toast('ล้างสีแล้ว');
  }

  // ---------- size-group ops (เพิ่ม/ลบขนาดยาง) ----------
  function addSizeGroup() {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    pushUndo();
    var ri = normSize(sel.r, sel.c), src = doc.rows[ri];
    var g = src.gid, end = ri;
    while (end + 1 < doc.rows.length && doc.rows[end + 1].gid === g) end++;
    var maxg = 0; doc.rows.forEach(function (rw) { if (rw.gid > maxg) maxg = rw.gid; });
    var nr = { id:'r' + Date.now(), rim:src.rim, series:src.series, size:'ขนาดใหม่', gid:maxg + 1,
      ply:'', brand:'', brandColor:null, model:'', dot:'', side:'', cost:'', retail:'',
      sFlag:'-', dt:'-', warranty:'', warrantyColor:null, priceB:'', priceA:'', priceS:'', note:'', diameter:'', fill:null };
    doc.rows.splice(end + 1, 0, nr);
    persist(); render(); setActive(end + 1, 0);
    toast('เพิ่มขนาดยางใหม่แล้ว — กด Enter เพื่อพิมพ์ขนาด');
  }

  // ---------- เพิ่ม section ขอบใหม่ต่อท้ายชีต (ชีตต่อเนื่อง แยกเฉพาะขอบเปลี่ยน) ----------
  function addRimSection() {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    pushUndo();
    var last = doc.rows[doc.rows.length - 1];
    var maxg = 0; doc.rows.forEach(function (rw) { if (rw.gid > maxg) maxg = rw.gid; });
    // เดาชื่อขอบถัดไปจากขอบล่าสุด เช่น ขอบ 15" → ขอบ 16"
    var nm = (last.rim || '').match(/(\d+)/);
    var newRim = nm ? ('ขอบ ' + (+nm[1] + 1) + '"') : 'ขอบใหม่';
    var nr = { id:'r' + Date.now(), rim:newRim, series:last.series || '', size:'ขนาดใหม่', gid:maxg + 1,
      ply:'', brand:'', brandColor:null, model:'', dot:'', side:'', cost:'', retail:'',
      sFlag:'-', dt:'-', warranty:'', warrantyColor:null, priceB:'', priceA:'', priceS:'', note:'', diameter:'', fill:null };
    doc.rows.push(nr);
    persist(); render(); setActive(doc.rows.length - 1, 0);
    toast('เพิ่ม ' + newRim + ' ต่อท้ายแล้ว — ดับเบิ้ลคลิกชื่อขอบเพื่อแก้');
  }
  function delSizeGroup() {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var ri = normSize(sel.r, sel.c), g = doc.rows[ri].gid, sz = doc.rows[ri].size;
    var rest = doc.rows.filter(function (rw) { return rw.gid !== g; });
    if (!rest.length) { toast('ลบขนาดสุดท้ายไม่ได้'); return; }
    if (!confirm('ลบขนาด “' + sz + '” ทั้งกลุ่ม (' + (doc.rows.length - rest.length) + ' แถว)?')) return;
    pushUndo();
    doc.rows = rest;
    persist(); render(); setActive(Math.min(ri, doc.rows.length - 1), sel.c);
    toast('ลบขนาด ' + sz + ' แล้ว');
  }

  // ---------- autofit column ----------
  var measureCtx = null;
  function autofitCol(ci) {
    if (view.mode !== 'admin') return;
    if (!measureCtx) measureCtx = document.createElement('canvas').getContext('2d');
    var col = COLS[ci];
    measureCtx.font = '700 10px Arial';
    var max = measureCtx.measureText(col.L + (col.sub ? ' ' + col.sub : '')).width + 12;
    for (var r = 0; r < doc.rows.length; r++) {
      var w = measureCtx.measureText(String(cellDisplay(r, ci))).width + 10;
      if (w > max) max = w;
    }
    doc.colW = doc.colW || {};
    doc.colW[col.k] = Math.min(320, Math.max(24, Math.ceil(max)));
    persist(); render(); toast('ปรับความกว้างพอดีข้อความ: ' + col.L);
  }

  // ---------- font style (หนา/เอียง/ขีดเส้นใต้/ขนาด) ----------
  function applyFontStyle(prop, val) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    pushUndo();
    doc.fontStyles = doc.fontStyles || {};
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    if (prop !== 'sz') {   // สลับแบบ Excel: ถ้าทุกช่องเป็นอยู่แล้ว → เอาออก
      var all = true;
      outer: for (var rA = r1; rA <= r2; rA++) for (var cA = c1; cA <= c2; cA++) {
        var stA = doc.fontStyles[normSize(rA, cA) + ':' + COLS[cA].k];
        if (!stA || !stA[prop]) { all = false; break outer; }
      }
      val = all ? 0 : 1;
    }
    for (var r = r1; r <= r2; r++) for (var c = c1; c <= c2; c++) {
      var key = normSize(r, c) + ':' + COLS[c].k;
      var st = doc.fontStyles[key] || {};
      if (val) st[prop] = val; else delete st[prop];
      if (Object.keys(st).length) doc.fontStyles[key] = st; else delete doc.fontStyles[key];
    }
    persist(); render(); paintSelection();
    toast(prop === 'sz' ? 'ขนาดตัวอักษร ' + val + ' พอยนต์' : (val ? 'ใส่' : 'ยกเลิก') + (prop === 'b' ? 'ตัวหนา' : prop === 'i' ? 'ตัวเอียง' : 'ขีดเส้นใต้'));
  }

  // ---------- toast ----------
  var toastT;
  function toast(msg) {
    var t = document.getElementById('toast'); if (!t) return;
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastT); toastT = setTimeout(function () { t.classList.remove('show'); }, 1400);
  }

  // ---------- keyboard ----------
  function onKey(e) {
    if (editingHdr != null) {
      if (e.key === 'Enter') { e.preventDefault(); commitHeaderEdit(); }
      else if (e.key === 'Escape') { e.preventDefault(); editingHdr = null; inputEl.style.display = 'none'; rootEl.focus(); }
      return;
    }
    if (editingMeta) {
      if (e.key === 'Enter') { e.preventDefault(); commitMetaEdit(); }
      else if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); render(); }
      return;
    }
    if (editing) {
      if (e.key === 'Enter') { e.preventDefault(); commitEdit(e.shiftKey ? 'up' : 'down'); }
      else if (e.key === 'Tab') { e.preventDefault(); commitEdit('right'); }
      else if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
      return;
    }
    var k = e.key, meta = e.ctrlKey || e.metaKey;
    if (meta) {
      if (k === 'c' || k === 'C') { e.preventDefault(); doCopy(false); return; }
      if (k === 'x' || k === 'X') { e.preventDefault(); doCopy(true); return; }
      if (k === 'v' || k === 'V') { e.preventDefault(); doPaste(); return; }
      if (k === 'z' || k === 'Z') { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
      if (k === 'y' || k === 'Y') { e.preventDefault(); redo(); return; }
      return;
    }
    if (k === 'ArrowDown') { e.preventDefault(); setActive(stepRow(sel.r, 1), sel.c, e.shiftKey); }
    else if (k === 'ArrowUp') { e.preventDefault(); setActive(stepRow(sel.r, -1), sel.c, e.shiftKey); }
    else if (k === 'ArrowLeft') { e.preventDefault(); setActive(sel.r, stepCol(sel.c, -1), e.shiftKey); }
    else if (k === 'ArrowRight') { e.preventDefault(); setActive(sel.r, stepCol(sel.c, 1), e.shiftKey); }
    else if (k === 'Tab') { e.preventDefault(); setActive(sel.r, stepCol(sel.c, e.shiftKey ? -1 : 1)); }
    else if (k === 'Enter') { e.preventDefault(); startEdit(null); }
    else if (k === 'F2') { e.preventDefault(); startEdit(null); }
    else if (k === 'Delete' || k === 'Backspace') { e.preventDefault(); doDelete(); }
    else if (k === 'Home') { e.preventDefault(); setActive(sel.r, 0); }
    else if (k === 'End') { e.preventDefault(); setActive(sel.r, COLS.length - 1); }
    else if (k.length === 1 && !e.altKey) { e.preventDefault(); startEdit(k); }
  }

  // ---------- mouse ----------
  var dragging = false, dragKind = null;   // 'cell' | 'gut' | 'head'
  function onMouseDown(e) {
    hideCtx();
    // ลากปรับความกว้างคอลัมน์
    if (e.target.classList && e.target.classList.contains('rz-c')) {
      var rci = +e.target.dataset.rz, ck = COLS[rci].k;
      resize = { kind:'col', ci:rci, startX:e.clientX, startW:(doc.colW && doc.colW[ck]) || COLS[rci].w };
      document.body.classList.add('rz-col');
      e.preventDefault(); e.stopPropagation(); return;
    }
    // ลากปรับความสูงแถว
    if (e.target.classList && e.target.classList.contains('rz-r')) {
      var rri = +e.target.dataset.rzr, rid = doc.rows[rri].id;
      resize = { kind:'row', ri:rri, id:rid, startY:e.clientY, startH:(doc.rowH && doc.rowH[rid]) || 18 };
      document.body.classList.add('rz-row');
      e.preventDefault(); e.stopPropagation(); return;
    }
    // จุดลากเติม (fill handle)
    if (e.target === fhEl) {
      filling = { r1:Math.min(sel.r, sel.ar), r2:Math.max(sel.r, sel.ar), c1:Math.min(sel.c, sel.ac), c2:Math.max(sel.c, sel.ac), dir:null, ext:0 };
      e.preventDefault(); return;
    }
    var gut = e.target.closest('td.gut');
    if (gut && gut.dataset.gr != null) {           // ลากที่เลขแถว = เลือกทั้งแถว
      var gr = +gut.dataset.gr;
      if (editing) commitEdit();
      if (e.shiftKey) { sel.r = gr; }
      else { sel.ar = gr; sel.r = gr; }
      sel.ac = 0; sel.c = COLS.length - 1;
      dragging = true; dragKind = 'gut';
      paintSelection(); rootEl.focus();
      e.preventDefault();
      return;
    }
    var th = e.target.closest('th[data-hc]');
    if (th) {                                       // ลากที่หัวคอลัมน์ = เลือกทั้งคอลัมน์
      var hc = +th.dataset.hc;
      if (editing) commitEdit();
      if (e.shiftKey) { sel.c = hc; }
      else { sel.ac = hc; sel.c = hc; }
      sel.ar = 0; sel.r = doc.rows.length - 1;
      dragging = true; dragKind = 'head';
      paintSelection(); rootEl.focus();
      e.preventDefault();
      return;
    }
    var td = e.target.closest('td.cell'); if (!td) return;
    var r = +td.dataset.r, c = +td.dataset.c;
    if (editing) commitEdit();
    setActive(r, c, e.shiftKey);
    dragging = true; dragKind = 'cell';
    rootEl.focus();
  }
  function onMouseOver(e) {
    if (filling) {   // พรีวิวลากเติม
      var ftd = e.target.closest('td.cell');
      if (ftd) previewFill(+ftd.dataset.r, +ftd.dataset.c);
      return;
    }
    if (!dragging) return;
    if (dragKind === 'gut') {
      var g = e.target.closest('td.gut');
      if (g && g.dataset.gr != null) { sel.r = +g.dataset.gr; paintSelection(); }
      return;
    }
    if (dragKind === 'head') {
      var t = e.target.closest('th[data-hc]');
      if (t) { sel.c = +t.dataset.hc; paintSelection(); }
      return;
    }
    var td = e.target.closest('td.cell'); if (!td) return;
    setActive(+td.dataset.r, +td.dataset.c, true);
  }
  function onMouseUp() {
    if (resize) {
      if (resize.cur) {
        if (resize.kind === 'col') { doc.colW = doc.colW || {}; doc.colW[COLS[resize.ci].k] = Math.round(resize.cur); }
        else { doc.rowH = doc.rowH || {}; doc.rowH[resize.id] = Math.round(resize.cur); }
        persist(); render();
      }
      document.body.classList.remove('rz-col', 'rz-row');
      resize = null;
      return;
    }
    if (filling) { applyFillDrag(); return; }
    dragging = false; dragKind = null;
  }

  // ---------- resize live-preview (document-level) ----------
  function onDocMove(e) {
    if (!resize) return;
    if (resize.kind === 'col') {
      resize.cur = Math.max(22, resize.startW + (e.clientX - resize.startX) / view.zoom);
      var colEl = rootEl.querySelector('col[data-ci="' + resize.ci + '"]');
      if (colEl) colEl.style.width = Math.round(resize.cur * view.zoom) + 'px';
    } else {
      resize.cur = Math.max(14, resize.startH + (e.clientY - resize.startY) / view.zoom);
      var trEl = rootEl.querySelector('tr[data-r="' + resize.ri + '"]');
      if (trEl) trEl.style.height = Math.round(resize.cur * view.zoom) + 'px';
    }
  }

  // ---------- fill handle drag ----------
  function previewFill(tr, tc) {
    var f = filling;
    rootEl.querySelectorAll('.fillprev').forEach(function (el) { el.classList.remove('fillprev'); });
    var dDown = tr - f.r2, dUp = f.r1 - tr, dRight = tc - f.c2, dLeft = f.c1 - tc;
    var best = Math.max(dDown, dUp, dRight, dLeft);
    if (best <= 0) { f.dir = null; f.ext = 0; return; }
    if (best === dDown) { f.dir = 'down'; f.ext = dDown; markPrev(f.r2 + 1, f.r2 + dDown, f.c1, f.c2); }
    else if (best === dUp) { f.dir = 'up'; f.ext = dUp; markPrev(f.r1 - dUp, f.r1 - 1, f.c1, f.c2); }
    else if (best === dRight) { f.dir = 'right'; f.ext = dRight; markPrev(f.r1, f.r2, f.c2 + 1, f.c2 + dRight); }
    else { f.dir = 'left'; f.ext = dLeft; markPrev(f.r1, f.r2, f.c1 - dLeft, f.c1 - 1); }
  }
  function markPrev(r1, r2, c1, c2) {
    for (var r = Math.max(0, r1); r <= Math.min(doc.rows.length - 1, r2); r++)
      for (var c = Math.max(0, c1); c <= Math.min(COLS.length - 1, c2); c++) {
        var p = anchorOf(r, c); var el = cellEl(p[0], p[1]);
        if (el) el.classList.add('fillprev');
      }
  }
  function applyFillDrag() {
    var f = filling; filling = null;
    rootEl.querySelectorAll('.fillprev').forEach(function (el) { el.classList.remove('fillprev'); });
    if (!f || !f.dir || f.ext < 1) { paintSelection(); return; }
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    pushUndo();
    var nR = f.r2 - f.r1 + 1, nC = f.c2 - f.c1 + 1, i, r, c;
    function rawVal(rr, cc) { var col = COLS[cc]; var v = (col.t === 'calc' || col.t === 'cipher') ? XLS.compute(col, doc.rows[rr]) : doc.rows[rr][col.k]; return v == null ? '' : v; }
    function setVal(rr, cc, v) { var col = COLS[cc]; if (!col.ed || col.k === 'size') return; if (col.t === 'int') v = String(num(v) || (v === '' ? '' : 0)); doc.rows[rr][col.k] = String(v); }
    if (f.dir === 'down') {
      for (i = 1; i <= f.ext; i++) { r = f.r2 + i; if (r >= doc.rows.length) break; for (c = f.c1; c <= f.c2; c++) setVal(r, c, rawVal(f.r1 + ((i - 1) % nR), c)); }
      sel.ar = f.r1; sel.ac = f.c1; sel.r = Math.min(doc.rows.length - 1, f.r2 + f.ext); sel.c = f.c2;
    } else if (f.dir === 'up') {
      for (i = 1; i <= f.ext; i++) { r = f.r1 - i; if (r < 0) break; for (c = f.c1; c <= f.c2; c++) setVal(r, c, rawVal(f.r2 - ((i - 1) % nR), c)); }
      sel.ar = Math.max(0, f.r1 - f.ext); sel.ac = f.c1; sel.r = f.r2; sel.c = f.c2;
    } else if (f.dir === 'right') {
      for (i = 1; i <= f.ext; i++) { c = f.c2 + i; if (c >= COLS.length) break; for (r = f.r1; r <= f.r2; r++) setVal(r, c, rawVal(r, f.c1 + ((i - 1) % nC))); }
      sel.ar = f.r1; sel.ac = f.c1; sel.r = f.r2; sel.c = Math.min(COLS.length - 1, f.c2 + f.ext);
    } else {
      for (i = 1; i <= f.ext; i++) { c = f.c1 - i; if (c < 0) break; for (r = f.r1; r <= f.r2; r++) setVal(r, c, rawVal(r, f.c2 - ((i - 1) % nC))); }
      sel.ar = f.r1; sel.ac = Math.max(0, f.c1 - f.ext); sel.r = f.r2; sel.c = f.c2;
    }
    persist(); render(); toast('เติมข้อมูลแล้ว (ลากเติมแบบ Excel)');
  }

  // ---------- context menu (คลิกขวา) ----------
  function hideCtx() { if (ctxEl) ctxEl.style.display = 'none'; }
  function onCtx(e) {
    var td = e.target.closest('td.cell'); if (!td) return;
    e.preventDefault();
    var r = +td.dataset.r, c = +td.dataset.c;
    var r1 = Math.min(sel.r, sel.ar), r2 = Math.max(sel.r, sel.ar);
    var c1 = Math.min(sel.c, sel.ac), c2 = Math.max(sel.c, sel.ac);
    if (!(r >= r1 && r <= r2 && c >= c1 && c <= c2)) { setActive(r, c); r1 = r2 = sel.r; c1 = c2 = sel.c; }
    var isAdmin = view.mode === 'admin';
    var fk = (doc.formats && doc.formats[normSize(sel.r, sel.c) + ':' + COLS[sel.c].k]) || 'auto';
    var merged = hasMergeIn(r1, r2, c1, c2);
    var H = '';
    function mi(act, ic, label, opts) {
      opts = opts || {};
      H += '<div class="mi' + (opts.dis ? ' dis' : '') + '" data-act="' + (opts.dis ? '' : act) + '"><span class="mic">' + ic + '</span><span>' + label + '</span>' + (opts.chk ? '<span class="chk">✓</span>' : '') + '</div>';
    }
    mi('copy', '📋', 'คัดลอก <small>Ctrl+C</small>');
    mi('cut', '✂️', 'ตัด', { dis: !isAdmin });
    mi('paste', '📌', 'วาง <small>Ctrl+V</small>', { dis: !isAdmin || !clip });
    H += '<div class="sep"></div><div class="mlbl">รูปแบบข้อมูลในช่อง</div>';
    mi('fmt-num', '🔢', 'ตัวเลข (คั่นหลักพัน)', { dis: !isAdmin, chk: fk === 'num' });
    mi('fmt-txt', '🔤', 'ข้อความ', { dis: !isAdmin, chk: fk === 'txt' });
    mi('fmt-auto', '↺', 'อัตโนมัติ (ตามคอลัมน์)', { dis: !isAdmin, chk: fk === 'auto' });
    H += '<div class="sep"></div>';
    mi('merge', merged ? '⊟' : '⊞', merged ? 'ยกเลิกผสานช่อง' : 'ผสานช่อง', { dis: !isAdmin });
    H += '<div class="sep"></div>';
    mi('addrow', '➕', 'เพิ่มรุ่น (แถวใหม่)', { dis: !isAdmin });
    mi('addsize', '➕', 'เพิ่มขนาดยางใหม่', { dis: !isAdmin });
    mi('delrow', '🗑️', 'ลบแถวที่เลือก', { dis: !isAdmin });
    H += '<div class="sep"></div>';
    mi('clearfill', '🧽', 'ล้างสีช่อง/สีอักษร', { dis: !isAdmin });
    ctxEl.innerHTML = H;
    ctxEl.style.display = 'block';
    var mw = ctxEl.offsetWidth, mh = ctxEl.offsetHeight;
    ctxEl.style.left = Math.min(e.clientX, window.innerWidth - mw - 8) + 'px';
    ctxEl.style.top = Math.min(e.clientY, window.innerHeight - mh - 8) + 'px';
  }
  function onCtxClick(e) {
    var item = e.target.closest('.mi'); if (!item || !item.dataset.act) return;
    var act = item.dataset.act;
    hideCtx();
    if (act === 'copy') doCopy(false);
    else if (act === 'cut') doCopy(true);
    else if (act === 'paste') doPaste();
    else if (act === 'fmt-num') setFormat('num');
    else if (act === 'fmt-txt') setFormat('txt');
    else if (act === 'fmt-auto') setFormat('auto');
    else if (act === 'merge') toggleMerge();
    else if (act === 'addrow') addRow();
    else if (act === 'addsize') addSizeGroup();
    else if (act === 'delrow') deleteRows();
    else if (act === 'clearfill') clearStyles();
    rootEl.focus();
  }

  function onDblClick(e) {
    if (e.target.classList && e.target.classList.contains('rz-c')) { autofitCol(+e.target.dataset.rz); return; }   // ดับเบิลคลิกขอบ = พอดีข้อความ
    if (e.target.classList && e.target.classList.contains('rz-r')) {
      var rr = +e.target.dataset.rzr;
      if (doc.rowH) delete doc.rowH[doc.rows[rr].id];
      persist(); render(); toast('คืนความสูงอัตโนมัติ'); return;
    }
    var mt = e.target.closest('td.editable-band');
    if (mt) { startMetaEdit(mt); return; }
    var hth = e.target.closest('tr.r-head th[data-hc]');
    if (hth) { startHeaderEdit(hth); return; }
    var td = e.target.closest('td.cell'); if (!td) return; setActive(+td.dataset.r, +td.dataset.c); startEdit(null);
  }

  // ---------- header label editing (ชื่อหัวคอลัมน์แก้ได้ · รูปแบบ "ชื่อ|ชื่อรอง") ----------
  var editingHdr = null;   // ci
  function startHeaderEdit(th) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    if (editing) commitEdit();
    if (editingMeta) commitMetaEdit();
    var ci = +th.dataset.hc, c = COLS[ci], hd = hdr(c);
    editingHdr = ci;
    inputEl.style.display = 'block';
    inputEl.style.left = th.offsetLeft + 'px';
    inputEl.style.top = th.offsetTop + 'px';
    inputEl.style.width = Math.max(90, th.offsetWidth - 1) + 'px';
    inputEl.style.height = (th.offsetHeight - 1) + 'px';
    inputEl.style.textAlign = 'center';
    inputEl.style.fontSize = (10 * view.zoom) + 'px';
    inputEl.value = hd.L + (hd.sub ? '|' + hd.sub : '');
    inputEl.focus(); inputEl.select();
    toast('แก้ชื่อหัวคอลัมน์ — ใช้ | คั่นชื่อบรรทัดบน|ล่าง เช่น ทุน|COST');
  }
  function commitHeaderEdit() {
    if (editingHdr == null) return;
    var ci = editingHdr, c = COLS[ci], hd = hdr(c);
    var val = inputEl.value;
    var cur = hd.L + (hd.sub ? '|' + hd.sub : '');
    if (val !== cur) {
      pushUndo();
      doc.headerLabels = doc.headerLabels || {};
      var parts = val.split('|');
      doc.headerLabels[c.k] = { L: (parts[0] || '').trim(), sub: (parts[1] || '').trim() };
      persist();
    }
    editingHdr = null;
    inputEl.style.display = 'none';
    render();
    rootEl.focus();
  }

  // ---------- public init ----------
  function init(opts) {
    rootEl = opts.root; statusEl = opts.status;
    // load current or seed
    var saved = XLS.store.loadCurrent();
    if (saved && saved.rows && saved.rows.length) doc = saved;
    else doc = seedDoc();
    if (!doc.colors) doc.colors = {};
    ensureAdminDefaults(doc);
    // input overlay (created before render; render re-appends it)
    inputEl = document.createElement('input');
    inputEl.className = 'cell-input'; inputEl.style.display = 'none';
    // fill handle overlay
    fhEl = document.createElement('div');
    fhEl.className = 'fill-handle';
    fhEl.title = 'ลากเพื่อคัดลอกไปตามแถวหรือคอลัมน์';
    // context menu
    ctxEl = document.createElement('div');
    ctxEl.id = 'ctxMenu';
    document.body.appendChild(ctxEl);
    ctxEl.addEventListener('mousedown', function (e) { e.stopPropagation(); });
    ctxEl.addEventListener('click', onCtxClick);
    render();
    setActive(0, COLKEYIDX('brand'));
    markClean();

    rootEl.tabIndex = 0;
    rootEl.addEventListener('keydown', onKey);
    rootEl.addEventListener('mousedown', onMouseDown);
    rootEl.addEventListener('mouseover', onMouseOver);
    document.addEventListener('mouseup', onMouseUp);
    rootEl.addEventListener('dblclick', onDblClick);
    rootEl.addEventListener('contextmenu', onCtx);
    rootEl.addEventListener('scroll', hideCtx);
    document.addEventListener('mousemove', onDocMove);
    document.addEventListener('mousedown', function (e) { if (ctxEl && !ctxEl.contains(e.target) && !rootEl.contains(e.target)) hideCtx(); });
    inputEl.addEventListener('blur', function () { if (editingHdr != null) commitHeaderEdit(); else if (editingMeta) commitMetaEdit(); else if (editing) commitEdit(); });
    rootEl.focus();
  }

  function seedDoc() {
    var src = window.PICKUP01;
    var d = { meta: JSON.parse(JSON.stringify(src.meta)), rows: JSON.parse(JSON.stringify(src.rows)), colors: {}, name: 'ราคายาง ปิคอัพ-01' };
    ensureAdminDefaults(d);
    return d;
  }
  function ensureAdminDefaults(d) {
    if (!d.adminRows) d.adminRows = {};
    if (!d.fontColors) d.fontColors = {};
    if (!d.fontStyles) d.fontStyles = {};
    if (!d.merges) d.merges = {};
    if (!d.formats) d.formats = {};
    if (!d.colW) d.colW = {};
    if (!d.rowH) d.rowH = {};
    if (!d.adminCols) {
      d.adminCols = {};
      COLS.forEach(function (c) { if (c.secret) d.adminCols[c.k] = 1; });  // ค่าเริ่มต้น: ซ่อนทุน/ราคาส่ง/ส่วนต่างจากผู้ใช้
    }
  }

  // version mgmt
  function saveAs(name) {
    var id = 'v' + Date.now();
    var meta = { id: id, name: name || ('เวอร์ชัน ' + new Date().toLocaleString('th-TH')), savedAt: Date.now() };
    XLS.store.saveVersionDoc(id, doc);
    var vs = XLS.store.loadVersions(); vs.unshift(meta); XLS.store.saveVersions(vs);
    markClean(); toast('บันทึกเป็น: ' + meta.name);
    return meta;
  }
  function saveCurrentNamed() { XLS.store.saveCurrent(doc); markClean(); toast('บันทึกแล้ว'); }
  function openVersion(id) {
    var d = XLS.store.loadVersion(id); if (!d) return;
    doc = d; if (!doc.colors) doc.colors = {}; ensureAdminDefaults(doc); undoStack.length = redoStack.length = 0;
    render(); setActive(0, COLKEYIDX('brand')); persist(); toast('เปิดเวอร์ชันแล้ว');
  }
  function newBlankFromSource() { doc = seedDoc(); undoStack.length = redoStack.length = 0; persist(); render(); setActive(0, COLKEYIDX('brand')); toast('โหลดต้นฉบับใหม่'); }
  function getDoc() { return doc; }

  window.Grid = {
    init: init, render: render, undo: undo, redo: redo, addRow: addRow, deleteRows: deleteRows,
    moveRow: moveRow, applyFill: applyFill, applyFontColor: applyFontColor, toggleSecret: toggleSecret, setZoom: setZoom,
    getZoom: function () { return view.zoom; }, copy: function () { doCopy(false); }, paste: doPaste,
    saveAs: saveAs, save: saveCurrentNamed, openVersion: openVersion, newFromSource: newBlankFromSource,
    getDoc: getDoc, isDirty: function () { return dirty; }, isSecret: function () { return view.secret; },
    setMode: setMode, getMode: function () { return view.mode; },
    toggleLockRows: toggleLockRows, toggleLockCols: toggleLockCols,
    toggleMerge: toggleMerge, setFormat: setFormat, addSizeGroup: addSizeGroup, delSizeGroup: delSizeGroup, addRimSection: addRimSection,
    autofitCol: autofitCol, clearStyles: clearStyles, applyFontStyle: applyFontStyle
  };
})();
