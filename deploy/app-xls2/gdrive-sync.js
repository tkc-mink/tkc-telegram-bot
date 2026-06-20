/* ============================================================
   gdrive-sync.js — ซิงค์ข้อมูลราคายางขึ้น Google Drive
   • ใช้ Google Identity Services (GIS) + Drive API v3 (ฝั่งเบราว์เซอร์ ไม่ต้องมี server/secret)
   • scope: drive.file → แอปเห็นเฉพาะไฟล์ที่ตัวเองสร้าง (ปลอดภัย ไม่ยุ่งไฟล์อื่นใน Drive)
   • เก็บข้อมูลทั้งหมด (ทุก key ที่ขึ้นต้นด้วย xls2*) เป็นไฟล์ JSON ไฟล์เดียวใน Drive
   • โหมดเริ่มต้น: อัป/ดึง ด้วยมือ + ปุ่มเชื่อม · ออโต้ซิงค์เปิดได้ (ค่าเริ่มต้นปิดไว้ก่อน กันพลาด)
   exposes window.GDrive
   ============================================================ */
(function () {
  var DEFAULT_CLIENT_ID = '1024761428527-sqtun1ggudnqjgia937c1era5u5sacme.apps.googleusercontent.com';
  var SCOPE = 'https://www.googleapis.com/auth/drive.file';
  var FILE_NAME = 'DPC-TKC-pricelist.json';     // ชื่อไฟล์ข้อมูลใน Drive
  var FOLDER_NAME = 'Dynamic-PriceList';         // โฟลเดอร์เฉพาะใน Drive (สร้างอัตโนมัติ · ลากเข้า AAA-AI365 ได้)
  var LS_PREFIX = 'xls2';                         // เก็บ/กู้ทุก key ที่ขึ้นต้นด้วยนี้
  var K_CLIENT = 'gdrive_client_id', K_FILEID = 'gdrive_file_id', K_FOLDERID = 'gdrive_folder_id', K_LASTSYNC = 'gdrive_last_sync', K_AUTO = 'gdrive_auto';

  var state = {
    gisReady: false, token: null, tokenExp: 0, tokenClient: null,
    connected: false, busy: false, lastMsg: '', email: ''
  };
  var autoTimer = null;

  function clientId() { return localStorage.getItem(K_CLIENT) || DEFAULT_CLIENT_ID; }
  function autoOn() { return localStorage.getItem(K_AUTO) === '1'; }

  // ---------- โหลดสคริปต์ GIS ----------
  function loadGIS(cb) {
    if (window.google && google.accounts && google.accounts.oauth2) { state.gisReady = true; return cb(); }
    var existing = document.getElementById('gis-script');
    if (existing) { existing.addEventListener('load', function () { state.gisReady = true; cb(); }); return; }
    var s = document.createElement('script');
    s.id = 'gis-script'; s.src = 'https://accounts.google.com/gsi/client'; s.async = true; s.defer = true;
    s.onload = function () { state.gisReady = true; cb(); };
    s.onerror = function () { setStatus('โหลด Google ไม่สำเร็จ — เช็คเน็ต/ตัวบล็อกโฆษณา', 'err'); };
    document.head.appendChild(s);
  }

  // ---------- token ----------
  function ensureTokenClient() {
    if (state.tokenClient) return;
    state.tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: clientId(), scope: SCOPE,
      callback: function (resp) {
        if (resp && resp.access_token) {
          state.token = resp.access_token;
          state.tokenExp = Date.now() + (resp.expires_in ? (resp.expires_in - 60) * 1000 : 3000000);
          state.connected = true;
          if (state._resolve) { state._resolve(); state._resolve = null; }
        } else if (state._reject) { state._reject(new Error('ไม่ได้รับสิทธิ์')); state._reject = null; }
        render();
      },
      error_callback: function (err) {
        setStatus('เชื่อมไม่สำเร็จ: ' + (err && err.type ? err.type : 'ผู้ใช้ปิด/ปฏิเสธ'), 'err');
        if (state._reject) { state._reject(err); state._reject = null; }
      }
    });
  }

  function getToken(interactive) {
    return new Promise(function (resolve, reject) {
      if (state.token && Date.now() < state.tokenExp) return resolve();
      loadGIS(function () {
        ensureTokenClient();
        state._resolve = resolve; state._reject = reject;
        try { state.tokenClient.requestAccessToken({ prompt: interactive ? 'consent' : '' }); }
        catch (e) { reject(e); }
      });
    });
  }

  // ---------- Drive REST ----------
  function api(url, opts) {
    opts = opts || {}; opts.headers = opts.headers || {};
    opts.headers.Authorization = 'Bearer ' + state.token;
    return fetch(url, opts).then(function (r) {
      if (r.status === 401) { state.token = null; throw new Error('TOKEN'); }
      return r;
    });
  }

  function findFile() {
    var q = encodeURIComponent("name='" + FILE_NAME + "' and trashed=false");
    return api('https://www.googleapis.com/drive/v3/files?q=' + q + '&spaces=drive&fields=files(id,name,modifiedTime,parents)')
      .then(function (r) { return r.json(); })
      .then(function (d) { return (d.files && d.files[0]) || null; });
  }

  // หา/สร้างโฟลเดอร์เฉพาะของแอป (drive.file — เห็นเฉพาะโฟลเดอร์ที่แอปสร้าง)
  function ensureFolder() {
    var cached = localStorage.getItem(K_FOLDERID);
    if (cached) {
      return api('https://www.googleapis.com/drive/v3/files/' + cached + '?fields=id,trashed')
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d && d.id && !d.trashed) return d.id; localStorage.removeItem(K_FOLDERID); return findOrCreateFolder(); })
        .catch(function () { return findOrCreateFolder(); });
    }
    return findOrCreateFolder();
  }
  function findOrCreateFolder() {
    var q = encodeURIComponent("name='" + FOLDER_NAME + "' and mimeType='application/vnd.google-apps.folder' and trashed=false");
    return api('https://www.googleapis.com/drive/v3/files?q=' + q + '&spaces=drive&fields=files(id,name)')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.files && d.files[0]) { localStorage.setItem(K_FOLDERID, d.files[0].id); return d.files[0].id; }
        return api('https://www.googleapis.com/drive/v3/files?fields=id', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: FOLDER_NAME, mimeType: 'application/vnd.google-apps.folder' })
        }).then(function (r) { return r.json(); }).then(function (f) { localStorage.setItem(K_FOLDERID, f.id); return f.id; });
      });
  }
  // ย้ายไฟล์เข้าโฟลเดอร์ (ถ้ายังไม่อยู่) — ใช้ย้ายไฟล์เก่าที่อยู่ root เข้าโฟลเดอร์
  function moveToFolder(fileId, folderId, curParents) {
    if (!fileId || !folderId) return Promise.resolve();
    if (curParents && curParents.indexOf(folderId) >= 0) return Promise.resolve();
    var remove = (curParents && curParents.length) ? '&removeParents=' + curParents.join(',') : '';
    return api('https://www.googleapis.com/drive/v3/files/' + fileId + '?addParents=' + folderId + remove + '&fields=id,parents',
      { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }

  function gather() {
    var data = {};
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k && k.indexOf(LS_PREFIX) === 0) data[k] = localStorage.getItem(k);
    }
    return { _app: 'DPC-TKC', _type: 'backup', _version: 1, exportedAt: new Date().toISOString(), data: data };
  }
  function applyData(obj) {
    if (!obj || obj._type !== 'backup' || !obj.data) throw new Error('รูปแบบไฟล์ไม่ถูกต้อง');
    var rm = []; for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (k && k.indexOf(LS_PREFIX) === 0) rm.push(k); }
    rm.forEach(function (k) { localStorage.removeItem(k); });
    Object.keys(obj.data).forEach(function (k) { localStorage.setItem(k, obj.data[k]); });
  }

  function uploadContent(fileId, content, folderId) {
    if (fileId) {
      return api('https://www.googleapis.com/upload/drive/v3/files/' + fileId + '?uploadType=media&fields=id,modifiedTime',
        { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: content })
        .then(function (r) { return r.json(); });
    }
    var boundary = '-------dpc' + Date.now();
    var meta = { name: FILE_NAME, mimeType: 'application/json' };
    if (folderId) meta.parents = [folderId];   // สร้างไฟล์ใหม่ไว้ในโฟลเดอร์เฉพาะเลย
    var body = '--' + boundary + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' +
      JSON.stringify(meta) + '\r\n--' + boundary +
      '\r\nContent-Type: application/json\r\n\r\n' + content + '\r\n--' + boundary + '--';
    return api('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,modifiedTime',
      { method: 'POST', headers: { 'Content-Type': 'multipart/related; boundary=' + boundary }, body: body })
      .then(function (r) { return r.json(); });
  }

  // ---------- การทำงานหลัก ----------
  function withRetry(fn) {
    return fn().catch(function (e) {
      if (String(e.message) === 'TOKEN') { return getToken(false).then(fn); }
      throw e;
    });
  }

  function upload(silent) {
    if (state.busy) return Promise.resolve();
    state.busy = true; setStatus('กำลังอัปขึ้น Drive…', 'work');
    try { if (window.SG && SG.save) SG.save(); } catch (e) {}
    var content = JSON.stringify(gather());
    var folderId = null;
    return getToken(false).then(function () {
      return withRetry(function () { return ensureFolder(); });
    }).then(function (fid2) {
      folderId = fid2;
      return withRetry(function () { return findExisting(); });
    }).then(function (existing) {
      var fileId = existing && existing.id;
      // ย้ายไฟล์เก่าที่อยู่ root เข้าโฟลเดอร์ (ครั้งเดียว)
      var mv = (fileId && existing.parents) ? moveToFolder(fileId, folderId, existing.parents) : Promise.resolve();
      return mv.then(function () { return withRetry(function () { return uploadContent(fileId, content, folderId); }); });
    }).then(function (res) {
      if (res && res.id) localStorage.setItem(K_FILEID, res.id);
      localStorage.setItem(K_LASTSYNC, new Date().toISOString());
      state.busy = false; setStatus('อัปขึ้น Drive สำเร็จ ✓ · โฟลเดอร์: ' + FOLDER_NAME, 'ok'); render();
    }).catch(function (e) {
      state.busy = false; setStatus('อัปไม่สำเร็จ: ' + e.message, 'err'); render();
      if (!silent) console.warn('[GDrive upload]', e);
    });
  }
  // หาไฟล์เดิม (คืน id+parents) — จาก cache ก่อน ไม่มีค่อยค้นจากชื่อ
  function findExisting() {
    var fid = localStorage.getItem(K_FILEID);
    if (fid) {
      return api('https://www.googleapis.com/drive/v3/files/' + fid + '?fields=id,parents,trashed')
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d && d.id && !d.trashed) return d; return findFile(); })
        .catch(function () { return findFile(); });
    }
    return findFile();
  }

  function download() {
    if (state.busy) return Promise.resolve();
    var run = function () {
      try {
        var b = new Blob([JSON.stringify(gather(), null, 2)], { type: 'application/json' });
        var a = document.createElement('a'); a.href = URL.createObjectURL(b);
        a.download = 'ราคายาง-ก่อนดึงจาก-drive.json'; document.body.appendChild(a); a.click(); document.body.removeChild(a);
      } catch (e) {}
      state.busy = true; setStatus('กำลังดึงจาก Drive…', 'work');
      _doDownload();
    };
    if (window.AppDialog) { AppDialog.confirm('ดึงจาก Google Drive?', 'ข้อมูลในเครื่องนี้จะถูกเขียนทับด้วยข้อมูลจาก Drive<br>(ระบบสำรองไฟล์ของเครื่องนี้ให้ก่อนอัตโนมัติ)', run); return Promise.resolve(); }
    if (!confirm('ดึงข้อมูลล่าสุดจาก Google Drive มาแทนที่ในเครื่องนี้?')) return Promise.resolve();
    run();
    return Promise.resolve();
  }
  function _doDownload() {
    return getToken(false).then(function () {
      return withRetry(function () { return findFile(); });
    }).then(function (f) {
      if (!f) { state.busy = false; setStatus('ยังไม่มีไฟล์ใน Drive — กด “อัปขึ้น Drive” ครั้งแรกก่อน', 'err'); render(); return; }
      localStorage.setItem(K_FILEID, f.id);
      return withRetry(function () { return api('https://www.googleapis.com/drive/v3/files/' + f.id + '?alt=media'); })
        .then(function (r) { return r.json(); })
        .then(function (obj) {
          applyData(obj);
          localStorage.setItem(K_LASTSYNC, new Date().toISOString());
          state.busy = false; setStatus('ดึงสำเร็จ — กำลังโหลดใหม่…', 'ok');
          setTimeout(function () { location.reload(); }, 600);
        });
    }).catch(function (e) {
      state.busy = false; setStatus('ดึงไม่สำเร็จ: ' + e.message, 'err'); render();
    });
  }

  function connect() {
    setStatus('กำลังเปิดหน้าต่างเข้าสู่ระบบ Google…', 'work');
    getToken(true).then(function () {
      state.connected = true; setStatus('เชื่อม Google สำเร็จ ✓ — กด “อัปขึ้น Drive” เพื่อสำรองครั้งแรก', 'ok'); render();
    }).catch(function (e) { setStatus('ยังไม่ได้เชื่อม: ' + (e.message || 'ยกเลิก'), 'err'); render(); });
  }
  function disconnect() {
    if (state.token && window.google && google.accounts && google.accounts.oauth2) {
      try { google.accounts.oauth2.revoke(state.token, function () {}); } catch (e) {}
    }
    state.token = null; state.tokenExp = 0; state.connected = false;
    setStatus('ตัดการเชื่อมต่อแล้ว', ''); render();
  }

  // ---------- ออโต้ซิงค์ (เปิด/ปิดได้) ----------
  function scheduleAuto() {
    if (!autoOn() || !state.connected) return;
    clearTimeout(autoTimer);
    autoTimer = setTimeout(function () { upload(true); }, 4000);   // หน่วง 4 วิ หลังหยุดแก้
  }
  // ผูกกับการบันทึกของแอป: ทุกครั้งที่ saveCurrent ทำงาน → นัดอัปขึ้น Drive
  function hookStore() {
    if (!window.XL2 || !XL2.store || XL2.store._gdriveHooked) return;
    var orig = XL2.store.saveCurrent;
    XL2.store.saveCurrent = function () { var r = orig.apply(this, arguments); try { scheduleAuto(); } catch (e) {} return r; };
    XL2.store._gdriveHooked = true;
  }

  // ---------- UI ----------
  function setStatus(msg, kind) { state.lastMsg = msg; state.lastKind = kind || ''; render(); }
  function fmtTime(iso) { if (!iso) return '—'; try { return new Date(iso).toLocaleString('th-TH'); } catch (e) { return iso; } }

  function buildPanel() {
    if (document.getElementById('gdModal')) return;
    var m = document.createElement('div');
    m.id = 'gdModal';
    m.innerHTML =
      '<div class="gd-back"></div>' +
      '<div class="gd-dlg">' +
        '<div class="gd-h"><span>☁️ Google Drive — ซิงค์ข้อมูล <small style="opacity:.7;font-size:11px;font-weight:600">v2 · โฟลเดอร์</small></span><button class="gd-x" title="ปิด">✕</button></div>' +
        '<div class="gd-bd">' +
          '<div class="gd-stat" id="gdStat"></div>' +
          '<div class="gd-row"><span class="gd-lab">บัญชี/สถานะ</span><b id="gdConn">ยังไม่ได้เชื่อม</b></div>' +
          '<div class="gd-row"><span class="gd-lab">ซิงค์ล่าสุด</span><b id="gdLast">—</b></div>' +
          '<div class="gd-btns" id="gdBtns"></div>' +
          '<label class="gd-auto"><input type="checkbox" id="gdAuto" /> <span>ออโต้ซิงค์ — อัปขึ้น Drive อัตโนมัติทุกครั้งที่แก้ (หน่วง ~4 วิ)</span></label>' +
          '<details class="gd-adv"><summary>ตั้งค่าขั้นสูง (Client ID)</summary>' +
            '<input id="gdClient" placeholder="xxxx.apps.googleusercontent.com" />' +
            '<div class="gd-hint">ปกติไม่ต้องแก้ — ใส่เองเฉพาะกรณีเปลี่ยนโปรเจกต์ Google</div>' +
          '</details>' +
          '<div class="gd-note">🔒 ใช้สิทธิ์ <b>drive.file</b> — โปรแกรมเห็นเฉพาะไฟล์ที่ตัวเองสร้างใน Drive ของคุณ ไม่ยุ่งไฟล์อื่น<br>📁 เก็บไฟล์ไว้ในโฟลเดอร์ <b>DYNAMIC PRICE LIST (TKC)</b> อัตโนมัติ</div>' +
        '</div>' +
      '</div>';
    document.body.appendChild(m);
    var css = document.createElement('style');
    css.textContent =
      '#gdModal{position:fixed;inset:0;z-index:300;display:none;align-items:center;justify-content:center;font-family:inherit}' +
      '#gdModal.open{display:flex}' +
      '#gdModal .gd-back{position:absolute;inset:0;background:rgba(0,0,0,.4)}' +
      '#gdModal .gd-dlg{position:relative;background:#fff;width:430px;max-width:94vw;border-radius:13px;box-shadow:0 20px 60px rgba(0,0,0,.3);overflow:hidden;animation:gdpop .15s ease}' +
      '@keyframes gdpop{from{transform:translateY(10px);opacity:0}}' +
      '#gdModal .gd-h{background:#F47C20;color:#fff;padding:13px 16px;font-weight:800;font-size:15px;display:flex;justify-content:space-between;align-items:center}' +
      '#gdModal .gd-x{background:transparent;border:none;color:#fff;font-size:16px;cursor:pointer}' +
      '#gdModal .gd-bd{padding:16px 18px}' +
      '#gdModal .gd-stat{font-size:13px;border-radius:8px;padding:9px 12px;margin-bottom:13px;background:#f2f2f2;color:#555;line-height:1.5}' +
      '#gdModal .gd-stat.ok{background:#eefaf1;color:#0a7d3c;border:1px solid #cdeed7}' +
      '#gdModal .gd-stat.err{background:#fdecec;color:#c0392b;border:1px solid #f3c5c5}' +
      '#gdModal .gd-stat.work{background:#FFF6E6;color:#a05c1a;border:1px solid #F3D9A6}' +
      '#gdModal .gd-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #f0f0f0;font-size:13.5px}' +
      '#gdModal .gd-lab{color:#888}' +
      '#gdModal .gd-btns{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 4px}' +
      '#gdModal .gd-b{flex:1;min-width:120px;border:1px solid #c4c4c4;background:#fff;border-radius:8px;padding:10px;font-size:13.5px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:6px}' +
      '#gdModal .gd-b:hover{background:#FFF3E6;border-color:#F47C20}' +
      '#gdModal .gd-b.primary{background:#F47C20;color:#fff;border-color:#F47C20}' +
      '#gdModal .gd-b.primary:hover{background:#E0641A}' +
      '#gdModal .gd-b:disabled{opacity:.5;cursor:not-allowed}' +
      '#gdModal .gd-auto{display:flex;gap:8px;align-items:flex-start;margin:14px 0 6px;font-size:12.5px;color:#444;cursor:pointer;line-height:1.45}' +
      '#gdModal .gd-auto input{margin-top:2px}' +
      '#gdModal .gd-adv{margin:8px 0;font-size:12.5px}' +
      '#gdModal .gd-adv summary{cursor:pointer;color:#888}' +
      '#gdModal .gd-adv input{width:100%;height:32px;border:1px solid #c4c4c4;border-radius:6px;padding:0 8px;font-family:Consolas,monospace;font-size:11.5px;margin-top:7px}' +
      '#gdModal .gd-hint{color:#aaa;font-size:11px;margin-top:4px}' +
      '#gdModal .gd-note{margin-top:12px;font-size:11.5px;color:#777;background:#f7f7f7;border-radius:8px;padding:9px 11px;line-height:1.5}' +
      'body.dark #gdModal .gd-dlg{background:#2a2a2a;color:#eee}' +
      'body.dark #gdModal .gd-bd .gd-row{border-color:#3a3a3a}' +
      'body.dark #gdModal .gd-b{background:#333;border-color:#555;color:#eee}' +
      'body.dark #gdModal .gd-note,body.dark #gdModal .gd-stat{background:#1f1f1f}';
    document.head.appendChild(css);

    m.querySelector('.gd-back').onclick = closePanel;
    m.querySelector('.gd-x').onclick = closePanel;
    var auto = m.querySelector('#gdAuto');
    auto.checked = autoOn();
    auto.onchange = function () { localStorage.setItem(K_AUTO, auto.checked ? '1' : '0'); if (auto.checked) scheduleAuto(); };
    var cl = m.querySelector('#gdClient');
    cl.value = localStorage.getItem(K_CLIENT) || '';
    cl.onchange = function () { var v = cl.value.trim(); if (v) localStorage.setItem(K_CLIENT, v); else localStorage.removeItem(K_CLIENT); state.tokenClient = null; };
  }

  function render() {
    var m = document.getElementById('gdModal'); if (!m) return;
    var st = m.querySelector('#gdStat'); st.className = 'gd-stat ' + (state.lastKind || ''); st.textContent = state.lastMsg || 'พร้อมเชื่อมต่อ Google Drive';
    m.querySelector('#gdConn').textContent = state.connected ? 'เชื่อมแล้ว ✓' : 'ยังไม่ได้เชื่อม';
    m.querySelector('#gdLast').textContent = fmtTime(localStorage.getItem(K_LASTSYNC));
    var btns = m.querySelector('#gdBtns');
    if (!state.connected) {
      btns.innerHTML = '<button class="gd-b primary" id="gdConnect">🔗 เชื่อม Google</button>';
      btns.querySelector('#gdConnect').onclick = connect;
    } else {
      btns.innerHTML =
        '<button class="gd-b primary" id="gdUp"' + (state.busy ? ' disabled' : '') + '>☁️↑ อัปขึ้น Drive</button>' +
        '<button class="gd-b" id="gdDown"' + (state.busy ? ' disabled' : '') + '>☁️↓ ดึงจาก Drive</button>' +
        '<button class="gd-b" id="gdDisc">ออกจากระบบ</button>';
      btns.querySelector('#gdUp').onclick = function () { upload(false); };
      btns.querySelector('#gdDown').onclick = download;
      btns.querySelector('#gdDisc').onclick = disconnect;
    }
  }

  function openPanel() { buildPanel(); hookStore(); document.getElementById('gdModal').classList.add('open'); render(); loadGIS(function () {}); }
  function closePanel() { var m = document.getElementById('gdModal'); if (m) m.classList.remove('open'); }

  // เริ่มต้น: ผูก store เผื่อออโต้ซิงค์ + (ถ้าเคยเชื่อมไว้) ขอ token เงียบๆ
  function init() {
    hookStore();
    if (autoOn()) { loadGIS(function () { getToken(false).then(function () { state.connected = true; }).catch(function () {}); }); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else setTimeout(init, 0);

  window.GDrive = { openPanel: openPanel, upload: upload, download: download, connect: connect };
})();
