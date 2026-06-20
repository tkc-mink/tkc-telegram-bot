/* ============================================================
   interact.js — เมาส์/คีย์บอร์ด: resize+ตัวเลข, autofit, fill drag,
   เลือกแถว/คอลัมน์แยก, คลิกขวา, formula bar
   ============================================================ */
(function () {
  var X = window.XL2, G = window.Grid2;
  var rootEl, wrapEl, fxEl, nameEl;
  var drag = null;   // {kind:'cells'|'rows'|'cols'|'rzc'|'rzr'|'fill', ...}
  var rzTip, ctxEl;

  function sh() { return G.sheet(); }
  function z() { return G.getZoom(); }

  // ---------- helpers ----------
  function tdFromEvent(e) {
    var el = document.elementFromPoint(e.clientX, e.clientY);
    return el ? el.closest && el.closest('td.cell') : null;
  }
  function visColEls() { return rootEl.querySelectorAll('colgroup col'); }
  function colElIndex(c) {  // map sheet col -> <col> index (offset 1 ตัวแรกคือ gutter)
    var idx = 1;
    for (var i = 0; i < sh().nC; i++) {
      if (G.isAdmin() || !sh().adminCols[i]) {
        if (i === c) return idx;
        idx++;
      } else if (i === c) return -1;
    }
    return -1;
  }
  function excelW(px) { return Math.max(0, (px - 5) / 7).toFixed(2); }
  function excelH(px) { return (px * 0.75).toFixed(2); }
  function showTip(x, y, text) {
    rzTip.style.display = 'block';
    rzTip.style.left = (x + 14) + 'px';
    rzTip.style.top = (y - 34) + 'px';
    rzTip.textContent = text;
  }
  function hideTip() { rzTip.style.display = 'none'; }

  // คอลัมน์เป้าหมายตอน resize: ถ้าคอลัมน์ที่จับอยู่ในช่วงที่เลือกแบบทั้งคอลัมน์ → ปรับทุกคอลัมน์ที่เลือก
  function resizeTargetsCols(c) {
    var rg = G.range();
    if (drag && drag.selKind === 'cols' && c >= rg.c1 && c <= rg.c2) {}
    if (lastSelKind === 'cols' && c >= rg.c1 && c <= rg.c2) {
      var out = [];
      for (var i = rg.c1; i <= rg.c2; i++) out.push(i);
      return out;
    }
    return [c];
  }
  function resizeTargetsRows(r) {
    var rg = G.range();
    if (lastSelKind === 'rows' && r >= rg.r1 && r <= rg.r2) {
      var out = [];
      for (var i = rg.r1; i <= rg.r2; i++) out.push(i);
      return out;
    }
    return [r];
  }
  var lastSelKind = 'cells';

  // ---------- autofit ----------
  var meas = document.createElement('canvas').getContext('2d');
  function autofitCol(c) {
    var s = sh(), max = 30;
    for (var r = 0; r < s.nR; r++) {
      if (s.rowKind[r] !== 'data' && s.rowKind[r] !== 'head') continue;
      var m = X.mergeAt(s, r, c);
      if (m && (m.cs > 1)) continue;  // ข้ามช่องผสานแนวนอน
      var cell = X.cellAt(s, r, c); if (!cell) continue;
      var txt = X.display(s, r, c); if (!txt) continue;
      var fs = (cell.s && cell.s.fs) || 10;
      meas.font = ((cell.s && cell.s.b) ? '700 ' : '') + fs + 'px Arial';
      txt.split('\n').forEach(function (line) {
        max = Math.max(max, meas.measureText(line).width + 12);
      });
    }
    return Math.ceil(max);
  }
  function autofitRow(r) {
    var s = sh(), max = 18;
    for (var c = 0; c < s.nC; c++) {
      var cell = X.cellAt(s, r, c); if (!cell) continue;
      var txt = X.display(s, r, c); if (!txt) continue;
      var fs = (cell.s && cell.s.fs) || 10;
      var lines = String(txt).split('\n').length;
      max = Math.max(max, lines * fs * 1.25 + 8);
    }
    return Math.ceil(max);
  }

  // ---------- mousedown ----------
  function onMouseDown(e) {
    if (e.button === 2) return;  // ขวา → contextmenu
    hideCtx();
    var t = e.target;

    // 1) resize คอลัมน์
    if (t.classList && t.classList.contains('rz-c')) {
      var c = +t.dataset.rzc;
      drag = { kind: 'rzc', targets: resizeTargetsCols(c), startX: e.clientX, startW: sh().colW[c], c: c };
      e.preventDefault(); return;
    }
    // 2) resize แถว
    if (t.classList && t.classList.contains('rz-r')) {
      var r = +t.dataset.rzr;
      drag = { kind: 'rzr', targets: resizeTargetsRows(r), startY: e.clientY, startH: sh().rowH[r], r: r };
      e.preventDefault(); return;
    }
    // 3) fill handle
    if (t.id === 'fillHandle') {
      var rg = G.range();
      drag = { kind: 'fill', rg: rg, tr: rg.r2, tc: rg.c2 };
      e.preventDefault(); return;
    }
    // 4) corner = เลือกทั้งหมด
    if (t.id === 'cornerAll' || (t.closest && t.closest('#cornerAll'))) {
      G.sel.ar = 0; G.sel.ac = 0; G.sel.r = sh().nR - 1; G.sel.c = sh().nC - 1;
      lastSelKind = 'cells'; G.paint();
      e.preventDefault(); return;
    }
    // 5) หัวคอลัมน์ = เลือกทั้งคอลัมน์
    var ch = t.closest && t.closest('th.ch');
    if (ch) {
      var hc = +ch.dataset.hc;
      if (G.isEditing()) G.commitEdit();
      if (e.shiftKey) { G.sel.c = hc; } else { G.sel.ac = hc; G.sel.c = hc; }
      G.sel.ar = 0; G.sel.r = sh().nR - 1;
      lastSelKind = 'cols';
      drag = { kind: 'cols' };
      G.paint(); rootEl.focus();
      e.preventDefault(); return;
    }
    // 6) เลขแถว = เลือกทั้งแถว
    var rh = t.closest && t.closest('th.rh');
    if (rh) {
      var hr = +rh.dataset.hr;
      if (G.isEditing()) G.commitEdit();
      if (e.shiftKey) { G.sel.r = hr; } else { G.sel.ar = hr; G.sel.r = hr; }
      G.sel.ac = 0; G.sel.c = sh().nC - 1;
      lastSelKind = 'rows';
      drag = { kind: 'rows' };
      G.paint(); rootEl.focus();
      e.preventDefault(); return;
    }
    // 7) เซลล์ปกติ
    var td = t.closest && t.closest('td.cell');
    if (td) {
      if (G.isEditing()) G.commitEdit();
      G.setActive(+td.dataset.r, +td.dataset.c, e.shiftKey);
      lastSelKind = 'cells';
      drag = { kind: 'cells' };
      rootEl.focus();
    }
  }

  // ---------- mousemove ----------
  function onMouseMove(e) {
    if (!drag) return;
    if (drag.kind === 'rzc') {
      var w = Math.max(18, Math.round(drag.startW + (e.clientX - drag.startX) / z()));
      drag.targets.forEach(function (c) { sh().colW[c] = w; });
      // live update <col>
      drag.targets.forEach(function (c) {
        var i = colElIndex(c);
        if (i >= 0) visColEls()[i].style.width = Math.round(w * z()) + 'px';
      });
      showTip(e.clientX, e.clientY, 'ความกว้าง: ' + excelW(w) + ' (' + w + ' พิกเซล)' + (drag.targets.length > 1 ? ' × ' + drag.targets.length + ' คอลัมน์' : ''));
      return;
    }
    if (drag.kind === 'rzr') {
      var h = Math.max(12, Math.round(drag.startH + (e.clientY - drag.startY) / z()));
      drag.targets.forEach(function (r) { sh().rowH[r] = h; });
      drag.targets.forEach(function (r) {
        var tr = rootEl.querySelector('tr[data-row="' + r + '"]');
        if (tr) tr.style.height = Math.round(h * z()) + 'px';
      });
      showTip(e.clientX, e.clientY, 'ความสูง: ' + excelH(h) + ' (' + h + ' พิกเซล)' + (drag.targets.length > 1 ? ' × ' + drag.targets.length + ' แถว' : ''));
      return;
    }
    if (drag.kind === 'fill') {
      var td = tdFromEvent(e);
      if (td) {
        var r = +td.dataset.r, c = +td.dataset.c, rg = drag.rg;
        // ทิศเด่น
        var dR = r > rg.r2 ? r - rg.r2 : (r < rg.r1 ? r - rg.r1 : 0);
        var dC = c > rg.c2 ? c - rg.c2 : (c < rg.c1 ? c - rg.c1 : 0);
        if (Math.abs(dR) >= Math.abs(dC)) { drag.tr = rg.r1 <= r && r <= rg.r2 ? rg.r2 : r; drag.tc = null; }
        else { drag.tc = rg.c1 <= c && c <= rg.c2 ? rg.c2 : c; drag.tr = null; }
        paintFillPreview(drag);
      }
      return;
    }
    if (drag.kind === 'cells') {
      var td2 = e.target.closest && e.target.closest('td.cell');
      if (td2) G.setActive(+td2.dataset.r, +td2.dataset.c, true);
      return;
    }
    if (drag.kind === 'rows') {
      var rh = e.target.closest && e.target.closest('th.rh');
      if (rh) { G.sel.r = +rh.dataset.hr; G.paint(); }
      return;
    }
    if (drag.kind === 'cols') {
      var ch = e.target.closest && e.target.closest('th.ch');
      if (ch) { G.sel.c = +ch.dataset.hc; G.paint(); }
      return;
    }
  }
  function paintFillPreview(d) {
    rootEl.querySelectorAll('.cell.fillprev').forEach(function (el) { el.classList.remove('fillprev'); });
    var rg = d.rg;
    var r1 = rg.r1, r2 = rg.r2, c1 = rg.c1, c2 = rg.c2;
    if (d.tr != null) { r1 = Math.min(r1, d.tr); r2 = Math.max(r2, d.tr); }
    if (d.tc != null) { c1 = Math.min(c1, d.tc); c2 = Math.max(c2, d.tc); }
    rootEl.querySelectorAll('td.cell').forEach(function (td) {
      var r = +td.dataset.r, c = +td.dataset.c;
      if (r >= r1 && r <= r2 && c >= c1 && c <= c2) td.classList.add('fillprev');
    });
  }

  // ---------- mouseup ----------
  function onMouseUp(e) {
    if (!drag) return;
    var d = drag; drag = null;
    if (d.kind === 'rzc' || d.kind === 'rzr') {
      hideTip();
      G.pushUndo(); G.persist(); G.render();
      return;
    }
    if (d.kind === 'fill') {
      rootEl.querySelectorAll('.cell.fillprev').forEach(function (el) { el.classList.remove('fillprev'); });
      var rg = d.rg;
      if (d.tr != null && (d.tr > rg.r2 || d.tr < rg.r1)) G.fillTo(d.tr, rg.c2);
      else if (d.tc != null && (d.tc > rg.c2 || d.tc < rg.c1)) G.fillTo(rg.r2, d.tc);
      return;
    }
  }

  // ---------- dblclick ----------
  function onDblClick(e) {
    var t = e.target;
    if (t.classList && t.classList.contains('rz-c')) {     // autofit กว้าง
      var c = +t.dataset.rzc;
      G.pushUndo();
      resizeTargetsCols(c).forEach(function (ci) { sh().colW[ci] = autofitCol(ci); });
      G.persist(); G.render();
      G.toast('ปรับความกว้างพอดีอักษร');
      return;
    }
    if (t.classList && t.classList.contains('rz-r')) {     // autofit สูง
      var r = +t.dataset.rzr;
      G.pushUndo();
      resizeTargetsRows(r).forEach(function (ri) { sh().rowH[ri] = autofitRow(ri); });
      G.persist(); G.render();
      G.toast('ปรับความสูงพอดีอักษร');
      return;
    }
    var td = t.closest && t.closest('td.cell');
    if (td) { G.setActive(+td.dataset.r, +td.dataset.c); G.startEdit(null); }
  }

  // ---------- context menu ----------
  function buildCtx() {
    ctxEl = document.createElement('div');
    ctxEl.id = 'ctxMenu';
    document.body.appendChild(ctxEl);
    document.addEventListener('mousedown', function (e) { if (!ctxEl.contains(e.target)) hideCtx(); });
  }
  function hideCtx() { if (ctxEl) ctxEl.style.display = 'none'; }
  function mi(label, fn, dis) {
    var d = document.createElement('div');
    d.className = 'ci' + (dis ? ' dis' : '');
    d.innerHTML = label;
    if (!dis) d.onmousedown = function (e) { e.preventDefault(); e.stopPropagation(); hideCtx(); fn(); };
    return d;
  }
  function sep() { var d = document.createElement('div'); d.className = 'csep'; return d; }
  function onCtx(e) {
    var td = e.target.closest && e.target.closest('td.cell');
    var rh = e.target.closest && e.target.closest('th.rh');
    var ch = e.target.closest && e.target.closest('th.ch');
    if (!td && !rh && !ch) return;
    e.preventDefault();
    if (td) {
      var r = +td.dataset.r, c = +td.dataset.c;
      var rg = G.range();
      if (r < rg.r1 || r > rg.r2 || c < rg.c1 || c > rg.c2) { G.setActive(r, c); lastSelKind = 'cells'; }
    } else if (rh) {
      var hr = +rh.dataset.hr;
      G.sel.ar = hr; G.sel.r = hr; G.sel.ac = 0; G.sel.c = sh().nC - 1; lastSelKind = 'rows'; G.paint();
    } else if (ch) {
      var hc = +ch.dataset.hc;
      G.sel.ac = hc; G.sel.c = hc; G.sel.ar = 0; G.sel.r = sh().nR - 1; lastSelKind = 'cols'; G.paint();
    }
    var adm = G.isAdmin();
    var L = G.leaderOf(G.sel.r, G.sel.c);
    var cell = X.cellAt(sh(), L.r, L.c);
    var merged = !!X.mergeAt(sh(), L.r, L.c);
    ctxEl.innerHTML = '';
    ctxEl.appendChild(mi('✂️ ตัด <span class="ks">Ctrl+X</span>', function () { G.copy(true); }, !adm));
    ctxEl.appendChild(mi('📄 คัดลอก <span class="ks">Ctrl+C</span>', function () { G.copy(false); }));
    ctxEl.appendChild(mi('📥 วาง <span class="ks">Ctrl+V</span>', function () { G.paste(); }, !adm));
    ctxEl.appendChild(sep());
    ctxEl.appendChild(mi('➕ แทรกแถวด้านบน', function () { G.insertRowAt(false); }, !adm));
    ctxEl.appendChild(mi('➕ แทรกแถวด้านล่าง', function () { G.insertRowAt(true); }, !adm));
    ctxEl.appendChild(mi('🗑️ ลบแถวที่เลือก', function () { G.deleteSelRows(); }, !adm));
    ctxEl.appendChild(sep());
    ctxEl.appendChild(mi(merged ? '⬜ ยกเลิกผสานเซลล์' : '⬛ ผสานเซลล์ (Merge)', function () { merged ? G.unmergeSel() : G.mergeSel(); }, !adm));
    ctxEl.appendChild(sep());
    var t = cell ? cell.t : 'auto';
    ctxEl.appendChild(mi((t === 'auto' ? '● ' : '○ ') + 'รูปแบบ: อัตโนมัติ', function () { G.setType('auto'); }, !adm));
    ctxEl.appendChild(mi((t === 'num' ? '● ' : '○ ') + 'รูปแบบ: ตัวเลข (1,234)', function () { G.setType('num'); }, !adm));
    ctxEl.appendChild(mi((t === 'text' ? '● ' : '○ ') + 'รูปแบบ: ข้อความ', function () { G.setType('text'); }, !adm));
    ctxEl.appendChild(sep());
    ctxEl.appendChild(mi('ƒx ใส่สูตร… (เช่น =H9-G9)', function () {
      fxEl.focus(); if (!fxEl.value) fxEl.value = '=';
    }, !adm));
    ctxEl.appendChild(mi('🗄️ ดึงจาก Database…', function () { promptDB(); }, !adm));
    ctxEl.appendChild(sep());
    ctxEl.appendChild(mi('🔒 ซ่อน/แสดงแถวนี้จากผู้ใช้', function () { G.toggleLockRows(); }, !adm));
    ctxEl.appendChild(mi('🔒 ซ่อน/แสดงคอลัมน์นี้จากผู้ใช้', function () { G.toggleLockCols(); }, !adm));
    ctxEl.style.display = 'block';
    var mw = 250, mh = ctxEl.offsetHeight || 420;
    ctxEl.style.left = Math.min(e.clientX, window.innerWidth - mw - 8) + 'px';
    ctxEl.style.top = Math.min(e.clientY, window.innerHeight - mh - 8) + 'px';
  }
  function promptDB() {
    var code = prompt('รหัสสินค้า (รุ่น) ใน Database เช่น ' + Object.keys(window.TIRE_DB || {}).slice(0, 3).join(', '));
    if (!code) return;
    var field = prompt('ฟิลด์ที่ต้องการ: dot / cost / retail / size / brand', 'dot');
    if (!field) return;
    G.startEdit('=DB("' + code + '","' + field + '")');
    G.commitEdit();
    G.toast('ผูกกับ Database แล้ว (ตอนนี้ใช้ข้อมูลตัวอย่าง — รอเชื่อม server)');
  }

  // ---------- keyboard ----------
  function onKey(e) {
    if (G.isEditing()) {
      if (e.key === 'Enter') { e.preventDefault(); G.commitEdit(e.shiftKey ? 'up' : 'down'); syncFx(); }
      else if (e.key === 'Tab') { e.preventDefault(); G.commitEdit(e.shiftKey ? 'left' : 'right'); syncFx(); }
      else if (e.key === 'Escape') { e.preventDefault(); G.cancelEdit(); syncFx(); }
      return;
    }
    var k = e.key, meta = e.ctrlKey || e.metaKey;
    if (meta) {
      if (k === 'c' || k === 'C') { e.preventDefault(); G.copy(false); return; }
      if (k === 'x' || k === 'X') { e.preventDefault(); G.copy(true); return; }
      if (k === 'v' || k === 'V') { e.preventDefault(); G.paste(); return; }
      if (k === 'z' || k === 'Z') { e.preventDefault(); e.shiftKey ? G.redo() : G.undo(); return; }
      if (k === 'y' || k === 'Y') { e.preventDefault(); G.redo(); return; }
      if (k === 'b' || k === 'B') { e.preventDefault(); toggleBold(); return; }
      return;
    }
    if (k === 'ArrowDown') { e.preventDefault(); G.setActive(G.stepRow(G.sel.r, 1), G.sel.c, e.shiftKey); lastSelKind = 'cells'; }
    else if (k === 'ArrowUp') { e.preventDefault(); G.setActive(G.stepRow(G.sel.r, -1), G.sel.c, e.shiftKey); lastSelKind = 'cells'; }
    else if (k === 'ArrowLeft') { e.preventDefault(); G.setActive(G.sel.r, G.stepCol(G.sel.c, -1), e.shiftKey); }
    else if (k === 'ArrowRight') { e.preventDefault(); G.setActive(G.sel.r, G.stepCol(G.sel.c, 1), e.shiftKey); }
    else if (k === 'Tab') { e.preventDefault(); G.setActive(G.sel.r, G.stepCol(G.sel.c, e.shiftKey ? -1 : 1)); }
    else if (k === 'Enter') { e.preventDefault(); G.startEdit(null); }
    else if (k === 'F2') { e.preventDefault(); G.startEdit(null); }
    else if (k === 'Delete' || k === 'Backspace') { e.preventDefault(); G.clear(); }
    else if (k === 'Home') { e.preventDefault(); G.setActive(G.sel.r, 0); }
    else if (k === 'End') { e.preventDefault(); G.setActive(G.sel.r, sh().nC - 1); }
    else if (k.length === 1 && !e.altKey) { e.preventDefault(); G.startEdit(k); }
  }
  function toggleBold() {
    var L = G.leaderOf(G.sel.r, G.sel.c);
    var cell = X.cellAt(sh(), L.r, L.c);
    G.setStyle('b', cell && cell.s && cell.s.b ? null : 1);
  }

  // ---------- formula bar ----------
  function syncFx() { /* updateBars จะจัดการตอน paint */ }
  function wireFx() {
    fxEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (!G.isAdmin()) { G.toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
        G.startEdit(fxEl.value, true);
        G.commitEdit('down');
        rootEl.focus();
      } else if (e.key === 'Escape') {
        e.preventDefault(); G.paint(); rootEl.focus();
      }
    });
    fxEl.addEventListener('focus', function () { if (!G.isAdmin()) fxEl.blur(); });
    // พิมพ์ในเซลล์ → สะท้อนใน fx
    G.inputEl().addEventListener('input', function () { fxEl.value = G.inputEl().value; });
    G.inputEl().addEventListener('blur', function () { if (G.isEditing()) G.commitEdit(); });
  }

  // ---------- init ----------
  function init(opts) {
    rootEl = opts.root; wrapEl = opts.wrap; fxEl = opts.fx; nameEl = opts.name;
    rzTip = document.createElement('div');
    rzTip.id = 'rzTip'; rzTip.style.display = 'none';
    document.body.appendChild(rzTip);
    buildCtx();
    rootEl.tabIndex = 0;
    rootEl.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    rootEl.addEventListener('dblclick', onDblClick);
    rootEl.addEventListener('contextmenu', onCtx);
    rootEl.addEventListener('keydown', onKey);
    wireFx();
    rootEl.focus();
  }

  window.XL2_Interact = { init: init };
})();
