/* device-registry-client.js — ฝั่งแอป: ต่อ Cloudflare Worker "ทะเบียนกลางอุปกรณ์"
   โหลดเป็นไฟล์ IIFE แยก (กลุ่ม E) · ต้องโหลดหลัง device-id.js (ใช้ DeviceID.id)
   ────────────────────────────────────────────────────────────────────────
   เปิด global: window.Registry
     ── การตั้งค่า ──
     Registry.cfg()                      → { url, enforce }
     Registry.setUrl(u) / Registry.setEnforce(bool)
     Registry.isRegistered()             → มี token แล้วหรือยัง
     ── เรียก Worker (คืน Promise) ──
     Registry.otpRequest({user,deviceName,deviceType}) → {ok, ref, expiresIn}
     Registry.otpVerify(code)            → {ok, token}  (เก็บ token ลงเครื่องให้อัตโนมัติ)
     Registry.check()                    → {ok} / {revoked:true}
     Registry.pushLog(event, meta)       → ส่ง log (ยิงทิ้ง ไม่รอผล)
     ── แอดมิน (ต้องมี adminKey) ──
     Registry.list(adminKey)             → {devices, pending}
     Registry.revoke(adminKey, deviceId) → {ok}
     Registry.logList(adminKey, limit)   → {logs}
     ── UI ──
     Registry.openRegister(opts)         → เปิดหน้าลงทะเบียน OTP (overlay)
     Registry.openConfig()               → เปิดหน้าตั้งค่า URL/บังคับ
   ────────────────────────────────────────────────────────────────────────
   ปลอดภัยไว้ก่อน: "บังคับลงทะเบียน" (enforce) ปิดเป็นค่าเริ่มต้น → แอปไม่ล็อกใครทันที
   คุณค่อยเปิดบังคับเองเมื่อพร้อม (Registry.setEnforce(true) หรือผ่านหน้าตั้งค่า)
*/
(function () {
  'use strict';

  // ── ค่าเริ่มต้น (URL ของ Worker ที่ deploy แล้ว) ──
  var DEFAULT_URL = 'https://tkc-registry.tkc-ai365.workers.dev/';
  var K_URL = 'xls2_reg_url', K_TOKEN = 'xls2_reg_token', K_ENFORCE = 'xls2_reg_enforce';
  var SS_CHECKED = 'xls2_reg_checked';   // กันเช็คซ้ำในเซสชันเดียว
  var PERM_CACHE = 'xls2_perm_';         // prefix cache สิทธิ์ตำแหน่งต่อ user

  function ls(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) {} }
  function toast(s) { if (window.SG && SG.toast) SG.toast(s); else if (window.toast) window.toast(s); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function url() { return (ls(K_URL, '') || DEFAULT_URL).replace(/\/?$/, '/'); }
  function token() { return ls(K_TOKEN, '') || ''; }
  function enforce() { return ls(K_ENFORCE, '') === '1'; }
  function deviceId() { return (window.DeviceID && DeviceID.id) || ''; }

  // ── เรียก Worker (POST JSON) ──
  function call(action, extra) {
    var body = {}; for (var k in extra) body[k] = extra[k]; body.action = action;
    return fetch(url(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json().catch(function () { return { error: 'ตอบกลับไม่ใช่ JSON' }; }); });
  }

  var Registry = {
    cfg: function () { return { url: url(), enforce: enforce() }; },
    setUrl: function (u) { u = String(u || '').trim(); if (u) lsSet(K_URL, u); else lsDel(K_URL); },
    setEnforce: function (b) { if (b) lsSet(K_ENFORCE, '1'); else lsDel(K_ENFORCE); },
    isRegistered: function () { return !!token(); },

    otpRequest: function (o) {
      o = o || {};
      return call('OTP_REQUEST', {
        user: o.user || (window.Auth && Auth.currentUser && Auth.currentUser()) || '',
        deviceId: deviceId(),
        deviceName: o.deviceName || (window.DeviceID && DeviceID.name()) || '',
        deviceType: o.deviceType || (window.DeviceID && DeviceID.type()) || 'shared'
      });
    },
    otpVerify: function (code) {
      return call('OTP_VERIFY', { deviceId: deviceId(), code: String(code || '').trim() })
        .then(function (res) {
          if (res && res.ok && res.token) {
            lsSet(K_TOKEN, res.token);
            try { sessionStorage.setItem(SS_CHECKED, '1'); } catch (e) {}
          }
          return res;
        });
    },
    check: function () {
      if (!token()) return Promise.resolve({ revoked: true, reason: 'ยังไม่ลงทะเบียน' });
      return call('DEVICE_CHECK', { deviceId: deviceId(), token: token() });
    },
    pushLog: function (event, meta) {
      if (!token()) return Promise.resolve({ ok: false });
      return call('LOG_PUSH', { deviceId: deviceId(), token: token(), event: event || '', meta: meta || null })
        .catch(function () { return { ok: false }; });
    },
    clearToken: function () { lsDel(K_TOKEN); try { sessionStorage.removeItem(SS_CHECKED); } catch (e) {} },

    // ── แอดมิน ──
    list: function (adminKey) { return call('DEVICE_LIST', { adminKey: adminKey }); },
    revoke: function (adminKey, id) { return call('DEVICE_REVOKE', { adminKey: adminKey, deviceId: id }); },
    logList: function (adminKey, limit) { return call('LOG_LIST', { adminKey: adminKey, limit: limit || 200 }); },

    // ── permission ตำแหน่ง (positions) ──
    permGet: function (adminKey) { return call('PERM_GET', { adminKey: adminKey }); },
    permSet: function (adminKey, payload) {
      payload = payload || {};
      return call('PERM_SET', { adminKey: adminKey, positions: payload.positions, userpos: payload.userpos, by: payload.by, deviceId: deviceId() });
    },
    // แอปถามสิทธิ์ของ user ที่ login → cache ในเครื่อง (ใช้ต่อแบบ sync ตอน render + ออฟไลน์)
    permResolve: function (user) {
      user = String(user || '').trim();
      return call('PERM_RESOLVE', { user: user }).then(function (res) {
        if (res && res.ok) { try { localStorage.setItem(PERM_CACHE + user, JSON.stringify({ ts: Date.now(), res: res })); } catch (e) {} }
        return res;
      }).catch(function () { return Registry.permCached(user); });   // ออฟไลน์ → ใช้ cache
    },
    permCached: function (user) {
      user = String(user || '').trim();
      try { var o = JSON.parse(localStorage.getItem(PERM_CACHE + user) || 'null'); return o ? o.res : null; } catch (e) { return null; }
    },

    openRegister: openRegister,
    openConfig: openConfig,
    // ── ข้อมูลขนาด/ชนิดสินค้า (ความสูง/กว้าง/alias) เก็บกลาง ──
    prodInfoGet: function () { return call('PRODINFO_GET', {}); },
    prodInfoSet: function (adminKey, data, by) { return call('PRODINFO_SET', { adminKey: adminKey, data: data, by: by || '', deviceId: deviceId() }); }
  };
  window.Registry = Registry;

  // ════════════════ CSS (inject ครั้งเดียว · ธีมส้มเดียวกับ auth.js) ════════════════
  function injectCss() {
    if (document.getElementById('reg-css')) return;
    var s = document.createElement('style'); s.id = 'reg-css';
    s.textContent =
      '.regov{position:fixed;inset:0;z-index:100000;background:rgba(20,16,10,.86);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;font-family:Arial,Tahoma,sans-serif;}' +
      '.regbox{width:340px;max-width:92vw;background:#fff;border-radius:18px;box-shadow:0 28px 80px rgba(0,0,0,.55);padding:26px 24px;text-align:center;box-sizing:border-box;}' +
      '.reg-logo{font-size:38px;margin-bottom:8px;}' +
      '.reg-ttl{font-size:17px;font-weight:800;color:#2a2a2a;margin-bottom:4px;}' +
      '.reg-sub{font-size:12.5px;color:#888;line-height:1.55;margin-bottom:16px;}' +
      '.reg-lbl{font-size:12px;font-weight:700;color:#666;text-align:left;margin:10px 2px 5px;}' +
      '.reg-in{width:100%;height:44px;border:1px solid #cfcfcf;border-radius:11px;padding:0 13px;font-size:15px;font-family:inherit;box-sizing:border-box;color:#222;}' +
      '.reg-in:focus{outline:2px solid #F47C20;border-color:#F47C20;}' +
      '.reg-code{text-align:center;letter-spacing:9px;font-weight:800;font-size:22px;}' +
      '.reg-seg{display:flex;gap:8px;}' +
      '.reg-seg button{flex:1;height:58px;border:1.5px solid #d8d8d8;border-radius:12px;background:#fafafa;font-family:inherit;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;color:#555;font-size:12px;font-weight:600;transition:.12s;}' +
      '.reg-seg button .ic{font-size:20px;}' +
      '.reg-seg button.on{border-color:#F47C20;background:#FFF3E6;color:#C75B00;box-shadow:0 4px 14px rgba(244,124,32,.22);}' +
      '.reg-msg{min-height:18px;font-size:12px;margin:10px 0 4px;}' +
      '.reg-msg.err{color:#C0392B;}.reg-msg.ok{color:#1F8A4C;}.reg-msg.wait{color:#999;}' +
      '.reg-go{width:100%;height:48px;border:none;border-radius:12px;background:#F47C20;color:#fff;font-size:15px;font-weight:800;font-family:inherit;cursor:pointer;margin-top:6px;}' +
      '.reg-go:hover{background:#e06f12;}.reg-go:disabled{opacity:.5;cursor:default;}' +
      '.reg-ghost{width:100%;height:38px;border:none;background:none;color:#999;font-size:12px;font-family:inherit;cursor:pointer;margin-top:8px;text-decoration:underline;}' +
      '.reg-ref{font-size:11px;color:#aaa;margin-top:12px;word-break:break-all;}' +
      '.reg-chip{position:fixed;right:14px;bottom:14px;z-index:9000;background:#fff;border:1.5px solid #F47C20;color:#C75B00;border-radius:999px;padding:8px 14px;font:600 12px/1 Arial,Tahoma,sans-serif;cursor:pointer;box-shadow:0 6px 18px rgba(244,124,32,.3);display:flex;align-items:center;gap:6px;}' +
      '.reg-chip:hover{background:#FFF3E6;}' +
      '.reg-x{position:absolute;top:14px;right:16px;border:none;background:none;font-size:20px;color:#bbb;cursor:pointer;line-height:1;}' +
      'body.dark .regbox{background:#262626;}body.dark .reg-ttl{color:#eee;}body.dark .reg-in{background:#333;border-color:#555;color:#eee;}body.dark .reg-seg button{background:#2e2e2e;border-color:#555;color:#bbb;}';
    document.head.appendChild(s);
  }

  var ov = null, ovBlocking = false;
  function closeOv() { if (ov) { ov.remove(); ov = null; } ovBlocking = false; }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && ov && !ovBlocking) closeOv(); }, true);

  // ════════════════ หน้าลงทะเบียน OTP ════════════════
  // opts.blocking = true → ปิดเองไม่ได้ (บังคับลงทะเบียน) · opts.revoked = true → ขึ้นข้อความถูกเพิกถอน
  function openRegister(opts) {
    opts = opts || {};
    injectCss();
    closeOv();
    ovBlocking = !!opts.blocking;
    var d = document.createElement('div'); d.className = 'regov';
    var step = 1, lastRef = '';

    function render() {
      if (step === 1) {
        d.innerHTML =
          '<div class="regbox">' +
          (opts.blocking ? '' : '<button class="reg-x" id="rX">×</button>') +
          '<div class="reg-logo">📱</div>' +
          '<div class="reg-ttl">ลงทะเบียนอุปกรณ์</div>' +
          '<div class="reg-sub">' +
          (opts.revoked
            ? '⚠️ อุปกรณ์นี้ถูกเพิกถอนสิทธิ์<br>กรุณาลงทะเบียนใหม่เพื่อเข้าใช้งาน'
            : 'เครื่องนี้ยังไม่ได้ลงทะเบียน<br>ขอรหัส OTP จากแอดมินเพื่อเปิดใช้งาน') +
          '</div>' +
          '<div class="reg-lbl">ชื่อผู้ใช้ / พนักงาน</div>' +
          '<input class="reg-in" id="rUser" placeholder="เช่น สมชาย" autocomplete="off" value="' + esc((window.Auth && Auth.currentUser && Auth.currentUser()) || '') + '">' +
          '<div class="reg-lbl">ชื่ออุปกรณ์</div>' +
          '<input class="reg-in" id="rName" placeholder="เช่น เครื่องหน้าร้าน" autocomplete="off" value="' + esc((window.DeviceID && DeviceID.name()) || '') + '">' +
          '<div class="reg-lbl">ประเภทอุปกรณ์</div>' +
          '<div class="reg-seg">' +
          '<button type="button" data-t="shared" class="on"><span class="ic">🏪</span>เครื่องของร้าน<br>(หลายคนใช้)</button>' +
          '<button type="button" data-t="bound"><span class="ic">📲</span>เครื่องส่วนตัว<br>(ผูกคนเดียว)</button>' +
          '</div>' +
          '<div class="reg-msg" id="rMsg"></div>' +
          '<button class="reg-go" id="rGo">ขอรหัส OTP</button>' +
          '</div>';
        var segType = 'shared';
        var segs = d.querySelectorAll('.reg-seg button');
        segs.forEach(function (b) {
          b.onclick = function () { segs.forEach(function (x) { x.classList.remove('on'); }); b.classList.add('on'); segType = b.getAttribute('data-t'); };
        });
        var msg = d.querySelector('#rMsg'), go = d.querySelector('#rGo');
        if (d.querySelector('#rX')) d.querySelector('#rX').onclick = closeOv;
        setTimeout(function () { d.querySelector('#rUser').focus(); }, 50);
        go.onclick = function () {
          var user = d.querySelector('#rUser').value.trim();
          var name = d.querySelector('#rName').value.trim();
          if (!user) { msg.className = 'reg-msg err'; msg.textContent = 'กรอกชื่อผู้ใช้'; return; }
          if (window.DeviceID) { DeviceID.setName(name); DeviceID.setType(segType); }
          go.disabled = true; msg.className = 'reg-msg wait'; msg.textContent = 'กำลังขอรหัส…';
          Registry.otpRequest({ user: user, deviceName: name, deviceType: segType }).then(function (res) {
            go.disabled = false;
            if (res && res.ok) { lastRef = res.ref || deviceId(); step = 2; render(); }
            else { msg.className = 'reg-msg err'; msg.textContent = '❌ ' + ((res && res.error) || 'ขอรหัสไม่สำเร็จ'); }
          }).catch(function (e) {
            go.disabled = false; msg.className = 'reg-msg err'; msg.textContent = '❌ ต่อเซิร์ฟเวอร์ไม่ได้ (' + (e && e.message || e) + ')';
          });
        };
      } else {
        d.innerHTML =
          '<div class="regbox">' +
          (opts.blocking ? '' : '<button class="reg-x" id="rX">×</button>') +
          '<div class="reg-logo">🔑</div>' +
          '<div class="reg-ttl">ใส่รหัส OTP</div>' +
          '<div class="reg-sub">แอดมินจะเห็นรหัส 6 หลักในระบบจัดการอุปกรณ์<br>(รหัสมีอายุ 3 นาที)</div>' +
          '<input class="reg-in reg-code" id="rCode" type="text" inputmode="numeric" maxlength="6" placeholder="••••••" autocomplete="off">' +
          '<div class="reg-msg" id="rMsg"></div>' +
          '<button class="reg-go" id="rGo">ยืนยันรหัส</button>' +
          '<button class="reg-ghost" id="rBack">← ขอรหัสใหม่</button>' +
          '<div class="reg-ref">รหัสอ้างอิงอุปกรณ์: ' + esc(lastRef) + '</div>' +
          '</div>';
        var code = d.querySelector('#rCode'), msg = d.querySelector('#rMsg'), go = d.querySelector('#rGo');
        if (d.querySelector('#rX')) d.querySelector('#rX').onclick = closeOv;
        d.querySelector('#rBack').onclick = function () { step = 1; render(); };
        setTimeout(function () { code.focus(); }, 50);
        function submit() {
          var c = code.value.trim();
          if (!/^\d{6}$/.test(c)) { msg.className = 'reg-msg err'; msg.textContent = 'รหัสต้องเป็นตัวเลข 6 หลัก'; return; }
          go.disabled = true; msg.className = 'reg-msg wait'; msg.textContent = 'กำลังยืนยัน…';
          Registry.otpVerify(c).then(function (res) {
            go.disabled = false;
            if (res && res.ok) {
              msg.className = 'reg-msg ok'; msg.textContent = '✅ ลงทะเบียนสำเร็จ!';
              if (window.UsageLog) UsageLog.push('register', { type: (window.DeviceID && DeviceID.type()) });
              setTimeout(function () { closeOv(); toast('✅ ลงทะเบียนอุปกรณ์สำเร็จ'); if (opts.onDone) opts.onDone(); }, 700);
            } else { msg.className = 'reg-msg err'; msg.textContent = '❌ ' + ((res && res.error) || 'รหัสไม่ถูกต้อง'); code.value = ''; code.focus(); }
          }).catch(function (e) {
            go.disabled = false; msg.className = 'reg-msg err'; msg.textContent = '❌ ต่อเซิร์ฟเวอร์ไม่ได้';
          });
        }
        go.onclick = submit;
        code.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); submit(); } });
      }
    }
    render();
    document.body.appendChild(d); ov = d;
  }

  // ════════════════ หน้าตั้งค่า (URL + บังคับลงทะเบียน) ════════════════
  function openConfig() {
    injectCss();
    closeOv();
    var c = Registry.cfg();
    var d = document.createElement('div'); d.className = 'regov';
    d.innerHTML =
      '<div class="regbox" style="text-align:left;">' +
      '<button class="reg-x" id="rX">×</button>' +
      '<div style="text-align:center;"><div class="reg-logo">⚙️</div>' +
      '<div class="reg-ttl">ตั้งค่าทะเบียนอุปกรณ์</div></div>' +
      '<div class="reg-lbl">URL ของเซิร์ฟเวอร์ (Worker)</div>' +
      '<input class="reg-in" id="cUrl" value="' + esc(c.url) + '" autocomplete="off">' +
      '<label style="display:flex;align-items:center;gap:10px;margin:16px 2px 4px;cursor:pointer;font-size:13.5px;color:#444;font-weight:600;">' +
      '<input type="checkbox" id="cEnf" style="width:18px;height:18px;" ' + (c.enforce ? 'checked' : '') + '>' +
      'บังคับลงทะเบียนก่อนเข้าแอป</label>' +
      '<div class="reg-sub" style="margin:4px 2px 0;">เปิด = ทุกเครื่องต้องผ่าน OTP ก่อนใช้งาน · ปิด = ไม่ล็อก (โหมดทดสอบ)</div>' +
      '<div class="reg-msg" id="cMsg"></div>' +
      '<button class="reg-go" id="cSave">บันทึก</button>' +
      '<button class="reg-ghost" id="cReg">📱 ลงทะเบียนเครื่องนี้เดี๋ยวนี้</button>' +
      (Registry.isRegistered() ? '<button class="reg-ghost" id="cUnreg" style="color:#C0392B;">ล้าง token เครื่องนี้ (ทดสอบ)</button>' : '') +
      '<div class="reg-ref">deviceId: ' + esc(deviceId()) + ' · ' + (Registry.isRegistered() ? 'ลงทะเบียนแล้ว ✅' : 'ยังไม่ลงทะเบียน') + '</div>' +
      '</div>';
    d.querySelector('#rX').onclick = closeOv;
    d.querySelector('#cSave').onclick = function () {
      Registry.setUrl(d.querySelector('#cUrl').value);
      Registry.setEnforce(d.querySelector('#cEnf').checked);
      var m = d.querySelector('#cMsg'); m.className = 'reg-msg ok'; m.textContent = '✅ บันทึกแล้ว';
      toast('⚙️ บันทึกการตั้งค่าทะเบียนอุปกรณ์');
    };
    d.querySelector('#cReg').onclick = function () { openRegister({ onDone: openConfig }); };
    if (d.querySelector('#cUnreg')) d.querySelector('#cUnreg').onclick = function () {
      Registry.clearToken(); closeOv(); toast('🗑️ ล้าง token แล้ว'); refreshChip();
    };
    document.body.appendChild(d); ov = d;
  }

  // ════════════════ chip มุมล่างขวา (เชิญลงทะเบียน ตอนยังไม่ได้ทำ และไม่ได้บังคับ) ════════════════
  var chip = null;
  // ปุ่ม "ลงทะเบียนอุปกรณ์" ย้ายเข้าเมนู ⋯ (#btnDeviceReg) แทน chip ลอยมุมล่างขวา (ไม่ได้ใช้บ่อย)
  function refreshChip() {
    if (chip) { chip.remove(); chip = null; }            // เก็บ chip ลอยเดิมทิ้ง (ถ้ามี)
    var btn = document.getElementById('btnDeviceReg');
    if (!btn) return;
    var reg = Registry.isRegistered();
    var tx = btn.querySelector('.tx'); if (tx) tx.textContent = reg ? 'อุปกรณ์ (ลงทะเบียนแล้ว)' : 'ลงทะเบียนอุปกรณ์';
    btn.title = reg ? 'อุปกรณ์ลงทะเบียนแล้ว — กดดูสถานะ/ตั้งค่า' : 'ลงทะเบียนเครื่องนี้กับทะเบียนกลาง';
    btn.onclick = function () { if (Registry.isRegistered()) openConfig(); else openRegister({ onDone: refreshChip }); };
    btn.oncontextmenu = function (e) { e.preventDefault(); openConfig(); };
  }

  // ════════════════ boot gate ════════════════
  function boot() {
    refreshChip();                                       // ผูกปุ่มในเมนู ⋯ เสมอ (เลิกใช้ chip ลอย)
    if (!enforce()) return;                              // ไม่บังคับ → ลงทะเบียนผ่านเมนูเมื่อพร้อม
    if (!Registry.isRegistered()) { openRegister({ blocking: true, onDone: boot }); return; }
    // บังคับ + มี token → เช็คกับ server (กันเช็คซ้ำในเซสชัน)
    try { if (sessionStorage.getItem(SS_CHECKED) === '1') return; } catch (e) {}
    Registry.check().then(function (res) {
      if (res && res.revoked) {
        Registry.clearToken();
        openRegister({ blocking: true, revoked: true, onDone: boot });
      } else {
        try { sessionStorage.setItem(SS_CHECKED, '1'); } catch (e) {}
        Registry.pushLog('open', { standalone: window.matchMedia && window.matchMedia('(display-mode: standalone)').matches });
      }
    }).catch(function () { /* server ล่ม → ไม่ล็อก (กันแอปใช้ไม่ได้ตอนเน็ตมีปัญหา) */ });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
