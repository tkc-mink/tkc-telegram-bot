/* เมนูโลโก้ + init ปิดท้าย + ชื่อไฟล์บนหัว + ออโต้เซฟ + เก็บแถบเครื่องมือ + เปิด global
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดต่อเนื่องตามลำดับก่อน price-update.js */
  // โลโก้: คลิกขวา = เมนูในเฟรม (ดูรูปเต็ม / เปลี่ยน / ลบ) — ไม่หลุดจออีก
  (function logoMenu() {
    var slot = document.getElementById('brand-logo');
    if (!slot) return;
    var menu = null;
    function closeM() { if (menu) menu.style.display = 'none'; }
    function sr(sel) { return slot.shadowRoot ? slot.shadowRoot.querySelector(sel) : null; }
    slot.addEventListener('contextmenu', function (e) {
      e.preventDefault(); e.stopPropagation();
      if (!menu) {
        menu = document.createElement('div');
        menu.className = 'sg-ctx';
        document.body.appendChild(menu);
        document.addEventListener('mousedown', function (ev) { var t = ev.target; if (!t.closest || !t.closest('.sg-ctx')) closeM(); });
        document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeM(); });
      }
      var img = sr('img');
      var reg = [];
      function it(ic, t, fn) { reg.push(fn); return '<div class="ctx-it" data-i="' + (reg.length - 1) + '"><span class="ctx-ic">' + ic + '</span><span class="ctx-tx">' + t + '</span></div>'; }
      menu.innerHTML =
        (img && img.src ? it('🔍', 'ดูโลโก้เต็ม', function () {
          var ov = document.createElement('div');
          ov.style.cssText = 'position:fixed;inset:0;z-index:120;background:rgba(0,0,0,.7);display:grid;place-items:center;cursor:zoom-out;';
          ov.innerHTML = '<img src="' + img.src + '" style="max-width:70vw;max-height:70vh;background:#fff;border-radius:12px;padding:14px;" />';
          ov.onclick = function () { ov.remove(); };
          document.body.appendChild(ov);
        }) : '') +
        it('♻️', 'เปลี่ยนโลโก้…', function () {
          var b = sr('[data-act="replace"]'), f = sr('input[type=file]');
          if (b) b.click(); else if (f) f.click();
        }) +
        (img && img.src ? it('🗑️', 'ลบโลโก้', function () { var b = sr('[data-act="clear"]'); if (b) b.click(); }) : '');
      menu.style.display = 'block';
      var vw = window.innerWidth, vh = window.innerHeight;
      menu.style.left = Math.max(8, Math.min(e.clientX, vw - menu.offsetWidth - 8)) + 'px';
      menu.style.top = Math.max(8, Math.min(e.clientY + 6, vh - menu.offsetHeight - 8)) + 'px';
      menu.onclick = function (ev) {
        var el = ev.target.closest('[data-i]'); if (!el) return;
        closeM(); reg[+el.dataset.i]();
      };
    });
  })();

  refresh();
  renderFltBar();
  // ชื่อไฟล์บนหัว: คลิกขวา = popup ชื่อเต็ม · Esc/คลิกที่อื่น = ปิด
  function showBrandPop(e) {
    e.preventDefault(); e.stopPropagation();
    var old = document.getElementById('brandNamePop');
    if (old) { old.remove(); return; }
    var fname = getFileName();
    var pop = document.createElement('div');
    pop.id = 'brandNamePop';
    pop.className = 'sg-ctx';
    pop.style.display = 'block';
    pop.style.padding = '10px 14px';
    pop.style.maxWidth = '360px';
    pop.innerHTML = '<div style="font-size:11px;color:#888;margin-bottom:3px;">ชื่อไฟล์ปัจจุบัน</div><div style="font-weight:700;font-size:14px;color:#222;word-break:break-word;">' + XL2.esc(fname) + '</div>' + fileTimesHtml();
    document.body.appendChild(pop);
    var r = this.getBoundingClientRect();
    pop.style.left = Math.max(8, r.left) + 'px';
    pop.style.top = (r.bottom + 4) + 'px';
    function close() { pop.remove(); document.removeEventListener('keydown', onEsc, true); document.removeEventListener('mousedown', onOut, true); }
    function onEsc(ev) { if (ev.key === 'Escape') { ev.preventDefault(); ev.stopImmediatePropagation(); close(); } }
    function onOut(ev) { var tg = ev.target; if (tg === pop || (tg.closest && (tg.closest('#brandNamePop') || tg.closest('#brandTtl')))) return; close(); }
    document.addEventListener('keydown', onEsc, true);
    setTimeout(function () { document.addEventListener('mousedown', onOut, true); }, 0);
  }
  // เวลาสร้าง/บันทึกล่าสุด
  if (!localStorage.getItem('xls2_createdAt')) localStorage.setItem('xls2_createdAt', String(Date.now()));
  function fmtTime(ms) { if (!ms) return '—'; try { return new Date(+ms).toLocaleString('th-TH'); } catch (e) { return '—'; } }
  function stampSaved() { localStorage.setItem('xls2_savedAt', String(Date.now())); }
  function fileTimesHtml() {
    return '<div style="margin-top:7px;padding-top:6px;border-top:1px dashed #e0d5c5;font-size:11px;color:#666;line-height:1.7;">' +
      '🕘 สร้างเมื่อ: ' + fmtTime(localStorage.getItem('xls2_createdAt')) + '<br>' +
      '💾 บันทึกล่าสุด: ' + fmtTime(localStorage.getItem('xls2_savedAt')) + '</div>';
  }
  $('brandTtl').addEventListener('click', showBrandPop);
  $('brandTtl').addEventListener('contextmenu', showBrandPop);
  $('brandTtl').addEventListener('dblclick', function (e) {
    e.preventDefault(); e.stopPropagation();
    var old = document.getElementById('brandNamePop'); if (old) old.remove();
    promptDialog('ตั้งชื่อไฟล์', 'ชื่อที่แสดงบนหัวโปรแกรม', getFileName(), function (n) { if (n !== null) setFileName(n); });
  });
  $('brandTtl').style.cursor = 'pointer';
  $('brandTtl').title = 'คลิก = ดูชื่อไฟล์เต็ม · ดับเบิลคลิก = เปลี่ยนชื่อไฟล์';
  // ⏳ ออโต้เซฟ (ปรับเวลาได้ — คลิกที่ตัวนับถอยหลัง) · เซฟเอง = เริ่มนับใหม่
  function autoMin() { var m = parseInt(localStorage.getItem('xls2_autosave_min') || '5', 10); return (m >= 1 && m <= 60) ? m : 5; }
  var autosaveLeft = autoMin() * 60;
  function resetAutoTimer() { autosaveLeft = autoMin() * 60; }
  $('saveState').style.cursor = 'pointer';
  $('saveState').title = 'คลิกเพื่อตั้งเวลาออโต้เซฟ';
  $('saveState').onclick = function () {
    promptDialog('ตั้งเวลาออโต้เซฟ', 'กี่นาทีต่อครั้ง (1–60)', String(autoMin()), function (m) {
    if (m === null) return;
    m = parseInt(m, 10);
    if (!(m >= 1 && m <= 60)) { alertDialog('ค่าไม่ถูกต้อง', 'ใส่ตัวเลข 1–60 นาที'); return; }
    localStorage.setItem('xls2_autosave_min', String(m));
    resetAutoTimer();
    });
  };
  (function wrapSaves() {
    var oSave = SG.save, oSaveAs = SG.saveAs;
    SG.save = function () { var r = oSave.apply(SG, arguments); resetAutoTimer(); return r; };
    SG.saveAs = function () { var r = oSaveAs.apply(SG, arguments); resetAutoTimer(); return r; };
  })();
  setInterval(function () {
    autosaveLeft--;
    if (autosaveLeft <= 0) {
      if (SG.isDirty()) { SG.save(); stampSaved(); }   // ถึงเวลา → เซฟให้ (ถ้าไม่มีอะไรค้าง ข้าม)
      else resetAutoTimer();
    }
  }, 1000);

  setInterval(function () {
    var s = $('saveState');
    var mm = Math.floor(Math.max(0, autosaveLeft) / 60);
    var ss = String(Math.max(0, autosaveLeft) % 60).padStart(2, '0');
    if (SG.isDirty()) { s.innerHTML = '<span class="unsaved">● ยังไม่เซฟ</span> · ' + mm + ':' + ss; s.classList.remove('clean'); }
    else { s.textContent = '✓ ⏳ ' + mm + ':' + ss; s.classList.add('clean'); var sv = localStorage.getItem('xls2_savedAt'); s.title = sv ? 'บันทึกแล้ว · ล่าสุด: ' + new Date(+sv).toLocaleString('th-TH') + ' · ออโต้เซฟอีก ' + mm + ':' + ss : 'บันทึกแล้ว'; }
    // ช่องฟอนต์สะท้อนฟอนต์ของช่องที่เลือก (เหมือน Excel)
    var ffSel = $('fontFam');
    if (ffSel && document.activeElement !== ffSel) {
      var cellF = SG.getDoc().cells[SG.sel.r + ':' + SG.sel.c];
      var ffv = (cellF && cellF.s && cellF.s.ff) ? cellF.s.ff : 'Arial';
      if ([...ffSel.options].some(function (o) { return o.value === ffv; })) ffSel.value = ffv;
      else ffSel.value = '';
    }
  }, 700);

  // 🧩 ปรับแต่ง toolbar: ลากได้ทุกที่ (ข้ามกลุ่ม/ข้ามแถว/เข้า-ออก ⋯) · คลิกขวา = สั้น/ยาว · จดจำถาวร
  (function tbCustom() {
    var KEY = 'xls2_toolbar_layout2';
    var morePop = $('morePop');
    var ribbonEl = document.querySelector('.ribbon');
    var fxbarEl = document.querySelector('.fxbar');
    function grps() { return [].slice.call(document.querySelectorAll('.ribbon .grp')); }
    function saveLayout() {
      var data = [];
      grps().forEach(function (g, gi) {
        g.querySelectorAll('.btn[id]').forEach(function (b) {
          if (b.closest('.swpop')) return;
          data.push({ id: b.id, g: gi, wide: b.classList.contains('wide') });
        });
      });
      fxbarEl.querySelectorAll('.btn[id]').forEach(function (b) { data.push({ id: b.id, fx: 1, wide: b.classList.contains('wide') }); });
      morePop.querySelectorAll('.btn[id]').forEach(function (b) { data.push({ id: b.id, more: 1, wide: b.classList.contains('wide') }); });
      localStorage.setItem(KEY, JSON.stringify(data));
    }
    function loadLayout() {
      var data; try { data = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) {}
      if (!data || !data.length) return;
      var gl = grps();
      data.forEach(function (rec) {
        var el = document.getElementById(rec.id);
        if (!el || !el.classList.contains('btn')) return;
        var host = rec.more ? morePop : (rec.fx ? fxbarEl : gl[rec.g]);
        if (host) host.appendChild(el);
        el.classList.toggle('wide', !!rec.wide);
      });
    }
    var dragEl = null;
    [].slice.call(document.querySelectorAll('.ribbon .btn[id], #morePop .btn[id], #fontFam')).forEach(function (b) {
      b.draggable = true;
      b.addEventListener('dragstart', function (e) { dragEl = b; try { e.dataTransfer.setData('text', b.id); } catch (er) {} });
      b.addEventListener('contextmenu', function (e) {
        e.preventDefault(); e.stopPropagation();
        b.classList.toggle('wide');
        saveLayout();
      });
    });
    // คลิกขวาที่ปุ่ม/ช่องฟอนต์ใดๆ บนแถบเครื่องมือ = ยุบ/ขยายข้อความ (ทำงานแม้ย้ายไปแถวค้นหา · กันเมนู Excel เด้ง)
    document.addEventListener('contextmenu', function (e) {
      var b = e.target.closest('.ribbon .btn[id], .fxbar .btn[id]');
      if (!b) return;
      if (e.target.closest('.swpop')) return;   // ในกล่อง popup ไม่ต้องยุบ
      e.preventDefault(); e.stopPropagation();
      b.classList.toggle('wide');
      saveLayout();
    }, true);
    function dropAt(host, e) {
      if (!dragEl) return;
      var tgt = e.target.closest('.btn[id]');
      if (tgt && tgt !== dragEl && !tgt.closest('.swpop')) {
        var r = tgt.getBoundingClientRect();
        tgt.parentElement.insertBefore(dragEl, e.clientX < r.left + r.width / 2 ? tgt : tgt.nextSibling);
      } else {
        var container = e.target.closest('.grp');
        if (container && host === ribbonEl) { container.appendChild(dragEl); }
        else {
          // พื้นที่ว่าง: หาปุ่มที่ใกล้ที่สุดในแถวเดียวกัน แล้วแทรกข้างๆ
          var best = null, bd = 1e9;
          host.querySelectorAll('.btn[id]').forEach(function (b) {
            if (b === dragEl || b.closest('.swpop')) return;
            var br = b.getBoundingClientRect();
            if (Math.abs((br.top + br.height / 2) - e.clientY) > 24) return;   // เฉพาะแถวเดียวกัน
            var d = Math.abs((br.left + br.width / 2) - e.clientX);
            if (d < bd) { bd = d; best = b; }
          });
          if (best) {
            var br2 = best.getBoundingClientRect();
            best.parentElement.insertBefore(dragEl, e.clientX < br2.left + br2.width / 2 ? best : best.nextSibling);
          } else if (host === morePop) morePop.appendChild(dragEl);
          else if (host === fxbarEl) fxbarEl.appendChild(dragEl);
          else (grps().slice(-1)[0] || host).appendChild(dragEl);
        }
      }
      dragEl = null;
      saveLayout();
    }
    [ribbonEl, fxbarEl, morePop].forEach(function (host) {
      host.addEventListener('dragover', function (e) { e.preventDefault(); });
      host.addEventListener('drop', function (e) { e.preventDefault(); e.stopPropagation(); dropAt(host, e); });
    });
    // ลากไอคอนมาวางที่ปุ่ม ⋯ = เก็บไอคอนนั้นเข้าเมนู (ออกจากแถบ)
    var moreBtn = document.getElementById('btnMore');
    if (moreBtn) {
      moreBtn.addEventListener('dragover', function (e) { e.preventDefault(); e.stopPropagation(); moreBtn.classList.add('drophot'); });
      moreBtn.addEventListener('dragleave', function () { moreBtn.classList.remove('drophot'); });
      moreBtn.addEventListener('drop', function (e) {
        e.preventDefault(); e.stopPropagation(); moreBtn.classList.remove('drophot');
        if (dragEl && dragEl !== moreBtn && !dragEl.closest('.swpop')) { morePop.appendChild(dragEl); dragEl = null; saveLayout(); if (typeof groupMorePop === 'function') groupMorePop(); }
      });
    }
    loadLayout();
    // ปุ่มไฟล์ (บันทึก/บันทึกเป็น/เปิดเก่า) ต้องอยู่รวมในเมนูเดียวเสมอ — กันโดนลากแยกออก
    ['btnSaveAs', 'btnVersions', 'btnBackup', 'btnRestore', 'btnGDrive'].forEach(function (id) {
      var b = document.getElementById(id);
      if (b) { if (!b.closest('#filePop')) document.getElementById('filePop').appendChild(b); b.draggable = false; }
    });
    try {
      var L = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (L && L.length) { var L2 = L.filter(function (r) { return ['btnSaveAs', 'btnVersions', 'btnBackup', 'btnRestore', 'btnGDrive'].indexOf(r.id) < 0; }); if (L2.length !== L.length) localStorage.setItem(KEY, JSON.stringify(L2)); }
    } catch (e) {}
  })();

  // ⏀ ย่อ/ขยายชุดเครื่องมือแต่ละกลุ่มได้เอง (จดจำถาวร) — คลิกลูกศรเล็กหน้ากลุ่ม หรือดับเบิลคลิกพื้นว่างของกลุ่ม
  (function grpCollapse() {
    var KEY = 'xls2_grp_collapsed';
    function load() { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; } }
    function save(a) { localStorage.setItem(KEY, JSON.stringify(a)); }
    var grps = [].slice.call(document.querySelectorAll('.ribbon .grp')).filter(function (g) {
      return !g.classList.contains('grp-status') && g.querySelector('.btn');   // ข้ามกลุ่มว่าง (ปุ่มถูกย้ายออกหมดแล้ว)
    });
    grps.forEach(function (g, i) {
      var h = document.createElement('button');
      h.className = 'grp-tg';
      h.title = 'ย่อ/ขยายชุดเครื่องมือนี้';
      h.textContent = '▾';
      g.insertBefore(h, g.firstChild);
      function toggle() {
        g.classList.toggle('clps');
        var arr = load().filter(function (x) { return x !== i; });
        if (g.classList.contains('clps')) arr.push(i);
        save(arr);
      }
      h.onclick = function (e) { e.stopPropagation(); toggle(); };
      g.addEventListener('dblclick', function (e) { if (e.target === g) toggle(); });
    });
    load().forEach(function (i) { if (grps[i]) grps[i].classList.add('clps'); });
  })();

  // Esc ปิดหน้าต่าง/เมนูทุกชนิดของโปรแกรม
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    document.querySelectorAll('.modal.open').forEach(function (m) { m.classList.remove('open'); });
    ['swPop', 'fontPop', 'bdPop', 'morePop'].forEach(function (id) { var p = $(id); if (p) p.classList.remove('open'); });
  });

  window.addEventListener('beforeunload', function (e) { if (SG.isDirty()) { e.preventDefault(); e.returnValue = ''; } });
  window.$ = $; window.refresh = refresh; window.renderSheets = renderSheets;
/* ── จบ core (เดิมอยู่ใน IIFE) ── */

