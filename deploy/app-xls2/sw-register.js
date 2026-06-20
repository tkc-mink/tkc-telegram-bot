/* ลงทะเบียน Service Worker — โหลดไฟล์ล่าสุดอัตโนมัติ (ไม่ต้องกด Ctrl+Shift+R) + เปิดออฟไลน์ได้
   แยกจาก index.html เพื่อให้หน้า HTML ไม่มี JS ฝังในตัว */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('sw.js').catch(function () {});
  });
}
