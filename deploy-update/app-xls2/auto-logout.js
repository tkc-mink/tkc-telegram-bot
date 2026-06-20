/* auto-logout.js — ล็อกหน้าจออัตโนมัติเมื่อไม่ได้ใช้งาน (สำหรับ "เครื่องของร้าน")
   เปิด global: window.AutoLogout = { minutes(), setMinutes(n), enabled(), setEnabled(b), ping() }
   หลักการ:
     • ทำงานเมื่อ: ตั้ง PIN แล้ว (Auth.isSet) — ไม่มี PIN = ไม่มีอะไรให้ล็อก
     • ค่าเริ่มต้น 5 นาที · ปรับได้ (เก็บ xls2_autologout_min) · 0 = ปิด
     • นับถอยหลังจาก "การกระทำล่าสุด" (คลิก/พิมพ์/แตะ/เลื่อน) — มีกิจกรรม = รีเซ็ตนาฬิกา
     • ครบเวลา → Auth.lock() (ต้องใส่ PIN ใหม่) + บันทึก log 'auto-logout'
     • เครื่องส่วนตัว (DeviceID.type='bound') ค่าเริ่มต้น = ปิด (ปรับเปิดได้) ; เครื่องร้าน ('shared') = เปิด
*/
(function () {
  var K_MIN = 'xls2_autologout_min', K_EN = 'xls2_autologout_en';
  var DEFAULT_MIN = 5;
  var timer = null, lastActivity = Date.now();

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function minutes() { var v = parseInt(lsGet(K_MIN), 10); return isNaN(v) ? DEFAULT_MIN : v; }
  function enabledDefault() {
    // เครื่องร้าน = เปิด · เครื่องส่วนตัว = ปิด (เป็นค่าเริ่มต้น ปรับเองได้)
    try { return !(window.DeviceID && DeviceID.type && DeviceID.type() === 'bound'); } catch (e) { return true; }
  }
  function enabled() { var v = lsGet(K_EN); return v == null ? enabledDefault() : v === '1'; }

  function active() {
    return enabled() && minutes() > 0 && window.Auth && Auth.isSet && Auth.isSet();
  }

  function fire() {
    if (!active()) return;
    if (Date.now() - lastActivity < minutes() * 60000 - 250) return schedule();  // ยังไม่ถึงเวลา (กันตื่นเร็ว)
    try { if (window.UsageLog) UsageLog.push('auto-logout', { afterMin: minutes() }); } catch (e) {}
    try { Auth.lock(); } catch (e) {}
  }
  function schedule() {
    if (timer) clearTimeout(timer);
    if (!active()) return;
    var remain = minutes() * 60000 - (Date.now() - lastActivity);
    timer = setTimeout(fire, Math.max(1000, remain));
  }
  function ping() { lastActivity = Date.now(); schedule(); }

  ['mousedown', 'keydown', 'touchstart', 'wheel', 'pointerdown', 'visibilitychange'].forEach(function (ev) {
    window.addEventListener(ev, function () { if (document.visibilityState !== 'hidden') ping(); }, { passive: true, capture: true });
  });

  window.AutoLogout = {
    minutes: minutes,
    setMinutes: function (n) { n = Math.max(0, parseInt(n, 10) || 0); lsSet(K_MIN, n); ping(); return n; },
    enabled: enabled,
    setEnabled: function (b) { lsSet(K_EN, b ? '1' : '0'); ping(); },
    ping: ping
  };

  // เริ่มนับเมื่อโหลดเสร็จ
  if (document.readyState === 'complete') ping();
  else window.addEventListener('load', ping);
})();
