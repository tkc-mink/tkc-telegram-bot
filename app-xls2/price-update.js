/* คลัสเตอร์อัพเดทราคา (upd*) — แยกจาก index.html
   ใช้ global: $, SG, XL2, refresh, renderSheets (เปิดไว้โดยสคริปต์หลัก) */
(function () {
  function $(id) { return document.getElementById(id); }
  // ---- อัพเดทราคา: เลือกเวลา → สรุป → ยืนยัน ----
  var PRICE_LBL = { 7: 'ราคาตั้ง', 13: 'SUB-B', 16: 'SUB-A', 19: 'SUB-S' };
  var PRICE_KEY = { 7: 'retail', 13: 'B', 16: 'A', 19: 'S' };
  function updItems() {
    var d = SG.getDoc(), byR = {};
    SG.dataRows().forEach(function (rw) { byR[rw.r] = rw; });
    var items = [];
    Object.keys(d.changes || {}).forEach(function (r) {
      var rc = d.changes[r], rw = byR[r];
      if (!rw) return;
      Object.keys(rc).forEach(function (c) {
        var e = rc[c];
        var cur = parseFloat(String(rw[PRICE_KEY[c]] != null ? rw[PRICE_KEY[c]] : '').replace(/,/g, ''));
        var old = parseFloat(String(e.old != null ? e.old : 0).replace(/,/g, '')) || 0;
        if (!isFinite(cur) || cur === old) return;
        items.push({ name: rw.size + ' · ' + rw.brand + ' ' + rw.model, col: PRICE_LBL[c], old: old, nw: cur });
      });
    });
    return items;
  }
  function updStep(n) {
    $('updStep1').style.display = n === 1 ? '' : 'none';
    $('updStep2').style.display = n === 2 ? '' : 'none';
    $('updNext').style.display = n === 1 ? '' : 'none';
    $('updBack').style.display = n === 2 ? '' : 'none';
    $('updConfirm').style.display = n === 2 ? '' : 'none';
  }
  function updWhen() {
    var sched = document.querySelector('input[name="updWhen"]:checked').value === 'sched';
    return sched ? ($('updTime').value || '') : '';
  }
  // ── ส่วนเสริม: การ์ดเลือกได้ · ปุ่มลัด · ตัวอย่างวันเวลาไทย · กันพลาด ──
  function updPad(n) { return (n < 10 ? '0' : '') + n; }
  function updLocalVal(d) { return d.getFullYear() + '-' + updPad(d.getMonth() + 1) + '-' + updPad(d.getDate()) + 'T' + updPad(d.getHours()) + ':' + updPad(d.getMinutes()); }
  var UPD_DAY = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์'];
  var UPD_MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
  function updThaiDate(d) {
    return 'วัน' + UPD_DAY[d.getDay()] + 'ที่ ' + d.getDate() + ' ' + UPD_MON[d.getMonth()] + ' ' + (d.getFullYear() + 543) + ' · ' + updPad(d.getHours()) + ':' + updPad(d.getMinutes()) + ' น.';
  }
  function updRel(ms) {
    if (ms <= 0) return 'ผ่านมาแล้ว';
    var m = Math.round(ms / 60000), h = Math.floor(m / 60), dd = Math.floor(h / 24);
    if (dd >= 1) return 'อีก ~' + dd + ' วัน' + (h % 24 ? ' ' + (h % 24) + ' ชม.' : '');
    if (h >= 1) return 'อีก ~' + h + ' ชม.' + (m % 60 ? ' ' + (m % 60) + ' นาที' : '');
    return 'อีก ~' + Math.max(1, m) + ' นาที';
  }
  function updHeadRender() {
    var items = updItems(), linked = Object.keys(SG.getDoc().rowLinks || {}).length;
    $('updHead').innerHTML =
      '<span class="upd-stat' + (items.length ? '' : ' zero') + '">✏️ ปรับราคา ' + items.length + ' จุด</span>' +
      '<span class="upd-stat db">🗄️ ลิงก์ DB ' + linked + ' สินค้า</span>';
  }
  function updEchoRender() {
    var echo = $('updEcho');
    var sched = document.querySelector('input[name="updWhen"]:checked').value === 'sched';
    if (!sched) { echo.style.display = 'none'; return; }
    var v = $('updTime').value;
    if (!v) { echo.style.display = 'block'; echo.className = 'upd-echo warn'; echo.innerHTML = '⚠️ ยังไม่ได้เลือกวัน–เวลา — กดปุ่มลัด หรือแตะที่ช่องด้านบน'; return; }
    var d = new Date(v), ms = d.getTime() - Date.now();
    echo.style.display = 'block';
    if (ms <= 0) { echo.className = 'upd-echo warn'; echo.innerHTML = '🗓️ ' + updThaiDate(d) + '<br>⚠️ เป็นเวลาที่ผ่านมาแล้ว — จะมีผลทันทีที่ยืนยัน'; }
    else { echo.className = 'upd-echo'; echo.innerHTML = '🗓️ ' + updThaiDate(d) + ' &nbsp;<b>(' + updRel(ms) + ')</b>'; }
  }
  function updSyncOpt() {
    var sched = document.querySelector('input[name="updWhen"]:checked').value === 'sched';
    $('updOptNow').classList.toggle('on', !sched);
    $('updOptSched').classList.toggle('on', sched);
    updEchoRender();
  }
  function updSelSched() { var s = document.querySelector('input[name="updWhen"][value="sched"]'); if (!s.checked) { s.checked = true; updSyncOpt(); } }
  function updChipClear() { document.querySelectorAll('#updChips .upd-chip').forEach(function (c) { c.classList.remove('on'); }); }
  document.querySelectorAll('input[name="updWhen"]').forEach(function (r) { r.addEventListener('change', function () { updChipClear(); updSyncOpt(); }); });
  $('updTime').addEventListener('focus', updSelSched);
  $('updTime').addEventListener('input', function () { updSelSched(); updChipClear(); updEchoRender(); });
  $('updChips').addEventListener('click', function (e) {
    var b = e.target.closest('.upd-chip'); if (!b) return;
    updSelSched(); updChipClear(); b.classList.add('on');
    var now = new Date(), d = new Date(now);
    switch (b.dataset.preset) {
      case 't17': d.setHours(17, 0, 0, 0); if (d <= now) d.setDate(d.getDate() + 1); break;
      case 'tm8': d.setDate(d.getDate() + 1); d.setHours(8, 0, 0, 0); break;
      case 'd2': d.setDate(d.getDate() + 2); d.setHours(8, 0, 0, 0); break;
      case 'mon': { var add = ((1 - d.getDay()) + 7) % 7; if (add === 0) add = 7; d.setDate(d.getDate() + add); d.setHours(8, 0, 0, 0); } break;
      case 'm1': d.setMonth(d.getMonth() + 1, 1); d.setHours(8, 0, 0, 0); break;
    }
    $('updTime').value = updLocalVal(d);
    updEchoRender();
  });
  $('btnSync').onclick = function () {
    var cur = SG.getSchedule();
    document.querySelector('input[name="updWhen"][value="' + (cur ? 'sched' : 'now') + '"]').checked = true;
    $('updTime').value = cur || '';
    $('updTime').min = updLocalVal(new Date());
    updChipClear();
    updHeadRender();
    updSyncOpt();
    updStep(1);
    $('mUpdate').classList.add('open');
  };
  $('updNext').onclick = function () {
    var schedSel = document.querySelector('input[name="updWhen"]:checked').value === 'sched';
    if (schedSel && !$('updTime').value) { updEchoRender(); return; }   // กันพลาด: เลือกตั้งเวลาแต่ยังไม่ใส่
    var items = updItems();
    var linked = Object.keys(SG.getDoc().rowLinks || {}).length;
    var when = updWhen();
    var html = '<div class="upd-line">⏱ มีผล: <b>' + (when ? when.replace('T', ' ') : 'ทันที') + '</b></div>';
    if (items.length) {
      html += '<div class="upd-line">✏️ ปรับราคา <b>' + items.length + ' จุด</b>:</div><div class="upd-list">' +
        items.slice(0, 10).map(function (it) {
          var up = it.nw > it.old;
          return '<div class="upd-it"><span>' + it.name + ' · ' + it.col + '</span><b style="color:' + (up ? '#0a8f3c' : '#d62828') + ';">' + it.old.toLocaleString() + ' → ' + it.nw.toLocaleString() + ' ' + (up ? '▲' : '▼') + '</b></div>';
        }).join('') + (items.length > 10 ? '<div class="upd-it">…อีก ' + (items.length - 10) + ' จุด</div>' : '') + '</div>';
    } else {
      html += '<div class="upd-line" style="color:#a05c1a;">⚠️ รอบนี้ไม่มีการปรับราคา</div>';
    }
    html += '<div class="upd-line">🗄️ ส่งราคาเข้า DB: <b>' + linked + ' สินค้าที่ลิงก์</b></div>';
    $('updSummary').innerHTML = html;
    $('updConfirm').disabled = (!items.length && !linked);
    updStep(2);
  };
  $('updBack').onclick = function () { updStep(1); };
  $('updConfirm').onclick = function () {
    SG.setSchedule(updWhen());
    SG.syncToDB();
    // 📦 เก็บสำเนาหลังอัพเดททุกครั้ง แยกไว้ในหมวดประวัติ เผื่อย้อนกลับมาดู
    try {
      var aid = 'a' + Date.now();
      var stamp = new Date().toLocaleString('th-TH', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
      var curName = (XL2.store.sheetsList().find(function (s) { return s.id === XL2.store.curSheet(); }) || {}).name || 'ชีต';
      XL2.store.saveSheetDoc(aid, SG.getDoc());
      var sheets = XL2.store.sheetsList();
      sheets.push({ id: aid, name: '📦 ' + curName + ' · อัพเดท ' + stamp, archived: 1 });
      XL2.store.saveSheets(sheets);
      renderSheets();
    } catch (e) {}
    $('mUpdate').classList.remove('open');
    refresh();
  };
})();
