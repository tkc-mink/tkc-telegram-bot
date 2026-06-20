/* ============================================================
   icon-kit.js — ตัวช่วยไอคอนแบบรูป (เวกเตอร์จาก Iconify) ใช้เป็นไอคอนสถานะได้
   ------------------------------------------------------------
   • โหลดเป็นสคริปต์แรก (ไม่พึ่งอะไร) → ทุกไฟล์เรียก window.IconKit ได้
   • รูปแบบค่าไอคอน:
       - อีโมจิ/สัญลักษณ์ปกติ  → เก็บเป็นข้อความเหมือนเดิม ('🟢', '✅' …)
       - ไอคอนเวกเตอร์เน็ต     → เก็บเป็น token  "ico:PREFIX:NAME"  เช่น "ico:mdi:truck-outline"
   • recolor: ไอคอนเวกเตอร์เรนเดอร์ด้วย CSS mask + background-color:currentColor
       → รับสีจากช่องสีสถานะ (style="color:#xxx" บน span ครอบ) อัตโนมัติ
   ============================================================ */
(function () {
  var API = 'https://api.iconify.design';

  function isImg(v) {
    v = String(v || '');
    return v.indexOf('ico:') === 0 || /^https?:\/\//.test(v) || v.indexOf('data:image/') === 0;
  }
  // token "ico:mdi:truck-outline" → "https://api.iconify.design/mdi/truck-outline.svg"
  function url(v) {
    v = String(v || '');
    if (v.indexOf('ico:') === 0) {
      var rest = v.slice(4);                 // "mdi:truck-outline"
      var i = rest.indexOf(':');
      if (i < 0) return '';
      var prefix = rest.slice(0, i), name = rest.slice(i + 1);
      return API + '/' + encodeURIComponent(prefix) + '/' + encodeURIComponent(name) + '.svg';
    }
    return v;   // URL/dataURL ตรง ๆ
  }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

  // คืน HTML ของไอคอน (ฝังในช่อง/ปุ่ม/เมนูได้) — emoji=ข้อความ · เวกเตอร์=<i> มาสก์ recolor ได้
  function html(v) {
    v = String(v || '');
    if (!v) return '';
    if (!isImg(v)) return esc(v) + '\uFE0E';
    var u = url(v);
    if (!u) return '';
    var q = "url('" + u.replace(/'/g, "%27") + "') center/contain no-repeat";
    return '<i class="ic-svgimg" style="-webkit-mask:' + q + ';mask:' + q + ';"></i>';
  }
  // ข้อความล้วน (สำหรับ tooltip ที่ฝังรูปไม่ได้) — emoji คืนตัวเอง · เวกเตอร์คืนว่าง
  function plain(v) { return isImg(v) ? '' : String(v || ''); }

  window.IconKit = { isImg: isImg, url: url, html: html, plain: plain, API: API };
})();
