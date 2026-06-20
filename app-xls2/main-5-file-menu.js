/* [5/7] เมนูไฟล์ + บันทึกเป็น + เวอร์ชัน + modals
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดตามลำดับ 1→7 ก่อน price-update.js */
  // modals
  document.querySelectorAll('[data-close]').forEach(function (b) { b.onclick = function () { b.closest('.modal').classList.remove('open'); }; });
  document.querySelectorAll('.modal').forEach(function (m) { m.onclick = function (e) { if (e.target === m) m.classList.remove('open'); }; });
  $('btnFile').onclick = function (e) {
    e.stopPropagation();
    $('swPop').classList.remove('open'); $('fontPop').classList.remove('open'); $('bdPop').classList.remove('open'); $('morePop').classList.remove('open');
    $('filePop').classList.toggle('open');
    placePop($('filePop'), this);
  };
  $('filePop').onclick = function (e) { e.stopPropagation(); if (e.target.closest('button.btn')) $('filePop').classList.remove('open'); };
  $('btnQuickSave').onclick = function () { SG.save(); stampSaved(); };
  if ($('btnReload')) $('btnReload').onclick = function () {
    function doReload() { var u = location.href.split('#')[0].replace(/[?&]_r=\d+/, ''); location.href = u + (u.indexOf('?') >= 0 ? '&' : '?') + '_r=' + Date.now(); }
    var dirty = false; try { dirty = !!(SG && SG.isDirty && SG.isDirty()); } catch (e) {}
    if (dirty) { confirmDialog('รีโหลดเลยไหม?', 'ยังไม่ได้บันทึก — การแก้ที่ยังไม่เซฟจะหาย', doReload); }
    else doReload();
  };  $('btnSaveAs').onclick = function () {
    $('saveAsName').value = (SG.getDoc().name || 'ราคายาง') + ' ' + new Date().toLocaleDateString('th-TH');
    $('mSaveAs').classList.add('open');
    setTimeout(function () { $('saveAsName').focus(); $('saveAsName').select(); }, 50);
  };
  $('saveAsOk').onclick = function () {
    var nm = $('saveAsName').value.trim();
    SG.getDoc().name = nm || SG.getDoc().name;
    SG.saveAs(nm); $('mSaveAs').classList.remove('open');
    if (nm) { setFileName(nm); localStorage.setItem('xls2_savedAt', String(Date.now())); if (typeof toast === 'function') toast('✓ บันทึกเป็นไฟล์ใหม่ “' + nm + '” แล้ว — ทำงานต่อในไฟล์นี้'); }
    refresh();
  };
  $('saveAsName').addEventListener('keydown', function (e) { if (e.key === 'Enter') $('saveAsOk').click(); });
  $('btnVersions').onclick = function () { renderVersions(); $('mVersions').classList.add('open'); };
  $('btnReset').onclick = function () { confirmDialog('แทนที่ด้วยต้นฉบับ?', 'จะแทนที่ข้อมูลปัจจุบันด้วยต้นฉบับจาก Excel', function () { SG.resetFromSource(); $('mVersions').classList.remove('open'); refresh(); }); };

  function renderVersions() {
    var vs = XL2.store.loadVersions(), host = $('vList');
    if (!vs.length) { host.innerHTML = '<div class="empty">ยังไม่มีเวอร์ชันที่บันทึก</div>'; return; }
    host.innerHTML = '';
    vs.forEach(function (v) {
      var row = document.createElement('div'); row.className = 'vrow';
      row.innerHTML = '<div><div class="vn">' + XL2.esc(v.name) + '</div><div class="vt">' + new Date(v.savedAt).toLocaleString('th-TH') + '</div></div>' +
        '<div class="sp"><button class="mini" data-open>เปิด</button><button class="mini del" data-del>ลบ</button></div>';
      row.querySelector('[data-open]').onclick = function () { SG.openVersion(v.id); setFileName(v.name); localStorage.setItem('xls2_savedAt', String(v.savedAt || Date.now())); $('mVersions').classList.remove('open'); refresh(); };
      row.querySelector('[data-del]').onclick = function () { confirmDialog('ลบเวอร์ชัน?', 'ลบ “' + v.name + '” ทิ้ง', function () { XL2.store.deleteVersion(v.id); renderVersions(); }); };
      host.appendChild(row);
    });
  }


