/* ============================================================
   sheet-grid.js — true-Excel grid core (v2)
   ทุกช่องเป็นเซลล์อิสระ: ค่า (v) หรือสูตร (f) + สไตล์ (s)
   depends: engine2.js (XL2), sheet-build.js (XL2Build)
   exposes window.SG
   ============================================================ */
(function () {
  var XL2 = window.XL2, esc = XL2.esc;

  var doc = null;
  var view = { mode: 'admin', zoom: 1, secret: false };
  var sel = { r: 0, c: 0, ar: 0, ac: 0 };
  var editing = null;          // {r,c, viaFx}
  var undoStack = [], redoStack = [], clip = null;
  var rootEl, inputEl, fxEl, nameEl, statusEl, sumEl, ctxEl, tipEl;
  var cover = {};              // "r:c" -> anchor key for merged-covered cells
  var dirty = false;

  // ---------- doc helpers ----------
  function key(r, c) { return r + ':' + c; }
  function cellAt(r, c) { return doc.cells[key(r, c)] || null; }
  function ensureCell(r, c) { var k = key(r, c); if (!doc.cells[k]) doc.cells[k] = { v: '', t: 'auto', s: {} }; return doc.cells[k]; }
  function snapshot() { return JSON.stringify({ cells: doc.cells, merges: doc.merges, colW: doc.colW, rowH: doc.rowH, nRows: doc.nRows, nCols: doc.nCols, adminRows: doc.adminRows, adminCols: doc.adminCols, name: doc.name, rowLinks: doc.rowLinks, condColors: doc.condColors, schedule: doc.schedule, rowSchedules: doc.rowSchedules, changes: doc.changes, images: doc.images || [], hideRows: doc.hideRows, hideCols: doc.hideCols, uHideRows: doc.uHideRows, uHideCols: doc.uHideCols, sizeCol: doc.sizeCol }); }
  function restore(s) { var d = JSON.parse(s); doc.cells = d.cells; doc.merges = d.merges; doc.colW = d.colW; doc.rowH = d.rowH; doc.nRows = d.nRows; doc.nCols = d.nCols; doc.adminRows = d.adminRows; doc.adminCols = d.adminCols; doc.name = d.name; doc.rowLinks = d.rowLinks || {}; doc.condColors = d.condColors; doc.schedule = d.schedule; doc.rowSchedules = d.rowSchedules || {}; doc.changes = d.changes || {}; doc.images = d.images || []; doc.hideRows = d.hideRows || {}; doc.hideCols = d.hideCols || {}; doc.uHideRows = d.uHideRows || {}; doc.uHideCols = d.uHideCols || {}; doc.sizeCol = (d.sizeCol != null ? d.sizeCol : 0); }
  function pushUndo() { undoStack.push(snapshot()); if (undoStack.length > 80) undoStack.shift(); redoStack.length = 0; }
  function undo() { if (!undoStack.length) return; redoStack.push(snapshot()); restore(undoStack.pop()); afterChange(); toast('ย้อนกลับ'); }
  function redo() { if (!redoStack.length) return; undoStack.push(snapshot()); restore(redoStack.pop()); afterChange(); toast('ทำซ้ำ'); }
  function persist() { try { XL2.store.saveCurrent(doc); } catch (e) {} dirty = true; }
  function afterChange() { invalidate(); buildCover(); render(); persist(); }

  // ---------- merges ----------
  function buildCover() {
    cover = {};
    Object.keys(doc.merges || {}).forEach(function (k) {
      var m = doc.merges[k], p = k.split(':'), r = +p[0], c = +p[1];
      for (var rr = r; rr < r + m.rs; rr++) for (var cc = c; cc < c + m.cs; cc++)
        if (!(rr === r && cc === c)) cover[key(rr, cc)] = k;
    });
  }
  function anchorOf(r, c) {
    var cv = cover[key(r, c)];
    if (!cv) return { r: r, c: c };
    var p = cv.split(':'); return { r: +p[0], c: +p[1] };
  }

  // ---------- evaluation ----------
  var cache = null;
  function invalidate() { cache = null; }
  // ---------- DB clean-model cache (ชั้นกลาง DBX) ----------
  // dbCache: code13 -> clean model (sync) · เติมแบบ async ตอน render/refresh
  var dbCache = {};
  function clearDbCache() { dbCache = {}; dbTried = {}; }   // ล้างแคชเพื่อบังคับดึง clean model ใหม่ (เมื่อ enrich/flags เปลี่ยน)
  function rowCode(r) { var v = (doc.rowLinks && doc.rowLinks[r]) || null; return (v && /^\d{13}$/.test(v)) ? v : null; }   // code13 ของแถว (เฉพาะรูปแบบ 13 หลัก)
  function isCode13(v) { return !!v && /^\d{13}$/.test(v); }
  function dbProduct(code) { return code ? dbCache[code] : null; }
  // สถานะลิงก์ของแถว: null=ไม่ลิงก์ · 'ok' · 'inactive' · 'missing' · 'loading'
  function rowLinkStatus(r) {
    var code = rowCode(r); if (!code) return null;
    var p = dbCache[code];
    if (p) return (p.status && p.status !== 'active') ? 'inactive' : 'ok';
    return dbTried[code] ? 'missing' : 'loading';
  }
  function rowLinkLabel(r) {
    var code = rowCode(r); if (!code) return '';
    var p = dbCache[code];
    if (p) return code + ' · ' + p.name + (p.status !== 'active' ? ' (inactive)' : '');
    return dbTried[code] ? ('⚠️ ลิงก์ค้าง — ไม่พบ "' + code + '" ใน DB') : (code + ' · กำลังโหลด…');
  }
  // แม่กุญแจ (ซ่อนจากผู้ใช้) — ปรับไอคอน/คำอธิบายได้ในตั้งค่า
  function lockGlyph() { return localStorage.getItem('xls2_lockglyph') || '🔒'; }
  function lockDesc() { return localStorage.getItem('xls2_lockdesc') || 'ซ่อนจากผู้ใช้'; }
  // ---------- ขั้น4: ไอคอนสถานะของช่อง (auto / manual / mixed) ----------
  function statusIconsFor(r) {
    if (!window.DBX) return [];
    var code = rowCode(r); var p = code ? dbCache[code] : null; if (!p) return [];
    var sc = (doc.statusCell && doc.statusCell[r]) || { mode: 'auto' };
    var auto = window.DBX.computeStatus(p, 4);
    function byKey(k) { return window.DBX.statusDefByKey(k); }
    if (sc.mode === 'manual') return (sc.pinned || []).map(byKey).filter(Boolean).slice(0, 4);
    if (sc.mode === 'mixed') {
      var merged = (sc.pinned || []).map(byKey).filter(Boolean);
      auto.forEach(function (d) { if (!merged.some(function (m) { return m.key === d.key; })) merged.push(d); });
      return merged.slice(0, 4);
    }
    if (sc.hidden && sc.hidden.length) auto = auto.filter(function (d) { return sc.hidden.indexOf(d.key) < 0; });
    return auto.slice(0, 4);
  }
  function statusCellInner(r) {
    var icons = statusIconsFor(r);
    if (!icons.length) return '';
    var corners = ['tr', 'tl', 'bl', 'br'];   // 1=บนขวา · 2=บนซ้าย · 3=ล่างซ้าย · 4=ล่างขวา
    return '<span class="sg-status n' + icons.length + '">' + icons.slice(0, 4).map(function (d, i) {
      return '<span class="sg-st-ic c-' + corners[i] + '" data-stkey="' + esc(d.key) + '"' + (d.color ? ' style="color:#' + d.color + '"' : '') + '>' + (window.IconKit ? IconKit.html(d.icon) : esc(d.icon) + '\uFE0E') + '</span>';
    }).join('') + '</span>';
  }
  // เมนูคลิกขวาช่องสถานะ: auto / manual / mixed + เลือกไอคอน pin
  var statusMenuEl = null;
  function openStatusMenu(r, c, x, y) {
    if (!window.DBX) return;
    if (!statusMenuEl) { statusMenuEl = document.createElement('div'); statusMenuEl.className = 'sg-ctx sg-statusmenu'; document.body.appendChild(statusMenuEl); }
    var sc = (doc.statusCell && doc.statusCell[r]) || { mode: 'auto', pinned: [] };
    function radio(mode, label) { return '<div class="ctx-it" data-mode="' + mode + '"><span class="ctx-ic">' + (sc.mode === mode ? '●' : '○') + '</span>' + label + '</div>'; }
    var defs = window.DBX.statusDefs();
    var fav = window.DBX.iconFav();
    var pinHtml = defs.map(function (d) {
      var on = (sc.pinned || []).indexOf(d.key) >= 0;
      return '<span class="stm-pin' + (on ? ' on' : '') + '" data-pin="' + esc(d.key) + '" title="' + esc(d.label) + '"' + (d.color ? ' style="color:#' + d.color + '"' : '') + '>' + (window.IconKit ? IconKit.html(d.icon) : esc(d.icon)) + '</span>';
    }).join('');
    statusMenuEl.innerHTML =
      '<div class="stm-drag">⠿ โหมด/ไอคอนสถานะ<span class="stm-x">✕</span></div>' +
      '<div class="ctx-row"><div class="ctx-rowlab">โหมดช่องสถานะ</div></div>' +
      radio('auto', 'อัตโนมัติ (คำนวณจากสต็อก/ธง)') +
      radio('manual', 'กำหนดเอง (เฉพาะไอคอนที่ pin)') +
      radio('mixed', 'ผสม (auto + pin เพิ่ม)') +
      '<div class="ctx-sep"></div>' +
      '<div class="ctx-row"><div class="ctx-rowlab">Pin ไอคอน (คลิกเปิด/ปิด)</div></div>' +
      '<div class="stm-pins">' + pinHtml + '</div>';
    statusMenuEl.style.display = 'block';
    statusMenuEl.style.transform = 'none';
    statusMenuEl.style.left = Math.min(x, window.innerWidth - statusMenuEl.offsetWidth - 8) + 'px';
    statusMenuEl.style.top = Math.min(y, window.innerHeight - statusMenuEl.offsetHeight - 8) + 'px';
    makeDraggable(statusMenuEl, '.stm-drag');
    function ensure() { doc.statusCell = doc.statusCell || {}; doc.statusCell[r] = doc.statusCell[r] || { mode: 'auto', pinned: [] }; return doc.statusCell[r]; }
    function navItems() { return [].slice.call(statusMenuEl.querySelectorAll('[data-mode],[data-pin]')); }
    function setKb(el) { navItems().forEach(function (n) { n.classList.toggle('kbsel', n === el); }); if (el) el.scrollIntoView({ block: 'nearest' }); }
    setKb(statusMenuEl.querySelector('[data-mode="' + sc.mode + '"]'));
    if (statusMenuEl._stmKey) document.removeEventListener('keydown', statusMenuEl._stmKey);
    statusMenuEl._stmKey = function (e) {
      if (statusMenuEl.style.display === 'none') return;
      var items = navItems(), cur = statusMenuEl.querySelector('.kbsel'), idx = items.indexOf(cur);
      if (e.key === 'Escape') { e.preventDefault(); statusMenuEl.style.display = 'none'; document.removeEventListener('keydown', statusMenuEl._stmKey); }
      else if (e.key === 'Enter') { e.preventDefault(); (cur || items[0]) && (cur || items[0]).click(); }
      else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); setKb(items[Math.min(items.length - 1, idx + 1)]); }
      else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); setKb(items[Math.max(0, idx < 0 ? 0 : idx - 1)]); }
    };
    document.addEventListener('keydown', statusMenuEl._stmKey);
    statusMenuEl.onclick = function (e) {
      if (e.target.closest('.stm-x')) { statusMenuEl.style.display = 'none'; document.removeEventListener('keydown', statusMenuEl._stmKey); return; }
      var md = e.target.closest('[data-mode]');
      if (md) { pushUndo(); var s = ensure(); s.mode = md.dataset.mode; invalidate(); afterChange(); openStatusMenu(r, c, x, y); return; }
      var pn = e.target.closest('[data-pin]');
      if (pn) {
        pushUndo(); var s2 = ensure(); s2.pinned = s2.pinned || [];
        var k = pn.dataset.pin, i = s2.pinned.indexOf(k);
        if (i >= 0) s2.pinned.splice(i, 1); else s2.pinned.push(k);
        if (s2.mode === 'auto') s2.mode = 'mixed';   // pin แรก = เปลี่ยนเป็น mixed อัตโนมัติ
        invalidate(); afterChange(); openStatusMenu(r, c, x, y); return;
      }
    };
  }
  // ---------- ขั้น5: Side panel รายละเอียดสินค้า (เปิดซ้าย/ขวาตามพื้นที่ · ไม่ทับแถว · ไม่หลุดเฟรม) ----------
  var detailEl = null;
  function openDetailPanel(r, anchorEl) {
    var code = rowCode(r); if (!code || !window.DBX) return;
    if (!detailEl) { detailEl = document.createElement('div'); detailEl.className = 'sg-detail'; document.body.appendChild(detailEl); }
    detailEl.style.display = 'flex';
    detailEl.innerHTML = '<div class="dp-head">📦 รายละเอียดสินค้า<span class="pk-x">✕</span></div><div class="dp-body"><div class="dp-loading">กำลังโหลดจากฐานข้อมูล…</div></div>';
    positionDetail(anchorEl);
    var closeDP = function () { detailEl.style.display = 'none'; if (window.PopupStack) PopupStack.remove(detailEl); };
    detailEl.querySelector('.pk-x').onclick = closeDP;
    if (window.PopupStack) PopupStack.push(detailEl, closeDP);
    makeDraggable(detailEl, '.dp-head');
    window.DBX.getClean(code).then(function (p) {
      if (!p) { detailEl.querySelector('.dp-body').innerHTML = '<div class="dp-loading">⚠️ ไม่พบสินค้า "' + esc(code) + '" ใน DB</div>'; return; }
      var icons = window.DBX.computeStatus(p, 8).map(function (d) { var clk = (d.key === 'incoming' && p.incomingInfo) ? ' dp-stchip-click' : ''; return '<span class="dp-stchip' + clk + '" data-stkey="' + esc(d.key || '') + '"' + (d.color ? ' style="color:#' + d.color + '"' : '') + '>' + (window.IconKit ? IconKit.html(d.icon) : esc(d.icon)) + ' ' + esc(d.label) + '</span>'; }).join('');
      var dotRows = (p.dotWeeks && p.dotWeeks.length)
        ? p.dotWeeks.map(function (d) { return '<tr><td>' + esc(d.dot) + '</td><td>' + esc(d.week) + '</td><td class="dp-num">' + (typeof d.qty === 'number' ? d.qty.toLocaleString('en-US') : esc(d.qty)) + '</td></tr>'; }).join('')
        : '<tr><td colspan="3" class="dp-dim">— ไม่มีข้อมูล DOT —</td></tr>';
      var imgN = (p.images && p.images.length) || 0;
      var ss = p._setSize || { check: true, size: 4 };
      detailEl.querySelector('.dp-body').innerHTML =
        '<div class="dp-top"><div class="dp-code">' + esc(p.code13) + (p.status && p.status !== 'active' ? ' <span class="dp-inact">inactive</span>' : '') + '</div>' +
        '<button class="dp-imgbtn"' + (imgN ? '' : ' disabled') + '>🖼️ ดูรูป' + (imgN ? ' (' + imgN + ')' : '') + '</button></div>' +
        '<div class="dp-name">' + esc(p.name || '') + '</div>' +
        (icons ? '<div class="dp-icons">' + icons + '</div>' : '') +
        '<div class="dp-stats">' +
          stat('จำนวน', (p.qtyOnHand != null ? p.qtyOnHand : '–')) +
          stat('ค้างส่ง', (p.qtyReserved || 0), (p.qtyReserved > 0 ? 'warn' : '')) +
          stat('สุทธิ', (p.qtyAvailable != null ? p.qtyAvailable : '–'), p.qtyAvailable <= 0 ? 'neg' : (ss.check && p.qtyAvailable < ss.size ? 'warn' : 'ok')) +
        '</div>' +
        '<div class="dp-dothead">DOT คงเหลือ <span class="dp-dim">(ปีผลิต · สัปดาห์ · จำนวน)</span></div>' +
        '<table class="dp-dot"><tbody>' + dotRows + '</tbody></table>';
      var ib = detailEl.querySelector('.dp-imgbtn');
      if (ib && imgN) ib.onclick = function () { openImageGallery(p); };
      detailEl.querySelectorAll('.dp-stchip-click').forEach(function (ch) { ch.onclick = function (e) { e.stopPropagation(); showIncomingPopup(p, ch); }; });   // คลิกไอคอนของกำลังเข้า → popup ซ้อนเหนือ
      positionDetail(anchorEl);
    });
    function stat(label, val, tone) { var s = (typeof val === 'number') ? val.toLocaleString('en-US') : String(val); return '<div class="dp-stat' + (tone ? ' dp-' + tone : '') + '"><span class="dp-lbl">' + label + '</span><span class="dp-val">' + esc(s) + '</span></div>'; }
    function incomingHTML(p) {
      if (!(p.incoming > 0) || !p.incomingInfo) return '';
      var ii = p.incomingInfo, d = ii.orderedAt ? new Date(ii.orderedAt) : null;
      var dateStr = d ? d.toLocaleDateString('th-TH', { day: '2-digit', month: 'short', year: '2-digit' }) : '–';
      var days = d ? Math.floor((Date.now() - d.getTime()) / 86400000) : null;
      var st = (ii.status === 'receiving') ? 'กำลังรับเข้า' : 'สั่งซื้อแล้ว (รอของ)';
      return '<div class="dp-incoming">🚚 <b>ของกำลังเข้า ' + esc(p.incoming) + ' เส้น</b>' +
        '<div class="dp-inc-row">สั่งเมื่อ: <b>' + dateStr + '</b>' + (days != null ? ' (' + days + ' วันก่อน)' : '') + '</div>' +
        '<div class="dp-inc-row">สถานะ: <span class="dp-inc-st">' + st + '</span></div></div>';
    }
  }
  // popup รายละเอียดของกำลังเข้า (ซ้อนเหนือแผงรายละเอียด · เข้า PopupStack)
  var incPopEl = null;
  function showIncomingPopup(p, anchor) {
    if (!p || !p.incomingInfo) return;
    if (!incPopEl) { incPopEl = document.createElement('div'); incPopEl.className = 'dp-incpop'; document.body.appendChild(incPopEl); }
    var ii = p.incomingInfo, d = ii.orderedAt ? new Date(ii.orderedAt) : null;
    var dateStr = d ? d.toLocaleDateString('th-TH', { day: '2-digit', month: 'long', year: '2-digit' }) : '–';
    var days = d ? Math.floor((Date.now() - d.getTime()) / 86400000) : null;
    var st = (ii.status === 'receiving') ? 'กำลังรับเข้า' : 'สั่งซื้อแล้ว (รอของ)';
    incPopEl.innerHTML = '<div class="dp-incpop-h">🚚 ของกำลังเข้า<span class="pk-x">✕</span></div>' +
      '<div class="dp-incpop-b">' +
      '<div class="dp-incpop-row"><span>จำนวน</span><b>' + esc(p.incoming) + ' เส้น</b></div>' +
      '<div class="dp-incpop-row"><span>สั่งเมื่อ</span><b>' + esc(dateStr) + (days != null ? ' (' + days + ' วันก่อน)' : '') + '</b></div>' +
      '<div class="dp-incpop-row"><span>สถานะ</span><b class="dp-inc-st">' + st + '</b></div>' +
      '</div>' +
      '<div class="dp-incpop-foot"><a class="dp-incpop-link">⚙ ตั้งค่า / เชื่อมต่อฐานข้อมูล</a></div>';
    incPopEl.style.display = 'block';
    var rc = anchor.getBoundingClientRect();
    incPopEl.style.left = Math.max(8, Math.min(rc.left, window.innerWidth - incPopEl.offsetWidth - 12)) + 'px';
    var top = rc.top - incPopEl.offsetHeight - 6;
    incPopEl.style.top = (top < 8 ? (rc.bottom + 6) : top) + 'px';   // อยู่เหนือไอคอน (ไม่พอก็ลงล่าง)
    var close = function () { incPopEl.style.display = 'none'; if (window.PopupStack) PopupStack.remove(incPopEl); };
    if (window.PopupStack) PopupStack.push(incPopEl, close);
    incPopEl.querySelector('.pk-x').onclick = close;
    var lk = incPopEl.querySelector('.dp-incpop-link'); if (lk) lk.onclick = function () { close(); if (window.openSettings) window.openSettings('dbconn'); };
  }

  // แกลเลอรีรูปสินค้า — ป๊อปอัปซ้อนเหนือ panel เดิม (เข้า PopupStack · Esc ปิดทีละชั้น)
  var galleryEl = null;
  function openImageGallery(p) {
    if (!galleryEl) { galleryEl = document.createElement('div'); galleryEl.className = 'sg-detail sg-gallery'; document.body.appendChild(galleryEl); }
    var imgs = p.images || [];
    var tiles = imgs.map(function (im, i) {
      return '<div class="gl-tile' + (im.url ? '' : ' gl-empty') + '" data-i="' + i + '">' +
        (im.url ? '<img src="' + esc(im.url) + '" alt="" onerror="this.parentNode.classList.add(\'gl-empty\');this.remove();">' : 'รูป ' + (i + 1)) +
        '</div>';
    }).join('');
    galleryEl.innerHTML = '<div class="dp-head gl-head">🖼️ รูปสินค้า · ' + esc(p.code13) + ' <span class="gl-count">(' + imgs.length + ' รูป)</span><span class="pk-x">✕</span></div>' +
      '<div class="gl-body">' + tiles + '</div>';
    galleryEl.style.display = 'flex';
    // วางกึ่งกลางเหนือ panel เดิม
    var w = 360, dh = detailEl ? detailEl.getBoundingClientRect() : null;
    galleryEl.style.width = w + 'px';
    var L = dh ? Math.max(6, Math.min(dh.left - 20, window.innerWidth - w - 6)) : (window.innerWidth - w) / 2;
    galleryEl.style.left = L + 'px';
    galleryEl.style.top = (dh ? Math.max(6, dh.top - 12) : 60) + 'px';
    galleryEl.style.transform = 'none';
    makeDraggable(galleryEl, '.gl-head');
    clampPopup(galleryEl);
    var closeG = function () { galleryEl.style.display = 'none'; if (window.PopupStack) PopupStack.remove(galleryEl); };
    if (window.PopupStack) PopupStack.push(galleryEl, closeG);
    galleryEl.querySelector('.pk-x').onclick = closeG;
    galleryEl.querySelector('.gl-body').onclick = function (e) {
      var t = e.target.closest('.gl-tile'); if (!t) return;
      openImageViewer(p, +t.dataset.i);
    };
  }
  // Lightbox: ขยายรูปเดี่ยว (ชั้นบนสุด) + ปุ่มเซฟลงเครื่อง · เลื่อนรูปก่อน/ถัดไป
  var viewerEl = null;
  function openImageViewer(p, idx) {
    var imgs = p.images || []; if (!imgs.length) return;
    idx = Math.max(0, Math.min(idx, imgs.length - 1));
    if (!viewerEl) { viewerEl = document.createElement('div'); viewerEl.className = 'sg-imgviewer'; document.body.appendChild(viewerEl); }
    function render() {
      var im = imgs[idx] || {};
      var fname = (p.code13 || 'image') + '_' + (idx + 1) + '.jpg';
      viewerEl.innerHTML =
        '<div class="iv-head"><span class="iv-title">รูป ' + (idx + 1) + ' / ' + imgs.length + ' · ' + esc(p.code13) + '</span>' +
        '<span class="iv-x">✕</span></div>' +
        '<div class="iv-stage">' +
          (imgs.length > 1 ? '<button class="iv-nav iv-prev" title="ก่อนหน้า">‹</button>' : '') +
          (im.url ? '<img class="iv-img" src="' + esc(im.url) + '" alt="" data-fname="' + esc(fname) + '">' : '<div class="iv-empty">ยังไม่มีรูป (รอ URL จาก DB)</div>') +
          (imgs.length > 1 ? '<button class="iv-nav iv-next" title="ถัดไป">›</button>' : '') +
        '</div>' +
        '<div class="iv-foot"><button class="btn primary iv-save"' + (im.url ? '' : ' disabled') + '>⬇️ เซฟรูปลงเครื่อง</button></div>';
      var prev = viewerEl.querySelector('.iv-prev'), next = viewerEl.querySelector('.iv-next');
      if (prev) prev.onclick = function () { idx = (idx - 1 + imgs.length) % imgs.length; render(); };
      if (next) next.onclick = function () { idx = (idx + 1) % imgs.length; render(); };
      viewerEl.querySelector('.iv-x').onclick = closeV;
      var sv = viewerEl.querySelector('.iv-save');
      if (sv && im.url) sv.onclick = function () { saveImage(im.url, fname); };
    }
    function closeV() { viewerEl.style.display = 'none'; document.removeEventListener('keydown', onKey, true); if (window.PopupStack) PopupStack.remove(viewerEl); }
    function onKey(e) {
      if (viewerEl.style.display === 'none' || imgs.length < 2) return;
      if (e.key === 'ArrowLeft') { e.preventDefault(); e.stopPropagation(); idx = (idx - 1 + imgs.length) % imgs.length; render(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); e.stopPropagation(); idx = (idx + 1) % imgs.length; render(); }
    }
    viewerEl.style.display = 'flex';
    render();
    clampPopup(viewerEl);
    document.addEventListener('keydown', onKey, true);
    if (window.PopupStack) PopupStack.push(viewerEl, closeV);
  }
  function saveImage(url, fname) {
    // พยายามดึงเป็น blob เพื่อบังคับดาวน์โหลด · ถ้าข้าม origin ไม่ได้ → เปิดแท็บใหม่ให้เซฟเอง
    fetch(url).then(function (r) { return r.blob(); }).then(function (b) {
      var a = document.createElement('a'), u = URL.createObjectURL(b);
      a.href = u; a.download = fname || 'image.jpg'; document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(u); a.remove(); }, 1000);
    }).catch(function () {
      var a = document.createElement('a'); a.href = url; a.download = fname || 'image.jpg'; a.target = '_blank'; a.rel = 'noopener';
      document.body.appendChild(a); a.click(); a.remove();
    });
  }
  function positionDetail(anchorEl) {
    if (!detailEl || !anchorEl) return;
    detailEl.style.transform = 'none';
    var w = detailEl.offsetWidth || 300, h = detailEl.offsetHeight || 320;
    var a = anchorEl.getBoundingClientRect();
    var spaceRight = window.innerWidth - a.right, spaceLeft = a.left;
    var L = (spaceRight >= w + 12) ? a.right + 8 : (spaceLeft >= w + 12 ? a.left - w - 8 : Math.max(6, window.innerWidth - w - 6));
    var T = Math.min(Math.max(6, a.top), window.innerHeight - h - 6);
    detailEl.style.left = Math.max(6, L) + 'px';
    detailEl.style.top = T + 'px';
  }
  // ค่าที่ดึงจาก DB สำหรับช่องนี้ (cell-link ชนะ row-link+columnMap) — undefined = ไม่ผูก/ยังไม่แคช
  function dbCellValue(r, c) {
    if (!window.DBX) return undefined;
    var cl = doc.cellLinks && doc.cellLinks[r] && doc.cellLinks[r][c];
    if (cl && isCode13(cl.code) && cl.field) { var p = dbCache[cl.code]; return p ? dbFieldVal(p, cl.field) : (dbTried[cl.code] ? '' : '\u2026'); }
    var cm = doc.columnMap && doc.columnMap[c];
    var code = rowCode(r);
    if (cm && cm.field && code) { var p2 = dbCache[code]; return p2 ? dbFieldVal(p2, cm.field) : (dbTried[code] ? '' : '\u2026'); }
    return undefined;
  }
  function dbFieldVal(p, field) { if (field === 'dotRange') return window.DOT ? window.DOT.rangeText(p) : ''; var v = p[field]; return (v == null) ? '' : v; }
  // ช่องนี้ผูก DB อยู่ไหม (มีไว้ล็อก read-only) · 'read'|'write'|null
  function dbCellMode(r, c) {
    if (!window.DBX) return null;
    var cl = doc.cellLinks && doc.cellLinks[r] && doc.cellLinks[r][c];
    if (cl && isCode13(cl.code) && cl.field) return window.DBX.isWritable(cl.field) ? 'write' : 'read';
    var cm = doc.columnMap && doc.columnMap[c];
    if (cm && cm.field && rowCode(r)) return cm.mode || (window.DBX.isWritable(cm.field) ? 'write' : 'read');
    return null;
  }
  // เติมแคชจาก DBX ตามรหัสที่ผูกในชีต แล้ว callback ให้ re-render
  var dbCacheBusy = false;
  var dbTried = {};   // code ที่พยายามดึงแล้ว (กันลูป re-render เมื่อรหัสเก่า/หาไม่เจอใน DB)
  var dbRerenderPending = false;
  function refreshDbCache(cb) {
    if (!window.DBX) { if (cb) cb(false); return; }
    if (dbCacheBusy) { if (cb) cb(false); return; }
    var codes = {};
    Object.keys(doc.rowLinks || {}).forEach(function (r) { var v = doc.rowLinks[r]; if (isCode13(v)) codes[v] = 1; });
    Object.keys(doc.cellLinks || {}).forEach(function (r) { var row = doc.cellLinks[r]; Object.keys(row).forEach(function (c) { if (row[c] && isCode13(row[c].code)) codes[row[c].code] = 1; }); });
    var missing = Object.keys(codes).filter(function (cd) { return !dbCache[cd] && !dbTried[cd]; });
    if (!missing.length) { if (cb) cb(false); return; }
    dbCacheBusy = true;
    missing.forEach(function (cd) { dbTried[cd] = 1; });   // ทำเครื่องหมายว่าพยายามแล้ว (สำเร็จหรือไม่ก็ไม่วนซ้ำ)
    window.DBX.batchClean(missing).then(function (arr) {
      var got = false;
      arr.forEach(function (p) { if (p && p.code13) { dbCache[p.code13] = p; got = true; } });
      dbCacheBusy = false; if (cb) cb(got);
    }).catch(function () { dbCacheBusy = false; if (cb) cb(false); });
  }
  // เรียกหลัง render: เติมแคช DB แล้ว re-render รอบเดียว (กันลูปด้วย setTimeout + flag)
  function scheduleDbFill() {
    if (dbRerenderPending || dbCacheBusy) return;
    refreshDbCache(function (changed) {
      if (!changed) return;
      dbRerenderPending = true;
      setTimeout(function () { dbRerenderPending = false; invalidate(); render(); }, 0);
    });
  }
  function valueOf(r, c, seen) {
    var k = key(r, c);
    if (!cache) cache = {};
    if (k in cache) return cache[k];
    // ค่าที่ผูกจาก DB (read fields) ชนะค่าที่เก็บในเซลล์ · ราคา (write) ใช้ค่าในเซลล์เป็นหลัก (แก้ได้)
    var dbm = dbCellMode(r, c);
    if (dbm === 'read') { var dv = dbCellValue(r, c); if (dv !== undefined) { cache[k] = dv; return dv; } }
    var cell = doc.cells[k];
    var out = '';
    if (cell) {
      if (cell.f) {
        seen = seen || {};
        if (seen[k]) { cache[k] = '#วน!'; return '#วน!'; }
        seen[k] = 1;
        try { out = XL2.evaluate(cell.f, function (rr, cc) { return valueOf(rr, cc, seen); }); }
        catch (e) { out = '#ERR'; }
        delete seen[k];
      } else out = (cell.v != null ? cell.v : '');
    }
    cache[k] = out;
    return out;
  }
  function displayOf(r, c) {
    var cell = cellAt(r, c);
    var v = valueOf(r, c);
    if (v == null || v === '') return '';
    var t = cell ? cell.t : 'auto';
    if (t === 'text') return String(v);
    if (XL2.isNumeric(v)) {
      var n = XL2.toN(v);
      var s;
      var dp = (cell && cell.s && cell.s.dp != null) ? cell.s.dp : null;
      if (dp != null) s = n.toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp });
      else s = XL2.fmtNum(n);
      if (cell && cell.s && cell.s.pm && n > 0) s = '+' + s;
      return s;
    }
    return String(v);
  }

  // ---------- visibility (admin/user) ----------
  function rowHidden(r) {
    if (doc.hideRows && doc.hideRows[r]) return true;                 // ซ่อนแบบ Excel (ทั้งสองโหมด)
    if (view.mode === 'user') {
      if (doc.adminRows && doc.adminRows[r]) return true;            // ล็อก = ซ่อนจากผู้ใช้
      if (doc.uHideRows && doc.uHideRows[r]) return true;            // ซ่อนเฉพาะโหมดผู้ใช้
      if (window.PermEnforce && PermEnforce.active()) {             // ซ่อนตามสิทธิ์ตำแหน่ง (กลุ่ม/หมวด/ยี่ห้อ/รหัส)
        var pcode = rowCode(r);
        if (pcode) { var pp = dbCache[pcode]; if (pp && PermEnforce.rowHiddenProduct(pp)) return true; }
      }
    }
    return false;
  }
  function colHidden(c) {
    if (doc.hideCols && doc.hideCols[c]) return true;
    if (view.mode === 'user') {
      if (doc.adminCols && doc.adminCols[c]) return true;
      if (doc.uHideCols && doc.uHideCols[c]) return true;
      if (window.PermEnforce && PermEnforce.active()) {             // ซ่อนคอลัมน์ตามสิทธิ์ตำแหน่ง
        var cm = doc.columnMap && doc.columnMap[c];
        if (cm && cm.field && PermEnforce.colHiddenField(cm.field)) return true;
      }
    }
    return false;
  }
  function stepRow(r, d) { var n = r + d; while (n >= 0 && n < doc.nRows && rowHidden(n)) n += d; return (n < 0 || n >= doc.nRows) ? r : n; }
  function stepCol(c, d) { var n = c + d; while (n >= 0 && n < doc.nCols && colHidden(n)) n += d; return (n < 0 || n >= doc.nCols) ? c : n; }

  // ---------- filter / search (สกรีนผล) ----------
  // admin: พิมพ์ค้นหาแล้วกรองทันที · user: ต้องเลือกเงื่อนไข+กดค้นหาก่อนจึงเห็นข้อมูล
  var flt = { q: '', brand: '', size: '', rim: '', applied: false };
  var lastMatchCount = 0;
  var USER_MAX = 60;            // ผู้ใช้: ผลลัพธ์เกิน 60 รายการ = ให้ระบุเงื่อนไขเพิ่ม
  var tooMany = false;
  function rowKind(r) {
    if (r < 2) return 'title';
    var m = doc.merges[r + ':0'];
    var v0 = String(valueOf(r, 0));
    if (m && m.cs > 1) return v0.indexOf('ขอบ') >= 0 ? 'sect' : 'title';
    if (v0 === 'ขนาด') return 'head';
    return 'data';
  }
  function sizeCol() { return (doc && doc.sizeCol != null) ? (doc.sizeCol | 0) : 0; }   // คอลัมน์ "ขนาด" หลัก (ตั้งได้ · ค่าเริ่มต้น A=0)
  function rowSizeText(r) { var sc = sizeCol(); var a = anchorOf(r, sc); return String(valueOf(a.r, sc)).split('\n')[0].trim(); }
  // แยกส่วนขนาดยาง: 205/75R14C → {w:205, series:'75', rim:'14'} · 185R14C → {w:185, series:'', rim:'14'}
  function parseSizeStr(t) {
    var m = /(\d{3})(?:\/(\d{2,3}))?\s*R\s*(\d{2})/i.exec(String(t || ''));
    if (!m) return null;
    return { w: m[1], series: m[2] || '', rim: m[3] };
  }
  // ความสูง (เส้นผ่าศูนย์กลาง) — หาจากช่องขนาด หรือคอลัมน์หมายเหตุของกลุ่ม เช่น "( 65.2 cm )"
  function rowDiaCm(r) {
    var re = /([\d.]+)\s*cm/i;
    var a = anchorOf(r, 0);
    var m = re.exec(String(valueOf(a.r, 0)));
    if (m) return parseFloat(m[1]);
    var mg = doc.merges[a.r + ':0'];
    var n = (mg && mg.cs === 1) ? mg.rs : 1;
    var noteCol = Math.min(22, doc.nCols - 1);
    for (var rr = a.r; rr < a.r + n && rr < doc.nRows; rr++) {
      var m2 = re.exec(String(valueOf(rr, noteCol)));
      if (m2) return parseFloat(m2[1]);
    }
    return null;
  }
  // ความสูงยาง (เส้นผ่านศูนย์กลางรวม) → {cm, inch} · ใช้ค่าที่บันทึกไว้ก่อน ไม่มีค่อยคำนวณจากขนาด
  function tireHeight(r) {
    var sizeText = rowSizeText(r);
    var stored = rowDiaCm(r);                                  // ค่าที่บันทึกไว้ "( 65.2 cm )"
    var cm = null, approx = false, wCm = null, wIn = null;
    var sz = parseSizeStr(sizeText);
    if (sz) {
      var w = parseInt(sz.w, 10), rim = parseInt(sz.rim, 10);
      var ar = sz.series ? parseInt(sz.series, 10) : 80; approx = !sz.series;   // ไม่ระบุซีรีส์ = ประมาณ 80
      if (w && rim) cm = (rim * 25.4 + 2 * w * ar / 100) / 10;               // เส้นผ่าศูนย์กลาง = ขอบล้อ + 2×แก้มยาง
      if (w) { wCm = w / 10; wIn = w / 25.4; }                                // หน้ากว้าง (มม.→ซม./นิ้ว)
    } else {
      var fl = /(\d{2}(?:\.\d+)?)\s*[xX]\s*(\d{1,2}(?:\.\d+)?)/.exec(sizeText);   // ยางบอลลูน (flotation): 31x10.5R15 → สูง 31 นิ้ว · กว้าง 10.5 นิ้ว
      if (fl) { cm = parseFloat(fl[1]) * 2.54; wIn = parseFloat(fl[2]); wCm = wIn * 2.54; }
    }
    var useCm = (stored != null && !isNaN(stored)) ? stored : cm;
    if (useCm == null || isNaN(useCm)) return null;
    return { cm: useCm, inch: useCm / 2.54, widthCm: wCm, widthIn: wIn, stored: (stored != null && !isNaN(stored)), approx: (stored == null && approx), sizeText: sizeText };
  }
  function rowText(r) {
    var out = [rowSizeText(r)];
    for (var c = 1; c < doc.nCols; c++) out.push(String(displayOf(r, c)));
    return out.join(' ').toLowerCase();
  }
  function filterActive() {
    if (view.mode === 'user') return true;
    return !!(flt.q || flt.brand || flt.size || flt.rim || flt.width || flt.series || flt.height);
  }
  function computeRowVis() {
    var vis = new Array(doc.nRows);
    lastMatchCount = 0; tooMany = false;
    if (!filterActive()) { for (var r0 = 0; r0 < doc.nRows; r0++) vis[r0] = !rowHidden(r0); return vis; }
    if (view.mode === 'user' && !flt.applied) { for (var r1 = 0; r1 < doc.nRows; r1++) vis[r1] = (rowKind(r1) === 'title' && r1 < 2); return vis; }
    var q = flt.q.toLowerCase();
    var curRim = '', kinds = [], rims = [];
    for (var r = 0; r < doc.nRows; r++) {
      var kind = rowKind(r); kinds[r] = kind;
      if (kind === 'sect') curRim = String(valueOf(r, 0));
      rims[r] = curRim;
      if (kind !== 'data') { vis[r] = false; continue; }
      if (rowHidden(r)) { vis[r] = false; continue; }
      var ok = true;
      var sz = parseSizeStr(rowSizeText(r));
      if (flt.rim) ok = !!(sz && sz.rim === flt.rim);
      if (ok && flt.width) ok = !!(sz && sz.w === flt.width);
      if (ok && flt.series) ok = !!(sz && (flt.series === 'full' ? !sz.series : sz.series === flt.series));
      if (ok && flt.height) {
        var dia = rowDiaCm(r);
        var target = (flt.hUnit === 'in') ? parseFloat(flt.height) * 2.54 : parseFloat(flt.height);
        ok = !!(dia && isFinite(target) && Math.abs(dia - target) <= 1.5);
      }
      if (ok && flt.brand && String(valueOf(r, 2)).trim() !== flt.brand) ok = false;
      if (ok && flt.size && rowSizeText(r) !== flt.size) ok = false;
      if (ok && q && rowText(r).indexOf(q) < 0) {
        var _ah = false;   // ค้นเจอผ่าน "ชื่อเรียกอื่น" (alias) เช่น พิมพ์ 15-30 → เจอแถว 18.4-30
        if (window.ProductInfo) { try { var _al = ProductInfo.get(rowSizeText(r)).aliases || []; for (var _i = 0; _i < _al.length; _i++) { if (String(_al[_i]).toLowerCase().indexOf(q) >= 0) { _ah = true; break; } } } catch (e) {} }
        if (!_ah) ok = false;
      }
      if (ok && !String(valueOf(r, 2)).trim() && !rowSizeText(r)) ok = false;  // แถวเปล่าไม่ต้องโผล่
      vis[r] = ok;
      if (ok) lastMatchCount++;
    }
    // หัวเรื่อง/หัว section/หัวตาราง โผล่เมื่อ section นั้นมีผลลัพธ์
    if (view.mode === 'user' && lastMatchCount > USER_MAX) {
      tooMany = true;
      for (var rt = 0; rt < doc.nRows; rt++) vis[rt] = (rt < 2 && rowKind(rt) === 'title');
      return vis;
    }
    for (var r2 = 0; r2 < doc.nRows; r2++) {
      if (kinds[r2] === 'title' && r2 < 2) vis[r2] = q ? (rowText(r2).indexOf(q) >= 0) : true;   // ค้นหาอยู่ → แถวหัว (2 แถวแรก) ต้องตรงคำค้นด้วย ไม่งั้นซ่อน
      else if (kinds[r2] === 'sect' || kinds[r2] === 'head' || kinds[r2] === 'title') {
        // มองไปข้างหน้าจนจบ section
        var any = false;
        for (var rr = r2 + 1; rr < doc.nRows; rr++) {
          if (kinds[rr] === 'sect') break;
          if (kinds[rr] === 'data' && vis[rr]) { any = true; break; }
        }
        vis[r2] = any;
      }
    }
    return vis;
  }
  function setFilter(o) {
    flt.q = (o.q || '').trim(); flt.brand = o.brand || ''; flt.size = o.size || ''; flt.rim = o.rim || '';
    flt.width = o.width || ''; flt.series = o.series || ''; flt.height = (o.height || '').toString().trim(); flt.hUnit = o.hUnit || 'cm';
    flt.applied = !!o.applied;
    render();
    return lastMatchCount;
  }
  function clearFilter() { flt = { q: '', brand: '', size: '', rim: '', width: '', series: '', height: '', hUnit: 'cm', applied: false }; render(); }
  function filterOptions() {
    if (!cache) cache = {};
    var brands = {}, sizes = {}, rims = {}, widths = {}, seriesL = {}, heights = {}, hasFull = false;
    for (var r = 0; r < doc.nRows; r++) {
      var kind = rowKind(r);
      if (kind !== 'data') continue;
      var b = String(valueOf(r, 2)).trim(); if (b) brands[b] = 1;
      var s = rowSizeText(r);
      if (s && s !== 'ขนาดใหม่') {
        sizes[s] = 1;
        var p = parseSizeStr(s);
        if (p) {
          rims[p.rim] = 1; widths[p.w] = 1;
          if (p.series) seriesL[p.series] = 1; else hasFull = true;
        }
        var dia = rowDiaCm(r);
        if (dia) heights[dia.toFixed(1)] = 1;
      }
    }
    function numSort(o) { return Object.keys(o).sort(function (a, b) { return (+a) - (+b); }); }
    return { brands: Object.keys(brands).sort(), sizes: Object.keys(sizes).sort(),
      rims: numSort(rims), widths: numSort(widths), seriesList: numSort(seriesL), hasFullSeries: hasFull,
      heights: numSort(heights) };
  }

  // ---------- render ----------
  function colW(c) { return Math.round((doc.colW[c] || 64) * view.zoom); }
  function rowH(r) { return Math.round((doc.rowH[r] || 19) * view.zoom); }

  function render() {
    if (!cache) cache = {};
    if (!doc.hideRows) doc.hideRows = {}; if (!doc.hideCols) doc.hideCols = {};
    if (!doc.uHideRows) doc.uHideRows = {}; if (!doc.uHideCols) doc.uHideCols = {};
    if (doc.sizeCol == null) doc.sizeCol = 0;
    uiDark = !!(document.body && document.body.classList.contains('dark'));
    var isAdmin = view.mode === 'admin';
    var rowVis = computeRowVis();
    function firstVisIn(r0, rs) { for (var r = r0; r < r0 + rs && r < doc.nRows; r++) if (rowVis[r]) return r; return -1; }
    function visInSpan(r0, rs) { var n = 0; for (var r = r0; r < r0 + rs && r < doc.nRows; r++) if (rowVis[r]) n++; return Math.max(1, n); }
    function visColsInSpan(c0, cs) { var n = 0; for (var c = c0; c < c0 + cs && c < doc.nCols; c++) if (!colHidden(c)) n++; return Math.max(1, n); }
    var gutW = Math.round(30 * view.zoom);
    var totalW = gutW, colsHtml = '';
    for (var c = 0; c < doc.nCols; c++) if (!colHidden(c)) { var cw = colW(c); colsHtml += '<col style="width:' + cw + 'px">'; totalW += cw; }
    var html = '<table class="sg" style="font-size:' + (10 * view.zoom) + 'px;width:' + totalW + 'px"><colgroup><col style="width:' + gutW + 'px">' + colsHtml + '</colgroup>';
    // A-B-C header
    html += '<tr class="sg-abc" style="height:' + Math.round(18 * view.zoom) + 'px"><th class="sg-corner" title="เลือกทั้งหมด"></th>';
    for (var c2 = 0; c2 < doc.nCols; c2++) {
      if (colHidden(c2)) continue;
      var lockC = doc.adminCols && doc.adminCols[c2];
      var cmB = isAdmin && doc.columnMap && doc.columnMap[c2];
      var isStatusCol = isAdmin && doc.statusCol === c2;
      var isSizeCol = isAdmin && sizeCol() === c2;
      var hicons = [];
      if (isStatusCol) hicons.push(['📊', 'คอลัมน์สถานะ', 'c-tr']);
      else if (cmB) hicons.push([(cmB.mode === 'write' ? '✏️' : '🔗'), 'ผูก DB: ' + (window.DBX ? window.DBX.fieldLabel(cmB.field) : cmB.field) + (cmB.mode === 'write' ? ' · เขียนได้' : ' · อ่านอย่างเดียว'), '']);
      if (isSizeCol) hicons.push(['📏', 'คอลัมน์ขนาดหลัก (ใช้ตอนเพิ่มขนาด/รุ่น)', 'c-tl']);
      // ไอคอนทั่วไปใช้ 3 มุม: ขวาบน → ซ้ายบน → ซ้ายล่าง (ห้ามใช้ขวาล่าง)
      var HC3 = ['c-tr', 'c-tl', 'c-bl'], gi = 0;
      var marks = hicons.map(function (o) { return '<span class="sg-cic ' + (o[2] || HC3[gi++]) + '" title="' + esc(o[1]) + '">' + o[0] + '</span>'; }).join('');
      if (lockC && isAdmin) marks += '<span class="sg-cic c-br sg-lockic" title="' + esc(lockGlyph() + ' ' + lockDesc()) + '">' + lockGlyph() + '</span>';   // แม่กุญแจ มุมขวาล่าง
      html += '<th class="sg-h' + (lockC && isAdmin ? ' lockh' : '') + (cmB || isStatusCol || isSizeCol ? ' cmbound' : '') + '" data-hc="' + c2 + '">' + '<span class="sg-hname">' + XL2.colName(c2) + '</span>' + marks +
        (isAdmin ? '<span class="sg-rzc" data-rz="' + c2 + '"></span>' + (c2 > 0 ? '<span class="sg-rzc sg-rzc-l" data-rz="' + (c2 - 1) + '"></span>' : '') : '') + '</th>';
    }
    html += '</tr>';
    if (!isAdmin) html += '<tr><td class="sg-uview" colspan="999">👁️ มุมมองผู้ใช้ — อ่านอย่างเดียว · แถว/คอลัมน์ 🔒 ถูกซ่อน</td></tr>';

    for (var r = 0; r < doc.nRows; r++) {
      if (!rowVis[r]) continue;
      var lockR = doc.adminRows && doc.adminRows[r];
      var lnkG = rowCode(r);
      var lnkStatus = lnkG ? rowLinkStatus(r) : null;
      var lnkBad = (lnkStatus === 'missing' || lnkStatus === 'inactive');   // ลิงก์ค้าง/inactive
      html += '<tr data-row="' + r + '" style="height:' + rowH(r) + 'px">';
      html += '<td class="sg-g' + (lockR && isAdmin ? ' lockg' : '') + (lnkG ? ' glinked' : '') + (lnkBad ? ' glinked-bad' : '') + '" data-gr="' + r + '" title="แถว ' + (r + 1) + (lockR ? ' · 🔒เฉพาะแอดมิน' : '') + (isAdmin && doc.changes && doc.changes[r] ? ' · ✏️ มีการปรับราคารอบนี้' : '') + '">' + (r + 1) + (lnkG ? '<span class="glink-corner"></span>' : '') + (isAdmin && doc.changes && doc.changes[r] ? '<span class="gchg-corner"></span>' : '') + (isAdmin ? '<span class="sg-rzr" data-rzr="' + r + '"></span>' + (r > 0 ? '<span class="sg-rzr sg-rzr-t" data-rzr="' + (r - 1) + '"></span>' : '') : '') + '</td>';
      for (var c3 = 0; c3 < doc.nCols; c3++) {
        if (colHidden(c3)) continue;
        var k = key(r, c3);
        if (cover[k]) {
          var a = anchorOf(r, c3);
          var mA = doc.merges[a.r + ':' + a.c];
          // ถ้าแถวหัวผสานถูกกรองออก ให้แถวแรกที่มองเห็นเป็นเจ้าบ้านเซลล์แทน (เช่นช่องขนาด)
          if (c3 === a.c && !rowVis[a.r] && firstVisIn(a.r, mA.rs) === r) {
            html += tdHTML(a.r, c3, isAdmin, visInSpan(a.r, mA.rs), visColsInSpan(a.c, mA.cs));
          }
          continue;
        }
        var mg0 = doc.merges[k];
        if (mg0) html += tdHTML(r, c3, isAdmin, visInSpan(r, mg0.rs), visColsInSpan(c3, mg0.cs));
        else html += tdHTML(r, c3, isAdmin);
      }
      html += '</tr>';
    }
    if (view.mode === 'user' && !flt.applied) {
      html += '<tr><td class="sg-hint" colspan="999">🔍 เลือก ยี่ห้อ · ขนาด · ขอบ หรือพิมพ์คำค้น แล้วกด “ค้นหา” เพื่อแสดงรายการ</td></tr>';
    } else if (view.mode === 'user' && tooMany) {
      html += '<tr><td class="sg-hint sg-hint-warn" colspan="999">⚠️ พบ ' + lastMatchCount + ' รายการ — มากเกินไป (เกิน ' + USER_MAX + ') โปรดระบุ ยี่ห้อ / ขนาด / ขอบ เพิ่ม แล้วค้นหาใหม่</td></tr>';
    } else if (filterActive() && (view.mode === 'admin' || flt.applied) && lastMatchCount === 0) {
      html += '<tr><td class="sg-hint" colspan="999">ไม่พบรายการที่ตรงเงื่อนไข — ลองปรับคำค้นหรือกด ล้าง</td></tr>';
    }
    html += '</table>';
    rootEl.innerHTML = html;
    if (inputEl) rootEl.appendChild(inputEl);
    if (tipEl) rootEl.appendChild(tipEl);
    paintSel();
    updateBars();
    // เส้นขอบที่ผู้ใช้ตีไว้ วาดด้วย SVG overlay (คมชัด ต่อเนื่อง ตรงแบบ Excel)
    if (window.BorderOverlay) window.BorderOverlay.draw(rootEl, doc, view);
    // ดึงค่าจาก DB (ชั้นกลาง DBX) สำหรับคอลัมน์/ช่องที่ผูกไว้ — เติมแคชแล้ว re-render รอบเดียว
    scheduleDbFill();
  }

  // ---------- โหมดมืด: สีตัวอักษรที่มืดจนกลืนกับพื้น → ปรับเป็นสีคอนทราสต์ชั่วคราว (เฉพาะตอนแสดงผล ไม่แตะข้อมูลจริง)
  var uiDark = false;
  function darkContrast(hex) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var r = parseInt(h.substr(0, 2), 16), g = parseInt(h.substr(2, 2), 16), b = parseInt(h.substr(4, 2), 16);
    if (isNaN(r) || isNaN(g) || isNaN(b)) return h;
    var lum = 0.299 * r + 0.587 * g + 0.114 * b;
    if (lum >= 140) return h;                       // สว่างพออยู่แล้ว
    function f(c) { var v = Math.round(c + (255 - c) * 0.55).toString(16); return v.length < 2 ? '0' + v : v; }
    return f(r) + f(g) + f(b);
  }

  // ตัวเลขแบบปลอดภัย (ค่าเก่าอาจเป็นข้อความ — ไม่ให้ throw จนหน้าพัง)
  function nOr(v, fb) { return XL2.isNumeric(v) ? XL2.toN(v) : fb; }

  // เนื้อหาในช่อง: ถ้าคอลัมน์/ช่องผูกฟิลด์ 'dotRange' และแถวลิงก์ DB → แสดงช่วงปี DOT ลงสีตามอายุ · มิฉะนั้นข้อความปกติ
  function dotCellBody(r, c, disp, cl3c) {
    if (window.DOT) {
      var cmF = doc.columnMap && doc.columnMap[c] && doc.columnMap[c].field;
      var clF = cl3c && cl3c.field;
      if (cmF === 'dotRange' || clF === 'dotRange') {
        var code = (clF === 'dotRange' && cl3c) ? cl3c.code : rowCode(r);
        var p = (code && isCode13(code)) ? dbCache[code] : null;
        if (p) return window.DOT.cellHTML(p, uiDark ? darkContrast : null, view.zoom) || '';
      }
    }
    return esc(disp).replace(/\n/g, '<br>');
  }

  function tdHTML(r, c, isAdmin, effRs, effCs) {
    var cell = cellAt(r, c), s = (cell && cell.s) || {};
    var mg = doc.merges[key(r, c)];
    var st = '';
    if (s.bg) st += 'background:#' + s.bg + ';';
    if (s.fc) st += 'color:#' + ((uiDark && !s.bg) ? darkContrast(s.fc) : s.fc) + ';';
    if (s.b) st += 'font-weight:700;';
    if (s.i) st += 'font-style:italic;';
    if (s.u) st += 'text-decoration:underline;';
    if (s.fs) st += 'font-size:' + Math.round(s.fs * view.zoom) + 'px;';
    if (s.ff) st += "font-family:'" + s.ff + "',Arial,sans-serif;";
    if (s.va) st += 'vertical-align:' + s.va + ';';
    if (s.mn) st += "font-family:Consolas,'Courier New',monospace;letter-spacing:.5px;";
    // เส้นขอบ (s.bd) ไม่วาดเป็น CSS border บน td อีกต่อไป — ใช้ SVG overlay แทน (ดู border-overlay.js)
    // เพื่อเลี่ยงปัญหา border-collapse: เส้นสีชนเส้นตารางเทา / เส้นหนาเยื้องข้างเดียว / เส้นประไม่ต่อกัน
    // ซ่อนเส้นตารางเทาใต้ขอบที่ตีสีไว้ → เหลือเส้นเดียว (กันดูหนาซ้อนกับเส้นเทา)
    if (s.bd) {
      if (s.bd.t) st += 'border-top-color:transparent;';
      if (s.bd.b) st += 'border-bottom-color:transparent;';
      if (s.bd.l) st += 'border-left-color:transparent;';
      if (s.bd.r) st += 'border-right-color:transparent;';
    }
    st += 'text-align:' + (s.al || (XL2.isNumeric(valueOf(r, c)) ? 'right' : 'left')) + ';';
    // สีตามเงื่อนไข (Margin): บวกเขียว / ลบแดง — ตั้งค่าสีได้ที่ doc.condColors
    if (s.cond === 'pn') {
      var cv = valueOf(r, c);
      if (XL2.isNumeric(cv)) {
        var cn = XL2.toN(cv), cc = doc.condColors || {};
        var pc = cn > 0 ? (cc.pos || '008000') : cn < 0 ? (cc.neg || 'C00000') : null;
        if (pc) st += 'color:#' + ((uiDark && !s.bg) ? darkContrast(pc) : pc) + ';';
      }
    }
    var cls = 'sg-c';
    var adm = isAdmin && ((doc.adminRows && doc.adminRows[r]) || (doc.adminCols && doc.adminCols[c]));
    if (adm) cls += ' adm';
    if (cell && cell.f) cls += ' hasf';
    var disp = displayOf(r, c);
    if (view.secret) {
      var ds = String(disp);
      // ซ่อนตัวเลขล้วน (ไม่มีตัวอักษรผสม) ทั้งชีต → *** · ส่วนรหัส/ตัวอักษรยังโชว์
      if (ds !== '' && /[0-9]/.test(ds) && !/[A-Za-z\u0E00-\u0E7F]/.test(ds)) disp = '***';
      else if ((doc.adminCols && doc.adminCols[c]) && ds !== '' && !(cell && cell.f && /COGS|DEALER/i.test(cell.f))) disp = '•••';
    }
    var linked = (c === 3 && rowCode(r));
    // ไม่ใส่ไอคอน/มาร์กในเซลล์ — สถานะลิงก์แสดงที่แถบหัวแถวเท่านั้น (ตามที่ผู้ใช้ต้องการ)
    // สัญลักษณ์การปรับราคา
    var suffix = '', chg = doc.changes && doc.changes[r] && doc.changes[r][c];
    if (chg && chgExpired(chg)) chg = null;   // สัญลักษณ์ปรับราคา มีอายุ 7 วันจากเวลาอัปเดต แล้วหายไป
    if (chg && isAdmin) {
      // มุมเขียว = ปรับขึ้น · มุมส้ม = ปรับลง · เท่าเดิม = ไม่แสดง (ยังไม่ถือว่าเปลี่ยน)
      var aCur = valueOf(r, c);
      var aOld = nOr(chg.old, 0), aNew = nOr(aCur, aOld);
      if (aNew > aOld) cls += ' chg chg-up';
      else if (aNew < aOld) cls += ' chg chg-dn';
    } else if (chg && !isAdmin && chg.sent) {
      var eff = parseEff(chg.effectiveAt);
      if (eff.getTime() > Date.now()) {
        cls += ' pend pclick';
        suffix = ' <span class="pbadge">⏳</span>';
      } else {
        var curV = valueOf(r, c);
        var oldN = nOr(chg.old, 0), curN = nOr(curV, oldN);
        if (curN > oldN) { cls += ' pclick'; suffix = ' <span class="arr arr-up">▲</span>'; }
        else if (curN < oldN) { cls += ' pclick'; suffix = ' <span class="arr arr-dn">▼</span>'; }
      }
    }
    var rsv = (effRs != null) ? effRs : (mg ? mg.rs : 0);
    var csv = (effCs != null) ? effCs : (mg ? mg.cs : 0);
    var span = (rsv > 1 || csv > 1 || mg) ? ' rowspan="' + Math.max(1, rsv) + '" colspan="' + Math.max(1, csv) + '"' : '';
    // มาร์กมุมบนซ้าย: ช่องที่ลิงก์เฉพาะช่อง (cell-link 3C)
    var cl3c = doc.cellLinks && doc.cellLinks[r] && doc.cellLinks[r][c];
    var cellMark = cl3c ? '<span class="celllink-corner"></span>' : '';
    if (cl3c) cls += ' celllinked';
    if (c === sizeCol() && window.ProductInfo && rowKind(r) === 'data') {
      var _piSz = rowSizeText(r);
      if (_piSz) { cellMark += ProductInfo.isComplete(_piSz) ? '<span class="sg-pi-done" title="ข้อมูลขนาด/ชนิดครบ"></span>' : '<span class="sg-pi-todo" title="ยังไม่ได้ใส่รายละเอียดของขนาดนี้"></span>'; cls += ' sg-pimark'; }
    }
    // คอลัมน์สถานะ: แสดงจุดสี/ไอคอนแทนค่า (เฉพาะแถวที่ลิงก์ DB)
    if (doc.statusCol === c && window.DBX && rowCode(r)) {
      var stInner = statusCellInner(r);
      return '<td class="' + cls + ' sg-statuscell" data-r="' + r + '" data-c="' + c + '"' + span + (st ? ' style="' + st + '"' : '') + ' title="คลิกดูรายละเอียด · คลิกขวาตั้ง auto/manual">' + stInner + '</td>';
    }
    return '<td class="' + cls + '" data-r="' + r + '" data-c="' + c + '"' + span + (st ? ' style="' + st + '"' : '') +
      (cl3c ? ' title="🗄️ ลิงก์เฉพาะช่อง: ' + esc(cl3c.code) + ' · ' + esc(window.DBX ? window.DBX.fieldLabel(cl3c.field) : cl3c.field) + '"' : (linked ? ' title="🔗 ' + esc(rowLinkLabel(r)) + '"' : (chg && isAdmin && cls.indexOf(' chg') >= 0 ? ' title="✏️ ปรับรอบนี้ · เดิม: ' + esc(XL2.fmtNum(nOr(chg.old, 0))) + (cls.indexOf('chg-up') >= 0 ? ' (ขึ้น)' : ' (ลง)') + '"' : ''))) +
      '>' + cellMark + dotCellBody(r, c, disp, cl3c) + suffix + '</td>';
  }

  // ---------- selection ----------
  function cellEl(r, c) { var a = anchorOf(r, c); return rootEl.querySelector('td[data-r="' + a.r + '"][data-c="' + a.c + '"]'); }
  function range() { return { r1: Math.min(sel.r, sel.ar), r2: Math.max(sel.r, sel.ar), c1: Math.min(sel.c, sel.ac), c2: Math.max(sel.c, sel.ac) }; }

  // Ctrl+คลิกหัวคอลัมน์/แถว → เลือกหลายอันแบบไม่ต่อเนื่อง (คอลัมน์กับแถวแยกชุดกัน) — สำหรับลากปรับขนาดพร้อมกัน
  var multiCols = [], multiRows = [];
  function clearMulti() { if (multiCols.length || multiRows.length) { multiCols = []; multiRows = []; paintMulti(); } }
  function paintMulti() {
    rootEl.querySelectorAll('.sg-h.multi,.sg-g.multi').forEach(function (e) { e.classList.remove('multi'); });
    rootEl.querySelectorAll('.sg-c.multisel').forEach(function (e) { e.classList.remove('multisel'); });
    multiCols.forEach(function (c) {
      var h = rootEl.querySelector('.sg-h[data-hc="' + c + '"]'); if (h) h.classList.add('multi');
      // ไฮไลต์ตัวคอลัมน์ในตารางด้วย — ข้ามเซลล์ผสานข้ามคอลัมน์ (กันลามไปคอลัมน์อื่น)
      rootEl.querySelectorAll('td.sg-c[data-c="' + c + '"]').forEach(function (td) {
        if ((td.colSpan || 1) > 1) return;
        td.classList.add('multisel');
      });
    });
    multiRows.forEach(function (r) {
      var g = rootEl.querySelector('.sg-g[data-gr="' + r + '"]'); if (g) g.classList.add('multi');
      // ไฮไลต์ตัวแถวในตารางด้วย — ข้ามเซลล์ผสานข้ามแถว
      rootEl.querySelectorAll('td.sg-c[data-r="' + r + '"]').forEach(function (td) {
        if ((td.rowSpan || 1) > 1) return;
        td.classList.add('multisel');
      });
    });
  }

  function paintSel() {
    rootEl.querySelectorAll('.sg-c.sel,.sg-c.act').forEach(function (e) { e.classList.remove('sel', 'act'); });
    rootEl.querySelectorAll('.sg-h.on,.sg-g.on').forEach(function (e) { e.classList.remove('on'); });
    var R = range();
    // เลือกทั้งคอลัมน์ / ทั้งแถว → ไม่ระบายเซลล์ผสานที่ล้นออกนอกแกนที่เลือก
    // (เลือกคอลัมน์เดียว จะไม่ลามไปไฮไลต์แบนเนอร์ที่ผสานข้ามหลายคอลัมน์ในบางแถว เช่น "Dealer" · เลือกแถวก็เช่นกัน)
    var colSel = (R.c1 === R.c2 && R.r1 === 0 && R.r2 === doc.nRows - 1);
    var rowSel = (R.r1 === R.r2 && R.c1 === 0 && R.c2 === doc.nCols - 1);
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) {
      // ช่องผสานที่จุดตั้งต้นอยู่นอกกรอบที่ลาก — ไม่ระบาย (ไม่ให้แถว/ตารางอื่นติดมาด้วย)
      var a = anchorOf(r, c);
      if (a.r < R.r1 || a.r > R.r2 || a.c < R.c1 || a.c > R.c2) continue;
      if (colSel || rowSel) {
        var mg = doc.merges && doc.merges[a.r + ':' + a.c];
        if (mg) {
          if (colSel && a.c + (mg.cs || 1) - 1 > R.c2) continue;  // ผสานล้นไปคอลัมน์อื่น
          if (rowSel && a.r + (mg.rs || 1) - 1 > R.r2) continue;  // ผสานล้นไปแถวอื่น
        }
      }
      var el = rootEl.querySelector('td[data-r="' + a.r + '"][data-c="' + a.c + '"]');
      if (el) el.classList.add('sel');
    }
    var act = cellEl(sel.r, sel.c); if (act) act.classList.add('act');
    for (var c2 = R.c1; c2 <= R.c2; c2++) { var h = rootEl.querySelector('.sg-h[data-hc="' + c2 + '"]'); if (h) h.classList.add('on'); }
    for (var r2 = R.r1; r2 <= R.r2; r2++) { var g = rootEl.querySelector('.sg-g[data-gr="' + r2 + '"]'); if (g) g.classList.add('on'); }
    paintMulti();
    drawSelRect();
    updateBars();
  }
  // กรอบสีรอบช่วงที่เลือกทั้งหมด (เส้นทึบสีที่บันทึกไว้ — แบบ Excel)
  function drawSelRect() {
    var box = document.getElementById('selRect');
    var cells = rootEl.querySelectorAll('.sg-c.sel, .sg-c.act, .sg-c.fillpv');
    rootEl.classList.toggle('hasrange', cells.length >= 2);
    if (cells.length < 2) { if (box) box.style.display = 'none'; return; }
    var gr = rootEl.getBoundingClientRect();
    var minL = 1e9, minT = 1e9, maxR = -1e9, maxB = -1e9;
    cells.forEach(function (c) { var r = c.getBoundingClientRect(); if (r.width === 0 && r.height === 0) return; minL = Math.min(minL, r.left); minT = Math.min(minT, r.top); maxR = Math.max(maxR, r.right); maxB = Math.max(maxB, r.bottom); });
    if (!box) { box = document.createElement('div'); box.id = 'selRect'; rootEl.appendChild(box); }
    box.style.display = 'block';
    box.style.left = (minL - gr.left) + 'px';
    box.style.top = (minT - gr.top) + 'px';
    box.style.width = (maxR - minL) + 'px';
    box.style.height = (maxB - minT) + 'px';
  }

  function setActive(r, c, keepAnchor, noScroll) {
    r = Math.max(0, Math.min(doc.nRows - 1, r));
    c = Math.max(0, Math.min(doc.nCols - 1, c));
    sel.r = r; sel.c = c;
    if (!keepAnchor) { sel.ar = r; sel.ac = c; }
    paintSel();
    if (noScroll) return;   // คลิกเลือกช่องที่เห็นอยู่แล้ว → ไม่ต้องเลื่อนจอ (กันตารางขยับ)
    var el = cellEl(r, c);
    if (el) {
      var rect = el.getBoundingClientRect(), pr = rootEl.getBoundingClientRect();
      if (rect.bottom > pr.bottom - 6) rootEl.scrollTop += rect.bottom - pr.bottom + 26;
      if (rect.top < pr.top + 24) rootEl.scrollTop -= (pr.top + 24 - rect.top);
      if (rect.right > pr.right - 6) rootEl.scrollLeft += rect.right - pr.right + 26;
      if (rect.left < pr.left + 34) rootEl.scrollLeft -= (pr.left + 34 - rect.left);
    }
  }

  function updateBars() {
    paintClip();
    if (nameEl) nameEl.textContent = XL2.refStr(sel.r, sel.c);
    var fsB = document.getElementById('fsBox');
    if (fsB && document.activeElement !== fsB) { var fc = cellAt(sel.r, sel.c); fsB.value = (fc && fc.s && fc.s.fs) ? fc.s.fs : 10; }
    if (fxEl && !editing) {
      var cell = cellAt(sel.r, sel.c);
      fxEl.value = cell ? (cell.f ? cell.f : (cell.v != null ? String(cell.v) : '')) : '';
    }
    if (statusEl) {
      var cell = cellAt(sel.r, sel.c);
      var info = cell && cell.f ? 'สูตร: ' + cell.f : (cell && cell.t === 'text' ? 'ข้อความ' : cell && cell.t === 'num' ? 'ตัวเลข' : 'อัตโนมัติ');
      statusEl.innerHTML = '<b>' + XL2.refStr(sel.r, sel.c) + '</b> · ' + esc(info);
    }
    if (sumEl) {
      var R = range(), nums = [], cnt = 0;
      for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) {
        var v = valueOf(r, c);
        if (v !== '' && v != null) { cnt++; if (XL2.isNumeric(v)) nums.push(XL2.toN(v)); }
      }
      if (nums.length > 1) {
        var sum = nums.reduce(function (a, b) { return a + b; }, 0);
        sumEl.textContent = 'ผลรวม: ' + XL2.fmtNum(sum) + ' · เฉลี่ย: ' + XL2.fmtNum(sum / nums.length) + ' · จำนวน: ' + cnt;
      } else sumEl.textContent = '';
    }
  }

  // ---------- price-change tracking (ปรับปรุงรอบนี้) ----------
  var PRICE_NAME = { 7: 'ราคาตั้ง', 13: 'SUB-B', 16: 'SUB-A', 19: 'SUB-S' };
  function recordChange(r, c, oldVal) {
    if (!PRICE_NAME[c]) return;
    if (rowKind(r) !== 'data') return;
    doc.changes = doc.changes || {};
    var rc = doc.changes[r] = doc.changes[r] || {};
    if (!rc[c]) rc[c] = { old: oldVal, ts: Date.now() };   // เก็บราคาเดิมของรอบนี้ไว้ครั้งแรกครั้งเดียว
  }
  function parseEff(s) {
    if (!s || s === 'ทันที') return new Date(0);
    var d = new Date(String(s).replace(' ', 'T'));
    return isNaN(d.getTime()) ? new Date(0) : d;
  }
  // สัญลักษณ์ปรับราคา มีอายุ 7 วัน นับจากเวลาที่มีผล (เฉพาะที่ส่งแล้ว) — ครบแล้วหาย
  var CHG_TTL = 7 * 86400 * 1000;
  function chgExpired(chg) {
    if (!chg || !chg.sent) return false;
    var base = chg.effectiveAt ? parseEff(chg.effectiveAt).getTime() : (chg.ts || 0);
    if (!base) return false;
    return (Date.now() - base) > CHG_TTL;
  }
  // ถ้าปรับกลับมาเท่าราคาเดิม (และยังไม่เผยแพร่) → ลบเครื่องหมายทิ้ง ถือว่าไม่มีการเปลี่ยนแปลง
  function pruneChange(r, c) {
    var rc = doc.changes && doc.changes[r];
    if (!rc || !rc[c] || rc[c].sent) return;
    var cur = valueOf(r, c);
    var oldN = nOr(rc[c].old, 0);
    var curN = nOr(cur, NaN);
    if (curN === oldN) {
      delete rc[c];
      if (!Object.keys(rc).length) delete doc.changes[r];
    }
  }
  // มีการปรับจริงอย่างน้อย 1 ช่อง (ไม่นับที่ปรับกลับมาเท่าเดิม)
  function rowHasRealChange(r) {
    var rc = doc.changes && doc.changes[r];
    if (!rc) return false;
    return Object.keys(rc).some(function (c) {
      var e = rc[c];
      if (e.sent) return true;
      var cur = valueOf(r, +c);
      var oldN = nOr(e.old, 0);
      var curN = nOr(cur, oldN);
      return curN !== oldN;
    });
  }

  function clearChanges() {
    if (view.mode !== 'admin') return;
    pushUndo();
    doc.changes = {};
    afterChange(); toast('ล้างเครื่องหมายการปรับปรุง — เริ่มรอบใหม่');
  }

  // ---------- editing ----------
  function startEdit(initial, viaFx) {
    if (view.mode !== 'admin') { toast('มุมมองผู้ใช้ — อ่านอย่างเดียว'); return; }
    var a = anchorOf(sel.r, sel.c);
    hideSizePop();
    editing = { r: a.r, c: a.c, viaFx: !!viaFx };
    var el = cellEl(a.r, a.c);
    if (el && !viaFx) {
      inputEl.style.display = 'block';
      inputEl.style.left = el.offsetLeft + 'px';
      inputEl.style.top = el.offsetTop + 'px';
      inputEl.style.width = Math.max(40, el.offsetWidth - 1) + 'px';
      inputEl.style.height = (el.offsetHeight - 1) + 'px';
      inputEl.style.fontSize = (10 * view.zoom) + 'px';
      var cell = cellAt(a.r, a.c);
      inputEl.value = (initial != null) ? initial : (cell ? (cell.f || (cell.v != null ? String(cell.v) : '')) : '');
      inputEl.focus();
      if (initial == null) inputEl.select();
    }
    if (fxEl) fxEl.value = inputEl.value;
  }
  function commitEdit(move) {
    if (!editing) return;
    var r = editing.r, c = editing.c;
    var val = editing.viaFx ? fxEl.value : inputEl.value;
    var cell = cellAt(r, c);
    var oldRepr = cell ? (cell.f || String(cell.v != null ? cell.v : '')) : '';
    if (oldRepr !== val) {
      pushUndo();
      recordChange(r, c, valueOf(r, c));
      var nc = ensureCell(r, c);
      if (val.charAt(0) === '=') { nc.f = val; }
      else {
        delete nc.f;
        nc.v = val;
        if (nc.t === 'num' && val !== '' && !XL2.isNumeric(val)) { /* เก็บตามพิมพ์ แต่เตือน */ toast('⚠ ช่องนี้กำหนดเป็นตัวเลข'); }
      }
      invalidate();
      pruneChange(r, c);
      afterChange();
    }
    editing = null;
    inputEl.style.display = 'none';
    if (move === 'down') setActive(stepRow(sel.r, 1), sel.c);
    else if (move === 'up') setActive(stepRow(sel.r, -1), sel.c);
    else if (move === 'right') setActive(sel.r, stepCol(sel.c, 1));
    else if (move === 'left') setActive(sel.r, stepCol(sel.c, -1));
    else paintSel();
    rootEl.focus();
  }
  function cancelEdit() { editing = null; inputEl.style.display = 'none'; updateBars(); rootEl.focus(); }

  // ---------- clipboard ----------
  function doCopy(cut) {
    var R = range(), rows = [], tsv = [];
    for (var r = R.r1; r <= R.r2; r++) {
      var line = [], vals = [];
      for (var c = R.c1; c <= R.c2; c++) {
        var cell = cellAt(r, c);
        vals.push(cell ? { f: cell.f, v: cell.v, t: cell.t, s: JSON.parse(JSON.stringify(cell.s || {})) } : null);
        line.push(String(valueOf(r, c)));
      }
      rows.push(vals); tsv.push(line.join('\t'));
    }
    clip = { rows: rows, r0: R.r1, c0: R.c1, range: { r1: R.r1, r2: R.r2, c1: R.c1, c2: R.c2 } };
    // จำว่าคัดลอกทั้งแถว/ทั้งคอลัมน์ (ไว้ใช้ “แทรกที่คัดลอก” แบบ Excel)
    clip.fullRows = (R.c1 === 0 && R.c2 === doc.nCols - 1);
    clip.fullCols = (R.r1 === 0 && R.r2 === doc.nRows - 1);
    if (clip.fullRows) {
      clip.rowHs = []; for (var rh = R.r1; rh <= R.r2; rh++) clip.rowHs.push(doc.rowH[rh] || 19);
      clip.mergesR = [];
      Object.keys(doc.merges).forEach(function (mk) {
        var p = mk.split(':'), mr = +p[0], mc2 = +p[1], m = doc.merges[mk];
        if (mr >= R.r1 && mr + m.rs - 1 <= R.r2) clip.mergesR.push({ dr: mr - R.r1, c: mc2, rs: m.rs, cs: m.cs });
      });
    }
    if (clip.fullCols) {
      clip.colWs = []; for (var cw = R.c1; cw <= R.c2; cw++) clip.colWs.push(doc.colW[cw] || 64);
      clip.mergesC = [];
      Object.keys(doc.merges).forEach(function (mk) {
        var p = mk.split(':'), mr = +p[0], mc3 = +p[1], m = doc.merges[mk];
        if (mc3 >= R.c1 && mc3 + m.cs - 1 <= R.c2) clip.mergesC.push({ r: mr, dc: mc3 - R.c1, rs: m.rs, cs: m.cs });
      });
    }
    try { if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(tsv.join('\n')).catch(function () {}); } catch (e) {}
    clip.cut = !!cut;   // ตัด = ยังไม่ลบต้นทาง รอจนกว่าจะวาง (เหมือน Excel)
    paintClip();
    toast((cut ? 'ตัดแล้ว — เลือกปลายทางแล้ววาง (Ctrl+V)' : 'คัดลอกแล้ว' + (clip.fullRows ? ' (' + rows.length + ' แถวเต็ม)' : clip.fullCols ? ' (ทั้งคอลัมน์)' : '')) + ' · Esc = ยกเลิก');
  }

  // ขอบประช่วงที่คัดลอก (เส้นประเขียวแบบ Excel) · Esc = ยกเลิก
  function paintClip() {
    rootEl.querySelectorAll('.sg-c.cpm').forEach(function (e) { e.classList.remove('cpm'); });
    if (!clip || !clip.range) return;
    var R = clip.range;
    for (var r = R.r1; r <= R.r2 && r < doc.nRows; r++) for (var c = R.c1; c <= R.c2 && c < doc.nCols; c++) {
      var el = cellEl(r, c); if (el) el.classList.add('cpm');
    }
  }
  function clearClip(silent) {
    if (!clip) return;
    clip = null;
    paintClip();
    if (!silent) toast('ยกเลิกการคัดลอกแล้ว — คัดลอก/ตัดใหม่ได้เลย');
  }
  function doPaste() {
    if (!clip || view.mode !== 'admin') return;
    pushUndo();
    var R = range();
    var dr = R.r1 - clip.r0, dc = R.c1 - clip.c0;
    var isCut = !!clip.cut;
    var nRows = clip.rows.length, nCols = clip.rows[0] ? clip.rows[0].length : 0;
    for (var i = 0; i < nRows; i++) for (var j = 0; j < clip.rows[i].length; j++) {
      var r = R.r1 + i, c = R.c1 + j;
      if (r >= doc.nRows || c >= doc.nCols) continue;
      var src = clip.rows[i][j];
      if (PRICE_NAME[c]) recordChange(r, c, valueOf(r, c));
      if (!src) { delete doc.cells[key(r, c)]; continue; }
      var nc = ensureCell(r, c);
      nc.t = src.t; nc.s = JSON.parse(JSON.stringify(src.s));
      // ตัด→วาง = ย้าย (สูตรไม่เลื่อนอ้างอิง เหมือน Excel) · คัดลอก→วาง = เลื่อนอ้างอิง
      if (src.f) { nc.f = isCut ? src.f : XL2.shiftFormula(src.f, dr, dc); delete nc.v; }
      else { nc.v = src.v; delete nc.f; }
    }
    if (isCut && clip.range) {
      // ลบต้นทางเฉพาะส่วนที่ไม่ทับกับปลายทาง — ถึงตอนนี้ค่อยตัดจริง
      var S = clip.range;
      for (var sr = S.r1; sr <= S.r2; sr++) for (var sc = S.c1; sc <= S.c2; sc++) {
        if (sr >= R.r1 && sr < R.r1 + nRows && sc >= R.c1 && sc < R.c1 + nCols) continue;
        delete doc.cells[key(sr, sc)];
      }
      clip = null;   // ตัดใช้ได้ครั้งเดียว — จบงาน เส้นกระพริบหาย
    }
    afterChange(); toast(isCut ? 'ย้ายเรียบร้อย (ตัด → วาง)' : 'วางแล้ว');
  }
  function delRange() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range();
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) {
      var cell = cellAt(r, c);
      if (cell) { delete cell.f; cell.v = ''; }
    }
    afterChange();
  }

  // ---------- fill handle (ลากมุมขวาล่าง copy ตามแถว/คอลัมน์) ----------
  function fillTo(tr, tc) {
    var R = range();
    pushUndo();
    // ทิศทางหลัก: แนวตั้งหรือแนวนอน
    if (tr > R.r2) { // ลงล่าง
      for (var r = R.r2 + 1; r <= tr && r < doc.nRows; r++) for (var c = R.c1; c <= R.c2; c++) copyShift(R.r1 + ((r - R.r1) % (R.r2 - R.r1 + 1)), c, r, c);
      sel.ar = R.r1; sel.ac = R.c1; sel.r = tr; sel.c = R.c2;
    } else if (tc > R.c2) { // ไปขวา
      for (var c2 = R.c2 + 1; c2 <= tc && c2 < doc.nCols; c2++) for (var r2 = R.r1; r2 <= R.r2; r2++) copyShift(r2, R.c1 + ((c2 - R.c1) % (R.c2 - R.c1 + 1)), r2, c2);
      sel.ar = R.r1; sel.ac = R.c1; sel.r = R.r2; sel.c = tc;
    }
    afterChange();
  }
  function copyShift(sr, sc, tr, tc) {
    var src = cellAt(sr, sc);
    if (!src) { delete doc.cells[key(tr, tc)]; return; }
    var nc = ensureCell(tr, tc);
    nc.t = src.t; nc.s = JSON.parse(JSON.stringify(src.s || {}));
    if (src.f) { nc.f = XL2.shiftFormula(src.f, tr - sr, tc - sc); delete nc.v; }
    else { nc.v = src.v; delete nc.f; }
  }

  // ---------- structure ops ----------
  function remapAll(fn) {
    // fn(r,c) -> [nr,nc] or null (deleted)
    var nc = {}, nm = {};
    Object.keys(doc.cells).forEach(function (k) {
      var p = k.split(':'), out = fn(+p[0], +p[1]);
      if (out) nc[out[0] + ':' + out[1]] = doc.cells[k];
    });
    Object.keys(doc.merges).forEach(function (k) {
      var p = k.split(':'), out = fn(+p[0], +p[1]);
      if (out) nm[out[0] + ':' + out[1]] = doc.merges[k];
    });
    doc.cells = nc; doc.merges = nm;
    // rewrite formulas
    Object.keys(doc.cells).forEach(function (k) {
      var cell = doc.cells[k];
      if (cell.f) cell.f = XL2.remapFormula(cell.f, function (r, c) { return fn(r, c); });
    });
  }
  function insertRow(at, silent) { insertRows(at, 1, silent); }
  function insertRows(at, n, silent) {
    if (view.mode !== 'admin') return;
    n = Math.max(1, n || 1);
    if (!silent) pushUndo();
    remapAll(function (r, c) { return [r >= at ? r + n : r, c]; });
    // ขยายช่วงผสานที่คร่อมจุดแทรก
    Object.keys(doc.merges).forEach(function (k) {
      var p = k.split(':'), r = +p[0], m = doc.merges[k];
      if (r < at && r + m.rs > at) m.rs += n;
    });
    for (var i = 0; i < n; i++) doc.rowH.splice(at, 0, doc.rowH[at] || 19);
    var na = {}; Object.keys(doc.adminRows).forEach(function (r) { r = +r; na[r >= at ? r + n : r] = 1; }); doc.adminRows = na;
    var nl = {}; Object.keys(doc.rowLinks || {}).forEach(function (r) { var code = doc.rowLinks[r]; r = +r; nl[r >= at ? r + n : r] = code; }); doc.rowLinks = nl;
    var ns = {}; Object.keys(doc.rowSchedules || {}).forEach(function (r) { var w = doc.rowSchedules[r]; r = +r; ns[r >= at ? r + n : r] = w; }); doc.rowSchedules = ns;
    var nch = {}; Object.keys(doc.changes || {}).forEach(function (r) { var v = doc.changes[r]; r = +r; nch[r >= at ? r + n : r] = v; }); doc.changes = nch;
    doc.nRows += n;
    if (!silent) { afterChange(); toast('แทรก ' + n + ' แถวที่แถว ' + (at + 1)); }
  }
  function deleteRow() {
    if (view.mode !== 'admin') return;
    var R = range(), n = R.r2 - R.r1 + 1;
    if (doc.nRows - n < 1) return;
    pushUndo();
    remapAll(function (r, c) { if (r >= R.r1 && r <= R.r2) return null; return [r > R.r2 ? r - n : r, c]; });
    // หดช่วงผสานที่คร่อมแถวที่ลบ
    Object.keys(doc.merges).forEach(function (k) {
      var p = k.split(':'), r = +p[0], m = doc.merges[k];
      var top = r < R.r1 ? r : null;
      if (top != null) {
        var spanEnd = r + m.rs - 1 + n; // พิกัดเดิมก่อนลบ (anchor ไม่ถูกย้าย)
        var oldEnd = r + m.rs - 1;
        // m.rs ยังอิงจำนวนเดิม: นับจำนวนแถวที่ถูกลบภายในช่วงเดิม
        var ov = Math.max(0, Math.min(R.r2, oldEnd) - R.r1 + 1);
        if (ov > 0) {
          m.rs -= ov;
          if (m.rs <= 1 && m.cs <= 1) delete doc.merges[k];
        }
      }
    });
    doc.rowH.splice(R.r1, n);
    var na = {}; Object.keys(doc.adminRows).forEach(function (r) { r = +r; if (r < R.r1) na[r] = 1; else if (r > R.r2) na[r - n] = 1; }); doc.adminRows = na;
    var nl = {}; Object.keys(doc.rowLinks || {}).forEach(function (r) { var code = doc.rowLinks[r]; r = +r; if (r < R.r1) nl[r] = code; else if (r > R.r2) nl[r - n] = code; }); doc.rowLinks = nl;
    var ns = {}; Object.keys(doc.rowSchedules || {}).forEach(function (r) { var w = doc.rowSchedules[r]; r = +r; if (r < R.r1) ns[r] = w; else if (r > R.r2) ns[r - n] = w; }); doc.rowSchedules = ns;
    var nch = {}; Object.keys(doc.changes || {}).forEach(function (r) { var v = doc.changes[r]; r = +r; if (r < R.r1) nch[r] = v; else if (r > R.r2) nch[r - n] = v; }); doc.changes = nch;
    doc.nRows -= n;
    setActive(Math.min(R.r1, doc.nRows - 1), sel.c);
    afterChange(); toast('ลบ ' + n + ' แถว');
  }
  function insertCol(at) { insertCols(at, 1); }
  function insertCols(at, n, silent) {
    if (view.mode !== 'admin') return;
    n = Math.max(1, n || 1);
    if (!silent) pushUndo();
    remapAll(function (r, c) { return [r, c >= at ? c + n : c]; });
    Object.keys(doc.merges).forEach(function (k) {
      var p = k.split(':'), c = +p[1], m = doc.merges[k];
      if (c < at && c + m.cs > at) m.cs += n;
    });
    for (var i = 0; i < n; i++) doc.colW.splice(at, 0, doc.colW[at] || 64);
    var na = {}; Object.keys(doc.adminCols).forEach(function (c) { c = +c; na[c >= at ? c + n : c] = 1; }); doc.adminCols = na;
    doc.nCols += n;
    if (!silent) { afterChange(); toast('แทรก ' + n + ' คอลัมน์ที่ ' + XL2.colName(at)); }
  }
  function deleteCol() {
    if (view.mode !== 'admin') return;
    var R = range(), n = R.c2 - R.c1 + 1;
    if (doc.nCols - n < 1) return;
    pushUndo();
    remapAll(function (r, c) { if (c >= R.c1 && c <= R.c2) return null; return [r, c > R.c2 ? c - n : c]; });
    doc.colW.splice(R.c1, n);
    var na = {}; Object.keys(doc.adminCols).forEach(function (c) { c = +c; if (c < R.c1) na[c] = 1; else if (c > R.c2) na[c - n] = 1; }); doc.adminCols = na;
    doc.nCols -= n;
    setActive(sel.r, Math.min(R.c1, doc.nCols - 1));
    afterChange(); toast('ลบ ' + n + ' คอลัมน์');
  }
  // ---------- แทรกสิ่งที่คัดลอก (ทั้งแถว/ทั้งคอลัมน์ หลายรายการ แบบ Excel) ----------
  function insertCopiedRows() {
    if (view.mode !== 'admin' || !clip || !clip.fullRows) return;
    pushUndo();
    var at = range().r1, n = clip.rows.length;
    insertRows(at, n, true);
    for (var i = 0; i < n; i++) {
      if (clip.rowHs && clip.rowHs[i]) doc.rowH[at + i] = clip.rowHs[i];
      for (var j = 0; j < clip.rows[i].length && j < doc.nCols; j++) {
        var src = clip.rows[i][j];
        if (!src) { delete doc.cells[key(at + i, j)]; continue; }
        var nc = ensureCell(at + i, j);
        nc.t = src.t; nc.s = JSON.parse(JSON.stringify(src.s));
        if (src.f) { nc.f = XL2.shiftFormula(src.f, (at + i) - (clip.r0 + i), 0); delete nc.v; }
        else { nc.v = src.v; delete nc.f; }
      }
    }
    (clip.mergesR || []).forEach(function (m) { doc.merges[(at + m.dr) + ':' + m.c] = { rs: m.rs, cs: m.cs }; });
    afterChange();
    sel.ar = at; sel.r = at + n - 1; sel.ac = 0; sel.c = doc.nCols - 1; paintSel();
    clearClip(true);   // แทรกแล้วล้างคลิปบอร์ด (เหมือน Excel)
    toast('แทรกแถวที่คัดลอก ' + n + ' แถว');
  }
  function insertCopiedCols() {
    if (view.mode !== 'admin' || !clip || !clip.fullCols) return;
    pushUndo();
    var at = range().c1, n = clip.rows[0].length;
    insertCols(at, n, true);
    for (var i = 0; i < clip.rows.length && i < doc.nRows; i++) {
      for (var j = 0; j < n; j++) {
        var src = clip.rows[i][j];
        if (!src) { delete doc.cells[key(i, at + j)]; continue; }
        var nc = ensureCell(i, at + j);
        nc.t = src.t; nc.s = JSON.parse(JSON.stringify(src.s));
        if (src.f) { nc.f = XL2.shiftFormula(src.f, 0, (at + j) - (clip.c0 + j)); delete nc.v; }
        else { nc.v = src.v; delete nc.f; }
      }
      if (clip.colWs) for (var w = 0; w < n; w++) doc.colW[at + w] = clip.colWs[w];
    }
    (clip.mergesC || []).forEach(function (m) { doc.merges[m.r + ':' + (at + m.dc)] = { rs: m.rs, cs: m.cs }; });
    afterChange();
    sel.ac = at; sel.c = at + n - 1; sel.ar = 0; sel.r = doc.nRows - 1; paintSel();
    clearClip(true);
    toast('แทรกคอลัมน์ที่คัดลอก ' + n + ' คอลัมน์');
  }

  function addRowsBottom(n) {
    if (view.mode !== 'admin') return;
    pushUndo(); doc.nRows += n; afterChange(); toast('เพิ่ม ' + n + ' แถวท้ายชีต');
  }

  // ---------- เพิ่มขนาด/เพิ่มรุ่น (เหมือน v1) ----------
  function sizeGroupOf(r) {
    var sc = sizeCol();
    var a = anchorOf(r, sc);
    var m = doc.merges[a.r + ':' + sc];
    if (m && m.cs !== 1) m = null;   // ผสานแนวนอน (หัวตาราง/แถบ) ไม่ใช่กลุ่มขนาด
    return { top: a.r, n: m ? m.rs : 1, hasMerge: !!m };
  }
  function copyRowPattern(srcR, dstR) {
    var sc = sizeCol();
    for (var c = 0; c < doc.nCols; c++) {
      if (c === sc) continue;
      var src = cellAt(srcR, c);
      if (!src) continue;
      var nc = ensureCell(dstR, c);
      nc.t = src.t;
      nc.s = JSON.parse(JSON.stringify(src.s || {}));
      if (src.f) { nc.f = XL2.shiftFormula(src.f, dstR - srcR, 0); delete nc.v; }
      else { nc.v = (c === 1 || c === 4 || c === 5) ? src.v : ''; delete nc.f; }  // คัดลอก ชั้น/DOT/ขอบสี ที่เหลือเว้นว่าง
    }
  }
  function addModelRow() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var r = sel.r, g = sizeGroupOf(r);
    var at = r + 1;
    insertRow(at, true);
    copyRowPattern(r, at);
    // ให้แถวใหม่อยู่ในกลุ่มขนาดเดียวกัน (ขยายผสานคอลัมน์ A)
    var mk = g.top + ':' + sizeCol(), m = g.hasMerge ? doc.merges[mk] : null;
    if (m) { if (at >= g.top + m.rs) m.rs++; }
    else { doc.merges[mk] = { rs: at - g.top + 1, cs: 1 }; }
    delete doc.cells[at + ':' + sizeCol()];
    afterChange();
    setActive(at, 2);
    toast('เพิ่มรุ่นใหม่ในกลุ่มขนาดเดิม — พิมพ์ยี่ห้อ/รุ่น/ราคาได้เลย');
  }
  function addSizeGroup() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var g = sizeGroupOf(sel.r);
    var at = g.top + g.n;            // ต่อท้ายกลุ่มปัจจุบัน
    var tpl = at - 1;                // แถวสุดท้ายของกลุ่มเดิมเป็นต้นแบบ
    insertRow(at, true);
    copyRowPattern(tpl, at);
    var _sc = sizeCol();
    doc.cells[at + ':' + _sc] = { v: 'ขนาดใหม่', t: 'text', s: { bg: 'F2F2F2', fc: '0000FF', b: 1, al: 'center' } };
    afterChange();
    setActive(at, _sc);
    toast('เพิ่มขนาดใหม่แล้ว — กด Enter พิมพ์ขนาดยาง');
  }
  function toggleSizeCol(col) {
    if (view.mode !== 'admin') return;
    pushUndo();
    doc.sizeCol = (sizeCol() === col) ? 0 : col;
    invalidate(); afterChange();
    toast(doc.sizeCol === col ? ('📏 ตั้งคอลัมน์ ' + XL2.colName(col) + ' เป็นคอลัมน์ขนาดหลัก') : ('ยกเลิก — คอลัมน์ขนาดหลักกลับเป็น ' + XL2.colName(0)));
  }
  function delSizeGroup() {
    if (view.mode !== 'admin') return;
    var g = sizeGroupOf(sel.r);
    var szCell = cellAt(g.top, sizeCol());
    if (!confirm('ลบขนาด “' + (szCell ? String(szCell.v || valueOf(g.top, 0)).split('\n')[0] : '') + '” ทั้งกลุ่ม (' + g.n + ' แถว)?')) return;
    sel.ar = g.top; sel.r = g.top + g.n - 1; sel.ac = 0; sel.c = doc.nCols - 1;
    deleteRow();
  }

  // ---------- แทรกคอลัมน์คำนวณ: Margin / แปลโค้ด (อ้างอิงคอลัมน์ที่พิมพ์ระบุ) ----------
  function insertCalcCol(kind) {
    if (view.mode !== 'admin') return;
    var at = range().c2 + 1;
    var cA, cB, refIdx, fnName;
    if (kind === 'margin') {
      var p = prompt('เพิ่มคอลัมน์ Margin = ราคา − ทุน\nพิมพ์อ้างอิงจากตาราง เช่น H-G (ราคาตั้ง−ทุน) หรือ N-G (SUB-B−ทุน)', 'H-G');
      if (p === null) return;
      var m = /^\s*([A-Za-z]{1,2})\s*-\s*([A-Za-z]{1,2})\s*$/.exec(p);
      if (!m) { toast('รูปแบบไม่ถูก — พิมพ์เช่น H-G'); return; }
      cA = XL2.colIndex(m[1].toUpperCase()); cB = XL2.colIndex(m[2].toUpperCase());
    } else {
      var refL = prompt('แปลโค้ดจากคอลัมน์ไหน? พิมพ์ชื่อคอลัมน์ เช่น G (ทุน) หรือ N (ราคาส่ง)', 'G');
      if (refL === null) return;
      if (!/^[A-Za-z]{1,2}$/.test(refL.trim())) { toast('พิมพ์ชื่อคอลัมน์ เช่น G'); return; }
      refIdx = XL2.colIndex(refL.trim().toUpperCase());
      var setSel = prompt('ใช้ชุดรหัสไหน?\n1 = ชุดทุน (COGS: X T N S F V L C B K)\n2 = ชุดขายส่ง (DEALER: O I Z M D E H Y P R)', '1');
      if (setSel === null) return;
      fnName = (setSel.trim() === '2') ? 'DEALER' : 'COGS';
    }
    pushUndo();
    insertCols(at, 1, true);
    invalidate();
    // ปรับอ้างอิงถ้าคอลัมน์ที่อ้างอยู่หลังจุดแทรก (ตัวอักษรเลื่อน)
    if (cA != null && cA >= at) cA++;
    if (cB != null && cB >= at) cB++;
    if (refIdx != null && refIdx >= at) refIdx++;
    for (var r = 0; r < doc.nRows; r++) {
      var rk = rowKind(r);
      if (rk === 'head') {
        doc.cells[r + ':' + at] = { v: (kind === 'margin' ? 'Margin' : 'รหัส\nแปลโค้ด'), t: 'text', s: { bg: kind === 'margin' ? 'FFF2CC' : 'FCE4D6', b: 1, al: 'center', fs: 9 } };
      } else if (rk === 'data') {
        var n = r + 1;
        if (kind === 'margin') doc.cells[r + ':' + at] = { f: '=' + XL2.colName(cA) + n + '-' + XL2.colName(cB) + n, t: 'num', s: { pm: 1, cond: 'pn', fs: 9, al: 'center' } };
        else doc.cells[r + ':' + at] = { f: '=' + fnName + '(' + XL2.colName(refIdx) + n + ')', t: 'text', s: { bg: 'FFF7EF', fc: 'B15C00', b: 1, mn: 1, al: 'center' } };
      }
    }
    doc.colW[at] = 66;
    afterChange();
    setActive(sel.r, at);
    toast(kind === 'margin' ? '➕ เพิ่มคอลัมน์ Margin (' + XL2.colName(cA) + '−' + XL2.colName(cB) + ') ที่ ' + XL2.colName(at) : '➕ เพิ่มคอลัมน์แปลโค้ด ' + fnName + '(' + XL2.colName(refIdx) + ') ที่ ' + XL2.colName(at));
  }

  // ---------- merge ----------
  function toggleMerge() {
    if (view.mode !== 'admin') return;
    var R = range();
    var k = key(R.r1, R.c1);
    pushUndo();
    if (doc.merges[k] && R.r1 === R.r2 && R.c1 === R.c2) { delete doc.merges[k]; afterChange(); toast('ยกเลิกผสานเซลล์'); return; }
    // ถ้ามี merge ใดๆ ในช่วง → ยกเลิกทั้งหมด
    var had = false;
    Object.keys(doc.merges).forEach(function (mk) {
      var p = mk.split(':'), r = +p[0], c = +p[1];
      if (r >= R.r1 && r <= R.r2 && c >= R.c1 && c <= R.c2) { delete doc.merges[mk]; had = true; }
    });
    if (!had && (R.r1 !== R.r2 || R.c1 !== R.c2)) {
      doc.merges[k] = { rs: R.r2 - R.r1 + 1, cs: R.c2 - R.c1 + 1 };
      toast('ผสานเซลล์ ' + XL2.refStr(R.r1, R.c1) + ':' + XL2.refStr(R.r2, R.c2));
    } else toast('ยกเลิกผสานเซลล์');
    afterChange();
  }

  // ---------- borders (ตีเส้นแบบ Excel · เลือกสี/ลายเส้นได้) ----------
  var bdOpts = { style: 'solid', color: '000000', w: 1 };
  function setBorderOpts(o) { if (o.style) bdOpts.style = o.style; if (o.color) bdOpts.color = o.color; if (o.w != null) bdOpts.w = o.w; }
  function bdCss(v) {
    if (v == null) return null;
    if (typeof v === 'number' || /^\d+$/.test(String(v))) return (String(v) === '2' ? '2px' : '1px') + ' solid #000';
    var p = String(v).split('|');
    return (p[0] === '2' ? '2px' : '1px') + ' ' + (p[1] || 'solid') + ' #' + (p[2] || '000000');
  }
  // ค่าเส้น: 1=บาง, 2=หนา · เก็บใน cell.s.bd = {t,r,b,l}
  function applyBorders(mode) {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range();
    function setB(r, c, side, val) {
      function put(rr, cc, sd, v) {
        if (rr < 0 || cc < 0) return;
        var cell = ensureCell(rr, cc); cell.s = cell.s || {};
        var bd = cell.s.bd = cell.s.bd || {};
        if (v) bd[sd] = v; else delete bd[sd];
        if (!Object.keys(bd).length) delete cell.s.bd;
      }
      put(r, c, side, val);
      // ซิงค์ "ขอบที่แชร์" กับช่องข้างเคียงให้ตรงกัน — โมเดลแบบ Excel: 1 ขอบ = 1 เส้น
      // (กันเส้นหนาเดิมของช่องข้างนอกพื้นที่เลือกมาเหลื่อมกับเส้นที่เพิ่งตี → ในกับนอกหนาเท่ากัน)
      if (side === 't') put(r - 1, c, 'b', val);
      else if (side === 'b') put(r + 1, c, 't', val);
      else if (side === 'l') put(r, c - 1, 'r', val);
      else if (side === 'r') put(r, c + 1, 'l', val);
    }
    var baseW = bdOpts.w || 1;
    var thick = /thick/.test(mode) ? (baseW + 1) : baseW;
    var val1 = baseW + '|' + bdOpts.style + '|' + bdOpts.color;
    var valT = thick + '|' + bdOpts.style + '|' + bdOpts.color;
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) {
      if (mode === 'none' || mode === 'erase-all') {
        // ล้างทุกเส้นรอบช่อง + ขอบที่แชร์กับเพื่อนบ้านด้วย (กันขอบนอกค้าง) ผ่าน setB(null)
        setB(r, c, 't', null); setB(r, c, 'b', null); setB(r, c, 'l', null); setB(r, c, 'r', null);
        continue;
      }
      if (mode.indexOf('erase') === 0) {
        if (/bottom/.test(mode) && r === R.r2) setB(r, c, 'b', null);
        if (/top/.test(mode) && r === R.r1) setB(r, c, 't', null);
        if (/left/.test(mode) && c === R.c1) setB(r, c, 'l', null);
        if (/right/.test(mode) && c === R.c2) setB(r, c, 'r', null);
        continue;
      }
      if (mode === 'all') { setB(r, c, 't', val1); setB(r, c, 'b', val1); setB(r, c, 'l', val1); setB(r, c, 'r', val1); continue; }
      if (mode === 'topbottom') { if (r === R.r1) setB(r, c, 't', valT); if (r === R.r2) setB(r, c, 'b', valT); continue; }
      if (/^outer/.test(mode)) {
        if (r === R.r1) setB(r, c, 't', valT);
        if (r === R.r2) setB(r, c, 'b', valT);
        if (c === R.c1) setB(r, c, 'l', valT);
        if (c === R.c2) setB(r, c, 'r', valT);
        continue;
      }
      if (/^bottom/.test(mode) && r === R.r2) setB(r, c, 'b', valT);
      if (/^top/.test(mode) && r === R.r1) setB(r, c, 't', valT);
      if (/^left/.test(mode) && c === R.c1) setB(r, c, 'l', valT);
      if (/^right/.test(mode) && c === R.c2) setB(r, c, 'r', valT);
    }
    afterChange();
    var names = { none: 'ลบเส้นออก', all: 'เส้นขอบทั้งหมด', outer: 'เส้นขอบนอก', 'outer-thick': 'เส้นขอบนอกหนา', bottom: 'เส้นล่าง', 'bottom-thick': 'เส้นล่างหนา', top: 'เส้นบน', left: 'เส้นซ้าย', right: 'เส้นขวา' };
    toast('ตีเส้น: ' + (names[mode] || mode));
  }

  // ---------- styles & types ----------
  function applyStyle(prop, val) {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range();
    var target = val;
    if (val === 'toggle' && (prop === 'b' || prop === 'i' || prop === 'u')) {
      // แบบ Excel: ถ้ายังไม่หนาทั้งหมด → ทำให้หนาทุกตัว · ถ้าหนาหมดแล้ว → ค่อยเปลี่ยนเป็นบาง
      var allOn = true;
      for (var rr = R.r1; rr <= R.r2 && allOn; rr++) for (var cc = R.c1; cc <= R.c2; cc++) {
        var cz = cellAt(rr, cc); if (!(cz && cz.s && cz.s[prop])) { allOn = false; break; }
      }
      target = allOn ? null : 1;
    }
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) {
      var cell = ensureCell(r, c); cell.s = cell.s || {};
      if (target === null) delete cell.s[prop];
      else cell.s[prop] = target;
    }
    afterChange();
  }
  function setType(t) {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range();
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) ensureCell(r, c).t = t;
    afterChange();
    toast('กำหนดรูปแบบ: ' + (t === 'num' ? 'ตัวเลข' : t === 'text' ? 'ข้อความ' : 'อัตโนมัติ'));
  }
  // ---------- 3A: ผูกคอลัมน์กับฟิลด์ DB (column binding) ----------
  // เทมเพลตเริ่มต้น (แก้ได้) — index คอลัมน์ → ฟิลด์ DBX
  var COLMAP_TEMPLATE = { 6: 'costStandard', 7: 'salePrice1', 8: 'salePrice2', 9: 'salePrice3' };
  function applyColMapTemplate() {
    if (view.mode !== 'admin' || !window.DBX) return;
    pushUndo();
    doc.columnMap = doc.columnMap || {};
    Object.keys(COLMAP_TEMPLATE).forEach(function (c) {
      var field = COLMAP_TEMPLATE[c];
      doc.columnMap[c] = { field: field, mode: window.DBX.isWritable(field) ? 'write' : 'read' };
    });
    invalidate(); afterChange(); toast('ใช้เทมเพลตผูกคอลัมน์แล้ว (แก้ไขได้)');
  }
  var colBindEl = null;
  function openColBind(col) {
    if (view.mode !== 'admin' || !window.DBX) return;
    if (!colBindEl) { colBindEl = document.createElement('div'); colBindEl.className = 'sg-pick sg-colbind'; document.body.appendChild(colBindEl); }
    var cur = (doc.columnMap && doc.columnMap[col]) || null;
    var isStatus = doc.statusCol === col;
    var groups = window.DBX.allGroups();
    var curGroup = null;
    if (cur) { var cf = window.DBX.allFields().find(function (x) { return x.key === cur.field; }); curGroup = cf ? cf.group : null; }
    // รายการหมวด (กระชับ) — แต่ละหมวดมี flyout รายละเอียดออกข้าง
    var cats = '<div class="cb-cat cb-special' + (isStatus ? ' on' : '') + '" data-special="status"><span class="cb-ic">📊</span><span class="cb-cat-name">คอลัมน์สถานะ (จุดสี/ไอคอน)</span></div>';
    cats += '<div class="cb-cat cb-special' + (sizeCol() === col ? ' on' : '') + '" data-special="size"><span class="cb-ic">📏</span><span class="cb-cat-name">คอลัมน์ขนาดหลัก (ใช้ตอนเพิ่มขนาด/รุ่น)</span></div>';
    cats += groups.map(function (g) {
      var fields = window.DBX.fieldsInGroup(g, true);
      if (!fields.length) return '';   // ซ่อนหมวดที่ไม่มีฟิลด์เปิดใช้งาน
      var hasCur = curGroup === g;
      return '<div class="cb-cat' + (hasCur ? ' on' : '') + '" data-group="' + esc(g) + '">' +
        '<span class="cb-cat-name">' + esc(g) + '</span>' +
        '<span class="cb-cat-meta">' + fields.length + ' ฟิลด์ ▸</span></div>';
    }).join('');
    colBindEl.innerHTML = '<div class="pk-head">🔗 ผูกคอลัมน์ ' + XL2.colName(col) + ' กับฟิลด์ DB<span class="pk-x">✕</span></div>' +
      '<div class="cb-cur">' + (cur ? 'ผูกอยู่: <b>' + esc(window.DBX.fieldLabel(cur.field)) + '</b> · ' + (cur.mode === 'write' ? 'เขียนได้ (ราคา)' : 'อ่านอย่างเดียว') : (isStatus ? 'เป็น <b>คอลัมน์สถานะ</b>' : 'ยังไม่ผูก')) + '</div>' +
      '<div class="cb-cats">' + cats + '</div>' +
      '<div class="cb-foot"><button class="btn" data-tpl>📋 ใช้เทมเพลต</button><button class="btn" data-manage>⚙️ จัดการฟิลด์/หมวด</button>' + (cur || isStatus ? '<button class="btn" data-unbind>ยกเลิก</button>' : '') + '</div>';
    var r = rootEl.querySelector('.sg-h[data-hc="' + col + '"]');
    var rc = r ? r.getBoundingClientRect() : { left: 200, bottom: 120 };
    colBindEl.style.display = 'block';
    colBindEl.style.left = Math.min(rc.left, window.innerWidth - colBindEl.offsetWidth - 10) + 'px';
    colBindEl.style.top = Math.min(rc.bottom + 4, window.innerHeight - colBindEl.offsetHeight - 10) + 'px';
    makeDraggable(colBindEl, '.pk-head'); clampPopup(colBindEl);
    var closeCB = function () { colBindEl.style.display = 'none'; closeCbFlyout(); if (window.PopupStack) PopupStack.remove(colBindEl); };
    if (window.PopupStack) PopupStack.push(colBindEl, closeCB);
    colBindEl.querySelector('.pk-x').onclick = closeCB;
    colBindEl.querySelector('[data-tpl]').onclick = function () { applyColMapTemplate(); closeCB(); };
    colBindEl.querySelector('[data-manage]').onclick = function () { closeCB(); if (window.openDbFieldManager) window.openDbFieldManager(); };
    var ub = colBindEl.querySelector('[data-unbind]'); if (ub) ub.onclick = function () { if (isStatus) toggleStatusCol(col); else bindColumn(col, null); closeCB(); };
    // คลิก/hover หมวด → flyout รายละเอียดฟิลด์ออกข้าง
    var cs = colBindEl.querySelector('.cb-cats');
    cs.onclick = function (e) {
      var sp = e.target.closest('[data-special]');
      if (sp) { if (sp.dataset.special === 'size') toggleSizeCol(col); else toggleStatusCol(col); closeCB(); return; }
      var cat = e.target.closest('.cb-cat[data-group]'); if (!cat) return;
      openCbFlyout(col, cat.dataset.group, cat, cur, closeCB);
    };
    cs.onmouseover = function (e) {
      var cat = e.target.closest('.cb-cat[data-group]'); if (!cat) return;
      openCbFlyout(col, cat.dataset.group, cat, cur, closeCB);
    };
  }
  var cbFlyoutEl = null;
  function closeCbFlyout() { if (cbFlyoutEl) cbFlyoutEl.style.display = 'none'; }
  function openCbFlyout(col, group, catEl, cur, closeCB) {
    if (!cbFlyoutEl) { cbFlyoutEl = document.createElement('div'); cbFlyoutEl.className = 'sg-pick cb-flyout'; document.body.appendChild(cbFlyoutEl); }
    var fields = window.DBX.fieldsInGroup(group, true);
    var body = fields.map(function (f) {
      var on = cur && cur.field === f.key;
      return '<div class="cb-f' + (on ? ' on' : '') + (f.writable ? ' wr' : '') + '" data-field="' + esc(f.key) + '">' +
        '<span class="cb-ic">' + (f.writable ? '✏️' : '🔒') + '</span>' + esc(f.label) + '</div>';
    }).join('') || '<div class="cb-empty">หมวดนี้ยังไม่มีฟิลด์</div>';
    cbFlyoutEl.innerHTML = '<div class="cb-fly-head">' + esc(group) + '</div><div class="cb-fly-body">' + body + '</div>';
    // ไฮไลต์หมวดที่เลือก
    colBindEl.querySelectorAll('.cb-cat.hi').forEach(function (x) { x.classList.remove('hi'); });
    catEl.classList.add('hi');
    cbFlyoutEl.style.display = 'block';
    var cr = catEl.getBoundingClientRect(), pw = cbFlyoutEl.offsetWidth, ph = cbFlyoutEl.offsetHeight;
    var left = cr.right + 4; if (left + pw > window.innerWidth - 6) left = cr.left - pw - 4;
    cbFlyoutEl.style.left = Math.max(6, left) + 'px';
    cbFlyoutEl.style.top = Math.min(cr.top, window.innerHeight - ph - 6) + 'px';
    cbFlyoutEl.querySelector('.cb-fly-body').onclick = function (e) {
      var f = e.target.closest('.cb-f'); if (!f || !f.dataset.field) return;
      bindColumn(col, f.dataset.field); closeCB();
    };
  }
  function toggleStatusCol(col) {
    if (view.mode !== 'admin') return;
    pushUndo();
    if (doc.statusCol === col) { delete doc.statusCol; toast('ยกเลิกคอลัมน์สถานะ'); }
    else {
      doc.statusCol = col;
      if (doc.columnMap && doc.columnMap[col]) delete doc.columnMap[col];   // คอลัมน์สถานะไม่ผูกฟิลด์ DB
      toast('ตั้งคอลัมน์ ' + XL2.colName(col) + ' เป็นคอลัมน์สถานะ');
    }
    invalidate(); afterChange();
  }
  function bindColumn(col, field) {
    if (view.mode !== 'admin') return;
    pushUndo();
    doc.columnMap = doc.columnMap || {};
    if (!field) delete doc.columnMap[col];
    else { doc.columnMap[col] = { field: field, mode: (window.DBX && window.DBX.isWritable(field)) ? 'write' : 'read' }; if (doc.statusCol === col) delete doc.statusCol; }   // คอลัมน์เดียว เลือกได้อย่างเดียว: ฟิลด์ หรือ สถานะ
    invalidate(); afterChange();
    toast(field ? ('ผูกคอลัมน์ ' + XL2.colName(col) + ' → ' + (window.DBX ? window.DBX.fieldLabel(field) : field)) : ('ยกเลิกผูกคอลัมน์ ' + XL2.colName(col)));
  }

  function linkDB() {
    if (view.mode !== 'admin') return;
    var codes = XL2.dbKeys();
    var code = prompt('รหัสสินค้า (ขนาด|ยี่ห้อ|รุ่น) เช่น:\n' + codes.slice(0, 4).join('\n'), codes[0] || '');
    if (!code) return;
    var field = prompt('ฟิลด์ที่ต้องการ: ทุน / ราคา / B / A / S / DOT', 'ราคา');
    if (!field) return;
    pushUndo();
    var a = anchorOf(sel.r, sel.c);
    var nc = ensureCell(a.r, a.c);
    nc.f = '=DB("' + code + '","' + field + '")'; delete nc.v;
    afterChange();
    toast('ลิงก์ฐานข้อมูล: ' + code + ' → ' + field);
  }

  // ---------- row ↔ product link (ทั้งแถว = สินค้ารหัสเดียว) · ผ่านชั้นกลาง DBX (code13) ----------
  var pickEl = null, pickSel = null;
  // ---------- popup: ลากย้ายด้วยหัว + กันหลุดเฟรม ----------
  function clampPopup(el) {
    if (!el) return;
    el.style.transform = 'none';
    var r = el.getBoundingClientRect();
    var maxL = Math.max(4, window.innerWidth - r.width - 4);
    var maxT = Math.max(4, window.innerHeight - r.height - 4);
    var L = Math.min(Math.max(4, r.left), maxL);
    var T = Math.min(Math.max(4, r.top), maxT);
    el.style.left = L + 'px'; el.style.top = T + 'px';
  }
  function makeDraggable(el, handleSel) {
    if (!el || el._dragWired) return; el._dragWired = true;
    el.addEventListener('mousedown', function (e) {
      var h = e.target.closest(handleSel); if (!h || el.contains(e.target.closest('.pk-x'))) return;
      if (e.target.closest('.pk-x')) return;
      e.preventDefault();
      el.style.transform = 'none';
      var r = el.getBoundingClientRect(), ox = e.clientX - r.left, oy = e.clientY - r.top;
      el.style.left = r.left + 'px'; el.style.top = r.top + 'px';
      function mv(ev) {
        var L = Math.min(Math.max(4, ev.clientX - ox), window.innerWidth - el.offsetWidth - 4);
        var T = Math.min(Math.max(4, ev.clientY - oy), window.innerHeight - el.offsetHeight - 4);
        el.style.left = L + 'px'; el.style.top = T + 'px';
      }
      function up() { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); }
      document.addEventListener('mousemove', mv); document.addEventListener('mouseup', up);
    });
  }
  // คีย์บอร์ดนำทางในป๊อปอัปเลือกฟิลด์ (.cb-f) — ↑↓ เลื่อน · Enter เลือก · Esc ปิด
  function wireFieldNav(popup, scrollSel) {
    var sc = popup.querySelector(scrollSel); if (!sc) return;
    if (popup._navKey) document.removeEventListener('keydown', popup._navKey);
    function items() { return [].slice.call(sc.querySelectorAll('.cb-f')); }
    function cur() { return sc.querySelector('.cb-f.kbsel'); }
    function setSel(el) { items().forEach(function (x) { x.classList.toggle('kbsel', x === el); }); if (el) el.scrollIntoView({ block: 'nearest' }); }
    popup._navKey = function (e) {
      if (popup.style.display === 'none' || !popup.offsetParent) return;
      var all = items(); if (!all.length) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault(); var i = all.indexOf(cur());
        i = e.key === 'ArrowDown' ? Math.min(all.length - 1, i + 1) : Math.max(0, i < 0 ? 0 : i - 1);
        setSel(all[i]);
      } else if (e.key === 'Enter') {
        e.preventDefault(); var c = cur() || all[0]; if (c) c.click();
      } else if (e.key === 'Escape') { e.preventDefault(); popup.style.display = 'none'; }
    };
    document.addEventListener('keydown', popup._navKey);
    setSel(sc.querySelector('.cb-f.on') || items()[0]);
  }

  function openPicker(opt) {
    opt = opt || {};
    if (!pickEl) { pickEl = document.createElement('div'); pickEl.className = 'sg-pick'; document.body.appendChild(pickEl); }
    pickSel = null;
    pickEl.innerHTML = '<div class="pk-head">' + esc(opt.title || '🔗 เลือกสินค้าจากฐานข้อมูล') + '<span class="pk-x">✕</span></div>' +
      '<input class="pk-q" placeholder="ค้นหารหัส 13 หลัก / ชื่อ / ยี่ห้อ / ขนาด / รุ่น…" />' +
      '<div class="pk-list"><div class="pk-empty">กำลังโหลด…</div></div>' +
      '<div class="pk-note">' + esc(opt.note || 'ดับเบิลคลิกรายการเพื่อผูก · รหัสที่ผูกทั้งแถวแล้วจะมีเครื่องหมาย ✓ และผูกซ้ำไม่ได้') + '</div>';
    var q = pickEl.querySelector('.pk-q'), list = pickEl.querySelector('.pk-list');
    var items = [], used = usedRowCodes();
    function paint(filter) {
      var f = (filter || '').toLowerCase();
      var rows = items.filter(function (x) { return (x.code13 + ' ' + x.name + ' ' + x.brandCode + ' ' + x.size + ' ' + x.model).toLowerCase().indexOf(f) >= 0; }).slice(0, 80);
      list.innerHTML = rows.map(function (x) {
        var taken = used[x.code13] != null;
        var blocked = taken && !opt.allowUsed;
        var inactive = x.status && x.status !== 'active';
        return '<div class="pk-it' + (blocked ? ' pk-taken' : '') + (taken ? ' pk-linked' : '') + (pickSel === x.code13 ? ' pk-on' : '') + '" data-code="' + esc(x.code13) + '" title="' + (taken ? 'ผูกกับแถว ' + (used[x.code13] + 1) + ' แล้ว · คลิกขวาเพื่อถอดการเชื่อมต่อ' : 'ดับเบิลคลิก/Enter เพื่อผูก') + '">' +
          '<span class="pk-code">' + esc(x.code13) + '</span><span class="pk-name">' + esc(x.name) + '</span>' +
          (inactive ? '<span class="pk-badge pk-inact">inactive</span>' : '') + (taken ? '<span class="pk-badge pk-used">✓ แถว ' + (used[x.code13] + 1) + '</span>' : '') + '</div>';
      }).join('') || '<div class="pk-empty">ไม่พบ</div>';
    }
    function markSel() {   // อัปเดตไฮไลต์โดยไม่สร้าง DOM ใหม่ (กัน dblclick/Enter หลุด)
      list.querySelectorAll('.pk-it').forEach(function (el) { el.classList.toggle('pk-on', el.dataset.code === pickSel); });
    }
    function selectedEl() { return list.querySelector('.pk-it.pk-on'); }
    window.DBX.search({}).then(function (arr) { items = arr || []; paint(q.value); }).catch(function () { list.innerHTML = '<div class="pk-empty">โหลดฐานข้อมูลไม่ได้</div>'; });
    q.oninput = function () { paint(q.value); };
    function confirmPick(code) {
      if (used[code] != null && !opt.allowUsed) { askDisconnect(code); return; }
      closePicker(); opt.onPick(code);
    }
    // คลิกขวารายการที่ผูกแล้ว → ถามถอดการเชื่อมต่อ (Enter ยืนยัน)
    function askDisconnect(code) {
      var rr = used[code]; if (rr == null) return;
      var bar = pickEl.querySelector('.pk-confirm');
      if (!bar) { bar = document.createElement('div'); bar.className = 'pk-confirm'; pickEl.appendChild(bar); }
      bar.innerHTML = '<div class="pkc-msg">⛓️‍💥 ถอดการเชื่อมต่อรหัส <b>' + esc(code) + '</b> ออกจากแถว ' + (rr + 1) + '?</div>' +
        '<div class="pkc-btns"><button class="btn" data-pkc="no">ยกเลิก (Esc)</button><button class="btn primary" data-pkc="yes">ยืนยัน (Enter)</button></div>';
      bar.style.display = 'block';
      pickEl._pkcArmed = function () { bar.style.display = 'none'; pushUndo(); delete doc.rowLinks[rr]; used = usedRowCodes(); invalidate(); afterChange(); paint(q.value); toast('ถอดการเชื่อมต่อแถว ' + (rr + 1) + ' แล้ว'); };
      bar.querySelector('[data-pkc="yes"]').onclick = function () { pickEl._pkcArmed(); pickEl._pkcArmed = null; };
      bar.querySelector('[data-pkc="no"]').onclick = function () { bar.style.display = 'none'; pickEl._pkcArmed = null; };
    }
    list.onclick = function (e) { var it = e.target.closest('.pk-it'); if (!it) return; pickSel = it.dataset.code; markSel(); };
    list.ondblclick = function (e) { var it = e.target.closest('.pk-it'); if (!it) return; pickSel = it.dataset.code; confirmPick(it.dataset.code); };
    list.oncontextmenu = function (e) {
      var it = e.target.closest('.pk-it'); if (!it) return;
      e.preventDefault(); e.stopPropagation();
      if (used[it.dataset.code] != null) { pickSel = it.dataset.code; markSel(); askDisconnect(it.dataset.code); }
    };
    function pickKey(e) {
      if (pickEl.style.display !== 'block') return;
      if (e.key === 'Enter') {
        e.preventDefault();
        if (pickEl._pkcArmed) { pickEl._pkcArmed(); pickEl._pkcArmed = null; return; }
        if (pickSel) confirmPick(pickSel);
      } else if (e.key === 'Escape') {
        var bar = pickEl.querySelector('.pk-confirm');
        if (bar && bar.style.display === 'block') { e.preventDefault(); bar.style.display = 'none'; pickEl._pkcArmed = null; }
        else closePicker();
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        var all = [].slice.call(list.querySelectorAll('.pk-it')); if (!all.length) return;
        var idx = all.indexOf(selectedEl());
        idx = e.key === 'ArrowDown' ? Math.min(all.length - 1, idx + 1) : Math.max(0, idx - 1);
        pickSel = all[idx].dataset.code; markSel(); all[idx].scrollIntoView({ block: 'nearest' });
      }
    }
    document.addEventListener('keydown', pickKey);
    pickEl._detachKey = function () { document.removeEventListener('keydown', pickKey); };
    pickEl.querySelector('.pk-x').onclick = closePicker;
    pickEl.style.display = 'block';
    makeDraggable(pickEl, '.pk-head');
    clampPopup(pickEl);
    setTimeout(function () { q.focus(); }, 30);
  }
  function closePicker() { if (pickEl) { pickEl.style.display = 'none'; if (pickEl._detachKey) pickEl._detachKey(); } }
  function usedRowCodes() { var u = {}; Object.keys(doc.rowLinks || {}).forEach(function (rr) { var v = doc.rowLinks[rr]; if (isCode13(v)) u[v] = +rr; }); return u; }

  function linkRowDB() {
    if (view.mode !== 'admin' || !window.DBX) return;
    var r = sel.r;
    openPicker({
      title: '🔗 ผูกแถว ' + (r + 1) + ' กับสินค้า',
      onPick: function (code) {
        // กฎ unique: รหัสที่ผูกทั้งแถวแล้ว ห้ามผูกซ้ำแถวอื่น
        var used = usedRowCodes();
        if (used[code] != null && used[code] !== r) { toast('⚠️ รหัสนี้ผูกกับแถว ' + (used[code] + 1) + ' แล้ว — ผูกซ้ำไม่ได้'); return; }
        pushUndo();
        doc.rowLinks = doc.rowLinks || {};
        doc.rowLinks[r] = code;
        invalidate(); afterChange();
        window.DBX.getClean(code).then(function (p) { toast('🔗 ลิงก์แถว ' + (r + 1) + ' กับ ' + code + (p ? ' · ' + p.name : '')); });
      }
    });
  }
  function unlinkRow() {
    if (view.mode !== 'admin') return;
    if (!doc.rowLinks || !doc.rowLinks[sel.r]) { toast('แถวนี้ยังไม่ได้ลิงก์'); return; }
    pushUndo();
    delete doc.rowLinks[sel.r];
    invalidate(); afterChange(); toast('ยกเลิกลิงก์แถวแล้ว');
  }

  // ---------- 3C: ผูกเฉพาะช่อง (cell-link · ข้ามสินค้าได้ · ข้อยกเว้นของ unique) ----------
  function linkCellDB() {
    if (view.mode !== 'admin' || !window.DBX) return;
    var a = anchorOf(sel.r, sel.c), r = a.r, c = a.c;
    openPicker({
      title: '🗄️ ลิงก์เฉพาะช่อง ' + XL2.colName(c) + (r + 1),
      allowUsed: true,
      note: 'ดับเบิลคลิกเลือกสินค้า แล้วเลือกฟิลด์ที่จะดึงมาแสดงในช่องนี้ (ข้ามสินค้าได้)',
      onPick: function (code) { pickCellField(r, c, code); }
    });
  }
  var cellFieldEl = null;
  function pickCellField(r, c, code) {
    if (!cellFieldEl) { cellFieldEl = document.createElement('div'); cellFieldEl.className = 'sg-pick sg-colbind'; document.body.appendChild(cellFieldEl); }
    var groups = {};
    window.DBX.FIELDS.forEach(function (f) { (groups[f.group] = groups[f.group] || []).push(f); });
    var body = '';
    Object.keys(groups).forEach(function (g) {
      body += '<div class="cb-grp">' + esc(g) + '</div><div class="cb-fields">';
      groups[g].forEach(function (f) { body += '<div class="cb-f' + (f.writable ? ' wr' : '') + '" data-field="' + f.key + '"><span class="cb-ic">' + (f.writable ? '✏️' : '🔒') + '</span>' + esc(f.label) + '</div>'; });
      body += '</div>';
    });
    cellFieldEl.innerHTML = '<div class="pk-head">🗄️ ช่อง ' + XL2.colName(c) + (r + 1) + ' ← ฟิลด์ของ ' + esc(code) + '<span class="pk-x">✕</span></div>' +
      '<div class="cb-scroll">' + body + '</div>' +
      '<div class="pk-note">เลือกฟิลด์ที่จะดึงมาแสดงในช่องนี้ · ราคา (✏️) แก้/ส่งกลับได้ · อื่น ๆ (🔒) อ่านอย่างเดียว</div>';
    cellFieldEl.style.display = 'block';
    cellFieldEl.style.left = Math.min((window.innerWidth - cellFieldEl.offsetWidth) / 2, window.innerWidth - cellFieldEl.offsetWidth - 10) + 'px';
    cellFieldEl.style.top = '14%';
    makeDraggable(cellFieldEl, '.pk-head'); clampPopup(cellFieldEl); wireFieldNav(cellFieldEl, '.cb-scroll');
    cellFieldEl.querySelector('.pk-x').onclick = function () { cellFieldEl.style.display = 'none'; };
    cellFieldEl.querySelector('.cb-scroll').onclick = function (e) {
      var f = e.target.closest('.cb-f'); if (!f) return;
      cellFieldEl.style.display = 'none';
      pushUndo();
      doc.cellLinks = doc.cellLinks || {};
      doc.cellLinks[r] = doc.cellLinks[r] || {};
      doc.cellLinks[r][c] = { code: code, field: f.dataset.field };
      invalidate(); afterChange();
      toast('🗄️ ช่อง ' + XL2.colName(c) + (r + 1) + ' ← ' + code + ' · ' + window.DBX.fieldLabel(f.dataset.field));
    };
  }
  function unlinkCell() {
    if (view.mode !== 'admin') return;
    var a = anchorOf(sel.r, sel.c), r = a.r, c = a.c;
    if (!(doc.cellLinks && doc.cellLinks[r] && doc.cellLinks[r][c])) { toast('ช่องนี้ไม่ได้ลิงก์เฉพาะช่อง'); return; }
    pushUndo();
    delete doc.cellLinks[r][c];
    if (!Object.keys(doc.cellLinks[r]).length) delete doc.cellLinks[r];
    invalidate(); afterChange(); toast('ยกเลิกลิงก์เฉพาะช่องแล้ว');
  }

  // ---------- ส่งราคาเข้า DB (ราคาตั้ง/B/A/S → ช่อง 1/2/3/4 · ใช้เวลาจากตารางเวลา) ----------
  var PRICE_COLS = [{ c: 7, slot: 1, n: 'ราคาตั้ง' }, { c: 13, slot: 2, n: 'B' }, { c: 16, slot: 3, n: 'A' }, { c: 19, slot: 4, n: 'S' }];
  function effectiveOf(r) { return (doc.rowSchedules && doc.rowSchedules[r]) || doc.schedule || 'ทันที'; }
  function setSchedule(at) { pushUndo(); doc.schedule = at || ''; persist(); toast(at ? '⏱ ราคาชุดนี้จะมีผล: ' + at : '⏱ ราคามีผลทันทีเมื่อส่ง'); }
  function setRowSchedule(at) {
    if (view.mode !== 'admin') return;
    pushUndo();
    doc.rowSchedules = doc.rowSchedules || {};
    if (at) doc.rowSchedules[sel.r] = at; else delete doc.rowSchedules[sel.r];
    persist(); render();
    toast(at ? '⏱ แถว ' + (sel.r + 1) + ' ใช้เวลาเฉพาะ: ' + at : 'แถว ' + (sel.r + 1) + ' กลับไปใช้เวลาของชีต');
  }
  function syncToDB() {
    if (view.mode !== 'admin') return;
    var links = doc.rowLinks || {}, rows = Object.keys(links);
    var hasChanges = Object.keys(doc.changes || {}).length > 0;
    if (!rows.length && !hasChanges) { toast('ยังไม่มีแถวที่ลิงก์ DB หรือการปรับราคา — คลิกขวาที่ช่องรุ่น → ลิงก์แถวกับสินค้า'); return; }
    var out = [];
    var auditEntries = [], user = (window.DBX && DBX.currentUser()) || 'admin', dev = window.DBX ? DBX.deviceInfo() : {};
    rows.forEach(function (r) {
      r = +r;
      var code = links[r];
      var prices = {};
      PRICE_COLS.forEach(function (pc) { var v = valueOf(r, pc.c); if (XL2.isNumeric(v)) prices['salePrice' + pc.slot] = XL2.toN(v); });
      // ส่งจริงผ่านชั้นกลาง DBX (เขียนกลับได้เฉพาะ 5 ราคา — กฎเหล็ก)
      if (window.DBX && isCode13(code) && Object.keys(prices).length) {
        DBX.pushPrices(code, prices);
        // audit + ประวัติราคา (เฉพาะช่องที่ปรับรอบนี้)
        var rc = doc.changes && doc.changes[r];
        PRICE_COLS.forEach(function (pc) {
          var field = 'salePrice' + pc.slot, nv = prices[field];
          if (nv == null) return;
          var ch = rc && rc[pc.c];
          var ov = ch ? XL2.toN(ch.old) : null;
          if (ch && ov !== nv) {
            var p = dbCache[code];
            auditEntries.push({ ts: Date.now(), code13: code, name: p ? p.name : '', field: field, oldV: ov, newV: nv, user: user, device: dev.ua ? (dev.platform + ' · ' + dev.screen) : '', result: 'ok' });
            DBX.pushPriceHistory(code, field, nv, Date.now());
          }
        });
      }
      out.push({ code: code, row: r + 1, prices: prices, effectiveAt: effectiveOf(r), queuedAt: new Date().toISOString() });
    });
    if (window.DBX && auditEntries.length) DBX.logAudit(auditEntries);
    try {
      var box = JSON.parse(localStorage.getItem('xls2_db_outbox') || '[]');
      box = box.concat(out);
      localStorage.setItem('xls2_db_outbox', JSON.stringify(box));
    } catch (e) {}
    // ประทับสถานะ “ส่งแล้ว” ให้ทุกรายการที่ปรับ — ผู้ใช้จะเห็น ⏳ (รอมีผล) หรือ ▲▼ (มีผลแล้ว)
    Object.keys(doc.changes || {}).forEach(function (r) {
      var rc = doc.changes[r];
      Object.keys(rc).forEach(function (c) { rc[c].sent = 1; if (!rc[c].effectiveAt) rc[c].effectiveAt = effectiveOf(+r); });
    });
    persist(); render();
    var perRow = Object.keys(doc.rowSchedules || {}).length;
    toast('📤 เผยแพร่การปรับราคา: ' + out.length + ' สินค้าลิงก์ DB · มีผล: ' + (doc.schedule || 'ทันที') + (perRow ? ' (+' + perRow + ' แถวตั้งเวลาเฉพาะ)' : ''));
  }

  // ---------- ซ่อน/เลิกซ่อนแถว-คอลัมน์ (แบบ Excel) ----------
  function hideRows() {
    if (view.mode !== 'admin') return;
    pushUndo(); var R = range();
    for (var r = R.r1; r <= R.r2; r++) doc.hideRows[r] = 1;
    afterChange(); toast('ซ่อนแถวแล้ว (คลิกขวา → เลิกซ่อน เพื่อแสดงอีก)');
  }
  function unhideRows() {
    if (view.mode !== 'admin') return;
    pushUndo(); var R = range();
    // เลิกซ่อนแถวที่อยู่ระหว่าง/ในช่วงที่เลือก
    for (var r = Math.max(0, R.r1 - 1); r <= R.r2 + 1 && r < doc.nRows; r++) delete doc.hideRows[r];
    afterChange(); toast('เลิกซ่อนแถวแล้ว');
  }
  function hideCols() {
    if (view.mode !== 'admin') return;
    pushUndo(); var R = range();
    for (var c = R.c1; c <= R.c2; c++) doc.hideCols[c] = 1;
    afterChange(); toast('ซ่อนคอลัมน์แล้ว');
  }
  function unhideCols() {
    if (view.mode !== 'admin') return;
    pushUndo(); var R = range();
    for (var c = Math.max(0, R.c1 - 1); c <= R.c2 + 1 && c < doc.nCols; c++) delete doc.hideCols[c];
    afterChange(); toast('เลิกซ่อนคอลัมน์แล้ว');
  }
  function showAllHidden() {
    if (view.mode !== 'admin') return;
    pushUndo(); doc.hideRows = {}; doc.hideCols = {};
    afterChange(); toast('แสดงแถว/คอลัมน์ที่ซ่อนไว้ทั้งหมด');
  }
  // ซ่อนเฉพาะโหมดผู้ใช้ (ไม่เกี่ยวกับ admin)
  function toggleUserHideRows() {
    if (view.mode !== 'admin') return;
    pushUndo(); var R = range(), all = true;
    for (var r = R.r1; r <= R.r2; r++) if (!doc.uHideRows[r]) { all = false; break; }
    for (var r2 = R.r1; r2 <= R.r2; r2++) { if (all) delete doc.uHideRows[r2]; else doc.uHideRows[r2] = 1; }
    afterChange(); toast(all ? 'เลิกซ่อนเฉพาะโหมดผู้ใช้' : '👁️ ซ่อนแถวนี้เฉพาะในโหมดผู้ใช้');
  }
  function toggleUserHideCols() {
    if (view.mode !== 'admin') return;
    pushUndo(); var R = range(), all = true;
    for (var c = R.c1; c <= R.c2; c++) if (!doc.uHideCols[c]) { all = false; break; }
    for (var c2 = R.c1; c2 <= R.c2; c2++) { if (all) delete doc.uHideCols[c2]; else doc.uHideCols[c2] = 1; }
    afterChange(); toast(all ? 'เลิกซ่อนคอลัมน์เฉพาะโหมดผู้ใช้' : '👁️ ซ่อนคอลัมน์นี้เฉพาะในโหมดผู้ใช้');
  }

  // ---------- lock (admin-only rows/cols) ----------
  function toggleLockRows() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range(), all = true;
    for (var r = R.r1; r <= R.r2; r++) if (!doc.adminRows[r]) { all = false; break; }
    for (var r2 = R.r1; r2 <= R.r2; r2++) { if (all) delete doc.adminRows[r2]; else doc.adminRows[r2] = 1; }
    afterChange(); toast(all ? 'ยกเลิกซ่อนแถวจากผู้ใช้' : '🔒 ซ่อนแถวจากผู้ใช้แล้ว');
  }
  function toggleLockCols() {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range(), all = true;
    for (var c = R.c1; c <= R.c2; c++) if (!doc.adminCols[c]) { all = false; break; }
    for (var c2 = R.c1; c2 <= R.c2; c2++) { if (all) delete doc.adminCols[c2]; else doc.adminCols[c2] = 1; }
    afterChange(); toast(all ? 'ยกเลิกซ่อนคอลัมน์จากผู้ใช้' : '🔒 ซ่อนคอลัมน์จากผู้ใช้แล้ว');
  }

  // ---------- resize with tooltip + multi ----------
  var rz = null;
  function startRzCol(ci, x) {
    var R = range();
    var cols;
    if (multiCols.length > 1 && multiCols.indexOf(ci) >= 0) cols = multiCols.slice();   // ลากขยายหลายคอลัมน์ที่ Ctrl+เลือกไว้ (ไม่ต่อเนื่อง) พร้อมกัน
    else cols = (ci >= R.c1 && ci <= R.c2 && R.c1 !== R.c2) ? rangeArr(R.c1, R.c2) : [ci];
    rz = { kind: 'col', idx: ci, cols: cols, startX: x, w0: doc.colW[ci] || 64 };
    pushUndo();
  }
  function startRzRow(ri, y) {
    var R = range();
    var rows;
    if (multiRows.length > 1 && multiRows.indexOf(ri) >= 0) rows = multiRows.slice();   // ลากขยายหลายแถวที่ Ctrl+เลือกไว้ พร้อมกัน
    else rows = (ri >= R.r1 && ri <= R.r2 && R.r1 !== R.r2) ? rangeArr(R.r1, R.r2) : [ri];
    rz = { kind: 'row', idx: ri, rows: rows, startY: y, h0: doc.rowH[ri] || 19 };
    pushUndo();
  }
  function rangeArr(a, b) { var o = []; for (var i = a; i <= b; i++) o.push(i); return o; }
  function moveRz(x, y) {
    if (!rz) return;
    if (rz.kind === 'col') {
      var w = Math.max(18, Math.round(rz.w0 + (x - rz.startX) / view.zoom));
      rz.cols.forEach(function (c) { doc.colW[c] = w; });
      showTip(x, y, 'กว้าง: ' + w + ' px' + (rz.cols.length > 1 ? ' × ' + rz.cols.length + ' คอลัมน์' : ''));
    } else {
      var h = Math.max(12, Math.round(rz.h0 + (y - rz.startY) / view.zoom));
      rz.rows.forEach(function (r) { doc.rowH[r] = h; });
      showTip(x, y, 'สูง: ' + h + ' px' + (rz.rows.length > 1 ? ' × ' + rz.rows.length + ' แถว' : ''));
    }
    invalidate(); buildCover(); render();
  }
  function endRz() { if (rz) { hideTip(); persist(); rz = null; } }
  function autofitCol(ci) {
    var ctx = document.createElement('canvas').getContext('2d');
    var max = 24;
    for (var r = 0; r < doc.nRows; r++) {
      var cell = cellAt(r, ci); if (!cell) continue;
      var s = cell.s || {};
      ctx.font = (s.b ? '700 ' : '') + (s.fs || 10) + 'px Arial';
      String(displayOf(r, ci)).split('\n').forEach(function (ln) {
        var w = ctx.measureText(ln).width + 10;
        if (w > max) max = w;
      });
    }
    pushUndo();
    doc.colW[ci] = Math.min(400, Math.ceil(max));
    afterChange(); toast('พอดีข้อความ: ' + XL2.colName(ci) + ' = ' + doc.colW[ci] + ' px');
  }
  function showTip(x, y, text) {
    tipEl.className = 'sg-tip';
    tipEl.style.display = 'block';
    tipEl.style.left = (x - rootEl.getBoundingClientRect().left + rootEl.scrollLeft + 14) + 'px';
    tipEl.style.top = (y - rootEl.getBoundingClientRect().top + rootEl.scrollTop - 8) + 'px';
    tipEl.textContent = text;
  }
  // ป๊อปอัปชื่อสินค้า: วางเหนือ/ใต้แถว ไม่ทับแถวเดิม ไม่หลุดเฟรม
  function showLinkTip(g, text, bad, isHtml) {
    tipEl.className = 'sg-tip linktip' + (bad ? ' bad' : '') + (isHtml ? ' tip-multi' : '');
    if (isHtml) tipEl.innerHTML = text; else tipEl.textContent = text;
    tipEl.style.display = 'block';
    var gr = g.getBoundingClientRect(), rootR = rootEl.getBoundingClientRect();
    var th = tipEl.offsetHeight, tw = tipEl.offsetWidth;
    var topC = gr.top - th - 5;                          // เหนือแถว
    if (topC < rootR.top + 2) topC = gr.bottom + 5;      // ไม่พอด้านบน → ใต้แถว
    topC = Math.max(rootR.top + 2, Math.min(topC, rootR.bottom - th - 2));
    var leftC = Math.max(rootR.left + 2, Math.min(gr.left, rootR.right - tw - 2));
    tipEl.style.left = (leftC - rootR.left + rootEl.scrollLeft) + 'px';
    tipEl.style.top = (topC - rootR.top + rootEl.scrollTop) + 'px';
  }
  function hideTip() { tipEl.style.display = 'none'; }

  // ---------- context menu (จัดหมวด + ซับเมนูย่อย) ----------
  // ขนาด/ฟอนต์ ในเมนูจัดตัวอักษร — ผู้ใช้เพิ่ม/ลบเองได้ + จัดเรียงอัตโนมัติ
  function ctxSizes() { try { var a = JSON.parse(localStorage.getItem('xls2_ctx_sizes') || 'null'); if (Array.isArray(a) && a.length) return a.map(Number).filter(function (n) { return n > 0; }); } catch (e) {} return [9, 10, 12, 14, 18, 24]; }
  function saveCtxSizes(a) { var u = []; a.forEach(function (n) { n = Math.round(+n); if (n > 0 && u.indexOf(n) < 0) u.push(n); }); u.sort(function (x, y) { return x - y; }); localStorage.setItem('xls2_ctx_sizes', JSON.stringify(u)); }
  function ctxFonts() { try { var a = JSON.parse(localStorage.getItem('xls2_ctx_fonts') || 'null'); if (Array.isArray(a) && a.length) return a; } catch (e) {} return [['Arial Black', 'Black'], ['Tahoma', 'Tahoma'], ['Sarabun', 'สารบรรณ'], ['Prompt', 'พรอมพต์'], ['Kanit', 'คนิต']]; }
  function saveCtxFonts(a) { a = a.slice().sort(function (x, y) { return String(x[1]).localeCompare(String(y[1]), 'th'); }); localStorage.setItem('xls2_ctx_fonts', JSON.stringify(a)); }
  function openCtx(x, y, keepSub) {
    if (view.mode !== 'admin') return;
    var cell = cellAt(anchorOf(sel.r, sel.c).r, anchorOf(sel.r, sel.c).c);
    var t = cell ? cell.t : 'auto';
    var R = range(), nR = R.r2 - R.r1 + 1, nC = R.c2 - R.c1 + 1;
    var reg = [];
    function it(ic, tx, fn, hint) {
      reg.push(fn);
      return '<div class="ctx-it" data-i="' + (reg.length - 1) + '"><span class="ctx-ic">' + ic + '</span><span class="ctx-tx">' + esc(tx) + '</span>' + (hint ? '<span class="ctx-k">' + esc(hint) + '</span>' : '') + '</div>';
    }
    function sub(ic, tx, inner) {
      return '<div class="ctx-it has-sub"><span class="ctx-ic">' + ic + '</span><span class="ctx-tx">' + esc(tx) + '</span><span class="ctx-arr">▸</span><div class="ctx-flyout">' + inner + '</div></div>';
    }
    function sep() { return '<div class="ctx-sep"></div>'; }

    var html = '<div class="ctx-drag" title="ลากเพื่อย้ายเมนู">⠿ ลากเพื่อย้าย</div>';
    // ใช้บ่อยสุด — อยู่ชั้นบนสุด
    html += it('✂️', 'ตัด', function () { doCopy(true); }, 'Ctrl+X');
    html += it('📋', 'คัดลอก', function () { doCopy(false); }, 'Ctrl+C');
    html += it('📌', 'วาง', doPaste, 'Ctrl+V');
    if (clip && clip.fullRows) html += it('➕', 'แทรกแถวที่คัดลอก (' + clip.rows.length + ' แถว)', insertCopiedRows);
    if (clip && clip.fullCols) html += it('➕', 'แทรกคอลัมน์ที่คัดลอก (' + clip.rows[0].length + ')', insertCopiedCols);
    if (clip) html += it('❌', 'ยกเลิกการคัดลอก', clearClip, 'Esc');
    html += sep();
    // หมวดย่อย (ชี้แล้วกางออกข้าง)
    html += sub('➕', 'แทรก',
      it('⬆️', 'แถวด้านบน (' + nR + ' แถว)', function () { insertRows(R.r1, nR); }) +
      it('⬇️', 'แถวด้านล่าง (' + nR + ' แถว)', function () { insertRows(R.r2 + 1, nR); }) +
      sep() +
      it('⬅️', 'คอลัมน์ซ้าย (' + nC + ')', function () { insertCols(R.c1, nC); }) +
      it('➡️', 'คอลัมน์ขวา (' + nC + ')', function () { insertCols(R.c2 + 1, nC); }) +
      sep() +
      it('🖼️', 'แทรกรูปภาพ…', function () { if (window.ImgLayer) ImgLayer.pickFile(); }) +
      it('🔎', 'ค้นหารูปใน Google…', function () { if (window.ImgLayer) ImgLayer.googleSearch(); }) +
      sep() +
      it('±', 'คอลัมน์ Margin (อ้างอิงราคา−ทุน)…', function () { insertCalcCol('margin'); }) +
      it('🔐', 'คอลัมน์แปลโค้ดเป็นอักษร (ระบุคอลัมน์อ้างอิง)…', function () { insertCalcCol('cipher'); }));
    html += sub('🗑️', 'ลบ / ล้าง',
      it('🗑️', 'ลบแถวที่เลือก (' + nR + ')', deleteRow) +
      it('🗑️', 'ลบคอลัมน์ที่เลือก (' + nC + ')', deleteCol) +
      sep() +
      it('🧹', 'ล้างค่าในช่อง', delRange, 'Del'));
    html += sub('🔣', 'รูปแบบเซลล์',
      it('🔢', 'ตัวเลข' + (t === 'num' ? '  ✓' : ''), function () { setType('num'); }) +
      it('🔤', 'ข้อความ' + (t === 'text' ? '  ✓' : ''), function () { setType('text'); }) +
      it('✨', 'อัตโนมัติ' + (t === 'auto' || !t ? '  ✓' : ''), function () { setType('auto'); }) +
      sep() +
      it('ƒ', 'ใส่สูตร…', function () { startEdit('='); }));
    // จัดตัวอักษร: จัดตำแหน่ง · สี · ขนาด · ฟอนต์
    function chip(htmlIn, fn, title) { reg.push(fn); return '<span class="ctx-chip" data-i="' + (reg.length - 1) + '" title="' + esc(title || '') + '">' + htmlIn + '</span>'; }
    function dchip(htmlIn, fn, title, delAttr) { reg.push(fn); return '<span class="ctx-chip ctx-delable" data-i="' + (reg.length - 1) + '" ' + delAttr + ' title="' + esc(title || '') + '">' + htmlIn + '</span>'; }
    function addChip(kind) { return '<span class="ctx-chip ctx-addchip" data-add="' + kind + '" title="เพิ่มเอง">＋</span>'; }
    function chipRow(label, chips) { return '<div class="ctx-row"><span class="ctx-rowlab">' + esc(label) + '</span><span class="ctx-chips">' + chips + '</span></div>'; }
    // สีหลักของเมนูคลิกขวา = สีหลักเดียวกับปุ่มบนแถบเครื่องมือ (อัปเดตตามที่ผู้ใช้ปรับ)
    function cfMainRead(ns, def) { try { var a = JSON.parse(localStorage.getItem('xls2_cf_' + ns + '_main') || 'null'); if (Array.isArray(a) && a.length) return a.map(function (c) { return String(c).replace('#', '').toUpperCase(); }); } catch (e) {} return def; }
    var FCs = cfMainRead('font', ['000000', '808080', 'FF0000', 'C00000', 'FF6600', '008000', '0000FF', '7030A0']);
    var BGs = cfMainRead('fill', ['FFFF00', 'FF9900', '92D050', '00B0F0', '00FFFF', 'FF99CC', 'D8D8D8', 'FF6666']);
    html += sub('🅰️', 'จัดตัวอักษร',
      chipRow('แนวนอน',
        chip('◧', function () { applyStyle('al', 'left'); }, 'ชิดซ้าย') +
        chip('▤', function () { applyStyle('al', 'center'); }, 'กึ่งกลาง') +
        chip('◨', function () { applyStyle('al', 'right'); }, 'ชิดขวา')) +
      chipRow('แนวตั้ง',
        chip('⤒', function () { applyStyle('va', 'top'); }, 'ชิดบน') +
        chip('↔', function () { applyStyle('va', 'middle'); }, 'กึ่งกลางแนวตั้ง') +
        chip('⤓', function () { applyStyle('va', 'bottom'); }, 'ชิดล่าง')) +
      chipRow('ตัวอักษร',
        chip('𝐁', function () { applyStyle('b', 'toggle'); }, 'ตัวหนา (Ctrl+B)') +
        chip('𝐼', function () { applyStyle('i', 'toggle'); }, 'ตัวเอียง (Ctrl+I)') +
        chip('U̲', function () { applyStyle('u', 'toggle'); }, 'ขีดเส้นใต้ (Ctrl+U)')) +
      chipRow('ขนาด',
        chip('ปกติ', function () { applyStyle('fs', null); }, 'ขนาดปกติ') +
        ctxSizes().map(function (n) { return dchip(String(n), function () { applyStyle('fs', n); }, n + 'px · คลิกขวาเพื่อลบ', 'data-del-size="' + n + '"'); }).join('') +
        addChip('size')) +
      chipRow('สีอักษร',
        FCs.map(function (hex) { return chip('<span class="ctx-dot" style="background:#' + hex + '"></span>', function () { applyStyle('fc', hex); }, '#' + hex); }).join('') +
        chip('✕', function () { applyStyle('fc', null); }, 'ค่าเดิม')) +
      chipRow('สีพื้น',
        chip('✕', function () { applyStyle('bg', null); }, 'ไม่มีสี') +
        BGs.map(function (hex) { return chip('<span class="ctx-dot" style="background:#' + hex + ';border-color:#bbb;"></span>', function () { applyStyle('bg', hex); }, '#' + hex); }).join('')) +
      chipRow('ฟอนต์',
        chip('ปกติ', function () { applyStyle('ff', null); }, 'ฟอนต์ปกติ') +
        ctxFonts().map(function (fdef) {
          return dchip('<span style="font-family:\'' + fdef[0] + '\'">' + esc(fdef[1]) + '</span>', function () { applyStyle('ff', fdef[0] || null); }, (fdef[0] || 'ปกติ') + ' · คลิกขวาเพื่อลบ', 'data-del-font="' + esc(fdef[0]) + '"');
        }).join('') +
        addChip('font')));
    html += sub('🗄️', 'ฐานข้อมูล / ราคา',
      it('🔗', rowCode(sel.r) ? ('ลิงก์แถว: ' + esc(rowLinkLabel(sel.r).replace(/^⚠️[^—]*— /, '')) + ' (เปลี่ยน)…') : 'ลิงก์แถวกับสินค้า DB…', linkRowDB) +
      it('🗄️', 'ลิงก์เฉพาะช่องนี้…', linkCellDB) +
      ((doc.cellLinks && doc.cellLinks[anchorOf(sel.r, sel.c).r] && doc.cellLinks[anchorOf(sel.r, sel.c).r][anchorOf(sel.r, sel.c).c]) ? it('✂️', 'ยกเลิกลิงก์เฉพาะช่องนี้', unlinkCell) : '') +
      it('⛓️', 'ยกเลิกลิงก์แถว', unlinkRow) +
      sep() +
      it('📤', 'อัพเดทราคาเข้า DB…', function () { var b = document.getElementById('btnSync'); if (b) b.click(); else syncToDB(); }) +
      it('⏱️', (doc.rowSchedules && doc.rowSchedules[sel.r]) ? ('เวลาเฉพาะแถว: ' + doc.rowSchedules[sel.r] + '…') : 'ตั้งเวลาใช้ราคาเฉพาะแถวนี้…', function () {
        var cur = (doc.rowSchedules && doc.rowSchedules[sel.r]) || '';
        var w = prompt('เวลาเริ่มใช้ราคาของแถวนี้ (เช่น 2026-06-15 08:00)\nเว้นว่าง = ใช้เวลาของชีต', cur);
        if (w === null) return;
        setRowSchedule(w.trim());
      }) +
      it('🧽', 'ล้างเครื่องหมายปรับราคา (เริ่มรอบใหม่)', clearChanges));
    (function () {
      var R = range();
      var rLocked = true; for (var r = R.r1; r <= R.r2; r++) if (!(doc.adminRows && doc.adminRows[r])) { rLocked = false; break; }
      var cLocked = true; for (var c = R.c1; c <= R.c2; c++) if (!(doc.adminCols && doc.adminCols[c])) { cLocked = false; break; }
      html += sub('🙈', 'ซ่อน / ล็อก แถว-คอลัมน์',
        it('🙈', 'ซ่อนแถว (แบบ Excel)', hideRows) +
        it('👁️', 'เลิกซ่อนแถว', unhideRows) +
        it('🙈', 'ซ่อนคอลัมน์ (แบบ Excel)', hideCols) +
        it('👁️', 'เลิกซ่อนคอลัมน์', unhideCols) +
        it('🔄', 'แสดงที่ซ่อนทั้งหมด', showAllHidden) +
        sep() +
        it(rLocked ? '🔓' : '🔒', rLocked ? 'ปลดล็อกการมองเห็นแถว (ให้ผู้ใช้เห็น)' : 'ล็อกแถว (ซ่อนจากผู้ใช้)', toggleLockRows) +
        it(cLocked ? '🔓' : '🔒', cLocked ? 'ปลดล็อกการมองเห็นคอลัมน์ (ให้ผู้ใช้เห็น)' : 'ล็อกคอลัมน์ (ซ่อนจากผู้ใช้)', toggleLockCols) +
        (rowCode(sel.r) ? (sep() + it('🏷️', 'ซ่อนแถวนี้สำหรับตำแหน่ง…', function () { if (window.AdminCentral && AdminCentral.quickHideRow) AdminCentral.quickHideRow(rowCode(sel.r), rowLinkLabel(sel.r)); else toast('ยังไม่มีโมดูลระบบกลาง'); })) : ''));
    })();
    html += sep();
    html += it('⊞', 'ผสาน/ยกเลิกผสานเซลล์', toggleMerge);

    ctxEl.innerHTML = html;
    ctxEl.style.display = 'block';
    ctxEl.style.maxHeight = ''; ctxEl.style.overflowY = '';   // ไม่ตัด overflow — ให้ซับเมนูรายละเอียดกางออกข้างได้
    var vw = window.innerWidth, vh = window.innerHeight;
    var mw = ctxEl.offsetWidth, mh = ctxEl.offsetHeight;
    var gap = 6;
    // อิงจุดที่คลิกเสมอ (ใช้ได้ทั้งช่อง/หัวคอลัมน์/เลขแถว) · เปิดขวา-ล่าง · พลิกด้าน/หนีขอบ ไม่หลุดเฟรม
    var lx = (x + gap + mw <= vw - 4) ? (x + gap) : (x - gap - mw >= 4 ? (x - gap - mw) : (vw - mw - 4));
    var ty = (y + gap + mh <= vh - 4) ? (y + gap) : (y - gap - mh >= 4 ? (y - gap - mh) : (vh - mh - 4));
    lx = Math.max(4, Math.min(lx, vw - mw - 4));
    ty = Math.max(4, Math.min(ty, vh - mh - 4));
    ctxEl.style.left = lx + 'px';
    ctxEl.style.top = ty + 'px';
    // แถบลากย้ายเมนู
    var dh = ctxEl.querySelector('.ctx-drag');
    if (dh) dh.onmousedown = function (e) {
      e.preventDefault(); e.stopPropagation();
      var sx = e.clientX, sy = e.clientY, ol = parseFloat(ctxEl.style.left) || 0, ot = parseFloat(ctxEl.style.top) || 0;
      function mv(ev) {
        ctxEl.style.left = Math.max(0, Math.min(ev.clientX - sx + ol, window.innerWidth - ctxEl.offsetWidth)) + 'px';
        ctxEl.style.top = Math.max(0, Math.min(ev.clientY - sy + ot, window.innerHeight - ctxEl.offsetHeight)) + 'px';
      }
      function up() { document.removeEventListener('mousemove', mv, true); document.removeEventListener('mouseup', up, true); }
      document.addEventListener('mousemove', mv, true); document.addEventListener('mouseup', up, true);
    };
    // ซับเมนูย่อย: ขยับขึ้นให้พอดีจอ — ข้อมูลเยอะก็ขยับสูงขึ้นอีก
    ctxEl.querySelectorAll('.ctx-it.has-sub').forEach(function (itEl) {
      itEl.addEventListener('mouseenter', function () {
        var fly = itEl.querySelector('.ctx-flyout');
        if (!fly) return;
        fly.style.display = 'block';                 // โชว์ชั่วคราวเพื่อวัดความสูงจริง
        var ir = itEl.getBoundingClientRect();
        var fh = fly.offsetHeight;
        var desired = Math.max(8, Math.min(ir.top - 5, window.innerHeight - fh - 8));
        fly.style.top = (desired - ir.top) + 'px';
        fly.style.display = '';                      // คืนให้ CSS hover คุม
      });
    });
    // ถ้าชิดขอบขวา ให้ซับเมนูกางออกทางซ้ายแทน
    ctxEl.classList.toggle('flip', lx + ctxEl.offsetWidth + 200 > vw);
    function rebuildSub() { openCtx(x, y, true); }
    function addSizePrompt() { var v = prompt('ใส่ขนาดตัวอักษรที่ต้องการ (เช่น 16, 28, 36)'); if (v === null) return; var n = Math.round(parseFloat(v)); if (!(n > 0)) return; saveCtxSizes(ctxSizes().concat([n])); rebuildSub(); }
    function addFontPrompt() {
      var fam = prompt('ใส่ชื่อฟอนต์/ภาษา (เช่น Times New Roman, Angsana New, Noto Sans Thai)'); if (fam === null) return; fam = fam.trim(); if (!fam) return;
      var label = prompt('ชื่อที่จะแสดงในเมนู (เว้นว่าง = ใช้ชื่อฟอนต์)', fam); if (label === null) return; label = (label || '').trim() || fam;
      var arr = ctxFonts().filter(function (p) { return String(p[0]).toLowerCase() !== fam.toLowerCase(); }); arr.push([fam, label]); saveCtxFonts(arr); rebuildSub();
    }
    ctxEl.onclick = function (e) {
      var add = e.target.closest('.ctx-addchip');
      if (add) { e.stopPropagation(); if (add.dataset.add === 'size') addSizePrompt(); else addFontPrompt(); return; }
      var el = e.target.closest('[data-i]');
      if (!el) return;
      closeCtx();
      reg[+el.dataset.i]();
    };
    // คลิกขวาที่ชิปขนาด/ฟอนต์ = ลบออกจากรายการ
    ctxEl.oncontextmenu = function (e) {
      var ds = e.target.closest('[data-del-size]');
      if (ds) { e.preventDefault(); e.stopPropagation(); var n = +ds.getAttribute('data-del-size'); saveCtxSizes(ctxSizes().filter(function (x) { return x !== n; })); rebuildSub(); return; }
      var df = e.target.closest('[data-del-font]');
      if (df) { e.preventDefault(); e.stopPropagation(); var fam = df.getAttribute('data-del-font'); saveCtxFonts(ctxFonts().filter(function (p) { return String(p[0]) !== fam; })); rebuildSub(); return; }
    };
    // หลังสร้างเมนูใหม่ (เพิ่ม/ลบขนาด-ฟอนต์) — เปิดซับเมนูจัดตัวอักษรค้างไว้
    if (keepSub) {
      var subEl = [].slice.call(ctxEl.querySelectorAll('.ctx-it.has-sub')).filter(function (e2) { return /จัดตัวอักษร/.test(e2.textContent); })[0];
      if (subEl) {
        var fly2 = subEl.querySelector('.ctx-flyout');
        if (fly2) {
          fly2.style.display = 'block';
          var ir2 = subEl.getBoundingClientRect(); var fh2 = fly2.offsetHeight;
          var des2 = Math.max(8, Math.min(ir2.top - 5, window.innerHeight - fh2 - 8));
          fly2.style.top = (des2 - ir2.top) + 'px';
          subEl.addEventListener('mouseleave', function () { fly2.style.display = ''; fly2.style.top = ''; }, { once: true });
        }
      }
    }
  }
  function closeCtx() { ctxEl.style.display = 'none'; }

  // ---------- price-change detail popover (คลิกดูรายละเอียด ขึ้น/ลงเท่าไหร่) ----------
  var popEl2 = null;
  function priceSlotField(c) { for (var i = 0; i < PRICE_COLS.length; i++) if (PRICE_COLS[i].c === c) return 'salePrice' + PRICE_COLS[i].slot; return null; }
  function showPricePop(r, c, td) {
    var isPrice = !!PRICE_NAME[c];
    var chg = doc.changes && doc.changes[r] && doc.changes[r][c];
    if (chg && chgExpired(chg)) chg = null;
    var curV = valueOf(r, c), curN = nOr(curV, 0);
    if (!isPrice && !chg) return;
    if (isPrice && !XL2.isNumeric(curV) && !chg) return;
    if (!popEl2) { popEl2 = document.createElement('div'); popEl2.className = 'sg-pricepop'; document.body.appendChild(popEl2); }
    var name = PRICE_NAME[c] || 'ราคา';
    var html = '';
    // ส่วนการปรับราคา (ถ้ามี)
    if (chg) {
      var oldN = nOr(chg.old, 0), cN = nOr(curV, oldN), d = cN - oldN;
      var pct = oldN ? Math.round(Math.abs(d) / oldN * 1000) / 10 : 0;
      var eff = parseEff(chg.effectiveAt), pending = eff.getTime() > Date.now();
      html += '<div class="pp-head">' + (pending ? '⏳ กำลังจะปรับปรุงราคา' : (d > 0 ? '▲ ปรับขึ้นแล้ว' : d < 0 ? '▼ ปรับลงแล้ว' : 'ปรับปรุงแล้ว')) + '</div>' +
        '<div class="pp-row"><span>' + esc(name) + ' เดิม</span><b>' + XL2.fmtNum(oldN) + '</b></div>' +
        '<div class="pp-row"><span>' + (pending ? 'ราคาใหม่' : 'ปัจจุบัน') + '</span><b>' + XL2.fmtNum(cN) + '</b></div>' +
        (d !== 0 ? '<div class="pp-row pp-d ' + (d > 0 ? 'up' : 'dn') + '"><span>ส่วนต่าง</span><b>' + (d > 0 ? '+' : '−') + XL2.fmtNum(Math.abs(d)) + ' (' + pct + '%)</b></div>' : '') +
        (chg.effectiveAt && chg.effectiveAt !== 'ทันที' ? '<div class="pp-eff">มีผล: ' + esc(chg.effectiveAt) + '</div>' : '');
    } else {
      html += '<div class="pp-head">💲 ' + esc(name) + '</div><div class="pp-row"><span>ราคา (เครดิต)</span><b>' + XL2.fmtNum(curN) + '</b></div>';
    }
    // เครดิต + VAT (คำนวณตามกฎ)
    if (window.DBX && isPrice && curN > 0) {
      var pr = DBX.computePricing(curN);
      html += '<div class="pp-sep"></div>' +
        '<div class="pp-row pp-credit"><span>เครดิต + VAT ' + Math.round(pr.vatRate * 100) + '%</span><b>' + XL2.fmtNum(pr.creditVatRounded) + '</b></div>' +
        '<div class="pp-sub">ปัดขึ้นทีละ ' + pr.roundStep + ' (ก่อนปัด ' + pr.creditVat.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ')</div>';
    }
    // ประวัติราคา (3 รอบ) + วันที่ใช้ล่าสุด
    var code = rowCode(r), fld = priceSlotField(c);
    if (window.DBX && code && fld) {
      var hist = (DBX.priceHistory(code) || {})[fld];
      if (hist && hist.length) {
        html += '<div class="pp-sep"></div><div class="pp-histlbl">ประวัติราคา (ล่าสุด → เก่า)</div>';
        html += hist.map(function (h, i) {
          var dt = new Date(h.ts);
          return '<div class="pp-hist"><span>' + (i === 0 ? '★ ใช้ล่าสุด' : 'ก่อนหน้า ' + i) + '</span><b>' + XL2.fmtNum(h.v) + '</b><span class="pp-histdt">' + dt.toLocaleDateString('th-TH') + '</span></div>';
        }).join('');
      }
    }
    popEl2.innerHTML = html;
    var rect = td.getBoundingClientRect();
    popEl2.style.display = 'block';
    popEl2.style.left = Math.min(rect.left, window.innerWidth - 230) + 'px';
    popEl2.style.top = Math.min(rect.bottom + 4, window.innerHeight - popEl2.offsetHeight - 8) + 'px';
    if (window.PopupStack) PopupStack.push(popEl2, hidePricePop);
  }
  function hidePricePop() { if (popEl2) { popEl2.style.display = 'none'; if (window.PopupStack) PopupStack.remove(popEl2); } }

  // ---------- ป๊อปอัปความสูงยาง (คลิกช่องขนาด) ----------
  var sizePopEl = null;
  function hideSizePop() { if (sizePopEl) { sizePopEl.style.display = 'none'; if (window.PopupStack) PopupStack.remove(sizePopEl); } }
  function showSizePop(td, h) {
    var dk = !!(document.body && document.body.classList.contains('dark'));
    if (!sizePopEl) { sizePopEl = document.createElement('div'); sizePopEl.className = 'sg-sizepop'; document.body.appendChild(sizePopEl); }
    sizePopEl.style.cssText = 'position:fixed;z-index:9500;border:1.5px solid #F47C20;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.25);padding:11px 14px;font-family:Arial,Tahoma,sans-serif;min-width:172px;background:' + (dk ? '#2a2a2a' : '#fff') + ';';
    var cm = Math.round(h.cm * 10) / 10, inch = Math.round(h.inch * 10) / 10;
    var wCm = (h.widthCm != null) ? Math.round(h.widthCm * 10) / 10 : null;
    var wIn = (h.widthIn != null) ? Math.round(h.widthIn * 10) / 10 : null;
    var numCol = dk ? '#f0f0f0' : '#222';
    var note = h.stored ? 'ความสูงจากค่าที่บันทึกไว้ · กว้างคำนวณจากขนาด' : (h.approx ? '≈ คำนวณ (อนุมานซีรีส์ 80)' : 'คำนวณจากขนาด');
    function pair(cmv, inv) {
      return '<div style="display:flex;gap:12px;align-items:baseline;">' +
        '<div><span style="font:800 19px/1 inherit;color:' + numCol + ';">' + cmv + '</span> <span style="font-size:12px;color:#888;">ซม.</span></div>' +
        '<div style="color:#ccc;">·</div>' +
        '<div><span style="font:800 19px/1 inherit;color:' + numCol + ';">' + inv + '</span> <span style="font-size:12px;color:#888;">นิ้ว</span></div></div>';
    }
    sizePopEl.innerHTML =
      '<div style="font:800 13px/1.2 inherit;color:#C75B00;margin-bottom:6px;">🛞 ' + esc(h.sizeText) + '</div>' +
      '<div style="font-size:11px;color:#999;margin-bottom:2px;">ความสูง (เส้นผ่าศูนย์กลางรวม)</div>' + pair(cm, inch) +
      (wCm != null ? '<div style="font-size:11px;color:#999;margin:8px 0 2px;">หน้ากว้าง (หน้ายาง)</div>' + pair(wCm, wIn) : '') +
      '<div style="font-size:10.5px;color:#bbb;margin-top:8px;">' + esc(note) + '</div>';
    sizePopEl.style.display = 'block';
    var rc = td.getBoundingClientRect();
    sizePopEl.style.left = Math.max(8, Math.min(rc.right + 6, window.innerWidth - sizePopEl.offsetWidth - 12)) + 'px';
    sizePopEl.style.top = Math.max(8, Math.min(rc.top, window.innerHeight - sizePopEl.offsetHeight - 12)) + 'px';
    if (window.PopupStack) PopupStack.push(sizePopEl, hideSizePop);
  }

  // ---------- fill down / right (Ctrl+D / Ctrl+R แบบ Excel) ----------
  function fillDown() {
    if (view.mode !== 'admin') return;
    var R = range();
    pushUndo();
    if (R.r1 === R.r2) { if (R.r1 > 0) for (var c = R.c1; c <= R.c2; c++) copyShift(R.r1 - 1, c, R.r1, c); }
    else for (var r = R.r1 + 1; r <= R.r2; r++) for (var c2 = R.c1; c2 <= R.c2; c2++) copyShift(R.r1, c2, r, c2);
    afterChange(); toast('เติมลง (Ctrl+D)');
  }
  function fillRight() {
    if (view.mode !== 'admin') return;
    var R = range();
    pushUndo();
    if (R.c1 === R.c2) { if (R.c1 > 0) for (var r = R.r1; r <= R.r2; r++) copyShift(r, R.c1 - 1, r, R.c1); }
    else for (var c = R.c1 + 1; c <= R.c2; c++) for (var r2 = R.r1; r2 <= R.r2; r2++) copyShift(r2, R.c1, r2, c);
    afterChange(); toast('เติมขวา (Ctrl+R)');
  }

  // เพิ่ม/ลดขนาดตัวอักษรทีละขั้น (เหมือนปุ่ม A˄ A˅ ของ Excel)
  var FS_STEPS = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36, 48];
  function setFontSize(px) {
    if (view.mode !== 'admin') return;
    px = parseFloat(px); if (!(px >= 6 && px <= 96)) return;
    pushUndo();
    var R = range();
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) { var cell = ensureCell(r, c); cell.s = cell.s || {}; cell.s.fs = px; }
    afterChange();
  }
  function stepFont(dir) {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range();
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) {
      var cell = ensureCell(r, c); cell.s = cell.s || {};
      var cur = cell.s.fs || 10;
      var i = 0;
      while (i < FS_STEPS.length - 1 && FS_STEPS[i] < cur) i++;
      if (dir > 0) i = Math.min(FS_STEPS.length - 1, (FS_STEPS[i] <= cur ? i + 1 : i));
      else i = Math.max(0, (FS_STEPS[i] >= cur ? i - 1 : i));
      cell.s.fs = FS_STEPS[i];
    }
    afterChange();
    toast(dir > 0 ? 'เพิ่มขนาดตัวอักษร' : 'ลดขนาดตัวอักษร');
  }

  // จัดการทศนิยม (เพิ่ม/ลดตำแหน่ง เหมือน Excel)
  function stepDp(dir) {
    if (view.mode !== 'admin') return;
    pushUndo();
    var R = range();
    for (var r = R.r1; r <= R.r2; r++) for (var c = R.c1; c <= R.c2; c++) {
      var cell = ensureCell(r, c); cell.s = cell.s || {};
      var cur = (cell.s.dp != null) ? cell.s.dp : 0;
      cell.s.dp = Math.max(0, Math.min(6, cur + dir));
    }
    afterChange();
    toast(dir > 0 ? 'เพิ่มทศนิยม' : 'ลดทศนิยม');
  }

  // ---------- keyboard ----------
  // เลื่อนด้วยลูกศร/Tab มาที่ช่อง "ขนาด" → เด้งป๊อปอัปข้อมูลเหมือนคลิกเมาส์ (noFocus = ไม่แย่งโฟกัส ลูกศรเลื่อนต่อได้)
  function syncSizePopup() {
    if (!window.ProductInfo) return;
    if (sel.c === sizeCol() && rowKind(sel.r) === 'data') {
      var t = rowSizeText(sel.r), a = anchorOf(sel.r, sel.c);
      var td = rootEl.querySelector('td.sg-c[data-r="' + a.r + '"][data-c="' + a.c + '"]');
      if (t && td) { ProductInfo.showPopup(t, td, { isAdmin: view.mode === 'admin', noFocus: true, onChange: function () { invalidate(); render(); } }); return; }
    }
    ProductInfo.close();
  }
  function onKey(e) {
    if (editing && !editing.viaFx) {
      if (e.key === 'Enter') { e.preventDefault(); commitEdit(e.shiftKey ? 'up' : 'down'); }
      else if (e.key === 'Tab') { e.preventDefault(); commitEdit(e.shiftKey ? 'left' : 'right'); }
      else if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
      return;
    }
    var meta = e.ctrlKey || e.metaKey;
    if (meta) {
      var k = e.key.toLowerCase();
      // แป้นพิมพ์ภาษาไทย: Ctrl+X ส่ง “ฝ” มาแทน x → ใช้ตำแหน่งปุ่มจริง (e.code) แทน
      if (k.length === 1 && !/[a-z0-9+\-= ]/.test(k) && /^Key[A-Z]$/.test(e.code || '')) k = e.code.slice(3).toLowerCase();
      if (k === 'c') { e.preventDefault(); doCopy(false); }
      else if (k === 'x') { e.preventDefault(); doCopy(true); }
      else if (k === 'v') { e.preventDefault(); doPaste(); }
      else if (k === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); }
      else if (k === 'y') { e.preventDefault(); redo(); }
      else if (k === '+' || k === '=') {
        e.preventDefault();
        var R0 = range();
        if (clip && clip.fullRows) insertCopiedRows();
        else if (clip && clip.fullCols) insertCopiedCols();
        else if (R0.c1 === 0 && R0.c2 === doc.nCols - 1) insertRows(R0.r1, R0.r2 - R0.r1 + 1);
        else if (R0.r1 === 0 && R0.r2 === doc.nRows - 1) insertCols(R0.c1, R0.c2 - R0.c1 + 1);
      }
      else if (k === '-') {
        e.preventDefault();
        var R1 = range();
        if (R1.c1 === 0 && R1.c2 === doc.nCols - 1) deleteRow();
        else if (R1.r1 === 0 && R1.r2 === doc.nRows - 1) deleteCol();
      }
      else if (k === 'b') { e.preventDefault(); applyStyle('b', 'toggle'); }
      else if (k === 'i') { e.preventDefault(); applyStyle('i', 'toggle'); }
      else if (k === 'u') { e.preventDefault(); applyStyle('u', 'toggle'); }
      else if (k === 'a') { e.preventDefault(); sel.ar = 0; sel.ac = 0; sel.r = doc.nRows - 1; sel.c = doc.nCols - 1; paintSel(); toast('เลือกทั้งหมด (Ctrl+A)'); }
      else if (k === 's') { e.preventDefault(); save(); }
      else if (k === 'p') { e.preventDefault(); window.print(); }
      else if (k === 'f') { e.preventDefault(); var fq = document.getElementById('fq'); if (fq) fq.focus(); }
      else if (k === 'd') { e.preventDefault(); fillDown(); }
      else if (k === 'r') { e.preventDefault(); fillRight(); }
      else if (k === 'home') { e.preventDefault(); setActive(0, 0); }
      else if (k === 'end') { e.preventDefault(); setActive(doc.nRows - 1, doc.nCols - 1); }
      else if (k === ' ') { e.preventDefault(); sel.ar = 0; sel.r = doc.nRows - 1; paintSel(); }   // Ctrl+Space = ทั้งคอลัมน์
      else if (k === 'arrowdown') { e.preventDefault(); setActive(doc.nRows - 1, sel.c, e.shiftKey); }
      else if (k === 'arrowup') { e.preventDefault(); setActive(0, sel.c, e.shiftKey); }
      else if (k === 'arrowleft') { e.preventDefault(); setActive(sel.r, 0, e.shiftKey); }
      else if (k === 'arrowright') { e.preventDefault(); setActive(sel.r, doc.nCols - 1, e.shiftKey); }
      return;
    }
    // Logitech G-keys (ตั้งมาโครใน G HUB ให้ส่ง F13–F24)
    var GK = { F13: function () { doCopy(false); }, F14: function () { doCopy(true); }, F15: doPaste,
      F16: undo, F17: redo, F18: save, F19: addModelRow, F20: addSizeGroup, F21: toggleMerge,
      F22: function () { window.print(); }, F23: syncToDB, F24: function () { var b = document.getElementById('btnKeys'); if (b) b.click(); } };
    if (GK[e.key]) { e.preventDefault(); GK[e.key](); return; }
    switch (e.key) {
      case 'ArrowDown': e.preventDefault(); setActive(stepRow(sel.r, 1), sel.c, e.shiftKey); break;
      case 'ArrowUp': e.preventDefault(); setActive(stepRow(sel.r, -1), sel.c, e.shiftKey); break;
      case 'ArrowLeft': e.preventDefault(); setActive(sel.r, stepCol(sel.c, -1), e.shiftKey); break;
      case 'ArrowRight': e.preventDefault(); setActive(sel.r, stepCol(sel.c, 1), e.shiftKey); break;
      case 'Tab': e.preventDefault(); setActive(sel.r, stepCol(sel.c, e.shiftKey ? -1 : 1)); break;
      case 'Enter': case 'F2': e.preventDefault(); startEdit(null); break;
      case 'Delete': case 'Backspace': e.preventDefault(); delRange(); break;
      case 'Home': e.preventDefault(); setActive(sel.r, 0); break;
      case 'End': e.preventDefault(); setActive(sel.r, doc.nCols - 1); break;
      case 'PageDown': e.preventDefault(); setActive(Math.min(doc.nRows - 1, sel.r + 20), sel.c, e.shiftKey); break;
      case 'PageUp': e.preventDefault(); setActive(Math.max(0, sel.r - 20), sel.c, e.shiftKey); break;
      case ' ': if (e.shiftKey) { e.preventDefault(); sel.ac = 0; sel.c = doc.nCols - 1; paintSel(); break; }   // Shift+Space = ทั้งแถว
        e.preventDefault(); startEdit(' '); break;
      case 'Escape':
        if (window.ProductInfo) ProductInfo.close();
        if (clip) { clearClip(); break; }
        if (multiCols.length || multiRows.length) { clearMulti(); break; }   // ยกเลิกการเลือกหลายคอลัมน์/แถวแบบ Ctrl ก่อน
        if (sel.r !== sel.ar || sel.c !== sel.ac) { sel.ar = sel.r; sel.ac = sel.c; paintSel(); break; }   // ยกเลิกการลากเลือกหลายช่อง → เหลือช่องเดียว
        closeCtx(); break;
      default:
        if (e.key.length === 1 && !e.altKey) { e.preventDefault(); startEdit(e.key); }
    }
    if (/^(Arrow|Tab|Home|End|Page)/.test(e.key)) syncSizePopup();
  }

  // ---------- mouse ----------
  var drag = null;  // 'cell' | 'gut' | 'head' | 'fill'
  function onMouseDown(e) {
    closeCtx();
    // คลิกช่องสถานะ → เปิด side panel รายละเอียดสินค้า
    if (e.button === 0) {
      var sccd = e.target.closest('td.sg-statuscell');
      if (sccd && window.DBX && rowCode(+sccd.dataset.r)) { openDetailPanel(+sccd.dataset.r, sccd); e.preventDefault(); return; }
    }
    if (e.target.classList.contains('sg-rzc')) { startRzCol(+e.target.dataset.rz, e.clientX); e.preventDefault(); return; }
    if (e.target.classList.contains('sg-rzr')) { startRzRow(+e.target.dataset.rzr, e.clientY); e.preventDefault(); return; }
    // จุดจับมุมขวาล่าง (fill handle) — ลากเพื่อก๊อปปี้ลง/ขวาเหมือน Excel
    if (e.button === 0 && view.mode === 'admin') {
      var tdf = e.target.closest('td.sg-c');
      if (tdf) {
        var Rf = range();
        var brEl = cellEl(Rf.r2, Rf.c2);
        if (tdf === brEl || tdf.classList.contains('act')) {
          var rect = tdf.getBoundingClientRect();
          if (e.clientX > rect.right - 9 && e.clientY > rect.bottom - 9) {
            drag = 'fill'; fillTarget = null;
            e.preventDefault();
            return;
          }
        }
      }
    }
    if (e.target.classList.contains('sg-fh')) { drag = 'fill'; e.preventDefault(); return; }
    var h = e.target.closest('th.sg-h');
    if (h) {
      if (editing) commitEdit();
      var hc = +h.dataset.hc;
      var Rh = range();
      if (e.button === 2) {
        // คลิกขวา: ถ้าคอลัมน์นี้อยู่ในช่วงที่เลือกไว้แล้ว คงการเลือกหลายคอลัมน์ไว้ (สั่งงานทีเดียวได้ทั้งชุด)
        if (!(hc >= Rh.c1 && hc <= Rh.c2)) { sel.ac = hc; sel.c = hc; sel.ar = 0; sel.r = doc.nRows - 1; }
        paintSel(); rootEl.focus(); return;
      }
      if (e.ctrlKey || e.metaKey) {   // Ctrl+คลิก = สลับเลือก/เอาออกคอลัมน์นี้ เข้าชุดเลือกหลายคอลัมน์
        var ic = multiCols.indexOf(hc);
        if (ic >= 0) multiCols.splice(ic, 1); else multiCols.push(hc);
        sel.ac = hc; sel.c = hc; sel.ar = 0; sel.r = doc.nRows - 1;
        paintSel(); rootEl.focus(); e.preventDefault();
        toast(multiCols.length > 1 ? 'เลือก ' + multiCols.length + ' คอลัมน์ — ลากเส้นขอบหัวคอลัมน์เพื่อปรับความกว้างพร้อมกัน' : (multiCols.length === 1 ? 'Ctrl+คลิกหัวคอลัมน์อื่นเพื่อเลือกหลายคอลัมน์' : ''));
        return;
      }
      clearMulti();
      if (e.shiftKey) sel.c = hc; else { sel.ac = hc; sel.c = hc; }
      sel.ar = 0; sel.r = doc.nRows - 1;
      drag = 'head'; paintSel(); rootEl.focus(); e.preventDefault(); return;
    }
    var g = e.target.closest('td.sg-g');
    if (g) {
      if (editing) commitEdit();
      var gr = +g.dataset.gr;
      var Rg = range();
      if (e.button === 2) {
        // คลิกขวา: ถ้าแถวนี้อยู่ในช่วงที่เลือกไว้แล้ว คงการเลือกหลายแถวไว้
        if (!(gr >= Rg.r1 && gr <= Rg.r2)) { sel.ar = gr; sel.r = gr; sel.ac = 0; sel.c = doc.nCols - 1; }
        paintSel(); rootEl.focus(); return;
      }
      if (e.ctrlKey || e.metaKey) {   // Ctrl+คลิก = สลับเลือก/เอาออกแถวนี้ เข้าชุดเลือกหลายแถว
        var ig = multiRows.indexOf(gr);
        if (ig >= 0) multiRows.splice(ig, 1); else multiRows.push(gr);
        sel.ar = gr; sel.r = gr; sel.ac = 0; sel.c = doc.nCols - 1;
        paintSel(); rootEl.focus(); e.preventDefault();
        toast(multiRows.length > 1 ? 'เลือก ' + multiRows.length + ' แถว — ลากเส้นขอบหัวแถวเพื่อปรับความสูงพร้อมกัน' : (multiRows.length === 1 ? 'Ctrl+คลิกหัวแถวอื่นเพื่อเลือกหลายแถว' : ''));
        return;
      }
      clearMulti();
      if (e.shiftKey) sel.r = gr; else { sel.ar = gr; sel.r = gr; }
      sel.ac = 0; sel.c = doc.nCols - 1;
      drag = 'gut'; paintSel(); rootEl.focus(); e.preventDefault(); return;
    }
    if (e.target.classList.contains('sg-corner')) {
      sel.ar = 0; sel.ac = 0; sel.r = doc.nRows - 1; sel.c = doc.nCols - 1; paintSel(); rootEl.focus(); return;
    }
    var td = e.target.closest('td.sg-c');
    if (!td) return;
    if (editing) commitEdit();
    // คลิกช่อง DOT (คอลัมน์ผูก dotRange) ที่มี > 1 ชุด → popup ราคาแยกราย DOT
    if (e.button === 0 && window.DOT && doc.columnMap && doc.columnMap[+td.dataset.c] && doc.columnMap[+td.dataset.c].field === 'dotRange') {
      var _dr = +td.dataset.r, _dcode = rowCode(_dr), _dp = _dcode ? dbCache[_dcode] : null;
      if (_dp && DOT.shouldPopup(_dp)) {
        var _pv = function (cc) { try { var v = valueOf(_dr, cc); return (window.XL2 && XL2.isNumeric(v)) ? XL2.toN(v) : ''; } catch (e2) { return ''; } };
        if (DOT.openPricePopup(_dp, td, view.mode, { retail: _pv(7), b: _pv(13), a: _pv(16), s: _pv(19) })) { rootEl.focus(); return; }
      }
    }
    // คลิกช่อง "ขนาด" (คอลัมน์ขนาดหลัก) → ป๊อปความสูงยาง cm + นิ้ว (ไม่บล็อกการเลือก/แก้ไข)
    if (e.button === 0 && +td.dataset.c === sizeCol()) {
      var _szt = rowSizeText(+td.dataset.r);
      if (_szt && window.ProductInfo) ProductInfo.showPopup(_szt, td, { isAdmin: view.mode === 'admin', onChange: function () { invalidate(); render(); } });
      else hideSizePop();
    } else { hideSizePop(); if (window.ProductInfo) ProductInfo.close(); }
    if ((view.mode === 'user' && td.classList.contains('pclick')) || (PRICE_NAME[+td.dataset.c] && rowCode(+td.dataset.r))) {
      showPricePop(+td.dataset.r, +td.dataset.c, td);
    } else hidePricePop();
    if (e.button === 2) { // right click: keep selection if inside
      var r = +td.dataset.r, c = +td.dataset.c, R = range();
      if (r < R.r1 || r > R.r2 || c < R.c1 || c > R.c2) setActive(r, c, false, true);
      return;
    }
    clearMulti();
    setActive(+td.dataset.r, +td.dataset.c, e.shiftKey, true);
    drag = 'cell';
    rootEl.focus();
  }
  var linkTipShown = false;
  function onMouseMove(e) {
    // ป้ายชื่อสินค้าทันทีเมื่อชี้เลขแถวที่ลิงก์กับ DB (อ้างอิงชื่อจากฐานข้อมูล)
    if (!rz && !drag) {
      // hover หัวคอลัมน์ที่ผูก DB/สถานะ → popup บอกว่าผูกกับอะไร
      var hh0 = e.target.closest('th.sg-h');
      if (hh0 && window.DBX && view.mode === 'admin') {
        var hc = +hh0.dataset.hc;
        var locked = doc.adminCols && doc.adminCols[hc];
        var lockTag = locked ? '<div class="tipm-lock">' + esc(lockGlyph() + ' ' + lockDesc()) + '</div>' : '';
        var msg = '';
        if (doc.statusCol === hc) {
          var seen = {}, lines = [];
          for (var rr = 0; rr < doc.nRows; rr++) {
            statusIconsFor(rr).forEach(function (d) { if (!seen[d.key]) { seen[d.key] = 1; lines.push('<div class="tipm-row"><span' + (d.color ? ' style="color:#' + d.color + '"' : '') + '>' + (window.IconKit ? IconKit.html(d.icon) : esc(d.icon)) + '</span> ' + esc(d.label) + (d.popup ? ' <i>— ' + esc(d.popup) + '</i>' : '') + '</div>'); } });
          }
          msg = '<div class="tipm-head">📊 คอลัมน์สถานะ — ไอคอนที่แสดงในคอลัมน์นี้</div>' + (lines.length ? lines.join('') : '<div class="tipm-row">— ยังไม่มีสถานะ —</div>') + lockTag;
        } else {
          var cmH = doc.columnMap && doc.columnMap[hc];
          if (cmH) msg = '<div class="tipm-head">' + (cmH.mode === 'write' ? '✏️ เขียนกลับ DB ได้' : '🔗 อ่านอย่างเดียว') + '</div><div class="tipm-row">ผูกฟิลด์: ' + esc(window.DBX.fieldLabel(cmH.field)) + '</div>' + lockTag;
          else if (locked) msg = '<div class="tipm-head">คอลัมน์ ' + XL2.colName(hc) + '</div>' + lockTag;   // คอลัมน์ที่ล็อกอย่างเดียว ก็แสดง popup
        }
        if (msg) { showLinkTip(hh0, msg, false, true); linkTipShown = true; return; }
        if (linkTipShown) { hideTip(); linkTipShown = false; }
      }
      // hover ไอคอนแม่กุญแจ → popup คำอธิบาย
      var lkIc = e.target.closest('.sg-lockic');
      if (lkIc) { showLinkTip(lkIc, lockGlyph() + ' ' + lockDesc(), false); linkTipShown = true; return; }
      // hover ไอคอนสถานะ → popup อธิบาย (เหนือ/ใต้แถว ไม่บัง ไม่หลุดเฟรม)
      var stIc = e.target.closest('.sg-st-ic');
      if (stIc && window.DBX) {
        var def = window.DBX.statusDefByKey(stIc.dataset.stkey);
        if (def) { showLinkTip(stIc, (window.IconKit ? IconKit.plain(def.icon) : (def.icon || '')) + ' ' + def.label + (def.popup ? ' — ' + def.popup : ''), false); linkTipShown = true; return; }
      }
      // hover มุมลิงก์เฉพาะช่อง (cell-link 3C) → popup บอกว่าผูกกับรหัส/ฟิลด์อะไร
      var clCorner = e.target.closest('.celllink-corner');
      if (clCorner && window.DBX) {
        var clTd = clCorner.closest('td.sg-c');
        if (clTd) {
          var clR = +clTd.dataset.r, clC = +clTd.dataset.c;
          var cl = doc.cellLinks && doc.cellLinks[clR] && doc.cellLinks[clR][clC];
          if (cl) {
            var clP = isCode13(cl.code) ? dbCache[cl.code] : null;
            var clName = clP ? (clP.name || '') : '';
            var clVal = (clP && cl.field != null) ? dbFieldVal(clP, cl.field) : '';
            var clWritable = window.DBX.isWritable(cl.field);
            var clMsg = '<div class="tipm-head">🗄️ ลิงก์เฉพาะช่องนี้</div>' +
              '<div class="tipm-row"><b>' + esc(cl.code) + '</b>' + (clName ? ' · ' + esc(clName) : '') + '</div>' +
              '<div class="tipm-row">' + (clWritable ? '✏️' : '🔒') + ' ' + esc(window.DBX.fieldLabel(cl.field)) +
              (clVal !== '' ? ' = <b>' + esc(String(clVal)) + '</b>' : '') +
              ' · ' + (clWritable ? 'เขียนได้' : 'อ่านอย่างเดียว') + '</div>';
            showLinkTip(clTd, clMsg, false, true); linkTipShown = true; return;
          }
        }
      }
      var g0 = e.target.closest('td.sg-g');
      var gr0 = g0 ? +g0.dataset.gr : -1;
      var lnk0 = g0 && rowCode(gr0);
      var gLocked = g0 && view.mode === 'admin' && doc.adminRows && doc.adminRows[gr0];
      if (lnk0 || gLocked) {
        var gmsg = lnk0 ? (rowLinkLabel(gr0).indexOf('⚠️') === 0 ? rowLinkLabel(gr0) : '🔗 ' + rowLinkLabel(gr0)) : ('แถว ' + (gr0 + 1));
        if (gLocked) gmsg += ' · ' + lockDesc();
        showLinkTip(g0, gmsg, lnk0 && (rowLinkStatus(gr0) === 'missing' || rowLinkStatus(gr0) === 'inactive'));
        linkTipShown = true;
      } else if (linkTipShown) { hideTip(); linkTipShown = false; }
    }
    if (rz) { moveRz(e.clientX, e.clientY); return; }
    if (!drag) return;
    if (drag === 'head') { var h = e.target.closest('th.sg-h'); if (h) { sel.c = +h.dataset.hc; paintSel(); } return; }
    if (drag === 'gut') { var g = e.target.closest('td.sg-g'); if (g) { sel.r = +g.dataset.gr; paintSel(); } return; }
    var td = e.target.closest('td.sg-c'); if (!td) return;
    if (drag === 'fill') { showFillPreview(+td.dataset.r, +td.dataset.c); return; }
    // ลากผ่านเซลล์ผสาน (ช่องขนาด/แถบหัว) → ขยายเฉพาะแถว ไม่ดึงคอลัมน์อื่นเข้ามา
    if ((td.rowSpan > 1 || td.colSpan > 1) && +td.dataset.c !== sel.ac) { setActive(+td.dataset.r, sel.c, true); return; }
    setActive(+td.dataset.r, +td.dataset.c, true);
  }
  var fillTarget = null;
  function showFillPreview(r, c) {
    fillTarget = { r: r, c: c };
    rootEl.querySelectorAll('.sg-c.fillpv').forEach(function (e) { e.classList.remove('fillpv'); });
    var R = range();
    if (r > R.r2) for (var rr = R.r2 + 1; rr <= r; rr++) for (var cc = R.c1; cc <= R.c2; cc++) mark(rr, cc);
    else if (c > R.c2) for (var cc2 = R.c2 + 1; cc2 <= c; cc2++) for (var rr2 = R.r1; rr2 <= R.r2; rr2++) mark(rr2, cc2);
    function mark(rr, cc) { var el = cellEl(rr, cc); if (el) el.classList.add('fillpv'); }
    drawSelRect();   // ขยายกรอบใหญ่ครอบพื้นที่ลากเติมทั้งหมด (กรอบเดียว ไม่มีเส้นรายช่อง)
  }
  function onMouseUp(e) {
    if (rz) { endRz(); return; }
    if (drag === 'fill' && fillTarget) {
      rootEl.querySelectorAll('.sg-c.fillpv').forEach(function (el) { el.classList.remove('fillpv'); });
      fillTo(fillTarget.r, fillTarget.c);
      fillTarget = null;
      drawSelRect();
    }
    drag = null;
  }
  function onDblClick(e) {
    if (e.target.classList.contains('sg-rzc')) { autofitCol(+e.target.dataset.rz); return; }
    if (e.target.classList.contains('sg-rzr')) { pushUndo(); delete doc.rowH[+e.target.dataset.rzr]; afterChange(); toast('คืนความสูงปกติ'); return; }
    var td = e.target.closest('td.sg-c'); if (!td) return;
    setActive(+td.dataset.r, +td.dataset.c, false, true);
    startEdit(null);
  }

  // ---------- misc ----------
  var toastT;
  function toast(msg) {
    var t = document.getElementById('toast'); if (!t) return;
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastT); toastT = setTimeout(function () { t.classList.remove('show'); }, 1500);
  }

  function setMode(m) {
    if (editing) cancelEdit();
    view.mode = m === 'user' ? 'user' : 'admin';
    invalidate(); buildCover(); render();
    return view.mode;
  }
  function setZoom(z) { view.zoom = Math.max(0.5, Math.min(2, z)); render(); }
  function toggleSecret() { view.secret = !view.secret; render(); return view.secret; }

  // ---------- init ----------
  function init(opts) {
    rootEl = opts.root; fxEl = opts.fx; nameEl = opts.name; statusEl = opts.status; sumEl = opts.sum; ctxEl = opts.ctx;
    var saved = XL2.store.loadCurrent();
    doc = (saved && saved.cells) ? saved : window.XL2Build.fromPickup01();
    doc.adminRows = doc.adminRows || {}; doc.adminCols = doc.adminCols || {};
    doc.merges = doc.merges || {}; doc.colW = doc.colW || []; doc.rowH = doc.rowH || [];
    doc.rowLinks = doc.rowLinks || {};
    // migrate: ช่อง Margin (คอลัมน์ K) ใส่สีตามบวก/ลบ
    for (var mr = 0; mr < doc.nRows; mr++) {
      var mc = doc.cells[mr + ':10'];
      if (mc && mc.f && /^=H\d+-G\d+$/.test(mc.f)) { mc.s = mc.s || {}; if (!mc.s.cond) { mc.s.cond = 'pn'; delete mc.s.fc; } }
    }

    inputEl = document.createElement('input');
    inputEl.className = 'sg-input'; inputEl.style.display = 'none';
    tipEl = document.createElement('div');
    tipEl.className = 'sg-tip'; tipEl.style.display = 'none';

    buildCover(); render(); setActive(0, 0);

    rootEl.tabIndex = 0;
    rootEl.addEventListener('keydown', onKey);
    rootEl.addEventListener('mousedown', onMouseDown);
    rootEl.addEventListener('mousemove', onMouseMove);
    rootEl.addEventListener('mouseleave', function () { if (linkTipShown) { hideTip(); linkTipShown = false; } });
    document.addEventListener('mouseup', onMouseUp);
    rootEl.addEventListener('dblclick', onDblClick);
    rootEl.addEventListener('contextmenu', function (e) {
      e.preventDefault();
      // คลิกขวาหัวคอลัมน์ (admin) → เมนูผูกฟิลด์ DB
      var hh = e.target.closest('th.sg-h');
      if (hh && view.mode === 'admin' && window.DBX) { closeCtx(); openColBind(+hh.dataset.hc); return; }
      var scc = e.target.closest('td.sg-statuscell');
      if (scc && view.mode === 'admin' && window.DBX) { closeCtx(); openStatusMenu(+scc.dataset.r, +scc.dataset.c, e.clientX, e.clientY); return; }
      openCtx(e.clientX, e.clientY);
    });
    document.addEventListener('mousedown', function (e) { var t = e.target && e.target.closest ? e.target : null; if (!t) return; if (!t.closest('.sg-ctx')) closeCtx(); if (detailEl && !t.closest('.sg-detail') && !t.closest('td.sg-statuscell')) detailEl.style.display = 'none'; if (statusMenuEl && !t.closest('.sg-statusmenu') && !t.closest('td.sg-statuscell')) statusMenuEl.style.display = 'none'; if (colBindEl && !t.closest('.sg-colbind') && !t.closest('th.sg-h') && !t.closest('.cb-flyout')) { colBindEl.style.display = 'none'; closeCbFlyout(); if (window.PopupStack) PopupStack.remove(colBindEl); } if (!t.closest('.sg-pricepop') && !t.closest('td.pclick')) hidePricePop(); });
    // Esc ที่ไหนก็ได้ (แม้โฟกัสไม่อยู่ที่ตาราง): ยกเลิกคัดลอก/ตัด · ปิดเมนู · ปิดป๊อปอัพต่างๆ
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (editing) return;               // กำลังพิมพ์ — ให้ Esc ยกเลิกการพิมพ์ตามปกติ
      if (clip) clearClip();
      closeCtx(); hidePricePop(); closePicker();
    });
    inputEl.addEventListener('blur', function () { if (editing && !editing.viaFx) commitEdit(); });
    inputEl.addEventListener('input', function () { if (fxEl && editing) fxEl.value = inputEl.value; });

    // fx bar
    if (fxEl) {
      fxEl.addEventListener('focus', function () { if (view.mode !== 'admin') return; if (!editing) editing = { r: anchorOf(sel.r, sel.c).r, c: anchorOf(sel.r, sel.c).c, viaFx: true }; });
      fxEl.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); commitEdit('down'); }
        else if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
      });
      fxEl.addEventListener('blur', function () { if (editing && editing.viaFx) commitEdit(); });
    }
    rootEl.focus();
  }

  // ---------- versions ----------
  function saveAs(name) {
    var id = 'v' + Date.now();
    var meta = { id: id, name: name || ('เวอร์ชัน ' + new Date().toLocaleString('th-TH')), savedAt: Date.now() };
    XL2.store.saveVersionDoc(id, doc);
    var vs = XL2.store.loadVersions(); vs.unshift(meta); XL2.store.saveVersions(vs);
    dirty = false; toast('บันทึกเป็น: ' + meta.name);
    return meta;
  }
  function save() { XL2.store.saveCurrent(doc); dirty = false; toast('บันทึกแล้ว'); }
  function openVersion(id) {
    var d = XL2.store.loadVersion(id); if (!d) return;
    doc = d; doc.adminRows = doc.adminRows || {}; doc.adminCols = doc.adminCols || {};
    undoStack.length = redoStack.length = 0;
    afterChange(); setActive(0, 0); toast('เปิดเวอร์ชันแล้ว');
  }
  function resetFromSource() {
    doc = window.XL2Build.fromPickup01();
    undoStack.length = redoStack.length = 0;
    afterChange(); setActive(0, 0); toast('โหลดต้นฉบับใหม่');
  }

  function setCondColors(o) {
    if (view.mode !== 'admin') return;
    pushUndo();
    doc.condColors = { pos: (o.pos || '008000'), neg: (o.neg || 'C00000') };
    afterChange(); toast('ตั้งสี Margin: บวก #' + doc.condColors.pos + ' · ลบ #' + doc.condColors.neg);
  }

  // ---------- data snapshot สำหรับโมดูลอื่น (เช่นแชทบอท) ----------
  function dataRows() {
    if (!cache) cache = {};
    var out = [];
    for (var r = 0; r < doc.nRows; r++) {
      if (rowKind(r) !== 'data') continue;
      var brand = String(valueOf(r, 2)).trim(), model = String(valueOf(r, 3)).trim();
      if (!brand && !model) continue;
      out.push({
        r: r, size: rowSizeText(r), brand: brand, model: model,
        dot: String(valueOf(r, 4)).trim(),
        cost: valueOf(r, 6), retail: valueOf(r, 7), margin: valueOf(r, 10),
        B: valueOf(r, 13), A: valueOf(r, 16), S: valueOf(r, 19),
        changed: !!(doc.changes && doc.changes[r])
      });
    }
    return out;
  }

  // ราคาที่ “มีผลจริง” เท่านั้น: ถ้าราคาถูกปรับแต่ยังไม่ถึงเวลา (หรือยังไม่เผยแพร่) จะคืนราคาเดิม
  var PRICE_FIELD = { 7: 'retail', 13: 'B', 16: 'A', 19: 'S' };
  function effectiveDataRows() {
    var rows = dataRows();
    rows.forEach(function (rw) {
      var rc = doc.changes && doc.changes[rw.r];
      if (!rc) return;
      Object.keys(PRICE_FIELD).forEach(function (c) {
        var e = rc[c]; if (!e) return;
        var effOk = e.sent && parseEff(e.effectiveAt).getTime() <= Date.now();
        if (!effOk) { rw[PRICE_FIELD[c]] = e.old; rw.pending = true; }
      });
    });
    return rows;
  }

  // โหลดชีตใหม่จาก store (ใช้ตอนสลับหมวด)
  function reloadSheet() {
    var saved = XL2.store.loadCurrent();
    doc = (saved && saved.cells) ? saved : window.XL2Build.fromPickup01();
    doc.adminRows = doc.adminRows || {}; doc.adminCols = doc.adminCols || {};
    doc.merges = doc.merges || {}; doc.colW = doc.colW || []; doc.rowH = doc.rowH || [];
    doc.rowLinks = doc.rowLinks || {}; doc.changes = doc.changes || {};
    doc.hideRows = doc.hideRows || {}; doc.hideCols = doc.hideCols || {}; doc.uHideRows = doc.uHideRows || {}; doc.uHideCols = doc.uHideCols || {};
    for (var mr = 0; mr < doc.nRows; mr++) {
      var mc = doc.cells[mr + ':10'];
      if (mc && mc.f && /^=H\d+-G\d+$/.test(mc.f)) { mc.s = mc.s || {}; if (!mc.s.cond) { mc.s.cond = 'pn'; delete mc.s.fc; } }
    }
    undoStack.length = redoStack.length = 0;
    if (editing) cancelEdit();
    invalidate(); buildCover(); render(); setActive(0, 0);
    persist();
  }

  // ---------- API สำหรับบอท/ปลั๊กอินภายนอก (Telegram bridge) ----------
  function apiSetCell(r, c, val) {
    if (r < 0 || r >= doc.nRows || c < 0 || c >= doc.nCols) throw 'out-of-range';
    pushUndo();
    recordChange(r, c, valueOf(r, c));
    var nc = ensureCell(r, c);
    if (String(val).charAt(0) === '=') { nc.f = String(val); delete nc.v; }
    else { delete nc.f; nc.v = val; }
    invalidate();
    pruneChange(r, c);
    afterChange();
    return valueOf(r, c);
  }

  window.SG = {
    init: init, render: render, undo: undo, redo: redo,
    copy: function () { doCopy(false); }, paste: doPaste, delRange: delRange, clearClip: clearClip,
    insertRow: insertRow, insertRows: insertRows, deleteRow: deleteRow, insertCol: insertCol, insertCols: insertCols, deleteCol: deleteCol, addRowsBottom: addRowsBottom,
    insertCopiedRows: insertCopiedRows, insertCopiedCols: insertCopiedCols, fillDown: fillDown, fillRight: fillRight,
    addModelRow: addModelRow, addSizeGroup: addSizeGroup, delSizeGroup: delSizeGroup,
    toggleMerge: toggleMerge, applyStyle: applyStyle, applyBorders: applyBorders, setBorderOpts: setBorderOpts, setType: setType, linkDB: linkDB, stepFont: stepFont, setFontSize: setFontSize, stepDp: stepDp,
    bindColumn: bindColumn, openColBind: openColBind, applyColMapTemplate: applyColMapTemplate, getColumnMap: function () { return doc.columnMap || {}; }, clearDbCache: clearDbCache,
    linkRowDB: linkRowDB, unlinkRow: unlinkRow, linkCellDB: linkCellDB, unlinkCell: unlinkCell, syncToDB: syncToDB,
    setSchedule: setSchedule, setRowSchedule: setRowSchedule, getSchedule: function () { return doc.schedule || ''; },
    setFilter: setFilter, clearFilter: clearFilter, filterOptions: filterOptions, getMatchCount: function () { return lastMatchCount; }, isTooMany: function () { return tooMany; },
    setCondColors: setCondColors, getCondColors: function () { return doc.condColors || { pos: '008000', neg: 'C00000' }; },
    clearChanges: clearChanges,
    toggleLockRows: toggleLockRows, toggleLockCols: toggleLockCols,
    hideRows: hideRows, unhideRows: unhideRows, hideCols: hideCols, unhideCols: unhideCols, showAllHidden: showAllHidden,
    toggleUserHideRows: toggleUserHideRows, toggleUserHideCols: toggleUserHideCols,
    setMode: setMode, getMode: function () { return view.mode; },
    allSizes: function () { var s = {}, out = []; for (var r = 0; r < doc.nRows; r++) { if (rowKind(r) !== 'data') continue; var t = rowSizeText(r); if (t && t !== 'ขนาดใหม่' && !s[t]) { s[t] = 1; out.push(t); } } return out; },
    setZoom: setZoom, getZoom: function () { return view.zoom; }, toggleSecret: toggleSecret,
    saveAs: saveAs, save: save, openVersion: openVersion, resetFromSource: resetFromSource,
    getDoc: function () { return doc; }, isDirty: function () { return dirty; },
    dataRows: dataRows, effectiveDataRows: effectiveDataRows, reloadSheet: reloadSheet, apiSetCell: apiSetCell, pushUndo: pushUndo,
    sel: sel, range: range, startEdit: startEdit
  };
})();
