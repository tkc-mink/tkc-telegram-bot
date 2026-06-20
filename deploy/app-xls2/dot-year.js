/* ปียาง DOT (ช่วงปี + DF + ลงสีตามอายุ + popup ราคาแยกราย DOT) — โมดูลแยก
   ใช้กับคอลัมน์/ช่องที่ผูกฟิลด์ DB 'dotRange' · เปิด global: window.DOT
   กติกาการแสดงในช่อง:
   • ปี DOT = 2 หลัก ไม่เกินปีปัจจุบัน (ปีอนาคต/ทศนิยม = ตัดทิ้ง)
   • แสดงช่วง min-max ของปีที่ "มีของในสต๊อก" (qty>0) · DF (ยางเกิด deflect) = แสดงนำหน้า "DF-…"
   • สินค้าต้องเบิก (needsWithdraw) → ไม่แสดง DOT
   • สินค้าหมด: ถ้าปีล่าสุดที่เคยเข้า = ปีปัจจุบัน → แสดงปีปัจจุบัน · ถ้าเป็นปีเก่า → แสดง "-"
   popup ราคาแยกราย DOT:
   • คลิกช่อง DOT ที่มี > 1 ชุด (DF นับเป็น 1) → ตารางแสดงจำนวนเส้น + ราคา ขาย/B/A/S แต่ละ DOT
   • แอดมินกรอกเป็นตัวเลข (ดึงราคาแถวหลักมาตั้งต้น) · ผู้ใช้เห็นเป็นโค้ดราคา (cipher #2)
   • เก็บใน local เท่านั้น (ไม่เขียนกลับ DB) · ชุดที่ขายหมด (qty 0) ไม่แสดง
   • ปรับสีได้ใน ตั้งค่า → แท็บ "สีปี DOT" */
(function () {
  var DEF = { newc: '000000', y1: '1F8A5B', y2: 'E5322E', flag: 'F1C40F', sep: '000000', pRetail: '1A5FB4', pB: '1A5FB4', pA: '1A5FB4', pS: '1A5FB4', popBg: '', popFg: '' };
  var LSK = { newc: 'xls2_dotcol_new', y1: 'xls2_dotcol_1y', y2: 'xls2_dotcol_2y', flag: 'xls2_dotcol_flag', sep: 'xls2_dotcol_sep', pRetail: 'xls2_dotcol_pretail', pB: 'xls2_dotcol_pb', pA: 'xls2_dotcol_pa', pS: 'xls2_dotcol_ps', popBg: 'xls2_popbg', popFg: 'xls2_popfg' };
  var PCOL = { retail: 'pRetail', b: 'pB', a: 'pA', s: 'pS' };
  var PRICE_LS = 'xls2_dotprices';                       // { code13: { dotKey: {retail,b,a,s} } }

  function get(which) { return ((localStorage.getItem(LSK[which]) || '').replace('#', '')) || DEF[which]; }
  function set(which, hex) { try { localStorage.setItem(LSK[which], (hex || '').replace('#', '')); } catch (e) {} }
  function applyPopupColors() {                            // สีพื้นหลัง/ตัวอักษร popup ทุกหน้าต่าง (ไม่ตั้ง = คงเดิม)
    var bg = (localStorage.getItem(LSK.popBg) || '').replace('#', '');
    var fg = (localStorage.getItem(LSK.popFg) || '').replace('#', '');
    var root = document.documentElement, body = document.body;
    if (bg) root.style.setProperty('--pop-bg', '#' + bg); else root.style.removeProperty('--pop-bg');
    if (fg) root.style.setProperty('--pop-fg', '#' + fg); else root.style.removeProperty('--pop-fg');
    if (body) { body.classList.toggle('pop-bg', !!bg); body.classList.toggle('pop-fg', !!fg); }
  }
  function curYY() { return new Date().getFullYear() % 100; }
  function ageOf(yy) { var a = curYY() - yy; if (a < -50) a += 100; if (a > 50) a -= 100; return a; }
  function tierColor(yy) { var a = ageOf(yy); if (a >= 2) return get('y2'); if (a === 1) return get('y1'); return get('newc'); }
  function pad(yy) { yy = ((yy % 100) + 100) % 100; return (yy < 10 ? '0' : '') + yy; }
  function needsWithdraw(p) { return !!(p && p.flags && p.flags.needsWithdraw); }

  // รวม dotWeeks เป็นชุด (batch): แยก DF/ปี · รวม qty · เฉพาะ 2 หลัก ≤ ปีปัจจุบัน
  function allBatches(p) {                               // ทุกชุดที่เคยเข้า (ไม่กรอง qty) — ใช้หา "ปีล่าสุดที่เคยเข้า"
    if (!p || !p.dotWeeks || !p.dotWeeks.length) return [];
    var cy = curYY(), m = {};
    p.dotWeeks.forEach(function (d) {
      var df = !!d.df;
      var y = parseInt(d.dot, 10); if (isNaN(y)) { if (!df) return; y = null; }
      if (y != null) { y = ((y % 100) + 100) % 100; if (y > cy) return; }
      var key = df ? ('DF' + (y != null ? y : '')) : String(y);
      if (!m[key]) m[key] = { key: key, df: df, year: y, qty: 0 };
      m[key].qty += (typeof d.qty === 'number' ? d.qty : (parseInt(d.qty, 10) || 0));
    });
    return Object.keys(m).map(function (k) { return m[k]; });
  }
  function stockBatches(p) { return allBatches(p).filter(function (b) { return b.qty > 0; }); }
  function inStockYears(p) {                             // ปี (ไม่ใช่ DF) ที่มีของ — เรียงน้อย→มาก
    var ys = stockBatches(p).filter(function (b) { return !b.df && b.year != null; }).map(function (b) { return b.year; });
    ys.sort(function (a, b) { return a - b; }); return ys;
  }
  function hasDF(p) { return stockBatches(p).some(function (b) { return b.df; }); }
  function newestEver(p) {                               // ปีล่าสุดที่เคยเข้า (ไม่สน qty)
    var ys = allBatches(p).filter(function (b) { return b.year != null; }).map(function (b) { return b.year; });
    return ys.length ? Math.max.apply(null, ys) : null;
  }

  // ปีที่จะแสดงในช่อง + สถานะ DF + placeholder "-"
  function cellModel(p) {
    if (needsWithdraw(p)) return { hide: true };          // ต้องเบิก → ไม่แสดง DOT
    var stock = stockBatches(p);
    var ys = stock.filter(function (b) { return !b.df && b.year != null; }).map(function (b) { return b.year; }).sort(function (a, b) { return a - b; });
    var dfB = stock.filter(function (b) { return b.df; });
    if (!ys.length && !dfB.length) {                      // หมดสต๊อก
      var ne = newestEver(p);
      if (ne != null && ne === curYY()) return { years: [curYY()], df: false };
      return { dash: true };                              // ปีล่าสุดเป็นปีเก่า → "-"
    }
    if (dfB.length) {                                     // มี DF → แสดง "DF-<ปีของชุด DF>" อย่างเดียว (ไม่แสดงช่วงปีปกติ)
      var dy = dfB.map(function (b) { return b.year; }).filter(function (y) { return y != null; });
      var dfYear = dy.length ? Math.max.apply(null, dy) : (ys.length ? ys[ys.length - 1] : curYY());
      return { df: true, dfYear: dfYear };
    }
    return { years: ys, df: false };
  }

  function rangeText(p) {                                 // ข้อความล้วน (fx/คัดลอก/ค่า)
    var m = cellModel(p); if (m.hide) return ''; if (m.dash) return '-';
    if (m.df) return 'DF-' + pad(m.dfYear);
    var ys = m.years, lo = ys[0], hi = ys[ys.length - 1];
    return (lo === hi) ? pad(hi) : (pad(lo) + '-' + pad(hi));
  }
  function fontSize() { var v = parseInt(localStorage.getItem('xls2_dotfontsize'), 10); return (v >= 6 && v <= 72) ? v : 0; }
  function fontWeight() { var v = parseInt(localStorage.getItem('xls2_dotfontweight'), 10); return (v >= 100 && v <= 900) ? v : 0; }
  function priceWeight() { var v = parseInt(localStorage.getItem('xls2_dotpriceweight'), 10); return (v >= 100 && v <= 900) ? v : 0; }
  function cellHTML(p, darkFn, zoom) {                    // HTML ลงสี (เรนเดอร์ในช่อง)
    var m = cellModel(p); if (m.hide) return '';
    var fw = fontWeight(), fwS = fw > 0 ? ('font-weight:' + fw + ';') : '';
    function col(hex) { return darkFn ? darkFn(hex) : hex; }
    function sep() { return '<span class="dot-sep" style="' + fwS + 'color:#' + col(get('sep')) + '">-</span>'; }
    var inner;
    if (m.dash) inner = sep();
    else {
      var yspan = function (yy) { return '<span class="dot-yr" style="' + fwS + 'color:#' + col(tierColor(yy)) + '">' + pad(yy) + '</span>'; };
      if (m.df) {
        inner = '<span class="dot-flag" style="' + fwS + 'color:#' + col(get('flag')) + '">DF</span>' + sep() + yspan(m.dfYear);
      } else {
        var ys = m.years, lo = ys[0], hi = ys[ys.length - 1];
        inner = (lo === hi) ? yspan(hi) : (yspan(lo) + sep() + yspan(hi));
      }
    }
    var fs = fontSize();
    if (fs > 0) return '<span class="dot-wrap" style="font-size:' + Math.round(fs * (zoom || 1)) + 'px">' + inner + '</span>';
    return inner;
  }

  // ---------- ราคาแยกราย DOT (เก็บ local) ----------
  function priceStore() { try { return JSON.parse(localStorage.getItem(PRICE_LS) || '{}') || {}; } catch (e) { return {}; } }
  function savePriceStore(o) { try { localStorage.setItem(PRICE_LS, JSON.stringify(o)); } catch (e) {} }
  function dotKey(b) { return b.df ? 'DF' : String(b.year); }
  function getPrices(code, b) { var s = priceStore(); return (s[code] && s[code][dotKey(b)]) || null; }
  function setPrices(code, b, vals) {
    var s = priceStore(); s[code] = s[code] || {}; s[code][dotKey(b)] = vals; savePriceStore(s);
    // เก็บกวาดชุดที่ขายหมด (ไม่มีในสต๊อกแล้ว) ออกอัตโนมัติ ทำตอนเปิด popup (ดู popupRows)
  }
  function pruneSold(code, liveKeys) {
    var s = priceStore(); if (!s[code]) return;
    Object.keys(s[code]).forEach(function (k) { if (liveKeys.indexOf(k) < 0) delete s[code][k]; });
    if (!Object.keys(s[code]).length) delete s[code];
    savePriceStore(s);
  }

  // ชุดที่จะแสดงใน popup (เรียงปีใหม่→เก่า · DF อยู่บนสุด · ปีปัจจุบันแสดงเฉพาะเมื่อมี DF)
  function popupRows(p) {
    if (needsWithdraw(p)) return [];
    var cy = curYY(), df = hasDF(p);
    var stock = stockBatches(p);
    var yearMap = {}; stock.forEach(function (b) { if (!b.df && b.year != null) yearMap[b.year] = b.qty; });
    var rows = [];
    if (df) {
      var dfb = stock.filter(function (b) { return b.df; })[0] || { df: true, year: null, qty: 0 };
      rows.push({ df: true, label: 'DF', year: cy, qty: dfb.qty });
      // ปีปัจจุบันหมด → ไม่แสดงแถวปีปัจจุบันใน popup (ใช้ราคาแถวหลักเป็นหลัก) — แสดงเฉพาะปีที่มีของ
    }
    Object.keys(yearMap).map(Number).sort(function (a, b) { return b - a; }).forEach(function (y) {
      if (!df && y === cy) return;                        // ไม่มี DF → ปีปัจจุบันไม่ต้องแสดง (ใช้ราคาแถวหลัก)
      rows.push({ df: false, label: pad(y), year: y, qty: yearMap[y] });
    });
    return rows;
  }
  function shouldPopup(p) {                               // มีแถวที่จะแสดงใน popup ≥ 1 → เด้ง (ครอบคลุม DF เดี่ยว / ปีเดียวที่ไม่ใช่ปีปัจจุบัน)
    return popupRows(p).length > 0;
  }

  var FIELDS = [['retail', 'ขาย', 'salePrice1'], ['b', 'B', 'salePrice2'], ['a', 'A', 'salePrice3'], ['s', 'S', 'salePrice4']];
  var popEl = null;
  function code2(n) { return (window.XL2 && XL2.dealer) ? (XL2.dealer(n) || '—') : String(n); }
  function fmt(n) { return (window.XL2 && XL2.fmtNum) ? XL2.fmtNum(n) : String(n); }
  function fmt2(n) { n = (window.XL2 ? XL2.toN(n) : parseFloat(n)) || 0; return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  // เปิด popup · p=สินค้า · anchor=td · mode='admin'|'user' · base={retail,b,a,s} ราคาแถวหลัก
  function openPricePopup(p, anchor, mode, base) {
    var rows = popupRows(p); if (!rows.length) return false;
    var code = p.code13 || '';
    pruneSold(code, rows.map(dotKey));                   // ลบราคาของชุดที่ขายหมดไปแล้ว
    base = base || {};
    if (!popEl) { popEl = document.createElement('div'); popEl.className = 'dotpop'; document.body.appendChild(popEl); }
    var isAdmin = mode === 'admin';
    // ซ่อนคอลัมน์ราคาที่ตำแหน่ง user มองไม่เห็น (เช่น เห็นแค่ราคาขาย → ซ่อน B/A/S)
    var FLD = FIELDS.filter(function (f) { return isAdmin || !(window.PermEnforce && PermEnforce.active() && PermEnforce.colHiddenField(f[2])); });
    if (!FLD.length) FLD = [FIELDS[0]];   // กันกรณีซ่อนหมด — อย่างน้อยโชว์ราคาขาย
    var head = '<div class="dotpop-h"><span>🛞 ราคาแยกตามปียาง (DOT)</span><span class="dotpop-x">✕</span></div>' +
      '<div class="dotpop-sub">' + esc(p.name || code) + (isAdmin ? ' · กรอกเป็นตัวเลข · เก็บในเครื่อง (ไม่เขียนกลับ DB)' : ' · โค้ดราคา') + '</div>';
    var ths = FLD.map(function (f) { return '<th>' + f[1] + '</th>'; }).join('');
    var pw = priceWeight(), pwS = pw > 0 ? ('font-weight:' + pw + ';') : '';
    var body = rows.map(function (b, i) {
      var saved = getPrices(code, b) || {};
      var cells = FLD.map(function (f) {
        var v = (saved[f[0]] != null && saved[f[0]] !== '') ? saved[f[0]] : (base[f[0]] != null ? base[f[0]] : '');
        var pc = get(PCOL[f[0]]);
        var num = (window.XL2 ? XL2.toN(v) : parseFloat(v)) || 0;
        if (isAdmin) return '<td><input class="dotpop-in" style="' + pwS + 'color:#' + pc + '" data-row="' + i + '" data-f="' + f[0] + '" inputmode="decimal" value="' + ((v === '' || v == null) ? '' : esc(fmt2(num))) + '"></td>';
        return '<td class="dotpop-code" style="' + pwS + 'color:#' + pc + '">' + (num ? code2(num) : '—') + '</td>';
      }).join('');
      var lab = b.df ? '<span class="dot-flag" style="color:#' + get('flag') + '">DF</span>'
        : '<span class="dot-yr" style="color:#' + tierColor(b.year) + '">' + b.label + '</span>';
      return '<tr><td class="dotpop-dot">' + lab + '</td><td class="dotpop-qty">' + (b.qty > 0 ? fmt(b.qty) : '<span class="dotpop-zero">0</span>') + '</td>' + cells + '</tr>';
    }).join('');
    popEl.innerHTML = head +
      '<table class="dotpop-t"><thead><tr><th>DOT</th><th>เส้น</th>' + ths + '</tr></thead><tbody>' + body + '</tbody></table>' +
      (isAdmin ? '<div class="dotpop-foot"><button class="btn primary dotpop-save">บันทึก</button><button class="btn dotpop-cancel">ปิด</button></div>'
        : '<div class="dotpop-foot"><button class="btn dotpop-cancel">ปิด</button></div>');
    // ตำแหน่ง
    popEl.style.display = 'block';
    var rc = anchor ? anchor.getBoundingClientRect() : { left: 200, bottom: 160 };
    popEl.style.left = Math.max(8, Math.min(rc.left, window.innerWidth - popEl.offsetWidth - 12)) + 'px';
    popEl.style.top = Math.min(rc.bottom + 4, window.innerHeight - popEl.offsetHeight - 12) + 'px';
    var close = function () { popEl.style.display = 'none'; if (window.PopupStack) PopupStack.remove(popEl); };
    if (window.PopupStack) PopupStack.push(popEl, close);
    if (window.makeDraggable) { var _h = popEl.querySelector('.dotpop-h'); if (_h) makeDraggable(popEl, _h); }
    popEl.querySelector('.dotpop-x').onclick = close;
    var cancel = popEl.querySelector('.dotpop-cancel'); if (cancel) cancel.onclick = close;
    var saveBtn = popEl.querySelector('.dotpop-save');
    if (saveBtn) saveBtn.onclick = function () {
      rows.forEach(function (b, i) {
        var vals = {};
        FLD.forEach(function (f) {
          var inp = popEl.querySelector('.dotpop-in[data-row="' + i + '"][data-f="' + f[0] + '"]');
          var raw = inp ? inp.value.trim() : '';
          if (raw !== '') vals[f[0]] = (window.XL2 ? XL2.toN(raw) : parseFloat(raw)) || raw;
        });
        if (Object.keys(vals).length) setPrices(code, b, vals); else setPrices(code, b, {});
      });
      close();
      if (window.SG && SG.render) SG.render();
      if (window.toast) toast('บันทึกราคาแยก DOT (เฉพาะในเครื่อง)');
    };
    // คีย์บอร์ดแบบ Excel: โฟกัสช่องแรกพร้อมพิมพ์ · Enter เลื่อนซ้าย→ขวา ลงแถวใหม่ จนถึงปุ่มบันทึก · ลูกศรบังคับทิศ
    if (isAdmin) {
      var FN = FLD.length, lastRC = { r: 0, c: 0 };
      function inAt(r, c) { return popEl.querySelector('.dotpop-in[data-row="' + r + '"][data-f="' + FLD[c][0] + '"]'); }
      function focusCell(r, c) { r = Math.max(0, Math.min(rows.length - 1, r)); c = Math.max(0, Math.min(FN - 1, c)); var el = inAt(r, c); if (el) { el.focus(); if (el.select) el.select(); } }
      rows.forEach(function (_b, r) {
        FLD.forEach(function (f, c) {
          var el = inAt(r, c); if (!el) return;
          el.addEventListener('focus', function () { if (el.select) el.select(); lastRC = { r: r, c: c }; });
          el.addEventListener('blur', function () { var n = (window.XL2 ? XL2.toN(el.value) : parseFloat(el.value)); el.value = (String(el.value).trim() === '') ? '' : fmt2(n); });   // ใส่ , + 2 ทศนิยม หลังพิมพ์
          el.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); var nc = c + 1, nr = r; if (nc >= FN) { nc = 0; nr = r + 1; } if (nr >= rows.length) { if (saveBtn) saveBtn.focus(); return; } focusCell(nr, nc); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); focusCell(r - 1, c); }
            else if (e.key === 'ArrowDown') { e.preventDefault(); if (r >= rows.length - 1) { if (saveBtn) saveBtn.focus(); } else focusCell(r + 1, c); }   // แถวสุดกดลง → ไปปุ่มบันทึก
            else if (e.key === 'ArrowLeft') { if (el.selectionStart === 0) { e.preventDefault(); focusCell(r, c - 1); } }
            else if (e.key === 'ArrowRight') { if (el.selectionEnd === (el.value || '').length) { e.preventDefault(); focusCell(r, c + 1); } }
          });
        });
      });
      if (saveBtn) saveBtn.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); saveBtn.click(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); focusCell(lastRC.r, lastRC.c); }                 // ขึ้น → ย้อนกลับไปช่องกรอก
        else if (e.key === 'ArrowRight') { e.preventDefault(); if (cancel) cancel.focus(); }                 // ขวา → ไปปุ่มยกเลิก/ปิด
      });
      if (cancel) cancel.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowLeft') { e.preventDefault(); if (saveBtn) saveBtn.focus(); }                     // ซ้าย → กลับไปปุ่มบันทึก
        else if (e.key === 'ArrowUp') { e.preventDefault(); focusCell(lastRC.r, lastRC.c); }
      });
      setTimeout(function () { focusCell(0, 0); }, 30);
    }
    return true;
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  window.DOT = {
    rangeText: rangeText, cellHTML: cellHTML, tierColor: tierColor, get: get, set: set, curYY: curYY, fontSize: fontSize, fontWeight: fontWeight, priceWeight: priceWeight,
    inStockYears: inStockYears, hasDF: hasDF, needsWithdraw: needsWithdraw,
    shouldPopup: shouldPopup, openPricePopup: openPricePopup, applyPopupColors: applyPopupColors
  };

  // ---------- แท็บตั้งค่า "สีปี DOT" ----------
  var PRESET = ['000000', '555555', '9a9a9a', '1F8A5B', '15A34A', '2A6FDB', 'E5322E', 'C00000', 'F1C40F', 'F47C20'];
  var ROWS = [['newc', 'dotPalNew'], ['y1', 'dotPal1y'], ['y2', 'dotPal2y'], ['flag', 'dotPalFlag'], ['sep', 'dotPalSep'], ['pRetail', 'dotPalPRetail'], ['pB', 'dotPalPB'], ['pA', 'dotPalPA'], ['pS', 'dotPalPS'], ['popBg', 'dotPalPopBg'], ['popFg', 'dotPalPopFg']];
  function buildPane() {
    var any = false;
    ROWS.forEach(function (rw) {
      var host = document.getElementById(rw[1]); if (!host) return;
      any = true; host.innerHTML = '';
      var cur = get(rw[0]).toLowerCase();
      if (rw[0].indexOf('pop') === 0) {                    // แถวสี popup: มีปุ่ม ✕ คืนค่าปกติ (ไม่เปลี่ยน)
        var rs = document.createElement('span');
        rs.className = 'sw dotpal-reset' + (get(rw[0]) === '' ? ' on' : '');
        rs.title = 'ปกติ (ไม่เปลี่ยน)'; rs.textContent = '✕';
        rs.onclick = function () { set(rw[0], ''); buildPane(); applyPopupColors(); };
        host.appendChild(rs);
      }
      PRESET.forEach(function (hex) {
        var sw = document.createElement('span');
        sw.className = 'sw' + (cur === hex.toLowerCase() ? ' on' : '');
        sw.style.background = '#' + hex; sw.title = '#' + hex;
        sw.onclick = function () { set(rw[0], hex); buildPane(); if (rw[0].indexOf('pop') === 0) applyPopupColors(); else if (window.SG && SG.render) SG.render(); };
        host.appendChild(sw);
      });
      var isCustom = cur !== '' && PRESET.map(function (h) { return h.toLowerCase(); }).indexOf(cur) < 0;
      var cust = document.createElement('label');
      cust.className = 'sw dotpal-custom' + (isCustom ? ' on' : '');
      cust.title = 'เลือกสีเอง (จานสี)'; cust.style.background = get(rw[0]) ? ('#' + get(rw[0])) : '#ffffff';
      var ci = document.createElement('input'); ci.type = 'color'; ci.value = '#' + (get(rw[0]) || 'ffffff');
      ci.oninput = function () { set(rw[0], ci.value); cust.style.background = ci.value; if (rw[0].indexOf('pop') === 0) applyPopupColors(); else if (window.SG && SG.render) SG.render(); updPrev(); };
      ci.onchange = function () { buildPane(); };
      cust.appendChild(ci);
      cust.insertAdjacentHTML('beforeend', '<span class="dotpal-custom-ic">🎨</span>');
      host.appendChild(cust);
    });
    if (!any) return;
    var cy = document.getElementById('dotCurYY');
    if (cy) cy.textContent = pad(curYY()) + ' (พ.ศ. ' + (new Date().getFullYear() + 543) + ' / ค.ศ. ' + new Date().getFullYear() + ')';
    var fsInp = document.getElementById('dotFontSize');
    if (fsInp) {
      fsInp.value = fontSize() || '';
      fsInp.oninput = function () {
        var v = parseInt(fsInp.value, 10);
        try { localStorage.setItem('xls2_dotfontsize', (v >= 6 && v <= 72) ? String(v) : ''); } catch (e) {}
        if (window.SG && SG.render) SG.render(); updPrev();
      };
    }
    var fwSel = document.getElementById('dotFontWeight');
    if (fwSel) {
      fwSel.value = String(fontWeight() || '');
      fwSel.onchange = function () {
        var v = parseInt(fwSel.value, 10);
        try { localStorage.setItem('xls2_dotfontweight', (v >= 100 && v <= 900) ? String(v) : ''); } catch (e) {}
        if (window.SG && SG.render) SG.render(); updPrev();
      };
    }
    var pwSel = document.getElementById('dotPriceWeight');
    if (pwSel) {
      pwSel.value = String(priceWeight() || '');
      pwSel.onchange = function () {
        var v = parseInt(pwSel.value, 10);
        try { localStorage.setItem('xls2_dotpriceweight', (v >= 100 && v <= 900) ? String(v) : ''); } catch (e) {}
      };
    }
    updPrev();
  }
  function updPrev() {
    var pv = document.getElementById('dotPrev'); if (!pv) return;
    var cy = curYY();
    pv.innerHTML =
      cellHTML({ dotWeeks: [{ dot: cy - 4, qty: 2 }, { dot: cy - 1, qty: 2 }, { dot: cy, qty: 2 }] }) +
      ' &nbsp;·&nbsp; ' + cellHTML({ dotWeeks: [{ dot: cy - 1, qty: 2 }, { dot: cy, qty: 2 }] }) +
      ' &nbsp;·&nbsp; ' + cellHTML({ dotWeeks: [{ dot: cy, qty: 2 }] }) +
      ' &nbsp;·&nbsp; ' + cellHTML({ dotWeeks: [{ dot: cy, qty: 2, df: true }, { dot: cy, qty: 2 }] }) +
      ' &nbsp;·&nbsp; ' + cellHTML({ dotWeeks: [{ dot: cy - 3, qty: 2, df: true }, { dot: cy - 3, qty: 2 }] });
  }
  function wire() { applyPopupColors(); if (document.getElementById('dotPalNew')) buildPane(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
  window.DOT.buildSettings = buildPane;
})();
