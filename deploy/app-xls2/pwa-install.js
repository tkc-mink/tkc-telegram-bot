/* PWA install helper — ปุ่ม "ติดตั้งแอป" + คำแนะนำสำหรับ iPhone
   • Android/Chrome: ดักเหตุการณ์ beforeinstallprompt → โชว์ปุ่ม → กดแล้วติดตั้ง
   • iOS/Safari: ไม่มี prompt อัตโนมัติ → โชว์วิธี "แชร์ → เพิ่มลงในหน้าจอโฮม"
   • ซ่อนเองเมื่อ: ติดตั้งแล้ว (standalone) หรือผู้ใช้กดปิด (จำ 30 วัน) */
(function () {
  var DISMISS_KEY = 'xls2_pwa_dismiss';
  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  }
  function dismissedRecently() {
    try { var t = +localStorage.getItem(DISMISS_KEY) || 0; return (Date.now() - t) < 30 * 864e5; } catch (e) { return false; }
  }
  if (isStandalone()) return;  // เปิดจากไอคอนแล้ว ไม่ต้องชวนติดตั้ง

  var deferred = null, chip = null;
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;

  function injectStyle() {
    if (document.getElementById('pwa-install-css')) return;
    var s = document.createElement('style'); s.id = 'pwa-install-css';
    s.textContent =
      '.pwa-chip{position:fixed;right:14px;bottom:14px;z-index:99999;display:flex;align-items:center;gap:9px;' +
      'background:#1a222e;color:#fff;border:1px solid #2c3a4a;border-radius:12px;padding:10px 13px;' +
      'box-shadow:0 8px 26px rgba(0,0,0,.4);font:600 13px/1.2 Kanit,Sarabun,system-ui,sans-serif;cursor:pointer;max-width:78vw}' +
      '.pwa-chip:hover{background:#222d3b}' +
      '.pwa-chip img{width:30px;height:30px;border-radius:7px;flex:0 0 30px}' +
      '.pwa-chip .pwa-tx{display:flex;flex-direction:column;gap:1px}' +
      '.pwa-chip .pwa-tx b{font-weight:700}' +
      '.pwa-chip .pwa-tx span{font-weight:400;color:#9fb0c2;font-size:11px}' +
      '.pwa-chip .pwa-x{margin-left:4px;color:#7d8ea0;font-size:18px;line-height:1;padding:0 2px}' +
      '.pwa-sheet{position:fixed;inset:0;z-index:100000;background:rgba(0,0,0,.55);display:flex;align-items:flex-end;justify-content:center}' +
      '.pwa-sheet .pwa-card{background:#1a222e;color:#fff;border-radius:16px 16px 0 0;padding:20px 20px 28px;max-width:480px;width:100%;' +
      'font:400 14px/1.55 Sarabun,system-ui,sans-serif;border-top:1px solid #2c3a4a}' +
      '.pwa-card h3{margin:0 0 12px;font:700 17px Kanit,sans-serif}' +
      '.pwa-card ol{margin:0;padding-left:20px}.pwa-card li{margin:7px 0}' +
      '.pwa-card .pwa-close{margin-top:16px;width:100%;background:#e8722e;color:#fff;border:0;border-radius:10px;padding:11px;font:700 14px Kanit,sans-serif;cursor:pointer}' +
      '.pwa-kbd{display:inline-block;background:#2c3a4a;border-radius:6px;padding:1px 7px;font-weight:700}';
    document.head.appendChild(s);
  }

  function showChip() {
    if (chip || dismissedRecently()) return;
    injectStyle();
    chip = document.createElement('div'); chip.className = 'pwa-chip';
    chip.innerHTML = '<img src="icons/icon-192.png" alt="">' +
      '<div class="pwa-tx"><b>ติดตั้งแอป</b><span>เพิ่มลงจอโฮม · ใช้ออฟไลน์ได้</span></div>' +
      '<span class="pwa-x" title="ปิด">×</span>';
    chip.querySelector('.pwa-x').addEventListener('click', function (e) {
      e.stopPropagation(); try { localStorage.setItem(DISMISS_KEY, Date.now()); } catch (er) {}
      chip.remove(); chip = null;
    });
    chip.addEventListener('click', doInstall);
    document.body.appendChild(chip);
  }

  function doInstall() {
    if (deferred) {
      deferred.prompt();
      deferred.userChoice.then(function () { deferred = null; if (chip) { chip.remove(); chip = null; } });
    } else if (isIOS) {
      showIosSheet();
    }
  }

  function showIosSheet() {
    injectStyle();
    var ov = document.createElement('div'); ov.className = 'pwa-sheet';
    ov.innerHTML = '<div class="pwa-card"><h3>📲 ติดตั้งลงไอโฟน</h3>' +
      '<ol><li>แตะปุ่ม <span class="pwa-kbd">แชร์</span> (รูปสี่เหลี่ยมมีลูกศรขึ้น) ด้านล่างของ Safari</li>' +
      '<li>เลื่อนหา <span class="pwa-kbd">เพิ่มลงในหน้าจอโฮม</span></li>' +
      '<li>แตะ <span class="pwa-kbd">เพิ่ม</span> มุมขวาบน</li></ol>' +
      '<button class="pwa-close">เข้าใจแล้ว</button></div>';
    function close() { ov.remove(); }
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    ov.querySelector('.pwa-close').addEventListener('click', close);
    document.body.appendChild(ov);
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault(); deferred = e; showChip();
  });
  window.addEventListener('appinstalled', function () {
    if (chip) { chip.remove(); chip = null; }
    try { localStorage.removeItem(DISMISS_KEY); } catch (e) {}
  });

  // iOS ไม่ยิง beforeinstallprompt → โชว์ชิปเองหลังโหลดสักครู่
  if (isIOS) setTimeout(showChip, 2500);
})();
