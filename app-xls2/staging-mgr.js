/* ============================================================
   staging-mgr.js — ขั้น6: จอจัดการชั้นกลาง (Staging & Enrichment Manager)
   ดึงสินค้าจาก DB (ผ่าน DBX) → กรอง → เติมแท็ก (setSize/ธง/หมายเหตุ) เก็บฝั่งเรา
   ไม่แตะ DB จริง · exposes window.StagingMgr
   ============================================================ */
(function () {
  var FLAGS = [
    { key: 'special', label: '⭐ ราคาพิเศษ' },
    { key: 'clearance', label: '🫗 ราคาโละ' },
    { key: 'rare', label: '💎 หายาก' },
    { key: 'needsWithdraw', label: '➕ ต้องเบิก' }
  ];
  var el = null, list = [], filtered = [];

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function open() {
    if (!window.DBX) { alert('ยังไม่มีฐานข้อมูล (DBX)'); return; }
    if (!el) { el = document.createElement('div'); el.className = 'stm-overlay'; document.body.appendChild(el); bindOnce(); }
    el.style.display = 'flex';
    render();
    if (window.PopupStack) PopupStack.push(el, close);
    DBX.search({}).then(function (arr) { list = arr || []; applyFilter(); });
  }
  function close() { if (el) { el.style.display = 'none'; if (window.PopupStack) PopupStack.remove(el); } }

  function render() {
    el.innerHTML =
      '<div class="stm-win">' +
        '<div class="stm-head"><span>🗃️ จัดการข้อมูลสินค้า (ชั้นกลาง · เก็บฝั่งเรา ไม่แตะ DB)</span><span class="stm-x">✕</span></div>' +
        '<div class="stm-filters">' +
          '<input class="stm-q" placeholder="🔍 ค้นหา รหัส/ชื่อ/ยี่ห้อ/ขนาด/รุ่น…">' +
          '<select class="stm-fgroup"><option value="">ทุกกลุ่ม</option></select>' +
          '<select class="stm-fbrand"><option value="">ทุกยี่ห้อ</option></select>' +
          '<select class="stm-fstatus"><option value="">ทุกสถานะ</option><option value="active">active</option><option value="inactive">inactive</option></select>' +
          '<select class="stm-fenrich"><option value="">ทั้งหมด</option><option value="tagged">มีแท็กแล้ว</option><option value="untagged">ยังไม่มีแท็ก</option></select>' +
          '<span class="stm-count"></span>' +
        '</div>' +
        '<div class="stm-tablewrap"><table class="stm-table"><thead><tr>' +
          '<th>รหัสสินค้า</th><th>ชื่อสินค้า</th><th>ยี่ห้อ</th><th>กลุ่ม</th><th>สถานะ</th><th>คงเหลือ</th>' +
          '<th>ชุด (setSize)</th><th>ธงสถานะ</th><th>หมายเหตุ</th><th></th>' +
        '</tr></thead><tbody class="stm-tbody"></tbody></table></div>' +
        '<div class="stm-foot">' +
          '<button class="btn stm-catrules">⚙️ กฎรายหมวดสินค้า</button>' +
          '<span class="stm-note">setSize: ค่าต่อสินค้าจะทับกฎรายหมวด · เว้นว่าง = ใช้กฎหมวด/ค่าเริ่มต้น 4</span>' +
        '</div>' +
      '</div>';
    fillFilterOptions();
  }

  function fillFilterOptions() {
    var groups = {}, brands = {};
    list.forEach(function (x) { if (x.group) groups[x.group] = 1; if (x.brandCode) brands[x.brandCode] = (x.brandName || x.brandCode); });
    var gsel = el.querySelector('.stm-fgroup'), bsel = el.querySelector('.stm-fbrand');
    Object.keys(groups).sort().forEach(function (g) { gsel.insertAdjacentHTML('beforeend', '<option value="' + esc(g) + '">กลุ่ม ' + esc(g) + '</option>'); });
    Object.keys(brands).sort().forEach(function (b) { bsel.insertAdjacentHTML('beforeend', '<option value="' + esc(b) + '">' + esc(b) + ' · ' + esc(brands[b]) + '</option>'); });
  }

  function applyFilter() {
    var q = (el.querySelector('.stm-q').value || '').toLowerCase();
    var g = el.querySelector('.stm-fgroup').value, b = el.querySelector('.stm-fbrand').value;
    var s = el.querySelector('.stm-fstatus').value, en = el.querySelector('.stm-fenrich').value;
    filtered = list.filter(function (x) {
      if (g && x.group !== g) return false;
      if (b && x.brandCode !== b) return false;
      if (s && (x.status || 'active') !== s) return false;
      var e = DBX.enrichGet(x.code13);
      var tagged = !!(e && ((e.flags && Object.keys(e.flags).some(function (k) { return e.flags[k]; })) || e.setSize != null || e.note));
      if (en === 'tagged' && !tagged) return false;
      if (en === 'untagged' && tagged) return false;
      if (q && (x.code13 + ' ' + x.name + ' ' + x.brandCode + ' ' + x.size + ' ' + x.model).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
    paintRows();
  }

  function paintRows() {
    var tb = el.querySelector('.stm-tbody');
    el.querySelector('.stm-count').textContent = filtered.length + ' / ' + list.length + ' รายการ';
    tb.innerHTML = filtered.slice(0, 300).map(function (x) {
      var e = DBX.enrichGet(x.code13) || {};
      var flags = e.flags || {};
      var ss = (e.setSize == null) ? '' : String(e.setSize);
      var flagHtml = FLAGS.map(function (f) {
        return '<label class="stm-flag' + (flags[f.key] ? ' on' : '') + '" title="' + esc(f.label) + '"><input type="checkbox" data-flag="' + f.key + '"' + (flags[f.key] ? ' checked' : '') + '>' + esc(f.label) + '</label>';
      }).join('');
      return '<tr data-code="' + esc(x.code13) + '"' + ((x.status && x.status !== 'active') ? ' class="stm-inact"' : '') + '>' +
        '<td class="stm-code">' + esc(x.code13) + '</td>' +
        '<td>' + esc(x.name) + '</td>' +
        '<td>' + esc(x.brandCode) + '</td>' +
        '<td>' + esc(x.group) + '</td>' +
        '<td>' + (x.status === 'inactive' ? '<span class="stm-badge-inact">inactive</span>' : 'active') + '</td>' +
        '<td class="stm-num">' + (x.qtyOnHand != null ? x.qtyOnHand : '–') + '</td>' +
        '<td><select class="stm-setsize"><option value=""' + (ss === '' ? ' selected' : '') + '>— (กฎหมวด)</option>' +
          '<option value="0"' + (ss === '0' ? ' selected' : '') + '>ไม่เช็คชุด</option>' +
          '<option value="2"' + (ss === '2' ? ' selected' : '') + '>2 เส้น/ชุด</option>' +
          '<option value="4"' + (ss === '4' ? ' selected' : '') + '>4 เส้น/ชุด</option>' +
          '<option value="custom"' + (ss && ss !== '0' && ss !== '2' && ss !== '4' ? ' selected' : '') + '>กำหนดเอง…</option>' +
          '</select></td>' +
        '<td class="stm-flags">' + flagHtml + '</td>' +
        '<td><input class="stm-noteinp" value="' + esc(e.note || '') + '" placeholder="หมายเหตุ…"></td>' +
        '<td>' + (Object.keys(e).length ? '<span class="stm-clear" title="ล้างแท็กสินค้านี้">✕</span>' : '') + '</td>' +
      '</tr>';
    }).join('') || '<tr><td colspan="10" class="stm-empty">ไม่พบสินค้าตามเงื่อนไข</td></tr>';
  }

  function bindOnce() {
    el.addEventListener('click', function (e) {
      if (e.target.closest('.stm-x')) { close(); return; }
      if (e.target === el) { close(); return; }
      if (e.target.closest('.stm-catrules')) { openCatRules(); return; }
      var clr = e.target.closest('.stm-clear');
      if (clr) { var code = clr.closest('tr').dataset.code; DBX.enrichClear(code); refreshGrid(); applyFilter(); return; }
    });
    el.addEventListener('input', function (e) {
      if (e.target.classList.contains('stm-q')) { applyFilter(); return; }
      var tr = e.target.closest('tr[data-code]'); if (!tr) return;
      var code = tr.dataset.code;
      if (e.target.classList.contains('stm-noteinp')) { DBX.enrichSet(code, { note: e.target.value }); refreshGrid(); }
    });
    el.addEventListener('change', function (e) {
      if (e.target.matches('.stm-fgroup,.stm-fbrand,.stm-fstatus,.stm-fenrich')) { applyFilter(); return; }
      var tr = e.target.closest('tr[data-code]'); if (!tr) return;
      var code = tr.dataset.code;
      if (e.target.classList.contains('stm-setsize')) {
        var v = e.target.value;
        if (v === 'custom') { var c = prompt('จำนวนเส้นต่อชุด (ตัวเลข)', '6'); v = c == null ? '' : String(Math.max(1, parseInt(c, 10) || 0)); }
        DBX.enrichSet(code, { setSize: v === '' ? null : parseInt(v, 10) });
        refreshGrid(); applyFilter();
      } else if (e.target.dataset.flag) {
        var ex = DBX.enrichGet(code) || {}; var fl = Object.assign({}, ex.flags || {});
        fl[e.target.dataset.flag] = e.target.checked;
        DBX.enrichSet(code, { flags: fl });
        e.target.closest('.stm-flag').classList.toggle('on', e.target.checked);
        refreshGrid();
      }
    });
  }
  function refreshGrid() { if (window.SG && SG.render) { if (SG.clearDbCache) SG.clearDbCache(); if (SG.invalidate) SG.invalidate(); SG.render(); } }

  // กฎรายหมวดสินค้า
  function openCatRules() {
    var groups = {}; list.forEach(function (x) { if (x.group) groups[x.group] = 1; });
    var rules = DBX.catRules();
    var body = Object.keys(groups).sort().map(function (g) {
      var r = rules[g] || {};
      var noCheck = r.checkSet === false;
      return '<div class="stm-catrow" data-group="' + esc(g) + '">' +
        '<span class="stm-catg">กลุ่ม ' + esc(g) + '</span>' +
        '<label class="stm-catchk"><input type="checkbox" class="stm-catcheck"' + (!noCheck ? ' checked' : '') + '> เช็คชุด</label>' +
        '<select class="stm-catsize"' + (noCheck ? ' disabled' : '') + '>' +
          '<option value="2"' + (r.setSize === 2 ? ' selected' : '') + '>2 เส้น/ชุด</option>' +
          '<option value="4"' + (r.setSize === 4 || r.setSize == null ? ' selected' : '') + '>4 เส้น/ชุด</option>' +
        '</select></div>';
    }).join('');
    var dlg = document.createElement('div'); dlg.className = 'stm-catdlg';
    dlg.innerHTML = '<div class="stm-catwin"><div class="stm-head"><span>⚙️ กฎรายหมวดสินค้า (ค่าเริ่มต้นของแต่ละกลุ่ม)</span><span class="stm-catx">✕</span></div>' +
      '<div class="stm-catbody">' + (body || '<div class="stm-empty">ไม่มีกลุ่ม</div>') + '</div>' +
      '<div class="stm-foot"><span class="stm-note">สินค้ารายตัวที่ตั้ง setSize เองจะทับกฎนี้</span></div></div>';
    el.appendChild(dlg);
    var closeDlg = function () { dlg.remove(); if (window.PopupStack) PopupStack.remove(dlg); };
    if (window.PopupStack) PopupStack.push(dlg, closeDlg);
    dlg.addEventListener('click', function (e) { if (e.target.closest('.stm-catx') || e.target === dlg) closeDlg(); });
    dlg.addEventListener('change', function (e) {
      var row = e.target.closest('.stm-catrow'); if (!row) return;
      var g = row.dataset.group;
      if (e.target.classList.contains('stm-catcheck')) {
        var on = e.target.checked; row.querySelector('.stm-catsize').disabled = !on;
        DBX.catRuleSet(g, { checkSet: on });
      } else if (e.target.classList.contains('stm-catsize')) {
        DBX.catRuleSet(g, { setSize: parseInt(e.target.value, 10) });
      }
      refreshGrid();
    });
  }

  window.StagingMgr = { open: open, close: close };
})();
