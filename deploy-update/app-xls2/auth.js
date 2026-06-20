/* ระบบล็อกหน้าจอด้วย PIN พนักงาน — โมดูลแยก (self-contained: รวม CSS ในตัว)
   เปิด global: window.Auth { isSet, currentUser, openSetup, lock, clearPin, unlockKey }
   หลักการ:
   • เปิดใช้เมื่อ "ตั้ง PIN" แล้วเท่านั้น — ยังไม่ตั้ง = แอปทำงานปกติ ไม่ล็อก (มีชิป "ตั้ง PIN" มุมจอให้กดเปิดใช้)
   • PIN ไม่เก็บตรงๆ — เก็บเป็น SHA-256(salt|pin) + salt สุ่ม
   • ปลดล็อกแล้วจำใน sessionStorage (รีเฟรชในเซสชันไม่ถามซ้ำ · ปิดแท็บ/เปิดใหม่ = ถามใหม่)
   • unlockKey() = คีย์ที่ได้จาก PIN (อยู่ใน RAM หลังปลดล็อก) ใช้เข้ารหัส snapshot ออฟไลน์ภายหลัง */
(function () {
  var LSK_PIN = 'xls2_auth_pin', LSK_SALT = 'xls2_auth_salt', LSK_USER = 'xls2_auth_user', SS_OK = 'xls2_auth_session', SS_SKIP = 'xls2_auth_skip';
  var keyInRam = null;

  function hex(buf) { return [].map.call(new Uint8Array(buf), function (b) { return ('0' + b.toString(16)).slice(-2); }).join(''); }
  function sha(str) {
    if (!(window.crypto && crypto.subtle)) return Promise.resolve('plain:' + str);   // fallback (เครื่องเก่า/ไม่ใช่ https)
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(hex);
  }
  function rndSalt() { var a = new Uint8Array(8); (window.crypto || {}).getRandomValues ? crypto.getRandomValues(a) : a.forEach(function (_, i) { a[i] = Math.floor(Math.random() * 256); }); return hex(a.buffer); }
  function isSet() { return !!localStorage.getItem(LSK_PIN); }
  function currentUser() { return localStorage.getItem(LSK_USER) || ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function setPin(user, pin) {
    var salt = rndSalt();
    return sha(salt + '|' + pin).then(function (h) {
      try { localStorage.setItem(LSK_SALT, salt); localStorage.setItem(LSK_PIN, h); localStorage.setItem(LSK_USER, user || ''); sessionStorage.setItem(SS_OK, '1'); } catch (e) {}
      return sha('k|' + salt + '|' + pin).then(function (k) { keyInRam = k; });
    });
  }
  function verify(pin) {
    var salt = localStorage.getItem(LSK_SALT) || '';
    return sha(salt + '|' + pin).then(function (h) {
      if (h === localStorage.getItem(LSK_PIN)) { try { sessionStorage.setItem(SS_OK, '1'); } catch (e) {} return sha('k|' + salt + '|' + pin).then(function (k) { keyInRam = k; return true; }); }
      return false;
    });
  }
  function clearPin() { [LSK_PIN, LSK_SALT, LSK_USER].forEach(function (k) { try { localStorage.removeItem(k); } catch (e) {} }); try { sessionStorage.removeItem(SS_OK); } catch (e) {} keyInRam = null; removeChip(); }

  // ---------- styles (inject once) ----------
  function injectCss() {
    if (document.getElementById('auth-css')) return;
    var s = document.createElement('style'); s.id = 'auth-css';
    s.textContent =
      '.authov{position:fixed;inset:0;z-index:99999;background:rgba(20,16,10,.82);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;font-family:Arial,Tahoma,sans-serif;}' +
      '.authbox{width:300px;max-width:92vw;background:#fff;border-radius:16px;box-shadow:0 24px 70px rgba(0,0,0,.5);padding:24px 22px;text-align:center;}' +
      '.auth-logo{font-size:34px;margin-bottom:6px;}' +
      '.auth-ttl{font-size:15px;font-weight:800;color:#333;margin-bottom:14px;}' +
      '.auth-user{font-size:13px;color:#777;margin-bottom:10px;min-height:18px;}' +
      '.auth-in{width:100%;height:42px;border:1px solid #cfcfcf;border-radius:10px;padding:0 12px;font-size:15px;font-family:inherit;margin-bottom:10px;box-sizing:border-box;}' +
      '.auth-in:focus{outline:2px solid #F47C20;border-color:#F47C20;}' +
      '.auth-pin{text-align:center;letter-spacing:6px;font-weight:700;}' +
      '.auth-msg{min-height:18px;font-size:12px;color:#C0392B;margin-bottom:8px;}' +
      '.auth-go{width:100%;height:44px;border:none;border-radius:10px;background:#F47C20;color:#fff;font-size:15px;font-weight:800;font-family:inherit;cursor:pointer;}' +
      '.auth-go:hover{background:#e06f12;}' +
      '.auth-skip{width:100%;height:34px;border:none;background:none;color:#999;font-size:12px;font-family:inherit;cursor:pointer;margin-top:8px;text-decoration:underline;}' +
      '.auth-chip{position:fixed;left:14px;bottom:14px;z-index:9000;background:#fff;border:1.5px solid #F47C20;color:#C75B00;border-radius:999px;padding:7px 13px;font:600 12px/1 Arial,Tahoma,sans-serif;cursor:pointer;box-shadow:0 6px 18px rgba(244,124,32,.3);}' +
      '.auth-chip:hover{background:#FFF3E6;}' +
      'body.dark .authbox{background:#262626;}body.dark .auth-ttl{color:#eee;}body.dark .auth-in{background:#333;border-color:#555;color:#eee;}';
    document.head.appendChild(s);
  }

  var ov = null;
  function showLock(mode) {
    injectCss();
    if (ov) ov.remove();
    var setup = mode === 'setup';
    var d = document.createElement('div'); d.className = 'authov';
    d.innerHTML = '<div class="authbox">' +
      '<div class="auth-logo">🔒</div>' +
      '<div class="auth-ttl">' + (setup ? 'ตั้งรหัส PIN พนักงาน' : 'ใส่รหัส PIN เพื่อเข้าใช้งาน') + '</div>' +
      (setup ? '<input class="auth-in" id="authUser" placeholder="ชื่อพนักงาน" autocomplete="off">' : '<div class="auth-user">' + (currentUser() ? ('👤 ' + esc(currentUser())) : '') + '</div>') +
      '<input class="auth-in auth-pin" id="authPin" type="password" inputmode="numeric" maxlength="6" placeholder="PIN 4-6 หลัก" autocomplete="off">' +
      (setup ? '<input class="auth-in auth-pin" id="authPin2" type="password" inputmode="numeric" maxlength="6" placeholder="ยืนยัน PIN อีกครั้ง" autocomplete="off">' : '') +
      '<div class="auth-msg" id="authMsg"></div>' +
      '<button class="auth-go" id="authGo">' + (setup ? 'ตั้งรหัส & เข้าใช้งาน' : 'เข้าใช้งาน') + '</button>' +
      (setup ? '<button class="auth-skip" id="authSkip">ยังไม่ตั้ง (ใช้แบบไม่ล็อก)</button>' : '') +
      '</div>';
    document.body.appendChild(d); ov = d;
    var pin = d.querySelector('#authPin'), msg = d.querySelector('#authMsg');
    setTimeout(function () { (setup ? d.querySelector('#authUser') : pin).focus(); }, 50);
    function close() { d.remove(); if (ov === d) ov = null; }
    function go() {
      var p = pin.value.trim();
      if (setup) {
        var u = d.querySelector('#authUser').value.trim(), p2 = d.querySelector('#authPin2').value.trim();
        if (!u) { msg.textContent = 'กรอกชื่อพนักงาน'; return; }
        if (!/^\d{4,6}$/.test(p)) { msg.textContent = 'PIN ต้องเป็นตัวเลข 4-6 หลัก'; return; }
        if (p !== p2) { msg.textContent = 'PIN ยืนยันไม่ตรงกัน'; return; }
        setPin(u, p).then(function () { removeChip(); close(); if (window.toast) toast('🔒 ตั้ง PIN แล้ว · ครั้งต่อไปต้องใส่ PIN เข้าใช้งาน'); });
      } else {
        if (!p) return;
        verify(p).then(function (ok) { if (ok) { close(); if (window.PermEnforce) PermEnforce.refresh(); } else { msg.textContent = 'PIN ไม่ถูกต้อง'; pin.value = ''; pin.focus(); } });
      }
    }
    d.querySelector('#authGo').onclick = go;
    d.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); go(); } });
    var sk = d.querySelector('#authSkip'); if (sk) sk.onclick = function () { try { sessionStorage.setItem(SS_SKIP, '1'); } catch (e) {} close(); };
  }

  // ชิป "ตั้ง PIN" มุมล่างซ้าย (เฉพาะตอนยังไม่ตั้ง · กดเพื่อเปิดใช้ระบบล็อก)
  var chip = null;
  function showChip() {
    injectCss(); if (chip || isSet()) return;
    chip = document.createElement('button'); chip.className = 'auth-chip'; chip.textContent = '🔒 ตั้ง PIN พนักงาน';
    chip.onclick = function () { showLock('setup'); };
    document.body.appendChild(chip);
  }
  function removeChip() { if (chip) { chip.remove(); chip = null; } }

  function gate() {
    try { if (sessionStorage.getItem(SS_OK) === '1') return; } catch (e) {}
    if (isSet()) { showLock('unlock'); return; }
    try { if (sessionStorage.getItem(SS_SKIP) === '1') return; } catch (e) {}
    showChip();   // ยังไม่ตั้ง PIN → ไม่บังคับ แค่เชิญชวนให้ตั้ง
  }

  window.Auth = {
    isSet: isSet, currentUser: currentUser,
    openSetup: function () { showLock('setup'); },
    lock: function () { try { sessionStorage.removeItem(SS_OK); } catch (e) {} showLock(isSet() ? 'unlock' : 'setup'); },
    clearPin: clearPin, unlockKey: function () { return keyInRam; }
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', gate); else gate();
})();
