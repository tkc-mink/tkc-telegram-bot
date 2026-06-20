/* ============================================================
   grid2.js — render + state + edit + clipboard + undo + API
   ============================================================ */
(function () {
  var X = window.XL2;

  var sh = null;                     // sheet
  var view = { mode: 'admin', secret: false, zoom: 1 };
  var sel = { r: 0, c: 0, ar: 0, ac: 0 };
  var editing = null;                // {r,c}
  var undoStack = [], redoStack = [], clip = null;
  var rootEl, wrapEl, inputEl, fillEl, statusEl, fxEl, nameEl;
  var dirty = false;

  // ---------- helpers ----------
  function snap() { return JSON.stringify(sh); }
  function pushUndo() { undoStack.push(snap()); if (undoStack.length > 60) undoStack.shift(); redoStack.length = 0; }
  function persist() { try { X.store.saveCurrent(sh); } catch (e) {} dirty = true; }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function isAdmin() { return view.mode === 'admin'; }
  function rowVis(r) { return isAdmin() || !sh.adminRows[r]; }
  function colVis(c) { return isAdmin() || !sh.adminCols[c]; }
  function leaderOf(r, c) {
    var m = X.mergeAt(sh, r, c);
    if (!m) return { r: r, c: c, m: null };
    var lr = m.r, lc = m.c;
    if (!isAdmin()) {
      while (lr < m.r + m.rs - 1 && !rowVis(lr)) lr++;
      while (lc < m.c + m.cs - 1 && !colVis(lc)) lc++;
    }
    return { r: lr, c: lc, m: m };
  }
  function stepRow(r, dir) { var n = r + dir; while (n >= 0 && n < sh.nR && !rowVis(n)) n += dir; return (n < 0 || n >= sh.nR) ? r : n; }
  function stepCol(c, dir) { var n = c + dir; while (n >= 0 && n < sh.nC && !colVis(n)) n += dir; return (n < 0 || n >= sh.nC) ? c : n; }

  // ---------- render ----------
  function render() {
    var z = view.zoom, html = '';
    html += '<table class="xl2" style="font-size:' + (10 * z) + 'px">';
    // colgroup
    html += '<colgroup><col style="width:' + Math.round(34 * z) + 'px">';
    for (var c = 0; c < sh.nC; c++) if (colVis(c)) html += '<col style="width:' + Math.round(sh.colW[c] * z) + 'px">';
    html += '</colgroup>';
    // column letters
    html += '<tr class="hdr"><th class="corner" id="cornerAll" title="เลือกทั้งหมด"></th>';
    for (c = 0; c < sh.nC; c++) {
      if (!colVis(c)) continue;
      var lockc = sh.adminCols[c];
      html += '<th class="ch' + (isAdmin() && lockc ? ' admc' : '') + '" data-hc="' + c + '" title="' +
        (lockc ? 'คอลัมน์ ' + X.colName(c) + ' — เฉพาะแอดมิน' : 'คอลัมน์ ' + X.colName(c)) + '">' +
        (isAdmin() && lockc ? '🔒' : '') + X.colName(c) + '<span class="rz-c" data-rzc="' + c + '"></span></th>';
    }
    html += '</tr>';
    if (!isAdmin()) {
      html += '<tr class="r-uview"><td colspan="' + (visColCount() + 1) + '" class="uview-cell">👁️ มุมมองผู้ใช้ — แถว/คอลัมน์ที่ติด 🔒 ถูกซ่อน · อ่านอย่างเดียว</td></tr>';
    }
    // build skip map from merges
    var skip = {}, spanMap = {};
    sh.merges.forEach(function (m) {
      var vr = [], vc = [];
      for (var r = m.r; r < m.r + m.rs; r++) if (rowVis(r)) vr.push(r);
      for (var cc = m.c; cc < m.c + m.cs; cc++) if (colVis(cc)) vc.push(cc);
      if (!vr.length || !vc.length) return;
      var lead = vr[0] + ',' + vc[0];
      spanMap[lead] = { rs: vr.length, cs: vc.length };
      vr.forEach(function (r) { vc.forEach(function (cc) { var k = r + ',' + cc; if (k !== lead) skip[k] = 1; }); });
    });
    // rows
    for (var r = 0; r < sh.nR; r++) {
      if (!rowVis(r)) continue;
      var kind = sh.rowKind[r];
      var lockr = sh.adminRows[r];
      html += '<tr data-row="' + r + '" style="height:' + Math.round(sh.rowH[r] * z) + 'px">';
      html += '<th class="rh' + (isAdmin() && lockr ? ' admr' : '') + '" data-hr="' + r + '">' +
        (isAdmin() && lockr ? '🔒' : (r + 1)) + '<span class="rz-r" data-rzr="' + r + '"></span></th>';
      for (var cc = 0; cc < sh.nC; cc++) {
        if (!colVis(cc)) continue;
        var k = r + ',' + cc;
        if (skip[k]) continue;
        html += tdHTML(r, cc, spanMap[k], kind);
      }
      html += '</tr>';
    }
    html += '</table>';
    rootEl.innerHTML = html;
    if (inputEl) rootEl.appendChild(inputEl);
    if (fillEl) rootEl.appendChild(fillEl);
    paintSelection();
  }
  function visColCount() { var n = 0; for (var c = 0; c < sh.nC; c++) if (colVis(c)) n++; return n; }

  function tdHTML(r, c, span, kind) {
    var cell = X.cellAt(sh, r, c) || { v: '', f: null, t: 'auto', s: {} };
    var s = cell.s || {};
    var disp;
    if (view.secret && sh.secretCols[c] && kind === 'data') disp = '•••';
    else disp = X.display(sh, r, c);
    var st = '';
    if (s.bg) st += 'background:#' + s.bg + ';';
    if (s.fc) st += 'color:#' + s.fc + ';';
    if (s.b) st += 'font-weight:700;';
    if (s.i) st += 'font-style:italic;';
    if (s.fs) st += 'font-size:' + (s.fs * view.zoom) + 'px;';
    st += 'text-align:' + (s.al || (X.isNumeric(disp) ? 'right' : 'left')) + ';';
    // ค่าติดลบ → แดง (เฉพาะช่องสูตร +/-)
    if (cell.f && !s.fc) { var nv = X.evalCell(sh, r, c); if (typeof nv === 'number' && nv < 0) st += 'color:#C00000;'; }
    var cls = 'cell k-' + kind;
    if (cell.f) cls += ' hasf';
    if (isAdmin() && (sh.adminRows[r] || sh.adminCols[c]) && kind === 'data') cls += ' adm';
    var spanAttr = span ? ' rowspan="' + span.rs + '" colspan="' + span.cs + '"' : '';
    return '<td class="' + cls + '" data-r="' + r + '" data-c="' + c + '"' + spanAttr + ' style="' + st + '">' +
      '<span class="cv">' + esc(disp).replace(/\n/g, '<br>') + '</span></td>';
  }

  // ---------- selection ----------
  function cellEl(r, c) { return rootEl.querySelector('td[data-r="' + r + '"][data-c="' + c + '"]'); }
  function range() {
    return { r1: Math.min(sel.r, sel.ar), r2: Math.max(sel.r, sel.ar), c1: Math.min(sel.c, sel.ac), c2: Math.max(sel.c, sel.ac) };
  }
  function paintSelection() {
    rootEl.querySelectorAll('.cell.sel,.cell.active').forEach(function (e) { e.classList.remove('sel', 'active'); });
    rootEl.querySelectorAll('.ch.hl,.rh.hl').forEach(function (e) { e.classList.remove('hl'); });
    var rg = range();
    rootEl.querySelectorAll('td.cell').forEach(function (td) {
      var r = +td.dataset.r, c = +td.dataset.c;
      var rs = td.rowSpan || 1, cs = td.colSpan || 1;
      if (r <= rg.r2 && rg.r1 <= r + rs - 1 && c <= rg.c2 && rg.c1 <= c + cs - 1) td.classList.add('sel');
    });
    var L = leaderOf(sel.r, sel.c);
    var ae = cellEl(L.r, L.c);
    if (ae) ae.classList.add('active');
    for (var c = rg.c1; c <= rg.c2; c++) { var th = rootEl.querySelector('th.ch[data-hc="' + c + '"]'); if (th) th.classList.add('hl'); }
    for (var r = rg.r1; r <= rg.r2; r++) { var rh = rootEl.querySelector('th.rh[data-hr="' + r + '"]'); if (rh) rh.classList.add('hl'); }
    positionFill();
    updateBars();
  }
  function positionFill() {
    if (!fillEl) return;
    if (!isAdmin()) { fillEl.style.display = 'none'; return; }
    var rg = range();
    var L = leaderOf(rg.r2, rg.c2);
    var el = cellEl(L.r, L.c) || cellEl(rg.r2, rg.c2);
    if (!el) { fillEl.style.display = 'none'; return; }
    fillEl.style.display = 'block';
    fillEl.style.left = (el.offsetLeft + el.offsetWidth - 4) + 'px';
    fillEl.style.top = (el.offsetTop + el.offsetHeight - 4) + 'px';
  }
  function setActive(r, c, keepAnchor) {
    r = Math.max(0, Math.min(sh.nR - 1, r));
    c = Math.max(0, Math.min(sh.nC - 1, c));
    sel.r = r; sel.c = c;
    if (!keepAnchor) { sel.ar = r; sel.ac = c; }
    paintSelection();
    scrollToActive();
  }
  function scrollToActive() {
    var L = leaderOf(sel.r, sel.c), el = cellEl(L.r, L.c);
    if (!el || !wrapEl) return;
    var rect = el.getBoundingClientRect(), pr = wrapEl.getBoundingClientRect();
    if (rect.bottom > pr.bottom - 6) wrapEl.scrollTop += rect.bottom - pr.bottom + 26;
    if (rect.top < pr.top + 30) wrapEl.scrollTop -= (pr.top + 30 - rect.top);
    if (rect.right > pr.right - 6) wrapEl.scrollLeft += rect.right - pr.right + 26;
    if (rect.left < pr.left + 40) wrapEl.scrollLeft -= (pr.left + 40 - rect.left);
  }

  // ---------- bars (name box / fx / status) ----------
  function updateBars() {
    var L = leaderOf(sel.r, sel.c);
    var cell = X.cellAt(sh, L.r, L.c);
    if (nameEl) nameEl.textContent = X.refStr(L.r, L.c);
    if (fxEl && document.activeElement !== fxEl) fxEl.value = cell ? (cell.f || cell.v || '') : '';
    if (statusEl) {
      var rg = range(), nums = [], cnt = 0;
      for (var r = rg.r1; r <= rg.r2; r++) for (var c = rg.c1; c <= rg.c2; c++) {
        if (!rowVis(r) || !colVis(c)) continue;
        var v = X.evalCell(sh, r, c);
        if (v !== '' && v != null) { cnt++; if (typeof v === 'number' || X.isNumeric(v)) nums.push(X.num(v)); }
      }
      var stat = '<b>' + X.refStr(L.r, L.c) + '</b>';
      var ct = cell && cell.t !== 'auto' ? (cell.t === 'num' ? ' · ตัวเลข' : ' · ข้อความ') : '';
      stat += ct;
      if (cell && cell.f) stat += ' · สูตร';
      if (nums.length > 1) {
        var sum = nums.reduce(function (a, b) { return a + b; }, 0);
        stat += ' &nbsp;|&nbsp; ผลรวม: <b>' + sum.toLocaleString('en-US') + '</b> · ค่าเฉลี่ย: ' + (sum / nums.length).toLocaleString('en-US', { maximumFractionDigits: 1 }) + ' · จำนวน: ' + cnt;
      }
      statusEl.innerHTML = stat;
    }
  }

  // ---------- editing ----------
  function startEdit(initial, fromFx) {
    if (!isAdmin()) { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var L = leaderOf(sel.r, sel.c);
    editing = { r: L.r, c: L.c };
    var el = cellEl(L.r, L.c); if (!el) return;
    var cell = X.cellAt(sh, L.r, L.c);
    inputEl.style.display = 'block';
    inputEl.style.left = el.offsetLeft + 'px';
    inputEl.style.top = el.offsetTop + 'px';
    inputEl.style.width = Math.max(el.offsetWidth, 60) + 'px';
    inputEl.style.height = el.offsetHeight + 'px';
    inputEl.style.fontSize = (10 * view.zoom) + 'px';
    inputEl.value = (initial != null) ? initial : (cell ? (cell.f || cell.v || '') : '');
    if (!fromFx) { inputEl.focus(); if (initial == null) inputEl.select(); }
  }
  function commitEdit(move) {
    if (!editing) return;
    var r = editing.r, c = editing.c;
    var val = inputEl.value;
    var cell = X.ensure(sh, r, c);
    var oldF = cell.f, oldV = cell.v;
    var nf = null, nv = '';
    if (/^=/.test(val.trim())) nf = val.trim();
    else nv = val;
    if (nf !== oldF || nv !== oldV) {
      pushUndo();
      cell.f = nf; cell.v = nv;
      persist();
    }
    editing = null;
    inputEl.style.display = 'none';
    render();
    if (move === 'down') setActive(stepRow(sel.r, 1), sel.c);
    else if (move === 'up') setActive(stepRow(sel.r, -1), sel.c);
    else if (move === 'right') setActive(sel.r, stepCol(sel.c, 1));
    else if (move === 'left') setActive(sel.r, stepCol(sel.c, -1));
    else setActive(sel.r, sel.c);
    rootEl.focus();
  }
  function cancelEdit() { editing = null; inputEl.style.display = 'none'; rootEl.focus(); }
  function isEditing() { return !!editing; }

  // ---------- clipboard ----------
  function doCopy(cut) {
    var rg = range(), vals = [], tsv = [];
    for (var r = rg.r1; r <= rg.r2; r++) {
      var rowv = [], line = [];
      for (var c = rg.c1; c <= rg.c2; c++) {
        var cell = X.cellAt(sh, r, c);
        rowv.push(cell ? { v: cell.v, f: cell.f, t: cell.t } : { v: '', f: null, t: 'auto' });
        line.push(X.display(sh, r, c));
      }
      vals.push(rowv); tsv.push(line.join('\t'));
    }
    clip = { vals: vals, r: rg.r1, c: rg.c1 };
    try { navigator.clipboard && navigator.clipboard.writeText(tsv.join('\n')); } catch (e) {}
    if (cut) doClear();
    toast(cut ? 'ตัดแล้ว' : 'คัดลอกแล้ว');
  }
  function doPaste() {
    if (!clip || !isAdmin()) return;
    pushUndo();
    var rg = range();
    for (var i = 0; i < clip.vals.length; i++) for (var j = 0; j < clip.vals[i].length; j++) {
      var r = rg.r1 + i, c = rg.c1 + j;
      if (r >= sh.nR || c >= sh.nC) continue;
      var src = clip.vals[i][j], cell = X.ensure(sh, r, c);
      cell.t = src.t;
      if (src.f) { cell.f = X.shiftFormula(src.f, r - (clip.r + i), c - (clip.c + j)); cell.v = ''; }
      else { cell.f = null; cell.v = src.v; }
    }
    persist(); render(); toast('วางแล้ว');
  }
  function doClear() {
    if (!isAdmin()) return;
    pushUndo();
    var rg = range();
    for (var r = rg.r1; r <= rg.r2; r++) for (var c = rg.c1; c <= rg.c2; c++) {
      var cell = X.cellAt(sh, r, c);
      if (cell) { cell.v = ''; cell.f = null; }
    }
    persist(); render();
  }

  // ---------- fill (ลากมุม) ----------
  function fillTo(tr, tc) {
    // คัดลอกช่วงที่เลือกไปถึง (tr,tc) ทิศเดียว (แนวตั้งหรือแนวนอน)
    var rg = range();
    pushUndo();
    if (tr > rg.r2) {  // ลงล่าง
      for (var r = rg.r2 + 1; r <= tr; r++) for (var c = rg.c1; c <= rg.c2; c++) copyCell(rg.r1 + ((r - rg.r1) % (rg.r2 - rg.r1 + 1)), c, r, c);
    } else if (tr < rg.r1) {
      for (r = rg.r1 - 1; r >= tr; r--) for (c = rg.c1; c <= rg.c2; c++) copyCell(rg.r1 + ((((r - rg.r1) % (rg.r2 - rg.r1 + 1)) + (rg.r2 - rg.r1 + 1)) % (rg.r2 - rg.r1 + 1)), c, r, c);
    } else if (tc > rg.c2) {  // ขวา
      for (c = rg.c2 + 1; c <= tc; c++) for (r = rg.r1; r <= rg.r2; r++) copyCell(r, rg.c1 + ((c - rg.c1) % (rg.c2 - rg.c1 + 1)), r, c);
    } else if (tc < rg.c1) {
      for (c = rg.c1 - 1; c >= tc; c--) for (r = rg.r1; r <= rg.r2; r++) copyCell(r, rg.c1 + ((((c - rg.c1) % (rg.c2 - rg.c1 + 1)) + (rg.c2 - rg.c1 + 1)) % (rg.c2 - rg.c1 + 1)), r, c);
    }
    persist();
    sel.ar = Math.min(rg.r1, tr); sel.ac = Math.min(rg.c1, tc);
    sel.r = Math.max(rg.r2, tr); sel.c = Math.max(rg.c2, tc);
    render();
    toast('คัดลอกด้วย Fill Handle แล้ว');
  }
  function copyCell(sr, sc, tr, tc) {
    var src = X.cellAt(sh, sr, sc), dst = X.ensure(sh, tr, tc);
    if (!src) { dst.v = ''; dst.f = null; return; }
    dst.t = src.t;
    dst.s = JSON.parse(JSON.stringify(src.s || {}));
    if (src.f) { dst.f = X.shiftFormula(src.f, tr - sr, tc - sc); dst.v = ''; }
    else { dst.f = null; dst.v = src.v; }
  }

  // ---------- undo ----------
  function undo() { if (!undoStack.length) return; redoStack.push(snap()); sh = JSON.parse(undoStack.pop()); persist(); render(); toast('ย้อนกลับ'); }
  function redo() { if (!redoStack.length) return; undoStack.push(snap()); sh = JSON.parse(redoStack.pop()); persist(); render(); toast('ทำซ้ำ'); }

  // ---------- row / size ops ----------
  function curDataRow() {
    var r = sel.r;
    if (sh.rowKind[r] === 'data') return r;
    for (var i = r; i < sh.nR; i++) if (sh.rowKind[i] === 'data') return i;
    return -1;
  }
  function addModelRow() {
    if (!isAdmin()) return;
    var r = curDataRow(); if (r < 0) return;
    pushUndo();
    X.insertRow(sh, r + 1, 'data', sh.rowGid[r]);
    // ค่าตั้งต้นเหมือนคอลัมน์สูตรของแถวบน
    [10, 11, 14, 15, 17, 18, 20, 21].forEach(function (c) {
      var src = X.cellAt(sh, r, c);
      if (src && src.f) copyCell(r, c, r + 1, c);
    });
    [1, 4, 5].forEach(function (c) { copyCell(r, c, r + 1, c); });
    X.rebuildSizeMerges(sh);
    persist(); render(); setActive(r + 1, 2); toast('เพิ่มรุ่นใหม่ในขนาดเดียวกัน');
  }
  function addSizeGroup() {
    if (!isAdmin()) return;
    var r = curDataRow(); if (r < 0) return;
    var g = sh.rowGid[r], end = r;
    while (end + 1 < sh.nR && sh.rowKind[end + 1] === 'data' && sh.rowGid[end + 1] === g) end++;
    pushUndo();
    var ng = Math.max.apply(null, sh.rowGid.filter(function (x) { return x != null; })) + 1;
    X.insertRow(sh, end + 1, 'data', ng);
    var nr = end + 1;
    var sz = X.ensure(sh, nr, 0); sz.v = 'ขนาดใหม่'; sz.t = 'text'; sz.s = { bg: 'F2F2F2', fc: '0000FF', b: 1, fs: 11, al: 'center' };
    [10, 11, 14, 15, 17, 18, 20, 21].forEach(function (c) {
      var src = X.cellAt(sh, r, c);
      if (src && src.f) copyCell(r, c, nr, c);
    });
    X.rebuildSizeMerges(sh);
    persist(); render(); setActive(nr, 0); toast('เพิ่มขนาดยางใหม่ — พิมพ์ขนาดได้เลย');
  }
  function deleteSelRows() {
    if (!isAdmin()) return;
    var rg = range();
    var r1 = rg.r1, r2 = rg.r2;
    if (r2 - r1 + 1 >= sh.nR) { toast('ลบทั้งหมดไม่ได้'); return; }
    pushUndo();
    X.deleteRowRange(sh, r1, r2 - r1 + 1);
    X.rebuildSizeMerges(sh);
    persist(); render(); setActive(Math.min(r1, sh.nR - 1), sel.c); toast('ลบแถวแล้ว');
  }
  function deleteSizeGroup() {
    if (!isAdmin()) return;
    var r = curDataRow(); if (r < 0) return;
    var g = sh.rowGid[r], start = r, end = r;
    while (start - 1 >= 0 && sh.rowKind[start - 1] === 'data' && sh.rowGid[start - 1] === g) start--;
    while (end + 1 < sh.nR && sh.rowKind[end + 1] === 'data' && sh.rowGid[end + 1] === g) end++;
    pushUndo();
    X.deleteRowRange(sh, start, end - start + 1);
    X.rebuildSizeMerges(sh);
    persist(); render(); setActive(Math.min(start, sh.nR - 1), 0); toast('ลบขนาดยางทั้งกลุ่มแล้ว');
  }
  function insertRowAt(after) {
    if (!isAdmin()) return;
    var r = sel.r;
    pushUndo();
    X.insertRow(sh, after ? r + 1 : r, sh.rowKind[r] === 'data' ? 'data' : 'data', sh.rowGid[r]);
    X.rebuildSizeMerges(sh);
    persist(); render(); toast('แทรกแถวแล้ว');
  }

  // ---------- merge ----------
  function mergeSel() {
    if (!isAdmin()) return;
    var rg = range();
    if (rg.r1 === rg.r2 && rg.c1 === rg.c2) { toast('เลือกมากกว่า 1 ช่องก่อนผสาน'); return; }
    pushUndo();
    X.addMerge(sh, rg.r1, rg.c1, rg.r2 - rg.r1 + 1, rg.c2 - rg.c1 + 1);
    persist(); render(); toast('ผสานเซลล์แล้ว');
  }
  function unmergeSel() {
    if (!isAdmin()) return;
    var rg = range();
    pushUndo();
    X.unmergeRange(sh, rg.r1, rg.c1, rg.r2, rg.c2);
    persist(); render(); toast('ยกเลิกผสานแล้ว');
  }

  // ---------- format / style ----------
  function setType(t) {
    if (!isAdmin()) return;
    pushUndo();
    var rg = range();
    for (var r = rg.r1; r <= rg.r2; r++) for (var c = rg.c1; c <= rg.c2; c++) X.ensure(sh, r, c).t = t;
    persist(); render();
    toast(t === 'num' ? 'กำหนดเป็นตัวเลข' : t === 'text' ? 'กำหนดเป็นข้อความ' : 'กำหนดเป็นอัตโนมัติ');
  }
  function setStyle(prop, val) {
    if (!isAdmin()) return;
    pushUndo();
    var rg = range();
    for (var r = rg.r1; r <= rg.r2; r++) for (var c = rg.c1; c <= rg.c2; c++) {
      var cell = X.ensure(sh, r, c);
      cell.s = cell.s || {};
      if (val == null) delete cell.s[prop]; else cell.s[prop] = val;
    }
    persist(); render();
  }

  // ---------- locks ----------
  function toggleLockRows() {
    if (!isAdmin()) return;
    pushUndo();
    var rg = range(), all = true;
    for (var r = rg.r1; r <= rg.r2; r++) if (!sh.adminRows[r]) { all = false; break; }
    for (r = rg.r1; r <= rg.r2; r++) { if (all) delete sh.adminRows[r]; else sh.adminRows[r] = 1; }
    persist(); render();
    toast(all ? 'ยกเลิกซ่อนแถว' : '🔒 ซ่อนแถวจากผู้ใช้แล้ว');
  }
  function toggleLockCols() {
    if (!isAdmin()) return;
    pushUndo();
    var rg = range(), all = true;
    for (var c = rg.c1; c <= rg.c2; c++) if (!sh.adminCols[c]) { all = false; break; }
    for (c = rg.c1; c <= rg.c2; c++) { if (all) delete sh.adminCols[c]; else sh.adminCols[c] = 1; }
    persist(); render();
    toast(all ? 'ยกเลิกซ่อนคอลัมน์' : '🔒 ซ่อนคอลัมน์จากผู้ใช้แล้ว');
  }

  // ---------- toast ----------
  var toastT;
  function toast(msg) {
    var t = document.getElementById('toast'); if (!t) return;
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastT); toastT = setTimeout(function () { t.classList.remove('show'); }, 1500);
  }

  // ---------- init / versions ----------
  function init(opts) {
    rootEl = opts.root; wrapEl = opts.wrap; statusEl = opts.status; fxEl = opts.fx; nameEl = opts.name;
    var saved = X.store.loadCurrent();
    sh = (saved && saved.nR) ? saved : window.XL2_SEED.buildSheet();
    inputEl = document.createElement('input');
    inputEl.className = 'cell-input'; inputEl.style.display = 'none';
    fillEl = document.createElement('div');
    fillEl.id = 'fillHandle';
    render();
    setActive(firstDataRow(), 2);
    dirty = false;
  }
  function firstDataRow() { for (var r = 0; r < sh.nR; r++) if (sh.rowKind[r] === 'data') return r; return 0; }
  function saveAs(name) {
    var id = 'v' + Date.now();
    sh.meta.name = name || sh.meta.name;
    X.store.saveVersionDoc(id, sh);
    var vs = X.store.loadVersions();
    vs.unshift({ id: id, name: name || sh.meta.name, savedAt: Date.now() });
    X.store.saveVersions(vs);
    X.store.saveCurrent(sh);
    dirty = false; toast('บันทึกเป็น: ' + (name || sh.meta.name));
  }
  function save() { X.store.saveCurrent(sh); dirty = false; toast('บันทึกแล้ว'); }
  function openVersion(id) {
    var d = X.store.loadVersion(id); if (!d) return;
    sh = d; undoStack.length = redoStack.length = 0;
    persist(); render(); setActive(firstDataRow(), 2); toast('เปิดเวอร์ชันแล้ว');
  }
  function newFromSource() {
    sh = window.XL2_SEED.buildSheet();
    undoStack.length = redoStack.length = 0;
    persist(); render(); setActive(firstDataRow(), 2); toast('โหลดต้นฉบับใหม่');
  }
  function setMode(m) {
    if (editing) cancelEdit();
    view.mode = m === 'user' ? 'user' : 'admin';
    if (view.mode === 'user') {
      if (!colVis(sel.c)) { sel.c = stepCol(sel.c, 1) === sel.c ? stepCol(sel.c, -1) : stepCol(sel.c, 1); sel.ac = sel.c; }
      if (!rowVis(sel.r)) { sel.r = stepRow(sel.r, 1) === sel.r ? stepRow(sel.r, -1) : stepRow(sel.r, 1); sel.ar = sel.r; }
    }
    render();
    return view.mode;
  }

  window.Grid2 = {
    init: init, render: render, paint: paintSelection,
    sheet: function () { return sh; }, view: function () { return view; },
    sel: sel, range: range, setActive: setActive, leaderOf: leaderOf, cellEl: cellEl,
    stepRow: stepRow, stepCol: stepCol,
    startEdit: startEdit, commitEdit: commitEdit, cancelEdit: cancelEdit, isEditing: isEditing,
    inputEl: function () { return inputEl; }, fillEl: function () { return fillEl; },
    copy: doCopy, paste: doPaste, clear: doClear, fillTo: fillTo,
    undo: undo, redo: redo, pushUndo: pushUndo, persist: persist,
    addModelRow: addModelRow, addSizeGroup: addSizeGroup, deleteSelRows: deleteSelRows,
    deleteSizeGroup: deleteSizeGroup, insertRowAt: insertRowAt,
    mergeSel: mergeSel, unmergeSel: unmergeSel, setType: setType, setStyle: setStyle,
    toggleLockRows: toggleLockRows, toggleLockCols: toggleLockCols,
    setMode: setMode, isAdmin: isAdmin,
    toggleSecret: function () { view.secret = !view.secret; render(); return view.secret; },
    setZoom: function (z) { view.zoom = Math.max(0.6, Math.min(1.8, z)); render(); },
    getZoom: function () { return view.zoom; },
    isDirty: function () { return dirty; },
    toast: toast
  };
})();
