/* ============================================================
   api-bridge.js — ปลั๊กอินเชื่อมบอท Telegram / AI LOCAL ผ่าน WebSocket
   สถาปัตยกรรม:  Telegram → เซิร์ฟเวอร์ local ของคุณ (ws) → โปรแกรมนี้
   แยก 2 API:  🔑 READ token = เช็คราคา (เห็นเฉพาะราคาที่มีผลแล้ว)
               🔐 ADMIN token = แก้ราคา/สั่งงานเหมือนแอดมิน
   ============================================================ */
(function () {
  var XL2 = window.XL2;
  var KEY = 'xls2_api_bridge';
  var ws = null, status = 'off', logs = [];
  var PRICE_COL = { cost: 6, retail: 7, B: 13, A: 16, S: 19 };

  function rnd() { return Math.random().toString(36).slice(2, 10).toUpperCase(); }
  function loadCfg() {
    try {
      var c = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (c) return c;
    } catch (e) {}
    var fresh = { enabled: false, url: 'ws://localhost:8765', readToken: 'READ-' + rnd(), adminToken: 'ADMIN-' + rnd() };
    localStorage.setItem(KEY, JSON.stringify(fresh));
    return fresh;
  }
  function saveCfg(c) { localStorage.setItem(KEY, JSON.stringify(c)); }
  function log(s) {
    logs.push(new Date().toLocaleTimeString('th-TH') + ' · ' + s);
    if (logs.length > 60) logs.shift();
    var el = document.getElementById('apiLog');
    if (el) { el.textContent = logs.slice(-12).join('\n'); el.scrollTop = el.scrollHeight; }
    var dot = document.getElementById('apiDot');
    if (dot) dot.className = 'api-dot ' + status;
  }
  function setStatus(s) { status = s; log('สถานะ: ' + s); }

  // ---- ค้นสินค้า ----
  function matchRows(q, asAdmin) {
    var rows = asAdmin ? SG.dataRows() : SG.effectiveDataRows();
    if (!q) return rows;
    var ql = String(q).toLowerCase().replace(/\s+/g, ' ');
    return rows.filter(function (r) {
      var hay = (r.size + ' ' + r.brand + ' ' + XL2.brandFull(r.brand) + ' ' + r.model).toLowerCase();
      return ql.split(' ').every(function (t) { return hay.indexOf(t) >= 0; });
    });
  }
  function pub(r) { return { row: r.r + 1, size: r.size, brand: r.brand, model: r.model, retail: r.retail, B: r.B, A: r.A, S: r.S, pending: !!r.pending }; }
  function adm(r) { var o = pub(r); o.cost = r.cost; o.margin = r.margin; o.changed = !!r.changed; return o; }

  // ---- ตัวประมวลคำสั่ง ----
  function handle(msg) {
    var cfg = loadCfg();
    var isAdmin = msg.token === cfg.adminToken;
    var isRead = isAdmin || msg.token === cfg.readToken;
    var m = msg.method || '';
    if (!isRead) throw 'unauthorized';
    if (/^admin\./.test(m) && !isAdmin) throw 'admin-token-required';

    switch (m) {
      case 'ping': return { pong: true, sheet: SG.getDoc().name, mode: isAdmin ? 'admin' : 'read' };
      case 'price.check': {
        var list = matchRows(msg.params && msg.params.q, false).slice(0, 10).map(pub);
        return { count: list.length, items: list };
      }
      case 'price.list': {
        var all = matchRows(msg.params && msg.params.q, false).map(pub);
        return { count: all.length, items: all.slice(0, 60) };
      }
      case 'admin.price.check': {
        var la = matchRows(msg.params && msg.params.q, true).slice(0, 10).map(adm);
        return { count: la.length, items: la };
      }
      case 'admin.price.set': {
        var p = msg.params || {};
        var field = PRICE_COL[p.field];
        if (field == null) throw 'field ต้องเป็น cost/retail/B/A/S';
        var hits = matchRows(p.q, true);
        if (p.row) hits = hits.filter(function (r) { return r.r + 1 === +p.row; });
        if (!hits.length) throw 'ไม่พบสินค้า';
        if (hits.length > 1 && !p.all) throw 'พบ ' + hits.length + ' รายการ — ระบุ q ให้แคบลง หรือส่ง all:true';
        var done = hits.map(function (r) {
          var nv = SG.apiSetCell(r.r, field, String(p.value));
          return { row: r.r + 1, size: r.size, model: r.model, field: p.field, value: nv };
        });
        return { updated: done.length, items: done };
      }
      case 'admin.cell.set': {
        var pc = msg.params || {};
        var ref = XL2.parseRef ? XL2.parseRef(pc.ref) : null;
        var mm = /^([A-Za-z]{1,2})([0-9]+)$/.exec(String(pc.ref || ''));
        if (!mm) throw 'ref ไม่ถูกต้อง เช่น H9';
        var c = XL2.colIndex(mm[1].toUpperCase()), r = +mm[2] - 1;
        return { ref: pc.ref, value: SG.apiSetCell(r, c, String(pc.value)) };
      }
      case 'admin.update.publish': {
        SG.setSchedule(msg.params && msg.params.effectiveAt || '');
        SG.syncToDB();
        return { published: true, effectiveAt: (msg.params && msg.params.effectiveAt) || 'ทันที' };
      }
      case 'admin.changes': {
        var ch = SG.getDoc().changes || {};
        return { rows: Object.keys(ch).map(function (r) { return +r + 1; }) };
      }
      default: throw 'unknown method: ' + m;
    }
  }

  // ---- WebSocket ----
  var retryT = null;
  function connect() {
    var cfg = loadCfg();
    if (!cfg.enabled || !cfg.url) { setStatus('off'); return; }
    try { if (ws) { ws.onclose = null; ws.close(); } } catch (e) {}
    setStatus('connecting');
    try { ws = new WebSocket(cfg.url); } catch (e) { setStatus('error'); return; }
    ws.onopen = function () {
      setStatus('online');
      ws.send(JSON.stringify({ role: 'app', name: 'แก้ราคายาง v2' }));
    };
    ws.onmessage = function (ev) {
      var msg; try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (!msg || !msg.method) return;
      var reply = { id: msg.id || null, method: msg.method };
      try { reply.ok = true; reply.result = handle(msg); log('✓ ' + msg.method); }
      catch (err) { reply.ok = false; reply.error = String(err); log('✗ ' + msg.method + ' — ' + err); }
      try { ws.send(JSON.stringify(reply)); } catch (e) {}
    };
    ws.onclose = function () {
      setStatus(loadCfg().enabled ? 'retry' : 'off');
      clearTimeout(retryT);
      if (loadCfg().enabled) retryT = setTimeout(connect, 5000);
    };
    ws.onerror = function () { setStatus('error'); };
  }
  function disconnect() {
    var cfg = loadCfg(); cfg.enabled = false; saveCfg(cfg);
    clearTimeout(retryT);
    try { if (ws) ws.close(); } catch (e) {}
    setStatus('off');
  }

  window.APIBridge = { connect: connect, disconnect: disconnect, loadCfg: loadCfg, saveCfg: saveCfg, getStatus: function () { return status; }, getLogs: function () { return logs.slice(); }, _handle: handle };
  // เชื่อมอัตโนมัติถ้าเปิดไว้
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', connect);
  else setTimeout(connect, 400);
})();
