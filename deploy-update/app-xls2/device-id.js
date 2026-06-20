/* device-id.js — รากฐานฝั่งจัดการอุปกรณ์ (เก็บในเครื่อง · ยังไม่ต่อ server)
   เปิด global:
     window.DeviceID = { id, name(), setName(s), type(), setType('shared'|'bound'), info() }
     window.UsageLog = { push(event, meta), all(), clear(), byUser(u) }
   หลักการ:
     • deviceId สุ่มครั้งเดียว ฝังในเครื่อง (คงที่จนกว่าจะล้าง/ถูกเพิกถอน)
     • ชื่ออุปกรณ์เดาให้อัตโนมัติจาก userAgent (แก้ได้)
     • บันทึก log เหตุการณ์ (เปิดแอป/ปลดล็อก) เก็บวนได้สูงสุด 500 รายการ
     • ออกแบบให้ "ยกขึ้น server" ภายหลังได้ทันที (โครงสร้างตรงกับ DEVICE_* endpoint ในแผน)
*/
(function () {
  var K_ID = 'xls2_device_id', K_NAME = 'xls2_device_name', K_TYPE = 'xls2_device_type', K_LOG = 'xls2_usage_log';
  var MAX_LOG = 500;

  function rndId() {
    var a = new Uint8Array(16);
    if (window.crypto && crypto.getRandomValues) crypto.getRandomValues(a);
    else for (var i = 0; i < 16; i++) a[i] = Math.floor(Math.random() * 256);
    return Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
  }
  function guessName() {
    var ua = navigator.userAgent || '';
    var os = /iphone/i.test(ua) ? 'iPhone' : /ipad/i.test(ua) ? 'iPad' : /android/i.test(ua) ? 'Android'
      : /windows/i.test(ua) ? 'Windows PC' : /mac/i.test(ua) ? 'Mac' : /linux/i.test(ua) ? 'Linux' : 'อุปกรณ์';
    var br = /edg/i.test(ua) ? 'Edge' : /chrome/i.test(ua) ? 'Chrome' : /firefox/i.test(ua) ? 'Firefox'
      : /safari/i.test(ua) ? 'Safari' : '';
    return os + (br ? ' · ' + br : '');
  }
  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  // deviceId: สร้างครั้งเดียว
  var id = lsGet(K_ID, null);
  if (!id) { id = rndId(); lsSet(K_ID, id); }

  window.DeviceID = {
    id: id,
    name: function () { return lsGet(K_NAME, '') || guessName(); },
    setName: function (s) { lsSet(K_NAME, String(s || '').trim()); },
    type: function () { return lsGet(K_TYPE, 'shared'); },         // 'shared' = เครื่องร้าน · 'bound' = เครื่องส่วนตัว
    setType: function (t) { lsSet(K_TYPE, t === 'bound' ? 'bound' : 'shared'); },
    info: function () {
      return { id: id, name: this.name(), type: this.type(),
        ua: navigator.userAgent || '', firstSeen: +lsGet('xls2_device_first', 0) || null };
    }
  };
  if (!lsGet('xls2_device_first', 0)) lsSet('xls2_device_first', Date.now());

  // ---- Usage log (ring buffer ในเครื่อง) ----
  function readLog() { try { return JSON.parse(lsGet(K_LOG, '[]')) || []; } catch (e) { return []; } }
  function writeLog(a) { lsSet(K_LOG, JSON.stringify(a.slice(-MAX_LOG))); }

  window.UsageLog = {
    push: function (event, meta) {
      var a = readLog();
      a.push({
        ts: Date.now(), event: String(event || ''),
        user: (window.Auth && Auth.currentUser && Auth.currentUser()) || '',
        device: id, deviceName: window.DeviceID.name(), meta: meta || null
      });
      writeLog(a);
    },
    all: function () { return readLog().slice().reverse(); },        // ใหม่สุดก่อน
    byUser: function (u) { return readLog().filter(function (r) { return r.user === u; }).reverse(); },
    clear: function () { lsSet(K_LOG, '[]'); }
  };

  // บันทึกเหตุการณ์ "เปิดแอป" (กันซ้ำในเซสชันเดียว)
  try {
    if (!sessionStorage.getItem('xls2_logged_open')) {
      sessionStorage.setItem('xls2_logged_open', '1');
      window.UsageLog.push('open', { standalone: window.matchMedia('(display-mode: standalone)').matches });
    }
  } catch (e) {}
})();
