/* product-info.js — ข้อมูลสินค้าต่อ "ขนาด": ชนิดสินค้า + ความสูง/กว้าง (ยาง) + ฟิลด์เฉพาะชนิด + ชื่อเรียกหลายแบบ (alias)
   โหลดก่อน sheet-grid.js (sheet-grid เรียกผ่าน window.ProductInfo) · เปิด global: window.ProductInfo
   ────────────────────────────────────────────────────────────────────────
   หลักการ:
   • โปรแกรมคำนวณเอง (เมตริก/บอลลูน/ยางเกษตรนิ้วมาตรฐาน) → ถ้าไม่มั่นใจ/ไม่รู้ = ให้แอดมินกรอกเอง
   • ชนิดสินค้าขยายได้ (TYPES) — เพิ่มชนิดใหม่ในอนาคตได้ที่เดียว
   • ยาง 1 เส้นเรียกได้หลายชื่อ (alias) → ผูกชื่อเข้าหากัน ใช้ค่าชุดเดียวกัน
   • เก็บใน localStorage (per-device) · ออกแบบให้ sync ขึ้น Worker ได้ภายหลัง
   API:
     ProductInfo.get(sizeText)          → { name, type, typeDef, dims:{hCm,wCm}, approx, fields, aliases, complete }
     ProductInfo.isComplete(sizeText)   → ข้อมูลครบ (ใช้ติดจุดเขียว)
     ProductInfo.setType(name, type) / setDims(name,hCm,wCm) / setField(name,key,val) / linkAlias(name, otherName) / unlink(name)
     ProductInfo.showPopup(sizeText, anchorEl, opts{isAdmin,onChange})
     ProductInfo.TYPES
*/
(function () {
  'use strict';
  var LSK = 'xls2_productinfo';

  // ── ชนิดสินค้า (ขยายได้) ──
  var TYPES = {
    tire:    { label: 'ยาง', icon: '🛞', dims: true, fields: [] },
    tube:    { label: 'ยางใน', icon: '⭕', dims: false, fields: [{ k: 'forSize', label: 'ใช้กับยางขนาด' }, { k: 'valve', label: 'วาล์ว (TR…)' }, { k: 'weight', label: 'น้ำหนัก (กก.)' }] },
    flap:    { label: 'ยางรอง (รองขอบ)', icon: '🔘', dims: false, fields: [{ k: 'forRim', label: 'สำหรับขอบ (นิ้ว)' }, { k: 'thick', label: 'ความหนา (มม.)' }, { k: 'weight', label: 'น้ำหนัก (กก.)' }] },
    wheel:   { label: 'กระทะ (ล้อ)', icon: '⚙️', dims: false, fields: [{ k: 'rim', label: 'ขอบ (นิ้ว)' }, { k: 'width', label: 'กว้าง (J)' }, { k: 'pcd', label: 'รู/PCD' }, { k: 'offset', label: 'ออฟเซ็ต (ET)' }, { k: 'weight', label: 'น้ำหนัก (กก.)' }] },
    trim:    { label: 'คิ้ว', icon: '✨', dims: false, fields: [{ k: 'forRim', label: 'ใช้กับขอบ (นิ้ว)' }, { k: 'material', label: 'วัสดุ/สี' }] },
    battery: { label: 'แบตเตอรี่', icon: '🔋', dims: false, fields: [{ k: 'ah', label: 'ความจุ (Ah)' }, { k: 'cca', label: 'CCA' }, { k: 'volt', label: 'แรงดัน (V)' }, { k: 'terminal', label: 'ขั้ว' }, { k: 'weight', label: 'น้ำหนัก (กก.)' }] },
    oil:     { label: 'น้ำมันหล่อลื่น', icon: '🛢️', dims: false, fields: [{ k: 'sae', label: 'เบอร์ (SAE)' }, { k: 'volume', label: 'ปริมาตร (ลิตร)' }, { k: 'api', label: 'มาตรฐาน (API)' }, { k: 'kind', label: 'ชนิด' }] },
    other:   { label: 'อื่นๆ', icon: '📦', dims: false, fields: [], freeform: true }
  };
  var TYPE_ORDER = ['tire', 'tube', 'flap', 'wheel', 'trim', 'battery', 'oil', 'other'];

  // ── ตารางแปลงยางเกษตรนิ้ว → หน้ายางเมตริก (มาตรฐาน R-1 ซีรีส์ 85) — ค่าที่มั่นใจ ──
  var INCH2METRIC = { 9.5: 240, 11.2: 280, 12.4: 320, 13.6: 340, 14.9: 380, 16.9: 420, 18.4: 460, 20.8: 520, 23.1: 580 };
  // ── ชื่อเรียกเก่า ↔ ใหม่ ของยางเส้นเดียวกัน (seed — แอดมินเพิ่มเองได้) ──
  var SEED_ALIAS = { '15-30': '18.4-30', '14-30': '16.9-30', '13-28': '14.9-28', '12-28': '13.6-28', '12-38': '13.6-38', '11-38': '12.4-38' };

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function load() { try { var o = JSON.parse(localStorage.getItem(LSK) || '{}'); o.type = o.type || {}; o.dims = o.dims || {}; o.fields = o.fields || {}; o.alias = o.alias || {}; o.customTypes = o.customTypes || {}; if (o.sourceMode !== 'database') o.sourceMode = 'manual'; return o; } catch (e) { return { type: {}, dims: {}, fields: {}, alias: {}, customTypes: {}, sourceMode: 'manual' }; } }
  function save(o) { try { localStorage.setItem(LSK, JSON.stringify(o)); } catch (e) {} }
  var store = load();
  // ชนิดสินค้า = ในตัว + ที่แอดมินเพิ่มเอง (ขยายได้)
  function allTypes() { var t = {}; Object.keys(TYPES).forEach(function (k) { t[k] = TYPES[k]; }); Object.keys(store.customTypes || {}).forEach(function (id) { t[id] = store.customTypes[id]; }); return t; }
  function typeOrder() { return TYPE_ORDER.concat(Object.keys(store.customTypes || {})); }
  function addType(label, icon, fieldLabels) {
    var id = 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 4);
    var fields = (fieldLabels || []).map(function (l, i) { return { k: 'f' + i, label: String(l).trim() }; }).filter(function (f) { return f.label; });
    store.customTypes[id] = { label: String(label || 'ชนิดใหม่').trim(), icon: icon || '📦', fields: fields, freeform: true, custom: true };
    save(store); logChange('addType', store.customTypes[id].label, store.customTypes[id].icon); return id;
  }
  function removeType(id) { var t = store.customTypes[id]; delete store.customTypes[id]; save(store); logChange('delType', (t && t.label) || id, ''); }

  function norm(s) { return String(s == null ? '' : s).trim().replace(/^\(\s*/, '').replace(/\s*\)$/, '').toUpperCase().replace(/\s+/g, ''); }
  function canonical(raw) { var n = norm(raw); return store.alias[n] || SEED_ALIAS[n] || n; }
  function aliasesOf(name) {
    var out = [];
    Object.keys(store.alias).forEach(function (k) { if (store.alias[k] === name && k !== name) out.push(k); });
    Object.keys(SEED_ALIAS).forEach(function (k) { if (SEED_ALIAS[k] === name && out.indexOf(k) < 0) out.push(k); });
    return out;
  }

  // คำนวณความสูง(เส้นผ่าศูนย์กลาง)+หน้ากว้าง จากชื่อขนาด → {hCm,wCm,approx,src} หรือ null
  function computeDims(raw) {
    var s = norm(raw);
    var m;
    // เมตริกมีซีรีส์: 460/85R30, 320/85-24, 205/75R14
    if ((m = /^(\d{2,3})\/(\d{2,3})[R-](\d{2}(?:\.\d)?)/.exec(s))) {
      var w = +m[1], ar = +m[2], rim = parseFloat(m[3]); return { hCm: (rim * 25.4 + 2 * w * ar / 100) / 10, wCm: w / 10, src: 'metric' };
    }
    // เมตริกไม่มีซีรีส์ (ตู้/กระบะ C): 195R14C, 205R16C → อนุมานซีรีส์ 80
    if ((m = /^(\d{3})R(\d{2}(?:\.\d)?)C?$/.exec(s))) {
      var w2 = +m[1], rim2 = parseFloat(m[2]); return { hCm: (rim2 * 25.4 + 2 * w2 * 0.8) / 10, wCm: w2 / 10, src: 'metric~80', approx: true };
    }
    // บอลลูน/ออฟโรด: 31X10.5R15, 33X12.5-15
    if ((m = /^(\d{2}(?:\.\d+)?)X(\d{1,2}(?:\.\d+)?)[R-]?(\d{2}(?:\.\d)?)/.exec(s))) {
      return { hCm: parseFloat(m[1]) * 2.54, wCm: parseFloat(m[2]) * 2.54, src: 'flotation' };
    }
    // ยางเกษตรนิ้ว: 18.4-30, 16.9R28, 11.2/12.4-24 (เอาหน้ายางตัวแรก)
    if ((m = /^(\d{1,2}(?:\.\d)?)(?:\/\d{1,2}(?:\.\d)?)*[R-](\d{2}(?:\.\d)?)$/.exec(s))) {
      var iw = parseFloat(m[1]), rim3 = parseFloat(m[2]), mw = INCH2METRIC[iw];
      if (mw) return { hCm: (rim3 * 25.4 + 2 * mw * 0.85) / 10, wCm: mw / 10, src: 'ag-inch' };
      return null;   // นอกตารางมาตรฐาน → ไม่เดา ให้แอดมินกรอก
    }
    return null;   // บรรทุกนิ้ว/โฟล์คลิฟต์/OTR/อื่นๆ → ให้แอดมินกรอกเอง
  }

  function get(raw) {
    var name = canonical(raw), type = store.type[name] || 'tire', TY = allTypes(), td = TY[type] || TY.other;
    var info = { name: name, raw: raw, type: type, typeDef: td, aliases: aliasesOf(name) };
    if (td.dims) {
      var ov = store.dims[name];
      if (ov && ov.hCm != null) { info.dims = ov; info.dimSource = 'manual'; info.complete = true; }
      else { var c = computeDims(name); if (c) { info.dims = { hCm: c.hCm, wCm: c.wCm }; info.dimSource = c.src; info.approx = !!c.approx; info.complete = !c.approx; } else { info.complete = false; } }
    } else {
      info.fields = store.fields[name] || {};
      var req = td.fields || [];
      info.complete = req.length ? req.some(function (f) { return String(info.fields[f.k] || '').trim() !== ''; }) : true;
    }
    return info;
  }
  function isComplete(raw) { try { return !!get(raw).complete; } catch (e) { return false; } }

  // 🕘 บันทึกประวัติการแก้ไขชนิดสินค้า (ใคร/เมื่อไร/ทำอะไร) — เก็บล่าสุด 120 รายการ
  function whoBy() { try { return (window.Auth && Auth.currentUser && Auth.currentUser()) || 'admin'; } catch (e) { return 'admin'; } }
  function logChange(action, name, detail) {
    store.history = store.history || [];
    store.history.unshift({ t: Date.now(), by: whoBy(), action: action, name: name, detail: detail || '' });
    if (store.history.length > 120) store.history = store.history.slice(0, 120);
    save(store);
  }
  function getHistory() { return (store.history || []).slice(); }
  function clearHistory() { store.history = []; save(store); }

  function setType(raw, type) { var n = canonical(raw); if (type === 'tire') delete store.type[n]; else store.type[n] = type; save(store); logChange('type', n, type); }
  function setDims(raw, hCm, wCm) { var n = canonical(raw); if (hCm == null || hCm === '') delete store.dims[n]; else store.dims[n] = { hCm: +hCm, wCm: (wCm === '' || wCm == null) ? null : +wCm }; save(store); logChange('dims', n, (hCm == null || hCm === '') ? 'ลบ' : (hCm + (wCm ? '×' + wCm : '') + ' ซม.')); }
  function setField(raw, key, val) { var n = canonical(raw); store.fields[n] = store.fields[n] || {}; if (val === '' || val == null) delete store.fields[n][key]; else store.fields[n][key] = val; save(store); logChange('field', n, key + '=' + (val || '—')); }
  function linkAlias(raw, otherRaw) { var canon = canonical(raw), other = norm(otherRaw); if (other && other !== canon) { store.alias[other] = canon; save(store); logChange('alias', canon, '+ ' + other); } }
  function unlink(raw) { var n = norm(raw); delete store.alias[n]; save(store); logChange('alias', n, 'ลบชื่อเรียก'); }

  // ════════════ CSS ════════════
  function injectCss() {
    if (document.getElementById('pi-css')) return;
    var s = document.createElement('style'); s.id = 'pi-css';
    s.textContent =
      '.pi-pop{position:fixed;z-index:9600;border:1.5px solid #F47C20;border-radius:13px;box-shadow:0 12px 34px rgba(0,0,0,.26);padding:13px 15px;font-family:Arial,Tahoma,sans-serif;min-width:210px;max-width:300px;background:#fff;}' +
      'body.dark .pi-pop{background:#2a2a2a;color:#eee;}' +
      '.pi-ttl{font:800 14px/1.2 inherit;color:#C75B00;display:flex;align-items:center;gap:6px;margin-bottom:3px;}' +
      '.pi-alias{font-size:11px;color:#9a8d80;margin-bottom:8px;}' +
      '.pi-lab{font-size:11px;color:#999;margin:7px 0 2px;}' +
      '.pi-pair{display:flex;gap:13px;align-items:baseline;}' +
      '.pi-num{font:800 19px/1 inherit;} body.dark .pi-num{color:#f0f0f0;} .pi-unit{font-size:12px;color:#888;}' +
      '.pi-frow{display:flex;justify-content:space-between;gap:10px;font-size:13px;padding:3px 0;border-bottom:1px dashed #eee;}' +
      'body.dark .pi-frow{border-color:#3a3a3a;} .pi-fk{color:#888;} .pi-fv{font-weight:700;}' +
      '.pi-note{font-size:10.5px;color:#bbb;margin-top:8px;}' +
      '.pi-srcmode{margin-top:9px;padding-top:8px;border-top:1px dashed #e3ddd6;font-size:11.5px;color:#888;}' +
      '.pi-srcmode a{color:#75695e;text-decoration:none;padding:2px 7px;border:1px solid #e3ddd6;border-radius:7px;margin-right:3px;}' +
      '.pi-srcmode a.on{background:#F47C20;color:#fff;border-color:#F47C20;font-weight:700;}' +
      'body.dark .pi-srcmode{border-color:#3a3a3a;} body.dark .pi-srcmode a{color:#ccc;border-color:#555;}' +
      '.pi-empty{font-size:12.5px;color:#aaa;padding:6px 0;}' +
      '.pi-row{display:flex;gap:6px;margin-top:9px;flex-wrap:wrap;}' +
      '.pi-btn{height:30px;padding:0 11px;border:1px solid #e3ddd6;border-radius:8px;background:#f6f3f0;font:600 12px/1 inherit;color:#75695e;cursor:pointer;}' +
      '.pi-btn.pri{background:#F47C20;color:#fff;border:none;}' +
      '.pi-in{width:100%;height:34px;border:1px solid #cfcfcf;border-radius:8px;padding:0 10px;font:inherit;font-size:13px;box-sizing:border-box;margin-top:4px;background:inherit;color:inherit;}' +
      '.pi-sel{width:100%;height:34px;border:1px solid #cfcfcf;border-radius:8px;font:inherit;font-size:13px;margin-top:4px;background:inherit;color:inherit;}' +
      '.pi-ed{margin-top:8px;}.pi-ed label{display:block;font-size:11px;color:#999;margin-top:6px;}' +
      '.pi-ttl{cursor:move;}.pi-chips{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:7px;}.pi-chip{font-size:12px;background:#FFF3E6;border:1px solid #F0B380;color:#C75B00;border-radius:7px;padding:2px 8px;}.pi-chip a{color:#C0392B;text-decoration:none;margin-left:3px;font-weight:700;}';
    document.head.appendChild(s);
  }

  var popEl = null;
  function close() { if (popEl) { popEl.style.display = 'none'; if (window.PopupStack) PopupStack.remove(popEl); } }
  function pairHtml(cmv, inv) {
    return '<div class="pi-pair"><div><span class="pi-num">' + cmv + '</span> <span class="pi-unit">ซม.</span></div><div style="color:#ccc;">·</div><div><span class="pi-num">' + inv + '</span> <span class="pi-unit">นิ้ว</span></div></div>';
  }

  // ════════════ ป๊อปอัปแสดงผล (ปรับตามชนิด) ════════════
  function showPopup(raw, anchor, opts) {
    opts = opts || {}; injectCss();
    if (!popEl) {
      popEl = document.createElement('div'); popEl.className = 'pi-pop'; popEl.tabIndex = -1; document.body.appendChild(popEl);
      popEl.addEventListener('mousedown', function (e) {   // ลากหัวป๊อปเพื่อย้ายตำแหน่ง
        var t = e.target.closest('.pi-ttl'); if (!t || e.target.closest('a,button,input,select')) return;
        e.preventDefault();
        var sx = e.clientX, sy = e.clientY, ol = parseFloat(popEl.style.left) || 0, ot = parseFloat(popEl.style.top) || 0;
        function mv(ev) { popEl.style.left = Math.max(0, Math.min(ol + ev.clientX - sx, window.innerWidth - popEl.offsetWidth)) + 'px'; popEl.style.top = Math.max(0, Math.min(ot + ev.clientY - sy, window.innerHeight - popEl.offsetHeight)) + 'px'; }
        function up() { document.removeEventListener('mousemove', mv, true); document.removeEventListener('mouseup', up, true); }
        document.addEventListener('mousemove', mv, true); document.addEventListener('mouseup', up, true);
      });
      popEl.onkeydown = function (e) {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); return; }   // ESC = ปิดหน้าต่าง
        if (e.key === 'Enter') {
          var ins = [].slice.call(popEl.querySelectorAll('.pi-in, .pi-sel'));
          var i = ins.indexOf(document.activeElement);
          if (i >= 0 && i < ins.length - 1) { e.preventDefault(); var nx = ins[i + 1]; nx.focus(); if (nx.select) nx.select(); return; }   // Enter = เลื่อนช่องถัดไป
          var btn = popEl.querySelector('#piSave') || popEl.querySelector('#piAliasOk') || popEl.querySelector('#piTypeOk');
          if (btn) { e.preventDefault(); btn.click(); }   // Enter ช่องสุดท้าย = ผูก/บันทึก
        }
      };
    }
    render(raw, opts);
    popEl.style.display = 'block';
    var rc = anchor.getBoundingClientRect();
    popEl.style.left = Math.max(8, Math.min(rc.right + 6, window.innerWidth - popEl.offsetWidth - 12)) + 'px';
    popEl.style.top = Math.max(8, Math.min(rc.top, window.innerHeight - popEl.offsetHeight - 12)) + 'px';
    if (window.PopupStack) PopupStack.push(popEl, close);
  }

  function render(raw, opts, mode) {
    var info = get(raw), td = info.typeDef, isAdmin = !!opts.isAdmin;
    var aliasLine = info.aliases.length ? '<div class="pi-alias">เรียกอีกชื่อ: ' + info.aliases.map(esc).join(' · ') + '</div>' : '';
    var head = '<div class="pi-ttl">' + td.icon + ' ' + esc(info.name) + (info.complete ? ' <span style="color:#1F8A4C;">●</span>' : '') + '</div>' + aliasLine;
    var body = '';

    if (mode === 'editType') {
      var curCustom = allTypes()[info.type] && allTypes()[info.type].custom;
      body = '<div class="pi-lab">ชนิดสินค้า</div><select class="pi-sel" id="piType">' +
        typeOrder().map(function (t) { var TT = allTypes()[t]; return '<option value="' + t + '"' + (t === info.type ? ' selected' : '') + '>' + TT.icon + ' ' + esc(TT.label) + '</option>'; }).join('') +
        '<option value="__add__">➕ เพิ่มชนิดใหม่…</option></select>' +
        '<div id="piNewType" style="display:none;margin-top:8px;">' +
          '<label>ไอคอน + ชื่อชนิด</label>' +
          '<div style="display:flex;gap:6px;"><input class="pi-in" id="piNTIcon" value="📦" style="width:46px;text-align:center;" maxlength="2"><input class="pi-in" id="piNTLabel" placeholder="เช่น ไส้กรอง / หัวเทียน" style="flex:1;"></div>' +
          '<label>ช่องข้อมูล (คั่นด้วย ,)</label>' +
          '<input class="pi-in" id="piNTFields" placeholder="เช่น ขนาด, วัสดุ, สี">' +
          '<div class="pi-note">สร้างแล้วใช้ซ้ำได้กับทุกสินค้า · บอตค้นหา/เทียบได้</div>' +
        '</div>' +
        (curCustom ? '<div class="pi-note"><a href="#" id="piDelType" style="color:#c0392b;">🗑 ลบชนิด “' + esc(td.label) + '” (ที่สร้างเอง)</a></div>' : '') +
        (isAdmin ? '<div class="pi-srcmode">แหล่งข้อมูลชนิดสินค้า: ' +
          '<a href="#" id="piSrcManual" class="' + (getSourceMode() === 'manual' ? 'on' : '') + '">⚙️ กำหนดเอง</a> · ' +
          '<a href="#" id="piSrcDb" class="' + (getSourceMode() === 'database' ? 'on' : '') + '">🗄️ ฐานข้อมูล</a>' +
          '<div class="pi-note" style="margin-top:3px;">' + (getSourceMode() === 'database' ? 'ดึงจากส่วนกลาง (server local) — ซิงก์อัตโนมัติ' : 'ใช้ค่าที่กำหนดในเครื่องนี้') + '</div></div>' : '') +
        '<div class="pi-row"><button class="pi-btn pri" id="piTypeOk">ตกลง</button><button class="pi-btn" id="piBack">ยกเลิก</button></div>';
    } else if (mode === 'edit') {
      var ed = '';
      if (td.dims) {
        ed = '<label>ความสูง — เส้นผ่าศูนย์กลางรวม (ซม.)</label><input class="pi-in" id="pi_hCm" inputmode="decimal" value="' + (info.dims && info.dims.hCm != null ? Math.round(info.dims.hCm * 10) / 10 : '') + '">' +
             '<label>หน้ากว้าง (ซม.)</label><input class="pi-in" id="pi_wCm" inputmode="decimal" value="' + (info.dims && info.dims.wCm != null ? Math.round(info.dims.wCm * 10) / 10 : '') + '">';
      } else {
        ed = (td.fields || []).map(function (f) { return '<label>' + esc(f.label) + '</label><input class="pi-in" data-fk="' + f.k + '" value="' + esc((info.fields && info.fields[f.k]) || '') + '">'; }).join('');
        if (td.freeform) ed += '<label>หมายเหตุ</label><input class="pi-in" data-fk="note" value="' + esc((info.fields && info.fields.note) || '') + '">';
        if (!ed) ed = '<div class="pi-empty">ชนิดนี้ยังไม่มีฟิลด์</div>';
      }
      body = '<div class="pi-ed">' + ed + '</div><div class="pi-row"><button class="pi-btn pri" id="piSave">บันทึก</button><button class="pi-btn" id="piBack">ยกเลิก</button></div>';
    } else if (mode === 'alias') {
      var chips = info.aliases.length ? '<div class="pi-chips">' + info.aliases.map(function (a) { return '<span class="pi-chip">' + esc(a) + ' <a href="#" data-unalias="' + esc(a) + '">✕</a></span>'; }).join('') + '</div>' : '<div class="pi-empty">ยังไม่มีชื่อเรียกอื่น</div>';
      body = '<div class="pi-lab">ชื่อเรียกอื่นของยางเส้นนี้ (เพิ่มได้หลายชื่อ 2-3 ชื่อ)</div>' + chips +
        '<input class="pi-in" id="piAlias" placeholder="พิมพ์ชื่อแล้วกด Enter · เช่น 15-30">' +
        '<div class="pi-row"><button class="pi-btn pri" id="piAliasOk">➕ เพิ่มชื่อ</button><button class="pi-btn" id="piBack">เสร็จ</button></div>';
    } else {
      // ── มุมมองปกติ ──
      if (td.dims) {
        if (info.dims) {
          var cm = Math.round(info.dims.hCm * 10) / 10, inch = Math.round(info.dims.hCm / 2.54 * 10) / 10;
          body += '<div class="pi-lab">ความสูง (เส้นผ่าศูนย์กลางรวม)</div>' + pairHtml(cm, inch);
          if (info.dims.wCm != null) { var wc = Math.round(info.dims.wCm * 10) / 10, wi = Math.round(info.dims.wCm / 2.54 * 10) / 10; body += '<div class="pi-lab">หน้ากว้าง</div>' + pairHtml(wc, wi); }
          var srcNote = info.dimSource === 'manual' ? 'จากค่าที่กรอกไว้' : info.approx ? '≈ ประมาณ (โปรดยืนยัน)' : 'คำนวณจากขนาด';
          body += '<div class="pi-note">' + srcNote + '</div>';
        } else {
          body += '<div class="pi-empty">⚠️ ยังไม่มีข้อมูลความสูง/กว้างของขนาดนี้' + (isAdmin ? ' — กด “ใส่ค่า”' : ' — แจ้งแอดมิน') + '</div>';
        }
      } else {
        var rows = (td.fields || []).map(function (f) { var v = info.fields && info.fields[f.k]; return v ? '<div class="pi-frow"><span class="pi-fk">' + esc(f.label) + '</span><span class="pi-fv">' + esc(v) + '</span></div>' : ''; }).join('');
        if (td.freeform && info.fields && info.fields.note) rows += '<div class="pi-frow"><span class="pi-fk">หมายเหตุ</span><span class="pi-fv">' + esc(info.fields.note) + '</span></div>';
        body += '<div class="pi-lab">' + esc(td.label) + '</div>' + (rows || '<div class="pi-empty">ยังไม่มีรายละเอียด' + (isAdmin ? ' — กด “ใส่ค่า”' : '') + '</div>');
      }
      if (isAdmin) {
        body += '<div class="pi-row">' +
          '<button class="pi-btn pri" id="piEdit">✏️ ใส่ค่า</button>' +
          '<button class="pi-btn" id="piEditType">เปลี่ยนชนิด</button>' +
          (td.dims ? '<button class="pi-btn" id="piAliasBtn">ผูกชื่ออื่น</button>' : '') +
          '</div>';
      }
    }
    popEl.innerHTML = head + body;
    wire(raw, opts, mode);
  }

  function wire(raw, opts, mode) {
    function re(m) { render(raw, opts, m); reposition(); }
    function done() { close(); if (opts.onChange) opts.onChange(); }
    var q = function (id) { return popEl.querySelector(id); };
    if (q('#piBack')) q('#piBack').onclick = function () { re(null); };
    if (q('#piEdit')) q('#piEdit').onclick = function () { re('edit'); };
    if (q('#piEditType')) q('#piEditType').onclick = function () { re('editType'); };
    if (q('#piAliasBtn')) q('#piAliasBtn').onclick = function () { re('alias'); };
    if (q('#piTypeOk')) q('#piTypeOk').onclick = function () {
      var v = q('#piType').value;
      if (v === '__add__') {
        var lab = (q('#piNTLabel').value || '').trim();
        if (!lab) { try { q('#piNTLabel').focus(); } catch (e) {} return; }
        var icon = (q('#piNTIcon').value || '📦').trim() || '📦';
        var flds = (q('#piNTFields').value || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
        var id = addType(lab, icon, flds);
        setType(raw, id);
      } else { setType(raw, v); }
      re(null); done();
    };
    if (q('#piType')) q('#piType').onchange = function () {
      var nt = q('#piNewType'); if (nt) nt.style.display = (q('#piType').value === '__add__') ? 'block' : 'none';
      var dt = q('#piDelType'); if (dt) dt.parentNode.style.display = (q('#piType').value === '__add__') ? 'none' : '';
    };
    if (q('#piDelType')) q('#piDelType').onclick = function (e) {
      e.preventDefault();
      var info = get(raw);
      if (allTypes()[info.type] && allTypes()[info.type].custom) { removeType(info.type); setType(raw, 'other'); }
      re(null); done();
    };
    if (q('#piSrcManual')) q('#piSrcManual').onclick = function (e) { e.preventDefault(); setSourceMode('manual'); re('editType'); };
    if (q('#piSrcDb')) q('#piSrcDb').onclick = function (e) { e.preventDefault(); setSourceMode('database'); re('editType'); };
    if (q('#piAliasOk')) q('#piAliasOk').onclick = function () { var v = q('#piAlias').value.trim(); if (v) { linkAlias(raw, v); if (opts.onChange) opts.onChange(); } re('alias'); };
    popEl.querySelectorAll('[data-unalias]').forEach(function (a) { a.onclick = function (e) { e.preventDefault(); unlink(a.dataset.unalias); if (opts.onChange) opts.onChange(); re('alias'); }; });
    if (q('#piSave')) q('#piSave').onclick = function () {
      var info = get(raw), td = info.typeDef;
      if (td.dims) { setDims(raw, q('#pi_hCm').value.trim(), q('#pi_wCm').value.trim()); }
      else { popEl.querySelectorAll('[data-fk]').forEach(function (inp) { setField(raw, inp.dataset.fk, inp.value.trim()); }); }
      re(null); done();
    };
    var firstIn = popEl.querySelector('.pi-in, .pi-sel');
    if (mode && firstIn) { setTimeout(function () { try { firstIn.focus(); if (firstIn.select) firstIn.select(); } catch (e) {} }, 20); }
    else if (!opts.noFocus) { try { popEl.focus(); } catch (e) {} }   // มุมมองปกติ → โฟกัสป๊อปอัปให้ ESC ทำงาน (ยกเว้นตอนเลื่อนด้วยลูกศร)
  }
  function reposition() { if (!popEl) return; var r = popEl.getBoundingClientRect(); if (r.bottom > window.innerHeight - 8) popEl.style.top = Math.max(8, window.innerHeight - popEl.offsetHeight - 12) + 'px'; }

  // แหล่งข้อมูลชนิดสินค้า: 'manual' = กำหนดเองในเครื่อง · 'database' = ดึงจากส่วนกลาง (server local)
  function getSourceMode() { return store.sourceMode === 'database' ? 'database' : 'manual'; }
  function setSourceMode(m) {
    store.sourceMode = (m === 'database') ? 'database' : 'manual'; save(store);
    if (store.sourceMode === 'database') { try { sessionStorage.removeItem('xls2_prodinfo_pulled'); } catch (e) {} syncPull().then(function (ok) { if (ok && window.SG && SG.render) SG.render(); }); }
    return store.sourceMode;
  }
  function exportData() { return { type: store.type, dims: store.dims, fields: store.fields, alias: store.alias, customTypes: store.customTypes }; }
  function importData(d, mode) {
    if (!d) return;
    var KEYS = ['type', 'dims', 'fields', 'alias', 'customTypes'];
    if (mode === true || mode === 'replace') {
      // ทับทั้งหมดด้วยของ server
      store.type = d.type || {}; store.dims = d.dims || {}; store.fields = d.fields || {}; store.alias = d.alias || {}; store.customTypes = d.customTypes || {};
    } else if (mode === 'override') {
      // server ชนะรายคีย์ (ทับค่าเดิม) แต่ยังเก็บคีย์ที่มีเฉพาะในเครื่อง — ใช้ตอน database mode
      KEYS.forEach(function (k) { var r = d[k] || {}; store[k] = store[k] || {}; Object.keys(r).forEach(function (n) { store[k][n] = r[n]; }); });
    } else {
      // เติมเฉพาะที่ว่าง (ของเครื่องมาก่อน) — ใช้ตอน manual mode
      KEYS.forEach(function (k) { var r = d[k] || {}; store[k] = store[k] || {}; Object.keys(r).forEach(function (n) { if (store[k][n] == null) store[k][n] = r[n]; }); });
    }
    save(store);
  }
  function listKnown() { var s = {}; ['type', 'dims', 'fields', 'alias'].forEach(function (k) { Object.keys(store[k]).forEach(function (n) { s[n] = 1; }); }); return Object.keys(s); }
  function syncPull() {
    if (!window.Registry || !Registry.prodInfoGet) return Promise.resolve(false);
    var override = getSourceMode() === 'database';
    return Registry.prodInfoGet().then(function (res) {
      if (res && res.ok && res.data) { importData(res.data, override ? 'override' : false); return true; }
      return false;
    }).catch(function () { return false; });
  }
  function syncPush(adminKey, by) { if (!window.Registry || !Registry.prodInfoSet) return Promise.resolve({ error: 'ไม่มีโมดูล Registry' }); return Registry.prodInfoSet(adminKey, exportData(), by); }

  window.ProductInfo = {
    TYPES: TYPES, TYPE_ORDER: TYPE_ORDER, getTypes: allTypes, getTypeOrder: typeOrder, addType: addType, removeType: removeType, get: get, isComplete: isComplete, computeDims: computeDims,
    setType: setType, setDims: setDims, setField: setField, linkAlias: linkAlias, unlink: unlink,
    showPopup: showPopup, close: close,
    exportData: exportData, importData: importData, listKnown: listKnown, syncPull: syncPull, syncPush: syncPush,
    getSourceMode: getSourceMode, setSourceMode: setSourceMode,
    getHistory: getHistory, clearHistory: clearHistory
  };

  (function markerCss() {
    if (document.getElementById('pi-marker-css')) return;
    var s = document.createElement('style'); s.id = 'pi-marker-css';
    s.textContent = '.sg-pimark{position:relative;}.sg-pi-done{position:absolute;top:0;right:0;width:0;height:0;border-top:10px solid #1F8A4C;border-left:10px solid transparent;pointer-events:none;z-index:3;}.sg-pi-todo{position:absolute;top:0;right:0;width:0;height:0;border-top:10px solid #F39C12;border-left:10px solid transparent;pointer-events:none;z-index:3;}';
    (document.head || document.documentElement).appendChild(s);
  })();

  // ดึงข้อมูลจากส่วนกลางรอบละครั้งต่อเซสชัน (best-effort · ได้ข้อมูลที่แอดมินแชร์ไว้)
  try {
    if (getSourceMode() === 'database' && !sessionStorage.getItem('xls2_prodinfo_pulled')) {
      sessionStorage.setItem('xls2_prodinfo_pulled', '1');
      setTimeout(function () { syncPull().then(function (ok) { if (ok && window.SG && SG.render) SG.render(); }); }, 1500);
    }
  } catch (e) {}
})();
