/* ============================================================
   ai-image.js — AI ตกแต่งรูป (หลายผู้ให้บริการ + ลำดับความสำคัญ + สำรองอัตโนมัติ)
   ------------------------------------------------------------
   • เรียกใช้: AIImage.editImage(dataURL, task, prompt) → Promise<dataURL>
       task: 'removebg' (ลบพื้นหลัง/พื้นใส) | 'edit' (สั่งด้วย prompt)
   • ลองผู้ให้บริการตามลำดับ (priority) ที่เปิดใช้ · ตัวไหนล้ม → ไปตัวถัดไปอัตโนมัติ
   • ชนิดผู้ให้บริการ:
       - browser : ลบพื้นหลังในเครื่อง (ไลบรารี @imgly) ไม่ต้องตั้งค่า · รองรับ task=removebg
       - web     : เรียก API ภายนอก (ใส่ URL)
       - local   : เรียก AI ในเครื่องของคุณเอง (ใส่ URL) — สำหรับอนาคต
   • สัญญา (contract) ของ web/local endpoint:
       Request : POST JSON { task, prompt, image:"data:image/...;base64,..." }
       Response: JSON { image:"data:image/...;base64,..." }  (ดีที่สุด)
                 หรือ { url:"https://..." }  หรือ ส่งไฟล์รูปดิบ (Content-Type: image/*)
   ============================================================ */
(function () {
  var LS_KEY = 'xls2_ai_providers';
  var IMGLY_URL = 'https://esm.sh/@imgly/background-removal@1.5.5';

  function defaults() {
    return [
      { id: 'browser', name: 'เบราว์เซอร์ — ลบพื้นหลัง (ไม่ต้องตั้งค่า)', kind: 'browser', url: '', enabled: true },
      { id: 'web', name: 'เว็บภายนอก (API)', kind: 'web', url: '', enabled: false },
      { id: 'local', name: 'AI ในเครื่อง (local)', kind: 'local', url: '', enabled: false }
    ];
  }
  function load() {
    try { var a = JSON.parse(localStorage.getItem(LS_KEY)); if (Array.isArray(a) && a.length) return a; } catch (e) {}
    return defaults();
  }
  function save(list) { localStorage.setItem(LS_KEY, JSON.stringify(list)); }
  var providers = load();

  function toast(s) {
    if (window.SG && SG.toast) return SG.toast(s);
    var t = document.getElementById('toast');
    if (t) { t.textContent = s; t.classList.add('show'); clearTimeout(t._tm); t._tm = setTimeout(function () { t.classList.remove('show'); }, 3000); }
  }
  function blobToDataURL(b) { return new Promise(function (res, rej) { var r = new FileReader(); r.onload = function () { res(r.result); }; r.onerror = rej; r.readAsDataURL(b); }); }

  // ---------- ผู้ให้บริการแต่ละชนิด ----------
  var imglyMod = null;
  async function runBrowser(dataURL, task) {
    if (task !== 'removebg') throw new Error('เบราว์เซอร์ทำได้เฉพาะลบพื้นหลัง');
    if (!imglyMod) { toast('🤖 กำลังโหลดโมเดลลบพื้นหลัง (ครั้งแรกใช้เวลาสักครู่)…'); imglyMod = await import(IMGLY_URL); }
    var fn = imglyMod.removeBackground || (imglyMod.default && imglyMod.default.removeBackground);
    if (!fn) throw new Error('โหลดไลบรารีไม่ได้');
    var blob = await (await fetch(dataURL)).blob();
    var out = await fn(blob);
    return await blobToDataURL(out);
  }
  async function runEndpoint(url, dataURL, task, prompt) {
    if (!url) throw new Error('ยังไม่ได้ตั้งค่า URL');
    var ac = new AbortController(); var to = setTimeout(function () { ac.abort(); }, 90000);
    try {
      var r = await fetch(url, {
        method: 'POST', signal: ac.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: task, prompt: prompt || '', image: dataURL })
      });
      clearTimeout(to);
      if (!r.ok) {
        // ดึงข้อความ error จริงจาก body (เช่นเหตุผลจาก MiniMax) มาแสดง
        var detail = '';
        try { var ej = await r.json(); detail = ej && ej.error ? (': ' + ej.error) : ''; }
        catch (e2) { try { var et = await r.text(); if (et) detail = ': ' + et.slice(0, 200); } catch (e3) {} }
        throw new Error('HTTP ' + r.status + detail);
      }
      var ct = (r.headers.get('Content-Type') || '').toLowerCase();
      if (ct.indexOf('application/json') >= 0) {
        var j = await r.json();
        if (j.error) throw new Error(j.error);
        if (j.image) return j.image;
        if (j.url) return await blobToDataURL(await (await fetch(j.url)).blob());
        throw new Error('ไม่พบรูปในผลลัพธ์');
      }
      if (ct.indexOf('image/') >= 0) return await blobToDataURL(await r.blob());
      // เผื่อส่งกลับเป็นข้อความ dataURL ล้วน
      var txt = await r.text();
      if (/^data:image\//.test(txt.trim())) return txt.trim();
      throw new Error('รูปแบบผลลัพธ์ไม่รองรับ');
    } catch (e) { clearTimeout(to); throw e; }
  }
  function runOne(p, dataURL, task, prompt) {
    if (p.kind === 'browser') return runBrowser(dataURL, task);
    return runEndpoint(p.url, dataURL, task, prompt);
  }

  // ---------- ตัวรันหลัก: ลองตามลำดับ + สำรอง ----------
  async function editImage(dataURL, task, prompt) {
    var list = providers.filter(function (p) { return p.enabled; });
    if (!list.length) { openSettings(); throw new Error('ยังไม่ได้เปิดผู้ให้บริการ AI — ตั้งค่าก่อน'); }
    var errs = [];
    for (var i = 0; i < list.length; i++) {
      var p = list[i];
      try {
        toast('🤖 ' + (i ? '(สำรอง) ' : '') + p.name + ' กำลังประมวลผล…');
        var out = await runOne(p, dataURL, task, prompt);
        if (out && /^data:image\//.test(out)) return out;
        errs.push(p.name + ': ผลลัพธ์ว่าง');
      } catch (e) {
        errs.push(p.name + ': ' + (e && e.message || e));
        // ไปลองตัวถัดไปอัตโนมัติ
      }
    }
    throw new Error(errs.join(' · '));
  }

  // ---------- หน้าต่างตั้งค่า (ลำดับ + เปิด/ปิด + URL) ----------
  var dlg = null;
  var statuses = {};   // id → { state:'unknown'|'checking'|'ok'|'err', msg }

  // ตรวจสถานะผู้ให้บริการ (ไม่ใช้เครดิต — เช็กแค่ว่าออนไลน์/เข้าถึงได้)
  async function checkProvider(p) {
    if (p.kind === 'browser') {
      statuses[p.id] = { state: 'ok', msg: 'ทำงานในเบราว์เซอร์ ใช้ได้เสมอ — ลบพื้นหลังอัตโนมัติ (โหลดโมเดลครั้งแรกอาจช้าสักครู่)' };
      return;
    }
    if (!p.url) { statuses[p.id] = { state: 'err', msg: 'ยังไม่ได้ใส่ URL — เปิดใช้ไม่ได้' }; return; }
    statuses[p.id] = { state: 'checking', msg: 'กำลังตรวจสอบ…' };
    var ac = new AbortController(); var to = setTimeout(function () { ac.abort(); }, 8000);
    try {
      // GET endpoint — Worker จะตอบ JSON กลับ (เช่น {"error":"ใช้ POST เท่านั้น"}) = ออนไลน์
      var r = await fetch(p.url, { method: 'GET', signal: ac.signal });
      clearTimeout(to);
      var note = '';
      try { var j = await r.json(); if (j && j.error) note = ' · ' + j.error; } catch (e) {}
      statuses[p.id] = { state: 'ok', msg: 'ออนไลน์ — เซิร์ฟเวอร์ตอบกลับ (HTTP ' + r.status + ')' + note + '\n\nหมายเหตุ: เป็นการเช็กว่าเข้าถึงได้เท่านั้น ยังไม่ได้ตรวจว่า API key/เครดิตถูกต้อง (การตรวจจริงจะใช้เครดิต)' };
    } catch (e) {
      clearTimeout(to);
      var m = (e && e.name === 'AbortError') ? 'หมดเวลา (เซิร์ฟเวอร์ไม่ตอบใน 8 วินาที)'
        : 'เข้าถึงไม่ได้ — ' + (e && e.message || e) + ' (อาจเป็น URL ผิด, เซิร์ฟเวอร์ล่ม, หรือถูกบล็อก CORS)';
      statuses[p.id] = { state: 'err', msg: m };
    }
  }
  function paintDots() {
    if (!dlg) return;
    providers.forEach(function (p) {
      var dot = dlg.querySelector('.ai-stat[data-sid="' + p.id + '"]');
      if (dot) { var st = statuses[p.id] || { state: 'unknown' }; dot.className = 'ai-stat ' + st.state; }
    });
  }
  function checkAll() {
    providers.forEach(function (p) {
      checkProvider(p).then(paintDots);
    });
    paintDots();
  }
  function statLabel(state) {
    return state === 'ok' ? '🟢 ใช้งานได้' : state === 'err' ? '🔴 ใช้งานไม่ได้' : state === 'checking' ? '⏳ กำลังตรวจ' : '⚪ ยังไม่ตรวจ';
  }
  function showStatPopup(p, anchor) {
    var old = document.querySelector('.ai-statpop'); if (old) old.remove();
    var st = statuses[p.id] || { state: 'unknown', msg: 'ยังไม่ได้ตรวจสอบ — กดปุ่ม “ตรวจสถานะ”' };
    var pop = document.createElement('div');
    pop.className = 'ai-statpop';
    pop.innerHTML = '<div class="ai-pop-t">' + statLabel(st.state) + '</div><div class="ai-pop-m">' + (st.msg || '').replace(/</g, '&lt;').replace(/\n/g, '<br>') + '</div><button class="ai-pop-re">↻ ตรวจสถานะใหม่</button>';
    document.body.appendChild(pop);
    var r = anchor.getBoundingClientRect();
    pop.style.left = Math.min(r.left, innerWidth - pop.offsetWidth - 10) + 'px';
    pop.style.top = (r.bottom + 6) + 'px';
    pop.querySelector('.ai-pop-re').onclick = function () { checkProvider(p).then(function () { paintDots(); showStatPopup(p, anchor); }); paintDots(); };
    setTimeout(function () {
      document.addEventListener('mousedown', function h(ev) { if (!ev.target.closest('.ai-statpop') && !ev.target.closest('.ai-stat')) { pop.remove(); document.removeEventListener('mousedown', h); } });
    }, 0);
  }

  function openSettings() {
    if (!dlg) {
      dlg = document.createElement('div');
      dlg.className = 'ai-cfg';
      document.body.appendChild(dlg);
      // Esc = ปิดหน้าต่าง (เมื่อเปิดอยู่)
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && dlg && dlg.style.display !== 'none') {
          var pop = document.querySelector('.ai-statpop');
          if (pop) { pop.remove(); return; }   // มี popup เปิดอยู่ → ปิด popup ก่อน
          close();
        }
      });
    }
    renderCfg();
    dlg.style.display = 'flex';
    checkAll();
  }
  function close() { if (dlg) dlg.style.display = 'none'; }
  function kindBadge(k) {
    if (k === 'browser') return '<span class="ai-badge b1">ในเบราว์เซอร์</span>';
    if (k === 'local') return '<span class="ai-badge b3">ในเครื่อง</span>';
    return '<span class="ai-badge b2">เว็บภายนอก</span>';
  }
  function renderCfg() {
    var rows = providers.map(function (p, i) {
      var urlField = (p.kind === 'browser') ? '<div class="ai-hint">ลบพื้นหลังอัตโนมัติ — ไม่ต้องใส่ลิงก์</div>'
        : '<input class="ai-url" data-i="' + i + '" type="text" placeholder="' + (p.kind === 'local' ? 'http://localhost:xxxx/edit' : 'https://…/edit') + '" value="' + (p.url || '').replace(/"/g, '&quot;') + '" />';
      return '<div class="ai-row' + (p.enabled ? ' on' : '') + '">' +
        '<div class="ai-rowtop">' +
        '<span class="ai-prio">' + (i + 1) + '</span>' +
        '<span class="ai-stat ' + ((statuses[p.id] || {}).state || 'unknown') + '" data-sid="' + p.id + '" title="คลิกดูสถานะ (เขียว=ใช้ได้ แดง=ใช้ไม่ได้)"></span>' +
        '<label class="ai-en"><input type="checkbox" data-en="' + i + '"' + (p.enabled ? ' checked' : '') + ' /> ใช้งาน</label>' +
        '<span class="ai-name">' + (p.name || '') + '</span>' + kindBadge(p.kind) +
        '<span class="ai-move">' +
        '<button class="ai-mv" data-up="' + i + '"' + (i === 0 ? ' disabled' : '') + ' title="เลื่อนขึ้น (สำคัญกว่า)">▲</button>' +
        '<button class="ai-mv" data-dn="' + i + '"' + (i === providers.length - 1 ? ' disabled' : '') + ' title="เลื่อนลง">▼</button>' +
        '</span></div>' + urlField + '</div>';
    }).join('');
    dlg.innerHTML =
      '<div class="ai-head">🤖 ตั้งค่า AI ตกแต่งรูป<span class="ai-x" title="ปิด">✕</span></div>' +
      '<div class="ai-body">' +
      '<div class="ai-note">ลำดับบน = ใช้ก่อน · ถ้าตัวบนใช้ไม่ได้จะข้ามไปตัวถัดไปอัตโนมัติ</div>' +
      rows +
      '<div class="ai-contract"><b>สำหรับ AI local / เว็บภายนอก</b> — endpoint รับ POST JSON: ' +
      '<code>{ task, prompt, image }</code> (image เป็น dataURL) แล้วตอบกลับ <code>{ image: dataURL }</code> หรือไฟล์รูปดิบ</div>' +
      '</div>' +
      '<div class="ai-foot"><button class="btn primary ai-save">บันทึก</button></div>';
    dlg.querySelector('.ai-x').onclick = close;
    dlg.querySelector('.ai-save').onclick = function () { save(providers); toast('✅ บันทึกการตั้งค่า AI แล้ว'); close(); };
    dlg.querySelectorAll('[data-en]').forEach(function (cb) { cb.onchange = function () { var p = providers[+cb.dataset.en]; p.enabled = cb.checked; renderCfg(); if (cb.checked) checkProvider(p).then(paintDots); }; });
    dlg.querySelectorAll('.ai-url').forEach(function (inp) {
      inp.oninput = function () { providers[+inp.dataset.i].url = inp.value.trim(); };
      inp.onchange = function () { var p = providers[+inp.dataset.i]; statuses[p.id] = { state: 'unknown' }; checkProvider(p).then(paintDots); };
    });
    dlg.querySelectorAll('.ai-stat').forEach(function (dot) {
      dot.onclick = function () { var p = providers.filter(function (x) { return x.id === dot.dataset.sid; })[0]; if (p) showStatPopup(p, dot); };
    });
    dlg.querySelectorAll('[data-up]').forEach(function (b) { b.onclick = function () { var i = +b.dataset.up; var t = providers[i - 1]; providers[i - 1] = providers[i]; providers[i] = t; renderCfg(); }; });
    dlg.querySelectorAll('[data-dn]').forEach(function (b) { b.onclick = function () { var i = +b.dataset.dn; var t = providers[i + 1]; providers[i + 1] = providers[i]; providers[i] = t; renderCfg(); }; });
    // ลากย้ายหน้าต่าง
    var head = dlg.querySelector('.ai-head');
    head.onmousedown = function (e) {
      if (e.target.closest('.ai-x')) return;
      var r = dlg.getBoundingClientRect(); dlg.style.left = r.left + 'px'; dlg.style.top = r.top + 'px'; dlg.style.transform = 'none';
      var ox = e.clientX - r.left, oy = e.clientY - r.top;
      function mv(ev) { dlg.style.left = Math.max(0, Math.min(ev.clientX - ox, innerWidth - dlg.offsetWidth)) + 'px'; dlg.style.top = Math.max(0, Math.min(ev.clientY - oy, innerHeight - dlg.offsetHeight)) + 'px'; }
      function up() { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); }
      document.addEventListener('mousemove', mv); document.addEventListener('mouseup', up); e.preventDefault();
    };
  }

  window.AIImage = {
    editImage: editImage,
    openSettings: openSettings,
    hasEnabled: function () { return providers.some(function (p) { return p.enabled; }); }
  };
})();
