/* [1/7] บูต + เริ่ม SG + แถบเครื่องมือจัดรูปแบบ + Ctrl+S/P (นิยาม $ global)
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดตามลำดับ 1→7 ก่อน price-update.js */
/* แกนหลักของโปรแกรม (โหมด/แถบเครื่องมือ/ระบบสี-เส้นขอบ-เทสี/หน้าตั้งค่า/หมวด-ไฟล์ + init)
   — แยกจาก index.html · โหลดหลัง dialogs.js + filter-bar.js · เปิด global: $, refresh, renderSheets ฯลฯ */
/* ── de-IIFE: ถอด wrapper ออก → ทุกสัญลักษณ์เป็น global โดยตั้งใจ (เช็คแล้วไม่ชนชื่อ built-in)
   เพื่อให้ซอยไฟล์ย่อยได้โดยไม่ต้องแก้ reference · ลำดับการรันเหมือนเดิมทุกประการ ── */
var $ = function (id) { return document.getElementById(id); };


  (function migrateSheets() {
    var sheets = XL2.store.sheetsList();
    if (!sheets.length) {
      var id = 's' + Date.now();
      sheets = [{ id: id, name: 'ยางปิคอัพ-01' }];
      XL2.store.saveSheets(sheets);
      XL2.store.setCurSheet(id);
      var legacy = localStorage.getItem('xls2_current');
      if (legacy) localStorage.setItem('xls2_sheet_' + id, legacy);
    }
    var cur = XL2.store.curSheet();
    if (!cur || !sheets.some(function (s) { return s.id === cur; })) XL2.store.setCurSheet(sheets[0].id);
  })();

  SG.init({ root: $('grid'), fx: $('fx'), name: $('nameBox'), status: $('status'), sum: $('sumbox'), ctx: $('ctx') });
  $('grid').addEventListener('mousedown', function () { setUndoSnap = null; }, true);   // แตะตาราง = เลิกสถานะย้อนการตั้งค่าสี
  // รวบแถบค้นหา + แถบสูตร fx เข้าแถว 2 (ช่องสูตรอยู่กลาง · ค้นหาอยู่ขวา)
  document.querySelector('.fxbar').appendChild($('fltbar'));
  document.querySelector('.fxbar').appendChild(document.querySelector('.grp-fx'));

  // toolbar
  $('btnUndo').onclick = function () { if (setUndoSnap) { restoreSettings(setUndoSnap); setUndoSnap = null; if (typeof toast === 'function') toast('↩ ย้อนการตั้งค่าสี'); return; } SG.undo(); };
  $('btnRedo').onclick = function () { SG.redo(); };
  $('btnAddSize').onclick = function () { SG.addSizeGroup(); };
  $('btnDelSize').onclick = function () { SG.delSizeGroup(); };
  $('btnAddModel').onclick = function () { SG.addModelRow(); };
  $('btnDelRow').onclick = function () { SG.deleteRow(); };
  $('btnMerge').onclick = function () { SG.toggleMerge(); };
  $('btnBold').onclick = function () { SG.applyStyle('b', 'toggle'); };
  $('btnItalic').onclick = function () { SG.applyStyle('i', 'toggle'); };
  $('btnUnder').onclick = function () { SG.applyStyle('u', 'toggle'); };
  $('fontFam').onchange = function () { SG.applyStyle('ff', this.value === 'Arial' ? null : (this.value || null)); };
  // ปุ่มจัดข้อความรวม: คลิกสลับ ซ้าย→กึ่งกลาง→ขวา · ไอคอนเปลี่ยนตาม
  var alCycle = ['left', 'center', 'right'], alClsMap = { left: 'l', center: 'c', right: 'r' };
  $('btnAlign').onclick = function () {
    var cur = (SG.getDoc().cells[SG.sel.r + ':' + SG.sel.c] || {}).s || {};
    var idx = alCycle.indexOf(cur.al || 'left');
    var next = alCycle[(idx + 1) % 3];
    SG.applyStyle('al', next);
    var ic = this.querySelector('.al-ic');
    ic.className = 'al-ic ' + alClsMap[next];
  };
  // ปรับไอคอนตามช่องที่เลือก
  function syncAlignIcon() {
    var cur = (SG.getDoc().cells[SG.sel.r + ':' + SG.sel.c] || {}).s || {};
    var ic = $('btnAlign') && $('btnAlign').querySelector('.al-ic');
    if (ic) ic.className = 'al-ic ' + (alClsMap[cur.al || 'left']);
  }
  var vaCycle = ['top', 'middle', 'bottom'], vaClsMap = { top: 't', middle: 'm', bottom: 'b' };
  $('btnValign').onclick = function () {
    var cur = (SG.getDoc().cells[SG.sel.r + ':' + SG.sel.c] || {}).s || {};
    var idx = vaCycle.indexOf(cur.va || 'top');
    var next = vaCycle[(idx + 1) % 3];
    SG.applyStyle('va', next);
    this.querySelector('.va-ic').className = 'va-ic ' + vaClsMap[next];
  };
  $('btnFsUp').onclick = function () { SG.stepFont(1); };
  $('btnFsDn').onclick = function () { SG.stepFont(-1); };
  $('fsBox').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); SG.setFontSize(this.value); this.blur(); } });
  $('fsBox').addEventListener('change', function () { SG.setFontSize(this.value); });
  $('btnTypeNum').onclick = function () { SG.setType('num'); };
  $('btnDpUp').onclick = function () { SG.stepDp(1); };
  $('btnDpDn').onclick = function () { SG.stepDp(-1); };
  $('btnTypeText').onclick = function () { SG.setType('text'); };
  $('btnDB').onclick = function () { SG.linkRowDB(); };
  $('btnLockRow').onclick = function () { SG.toggleLockRows(); };
  $('btnLockCol').onclick = function () { SG.toggleLockCols(); };
  $('btnPrint').onclick = function () { window.print(); };
  $('btnKeys').onclick = function () { $('mKeys').classList.add('open'); };
  $('btnImgAdd').onclick = function () { ImgLayer.pickFile(); };
  $('btnImgSearch').onclick = function () { ImgLayer.googleSearch(); };
  // 🗃️ จัดการข้อมูล DB (Staging Manager)
  if ($('btnStaging')) $('btnStaging').onclick = function () { if (window.StagingMgr) StagingMgr.open(); };
  if ($('btnAudit')) $('btnAudit').onclick = function () { if (window.AuditWin) AuditWin.open(); };
  if ($('btnUsers')) $('btnUsers').onclick = function () { if (window.UsersWin) UsersWin.open(); };
  // บันทึก session (อุปกรณ์) ตอนโหลดโปรแกรม
  if (window.DBX && DBX.logSession) { try { DBX.logSession(DBX.currentUser() || 'admin', 'ok'); } catch (e) {} }
  // 🔌 Telegram API
  $('btnApi').onclick = function () {
    var c = APIBridge.loadCfg();
    $('apiEnabled').checked = !!c.enabled;
    $('apiUrl').value = c.url || '';
    $('apiReadTok').value = c.readToken || '';
    $('apiAdminTok').value = c.adminToken || '';
    $('apiLog').textContent = APIBridge.getLogs().slice(-12).join('\n') || '—';
    $('apiDot').className = 'api-dot ' + APIBridge.getStatus();
    $('mApi').classList.add('open');
  };
  $('apiSave').onclick = function () {
    APIBridge.saveCfg({ enabled: $('apiEnabled').checked, url: $('apiUrl').value.trim(), readToken: $('apiReadTok').value.trim(), adminToken: $('apiAdminTok').value.trim() });
    if ($('apiEnabled').checked) APIBridge.connect(); else APIBridge.disconnect();
    $('apiDot').className = 'api-dot ' + APIBridge.getStatus();
  };
  // Ctrl+S / Ctrl+P ทั่วทั้งหน้า (กัน browser dialog)
  document.addEventListener('keydown', function (e) {
    if (!(e.ctrlKey || e.metaKey)) return;
    var k = e.key.toLowerCase();
    if (k.length === 1 && !/[a-z]/.test(k) && /^Key[A-Z]$/.test(e.code || '')) k = e.code.slice(3).toLowerCase();   // รองรับแป้นไทย
    if (k === 's') { e.preventDefault(); SG.save(); stampSaved(); }
    if (k === 'p') { e.preventDefault(); window.print(); }
    if (k === 'k' || k === 'f') { var fq = $('fq'); if (fq) { e.preventDefault(); fq.focus(); fq.select(); } }
  });
  $('btnSecret').onclick = function () { var on = SG.toggleSecret(); this.classList.toggle('on', on); };


