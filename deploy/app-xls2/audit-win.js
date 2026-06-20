/* ============================================================
   audit-win.js — ขั้น7: หน้าต่าง Audit & Update (แยก)
   - แท็บประวัติการแก้ไข (audit): ค้นหา/กรอง รหัส·ชื่อ·คำค้น·ช่วงวันที่
   - แท็บการอัปเดต (update): รายการที่กด/ตั้งเวลาอัปเดต + ค่า ก่อน→หลัง
   exposes window.AuditWin
   ============================================================ */
(function () {
  var el = null, tab = 'audit';
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtTs(ts) { if (!ts) return '–'; var d = new Date(ts); return d.toLocaleDateString('th-TH') + ' ' + d.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }); }
  function fmtN(v) { return (window.XL2 && XL2.fmtNum) ? XL2.fmtNum(v) : String(v); }

  function open() {
    if (!window.DBX) { window.AppDialog ? AppDialog.alert('ผิดพลาด', 'ยังไม่มีฐานข้อมูล (DBX)') : alert('ยังไม่มีฐานข้อมูล (DBX)'); return; }
    if (!el) { el = document.createElement('div'); el.className = 'aud-overlay'; document.body.appendChild(el); bindOnce(); }
    el.style.display = 'flex'; render();
    if (window.PopupStack) PopupStack.push(el, close);
  }
  function close() { if (el) { el.style.display = 'none'; if (window.PopupStack) PopupStack.remove(el); } }

  function render() {
    el.innerHTML =
      '<div class="aud-win">' +
        '<div class="aud-head"><span>🧾 ประวัติการอัปเดตราคา (Audit)</span><span class="aud-x">✕</span></div>' +
        '<div class="aud-tabs">' +
          '<button class="aud-tab' + (tab === 'audit' ? ' on' : '') + '" data-tab="audit">📋 ประวัติการแก้ไข</button>' +
          '<button class="aud-tab' + (tab === 'update' ? ' on' : '') + '" data-tab="update">🕐 การอัปเดต (ก่อน/หลัง)</button>' +
        '</div>' +
        '<div class="aud-filters">' +
          '<input class="aud-q" placeholder="🔍 ค้นหา รหัส/ชื่อ/ฟิลด์/ผู้ทำ…">' +
          '<label class="aud-dlbl">ตั้งแต่ <input type="date" class="aud-from"></label>' +
          '<label class="aud-dlbl">ถึง <input type="date" class="aud-to"></label>' +
          '<span class="aud-count"></span>' +
        '</div>' +
        '<div class="aud-bodywrap"><div class="aud-body"></div></div>' +
        '<div class="aud-foot"><span class="aud-note">เก็บฝั่งเรา · บันทึกทุกครั้งที่ส่งราคาเข้า DB (รหัส·ฟิลด์·ค่าเดิม→ใหม่·ผู้ทำ·อุปกรณ์·เวลา)</span></div>' +
      '</div>';
    paint();
  }

  function readFilter() {
    var q = (el.querySelector('.aud-q').value || '');
    var f = el.querySelector('.aud-from').value, t = el.querySelector('.aud-to').value;
    return { q: q, from: f ? new Date(f + 'T00:00:00').getTime() : 0, to: t ? new Date(t + 'T23:59:59').getTime() : 0 };
  }

  function paint() {
    var body = el.querySelector('.aud-body');
    var f = readFilter();
    if (tab === 'audit') {
      var rows = DBX.auditSearch(f);
      el.querySelector('.aud-count').textContent = rows.length + ' รายการ';
      body.innerHTML = rows.length ? '<table class="aud-table"><thead><tr>' +
        '<th>เวลา</th><th>รหัสสินค้า</th><th>ชื่อสินค้า</th><th>ฟิลด์</th><th>เดิม → ใหม่</th><th>ทิศ</th><th>ผู้ทำ</th><th>อุปกรณ์</th>' +
        '</tr></thead><tbody>' + rows.map(function (e) {
          var up = e.newV > e.oldV, dn = e.newV < e.oldV;
          var delta = (e.oldV != null) ? (up ? '▲' : dn ? '▼' : '–') : '';
          return '<tr><td class="aud-ts">' + fmtTs(e.ts) + '</td>' +
            '<td class="aud-code">' + esc(e.code13) + '</td>' +
            '<td>' + esc(e.name || '') + '</td>' +
            '<td>' + esc(fieldLabel(e.field)) + '</td>' +
            '<td class="aud-vals"><span class="aud-old">' + fmtN(e.oldV) + '</span> → <span class="aud-new">' + fmtN(e.newV) + '</span></td>' +
            '<td class="aud-dir ' + (up ? 'up' : dn ? 'dn' : '') + '">' + delta + '</td>' +
            '<td>' + esc(e.user || '') + '</td>' +
            '<td class="aud-dev">' + esc(e.device || '') + '</td></tr>';
        }).join('') + '</tbody></table>' : '<div class="aud-empty">— ยังไม่มีประวัติการแก้ไข —</div>';
    } else {
      // แท็บการอัปเดต: จัดกลุ่ม audit ตาม "รอบการกดอัปเดต" (เวลาใกล้กัน) แสดงก่อน/หลัง
      var all = DBX.auditSearch(f).slice().sort(function (a, b) { return b.ts - a.ts; });
      var batches = [];
      all.forEach(function (e) {
        var last = batches[batches.length - 1];
        if (last && Math.abs(last.ts - e.ts) < 4000) last.items.push(e);
        else batches.push({ ts: e.ts, items: [e] });
      });
      el.querySelector('.aud-count').textContent = batches.length + ' รอบอัปเดต';
      body.innerHTML = batches.length ? batches.map(function (b) {
        return '<div class="aud-batch"><div class="aud-batch-head">🕐 ' + fmtTs(b.ts) + ' · ' + b.items.length + ' รายการ · โดย ' + esc(b.items[0].user || '-') + '</div>' +
          '<table class="aud-table"><tbody>' + b.items.map(function (e) {
            var up = e.newV > e.oldV;
            return '<tr><td class="aud-code">' + esc(e.code13) + '</td><td>' + esc(e.name || '') + '</td><td>' + esc(fieldLabel(e.field)) + '</td>' +
              '<td class="aud-vals"><span class="aud-old">' + fmtN(e.oldV) + '</span> → <span class="aud-new">' + fmtN(e.newV) + '</span> <span class="aud-dir ' + (up ? 'up' : 'dn') + '">' + (up ? '▲' : '▼') + '</span></td></tr>';
          }).join('') + '</tbody></table></div>';
      }).join('') : '<div class="aud-empty">— ยังไม่มีการอัปเดต —</div>';
    }
  }
  function fieldLabel(f) { return window.DBX ? DBX.fieldLabel(f) : f; }

  function bindOnce() {
    el.addEventListener('click', function (e) {
      if (e.target.closest('.aud-x') || e.target === el) { close(); return; }
      var t = e.target.closest('.aud-tab'); if (t) { tab = t.dataset.tab; render(); return; }
    });
    el.addEventListener('input', function (e) { if (e.target.matches('.aud-q,.aud-from,.aud-to')) paint(); });
  }

  window.AuditWin = { open: open, close: close };
})();
