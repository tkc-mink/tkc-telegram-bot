/* โหมดมืด/สว่าง + สลับโหมดตอนพิมพ์ — แยกจาก index.html
   ใช้ global: $, SG */
(function () {
  function $(id) { return document.getElementById(id); }
  // 🌙/☀️ โหมดมืด-สว่าง (จำค่าไว้)
  function applyTheme(dark) {
    document.body.classList.toggle('dark', dark);
    $('themeIc').textContent = dark ? '☀️' : '🌙';
    $('btnTheme').querySelector('.tx').textContent = dark ? 'โหมดสว่าง' : 'โหมดมืด';
    try { localStorage.setItem('xls2_theme', dark ? 'dark' : 'light'); } catch (e) {}
    if (window.SG) SG.render();   // รีเรนเดอร์ให้สีคอนทราสต์ชั่วคราวทำงาน
  }
  $('btnTheme').onclick = function () { applyTheme(!document.body.classList.contains('dark')); };
  applyTheme(localStorage.getItem('xls2_theme') === 'dark');
  // พิมพ์ = สลับเป็นโหมดสว่างชั่วคราวเสมอ (กระดาษขาวอ่านชัด)
  var wasDark = false;
  window.addEventListener('beforeprint', function () {
    wasDark = document.body.classList.contains('dark');
    if (wasDark) { document.body.classList.remove('dark'); SG.render(); }
  });
  window.addEventListener('afterprint', function () {
    if (wasDark) { document.body.classList.add('dark'); SG.render(); }
  });
})();
