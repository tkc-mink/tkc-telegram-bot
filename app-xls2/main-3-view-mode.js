/* [3/7] สลับโหมดแอดมิน/ผู้ใช้ + ล็อกไฟล์ประวัติ (applyMode/enforceArchiveLock)
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดตามลำดับ 1→7 ก่อน price-update.js */
  function applyMode(m) {
    SG.clearFilter();   // ล้างตัวกรองเมื่อสลับโหมด กันตัวกรองค้างโดยมองไม่เห็น
    SG.setMode(m);
    var a = m === 'admin';
    $('btnMode').classList.toggle('on', true);
    var mb = $('btnMode');
    if (mb) { mb.querySelector('.ic').textContent = a ? '🛠️' : '👁️'; mb.querySelector('.tx').textContent = a ? 'แอดมิน' : 'ผู้ใช้'; mb.classList.toggle('usermode', !a); }
    ['btnAddSize','btnDelSize','btnAddModel','btnDelRow','btnMerge','btnBorder','btnBold','btnItalic','btnUnder','btnAlign','btnValign','btnFsUp','btnFsDn','fsBox','btnTypeNum','btnDpUp','btnDpDn','btnTypeText','btnDB','btnSync','btnLockRow','btnLockCol','btnFill','btnFont','btnUndo','btnRedo','fontFam','btnKeys'].forEach(function (id) { $(id).disabled = !a; });
    ['shAdd','shRen','shDel'].forEach(function (id) { $(id).style.display = a ? '' : 'none'; });   // ผู้ใช้สลับหมวดได้ แต่จัดการไม่ได้
    renderFltBar();
    try { window.dispatchEvent(new Event('sg-mode')); } catch (e) {}   // แจ้งแชทบอท ฯลฯ ให้ปรับสิทธิ์ตามโหมด
  }
  // 🔒 ไฟล์ประวัติ (📦 หลังอัพเดท) = อ่านอย่างเดียวถาวร — ดูย้อนหลังได้ แก้ไม่ได้ กันประวัติเพี้ยน
  function isArchivedCur() {
    var cur = XL2.store.curSheet();
    return XL2.store.sheetsList().some(function (s) { return s.id === cur && s.archived; });
  }
  var preArchiveMode = null;
  function enforceArchiveLock() {
    var locked = isArchivedCur(), mb = $('btnMode'), ab = document.getElementById('archBanner');
    if (locked) {
      if (SG.getMode() === 'admin') { preArchiveMode = 'admin'; applyMode('user'); }   // บังคับโหมดดูอย่างเดียว
      if (mb) { mb.disabled = true; mb.classList.add('locked-arch'); mb.title = '🔒 ไฟล์ประวัติ — ดูได้อย่างเดียว แก้ไขไม่ได้'; }
      if (ab) ab.style.display = 'flex';
    } else {
      if (mb) { mb.disabled = false; mb.classList.remove('locked-arch'); mb.title = 'สลับโหมด แอดมิน ⇄ ผู้ใช้ (คลิกเพื่อสลับ)'; }
      if (ab) ab.style.display = 'none';
      if (preArchiveMode === 'admin' && SG.getMode() === 'user') applyMode('admin');   // กลับหมวดปกติ → คืนโหมดแอดมินให้อัตโนมัติ
      preArchiveMode = null;
    }
  }
  $('btnMode').onclick = function () { if (isArchivedCur()) return; applyMode(SG.getMode() === 'admin' ? 'user' : 'admin'); };


