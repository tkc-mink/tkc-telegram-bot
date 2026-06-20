/* แถบหมวด + ชื่อไฟล์ + เพิ่ม/แก้/ลบหมวด + กำหนดเวลา + refresh()
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดต่อเนื่องตามลำดับก่อน price-update.js */
  // ---- sheet bar (หมวด) ----
  function renderSheets() {
    var sheets = XL2.store.sheetsList(), cur = XL2.store.curSheet();
    function opt(s) { return '<option value="' + s.id + '"' + (s.id === cur ? ' selected' : '') + '>' + XL2.esc(s.name) + '</option>'; }
    var normal = sheets.filter(function (s) { return !s.archived; });
    var arch = sheets.filter(function (s) { return s.archived; });
    $('sheetSel').innerHTML = normal.map(opt).join('') +
      (arch.length ? '<optgroup label="📦 ประวัติหลังอัพเดท (ย้อนดูได้)">' + arch.map(opt).join('') + '</optgroup>' : '');
    // ชื่อบนหัวโปรแกรม = ชื่อไฟล์ที่ทำอยู่ (แยกจากชื่อหน้าชีต) · บรรทัดรอง = หมวดที่กำลังดู
    var curS = sheets.find(function (s) { return s.id === cur; });
    var t = $('brandTtl');
    if (t) t.innerHTML = XL2.esc(getFileName()) + '<small>' + (curS ? '📄 ' + XL2.esc(curS.name) : '') + '</small>';
  }
  // ---------- ชื่อไฟล์ (เก็บถาวร · แก้ได้ด้วยดับเบิลคลิกที่ชื่อ) ----------
  var DEFAULT_FILE = 'แฟ้มราคายาง';
  function getFileName() { var n = (localStorage.getItem('xls2_filename') || '').trim(); return n || DEFAULT_FILE; }
  function setFileName(n) { n = (n || '').trim(); if (n) { localStorage.setItem('xls2_filename', n); renderSheets(); } }
  $('sheetSel').onchange = function () {
    XL2.store.setCurSheet(this.value);
    SG.reloadSheet();
    refresh(); renderFltBar();
  };
  $('shAdd').onclick = function () {
    promptDialog('เพิ่มหมวดใหม่', 'ตั้งชื่อหมวด เช่น ยางเก๋ง-01', '', function (nm) {
    if (!nm || !nm.trim()) return;
    nm = nm.trim();
    var id = 's' + Date.now();
    var colW = [92, 33, 41, 84, 36, 31, 71, 66, 26, 26, 71, 66, 30, 71, 66, 62, 71, 66, 62, 71, 66, 62, 101];
    var d = { name: nm, meta: {}, nCols: 23, nRows: 40,
      cells: { '0:0': { v: nm, t: 'text', s: { bg: 'FFFF99', fc: '0000FF', b: 1, fs: 15, al: 'center' } } },
      merges: { '0:0': { rs: 1, cs: 23 } }, colW: colW, rowH: [30],
      adminRows: {}, adminCols: { 6: 1, 10: 1, 13: 1, 15: 1, 16: 1, 18: 1, 19: 1, 21: 1 },
      rowLinks: {}, changes: {} };
    XL2.store.saveSheetDoc(id, d);
    var sheets = XL2.store.sheetsList(); sheets.push({ id: id, name: nm }); XL2.store.saveSheets(sheets);
    XL2.store.setCurSheet(id);
    SG.reloadSheet(); renderSheets(); refresh(); renderFltBar();
    });
  };
  $('shRen').onclick = function () {
    var sheets = XL2.store.sheetsList(), cur = XL2.store.curSheet();
    var s = sheets.find(function (x) { return x.id === cur; }); if (!s) return;
    promptDialog('แก้ไขชื่อหมวด', 'เปลี่ยนชื่อหมวดนี้', s.name, function (nm) {
    if (!nm || !nm.trim()) return;
    s.name = nm.trim();
    XL2.store.saveSheets(sheets);
    SG.getDoc().name = s.name; SG.save();
    renderSheets(); refresh();
    });
  };
  // ลบหมวด: ยืนยัน 2 รอบ + รอ 10 วินาทีก่อนกดยืนยันรอบสุดท้าย
  var delTimer = null, delStage = 0;
  function resetDelTimer() { if (delTimer) { clearInterval(delTimer); delTimer = null; } delStage = 0; }
  $('shDel').onclick = function () {
    var sheets = XL2.store.sheetsList();
    if (sheets.length <= 1) { alertDialog('ลบไม่ได้', 'ลบหมวดสุดท้ายไม่ได้ — ต้องมีอย่างน้อย 1 หมวด'); return; }
    var cur = XL2.store.curSheet();
    var s = sheets.find(function (x) { return x.id === cur; }); if (!s) return;
    resetDelTimer();
    $('delSheetBody').innerHTML = 'ต้องการลบหมวด “<b>' + XL2.esc(s.name) + '</b>”?<br><span style="color:#c0392b;">ข้อมูลทั้งชีตของหมวดนี้จะหายถาวร กู้คืนไม่ได้</span>';
    var b = $('delSheetBtn');
    b.disabled = false; b.textContent = '🗑️ ลบ (ยืนยันครั้งที่ 1)';
    $('mDelSheet').classList.add('open');
  };
  $('delSheetBtn').onclick = function () {
    var b = this;
    if (delStage === 0) {
      delStage = 1;
      var left = 10;
      b.disabled = true;
      b.textContent = '⏳ ยืนยันได้ใน ' + left + ' วิ…';
      delTimer = setInterval(function () {
        left--;
        if (left > 0) { b.textContent = '⏳ ยืนยันได้ใน ' + left + ' วิ…'; }
        else {
          clearInterval(delTimer); delTimer = null;
          b.disabled = false;
          b.style.background = '#c0392b'; b.style.color = '#fff';
          b.textContent = '🗑️ ยืนยันลบถาวร (ครั้งที่ 2)';
        }
      }, 1000);
      return;
    }
    // ครั้งที่ี 2 — ลบจริง
    var cur = XL2.store.curSheet();
    var sheets = XL2.store.sheetsList().filter(function (x) { return x.id !== cur; });
    XL2.store.saveSheets(sheets);
    XL2.store.deleteSheetDoc(cur);
    XL2.store.setCurSheet(sheets[0].id);
    resetDelTimer();
    b.style.background = ''; b.style.color = '#c0392b';
    $('mDelSheet').classList.remove('open');
    SG.reloadSheet(); renderSheets(); refresh(); renderFltBar();
  };
  $('mDelSheet').addEventListener('click', function (e) { if (e.target === this || e.target.closest('[data-close]')) resetDelTimer(); });

  function refresh() {
    renderSheets();
    enforceArchiveLock();
    var sc = SG.getSchedule();
    $('schedChip').textContent = '⏱ ใช้ราคา: ' + (sc ? sc.replace('T', ' ') : 'ทันที');
    $('schedChip').classList.toggle('hasdate', !!sc);
  }
  // schedule dialog
  $('schedChip').onclick = function () {
    var cur = SG.getSchedule();
    $('schedInput').value = cur || '';
    $('mSched').classList.add('open');
  };
  $('schedOk').onclick = function () {
    SG.setSchedule($('schedInput').value || '');
    $('mSched').classList.remove('open'); refresh();
  };
  $('schedNow').onclick = function () {
    SG.setSchedule('');
    $('mSched').classList.remove('open'); refresh();
  };

