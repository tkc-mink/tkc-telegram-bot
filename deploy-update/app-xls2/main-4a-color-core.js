/* สีพื้นฐาน: recentColors + cfBuild (เครื่องมือเลือกสีรวม) + จานเทสี/สีอักษร
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดต่อเนื่องตามลำดับก่อน price-update.js */
  // swatches + 🎨 สีกำหนดเอง + จดจำสีล่าสุด (ใช้ร่วมกันทุกพาเลตต์)
  function recentColors() { try { return JSON.parse(localStorage.getItem('xls2_recent_colors') || '[]'); } catch (e) { return []; } }
  var custRows = [];
  function renderRecentRows() {
    var rc = recentColors();
    custRows.forEach(function (row) {
      var host = row.querySelector('.cust-recent');
      host.innerHTML = rc.map(function (c) { return '<span class="sw rsw" data-c="' + c + '" style="background:#' + c + '" title="#' + c + '"></span>'; }).join('');
      host.querySelectorAll('.rsw').forEach(function (sw) { sw.onclick = function () { row._applyFn(sw.dataset.c); }; });
    });
  }
  function addRecentColor(hex) {
    hex = String(hex).replace('#', '').toUpperCase();
    var rc = recentColors().filter(function (c) { return c !== hex; });
    rc.unshift(hex);
    localStorage.setItem('xls2_recent_colors', JSON.stringify(rc.slice(0, 8)));
    renderRecentRows();
  }
  function buildCustomRow(hostEl, applyFn) {
    var row = document.createElement('div');
    row.className = 'cust-row';
    row.innerHTML = '<label class="cust-pick">➕ สีอื่น…<input type="color" value="#F47C20"></label><div class="cust-recent"></div>';
    row.querySelector('input').addEventListener('change', function () {
      var hex = this.value.replace('#', '').toUpperCase();
      addRecentColor(hex);
      applyFn(hex);
    });
    row._applyFn = function (hex) { addRecentColor(hex); applyFn(hex); };
    hostEl.appendChild(row);
    custRows.push(row);
  }
  // ===== ฟังก์ชันเลือกสีแบบรวม (สีหลัก + จานสีของฉัน + ลากทับ + ตัวเลือกสี + จดจำ) — ต้นแบบจากปุ่มเส้นขอบ =====
  function cfMyPal(ns) { try { return (JSON.parse(localStorage.getItem('xls2_cf_' + ns + '_pal') || '[]')).map(function (c) { return String(c).replace('#', '').toUpperCase(); }); } catch (e) { return []; } }
  function cfSavePal(ns, a) { localStorage.setItem('xls2_cf_' + ns + '_pal', JSON.stringify(a.slice(0, 7))); }
  function cfAddPal(ns, hex) { hex = String(hex).replace('#', '').toUpperCase(); if (!hex) return; var a = cfMyPal(ns).filter(function (c) { return c !== hex; }); a.unshift(hex); cfSavePal(ns, a); }
  function cfRemovePal(ns, hex) { hex = String(hex).replace('#', '').toUpperCase(); cfSavePal(ns, cfMyPal(ns).filter(function (c) { return c !== hex; })); }
  function cfMain(ns, def) { try { var a = JSON.parse(localStorage.getItem('xls2_cf_' + ns + '_main') || 'null'); if (Array.isArray(a) && a.length === def.length) return a.map(function (c) { return String(c).replace('#', '').toUpperCase(); }); } catch (e) {} return def.map(function (d) { return String(d[0]).toUpperCase(); }); }
  function cfSaveMain(ns, a) { localStorage.setItem('xls2_cf_' + ns + '_main', JSON.stringify(a.map(function (c) { return String(c).replace('#', '').toUpperCase(); }))); }
  function cfBuild(host, opts) {
    // opts: ns, mainDef([[hex,name],...]), mode('fill'|'font'|'block'), allowNone, noneLabel, current()->hexOrNullOr'', onPick(hexOrNull)
    host.classList.add('cf'); host.classList.remove('swgrid'); host.innerHTML = '';
    var lblMain = document.createElement('div'); lblMain.className = 'cf-lbl'; lblMain.textContent = 'สีหลัก';
    var mainWrap = document.createElement('div'); mainWrap.className = 'cf-main';
    var lblPal = document.createElement('div'); lblPal.className = 'cf-lbl'; lblPal.innerHTML = 'จานสีของฉัน <small>· ลากขึ้นไปทับสีหลัก · คลิกขวาลบ</small>';
    var palWrap = document.createElement('div'); palWrap.className = 'cf-pal';
    host.appendChild(lblMain); host.appendChild(mainWrap); host.appendChild(lblPal); host.appendChild(palWrap);
    function curHex() { var c = opts.current ? opts.current() : ''; if (c === null) return null; return String(c || '').replace('#', '').toUpperCase(); }
    function paint(el, hex) { if (opts.mode === 'font') { el.classList.add('cf-fontsw'); el.textContent = 'A'; el.style.color = '#' + hex; el.style.background = (hex === 'FFFFFF' ? '#999' : '#fff'); } else { el.style.background = '#' + hex; } }
    function pick(hex, viaChooser) { opts.onPick(hex, viaChooser); host._cfRefresh(); }
    function renderMain() {
      mainWrap.innerHTML = ''; var cur = curHex();
      if (opts.allowNone) {
        var none = document.createElement('span'); none.className = 'cf-sw cf-none' + ((cur === null || cur === '') ? ' on' : ''); none.title = opts.noneLabel || 'ไม่มีสี';
        none.addEventListener('click', function (e) { e.stopPropagation(); pick(null); }); mainWrap.appendChild(none);
      }
      cfMain(opts.ns, opts.mainDef).forEach(function (hex, idx) {
        var sw = document.createElement('span'); sw.className = 'cf-sw' + (cur === hex ? ' on' : ''); sw.dataset.cf = hex;
        var nm = (opts.mainDef[idx] && opts.mainDef[idx][1]) ? opts.mainDef[idx][1] + ' ' : '';
        sw.title = nm + '#' + hex + ' · ลากสีจากจานสีมาทับเพื่อเปลี่ยน'; paint(sw, hex);
        sw.addEventListener('click', function (e) { e.stopPropagation(); pick(hex); });
        sw.addEventListener('dragover', function (e) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; sw.classList.add('cf-drop'); });
        sw.addEventListener('dragleave', function () { sw.classList.remove('cf-drop'); });
        sw.addEventListener('drop', function (e) { e.preventDefault(); sw.classList.remove('cf-drop'); var h = (e.dataTransfer.getData('text/plain') || '').replace('#', '').toUpperCase(); if (!h) return; var arr = cfMain(opts.ns, opts.mainDef); arr[idx] = h; cfSaveMain(opts.ns, arr); pick(h); });
        mainWrap.appendChild(sw);
      });
    }
    function renderPal() {
      palWrap.innerHTML = ''; var cur = curHex(); var pal = cfMyPal(opts.ns);
      for (var i = 0; i < 7; i++) {
        var c = pal[i];
        if (c) {
          var sw = document.createElement('span'); sw.className = 'cf-sw cf-psw' + (cur === c ? ' on' : ''); sw.dataset.cf = c; sw.draggable = true; sw.title = '#' + c + ' · ลากขึ้นทับสีหลัก · คลิกขวาลบ'; paint(sw, c);
          sw.addEventListener('click', function (e) { e.stopPropagation(); pick(this.dataset.cf); });
          sw.addEventListener('contextmenu', function (e) { e.preventDefault(); e.stopPropagation(); cfRemovePal(opts.ns, this.dataset.cf); host._cfRefresh(); });
          sw.addEventListener('dragstart', function (e) { e.dataTransfer.setData('text/plain', this.dataset.cf); e.dataTransfer.effectAllowed = 'copy'; this.classList.add('cf-dragging'); });
          sw.addEventListener('dragend', function () { this.classList.remove('cf-dragging'); });
          palWrap.appendChild(sw);
        } else { var em = document.createElement('span'); em.className = 'cf-sw cf-empty'; em.title = 'ช่องว่าง — เลือกสีจากตัวเลือกสีด้านขวา'; palWrap.appendChild(em); }
      }
      var lab = document.createElement('label'); lab.className = 'cf-sw cf-chooser'; lab.title = 'ตัวเลือกสี — เลือกแล้วสีจะเข้าจานสีและใช้งานทันที';
      var inp = document.createElement('input'); inp.type = 'color'; inp.value = '#' + (cur && cur.length === 6 ? cur : '000000');
      inp.addEventListener('click', function (e) { e.stopPropagation(); });
      inp.addEventListener('input', function (e) { e.stopPropagation(); });   // แค่เปิด/ลากแถบสีรุ้ง ยังไม่ถือว่าเลือก
      inp.addEventListener('change', function (e) { e.stopPropagation(); var h = this.value.replace('#', '').toUpperCase(); cfAddPal(opts.ns, h); pick(h, true); });   // กดตกลง/enter จึงเลือก + เก็บลงจานสี
      lab.appendChild(inp); palWrap.appendChild(lab);
    }
    host._cfRefresh = function () { renderMain(); renderPal(); };
    host._cfRefresh();
    return host;
  }
  // ตัว A บนปุ่มสีตัวอักษร = สีล่าสุดที่เลือก (เหมือน Excel)
  var lastFontColor = localStorage.getItem('xls2_last_fc') || 'C00000';
  function setFontA(hex) { if (!hex) return; lastFontColor = hex; localStorage.setItem('xls2_last_fc', hex); var a = document.querySelector('#btnFont .ic'); if (a) a.style.color = '#' + hex; }
  setFontA(lastFontColor);
  // เทสีพื้นช่อง — สีหลัก + จานสีของฉัน (แบบเดียวกับเส้นขอบ)
  cfBuild($('swGrid'), {
    ns: 'fill', mode: 'fill', allowNone: true, noneLabel: 'ไม่มีสี (ใส)',
    mainDef: [['FFFF00', 'เหลือง'], ['FF9900', 'ส้ม'], ['92D050', 'เขียว'], ['00B0F0', 'ฟ้า'], ['00FFFF', 'ฟ้าน้ำเงิน'], ['FF99CC', 'ชมพู'], ['D8D8D8', 'เทา'], ['FF6666', 'แดง']],
    current: function () { return (localStorage.getItem('xls2_last_fill') || '').replace('#', ''); },
    onPick: function (hex, viaChooser) { SG.applyStyle('bg', hex); if (hex) setLastFill(hex); if (!viaChooser) $('swPop').classList.remove('open'); }
  });
  // สีตัวอักษร — สีหลัก + จานสีของฉัน (แบบเดียวกับเส้นขอบ)
  cfBuild($('fontGrid'), {
    ns: 'font', mode: 'font', allowNone: true, noneLabel: 'ค่าเริ่มต้น (ดำ)',
    mainDef: [['000000', 'ดำ'], ['808080', 'เทา'], ['FF0000', 'แดง'], ['C00000', 'แดงเข้ม'], ['FF6600', 'ส้ม'], ['008000', 'เขียว'], ['0000FF', 'น้ำเงิน'], ['7030A0', 'ม่วง']],
    current: function () { return (localStorage.getItem('xls2_last_fc') || 'C00000').replace('#', ''); },
    onPick: function (hex, viaChooser) { SG.applyStyle('fc', hex); if (hex) setFontA(hex); if (!viaChooser) $('fontPop').classList.remove('open'); }
  });

