/* สีเส้นขอบ + ปุ่มเทสี/สีอักษร/เส้นขอบบนแถบเครื่องมือ + placePop
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดต่อเนื่องตามลำดับก่อน price-update.js */
  // เส้นขอบ: จานสีของฉัน — จำได้ 6 สี (6 ช่อง) + ช่องตัวเลือกสี + ปุ่ม + · คลิกขวาลบสี
  var lastBdColor = (localStorage.getItem('xls2_last_bd_color') || '000000').replace('#', '').toUpperCase();
  function bdPalette() { try { return (JSON.parse(localStorage.getItem('xls2_bd_palette') || '[]')).map(function (c) { return String(c).replace('#', '').toUpperCase(); }); } catch (e) { return []; } }
  function saveBdPalette(arr) { localStorage.setItem('xls2_bd_palette', JSON.stringify(arr.slice(0, 7))); }
  function addBdPalette(hex) { hex = String(hex).replace('#', '').toUpperCase(); var a = bdPalette().filter(function (c) { return c !== hex; }); a.unshift(hex); saveBdPalette(a); }
  function removeBdPalette(hex) { hex = String(hex).replace('#', '').toUpperCase(); saveBdPalette(bdPalette().filter(function (c) { return c !== hex; })); }
  function markBdColor(hex) { hex = String(hex).replace('#', '').toUpperCase(); document.querySelectorAll('#bdPop .bd-c').forEach(function (x) { x.classList.toggle('on', (x.dataset.bdc || '').toUpperCase() === hex); }); }
  // สีหลัก 8 สีด้านบน — เปลี่ยนได้โดยลากสีจากจานสีขึ้นมาทับ + จดจำไว้
  var BD_PRESET_DEF = [['000000', 'ดำ'], ['FF0000', 'แดง'], ['0000FF', 'น้ำเงิน'], ['008000', 'เขียว'], ['F47C20', 'ส้ม'], ['7F1D9B', 'ม่วง'], ['C0A000', 'ทอง'], ['888888', 'เทา']];
  function bdPresets() { try { var a = JSON.parse(localStorage.getItem('xls2_bd_presets') || 'null'); if (Array.isArray(a) && a.length === 8) return a.map(function (c) { return String(c).replace('#', '').toUpperCase(); }); } catch (e) {} return BD_PRESET_DEF.map(function (p) { return p[0]; }); }
  function saveBdPresets(arr) { localStorage.setItem('xls2_bd_presets', JSON.stringify(arr.slice(0, 8).map(function (c) { return String(c).replace('#', '').toUpperCase(); }))); }
  function renderBdPresets() {
    var host = document.getElementById('bdColors'); if (!host) return;
    var pr = bdPresets();
    var sws = host.querySelectorAll('.bd-c');
    for (var i = 0; i < sws.length && i < 8; i++) {
      sws[i].dataset.bdc = pr[i];
      sws[i].style.background = '#' + pr[i];
      sws[i].title = (BD_PRESET_DEF[i] ? BD_PRESET_DEF[i][1] + ' ' : '') + '#' + pr[i] + ' · ลากสีจากจานสีมาทับเพื่อเปลี่ยน';
    }
    markBdColor(lastBdColor);
  }
  function renderBdMyPal() {
    var host = document.getElementById('bdMyPal'); if (!host) return;
    var pal = bdPalette();
    var cells = '';
    for (var i = 0; i < 7; i++) {
      var c = pal[i];
      cells += c
        ? '<span class="sw bd-c rsw" draggable="true" data-bdc="' + c + '" style="background:#' + c + '" title="#' + c + ' · ลากขึ้นไปทับสีหลัก · คลิกขวาเพื่อลบ"></span>'
        : '<span class="bd-slot-empty" title="ช่องว่าง — เลือกสีจากตัวเลือกสีด้านขวา"></span>';
    }
    cells += '<label class="bd-chooser" id="bdAddColor" title="ตัวเลือกสี — เลือกแล้วกด OK สีจะเข้าจานสีและใช้งานทันที"><input type="color" id="bdCustom" value="#' + lastBdColor + '"></label>';
    host.innerHTML = cells;
    var inp = document.getElementById('bdCustom');
    if (inp) {
      inp.addEventListener('input', function (e) { e.stopPropagation(); setBdColor(this.value, false); });   // ลากเลือกสี — แสดงตัวอย่างทันที
      inp.addEventListener('change', function (e) { e.stopPropagation(); setBdColor(this.value, true); });   // กดตกลง/enter/ดับเบิลคลิก — เก็บลงจานสี + ใช้งาน
      inp.addEventListener('click', function (e) { e.stopPropagation(); });
    }
    host.querySelectorAll('.rsw').forEach(function (sw) {
      sw.addEventListener('dragstart', function (e) { e.dataTransfer.setData('text/plain', sw.dataset.bdc); e.dataTransfer.effectAllowed = 'copy'; sw.classList.add('dragging'); });
      sw.addEventListener('dragend', function () { sw.classList.remove('dragging'); });
    });
  }
  function setBdColor(hex, remember) {
    hex = String(hex).replace('#', '').toUpperCase();
    SG.setBorderOpts({ color: hex });
    var d = $('bdDemo'); if (d) d.setAttribute('stroke', '#' + hex);
    lastBdColor = hex;
    localStorage.setItem('xls2_last_bd_color', hex);
    if (remember) { addBdPalette(hex); renderBdMyPal(); }
    var inp = document.getElementById('bdCustom'); if (inp) inp.value = '#' + hex;
    markBdColor(hex);
    updBorderIcon();
  }
  renderBdPresets();
  renderBdMyPal();
  // ลากสีจากจานสีขึ้นไปทับสีหลักด้านบน → เปลี่ยนสีหลัก (จดจำไว้)
  (function () {
    var host = document.getElementById('bdColors');
    if (!host) return;
    host.addEventListener('dragover', function (e) { var t = e.target.closest('.bd-c'); if (t) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; t.classList.add('drop-hot'); } });
    host.addEventListener('dragleave', function (e) { var t = e.target.closest('.bd-c'); if (t) t.classList.remove('drop-hot'); });
    host.addEventListener('drop', function (e) {
      var t = e.target.closest('.bd-c'); if (!t) return;
      e.preventDefault(); t.classList.remove('drop-hot');
      var hex = (e.dataTransfer.getData('text/plain') || '').replace('#', '').toUpperCase(); if (!hex) return;
      var sws = [].slice.call(host.querySelectorAll('.bd-c'));
      var idx = sws.indexOf(t); if (idx < 0) return;
      var pr = bdPresets(); pr[idx] = hex; saveBdPresets(pr);
      renderBdPresets();
      setBdColor(hex, false);   // ใช้สีหลักใหม่ทันที
      if (typeof toast === 'function') toast('🎨 ตั้งเป็นสีหลักแล้ว #' + hex);
    });
  })();
  // คลิกขวาที่สีในจานสี = ลบสีนั้น
  (function () {
    var host = document.getElementById('bdMyPal');
    if (host) host.addEventListener('contextmenu', function (e) {
      var sw = e.target.closest('.rsw'); if (!sw) return;
      e.preventDefault(); e.stopPropagation();
      removeBdPalette(sw.dataset.bdc); renderBdMyPal(); markBdColor(lastBdColor);
    });
  })();
  // จดจำสีล่าสุด: คืนค่าสีเส้นที่เลือกไว้ตอนเปิดโปรแกรมใหม่
  (function restoreBdColor() {
    markBdColor(lastBdColor);
    try { if (typeof SG !== 'undefined' && SG.setBorderOpts) SG.setBorderOpts({ color: lastBdColor }); } catch (e) {}
    updBorderIcon();
  })();
  renderRecentRows();
  // เทสีแบบ Excel: คลิกไอคอน = เทสีล่าสุด · คลิก ▾ = เลือกสี
  var lastFill = localStorage.getItem('xls2_last_fill') || 'FFEB3B';
  function setLastFill(hex) { if (!hex) return; lastFill = hex; localStorage.setItem('xls2_last_fill', hex); var b = document.querySelector('#btnFill .fill-drip'), p = document.querySelector('#btnFill .fill-pool'); if (b) b.setAttribute('fill', '#' + hex); if (p) p.setAttribute('fill', '#' + hex); }
  setLastFill(lastFill);
  $('btnFill').onclick = function (e) {
    e.stopPropagation();
    $('fontPop').classList.remove('open');
    var openDrop = !e.target.closest('.ic');
    if (openDrop) { var sgEl = $('swGrid'); if (sgEl && sgEl._cfRefresh) sgEl._cfRefresh(); $('swPop').classList.toggle('open'); placePop($('swPop'), this); }   // คลิก ▾ = เปิด dropdown
    else { SG.applyStyle('bg', lastFill); }                  // คลิกถังสี = เทสีล่าสุดลงช่องที่เลือก
  };
  // วางจานสีใต้ปุ่มเสมอ แม้ปุ่มถูกลากย้าย (กันปัญหา "กดแล้วไม่พบจานสี")
  function placePop(pop, btn) {
    if (!pop.classList.contains('open')) return;
    if (pop.parentElement !== document.body) document.body.appendChild(pop);   // กันปุ่มถูกลากออกแล้ว popup ติดอยู่ในกลุ่มที่ถูกซ่อน
    var r = btn.getBoundingClientRect();
    pop.style.position = 'fixed';
    pop.style.maxHeight = (window.innerHeight - 16) + 'px'; pop.style.overflowY = 'auto';
    var ph = pop.offsetHeight, pw = pop.offsetWidth;
    var left = Math.max(6, Math.min(r.left, window.innerWidth - pw - 6));
    var top = r.bottom + 3;
    if (top + ph > window.innerHeight - 6) top = r.top - ph - 3;          // ไม่พอด้านล่าง → ขึ้นด้านบนปุ่ม
    top = Math.max(6, Math.min(top, window.innerHeight - ph - 6));        // กันหลุดเฟรมบน/ล่าง
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
  }
  $('btnFont').onclick = function (e) {
    e.stopPropagation();
    if (e.target.closest('.ic')) {   // คลิกตัว A = ใช้สีล่าสุดทันที
      SG.applyStyle('fc', lastFontColor); $('fontPop').classList.remove('open'); return;
    }
    $('swPop').classList.remove('open'); $('bdPop').classList.remove('open'); var fgEl = $('fontGrid'); if (fgEl && fgEl._cfRefresh) fgEl._cfRefresh(); $('fontPop').classList.toggle('open'); placePop($('fontPop'), this);
  };
  document.addEventListener('click', function () { var fp = $('filePop'); if (fp) fp.classList.remove('open'); $('swPop').classList.remove('open'); $('fontPop').classList.remove('open'); $('bdPop').classList.remove('open'); $('morePop').classList.remove('open'); });
  $('swPop').onclick = function (e) { e.stopPropagation(); };
  $('fontPop').onclick = function (e) { e.stopPropagation(); };
  // ลากย้ายหน้าต่าง popup ของแถบเครื่องมือ (จับที่หัวข้อ .lbl)
  document.addEventListener('mousedown', function (e) {
    var lbl = e.target.closest('.swpop .lbl'); if (!lbl) return;
    var pop = lbl.closest('.swpop'); if (!pop) return;
    var r = pop.getBoundingClientRect();
    pop.style.position = 'fixed'; pop.style.left = r.left + 'px'; pop.style.top = r.top + 'px'; pop.style.right = 'auto';
    var sx = e.clientX, sy = e.clientY, ox = r.left, oy = r.top, moved = false;
    function mv(ev) { moved = true; pop.style.left = Math.max(2, Math.min(ox + ev.clientX - sx, window.innerWidth - pop.offsetWidth - 2)) + 'px'; pop.style.top = Math.max(2, oy + ev.clientY - sy) + 'px'; }
    function up() { document.removeEventListener('mousemove', mv, true); document.removeEventListener('mouseup', up, true); if (moved) { var blk = function (ev) { ev.stopPropagation(); document.removeEventListener('click', blk, true); }; document.addEventListener('click', blk, true); } }
    document.addEventListener('mousemove', mv, true); document.addEventListener('mouseup', up, true); e.preventDefault();
  }, true);
  // ⎋ Esc = ออก/ปิดทุกฟังก์ชัน (เมนู · ป๊อปอัป · หน้าต่าง · แชท) ยกเว้นปิดโปรแกรม
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var closed = false;
    // แชทบอท
    var cb = document.getElementById('cbPanel');
    if (cb && cb.classList.contains('open')) { var x = cb.querySelector('.cb-x'); if (x) x.click(); else cb.classList.remove('open'); closed = true; }
    // เมนู/ป๊อปอัปลอย
    var sm = document.getElementById('settingsMenu'); if (sm) { sm.remove(); closed = true; }
    var bp = document.getElementById('brandNamePop'); if (bp) { bp.remove(); closed = true; }
    document.querySelectorAll('.swpop.open').forEach(function (p) { p.classList.remove('open'); closed = true; });
    if (document.getElementById('btnMore')) document.getElementById('btnMore').classList.remove('drophot');
    // หน้าต่าง modal (ปิดอันบนสุดทีละชั้น)
    var openModals = [].slice.call(document.querySelectorAll('.modal.open'));
    if (openModals.length) { openModals[openModals.length - 1].classList.remove('open'); closed = true; }
    if (closed) { e.stopPropagation(); }   // ปิด UI ก่อน · ถ้าไม่มีอะไรเปิด ปล่อยให้ตาราง (ยกเลิกคัดลอก/เลือก) จัดการ
  }, true);

  // ไอคอนเส้นขอบแสดงรูปแบบ (ขอบไหน) + สี/ลายเส้นที่เลือก — เหมือน Excel
  var lastBdMode = 'bottom';
  function updBorderIcon(mode) {
    var c = (document.querySelector('#bdPop .bd-c.on') || {}).dataset;
    var s = (document.querySelector('#bdStyles .bd-s.on') || {}).dataset;
    var w = (document.querySelector('#bdWeights .bd-w.on') || {}).dataset;
    var color = c && c.bdc ? '#' + c.bdc : (typeof lastBdColor !== 'undefined' && lastBdColor ? '#' + lastBdColor : '#000');
    var bp = document.getElementById('bdPop'); if (bp) bp.style.setProperty('--bd-prev', color);   // ไอคอนโหมดในป็อปอัปใช้สีเส้นที่เลือก
    var bar = document.getElementById('bdColorBar'); if (bar) bar.setAttribute('fill', color);   // แถบสีใต้ไอคอน = สีเส้นที่เลือก (เห็นชัดทุกโหมด)
    var style = s && s.bds ? s.bds : 'solid';
    // ความหนาเส้นที่เลือก (ความหนาเส้น) → ความหนาของเส้นในไอคอน
    var wsel = w && w.bdw ? parseFloat(w.bdw) : 1;
    if (style === 'dashed-thick') wsel = Math.max(wsel, 2);   // ลายประหนา = อย่างน้อย 2
    // map น้ำหนัก 0.5/1/2/3 → ความหนาเส้นในไอคอน (บางมาก เรียบ แบบ Excel)
    var baseW = wsel <= 0.5 ? 0.5 : wsel >= 3 ? 1.1 : wsel >= 2 ? 0.85 : 0.65;
    // ลายเส้น (ลายเส้น) → รูปแบบเส้นประในไอคอน (ปรับตามความหนา)
    var k = baseW;
    var dash = '';
    if (style === 'dotted') dash = (0.7 * k).toFixed(2) + ' ' + (1.1 * k).toFixed(2);
    else if (style === 'dashed' || style === 'dashed-thick') dash = (2 * k).toFixed(2) + ' ' + (1.4 * k).toFixed(2);
    if (mode) lastBdMode = mode; mode = lastBdMode || 'all';
    var on = { t: 0, b: 0, l: 0, r: 0, ih: 0, iv: 0 };
    if (mode === 'all') on = { t: 1, b: 1, l: 1, r: 1, ih: 1, iv: 1 };
    else if (mode.indexOf('outer') === 0) { on.t = on.b = on.l = on.r = 1; }
    else if (mode.indexOf('top') === 0) on.t = 1;
    else if (mode.indexOf('bottom') === 0) on.b = 1;
    else if (mode.indexOf('left') === 0) on.l = 1;
    else if (mode.indexOf('right') === 0) on.r = 1;
    // เส้นขอบนอก/ล่างหนาพิเศษ จะหนากว่าเส้นในเล็กน้อย
    var tw = (mode && /thick/.test(mode)) ? Math.max(baseW, 1) : baseW;
    [['bdT', on.t], ['bdB', on.b], ['bdL', on.l], ['bdR', on.r], ['bdIH', on.ih], ['bdIV', on.iv]].forEach(function (pr) {
      var el = document.getElementById(pr[0]); if (!el) return;
      el.setAttribute('stroke', pr[1] ? color : 'transparent');
      el.setAttribute('stroke-dasharray', pr[1] ? dash : '');
      el.setAttribute('stroke-width', pr[1] ? tw : baseW);   // ทุกเส้นหนาเท่ากัน
    });
  }
  updBorderIcon();
  // 🌈 ไฮไลต์ค่าซ้ำ: ค่าเดียวกัน → สีเดียวกัน (สีสดใส) · ไม่แก้ข้อมูลจริง
  var dupHi = false;
  var DUP_PAL = ['#E5322E', '#1565C0', '#1E7F2C', '#E07A00', '#7B1FA2', '#00838F', '#C2185B', '#4527A0', '#33691E', '#AD1457', '#0277BD', '#D84315'];
  function applyDupHi() {
    var tds = document.querySelectorAll('#grid td.sg-c');
    tds.forEach(function (t) { if (t.dataset.oc !== undefined) { t.style.color = t.dataset.oc; t.style.fontWeight = t.dataset.ow || ''; delete t.dataset.oc; delete t.dataset.ow; } });
    if (!dupHi) return;
    var map = {};
    tds.forEach(function (t) { var v = t.textContent.trim(); if (!v) return; (map[v] = map[v] || []).push(t); });
    var i = 0;
    Object.keys(map).forEach(function (k) {
      if (map[k].length < 2) return;
      var c = DUP_PAL[i++ % DUP_PAL.length];
      map[k].forEach(function (t) { t.dataset.oc = t.style.color || ''; t.dataset.ow = t.style.fontWeight || ''; t.style.color = c; t.style.fontWeight = '700'; });
    });
  }
  var dupObs = new MutationObserver(function () { if (dupHi) applyDupHi(); });
  var btnDup = document.getElementById('btnDupHi');
  if (btnDup) btnDup.onclick = function () {
    dupHi = !dupHi;
    btnDup.classList.toggle('on', dupHi);
    if (dupHi) { dupObs.observe(document.getElementById('grid'), { childList: true, subtree: true }); applyDupHi(); if (typeof toast === 'function') toast('🌈 ไฮไลต์ค่าซ้ำแล้ว — ค่าเดียวกันสีเดียวกัน'); }
    else { dupObs.disconnect(); applyDupHi(); if (typeof toast === 'function') toast('ปิดไฮไลต์ค่าซ้ำ'); }
  };
  // borders dropdown
  $('btnBorder').onclick = function (e) { e.stopPropagation(); $('swPop').classList.remove('open'); $('fontPop').classList.remove('open'); if (e.target.closest('.ic')) { SG.applyBorders(lastBdMode || 'all'); $('bdPop').classList.remove('open'); return; } $('bdPop').classList.toggle('open'); placePop($('bdPop'), this); };
  $('bdPop').onclick = function (e) {
    e.stopPropagation();
    if (e.target.id === 'bdCustom' || e.target.closest('#bdAddColor')) return;
    var cdot = e.target.closest('.bd-c');
    if (cdot && cdot.dataset.bdc) {
      setBdColor(cdot.dataset.bdc, false);
      return;
    }
    var sty = e.target.closest('.bd-s');
    if (sty) {
      document.querySelectorAll('#bdStyles .bd-s').forEach(function (x) { x.classList.remove('on'); });
      sty.classList.add('on');
      SG.setBorderOpts({ style: sty.dataset.bds });
      updBorderIcon();
      return;
    }
    var wgt = e.target.closest('.bd-w');
    if (wgt) {
      document.querySelectorAll('#bdWeights .bd-w').forEach(function (x) { x.classList.remove('on'); });
      wgt.classList.add('on');
      SG.setBorderOpts({ w: parseFloat(wgt.dataset.bdw) });
      updBorderIcon();
      return;
    }
    var it = e.target.closest('.bd-it'); if (!it) return;
    document.querySelectorAll('#bdPop .bd-it').forEach(function (x) { x.classList.remove('on'); });
    it.classList.add('on');   // ไฮไลต์ลักษณะตาราง/ไม่มีเส้น/ยางลบ ที่เลือกล่าสุด
    SG.applyBorders(it.dataset.bd);
    updBorderIcon(it.dataset.bd);
    $('bdPop').classList.remove('open');
  };

