/* ซูม + เม้าส์ Logitech (ปุ่มโป้ง Back/Forward, Ctrl+ล้อ ซูม, ล้อคลิกซ่อนเลข) — แยกจาก index.html
   ใช้ global: $, SG */
(function () {
  function $(id) { return document.getElementById(id); }
  // zoom
  function setZ(z) { SG.setZoom(z); $('zVal').textContent = Math.round(SG.getZoom() * 100) + '%'; }
  $('zIn').onclick = function () { setZ(SG.getZoom() + 0.1); };
  $('zOut').onclick = function () { setZ(SG.getZoom() - 0.1); };

  // 🖱️ Logitech / เม้าส์ทุกรุ่น: ปุ่มข้างนิ้วโป้ง (Back/Forward) = ย้อนกลับ/ทำซ้ำ · Ctrl+ล้อเลื่อน = ซูม · ล้อเอียง (tilt wheel) = เลื่อนซ้าย-ขวา
  (function logiMouse() {
    var gw = document.getElementById('gridwrap');
    // ปุ่มโป้ง 4/5 (browser button 3=Back, 4=Forward) — กันย้อนหน้าเว็บ แล้วใช้เป็น undo/redo
    document.addEventListener('mousedown', function (e) {
      if (e.button === 3) { e.preventDefault(); SG.undo(); }
      else if (e.button === 4) { e.preventDefault(); SG.redo(); }
    });
    document.addEventListener('mouseup', function (e) { if (e.button === 3 || e.button === 4) e.preventDefault(); });
    window.addEventListener('auxclick', function (e) { if (e.button === 3 || e.button === 4) e.preventDefault(); });
    // Ctrl + ล้อเลื่อน = ซูมเข้า-ออก (กันซูมทั้งหน้าเว็บ)
    document.addEventListener('wheel', function (e) {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZ(SG.getZoom() + (e.deltaY < 0 ? 0.1 : -0.1));
    }, { passive: false });
    // ล้อเอียง/ปัดซ้ายขวา (tilt wheel ของ Logitech MX/G) — เลื่อนตารางแนวนอน (เบราว์เซอร์รองรับ deltaX อยู่แล้ว — ยืนยันว่าไม่ถูกบล็อก)
    // ปุ่มกลาง (ล้อคลิก) บนตาราง = สลับโหมดซ่อนเลข (กัน autoscroll)
    if (gw) gw.addEventListener('mousedown', function (e) {
      if (e.button === 1) { e.preventDefault(); var on = SG.toggleSecret(); $('btnSecret').classList.toggle('on', on); }
    });
  })();
})();
