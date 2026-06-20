/* [2/7] เมนู ⋯ เครื่องมือเพิ่มเติม (จัดกลุ่ม/badge)
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดตามลำดับ 1→7 ก่อน price-update.js */
  // ⋯ เครื่องมือเพิ่มเติม — badge นับจำนวน + จัดกลุ่มตามหมวดหมู่
  var MORE_CATS = [
    ['ไฟล์', ['btnQuickSave', 'btnSaveAs', 'btnVersions', 'btnSync', 'btnPrint']],
    ['เลิกทำ/ทำซ้ำ', ['btnUndo', 'btnRedo']],
    ['แถว / คอลัมน์', ['btnAddSize', 'btnDelSize', 'btnAddModel', 'btnDelRow']],
    ['จัดรูปแบบ', ['btnBold', 'btnItalic', 'btnUnder', 'btnAlign', 'btnValign', 'btnFsUp', 'btnFsDn', 'btnFill', 'btnFont', 'btnBorder', 'btnMerge']],
    ['ตัวเลข / ข้อมูล', ['btnTypeNum', 'btnTypeText', 'btnDpUp', 'btnDpDn', 'btnDB']],
    ['ซ่อน / ล็อก', ['btnLockRow', 'btnLockCol', 'btnSecret']],
    ['มุมมอง', ['btnMode', 'btnTheme', 'btnKeys']],
    ['รูปภาพ', ['btnImgAdd', 'btnImgSearch']],
    ['เชื่อมต่อ', ['btnApi', 'btnStaging', 'btnAudit', 'btnUsers', 'btnDeviceReg']]
  ];
  function moreCatOf(id) { for (var i = 0; i < MORE_CATS.length; i++) { if (MORE_CATS[i][1].indexOf(id) >= 0) return MORE_CATS[i][0]; } return 'อื่นๆ'; }
  function updateMoreBadge() {
    var n = $('morePop').querySelectorAll('.btn').length;
    var bd = $('moreBadge'); if (!bd) return;
    bd.textContent = n; bd.style.display = n ? 'flex' : 'none';
  }
  function groupMorePop() {
    var pop = $('morePop');
    var btns = [].slice.call(pop.querySelectorAll('.btn'));
    [].slice.call(pop.querySelectorAll('.lbl, .morecat')).forEach(function (h) { h.remove(); });
    var groups = {};
    btns.forEach(function (b) { var c = moreCatOf(b.id); (groups[c] = groups[c] || []).push(b); });
    var order = MORE_CATS.map(function (p) { return p[0]; }); order.push('อื่นๆ');
    order.forEach(function (name) {
      if (!groups[name]) return;
      var h = document.createElement('div'); h.className = 'morecat'; h.textContent = name;
      pop.appendChild(h);
      groups[name].forEach(function (b) { pop.appendChild(b); });
    });
    updateMoreBadge();
  }
  $('btnMore').onclick = function (e) {
    e.stopPropagation();
    $('swPop').classList.remove('open'); $('fontPop').classList.remove('open'); $('bdPop').classList.remove('open');
    if (!$('morePop').classList.contains('open')) groupMorePop();
    $('morePop').classList.toggle('open');
    placePop($('morePop'), this);
  };
  new MutationObserver(updateMoreBadge).observe($('morePop'), { childList: true });
  updateMoreBadge();
  $('morePop').addEventListener('click', function (e) {
    e.stopPropagation();
    if (e.target.closest('button.btn')) setTimeout(function () { $('morePop').classList.remove('open'); }, 120);
  });


