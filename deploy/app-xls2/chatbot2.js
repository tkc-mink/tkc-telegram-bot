/* ============================================================
   chatbot2.js — แชทบอทราคายาง 🤖 (มุมขวาล่าง)
   ตอบจากข้อมูลจริงในชีตผ่าน SG.dataRows() · เคารพโหมดแอดมิน/ผู้ใช้
   ============================================================ */
(function () {
  var XL2 = window.XL2;
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function fmt(v) { return XL2.isNumeric(v) ? XL2.fmtNum(XL2.toN(v)) : String(v || '-'); }
  function isAdmin() { return window.SG && SG.getMode() === 'admin'; }
  // แหล่งข้อมูล: ผู้ใช้/AI เห็นเฉพาะราคาที่มีผลแล้ว · แอดมินเห็นร่างล่าสุด
  function srcRows() { return isAdmin() ? SG.dataRows() : SG.effectiveDataRows(); }

  // ---------- AI plugin config (เชื่อม AI local เช่น Ollama / LM Studio) ----------
  var AICFG_KEY = 'xls2_ai_config';
  var AI_DEFAULTS = { enabled: false, endpoint: 'http://192.168.10.38:8080/v1/chat/completions', model: 'Qwen3.6-35B-A3B-NVFP4.gguf', apiKey: '' };
  function loadCfg() {
    var c;
    try { c = Object.assign({}, AI_DEFAULTS, JSON.parse(localStorage.getItem(AICFG_KEY) || '{}')); }
    catch (e) { c = Object.assign({}, AI_DEFAULTS); }
    // ค่าว่าง → ใช้ค่าเริ่มต้น vision (ให้พร้อมใช้งานเลย ผู้ใช้แค่ติ๊กเปิด + ทดสอบ)
    if (!c.endpoint) c.endpoint = AI_DEFAULTS.endpoint;
    if (!c.model) c.model = AI_DEFAULTS.model;
    return c;
  }
  function saveCfg(c) { localStorage.setItem(AICFG_KEY, JSON.stringify(c)); }

  // บริบทราคาสำหรับ AI — ใช้ “ราคาที่มีผลแล้วเท่านั้น” เสมอ (ไม่ส่งราคาล่วงหน้า/ร่าง ไม่ส่งทุน/รหัสลับ)
  function aiContext() {
    var rows = SG.effectiveDataRows();
    var lines = rows.map(function (r) {
      var l = r.size + ' | ' + r.brand + ' ' + r.model + ' | ราคาตั้ง ' + fmt(r.retail);
      if (isAdmin()) l += ' | B ' + fmt(r.B) + ' | A ' + fmt(r.A) + ' | S ' + fmt(r.S);
      return l;
    });
    return 'รายการราคายาง (เฉพาะราคาที่มีผลแล้ว ณ ตอนนี้):\n' + lines.join('\n');
  }
  function aiAsk(q, imgDataUrl) {
    var cfg = loadCfg();
    var headers = { 'Content-Type': 'application/json' };
    if (cfg.apiKey) headers['Authorization'] = 'Bearer ' + cfg.apiKey;
    var userContent = imgDataUrl
      ? [{ type: 'text', text: q || 'อ่านรูปนี้แล้วตอบเกี่ยวกับราคายาง' }, { type: 'image_url', image_url: { url: imgDataUrl } }]
      : q;
    var body = {
      model: cfg.model || 'local',
      stream: false,
      messages: [
        { role: 'system', content: 'คุณคือผู้ช่วยราคายางของร้าน TKC ตอบสั้น กระชับ เป็นภาษาไทย อ้างอิงเฉพาะราคาในข้อมูลนี้เท่านั้น ห้ามเดาราคาเอง\n\n' + aiContext() },
        { role: 'user', content: userContent }
      ]
    };
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, 20000);
    return fetch(cfg.endpoint, { method: 'POST', headers: headers, body: JSON.stringify(body), signal: ctrl.signal })
      .then(function (res) { if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); })
      .then(function (data) {
        clearTimeout(t);
        var txt = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) ||
                  (data.message && data.message.content) || data.response || '';
        if (!txt) throw new Error('empty');
        return txt;
      });
  }

  // ---------- AI vision = "ตา" อ่านรูปอย่างเดียว — สกัดข้อความจากรูป (ไม่ส่งราคา/ไม่วิเคราะห์) ----------
  // ย่อรูปก่อนส่ง (≤ maxPx) → vision อ่านเร็วขึ้นมาก · payload เล็กลง · ลดโอกาส timeout
  function downscaleImage(dataUrl, maxPx) {
    return new Promise(function (res) {
      try {
        var im = new Image();
        im.onload = function () {
          var w = im.naturalWidth, h = im.naturalHeight;
          if (!w || !h || (w <= maxPx && h <= maxPx)) { res(dataUrl); return; }
          var sc = maxPx / Math.max(w, h);
          var c = document.createElement('canvas'); c.width = Math.round(w * sc); c.height = Math.round(h * sc);
          c.getContext('2d').drawImage(im, 0, 0, c.width, c.height);
          try { res(c.toDataURL('image/jpeg', 0.85)); } catch (e) { res(dataUrl); }
        };
        im.onerror = function () { res(dataUrl); };
        im.src = dataUrl;
      } catch (e) { res(dataUrl); }
    });
  }
  // คืนข้อความสั้นๆ ที่อ่านได้จากรูป (ขนาด/ยี่ห้อ/รุ่น) → เอาไปป้อนให้สมองกฎในโปรแกรมวิเคราะห์ต่อ
  function aiReadImage(dataUrl, hint) {
    var cfg = loadCfg();
    var headers = { 'Content-Type': 'application/json' };
    if (cfg.apiKey) headers['Authorization'] = 'Bearer ' + cfg.apiKey;
    var prompt = 'ดูรูปสินค้านี้ แล้วอ่านข้อความ/ตัวเลขที่เห็นบนสินค้าออกมาสั้นๆ: ยี่ห้อ · รุ่น · ขนาด/สเปก. ' +
      'ตัวอย่างตามชนิด — ยาง: ขนาด (195R14C, 18.4-30, 31x10.5R15) · น้ำมันเครื่อง: เบอร์ SAE (เช่น 20W-50) และปริมาตร · แบต: Ah/CCA/แรงดัน · อื่นๆ ตามที่อ่านได้. ' +
      'ถ้าในรูปมีสินค้าหลายอย่าง ให้แยกเป็นบรรทัดละ 1 สินค้า ขึ้นต้นด้วย "- " · ถ้ามีอย่างเดียวตอบบรรทัดเดียว. ' +
      'ตอบเฉพาะข้อมูลที่อ่านได้จริงจากรูป ห้ามเดา ห้ามพูดเรื่องราคา.' +
      (hint ? ' (ผู้ใช้ระบุเพิ่ม: ' + hint + ')' : '');
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, 180000);   // โมเดลใหญ่ (35B) อ่านรูปอาจช้า — ให้เวลา 3 นาที
    return downscaleImage(dataUrl, 1280).then(function (img) {
      var body = { model: cfg.model || 'local', stream: false, messages: [
        { role: 'user', content: [ { type: 'text', text: prompt }, { type: 'image_url', image_url: { url: img } } ] }
      ] };
      return fetch(cfg.endpoint, { method: 'POST', headers: headers, body: JSON.stringify(body), signal: ctrl.signal });
    })
      .then(function (res) { if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); })
      .then(function (data) {
        clearTimeout(t);
        var txt = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) ||
                  (data.message && data.message.content) || data.response || '';
        if (!txt) throw new Error('empty');
        return String(txt).trim();
      });
  }

  // ทดสอบการเชื่อมต่อ vision แบบเบาๆ (ส่งข้อความสั้น ไม่ส่งราคา/บริบทใดๆ)
  // ตรวจ mixed-content: หน้า https เรียก vision http:// ไม่ได้ (เบราว์เซอร์บล็อก)
  function mixedBlocked() {
    try {
      var ep = loadCfg().endpoint || '';
      if (location.protocol === 'https:' && /^http:\/\//i.test(ep)) {
        return '⚠️ หน้านี้เปิดผ่าน <b>https</b> แต่ vision เป็น <b>http://…</b> — เบราว์เซอร์บล็อก (mixed-content) จึงขึ้น “Failed to fetch”<br><b>วิธีแก้:</b> เปิดหน้าราคา (ตัวที่ deploy/รันในเครือข่าย) ผ่าน <b>http</b> ในวง LAN เดียวกับ vision · หรือทำ vision ให้เป็น https';
      }
    } catch (e) {}
    return null;
  }
  function aiPing() {
    var cfg = loadCfg();
    var headers = { 'Content-Type': 'application/json' };
    if (cfg.apiKey) headers['Authorization'] = 'Bearer ' + cfg.apiKey;
    var body = { model: cfg.model || 'local', stream: false, messages: [{ role: 'user', content: 'ตอบสั้นๆ ว่า พร้อม' }] };
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, 15000);
    return fetch(cfg.endpoint, { method: 'POST', headers: headers, body: JSON.stringify(body), signal: ctrl.signal })
      .then(function (res) { if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); })
      .then(function (data) {
        clearTimeout(t);
        return ((data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) || (data.message && data.message.content) || data.response || 'OK');
      });
  }

  // ---------- bot brain ----------
  function rowsMatch(q) {
    var rows = srcRows();
    var ql = q.toLowerCase();
    // ----- จับ "ขนาดยาง" หลายรูปแบบ (ให้ค้นเจอครบ) -----
    //   • เรเดียล/เมตริก : 195r14 · 205/75r14c · 420/85r30
    //   • โฟลเทชัน       : 31x10.5r15
    //   • บายอัส/ยางไร่  : 15-30 · 18.4-30 · 12.4-24  (ใช้ขีด ไม่มี R)
    var szRaw =
      (/(\d{2,3}(?:\/\d{2,3})?\s*r\s*\d{2}[a-z]?)/i.exec(ql) || [])[1] ||
      (/(\d{2}\s*x\s*\d{1,2}(?:\.\d)?\s*r?\s*\d{2})/i.exec(ql) || [])[1] ||
      (/(\d{1,3}(?:\.\d)?\s*-\s*\d{2})/.exec(ql) || [])[1] || null;
    var szWant = szRaw ? szRaw.toLowerCase().replace(/\s/g, '') : null;
    var szLoose = szWant ? szWant.replace(/[\-x\/]/g, '') : null;
    // ขอบ เช่น ขอบ 14 — รับทั้งเรเดียล (r14) และยางไร่/บายอัส (-30)
    var rimm = /ขอบ\s*(\d{2})/.exec(ql);
    var out = rows.filter(function (rw) {
      var hit = true;
      if (szWant) {
        var s = String(rw.size || '').toLowerCase().replace(/\s/g, '');
        var sLoose = s.replace(/[\-x\/]/g, '');
        hit = s.indexOf(szWant) >= 0 || sLoose.indexOf(szLoose) >= 0;
        // ค้น "ชื่อเรียกอื่น" (alias) ของขนาดด้วย — เช่น พิมพ์ 14-30 → เจอ 420/85R30
        if (!hit && window.ProductInfo) {
          try {
            var al = (ProductInfo.get(rw.size) || {}).aliases || [];
            for (var ai = 0; ai < al.length; ai++) {
              var a = String(al[ai]).toLowerCase().replace(/\s/g, '');
              if (a.indexOf(szWant) >= 0 || a.replace(/[\-x\/]/g, '').indexOf(szLoose) >= 0) { hit = true; break; }
            }
          } catch (e) {}
        }
      }
      if (hit && rimm && !szWant) hit = new RegExp('[r\\-]' + rimm[1] + '(?!\\d)', 'i').test(String(rw.size || ''));
      return hit;
    });
    // ยี่ห้อ / รุ่น ที่พิมพ์มา (ผ่อนปรน: ถ้าระบุขนาดแล้วยี่ห้อ/รุ่นไม่ตรงเป๊ะ → แสดงขนาดเดียวกันแทนที่จะบอกไม่เจอ)
    var brands = {}; rows.forEach(function (r) { if (r.brand) brands[r.brand.toLowerCase()] = 1; });
    var tokens = ql.split(/[\s,]+/).filter(Boolean);
    var relaxed = false;
    var bTok = tokens.find(function (t) { return brands[t]; });
    if (!bTok && /otani/i.test(ql)) bTok = 'ot';
    if (bTok) {
      var ob = out.filter(function (r) { return r.brand.toLowerCase() === bTok || XL2.brandFull(r.brand).toLowerCase() === bTok; });
      if (ob.length || !(szWant || rimm)) out = ob; else relaxed = true;   // มีขนาด แต่ยี่ห้อไม่ตรง → คงผลตามขนาด
    }
    var mTok = tokens.find(function (t) { return t.length >= 2 && rows.some(function (r) { return r.model.toLowerCase() === t || r.model.toLowerCase().replace(/[\s\-\/]/g, '') === t.replace(/[\s\-\/]/g, ''); }); });
    if (mTok) {
      var om = out.filter(function (r) { return r.model.toLowerCase() === mTok || r.model.toLowerCase().replace(/[\s\-\/]/g, '') === mTok.replace(/[\s\-\/]/g, ''); });
      if (om.length || !(szWant || rimm)) out = om; else relaxed = true;   // มีขนาด แต่รุ่นไม่ตรง → คงผลตามขนาด
    }

    // ----- ความสูง / หน้ากว้าง (นิ้ว/ซม) → กรองจากมิติจริงใน ProductInfo -----
    function parseDim(re) {
      var mm = re.exec(ql); if (!mm) return null;
      var v = parseFloat(mm[1]); if (!(v > 0)) return null;
      var u = (mm[2] || '').toLowerCase();
      return (u === 'ซม' || u === 'cm') ? v : v * 2.54;   // ดีฟอลต์เป็นนิ้ว
    }
    var hWant = parseDim(/(?:ความสูง|สูง|เส้นผ่าน|เส้นผ่าศูนย์กลาง)\s*(\d{2,3}(?:\.\d)?)\s*(นิ้ว|"|''|ซม|cm)?/);
    var wWant = parseDim(/(?:หน้ากว้าง|หน้ายาง|กว้าง)\s*(\d{1,3}(?:\.\d)?)\s*(นิ้ว|"|''|ซม|cm)?/);
    if (hWant || wWant) {
      var tol = 2.6;   // ±~1 นิ้ว
      out = out.filter(function (r) {
        var d = null; try { d = (ProductInfo.get(r.size) || {}).dims; } catch (e) {}
        if (!d) return false;
        if (hWant && !(d.hCm && Math.abs(d.hCm - hWant) <= tol)) return false;
        if (wWant && !(d.wCm && Math.abs(d.wCm - wWant) <= tol)) return false;
        return true;
      });
    }
    // ----- งบ/ราคา: ไม่เกิน · ตั้งแต่ -----
    function pnum(s) { return parseFloat(String(s).replace(/[, ]/g, '')); }
    var maxRaw = (/(?:ไม่เกิน|ต่ำกว่า|ถูกกว่า|ในงบ|งบ|ภายใน|under)\s*([\d,]{2,})/.exec(ql) || [])[1];
    var minRaw = (!/ไม่เกิน/.test(ql)) ? (/(?:ตั้งแต่|เกิน|มากกว่า|สูงกว่า|over)\s*([\d,]{2,})/.exec(ql) || [])[1] : null;
    var maxP = maxRaw ? pnum(maxRaw) : null, minP = minRaw ? pnum(minRaw) : null;
    if (maxP || minP) {
      out = out.filter(function (r) {
        if (!XL2.isNumeric(r.retail)) return false;
        var p = XL2.toN(r.retail);
        if (maxP && p > maxP) return false;
        if (minP && p < minP) return false;
        return true;
      });
    }
    // ----- หมวดสินค้า (ยางใน/รองขอบ/กระทะ/คิ้ว/แบต/น้ำมัน/อะไหล่) → กรองตามชนิดใน ProductInfo -----
    var catId = catFromQuery(ql);
    if (catId) out = out.filter(function (r) { return prodType(r.size) === catId; });

    // ----- ค้นคำทั่วไป (ชื่อรุ่น/สเปก/หมวด) — สำหรับสินค้าที่ไม่ได้ระบุด้วยขนาดยาง -----
    var kwHit = false;
    if (!szWant && !rimm && !catId && !hWant && !wWant) {
      var STOP = /^(ราคา|มี|ของ|อะไร|บ้าง|เท่าไหร่|เท่าไร|กี่|ขอ|ดู|ค้นหา|ค้น|หา|คือ|ช่วย|หน่อย|ครับ|ค่ะ|ราย|การ|ทั้งหมด|และ|กับ|ที่|ตัว|อัน|ยัง|ไหม)$/;
      var kws = tokens.filter(function (t) { return t.length >= 2 && !STOP.test(t) && !brands[t]; });
      if (kws.length) {
        var matched = out.filter(function (r) {
          var hay = (String(r.size || '') + ' ' + String(r.brand || '') + ' ' + String(r.model || '') + ' ' + (XL2.brandFull(r.brand) || '') + ' ' + prodHay(r.size)).toLowerCase();
          return kws.every(function (k) { return hay.indexOf(k) >= 0; });
        });
        if (matched.length) { out = matched; kwHit = true; }
      }
    }
    return { list: out, hasFilter: !!(szWant || rimm || bTok || mTok || hWant || wWant || maxP || minP || catId || kwHit), cat: catId, relaxed: relaxed };
  }

  function rowLine(rw) {
    // กระชับ: ขนาด · ยี่ห้อรุ่น — ราคาตั้ง · (แอดมิน) ทุน/กำไร แบบสั้น
    var l = '<b>' + prodIcon(rw.size) + esc(rw.size) + '</b> ' + esc(rw.brand) + (rw.model ? ' ' + esc(rw.model) : '') +
      ' — <b>' + fmt(rw.retail) + '</b>';
    if (isAdmin()) {
      var extra = [];
      if (XL2.isNumeric(rw.cost)) extra.push('ทุน ' + fmt(rw.cost));
      if (XL2.isNumeric(rw.margin)) extra.push((XL2.toN(rw.margin) > 0 ? '+' : '') + fmt(rw.margin));
      if (extra.length) l += ' <span style="color:#9a8;font-size:.92em">(' + extra.join(' · ') + ')</span>';
    }
    if (rw.changed) l += ' ✏️';
    return l;
  }

  // ร่องราคาขายส่งเป็น "โค้ดลับ" (ชุด Dealer C2) — เหมือนที่แสดงในชีต
  function codeC2(v) { return XL2.isNumeric(v) ? (XL2.encode(XL2.toN(v), XL2.C2) || '-') : '-'; }
  // มิติจริงของขนาด (จาก ProductInfo) · แปลง ซม.→นิ้ว
  function dimsOf(sz) { try { return (ProductInfo.get(sz) || {}).dims || null; } catch (e) { return null; } }
  function inch(cm) { return (cm / 2.54).toFixed(1); }

  // ⚖️ เทียบ "สินค้าต่อสินค้า" แบบละเอียด — รองรับทุกชนิดสินค้า (ยาง/ยางใน/น้ำมัน/แบต/กระทะ/ฯลฯ)
  // จับชื่อ/ขนาด ≥2 ตัวในคำถาม + กรองราคา + แสดงราคา/สเปกตามชนิดสินค้า
  // สเปกของสินค้า (ตามชนิด) → ยาง: หน้ากว้าง+ดอก(รุ่น) · อื่นๆ: ฟิลด์จาก ProductInfo (SAE/Ah/ขอบ ฯลฯ)+รุ่น
  function specParts(sz, r, info) {
    var parts = [];
    var d = (info && info.dims) || null;
    var isTire = info && info.type === 'tire';
    if (isTire) {
      if (d && d.wCm) parts.push('กว้าง ' + inch(d.wCm) + '"');
      if (r.model) parts.push('ดอก ' + esc(r.model));
    } else {
      var defs = (info && info.typeDef && info.typeDef.fields) || [];
      var vals = (info && info.fields) || {};
      defs.forEach(function (f) {
        var v = vals[f.k];
        if (v != null && String(v).trim() !== '' && parts.length < 4) parts.push(esc(String(v)));
      });
      if (r.model) parts.push('รุ่น ' + esc(r.model));
    }
    return parts;
  }
  function compareSizes(ql) {
    var nq = ql.replace(/\s+/g, '');
    var sizes = [];
    (function () {
      var seen = {};
      srcRows().forEach(function (r) {
        if (!r.size || seen[r.size]) return;
        var pos = nq.indexOf(r.size.toLowerCase().replace(/\s+/g, ''));
        if (pos >= 0) { seen[r.size] = 1; sizes.push({ size: r.size, pos: pos }); }
      });
    })();
    sizes.sort(function (a, b) { return a.pos - b.pos; });
    if (sizes.length < 2) return null;   // ต้องมีอย่างน้อย 2 สินค้า ถึงจะเทียบแบบนี้
    sizes = sizes.slice(0, 3);

    // กรองราคา: "2000 บาทขึ้นไป" / "ตั้งแต่ 2000" / "ไม่เกิน 3000"
    function pnum(s) { return parseFloat(String(s).replace(/[, ]/g, '')); }
    var maxRaw = (/(?:ไม่เกิน|ต่ำกว่า|under)\s*([\d,]{2,})/.exec(ql) || [])[1];
    var minRaw = (/([\d,]{3,})\s*บาท?\s*ขึ้นไป/.exec(ql) || [])[1] ||
                 (/(?:ตั้งแต่|เกิน|มากกว่า|over)\s*([\d,]{2,})/.exec(ql) || [])[1];
    var maxP = maxRaw ? pnum(maxRaw) : null, minP = minRaw ? pnum(minRaw) : null;

    var all = [], anyTire = false, blocks = sizes.map(function (sz) {
      var info = prodInfo(sz.size);
      var d = (info && info.dims) || null;
      var isTire = info && info.type === 'tire'; if (isTire) anyTire = true;
      var rows = srcRows().filter(function (r) {
        if ((r.size || '').toLowerCase() !== sz.size.toLowerCase()) return false;
        if (!XL2.isNumeric(r.retail)) return false;
        var p = XL2.toN(r.retail);
        if (maxP && p > maxP) return false;
        if (minP && p < minP) return false;
        return true;
      });
      rows.sort(function (a, b) { return XL2.toN(a.retail) - XL2.toN(b.retail); });
      rows.forEach(function (r) { all.push({ r: r, w: d && d.wCm }); });
      var typeTag = (info && !isTire && info.typeDef) ? ' <span style="color:#9a8;font-size:.8em">' + info.typeDef.label + '</span>' : '';
      var dimTag = (isTire && d) ? ' <span style="color:#9a8;font-size:.85em">' + (d.hCm ? 'สูง~' + inch(d.hCm) + '"' : '') + (d.wCm ? ' · กว้าง~' + inch(d.wCm) + '"' : '') + '</span>' : '';
      var head = '<b>' + prodIcon(sz.size) + esc(sz.size) + '</b>' + typeTag + dimTag;
      if (!rows.length) return head + '<br>&nbsp;&nbsp;<span style="color:#c0392b">— ไม่มีรายการที่เข้าเงื่อนไข</span>';
      var li = rows.slice(0, 6).map(function (r) {
        var sp = ['<b>' + fmt(r.retail) + '</b>'].concat(specParts(sz.size, r, info));
        return '&nbsp;&nbsp;• ' + esc(r.brand) + ' <span style="color:#9a8;font-size:.9em">(' + sp.join(' · ') + ')</span>';
      }).join('<br>');
      return head + '<br>' + li + (rows.length > 6 ? '<br>&nbsp;&nbsp;<span style="color:#9a8;font-size:.85em">…อีก ' + (rows.length - 6) + ' ยี่ห้อ</span>' : '');
    });

    var foot = '';
    if (all.length >= 2) {
      var cheap = all.slice().sort(function (a, b) { return XL2.toN(a.r.retail) - XL2.toN(b.r.retail); })[0];
      foot += '<br><span style="color:#1d8a4f">💡 ถูกสุด: ' + esc(cheap.r.brand + ' ' + (cheap.r.model || '')) + ' ' + esc(cheap.r.size) + ' = ' + fmt(cheap.r.retail) + ' บาท</span>';
      if (anyTire) {
        var withW = all.filter(function (x) { return x.w; });
        if (withW.length >= 2) {
          var wide = withW.slice().sort(function (a, b) { return b.w - a.w; })[0];
          if (wide.w !== withW.slice().sort(function (a, b) { return a.w - b.w; })[0].w)
            foot += '<br><span style="color:#1d6f9e">📐 หน้ากว้างสุด: ' + esc(wide.r.size) + ' (~' + inch(wide.w) + '")</span>';
        }
      }
    }
    var cond = [];
    if (minP) cond.push('ราคา ≥ ' + fmt(minP));
    if (maxP) cond.push('ราคา ≤ ' + fmt(maxP));
    return '⚖️ เทียบ' + (cond.length ? ' <span style="color:#9a8;font-size:.85em">(' + cond.join(' · ') + ')</span>' : '') + ':<br>' + blocks.join('<br><br>') + foot;
  }

  // ---------- สินค้าหลายหมวด (ยางใน/รองขอบ/กระทะ/คิ้ว/แบต/น้ำมัน/อะไหล่ ฯลฯ) ----------
  function prodInfo(sz) { try { return (window.ProductInfo && ProductInfo.get(sz)) || null; } catch (e) { return null; } }
  function prodType(sz) { var p = prodInfo(sz); return p ? p.type : 'tire'; }
  function prodIcon(sz) { var p = prodInfo(sz); return (p && p.type !== 'tire' && p.typeDef) ? (p.typeDef.icon + ' ') : ''; }
  // ข้อความค้นเสริมต่อสินค้า: ป้ายชนิด + ค่าฟิลด์ (SAE/วาล์ว/ขอบ ฯลฯ) + ชื่อเรียกอื่น
  function prodHay(sz) {
    var p = prodInfo(sz); if (!p) return '';
    var f = p.fields ? Object.keys(p.fields).map(function (k) { return p.fields[k]; }).join(' ') : '';
    return (((p.typeDef && p.typeDef.label) || '') + ' ' + f + ' ' + ((p.aliases || []).join(' ')));
  }
  // หมวดสินค้า: คำพูด → type id (ตรงกับ ProductInfo.TYPES)
  var TYPE_KW = [
    { id: 'tube', re: /ยางใน|inner ?tube|\btube\b/i },
    { id: 'flap', re: /รองขอบ|ยางรอง|\bflap\b/i },
    { id: 'wheel', re: /กระทะ|ล้อแม็?ก|แม็?กซ?|\bwheel\b|\brim\b/i },
    { id: 'trim', re: /คิ้ว|\btrim\b/i },
    { id: 'battery', re: /แบตเ?ตอรี่|แบต\b|\bbattery\b/i },
    { id: 'oil', re: /น้ำมัน|หล่อลื่น|จาระบี|เกียร์|\boil\b|\bsae\b|\d{1,2}w-?\d{2}/i },
    { id: 'other', re: /อะไหล่|อุปกรณ์|ของแต่ง|\bspare\b|\bpart\b/i }
  ];
  function catFromQuery(ql) { for (var i = 0; i < TYPE_KW.length; i++) { if (TYPE_KW[i].re.test(ql)) return TYPE_KW[i].id; } return null; }
  function catLabel(id) { try { var t = ProductInfo.getTypes()[id]; return t ? (t.icon + ' ' + t.label) : id; } catch (e) { return id; } }

  // จัดผลลัพธ์แบบกระชับ: ขนาดเป็นหัวครั้งเดียว → ใต้ลงมาแต่ละยี่ห้อ (ราคาขาย + ร่อง B/A/S เป็นโค้ด)
  function groupedBySize(list) {
    var order = [], grp = {};
    list.forEach(function (rw) {
      var k = rw.size || '-';
      if (!grp[k]) { grp[k] = []; order.push(k); }
      grp[k].push(rw);
    });
    return order.map(function (k) {
      var lines = grp[k].map(function (rw) {
        var name = esc(rw.brand) + (rw.model ? ' ' + esc(rw.model) : '');
        var s = '&nbsp;&nbsp;• ' + name + ' - <b>' + fmt(rw.retail) + '</b>';
        if (isAdmin()) {
          s += ' <span style="color:#bbb">/</span> <span style="color:#F47C20;font-weight:700">' + codeC2(rw.B) + '</span>' +
               ' <span style="color:#bbb">/</span> <span style="color:#1d8a4f;font-weight:700">' + codeC2(rw.A) + '</span>' +
               ' <span style="color:#bbb">/</span> <span style="color:#e84393;font-weight:700">' + codeC2(rw.S) + '</span>';
        }
        if (rw.changed) s += ' ✏️';
        return s;
      });
      return '<b>' + prodIcon(k) + esc(k) + '</b><br>' + lines.join('<br>');
    }).join('<br>');
  }

  function answer(q) {
    var ql = q.toLowerCase().trim();
    if (!ql) return 'พิมพ์ถามได้เลยครับ เช่น “ราคา MK1000” หรือ “ยางถูกสุดขอบ 14”';

    // ถอดรหัสลับ (เฉพาะแอดมิน)
    var dm = /(?:ถอดรหัส|รหัส)\s*([a-zA-Z]{2,})/.exec(q);
    if (dm) {
      if (!isAdmin()) return 'ขออภัยครับ การถอดรหัสลับใช้ได้เฉพาะโหมดแอดมิน 🔒';
      var code = dm[1].toUpperCase();
      return 'รหัส <b>' + esc(code) + '</b>:<br>· ชุดทุน (COGS) → <b>' + (XL2.decode(code, XL2.C1) || '?') + '</b><br>· ชุดขายส่ง (Dealer) → <b>' + (XL2.decode(code, XL2.C2) || '?') + '</b>';
    }

    // ⚖️ เทียบ 2–3 รุ่น/ขนาด — "เทียบ X กับ Y" · "X vs Y"
    if (/เทียบ|เปรียบเทียบ|\bvs\b/i.test(ql)) {
      // (ก) เทียบ "ขนาดต่อขนาด" แบบละเอียด — กรองราคา + แสดงราคา/หน้ากว้าง/รุ่น(ดอก) ของทุกยี่ห้อในขนาด
      var detail = compareSizes(ql);
      if (detail) return detail;
      // (ข) เทียบรุ่น/ตัวเดียวต่อตัว (เดิม)
      var parts = q.replace(/เทียบราคา|เทียบ|เปรียบเทียบ/gi, ' ')
        .split(/\s+กับ\s+|\s+vs\s+|\s*\/\s*|\s+versus\s+/i)
        .map(function (s) { return s.trim(); }).filter(Boolean);
      if (parts.length >= 2) {
        var picks = parts.slice(0, 3).map(function (p) { return { q: p, rw: (rowsMatch(p).list[0] || null) }; });
        if (picks.some(function (x) { return x.rw; })) {
          var lines = picks.map(function (x) { return x.rw ? '▫️ ' + rowLine(x.rw) : '▫️ <span style="color:#c0392b">ไม่พบ “' + esc(x.q) + '”</span>'; });
          var foot = '';
          var valid = picks.filter(function (x) { return x.rw && XL2.isNumeric(x.rw.retail); });
          if (valid.length >= 2) {
            valid.sort(function (a, b) { return XL2.toN(a.rw.retail) - XL2.toN(b.rw.retail); });
            var lo = valid[0].rw, hi = valid[valid.length - 1].rw, d = XL2.toN(hi.retail) - XL2.toN(lo.retail);
            if (d > 0) foot = '<br><span style="color:#1d8a4f">💡 ' + esc(lo.brand + ' ' + (lo.model || lo.size)) + ' ถูกกว่า ' + fmt(d) + ' บาท</span>';
            else foot = '<br><span style="color:#9a8">ราคาขายเท่ากัน</span>';
          }
          return '⚖️ เทียบ:<br>' + lines.join('<br>') + foot;
        }
      }
      return 'พิมพ์สิ่งที่จะเทียบ 2 อย่าง คั่นด้วย “กับ” ครับ เช่น “เทียบ MK1000 กับ ขอบ14 DL”';
    }

    // 🔁 ยางทดแทน/ขนาดใกล้เคียง — อิงเส้นผ่าศูนย์กลางจริง (±3%)
    if (/ทดแทน|ใกล้เคียง|แทนขนาด|แทนรุ่น|ใส่แทน|size ?ใกล้/i.test(ql)) {
      var base = rowsMatch(q).list[0];
      if (!base) return 'บอกขนาดที่จะหายางทดแทนด้วยครับ เช่น “ทดแทน 195R14C”';
      var bd = dimsOf(base.size);
      if (!bd || !bd.hCm) return 'ยังไม่มีข้อมูลมิติของ ' + esc(base.size) + ' จึงแนะนำทดแทนไม่ได้ครับ (ใส่มิติในรายละเอียดสินค้าก่อน)';
      var seen = {}, cand = [];
      srcRows().forEach(function (r) {
        if (!r.size || r.size === base.size || seen[r.size]) return;
        var d = dimsOf(r.size);
        if (d && d.hCm && Math.abs(d.hCm - bd.hCm) <= bd.hCm * 0.03) { seen[r.size] = 1; cand.push({ size: r.size, hCm: d.hCm }); }
      });
      cand.sort(function (a, b) { return Math.abs(a.hCm - bd.hCm) - Math.abs(b.hCm - bd.hCm); });
      if (!cand.length) return 'ไม่พบยางขนาดอื่นที่เส้นผ่าศูนย์กลางใกล้เคียง ' + esc(base.size) + ' (~' + inch(bd.hCm) + ' นิ้ว) ครับ';
      return '🔁 ยางทดแทน <b>' + esc(base.size) + '</b> (สูง ~' + inch(bd.hCm) + ' นิ้ว · ภายใน ±3%):<br>' + cand.slice(0, 6).map(function (c) {
        var pct = (c.hCm - bd.hCm) / bd.hCm * 100;
        return '&nbsp;&nbsp;• <b>' + esc(c.size) + '</b> <span style="color:#9a8;font-size:.9em">(สูง ' + inch(c.hCm) + '" · ' + (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%)</span>';
      }).join('<br>');
    }

    // 📐 ถามมิติของขนาด — "195R14 สูงเท่าไหร่" · "มิติ 31x10.5R15"
    if (/มิติ|เส้นผ่า|(?:สูง|กว้าง)\s*(?:เท่าไหร่|เท่าไร|กี่)|(?:เท่าไหร่|กี่)\s*(?:นิ้ว|ซม)/.test(ql)) {
      var bz = rowsMatch(q).list[0];
      if (bz) {
        var d = dimsOf(bz.size);
        if (d && d.hCm) return '📐 <b>' + esc(bz.size) + '</b><br>· เส้นผ่าศูนย์กลาง ~' + inch(d.hCm) + ' นิ้ว (' + Math.round(d.hCm) + ' ซม.)' + (d.wCm ? '<br>· หน้ากว้าง ~' + inch(d.wCm) + ' นิ้ว (' + Math.round(d.wCm) + ' ซม.)' : '');
        return 'ยังไม่มีข้อมูลมิติของ ' + esc(bz.size) + ' ครับ (เพิ่มได้ในรายละเอียดสินค้า)';
      }
    }

    // มีปรับราคาอะไรบ้าง
    if (/ปรับ(ปรุง)?ราคา|เปลี่ยนราคา|อัพเดท|อัปเดต/.test(ql)) {
      var rows = srcRows().filter(function (r) { return r.changed; });
      if (!rows.length) return 'รอบนี้ยังไม่มีการปรับราคาครับ ✅';
      return 'รอบนี้มีการปรับราคา <b>' + rows.length + ' รายการ</b>:<br>' + groupedBySize(rows.slice(0, 12)) + (rows.length > 12 ? '<br>…และอีก ' + (rows.length - 12) + ' รายการ' : '');
    }

    // 📊 สรุปภาพรวมชีต
    if (/สรุป|ภาพรวม|มีกี่รายการ|ทั้งหมดกี่|overview|dashboard|สถิติ/i.test(ql)) {
      var allR = srcRows(); var szs = {}, brs = {}, prc = [], chg = 0;
      allR.forEach(function (r) { if (r.size) szs[r.size] = 1; if (r.brand) brs[r.brand] = 1; if (XL2.isNumeric(r.retail)) prc.push(XL2.toN(r.retail)); if (r.changed) chg++; });
      prc.sort(function (a, b) { return a - b; });
      var sm = '📊 สรุปชีตนี้:<br>· รายการทั้งหมด <b>' + allR.length + '</b><br>· ขนาด/รุ่น <b>' + Object.keys(szs).length + '</b> · ยี่ห้อ <b>' + Object.keys(brs).length + '</b>';
      if (prc.length) sm += '<br>· ช่วงราคาขาย <b>' + fmt(prc[0]) + '</b>–<b>' + fmt(prc[prc.length - 1]) + '</b>';
      sm += '<br>· รอบนี้ปรับราคา <b>' + chg + '</b> รายการ';
      return sm;
    }
    // 🏷️ มียี่ห้ออะไรบ้าง
    if (/ยี่ห้อ.*(บ้าง|อะไร|มีไหน)|แบรนด์.*(บ้าง|อะไร)|มี.*ยี่ห้อ/.test(ql)) {
      var bset = {}; srcRows().forEach(function (r) { if (r.brand) bset[r.brand] = 1; });
      var barr = Object.keys(bset).sort();
      if (!barr.length) return 'ยังไม่มีข้อมูลยี่ห้อครับ';
      return '🏷️ ยี่ห้อในชีต (' + barr.length + '):<br>' + barr.map(function (b) { var f = XL2.brandFull(b); return '<b>' + esc(b) + '</b>' + (f && f.toLowerCase() !== b.toLowerCase() ? ' <span style="color:#9a8;font-size:.9em">' + esc(f) + '</span>' : ''); }).join(' · ');
    }
    // 📐 มีขนาด/รุ่นอะไรบ้าง
    if (/ขนาด.*(บ้าง|อะไร|มีไหน)|ไซ.?ซ.?.*(บ้าง|อะไร)|มี.*ขนาด.*บ้าง|รุ่นอะไรบ้าง/.test(ql)) {
      var zseen = {}, zarr = []; srcRows().forEach(function (r) { if (r.size && !zseen[r.size]) { zseen[r.size] = 1; zarr.push(r.size); } });
      if (!zarr.length) return 'ยังไม่มีข้อมูลขนาดครับ';
      return '📐 ขนาด/รุ่นในชีต (' + zarr.length + '):<br>' + zarr.slice(0, 40).map(function (s) { return prodIcon(s) + esc(s); }).join(' · ') + (zarr.length > 40 ? ' …' : '');
    }

    var m = rowsMatch(q);

    // 🧮 คูณจำนวน (กี่เส้น/ล้อ/ชุด) — รวม VAT/กำไรรวมให้ด้วย
    var qtyM = /(\d+)\s*(เส้น|ล้อ|ลูก|ใบ|อัน|ชุด|กระป๋อง|ขวด|ก้อน|ตัว|ลิตร)/.exec(ql);
    if (qtyM && m.list.length) {
      var n = parseInt(qtyM[1], 10), unit = qtyM[2];
      var pick = m.list.find(function (r) { return XL2.isNumeric(r.retail); });
      if (pick && n > 0) {
        var up = XL2.toN(pick.retail), tot = up * n;
        var s = '🧮 ' + prodIcon(pick.size) + '<b>' + esc(pick.size) + '</b> ' + esc(pick.brand) + (pick.model ? ' ' + esc(pick.model) : '') +
          '<br>· ' + fmt(up) + ' × ' + n + ' ' + unit + ' = <b>' + fmt(tot) + ' บาท</b>';
        if (/vat|แวต|ภาษี|รวมภาษี/.test(ql)) s += '<br>· รวม VAT 7% = <b>' + fmt(Math.round(tot * 1.07)) + ' บาท</b>';
        if (isAdmin() && XL2.isNumeric(pick.cost)) { var pf = (up - XL2.toN(pick.cost)) * n; s += ' <span style="color:#9a8;font-size:.9em">(กำไรรวม ' + (pf >= 0 ? '+' : '') + fmt(pf) + ')</span>'; }
        return s;
      }
    }
    // 🧾 รวม VAT (ไม่ระบุจำนวน)
    if (/vat|แวต|ภาษี|รวมภาษี/.test(ql) && m.list.length) {
      var pv = m.list.find(function (r) { return XL2.isNumeric(r.retail); });
      if (pv) { var rv = XL2.toN(pv.retail); return '🧾 ' + prodIcon(pv.size) + '<b>' + esc(pv.size) + '</b> ' + esc(pv.brand) + (pv.model ? ' ' + esc(pv.model) : '') + '<br>· ราคาขาย ' + fmt(rv) + '<br>· รวม VAT 7% = <b>' + fmt(Math.round(rv * 1.07)) + ' บาท</b>'; }
    }
    // 💸 ลดได้เท่าไหร่ / ต่อรอง (แอดมิน)
    if (/ลดได้|ต่อรอง|ส่วนลด|discount|ลดราคา/.test(ql) && m.list.length) {
      if (!isAdmin()) return 'ข้อมูลส่วนลด/ต้นทุน ดูได้เฉพาะแอดมินครับ 🔒';
      var pk = m.list.find(function (r) { return XL2.isNumeric(r.retail) && XL2.isNumeric(r.cost); });
      if (pk) {
        var rt = XL2.toN(pk.retail), ct = XL2.toN(pk.cost), room = rt - ct;
        return '💸 ' + prodIcon(pk.size) + '<b>' + esc(pk.size) + '</b> ' + esc(pk.brand) + (pk.model ? ' ' + esc(pk.model) : '') +
          '<br>· ราคาขาย ' + fmt(rt) + ' · ทุน ' + fmt(ct) +
          '<br>· ลดได้สูงสุด <b>' + fmt(room) + '</b> บาท (เท่าทุน กำไร 0)' +
          '<br>· แนะนำคงกำไร ~10% → ต่ำสุด ~<b>' + fmt(Math.round(ct * 1.1)) + '</b> บาท';
      }
    }

    if (/ถูก(ที่)?สุด|ประหยัด/.test(ql) || /แพง(ที่)?สุด/.test(ql)) {
      var pool = (m.hasFilter ? m.list : srcRows()).filter(function (r) { return XL2.isNumeric(r.retail); });
      if (!pool.length) return 'ไม่พบรายการที่ตรงเงื่อนไขครับ';
      var cheap = /ถูก|ประหยัด/.test(ql);
      pool.sort(function (a, b) { return XL2.toN(a.retail) - XL2.toN(b.retail); });
      var pick = cheap ? pool[0] : pool[pool.length - 1];
      return (cheap ? '🏷️ ถูกสุด' : '💎 แพงสุด') + (m.hasFilter ? 'ตามเงื่อนไข' : 'ในชีตนี้') + ':<br>' + rowLine(pick);
    }

    // margin (แอดมิน)
    if (/margin|กำไร|ส่วนต่าง/.test(ql)) {
      if (!isAdmin()) return 'ข้อมูล Margin ดูได้เฉพาะโหมดแอดมินครับ 🔒';
      var pool2 = (m.hasFilter ? m.list : srcRows()).filter(function (r) { return XL2.isNumeric(r.margin); });
      if (!pool2.length) return 'ไม่พบรายการครับ';
      pool2.sort(function (a, b) { return XL2.toN(b.margin) - XL2.toN(a.margin); });
      return '📈 Margin ' + (m.hasFilter ? 'ตามเงื่อนไข' : 'สูงสุด 5 อันดับ') + ':<br>' + pool2.slice(0, 5).map(rowLine).join('<br>');
    }

    // ค้นราคา
    if (m.hasFilter) {
      if (!m.list.length) {
        if (m.cat) return 'ยังไม่มีสินค้าหมวด ' + catLabel(m.cat) + ' ในชีตนี้ครับ — แอดมินกำหนดชนิดสินค้าได้ที่ “รายละเอียดสินค้า” (คลิกขนาด)';
        return 'ไม่พบสินค้าที่ตรงกับ “' + esc(q) + '” ครับ ลองพิมพ์ขนาด เช่น 195R14 · ชื่อรุ่น · หรือหมวด เช่น ยางใน/น้ำมัน';
      }
      var head = m.cat ? ('🔎 หมวด ' + catLabel(m.cat) + ' · พบ ' + m.list.length + ' รายการ:') : ('🔎 พบ ' + m.list.length + ' รายการ:');
      if (m.relaxed) head += '<br><span style="color:#9a8;font-size:.9em">(ไม่เจอยี่ห้อ/รุ่นที่ระบุเป๊ะ — แสดงสินค้าขนาดเดียวกัน)</span>';
      return head + '<br>' + groupedBySize(m.list.slice(0, 12)) + (m.list.length > 12 ? '<br>…และอีก ' + (m.list.length - 12) + ' รายการ (ลองระบุเพิ่ม)' : '');
    }

    return 'ผมช่วยเรื่องราคา/สินค้าได้ครับ ลองถาม:<br>· “ราคา 195R14C” · “14-30” (ชื่อเรียกอื่นก็ได้)<br>· หมวดอื่นๆ: “ยางใน” · “รองขอบ” · “กระทะ” · “น้ำมัน” · “แบต” · “อะไหล่”<br>· “เทียบ MK1000 กับ KR” (เทียบราคา)<br>· “ทดแทน 195R14C” · “195R14C สูงเท่าไหร่” (ยางทดแทน/มิติ)<br>· “ขอบ 14 ไม่เกิน 2000” · “ยางถูกสุดขอบ 14” · “มีปรับราคาอะไรบ้าง”<br>· “สต็อก 195R14C” · “DOT 195R14C” (ต้องเชื่อมฐานข้อมูล)' + (isAdmin() ? '<br>· “margin สูงสุด” · “ถอดรหัส TNLX”' : '');
  }

  // ---------- ไอคอนหมาชิบะอินุ + หูฟัง call center 🐕🎧 ----------
  var SHIBA = '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-label="ชิบะ call center">' +
    '<polygon points="12,26 18,8 29,20" fill="#E8A33D" stroke="#9c6b1e" stroke-width="1.5"/>' +
    '<polygon points="52,26 46,8 35,20" fill="#E8A33D" stroke="#9c6b1e" stroke-width="1.5"/>' +
    '<polygon points="16,23 19,12 24,19" fill="#7a5220"/>' +
    '<polygon points="48,23 45,12 40,19" fill="#7a5220"/>' +
    '<rect x="11" y="18" width="42" height="36" rx="14" fill="#E8A33D" stroke="#9c6b1e" stroke-width="1.5"/>' +
    '<ellipse cx="32" cy="45" rx="16" ry="12" fill="#FFF6E8"/>' +
    '<ellipse cx="32" cy="31" rx="6.5" ry="8" fill="#FFF6E8"/>' +
    '<rect x="18" y="30.5" width="28" height="3" rx="1.5" fill="#1a1a1a"/>' +
    '<rect x="17.5" y="31" width="11.5" height="8" rx="3.2" fill="#1a1a1a"/>' +
    '<rect x="35" y="31" width="11.5" height="8" rx="3.2" fill="#1a1a1a"/>' +
    '<rect x="19.5" y="33" width="6.5" height="2.4" rx="1.2" fill="#5b8fd6"/>' +
    '<rect x="37" y="33" width="6.5" height="2.4" rx="1.2" fill="#5b8fd6"/>' +
    '<ellipse cx="32" cy="43" rx="3" ry="2.2" fill="#333"/>' +
    '<path d="M32 45 V48 M27 49 Q32 53 37 49" stroke="#333" stroke-width="2" fill="none" stroke-linecap="round"/>' +
    '<path d="M9 33 Q32 8 55 33" fill="none" stroke="#2A6FDB" stroke-width="4" stroke-linecap="round"/>' +
    '<rect x="5" y="29" width="9.5" height="16" rx="4.7" fill="#2A6FDB" stroke="#1b4f9e" stroke-width="1"/>' +
    '<rect x="49.5" y="29" width="9.5" height="16" rx="4.7" fill="#2A6FDB" stroke="#1b4f9e" stroke-width="1"/>' +
    '<path d="M54 38 Q58 50 40 51" fill="none" stroke="#2A6FDB" stroke-width="2.5" stroke-linecap="round"/>' +
    '<circle cx="39" cy="51" r="2.8" fill="#d62828"/>' +
    '</svg>';

  // ---------- โปรไฟล์บอต (รูป/ชื่อ/คำแนะนำตัว) — ผู้ใช้ตั้งเองได้ · จำถาวร ----------
  var PROF_KEY = 'xls2_cb_profile';
  var PROF_DEFAULT = {
    name: 'ชิบะคุง',
    sub: 'ผู้ช่วยราคายาง',
    avatar: '',
    gender: 'male',
    greeting: 'สวัสดีครับ 🐕 ผม “ชิบะคุง” ถามราคาสินค้าในชีตได้เลย — ยาง · ยางใน · รองขอบ · กระทะ · น้ำมัน · แบต · อะไหล่ ฯลฯ · พิมพ์ขนาด/ยี่ห้อ/รุ่น หรือกด 📷 แนบรูปให้ผมอ่านได้'
  };
  function loadProf() {
    var p; try { p = Object.assign({}, PROF_DEFAULT, JSON.parse(localStorage.getItem(PROF_KEY) || '{}')); }
    catch (e) { p = Object.assign({}, PROF_DEFAULT); }
    if (!p.name) p.name = PROF_DEFAULT.name;
    if (!p.sub) p.sub = PROF_DEFAULT.sub;
    if (!p.greeting) p.greeting = PROF_DEFAULT.greeting;
    return p;
  }
  function saveProf(p) { try { localStorage.setItem(PROF_KEY, JSON.stringify(p)); } catch (e) {} }
  // ปรับคำลงท้ายตามเพศ: หญิง → ครับ→ค่ะ · คำถาม (ลงท้าย ?) → คะ
  function particleize(html) {
    if (loadProf().gender !== 'female') return html;
    return String(html)
      .replace(/ครับ(\s*[?？])/g, 'คะ$1')
      .replace(/ครับ/g, 'ค่ะ')
      .replace(/ผม/g, 'ดิฉัน');
  }
  function avatarHTML() {
    var a = loadProf().avatar;
    return a ? '<img src="' + a + '" alt="avatar" style="width:100%;height:100%;object-fit:cover;border-radius:50%;display:block;" />' : SHIBA;
  }

  // ---------- UI ----------
  var open = false, panel, body, inp;
  function build() {
    var btn = document.createElement('button');
    btn.id = 'cbFab'; btn.title = 'แชทบอทราคายาง';
    btn.innerHTML = avatarHTML();
    document.body.appendChild(btn);

    panel = document.createElement('div');
    panel.id = 'cbPanel';
    panel.innerHTML =
      '<div class="cb-head"><span class="cb-ava">' + avatarHTML() + '</span><div><div class="cb-name">' + esc(loadProf().name) + '</div><div class="cb-sub" id="cbSub">ผู้ช่วยราคายาง · ตอบจากข้อมูลในชีต</div></div>' +
      '<span class="cb-gear" title="ตั้งค่า AI plugin">⚙️</span><span class="cb-x" title="ปิด">✕</span></div>' +
      '<div class="cb-cfg" id="cbCfg">' +
        '<div class="cb-prof">' +
          '<div class="cb-prof-row">' +
            '<span class="cb-prof-ava" id="cbProfAva">' + avatarHTML() + '</span>' +
            '<div class="cb-prof-btns"><button class="cb-chip" id="cbProfPic">🖼️ เปลี่ยนรูป</button><button class="cb-chip" id="cbProfPicClr">ลบรูป</button></div>' +
          '</div>' +
          '<input id="cbProfName" placeholder="ชื่อบอท เช่น ชิบะคุง" />' +
          '<input id="cbProfSub" placeholder="คำบรรยายใต้ชื่อ เช่น ผู้ช่วยราคายาง" />' +
          '<div class="cb-prof-sex"><span>เพศ/คำลงท้าย:</span>' +
            '<label><input type="radio" name="cbProfSex" value="male" /> ชาย (ครับ)</label>' +
            '<label><input type="radio" name="cbProfSex" value="female" /> หญิง (ค่ะ/คะ)</label>' +
          '</div>' +
          '<textarea id="cbProfGreet" placeholder="คำทักทาย/แนะนำตัว" rows="3"></textarea>' +
          '<div style="display:flex;gap:6px;justify-content:flex-end;"><button class="cb-chip" id="cbProfReset">คืนค่าเริ่มต้น</button><button class="cb-chip" id="cbProfSave" style="background:#1d6f42;color:#fff;">บันทึกโปรไฟล์</button></div>' +
          '<input type="file" id="cbProfFile" accept="image/*" style="display:none;" />' +
        '</div>' +
        '<div class="cb-cfg-sep">— ตั้งค่า AI อ่านรูป —</div>' +
        '<label class="cb-cfg-row"><input type="checkbox" id="aiEnabled" /> เปิด AI local สำหรับ“อ่านรูป” 📷 (คำถามข้อความใช้บอตในโปรแกรมเสมอ)</label>' +
        '<input id="aiEndpoint" placeholder="Endpoint vision เช่น http://192.168.10.38:8080/v1/chat/completions" />' +
        '<div style="display:flex;gap:6px;"><input id="aiModel" placeholder="โมเดล vision เช่น Qwen3.6-35B" style="flex:1;" /><input id="aiKey" placeholder="API key (ถ้ามี)" style="flex:1;" /></div>' +
        '<div class="cb-cfg-note">🔒 AI vision ใช้ <b>“อ่านรูป” อย่างเดียว</b> — เห็นแค่รูปที่แนบ ไม่เห็นราคา/ทุน/รหัสลับ · คำถามข้อความทั้งหมดวิเคราะห์ด้วยบอทในโปรแกรม (ออฟไลน์)</div>' +
        '<div style="display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap;"><button class="cb-chip" id="aiTest">🔌 ทดสอบ</button><button class="cb-chip" id="aiTestImg">📷 ทดสอบอ่านรูป</button><button class="cb-chip" id="aiSave" style="background:#1d6f42;color:#fff;">บันทึก</button></div>' +
      '</div>' +
      '<div class="cb-body" id="cbBody"></div>' +
      '<div class="cb-chips" id="cbChips"></div>' +
      '<div class="cb-foot"><button id="cbAttach" title="แนบรูปให้บอทอ่าน">📷</button><button id="cbMic" title="คำสั่งเสียง (พูดถามได้เลย)">🎤</button><input id="cbInp" placeholder="ถามเรื่องราคา เช่น ราคา MK1000…" /><button id="cbSend">ส่ง</button><input type="file" id="cbFile" accept="image/*" style="display:none;" /></div>';
    document.body.appendChild(panel);
    body = panel.querySelector('#cbBody');
    inp = panel.querySelector('#cbInp');

    // ---------- ปรับขนาดหน้าต่าง (ลากมุมซ้ายล่าง) + จำขนาด ----------
    var SIZE_KEY = 'xls2_cb_size';
    var resizer = document.createElement('div'); resizer.className = 'cb-resize'; resizer.title = 'ลากเพื่อปรับขนาด';
    panel.appendChild(resizer);
    function clampSize(w, h) {
      return {
        w: Math.max(300, Math.min(w, window.innerWidth - 12)),
        h: Math.max(320, Math.min(h, window.innerHeight - 12))
      };
    }
    (function () {
      try {
        var s = JSON.parse(localStorage.getItem(SIZE_KEY) || 'null');
        if (s && s.w && s.h) { var c = clampSize(s.w, s.h); panel.style.width = c.w + 'px'; panel.style.height = c.h + 'px'; panel.style.maxHeight = 'none'; }
      } catch (e) {}
    })();
    (function () {
      var rz = false, sx = 0, sy = 0, sw = 0, sh = 0, aRight = 0, aBottom = 0;
      function start(e) {
        var t = e.touches ? e.touches[0] : e;
        rz = true;
        var r = panel.getBoundingClientRect();
        sx = t.clientX; sy = t.clientY; sw = r.width; sh = r.height;
        aRight = r.right; aBottom = r.bottom;             // ตรึงมุมขวา-ล่างไว้กับที่
        panel.style.maxHeight = 'none'; panel.style.transition = 'none';
        document.addEventListener('mousemove', mv, true); document.addEventListener('mouseup', end, true);
        document.addEventListener('touchmove', mv, { passive: false, capture: true }); document.addEventListener('touchend', end, true);
        if (e.cancelable) e.preventDefault();
        e.stopPropagation();
      }
      function mv(e) {
        if (!rz) return;
        var t = e.touches ? e.touches[0] : e;
        var c = clampSize(sw + (sx - t.clientX), sh + (t.clientY - sy));   // ซ้าย→กว้างขึ้น · ล่าง→สูงขึ้น
        panel.style.width = c.w + 'px'; panel.style.height = c.h + 'px';
        // คงมุมขวา-ล่างไว้ที่เดิม (ยึดด้วย left/top เสมอไม่ว่าก่อนหน้าจะยึดมุมไหน)
        panel.style.right = 'auto'; panel.style.bottom = 'auto';
        panel.style.left = Math.max(6, aRight - c.w) + 'px';
        panel.style.top = Math.max(6, aBottom - c.h) + 'px';
        if (e.cancelable) e.preventDefault();
      }
      function end() {
        if (!rz) return; rz = false;
        panel.style.transition = '';
        document.removeEventListener('mousemove', mv, true); document.removeEventListener('mouseup', end, true);
        document.removeEventListener('touchmove', mv, true); document.removeEventListener('touchend', end, true);
        try { localStorage.setItem(SIZE_KEY, JSON.stringify({ w: parseInt(panel.style.width, 10), h: parseInt(panel.style.height, 10) })); } catch (e) {}
      }
      resizer.addEventListener('mousedown', start);
      resizer.addEventListener('touchstart', start, { passive: false });
    })();

    btn.onclick = function () { if (btn._dragged) { btn._dragged = false; return; } toggle(!open); };
    // ลากหุ่นยนต์ไปวางได้อิสระทุกตำแหน่ง (จำตำแหน่งถาวร)
    (function () {
      try { var p = JSON.parse(localStorage.getItem('xls2_fabpos') || 'null'); if (p) { btn.style.left = p.x + 'px'; btn.style.top = p.y + 'px'; btn.style.right = 'auto'; btn.style.bottom = 'auto'; } } catch (e) {}
      var dx = 0, dy = 0, moved = false, dragging = false;
      function down(e) {
        var pt = e.touches ? e.touches[0] : e;
        dragging = true; moved = false;
        var r = btn.getBoundingClientRect();
        dx = pt.clientX - r.left; dy = pt.clientY - r.top;
        document.addEventListener('mousemove', move, true); document.addEventListener('mouseup', up, true);
        document.addEventListener('touchmove', move, { passive: false, capture: true }); document.addEventListener('touchend', up, true);
      }
      function move(e) {
        if (!dragging) return;
        var pt = e.touches ? e.touches[0] : e;
        var x = pt.clientX - dx, y = pt.clientY - dy;
        x = Math.max(2, Math.min(window.innerWidth - btn.offsetWidth - 2, x));
        y = Math.max(2, Math.min(window.innerHeight - btn.offsetHeight - 2, y));
        btn.style.left = x + 'px'; btn.style.top = y + 'px'; btn.style.right = 'auto'; btn.style.bottom = 'auto';
        moved = true; if (e.cancelable) e.preventDefault();
      }
      function up() {
        document.removeEventListener('mousemove', move, true); document.removeEventListener('mouseup', up, true);
        document.removeEventListener('touchmove', move, { capture: true }); document.removeEventListener('touchend', up, true);
        if (moved) { btn._dragged = true; localStorage.setItem('xls2_fabpos', JSON.stringify({ x: parseInt(btn.style.left, 10), y: parseInt(btn.style.top, 10) })); if (typeof reposPanel === 'function') reposPanel(); }
        dragging = false;
      }
      btn.addEventListener('mousedown', down);
      btn.addEventListener('touchstart', down, { passive: true });
    })();
    function reposPanel() {
      var r = btn.getBoundingClientRect();
      var gap = 8;
      panel.style.right = 'auto';
      var roomAbove = r.top - gap;        // พื้นที่เหนือปุ่ม fab
      var roomBelow = window.innerHeight - r.bottom - gap;
      if (roomAbove >= 200 || roomAbove >= roomBelow) {
        // วางเหนือปุ่ม → ยึดขอบล่างไว้ใกล้ปุ่ม โตขึ้นด้านบน (เนื้อหาเลื่อนใน .cb-body)
        panel.style.top = 'auto';
        panel.style.bottom = (window.innerHeight - (r.top - gap)) + 'px';
        panel.style.maxHeight = Math.max(180, r.top - gap - gap) + 'px';
      } else {
        // ไม่พอด้านบน → วางใต้ปุ่ม โตลงล่าง
        panel.style.bottom = 'auto';
        panel.style.top = (r.bottom + gap) + 'px';
        panel.style.maxHeight = Math.max(180, window.innerHeight - r.bottom - gap - gap) + 'px';
      }
      panel.style.left = Math.max(8, Math.min(r.right - panel.offsetWidth, window.innerWidth - panel.offsetWidth - 8)) + 'px';
    }
    window.addEventListener('cb-open', reposPanel);
    window.addEventListener('resize', function () { if (open) reposPanel(); });
    // ลากหน้าต่างแชทด้วยหัวบนสุด (ย้ายขึ้น/ไปไหนก็ได้ · กันหลุดเฟรม)
    (function () {
      var head = panel.querySelector('.cb-head');
      var dx = 0, dy = 0, dragging = false;
      head.addEventListener('mousedown', function (e) {
        if (e.target.closest('.cb-x, .cb-gear')) return;
        dragging = true;
        var r = panel.getBoundingClientRect();
        dx = e.clientX - r.left; dy = e.clientY - r.top;
        panel.style.right = 'auto'; panel.style.bottom = 'auto';
        document.addEventListener('mousemove', pm, true); document.addEventListener('mouseup', pu, true);
        e.preventDefault();
      });
      function pm(e) {
        if (!dragging) return;
        var x = Math.max(6, Math.min(e.clientX - dx, window.innerWidth - panel.offsetWidth - 6));
        var y = Math.max(6, Math.min(e.clientY - dy, window.innerHeight - 40));
        panel.style.left = x + 'px'; panel.style.top = y + 'px';
      }
      function pu() { dragging = false; document.removeEventListener('mousemove', pm, true); document.removeEventListener('mouseup', pu, true); }
    })();
    panel.querySelector('.cb-x').onclick = function () { toggle(false); };
    panel.querySelector('#cbSend').onclick = send;
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') send(); });

    // settings
    var cfgEl = panel.querySelector('#cbCfg');
    panel.querySelector('.cb-gear').onclick = function () {
      var c = loadCfg();
      panel.querySelector('#aiEnabled').checked = !!c.enabled;
      panel.querySelector('#aiEndpoint').value = c.endpoint || '';
      panel.querySelector('#aiModel').value = c.model || '';
      panel.querySelector('#aiKey').value = c.apiKey || '';
      var pf = loadProf();
      panel.querySelector('#cbProfName').value = pf.name || '';
      panel.querySelector('#cbProfSub').value = pf.sub || '';
      panel.querySelector('#cbProfGreet').value = pf.greeting || '';
      var sexR = panel.querySelector('input[name="cbProfSex"][value="' + (pf.gender === 'female' ? 'female' : 'male') + '"]'); if (sexR) sexR.checked = true;
      panel.querySelector('#cbProfAva').innerHTML = avatarHTML();
      cfgEl.classList.toggle('open');
    };
    // ---------- โปรไฟล์: รูป/ชื่อ/คำแนะนำตัว ----------
    var profFile = panel.querySelector('#cbProfFile');
    var pendingAvatar = null;   // null = ยังไม่แก้ · '' = ลบ · dataUrl = รูปใหม่
    panel.querySelector('#cbProfPic').onclick = function () { profFile.click(); };
    profFile.onchange = function () {
      var f = profFile.files && profFile.files[0]; profFile.value = '';
      if (!f) return;
      var rd = new FileReader();
      rd.onload = function () {
        var im = new Image();
        im.onload = function () {
          var sz = 128, c = document.createElement('canvas'); c.width = sz; c.height = sz;
          var ctx = c.getContext('2d');
          var s = Math.min(im.naturalWidth, im.naturalHeight);
          ctx.drawImage(im, (im.naturalWidth - s) / 2, (im.naturalHeight - s) / 2, s, s, 0, 0, sz, sz);
          pendingAvatar = c.toDataURL('image/jpeg', 0.85);
          panel.querySelector('#cbProfAva').innerHTML = '<img src="' + pendingAvatar + '" alt="avatar" style="width:100%;height:100%;object-fit:cover;border-radius:50%;display:block;" />';
        };
        im.src = rd.result;
      };
      rd.readAsDataURL(f);
    };
    panel.querySelector('#cbProfPicClr').onclick = function () {
      pendingAvatar = '';
      panel.querySelector('#cbProfAva').innerHTML = SHIBA;
    };
    function applyProfile() {
      var pf = loadProf();
      panel.querySelector('.cb-ava').innerHTML = avatarHTML();
      panel.querySelector('.cb-name').textContent = pf.name;
      var fab = document.getElementById('cbFab'); if (fab) fab.innerHTML = avatarHTML();
      updateSub();
    }
    panel.querySelector('#cbProfSave').onclick = function () {
      var pf = loadProf();
      pf.name = panel.querySelector('#cbProfName').value.trim() || PROF_DEFAULT.name;
      pf.sub = panel.querySelector('#cbProfSub').value.trim() || PROF_DEFAULT.sub;
      pf.greeting = panel.querySelector('#cbProfGreet').value.trim() || PROF_DEFAULT.greeting;
      var sexSel = panel.querySelector('input[name="cbProfSex"]:checked');
      pf.gender = sexSel ? sexSel.value : 'male';
      if (pendingAvatar !== null) pf.avatar = pendingAvatar;
      saveProf(pf); pendingAvatar = null;
      applyProfile();
      cfgEl.classList.remove('open');
      bot('✅ บันทึกโปรไฟล์แล้ว — ชื่อ “' + esc(pf.name) + '”');
    };
    panel.querySelector('#cbProfReset').onclick = function () {
      saveProf(Object.assign({}, PROF_DEFAULT)); pendingAvatar = null;
      panel.querySelector('#cbProfName').value = PROF_DEFAULT.name;
      panel.querySelector('#cbProfSub').value = PROF_DEFAULT.sub;
      panel.querySelector('#cbProfGreet').value = PROF_DEFAULT.greeting;
      var mr = panel.querySelector('input[name="cbProfSex"][value="male"]'); if (mr) mr.checked = true;
      panel.querySelector('#cbProfAva').innerHTML = SHIBA;
      applyProfile();
    };
    panel.querySelector('#aiSave').onclick = function () {
      saveCfg({ enabled: panel.querySelector('#aiEnabled').checked, endpoint: panel.querySelector('#aiEndpoint').value.trim(), model: panel.querySelector('#aiModel').value.trim(), apiKey: panel.querySelector('#aiKey').value.trim() });
      cfgEl.classList.remove('open');
      updateSub();
      bot(loadCfg().enabled ? '✅ เปิด AI local สำหรับอ่านรูปแล้ว 📷 — คำถามข้อความยังตอบจากข้อมูลในชีตเหมือนเดิม · กด 📷 แนบรูปได้เลย' : 'บันทึกแล้ว (ใช้โหมดตอบจากกฎในตัว)');
    };
    panel.querySelector('#aiTest').onclick = function () {
      saveCfg({ enabled: panel.querySelector('#aiEnabled').checked, endpoint: panel.querySelector('#aiEndpoint').value.trim(), model: panel.querySelector('#aiModel').value.trim(), apiKey: panel.querySelector('#aiKey').value.trim() });
      bot('🔌 กำลังทดสอบการเชื่อมต่อ…');
      var mb0 = mixedBlocked(); if (mb0) { bot(mb0); return; }
      aiPing()
        .then(function (txt) { bot('✅ เชื่อมต่อ vision สำเร็จ: ' + esc(String(txt)).slice(0, 200)); })
        .catch(function (e) {
          var em = e && e.message || '';
          var tip = /Failed to fetch|NetworkError|HTTP 0/.test(em)
            ? ' — เช็ก: vision รันอยู่ไหม · CORS · หรือ https→http (mixed-content)'
            : ' — ตรวจ endpoint/โมเดล';
          bot('❌ เชื่อมไม่สำเร็จ (' + esc(em) + ')' + tip);
        });
    };

    // 📷 ทดสอบอ่านรูป: สร้างรูปตัวอย่างยางในตัว (มีข้อความขนาดชัด) → vision อ่าน → สมองในโปรแกรมค้นราคาต่อ
    function sampleTireImage() {
      var cv = document.createElement('canvas'); cv.width = 360; cv.height = 360;
      var x = cv.getContext('2d');
      x.fillStyle = '#111'; x.fillRect(0, 0, 360, 360);
      x.strokeStyle = '#555'; x.lineWidth = 26; x.beginPath(); x.arc(180, 180, 150, 0, 7); x.stroke();
      x.strokeStyle = '#333'; x.lineWidth = 60; x.beginPath(); x.arc(180, 180, 95, 0, 7); x.stroke();
      x.fillStyle = '#f2f2f2'; x.textAlign = 'center';
      x.font = 'bold 30px Arial'; x.fillText('215/75R14C', 180, 150);
      x.font = 'bold 22px Arial'; x.fillText('MAXXIS', 180, 195);
      x.font = '18px Arial'; x.fillText('CR966  8PR', 180, 225);
      return cv.toDataURL('image/jpeg', 0.9);
    }
    panel.querySelector('#aiTestImg').onclick = function () {
      saveCfg({ enabled: panel.querySelector('#aiEnabled').checked, endpoint: panel.querySelector('#aiEndpoint').value.trim(), model: panel.querySelector('#aiModel').value.trim(), apiKey: panel.querySelector('#aiKey').value.trim() });
      var cfg = loadCfg();
      if (!cfg.endpoint) { bot('ใส่ endpoint vision ก่อนครับ (ช่อง Endpoint)'); return; }
      var mbi = mixedBlocked(); if (mbi) { bot(mbi); return; }
      var img = sampleTireImage();
      panel.querySelector('.cb-cfg').classList.remove('open');
      msg('<img src="' + img + '" alt="รูปทดสอบ" /><div>📷 ทดสอบอ่านรูปตัวอย่าง (215/75R14C MAXXIS)</div>', 'me');
      var typ = document.createElement('div'); typ.className = 'cb-msg bot'; typ.textContent = '⋯ 👁️ กำลังอ่านรูปตัวอย่าง (vision)…';
      body.appendChild(typ); body.scrollTop = body.scrollHeight;
      aiReadImage(img, '')
        .then(function (seen) {
          typ.remove();
          bot('✅ vision อ่านรูปได้!<br>👁️ อ่านจากรูป: <i>' + esc(seen) + '</i>');
          var ans; try { ans = answer(seen); } catch (e) { ans = null; }
          if (ans) bot(ans);
          bot('🎉 ระบบอ่านรูป+ค้นราคาทำงานครบ — แนบรูปยางจริงได้เลย');
        })
        .catch(function (e) {
          typ.remove();
          var em = e && e.message || '';
          var tip = /Failed to fetch|NetworkError|HTTP 0/.test(em)
            ? ' — เช็ก: vision รันอยู่ไหม · CORS · https→http (mixed-content)'
            : (/HTTP 4|HTTP 5/.test(em) ? ' — โมเดลอาจไม่รับรูป/ชื่อโมเดลผิด' : '');
          bot('❌ อ่านรูปไม่สำเร็จ (' + esc(em) + ')' + tip);
        });
    };

    renderChips();
    updateSub();
    bot(loadProf().greeting);

    // 🎤 คำสั่งเสียง (Web Speech API · ภาษาไทย)
    var micBtn = panel.querySelector('#cbMic'), rec = null, recOn = false;
    // สัญลักษณ์เวฟ (กำลังอัดเสียง) — แสดงทับแถบล่างขณะฟัง
    var wave = document.createElement('div');
    wave.className = 'cb-wave';
    wave.innerHTML = '<span></span><span></span><span></span><span></span><span></span><span></span><span></span><em>กำลังฟัง… (แตะ 🎤 เพื่อหยุด)</em>';
    panel.querySelector('.cb-foot').appendChild(wave);
    function showWave(on) { wave.classList.toggle('on', on); }
    micBtn.onclick = function () {
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) { bot('ขออภัย เบราว์เซอร์นี้ไม่รองรับคำสั่งเสียง — ลอง Chrome หรือ Edge ครับ'); return; }
      if (recOn && rec) { rec.stop(); return; }
      rec = new SR();
      rec.lang = 'th-TH'; rec.interimResults = false; rec.maxAlternatives = 1;
      rec.onresult = function (ev) {
        var t = ev.results[0][0].transcript;
        inp.value = t;
        send();
      };
      rec.onend = function () { recOn = false; micBtn.classList.remove('rec'); showWave(false); };
      rec.onerror = function () { recOn = false; micBtn.classList.remove('rec'); showWave(false); bot('ฟังไม่ทัน/ไม่ได้ยินเสียง ลองกด 🎤 พูดใหม่อีกครั้งครับ'); };
      recOn = true; micBtn.classList.add('rec'); showWave(true);
      try { rec.start(); } catch (e) {}
    };

    // 📷 แนบรูปให้ชิบะคุงอ่าน → vision อ่านเป็นข้อความ → สมองในโปรแกรมบอก "มี/ไม่มี" + วาดวงเจาะจงได้
    function analyzeVision(seen) {
      var mm; try { mm = rowsMatch(String(seen || '')); } catch (e) { mm = { list: [], relaxed: false }; }
      if (mm.list && mm.list.length) {
        return '✅ <b>มีในร้านครับ</b> — พบ ' + mm.list.length + ' รายการ:<br>' + groupedBySize(mm.list.slice(0, 12)) +
          (mm.relaxed ? '<br><span style="color:#9a8;font-size:.9em">(รุ่น/ยี่ห้อไม่ตรงเป๊ะ — แสดงสินค้าขนาดเดียวกัน)</span>' : '') +
          (mm.list.length > 12 ? '<br>…และอีก ' + (mm.list.length - 12) + ' รายการ' : '');
      }
      return '❌ <b>ยังไม่มีในชีต/ร้านครับ</b> <span style="color:#9a8;font-size:.9em">(อ่านได้: ' + esc(String(seen).slice(0, 80)) + ')</span><br>ลองวาดวงเจาะจงสินค้าในรูป แล้วกด “✏️ อ่านเฉพาะวง” หรือพิมพ์ถามเองได้ครับ';
    }
    // เจอหลายสินค้าในรูป → ถามว่าเอาตัวไหน (กดเลือกได้) + วาดวงเองก็ได้
    function askWhich(items) {
      var wrap = document.createElement('div'); wrap.className = 'cb-msg bot';
      wrap.innerHTML = '👀 เจอ <b>' + items.length + '</b> อย่างในรูป — ต้องการถามตัวไหนครับ?';
      var bw = document.createElement('div'); bw.style.cssText = 'display:flex;flex-direction:column;gap:5px;margin-top:7px;';
      items.slice(0, 8).forEach(function (it) {
        var b = document.createElement('button'); b.className = 'cb-chip'; b.style.cssText = 'text-align:left;width:100%;';
        b.textContent = it;
        b.onclick = function () { msg(esc(it), 'me'); bot(analyzeVision(it)); };
        bw.appendChild(b);
      });
      wrap.appendChild(bw);
      var hint = document.createElement('div'); hint.style.cssText = 'font-size:.85em;color:#9a8;margin-top:7px;';
      hint.textContent = 'หรือวาดวงรอบสินค้าในรูปด้านบน แล้วกด ✏️ อ่านเฉพาะวง';
      wrap.appendChild(hint);
      body.appendChild(wrap); body.scrollTop = body.scrollHeight;
    }
    function visionRead(srcUrl, label, askMulti) {
      var mb = mixedBlocked(); if (mb) { bot(mb); return; }
      var typing = document.createElement('div');
      typing.className = 'cb-msg bot'; typing.textContent = '⋯ 👁️ กำลังอ่านรูป' + (label ? ' (' + label + ')' : '') + '… (โมเดลใหญ่อาจใช้เวลาสักครู่)';
      body.appendChild(typing); body.scrollTop = body.scrollHeight;
      aiReadImage(srcUrl, '')
        .then(function (seen) {
          typing.remove();
          bot('👁️ อ่านจากรูป' + (label ? ' ' + label : '') + ': <i>' + esc(seen).replace(/\n/g, '<br>') + '</i>');
          if (askMulti) {
            var items = String(seen).split(/\n+/).map(function (s) { return s.replace(/^[\s\-\*•·]+/, '').replace(/^\d+[\.\)]\s*/, '').trim(); }).filter(function (s) { return s.length >= 3; });
            if (items.length > 1) { askWhich(items); return; }
          }
          bot(analyzeVision(seen));
        })
        .catch(function (e) {
          typing.remove();
          var em = e && e.message || '';
          if (e && (e.name === 'AbortError' || /abort/i.test(em))) {
            bot('⏱️ อ่านรูปนานเกินไป (หมดเวลา) — โมเดล 35B อ่านรูปใหญ่ช้า· ลอง <b>✂️ วาดวงเฉพาะสินค้าที่อยากถาม</b> (รูปเล็กลง อ่านเร็วขึ้น) หรือลองใหม่อีกครั้ง');
            return;
          }
          var tip = /Failed to fetch|NetworkError|HTTP 0/.test(em)
            ? ' — ตรวจ: vision รันไหม · CORS · https→http (mixed-content)' : '';
          bot('❌ อ่านรูปไม่สำเร็จ (' + esc(em) + ')' + tip);
        });
    }
    function attachPickableImage(dataUrl, q) {
      var wrap = document.createElement('div'); wrap.className = 'cb-msg me'; wrap.style.maxWidth = '92%';
      var box = document.createElement('div'); box.style.cssText = 'position:relative;display:inline-block;line-height:0;';
      var img = document.createElement('img'); img.src = dataUrl; img.alt = 'รูปที่แนบ'; img.style.cssText = 'max-width:100%;border-radius:8px;display:block;';
      var cv = document.createElement('canvas'); cv.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;cursor:crosshair;touch-action:none;';
      box.appendChild(img); box.appendChild(cv);
      var btns = document.createElement('div'); btns.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;';
      btns.innerHTML = '<button class="cb-chip" data-act="full">🔍 อ่านทั้งรูป</button><button class="cb-chip" data-act="crop">✏️ อ่านเฉพาะวง</button>';
      wrap.appendChild(box); wrap.appendChild(btns);
      if (q) { var qd = document.createElement('div'); qd.textContent = q; qd.style.marginTop = '4px'; wrap.appendChild(qd); }
      body.appendChild(wrap); body.scrollTop = body.scrollHeight;

      var ctx = cv.getContext('2d'), sel = null, drag = null;
      function sync() { cv.width = box.clientWidth || img.clientWidth; cv.height = box.clientHeight || img.clientHeight; redraw(); }
      function pos(e) { var r = cv.getBoundingClientRect(), t = e.touches ? e.touches[0] : e; return { x: t.clientX - r.left, y: t.clientY - r.top }; }
      function redraw() {
        ctx.clearRect(0, 0, cv.width, cv.height); if (!sel) return;
        ctx.save(); ctx.strokeStyle = '#F47C20'; ctx.lineWidth = 3; ctx.setLineDash([6, 4]);
        ctx.beginPath(); ctx.ellipse(sel.x + sel.w / 2, sel.y + sel.h / 2, Math.max(1, sel.w / 2), Math.max(1, sel.h / 2), 0, 0, 7); ctx.stroke();
        ctx.fillStyle = 'rgba(244,124,32,.12)'; ctx.fill(); ctx.restore();
      }
      function down(e) { drag = pos(e); sel = { x: drag.x, y: drag.y, w: 0, h: 0 }; if (e.cancelable) e.preventDefault(); }
      function move(e) { if (!drag) return; var p = pos(e); sel = { x: Math.min(drag.x, p.x), y: Math.min(drag.y, p.y), w: Math.abs(p.x - drag.x), h: Math.abs(p.y - drag.y) }; redraw(); if (e.cancelable) e.preventDefault(); }
      function up() { drag = null; }
      cv.addEventListener('mousedown', down); cv.addEventListener('mousemove', move); window.addEventListener('mouseup', up);
      cv.addEventListener('touchstart', down, { passive: false }); cv.addEventListener('touchmove', move, { passive: false }); window.addEventListener('touchend', up);
      if (img.complete && img.naturalWidth) sync(); else img.onload = sync;
      window.addEventListener('resize', sync);
      function cropUrl() {
        if (!sel || sel.w < 8 || sel.h < 8) return null;
        var nw = img.naturalWidth, nh = img.naturalHeight;
        var sx = sel.x / cv.width * nw, sy = sel.y / cv.height * nh, sw = sel.w / cv.width * nw, sh = sel.h / cv.height * nh;
        var pad = 0.08; sx = Math.max(0, sx - sw * pad); sy = Math.max(0, sy - sh * pad); sw = Math.min(nw - sx, sw * (1 + 2 * pad)); sh = Math.min(nh - sy, sh * (1 + 2 * pad));
        var c = document.createElement('canvas'); c.width = Math.max(1, Math.round(sw)); c.height = Math.max(1, Math.round(sh));
        c.getContext('2d').drawImage(img, sx, sy, sw, sh, 0, 0, c.width, c.height);
        return c.toDataURL('image/jpeg', 0.9);
      }
      btns.querySelector('[data-act="full"]').onclick = function () { visionRead(dataUrl, '', true); };
      btns.querySelector('[data-act="crop"]').onclick = function () {
        var cu = cropUrl();
        if (!cu) { bot('วาดวงรอบสิ่งที่อยากถามในรูปก่อนนะครับ แล้วค่อยกด “✏️ อ่านเฉพาะวง” 🐕'); return; }
        msg('<img src="' + cu + '" alt="ส่วนที่วง" style="max-width:160px;border-radius:8px"><div>✏️ ถามเฉพาะส่วนนี้</div>', 'me');
        visionRead(cu, 'เฉพาะวง', false);
      };
      // อ่านทั้งรูปอัตโนมัติ 1 รอบ (ถ้ามีหลายอย่างจะชวนวาดวง)
      visionRead(dataUrl, '', true);
    }

    var fileEl = panel.querySelector('#cbFile');
    panel.querySelector('#cbAttach').onclick = function () { fileEl.click(); };
    fileEl.onchange = function () {
      var f = fileEl.files && fileEl.files[0];
      fileEl.value = '';
      if (!f) return;
      var rd = new FileReader();
      rd.onload = function () {
        var dataUrl = rd.result;
        var q = inp.value.trim(); inp.value = '';
        var cfg = loadCfg();
        if (!(cfg.enabled && cfg.endpoint)) {
          msg('<img src="' + dataUrl + '" alt="รูปที่แนบ" />', 'me');
          bot('ผมรับรูปไว้แล้ว แต่จะอ่านรูปได้ต้องเปิด vision ก่อน — กด ⚙️ ใส่ endpoint ของโมเดลอ่านภาพ (qwen3.6 vision) แล้วแนบรูปใหม่ครับ');
          return;
        }
        attachPickableImage(dataUrl, q);
      };
      rd.readAsDataURL(f);
    };
  }
  function updateSub() {
    var s = panel.querySelector('#cbSub');
    var pre = loadProf().sub || 'ผู้ช่วยราคายาง';
    if (s) s.textContent = loadCfg().enabled ? pre + ' · 🔌 AI local (อ่านรูป) · ตอบจากข้อมูลในชีต' : pre + ' · ตอบจากข้อมูลในชีต';
  }
  function renderChips() {
    var chips = ['ราคา 195R14C', 'เทียบ MK1000 กับ KR', 'ทดแทน 195R14C', 'ขอบ 14 ไม่เกิน 2000', '📊 สรุป', 'มียี่ห้ออะไรบ้าง'];
    if (isAdmin()) chips.push('margin สูงสุด');
    var host = panel.querySelector('#cbChips');
    var hidden = false; try { hidden = localStorage.getItem('xls2_cb_chips_hidden') === '1'; } catch (e) {}
    host.classList.toggle('cb-chips-hidden', hidden);
    host.innerHTML = chips.map(function (c) { return '<button class="cb-chip">' + esc(c) + '</button>'; }).join('') +
      '<button class="cb-chips-x" title="ซ่อนคำแนะนำ">×</button>';
    host.querySelectorAll('.cb-chip').forEach(function (b) {
      b.onclick = function () { inp.value = b.textContent; send(); };
    });
    host.querySelector('.cb-chips-x').onclick = function () {
      host.classList.add('cb-chips-hidden');
      try { localStorage.setItem('xls2_cb_chips_hidden', '1'); } catch (e) {}
    };
  }
  function applyAdminGate() {
    if (!panel) return;
    var admin = isAdmin();
    var gear = panel.querySelector('.cb-gear');
    if (gear) gear.style.display = admin ? '' : 'none';
    if (!admin) { var cfg = panel.querySelector('#cbCfg'); if (cfg) cfg.classList.remove('open'); }   // user เปิดแผงตั้งค่าไม่ได้
  }
  try { window.addEventListener('sg-mode', function () { applyAdminGate(); }); } catch (e) {}
  function toggle(o) {
    open = o;
    panel.classList.toggle('open', o);
    if (o) { applyAdminGate(); renderChips(); try { window.dispatchEvent(new Event('cb-open')); } catch (e) {} setTimeout(function () { inp.focus(); }, 60); }
  }
  function msg(html, who) {
    var d = document.createElement('div');
    d.className = 'cb-msg ' + who;
    d.innerHTML = html;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
  }
  function bot(html) { msg(particleize(html), 'bot'); }

  // 📦 สต็อก/DOT — ดึงจาก DBX (ชั้นกลางฐานข้อมูล · มี mock ใช้ได้เลย) แบบ async
  function tryStockDot(q) {
    var ql = q.toLowerCase();
    if (!/สต็อก|สตอก|ของเหลือ|คงเหลือ|เหลือกี่|มีกี่|กี่เส้น|กี่ลูก|สต๊อก|\bdot\b|ปีไหน|ปีอะไร|ปีผลิต|ดอท/i.test(ql)) return false;
    if (!window.DBX || !DBX.search) { bot('ฟีเจอร์สต็อก/DOT ต้องเชื่อมฐานข้อมูลก่อนครับ (ยังไม่มีโมดูล DBX)'); return true; }
    var wantDot = /\bdot\b|ปีไหน|ปีอะไร|ปีผลิต|ดอท/i.test(ql);
    // ดึงคำค้น: ตัดคำสั่ง/คำถามออก เหลือ ขนาด/รุ่น/ยี่ห้อ
    var term = q.replace(/สต็อก|สตอก|สต๊อก|ของเหลือ|คงเหลือ|เหลือกี่|มีกี่|กี่เส้น|กี่ลูก|เส้น|ลูก|dot|ปีไหน|ปีอะไร|ปีผลิต|ดอท|ของ|ราคา|เช็ก|เช็ค|ดู|หน่อย|ครับ|ค่ะ|คะ|\?/gi, ' ').replace(/\s+/g, ' ').trim();
    if (term.length < 2) { bot('บอกขนาด/รุ่นที่จะเช็ก' + (wantDot ? ' DOT' : 'สต็อก') + 'ด้วยครับ เช่น “' + (wantDot ? 'DOT 195R14C' : 'สต็อก 195R14C') + '”'); return true; }
    var typing = document.createElement('div');
    typing.className = 'cb-msg bot'; typing.textContent = '⋯ 📦 กำลังเช็ก' + (wantDot ? ' DOT' : 'สต็อก') + '…';
    body.appendChild(typing); body.scrollTop = body.scrollHeight;
    DBX.search({ q: term }).then(function (list) {
      if (!list || !list.length) { typing.remove(); bot('ไม่พบสินค้า “' + esc(term) + '” ในฐานข้อมูลครับ'); return; }
      var codes = list.slice(0, 8).map(function (x) { return x.code13; });
      return DBX.batchClean(codes).then(function (cl) {
        typing.remove();
        cl = (cl || []).filter(Boolean);
        if (!cl.length) { bot('ไม่พบรายละเอียดสินค้าครับ'); return; }
        var lines = cl.slice(0, 6).map(function (p) {
          var label = (p.size || '') + (p.model ? ' ' + p.model : '');
          if (!label.trim()) label = p.name || p.code13 || '';
          var head = '<b>' + esc(label) + '</b>' + (p.brandCode || p.brandName ? ' ' + esc(p.brandCode || p.brandName) : '');
          if (wantDot) {
            if (window.DOT && DOT.needsWithdraw && DOT.needsWithdraw(p)) return head + '<br>&nbsp;&nbsp;⚠️ ต้องเบิก (ไม่ระบุ DOT)';
            var ys = (window.DOT && DOT.inStockYears) ? DOT.inStockYears(p) : [];
            var df = (window.DOT && DOT.hasDF) ? DOT.hasDF(p) : false;
            var dotTxt = ys.length ? ('ปี ' + ys.map(function (y) { return 'DOT' + y; }).join(', ')) : (df ? 'มี DF' : 'หมดสต็อก');
            return head + '<br>&nbsp;&nbsp;🗓️ ' + dotTxt + (df && ys.length ? ' · มี DF' : '');
          }
          var avail = p.qtyAvailable != null ? p.qtyAvailable : ((p.qtyOnHand || 0) - (p.qtyReserved || 0));
          var unit = p.unit || 'เส้น';
          var note = (p.qtyReserved ? ' <span style="color:#9a8;font-size:.9em">(จอง ' + p.qtyReserved + ')</span>' : '') +
            (p.incoming ? ' <span style="color:#1d6f9e;font-size:.9em">· กำลังเข้า ' + p.incoming + '</span>' : '');
          return head + '<br>&nbsp;&nbsp;📦 คงเหลือ <b>' + avail + '</b> ' + unit + note + (avail <= 0 ? ' <span style="color:#c0392b">⚠️ หมด</span>' : '');
        });
        bot((wantDot ? '🗓️ DOT' : '📦 สต็อก') + ' “' + esc(term) + '”:<br>' + lines.join('<br>') + (cl.length > 6 ? '<br>…และอีก ' + (cl.length - 6) + ' รายการ' : ''));
      });
    }).catch(function (e) { typing.remove(); bot('เช็กไม่สำเร็จ (' + esc(e && e.message || '') + ')'); });
    return true;
  }
  function send() {
    var q = inp.value.trim(); if (!q) return;
    msg(esc(q), 'me');
    inp.value = '';
    // คำถามข้อความ → ใช้สมองกฎในตัวเสมอ (AI local สงวนไว้สำหรับ "อ่านรูป" เท่านั้น)
    setTimeout(function () {
      try { if (tryStockDot(q)) return; bot(answer(q)); } catch (e) { bot('ขออภัย มีข้อผิดพลาดครับ'); }
    }, 220);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
