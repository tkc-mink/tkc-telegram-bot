/* ============================================================
   users-win.js — ขั้น9: หน้าต่างจัดการผู้ใช้ + สิทธิ์ + ประวัติอุปกรณ์
   Permission Layer ครอบ login เดิม · เก็บฝั่งเรา · exposes window.UsersWin
   ============================================================ */
(function () {
  var el = null, tab = 'perms';
  var PERM_LABEL = {
    viewSheet: 'ดูตาราง', editPrice: 'แก้ราคา', pushDB: 'ส่งราคาเข้า DB', linkDB: 'ผูกลิงก์ DB',
    manageStaging: 'จัดการชั้นกลาง', manageIcons: 'จัดการไอคอน', manageUsers: 'จัดการผู้ใช้', viewAudit: 'ดูประวัติ', schedule: 'ตั้งเวลาอัปเดต'
  };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtTs(ts) { var d = new Date(ts); return d.toLocaleDateString('th-TH') + ' ' + d.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }); }

  function open() {
    if (!window.DBX) { window.AppDialog ? AppDialog.alert('ผิดพลาด', 'ยังไม่มีฐานข้อมูล (DBX)') : alert('ยังไม่มีฐานข้อมูล (DBX)'); return; }
    if (!el) { el = document.createElement('div'); el.className = 'usr-overlay'; document.body.appendChild(el); bindOnce(); }
    el.style.display = 'flex'; render();
    if (window.PopupStack) PopupStack.push(el, close);
  }
  function close() { if (el) { el.style.display = 'none'; if (window.PopupStack) PopupStack.remove(el); } }

  function knownUsers() {
    var u = {}; var cur = DBX.currentUser(); if (cur) u[cur] = 1;
    Object.keys(DBX.permAll()).forEach(function (k) { u[k] = 1; });
    DBX.sessionLog().forEach(function (s) { if (s.user) u[s.user] = 1; });
    // ดึงจากระบบ login เดิมถ้ามี
    try { var ls = JSON.parse(localStorage.getItem('xls2_users') || '[]'); if (Array.isArray(ls)) ls.forEach(function (x) { if (x && (x.name || x.user)) u[x.name || x.user] = 1; }); } catch (e) {}
    var arr = Object.keys(u); if (!arr.length) arr = ['admin'];
    return arr;
  }

  function render() {
    el.innerHTML =
      '<div class="usr-win">' +
        '<div class="usr-head"><span>👤 ผู้ใช้ · สิทธิ์ · อุปกรณ์ (Permission Layer — เก็บฝั่งเรา ไม่แตะระบบ login เดิม)</span><span class="usr-x">✕</span></div>' +
        '<div class="usr-tabs">' +
          '<button class="usr-tab' + (tab === 'perms' ? ' on' : '') + '" data-tab="perms">🔑 ผู้ใช้ & สิทธิ์</button>' +
          '<button class="usr-tab' + (tab === 'devices' ? ' on' : '') + '" data-tab="devices">💻 ประวัติอุปกรณ์</button>' +
          '<button class="usr-tab" id="usrCentral" style="margin-left:auto;color:#C75B00;">🛡️ ระบบกลาง (Worker) ▸</button>' +
        '</div>' +
        '<div class="usr-bodywrap"><div class="usr-body"></div></div>' +
        '<div class="usr-foot"><span class="usr-note">⚠️ ความปลอดภัยจริงต้องตรวจสิทธิ์ที่เซิร์ฟเวอร์ — ชั้นนี้คุมการแสดงผล/การทำงานฝั่งหน้าจอ</span></div>' +
      '</div>';
    paint();
  }

  function paint() {
    var body = el.querySelector('.usr-body');
    if (tab === 'perms') {
      var users = knownUsers(), cur = DBX.currentUser();
      var permCols = DBX.PERM_KEYS.map(function (k) { return '<th title="' + esc(PERM_LABEL[k] || k) + '">' + esc(PERM_LABEL[k] || k) + '</th>'; }).join('');
      body.innerHTML = '<div class="usr-curwrap">ผู้ใช้ปัจจุบัน: <select class="usr-curuser">' +
        users.map(function (u) { return '<option' + (u === cur ? ' selected' : '') + '>' + esc(u) + '</option>'; }).join('') +
        '</select> <input class="usr-adduser" placeholder="+ เพิ่มชื่อผู้ใช้"><button class="btn usr-addbtn">เพิ่ม</button></div>' +
        '<table class="usr-table"><thead><tr><th>ผู้ใช้</th><th>บทบาท</th>' + permCols + '</tr></thead><tbody>' +
        users.map(function (u) {
          var p = DBX.permGet(u);
          var cells = DBX.PERM_KEYS.map(function (k) { return '<td class="usr-pc"><input type="checkbox" data-user="' + esc(u) + '" data-perm="' + k + '"' + (p.perms[k] ? ' checked' : '') + '></td>'; }).join('');
          return '<tr><td class="usr-name">' + esc(u) + (u === cur ? ' <span class="usr-you">คุณ</span>' : '') + '</td>' +
            '<td><select class="usr-role" data-user="' + esc(u) + '">' +
              ['admin', 'manager', 'user'].map(function (r) { return '<option' + (p.role === r ? ' selected' : '') + '>' + r + '</option>'; }).join('') +
            '</select></td>' + cells + '</tr>';
        }).join('') + '</tbody></table>';
    } else {
      var logs = DBX.sessionLog();
      body.innerHTML = logs.length ? '<table class="usr-table"><thead><tr><th>เวลา</th><th>ผู้ใช้</th><th>บทบาท</th><th>อุปกรณ์/OS</th><th>จอ</th><th>ภาษา</th><th>โซนเวลา</th><th>ผล</th></tr></thead><tbody>' +
        logs.map(function (s) {
          return '<tr><td class="usr-ts">' + fmtTs(s.ts) + '</td><td>' + esc(s.user || '') + '</td><td>' + esc(s.role || '') + '</td>' +
            '<td class="usr-dev" title="' + esc(s.ua || '') + '">' + esc(s.device || '') + '</td><td>' + esc(s.screen || '') + '</td><td>' + esc(s.lang || '') + '</td><td>' + esc(s.tz || '') + '</td>' +
            '<td>' + (s.result === 'ok' ? '✅' : '⚠️ ' + esc(s.result)) + '</td></tr>';
        }).join('') + '</tbody></table>' : '<div class="usr-empty">— ยังไม่มีประวัติการเข้าใช้ —</div>';
    }
  }

  function bindOnce() {
    el.addEventListener('click', function (e) {
      if (e.target.closest('.usr-x') || e.target === el) { close(); return; }
      if (e.target.closest('#usrCentral')) { if (window.AdminCentral) AdminCentral.open(); else (window.SG && SG.toast ? SG.toast('ยังไม่มีโมดูลระบบกลาง') : 0); return; }
      var t = e.target.closest('.usr-tab'); if (t) { tab = t.dataset.tab; render(); return; }
      if (e.target.closest('#usrCentral')) { if (window.AdminCentral) AdminCentral.open(); else (window.SG && SG.toast ? SG.toast('ยังไม่มีโมดูลระบบกลาง') : 0); return; }
      if (e.target.closest('.usr-addbtn')) {
        var inp = el.querySelector('.usr-adduser'); var v = (inp.value || '').trim();
        if (v) { DBX.permSetRole(v, 'user'); paint(); } return;
      }
    });
    el.addEventListener('change', function (e) {
      if (e.target.classList.contains('usr-curuser')) { DBX.setCurrentUser(e.target.value); updateBadge(); return; }
      if (e.target.classList.contains('usr-role')) { DBX.permSetRole(e.target.dataset.user, e.target.value); paint(); return; }
      if (e.target.dataset && e.target.dataset.perm) {
        var u = e.target.dataset.user, p = DBX.permGet(u); var perms = Object.assign({}, p.perms);
        perms[e.target.dataset.perm] = e.target.checked; DBX.permSet(u, { perms: perms });
      }
    });
  }
  function updateBadge() {
    var b = document.getElementById('curUserName'); if (b) b.textContent = DBX.currentUser() || 'admin';
  }

  window.UsersWin = { open: open, close: close };
})();
