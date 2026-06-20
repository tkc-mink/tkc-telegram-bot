/* หน้าตั้งค่า: Margin/หัวตาราง/แถวพิเศษ/เชื่อมต่อ DB + openSettings + switchSetTab
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดต่อเนื่องตามลำดับก่อน price-update.js */
  // ---- Margin ± colors ----
  var condSel = { pos: null, neg: null };
  // ระบบพรีวิวก่อนบันทึก: เปลี่ยนสีในแท็บจะไม่มีผลจริงจนกว่าจะกดบันทึก
  var pend = {};
  var COLOR_KEYS = ['xls2_dragcolor', 'xls2_dragbg', 'xls2_clipcolor', 'xls2_clipbg', 'xls2_rowhdrbg', 'xls2_rowhdrfg', 'xls2_colhdrbg', 'xls2_colhdrfg', 'xls2_admbg', 'xls2_admfg', 'xls2_admpat', 'xls2_lockicon', 'xls2_dblinkok', 'xls2_dblinkbad', 'xls2_dblinktipfs', 'xls2_dblinktipfg', 'xls2_dblinktipbg'];
  // สีสถานะลิงก์ DB (แถบเลขแถว) — เชื่อมปกติ / ลิงก์ค้าง + สไตล์ป๊อปอัปชื่อสินค้า
  var DBLINK_DEF = { ok: '15A34A', bad: 'E5322E', tipfs: '12', tipfg: 'FFFFFF', tipbg: '333333' };
  function dblinkColor(which) { return ((localStorage.getItem('xls2_dblink' + which) || '').replace('#', '')) || DBLINK_DEF[which]; }
  function applyDbLinkColors() {
    document.documentElement.style.setProperty('--dblink-ok', '#' + dblinkColor('ok'));
    document.documentElement.style.setProperty('--dblink-bad', '#' + dblinkColor('bad'));
    document.documentElement.style.setProperty('--linktip-fs', (parseInt(localStorage.getItem('xls2_dblinktipfs'), 10) || DBLINK_DEF.tipfs) + 'px');
    document.documentElement.style.setProperty('--linktip-fg', '#' + dblinkColor('tipfg'));
    document.documentElement.style.setProperty('--linktip-bg', '#' + dblinkColor('tipbg'));
    document.documentElement.style.setProperty('--lock-icon', '"' + (localStorage.getItem('xls2_lockglyph') || '🔒') + '"');
  }
  applyDbLinkColors();
  function updDbLinkPrev() {
    var ok = '#' + ((pv('xls2_dblinkok').replace('#', '')) || DBLINK_DEF.ok);
    var bad = '#' + ((pv('xls2_dblinkbad').replace('#', '')) || DBLINK_DEF.bad);
    var po = $('dblinkPrevOk'), pb = $('dblinkPrevBad');
    if (po) { po.style.setProperty('--c', ok); po.querySelector('.dblink-prev-num').style.color = ok; }
    if (pb) { pb.style.setProperty('--c', bad); pb.querySelector('.dblink-prev-num').style.color = bad; }
    // พรีวิวป๊อปอัปชื่อสินค้า
    var fs = parseInt(pv('xls2_dblinktipfs'), 10) || DBLINK_DEF.tipfs;
    var fg = '#' + ((pv('xls2_dblinktipfg').replace('#', '')) || DBLINK_DEF.tipfg);
    var bg = '#' + ((pv('xls2_dblinktipbg').replace('#', '')) || DBLINK_DEF.tipbg);
    var prev = $('dblinkTipPrev');
    if (prev) { prev.style.fontSize = fs + 'px'; prev.style.color = fg; prev.style.background = bg; }
    var fsv = $('dblinkTipFsVal'); if (fsv) fsv.textContent = fs + 'px';
    // ไอคอน/คำอธิบายแม่กุญแจ
    var lg = $('lockGlyphInp'), ld = $('lockDescInp');
    if (lg && !lg._wired) {
      lg._wired = 1;
      lg.value = localStorage.getItem('xls2_lockglyph') || '🔒';
      ld.value = localStorage.getItem('xls2_lockdesc') || 'ซ่อนจากผู้ใช้';
      function saveLock() {
        var g = (lg.value || '🔒').trim() || '🔒';
        localStorage.setItem('xls2_lockglyph', g);
        localStorage.setItem('xls2_lockdesc', (ld.value || '').trim() || 'ซ่อนจากผู้ใช้');
        document.documentElement.style.setProperty('--lock-icon', '"' + g + '"');
        if (window.SG) SG.render();
      }
      lg.oninput = saveLock; ld.oninput = saveLock;
    }
  }
  function buildStatIconList() {
    var host = $('statIconList'); if (!host || !window.DBX) return;
    var defs = ((statWork && statWork.length) ? statWork : window.DBX.statusDefs()).slice().sort(function (a, b) { return (a.priority || 99) - (b.priority || 99); });
    var condLabel = function (c) {
      if (!c) return '';
      if (c.indexOf('flag:') === 0) return 'ธงสินค้า: ' + c.slice(5) + ' (flags)';
      return ({ out: 'คงเหลือ = 0 (qtyOnHand)', avail0: 'สุทธิ = 0 (qtyAvailable)', full: 'ครบชุด (qtyAvailable)', reservedPartial: 'ติดจองไม่ครบชุด (qtyReserved)', shortStock: 'ของไม่ถึงชุด (qtyOnHand)', incoming: 'ของกำลังเข้า (incoming/incomingInfo)' }[c]) || c;
    };
    host.innerHTML = defs.map(function (d, i) {
      return '<div class="stdef" draggable="true" data-key="' + d.key + '" data-i="' + i + '">' +
        '<span class="stdef-num">' + (i + 1) + '</span>' +
        '<span class="stdef-drag" title="ลากเรียงลำดับ">⠿</span>' +
        '<button type="button" class="stdef-icon stdef-iconglyph" data-icon="' + (d.icon || '').replace(/"/g, '&quot;') + '" title="คลิกเพื่อเลือกไอคอน" style="color:#' + (d.color || '888888') + '">' + (d.icon ? (window.IconKit ? IconKit.html(d.icon) : (d.icon + '\uFE0E')) : '＋') + '</button>' +
        '<input type="color" class="stdef-color" value="#' + (d.color || '888888') + '" title="สีไอคอน (เติมข้างใน · ขอบดำ)">' +
        '<input class="stdef-label" value="' + (d.label || '').replace(/"/g, '&quot;') + '" placeholder="ชื่อสถานะ">' +
        '<input class="stdef-popup" value="' + (d.popup || '').replace(/"/g, '&quot;') + '" placeholder="คำอธิบาย (popup)">' +
        '<span class="stdef-link' + (d.cond ? '' : ' nolink') + '" title="' + (d.cond ? ('🔗 ผูกกับข้อมูลสินค้า: ' + condLabel(d.cond) + ' · อ้างอิงจากรหัสสินค้า (code13) ที่ผูกในแถวนั้น · เปลี่ยนชื่อ/ไอคอน/สีได้ ลิงก์ไม่เปลี่ยน') : 'ไม่ผูกเงื่อนไข (สถานะกำหนดเอง)') + '">' + (d.cond ? '🔗' : '✎') + '</span>' +
        '<label class="stdef-en" title="เปิด/ปิด"><input type="checkbox"' + (d.enabled !== false ? ' checked' : '') + '></label>' +
        '<span class="stdef-del" title="ลบ">✕</span>' +
        '</div>';
    }).join('');
    function collect() {
      var arr = [];
      host.querySelectorAll('.stdef').forEach(function (row, idx) {
        var key = row.dataset.key;
        var base = defs.filter(function (x) { return x.key === key; })[0] || {};
        arr.push({
          key: key, kind: base.kind || 'icon', cond: base.cond || '',
          icon: row.querySelector('.stdef-icon').dataset.icon || '',
          color: row.querySelector('.stdef-color').value.replace('#', ''),
          label: row.querySelector('.stdef-label').value,
          popup: row.querySelector('.stdef-popup').value,
          enabled: row.querySelector('.stdef-en input').checked,
          priority: idx + 1
        });
      });
      window.statWork = arr; statWork = arr;   // เก็บลงบัฟเฟอร์ (ยังไม่ใช้งานจริงจนกดบันทึก)
    }
    host.oninput = function (e) {
      if (e && e.target && e.target.classList.contains('stdef-color')) {
        var row = e.target.closest('.stdef'); var g = row && row.querySelector('.stdef-iconglyph');
        if (g) g.style.color = e.target.value;
      }
      collect();
    };
    host.onchange = collect;
    host.onclick = function (e) {
      var del = e.target.closest('.stdef-del');
      if (del) { var row = del.closest('.stdef'); row.parentNode.removeChild(row); collect(); buildStatIconList(); return; }
      var ib = e.target.closest('.stdef-icon');
      if (ib) {
        openEmojiPicker(ib, ib.dataset.icon || '', function (emo) {
          ib.dataset.icon = emo; ib.innerHTML = emo ? (window.IconKit ? IconKit.html(emo) : (emo + '\uFE0E')) : '＋'; collect();
        });
      }
    };
    // ลากเรียงลำดับ priority
    var dragRow = null;
    host.addEventListener('dragstart', function (e) { dragRow = e.target.closest('.stdef'); if (dragRow) dragRow.classList.add('stdef-dragging'); });
    host.addEventListener('dragend', function () { if (dragRow) dragRow.classList.remove('stdef-dragging'); dragRow = null; });
    host.addEventListener('dragover', function (e) {
      e.preventDefault(); var over = e.target.closest('.stdef'); if (!over || over === dragRow || !dragRow) return;
      var rect = over.getBoundingClientRect(); var after = e.clientY > rect.top + rect.height / 2;
      host.insertBefore(dragRow, after ? over.nextSibling : over);
    });
    host.addEventListener('drop', function (e) { e.preventDefault(); collect(); });
  }
  function buildDbLinkGrids() {
    if (!$('dblinkOkGrid')) return;
    cfBuild($('dblinkOkGrid'), { ns: 'dblink_ok', mode: 'block', mainDef: CF_SET_MAIN, current: function () { return pv('xls2_dblinkok').replace('#', '') || DBLINK_DEF.ok; }, onPick: function (hex) { pend['xls2_dblinkok'] = hex || DBLINK_DEF.ok; updDbLinkPrev(); } });
    cfBuild($('dblinkBadGrid'), { ns: 'dblink_bad', mode: 'block', mainDef: CF_SET_MAIN, current: function () { return pv('xls2_dblinkbad').replace('#', '') || DBLINK_DEF.bad; }, onPick: function (hex) { pend['xls2_dblinkbad'] = hex || DBLINK_DEF.bad; updDbLinkPrev(); } });
    cfBuild($('dblinkTipFgGrid'), { ns: 'dblink_tipfg', mode: 'font', mainDef: CF_SET_MAIN, current: function () { return pv('xls2_dblinktipfg').replace('#', '') || DBLINK_DEF.tipfg; }, onPick: function (hex) { pend['xls2_dblinktipfg'] = hex || DBLINK_DEF.tipfg; updDbLinkPrev(); } });
    cfBuild($('dblinkTipBgGrid'), { ns: 'dblink_tipbg', mode: 'block', mainDef: CF_SET_FILL, current: function () { return pv('xls2_dblinktipbg').replace('#', '') || DBLINK_DEF.tipbg; }, onPick: function (hex) { pend['xls2_dblinktipbg'] = hex || DBLINK_DEF.tipbg; updDbLinkPrev(); } });
    var fsInput = $('dblinkTipFs');
    if (fsInput) { fsInput.value = parseInt(pv('xls2_dblinktipfs'), 10) || DBLINK_DEF.tipfs; fsInput.oninput = function () { pend['xls2_dblinktipfs'] = this.value; updDbLinkPrev(); }; }
    updDbLinkPrev();
  }
  var setUndoSnap = null;
  var statWork = null;   // บัฟเฟอร์แก้ไขไอคอนสถานะ — ใช้งานจริงเมื่อกดบันทึก
  function pv(key) { return (key in pend) ? pend[key] : (localStorage.getItem(key) || ''); }
  function snapshotSettings() { var o = { cond: SG.getCondColors() }; COLOR_KEYS.forEach(function (k) { o[k] = localStorage.getItem(k); }); return o; }
  function restoreSettings(o) { COLOR_KEYS.forEach(function (k) { if (o[k] == null) localStorage.removeItem(k); else localStorage.setItem(k, o[k]); }); applyMarkColors(); applyHdrColors(); applyAdmStyle(); applyDbLinkColors(); if (o.cond) SG.setCondColors(o.cond); }
  // สีหลักมาตรฐานสำหรับฟังก์ชันสีในหน้าตั้งค่า (สีตัวอักษร/พื้น/เส้น)
  var CF_SET_MAIN = [['000000', 'ดำ'], ['808080', 'เทา'], ['C00000', 'แดงเข้ม'], ['FF0000', 'แดง'], ['F47C20', 'ส้ม'], ['008000', 'เขียว'], ['2A6FDB', 'น้ำเงิน'], ['7030A0', 'ม่วง']];
  var CF_SET_FILL = [['FFFF00', 'เหลือง'], ['FFE3C2', 'ส้มอ่อน'], ['CCFFCC', 'เขียวอ่อน'], ['CCFFFF', 'ฟ้าอ่อน'], ['FFCCFF', 'ชมพูอ่อน'], ['EFEFEF', 'เทาอ่อน'], ['FF9900', 'ส้ม'], ['92D050', 'เขียว']];
  function buildCondGrid(hostId, kind) {
    var host = $(hostId); if (!host) return;
    cfBuild(host, {
      ns: 'cond_' + kind, mode: 'font', mainDef: CF_SET_MAIN,
      current: function () { return condSel[kind] || (kind === 'pos' ? '008000' : 'C00000'); },
      onPick: function (hex) {
        condSel[kind] = hex || (kind === 'pos' ? '008000' : 'C00000');
        $('condPrevPos').style.color = '#' + (condSel.pos || '008000');
        $('condPrevNeg').style.color = '#' + (condSel.neg || 'C00000');
      }
    });
  }
  $('condChip').onclick = function (e) {
    e.stopPropagation();
    openSettings('margin');
  };
  if ($('dbSrcBadge')) $('dbSrcBadge').onclick = function (e) { e.stopPropagation(); openSettings('dbconn'); };
  updDbSrcBadge();
  // ลากหน้าต่างตั้งค่าด้วยหัว (แถบส้มด้านบน)
  (function () {
    var h = document.querySelector('#mCond .dlg h3'); if (!h) return;
    var dlg = document.querySelector('#mCond .dlg');
    h.style.cursor = 'grab'; var ox = 0, oy = 0, sx = 0, sy = 0, on = false;
    h.addEventListener('mousedown', function (e) {
      on = true; var m = (dlg.style.transform.match(/translate\(([-\d.]+)px,\s*([-\d.]+)px\)/));
      ox = m ? parseFloat(m[1]) : 0; oy = m ? parseFloat(m[2]) : 0; sx = e.clientX; sy = e.clientY;
      document.addEventListener('mousemove', mv, true); document.addEventListener('mouseup', up, true); e.preventDefault();
    });
    function mv(e) { if (!on) return; dlg.style.transform = 'translate(' + (ox + e.clientX - sx) + 'px,' + (oy + e.clientY - sy) + 'px)'; }
    function up() { on = false; document.removeEventListener('mousemove', mv, true); document.removeEventListener('mouseup', up, true); }
  })();
  function openSettings(tab) {
    pend = {};
    var dlg0 = document.querySelector('#mCond .dlg'); if (dlg0) dlg0.style.transform = '';   // รีเซ็ตตำแหน่งลากทุกครั้งที่เปิด
    var cur = SG.getCondColors();
    condSel = { pos: cur.pos, neg: cur.neg };
    buildCondGrid('condPosGrid', 'pos');
    buildCondGrid('condNegGrid', 'neg');
    $('condPrevPos').style.color = '#' + cur.pos;
    $('condPrevNeg').style.color = '#' + cur.neg;
    buildMarkGrid('dragGrid', 'dragcolor', 'F47C20', false);
    buildMarkGrid('dragBgGrid', 'dragbg', '', true);
    buildMarkGrid('clipGrid', 'clipcolor', '0a8f3c', false);
    buildMarkGrid('clipBgGrid', 'clipbg', '', true);
    buildHdrGrid('rowhdrBgGrid', 'rowhdrbg', 'EFEFEF', '--rowhdr-bg');
    buildHdrGrid('rowhdrFgGrid', 'rowhdrfg', '777777', '--rowhdr-fg');
    buildHdrGrid('colhdrBgGrid', 'colhdrbg', 'FFE3C2', '--colhdr-bg');
    buildHdrGrid('colhdrFgGrid', 'colhdrfg', '8a4a0a', '--colhdr-fg');
    buildAdmColorGrid('admBgGrid', 'admbg');
    buildAdmColorGrid('admFgGrid', 'admfg');
    buildAdmExtras();
    buildDbLinkGrids();
    buildStatIconList();
    buildDbFieldList();
    buildPricingTab();
    buildConnTab();
    buildBackupTab();
    updAdmPrev();
    updHdrPrev();
    updMarkPrev('drag'); updMarkPrev('clip');
    switchSetTab(tab || 'margin');
    $('mCond').classList.add('open');
  }
  // ---- สีเส้นประ/พื้นหลัง ลาก/คัดลอก-ตัด-วาง ----
  var MARK_DEFAULT = { dragcolor: 'F47C20', clipcolor: '0a8f3c' };
  function rawMark(key) { return (localStorage.getItem('xls2_' + key) || ''); }
  function markColor(key) { return (rawMark(key).replace('#', '')) || MARK_DEFAULT[key] || ''; }
  function bgTint(key, defColor) {
    var v = rawMark(key);
    if (v === 'none') return 'transparent';
    v = v.replace('#', '');
    if (!v) return defColor ? '#' + defColor + '5a' : 'transparent';
    return '#' + v + '5a';
  }
  function applyMarkColors() {
    var dl = markColor('dragcolor'), cl = markColor('clipcolor');
    document.documentElement.style.setProperty('--fill-color', '#' + dl);
    document.documentElement.style.setProperty('--fill-bg', bgTint('dragbg', dl));
    document.documentElement.style.setProperty('--cpm-color', '#' + cl);
    document.documentElement.style.setProperty('--cpm-fade', '#' + cl + '40');
    document.documentElement.style.setProperty('--cpm-bg', bgTint('clipbg', ''));
  }
  function updMarkPrev(kind) {
    function mc(sk, def) { return (pv('xls2_' + sk).replace('#', '')) || def; }
    function bg(sk, defColor) { var v = pv('xls2_' + sk); if (v === 'none') return 'transparent'; v = v.replace('#', ''); if (!v) return defColor ? '#' + defColor + '5a' : 'transparent'; return '#' + v + '5a'; }
    if (kind === 'drag') {
      var dp = $('dragPrev'); if (dp) { dp.style.outline = '1.6px solid #' + mc('dragcolor', 'F47C20'); dp.style.background = bg('dragbg', mc('dragcolor', 'F47C20')); }
    } else {
      var cp = $('clipPrev'); if (cp) { cp.style.outline = '1.5px dashed #' + mc('clipcolor', '0a8f3c'); cp.style.background = bg('clipbg', ''); }
    }
  }
  function buildMarkGrid(hostId, storeKey, defColor, isBg) {
    var host = $(hostId); if (!host) return;
    var fullKey = 'xls2_' + storeKey;
    var which = storeKey.indexOf('drag') === 0 ? 'drag' : 'clip';
    cfBuild(host, {
      ns: 'mark_' + storeKey, mode: isBg ? 'fill' : 'block', mainDef: isBg ? CF_SET_FILL : CF_SET_MAIN,
      allowNone: isBg, noneLabel: 'ไม่มีพื้นหลัง',
      current: function () { var v = pv(fullKey); if (isBg && v === 'none') return null; v = v.replace('#', ''); return v || (isBg ? null : (defColor || '')); },
      onPick: function (hex) { pend[fullKey] = (hex == null ? (isBg ? 'none' : '') : hex); updMarkPrev(which); }
    });
  }
  applyMarkColors();
  // ---- สีหัวแถว/หัวคอลัมน์ (ตกแต่งแยกกัน) ----
  var HDR_DEF = { rowhdrbg: 'EFEFEF', rowhdrfg: '777777', colhdrbg: 'FFE3C2', colhdrfg: '8a4a0a' };
  function hdrColor(k) { return ((localStorage.getItem('xls2_' + k) || '').replace('#', '')) || HDR_DEF[k]; }
  function applyHdrColors() {
    document.documentElement.style.setProperty('--rowhdr-bg', '#' + hdrColor('rowhdrbg'));
    document.documentElement.style.setProperty('--rowhdr-fg', '#' + hdrColor('rowhdrfg'));
    document.documentElement.style.setProperty('--colhdr-bg', '#' + hdrColor('colhdrbg'));
    document.documentElement.style.setProperty('--colhdr-fg', '#' + hdrColor('colhdrfg'));
  }
  function updHdrPrev() {
    function hc(k) { return (pv('xls2_' + k).replace('#', '')) || HDR_DEF[k]; }
    var rp = $('rowhdrPrev'); if (rp) { rp.style.background = '#' + hc('rowhdrbg'); rp.style.color = '#' + hc('rowhdrfg'); }
    var cp = $('colhdrPrev'); if (cp) { cp.style.background = '#' + hc('colhdrbg'); cp.style.color = '#' + hc('colhdrfg'); }
  }
  function buildHdrGrid(hostId, storeKey, def, cssVar) {
    var host = $(hostId); if (!host) return;
    var fullKey = 'xls2_' + storeKey;
    var isBg = /bg$/.test(storeKey);
    cfBuild(host, {
      ns: 'hdr_' + storeKey, mode: isBg ? 'fill' : 'block', mainDef: isBg ? CF_SET_FILL : CF_SET_MAIN,
      current: function () { return (pv(fullKey).replace('#', '') || HDR_DEF[storeKey]); },
      onPick: function (hex) { pend[fullKey] = hex || HDR_DEF[storeKey]; updHdrPrev(); }
    });
  }
  applyHdrColors();
  // ---- แถว/คอลัมน์พิเศษ (ล็อก ซ่อนจากผู้ใช้) ----
  var LOCK_ICONS = ['\uD83D\uDD12', '\uD83D\uDC51', '\u2B50', '\uD83D\uDEE1\uFE0F', '\uD83D\uDC8E', '\uD83D\uDD11', '\uD83D\uDEAB', '\uD83D\uDCCC', '\u26A1', '\uD83D\uDD25'];
  function hexRgb(h) { h = (h || '').replace('#', ''); if (h.length === 3) h = h.split('').map(function (x) { return x + x; }).join(''); if (h.length !== 6) return '192,57,43'; var n = parseInt(h, 16); return ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255); }
  function patCss(p, hex) { var c = hexRgb(hex); if (p === 'dots') return 'radial-gradient(rgba(' + c + ',.5) 1.1px, transparent 1.6px)'; if (p === 'none') return 'none'; return 'repeating-linear-gradient(45deg, rgba(' + c + ',.22) 0 4px, transparent 4px 8px)'; }
  function applyAdmStyle() {
    var bg = (localStorage.getItem('xls2_admbg') || '').replace('#', '');
    var fg = (localStorage.getItem('xls2_admfg') || '').replace('#', '');
    var pat = localStorage.getItem('xls2_admpat') || 'stripe';
    var ic = localStorage.getItem('xls2_lockicon') || '\uD83D\uDD12';
    var rs = document.documentElement.style;
    rs.setProperty('--adm-bg', bg ? '#' + bg : 'transparent');
    rs.setProperty('--adm-fg', fg ? '#' + fg : 'inherit');
    rs.setProperty('--adm-pat', patCss(pat, fg || bg));
    rs.setProperty('--adm-patsize', pat === 'dots' ? '6px 6px' : 'auto');
    rs.setProperty('--lock-icon', '"' + ic + '"');
  }
  function updAdmPrev() {
    var p = $('admPrev'); if (!p) return;
    var bg = (pv('xls2_admbg').replace('#', '')) , fg = (pv('xls2_admfg').replace('#', ''));
    var pat = pv('xls2_admpat') || 'stripe', ic = pv('xls2_lockicon') || '\uD83D\uDD12';
    p.style.backgroundColor = bg ? '#' + bg : '#fff5f4';
    p.style.color = fg ? '#' + fg : '#333';
    p.style.backgroundImage = patCss(pat, fg || bg);
    p.style.backgroundSize = pat === 'dots' ? '6px 6px' : 'auto';
    p.textContent = 'ตัวอย่างแถว/คอลัมน์พิเศษ ' + ic;
  }
  function buildAdmColorGrid(hostId, storeKey) {
    var host = $(hostId); if (!host) return;
    var fullKey = 'xls2_' + storeKey;
    var isBg = /bg$/.test(storeKey);
    cfBuild(host, {
      ns: 'adm_' + storeKey, mode: isBg ? 'fill' : 'block', mainDef: isBg ? CF_SET_FILL : CF_SET_MAIN,
      allowNone: true, noneLabel: 'ไม่กำหนด (ค่าเดิม)',
      current: function () { var v = pv(fullKey).replace('#', ''); return v ? v : null; },
      onPick: function (hex) { pend[fullKey] = hex || ''; updAdmPrev(); }
    });
  }
  function buildAdmExtras() {
    var pp = $('admPatPick');
    if (pp) { var curp = pv('xls2_admpat') || 'stripe'; pp.querySelectorAll('.pat-opt').forEach(function (o) { o.classList.toggle('on', o.dataset.pat === curp); o.onclick = function () { pend['xls2_admpat'] = o.dataset.pat; pp.querySelectorAll('.pat-opt').forEach(function (x) { x.classList.remove('on'); }); o.classList.add('on'); updAdmPrev(); }; }); }
    var ip = $('lockIconPick');
    if (ip) { ip.innerHTML = ''; var curi = pv('xls2_lockicon') || '\uD83D\uDD12'; LOCK_ICONS.forEach(function (em) { var o = document.createElement('span'); o.className = 'ic-opt' + (em === curi ? ' on' : ''); o.textContent = em; o.onclick = function () { pend['xls2_lockicon'] = em; ip.querySelectorAll('.ic-opt').forEach(function (x) { x.classList.remove('on'); }); o.classList.add('on'); updAdmPrev(); }; ip.appendChild(o); }); }
  }
  applyAdmStyle();
  function switchSetTab(name) {
    document.querySelectorAll('#mCond .settab').forEach(function (b) { b.classList.toggle('on', b.dataset.tab === name); });
    document.querySelectorAll('#mCond .settab-pane').forEach(function (p) { p.style.display = p.dataset.pane === name ? '' : 'none'; });
    if (typeof colorizeTabs === 'function') colorizeTabs();
    $('condOk').style.display = (name === 'margin' || name === 'tablecolors' || name === 'special' || name === 'dblink' || name === 'pricing') ? '' : 'none';
  }
  function buildDbFieldList() {
    var host = $('dbfList'); if (!host || !window.DBX) return;
    var esc = function (s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); };
    var groups = window.DBX.allGroups();
    var custFieldKeys = {}; window.DBX.customFields().forEach(function (f) { custFieldKeys[f.key] = 1; });
    var custCats = window.DBX.customCats();
    var html = groups.map(function (g) {
      var fields = window.DBX.fieldsInGroup(g);
      var isCustomCat = custCats.indexOf(g) >= 0;
      var rows = fields.map(function (f) {
        var isCust = !!custFieldKeys[f.key];
        var on = window.DBX.isFieldEnabled(f.key);
        return '<div class="dbf-field' + (on ? '' : ' off') + '"><span class="dbf-ic">' + (f.writable ? '✏️' : (isCust ? '🔗' : '🔒')) + '</span>' +
          '<span class="dbf-flabel">' + esc(f.label) + '</span><span class="dbf-fkey">' + esc(f.key) + '</span>' +
          '<label class="dbf-tog" title="เปิด/ปิดการแสดงในเมนูผูกคอลัมน์"><input type="checkbox" data-togfield="' + esc(f.key) + '"' + (on ? ' checked' : '') + '></label>' +
          (isCust ? '<button class="dbf-del" data-delfield="' + esc(f.key) + '" title="ลบฟิลด์">✕</button>' : '<span class="dbf-sys" title="ฟิลด์ระบบ ลบไม่ได้">🔧</span>') + '</div>';
      }).join('') || '<div class="dbf-empty">— ยังไม่มีฟิลด์ —</div>';
      return '<div class="dbf-cat"><div class="dbf-cathead"><b>' + esc(g) + '</b>' +
        (isCustomCat ? '<button class="dbf-del" data-delcat="' + esc(g) + '" title="ลบหมวด (เฉพาะที่ว่าง)">✕</button>' : '<span class="dbf-sys" title="หมวดระบบ">🔧</span>') +
        '</div>' + rows + '</div>';
    }).join('');
    host.innerHTML = html;
    // เติม dropdown หมวดสำหรับเพิ่มฟิลด์
    var sel = $('dbfNewGroup');
    if (sel) sel.innerHTML = groups.map(function (g) { return '<option value="' + esc(g) + '">' + esc(g) + '</option>'; }).join('');
    host.onclick = function (e) {
      var tog = e.target.closest('[data-togfield]');
      if (tog) {
        window.DBX.setFieldEnabled(tog.dataset.togfield, tog.checked);
        var row = tog.closest('.dbf-field'); if (row) row.classList.toggle('off', !tog.checked);
        if (window.SG) { if (SG.clearDbCache) SG.clearDbCache(); SG.render(); }
        return;
      }
      var df = e.target.closest('[data-delfield]');
      if (df) {
        var arr = window.DBX.customFields().filter(function (x) { return x.key !== df.dataset.delfield; });
        window.DBX.saveCustomFields(arr); buildDbFieldList();
        if (window.SG) { if (SG.clearDbCache) SG.clearDbCache(); SG.render(); }
        return;
      }
      var dc = e.target.closest('[data-delcat]');
      if (dc) {
        var g = dc.dataset.delcat;
        if (window.DBX.fieldsInGroup(g).length) { if (typeof toast === 'function') toast('ลบไม่ได้: ย้าย/ลบฟิลด์ในหมวดนี้ก่อน'); return; }
        window.DBX.saveCustomCats(window.DBX.customCats().filter(function (x) { return x !== g; })); buildDbFieldList();
      }
    };
  }
  (function wireDbFieldAdd() {
    document.addEventListener('DOMContentLoaded', function () {});
    var addCat = $('dbfAddCat'), addField = $('dbfAddField');
    if (addCat) addCat.onclick = function () {
      var v = ($('dbfNewCat').value || '').trim(); if (!v || !window.DBX) return;
      if (window.DBX.allGroups().indexOf(v) >= 0) { if (typeof toast === 'function') toast('มีหมวดนี้อยู่แล้ว'); return; }
      window.DBX.saveCustomCats(window.DBX.customCats().concat([v])); $('dbfNewCat').value = ''; buildDbFieldList();
    };
    if (addField) addField.onclick = function () {
      if (!window.DBX) return;
      var g = $('dbfNewGroup').value, key = ($('dbfNewKey').value || '').trim(), label = ($('dbfNewLabel').value || '').trim();
      if (!g || !key || !label) { if (typeof toast === 'function') toast('กรอกหมวด + key + ชื่อให้ครบ'); return; }
      if (window.DBX.allFields().some(function (f) { return f.key === key; })) { if (typeof toast === 'function') toast('มี field key นี้อยู่แล้ว'); return; }
      window.DBX.saveCustomFields(window.DBX.customFields().concat([{ key: key, label: label, group: g }]));
      $('dbfNewKey').value = ''; $('dbfNewLabel').value = ''; buildDbFieldList();
    };
  })();
  window.openDbFieldManager = function () { openSettings('dbfields'); };

  // ---------- แท็บเชื่อมต่อ DB [#7] ----------
  function buildConnTab() {
    if (!window.DBX || !$('connUrl')) return;
    var cfg = DBX.config();
    $('connUrl').value = cfg.baseUrl || '';
    $('connToken').value = cfg.token || '';
    if ($('connUser')) $('connUser').value = cfg.username || '';
    if ($('connPass')) $('connPass').value = cfg.password || '';
    if ($('connFlag')) $('connFlag').value = cfg.flag || 'PRICE';
    $('connUseAuth').checked = !!cfg.useAuth;
    $('connTimeout').value = cfg.timeoutMs ? Math.round(cfg.timeoutMs / 1000) : 12;
    setConnMode(cfg.adapter === 'http' ? 'http' : 'mock');
    $('connStatus').textContent = ''; $('connStatus').className = 'conn-status';
    document.querySelectorAll('#connMode button').forEach(function (b) {
      b.onclick = function () {
        setConnMode(b.dataset.mode);
        if (b.dataset.mode === 'mock') {   // กดจำลอง → ใช้ข้อมูลจำลองชุดใหม่ทันที (อัพเดท)
          DBX.setConfig({ adapter: 'mock' }); DBX.applyAdapter();
          if (window.SG) { if (SG.clearDbCache) SG.clearDbCache(); SG.render(); }
          updDbSrcBadge();
          var st = $('connStatus'); st.className = 'conn-status ok'; st.textContent = '🔄 จำลองชุดใหม่ #' + (DBX.mockSeed ? DBX.mockSeed() : '') + ' — สุ่มสต็อก/ปี DOT/ของเข้าใหม่ (ราคาคงที่ตามชุดข้อมูลจริง)';
        }
      };
    });
    $('connTest').onclick = function () {
      var st = $('connStatus'); st.className = 'conn-status busy'; st.textContent = '⏳ กำลังทดสอบ…';
      DBX.testConnection(readConnForm()).then(function (r) {
        if (r.ok) { st.className = 'conn-status ok'; st.textContent = '✅ เชื่อมต่อสำเร็จ (' + r.ms + ' ms' + (r.count != null ? ' · ' + r.count + ' รายการ' : '') + ')'; }
        else { st.className = 'conn-status err'; st.textContent = '❌ ' + r.error; }
      });
    };
    $('connSave').onclick = function () {
      DBX.setConfig(readConnForm()); DBX.applyAdapter();
      if (window.SG) { if (SG.clearDbCache) SG.clearDbCache(); SG.render(); }
      updDbSrcBadge();
      var st = $('connStatus'); st.className = 'conn-status ok';
      st.textContent = '💾 บันทึกแล้ว · ใช้แหล่ง: ' + (DBX.adapter().kind === 'http' ? 'เซิร์ฟเวอร์จริง' : 'ข้อมูลจำลอง');
      if (typeof toast === 'function') toast('บันทึกการเชื่อมต่อแล้ว');
    };
  }
  // ป้ายแหล่งข้อมูลบนแถบเครื่องมือ [#1]
  function updDbSrcBadge() {
    var b = $('dbSrcBadge'); if (!b || !window.DBX) return;
    var live = DBX.adapter().kind === 'http';
    b.classList.toggle('dbsrc-mock', !live);
    if (!live) {
      b.classList.remove('dbsrc-live', 'dbsrc-bad');
      b.querySelector('.dbsrc-txt').textContent = 'จำลอง';
      b.title = 'กำลังใช้ข้อมูลจำลอง (Mock) — คลิกเพื่อตั้งค่าการเชื่อมต่อ';
      return;
    }
    // http: ตรวจสุขภาพการเชื่อมต่อจริง → เขียว=ต่อได้ · แดง=ต่อไม่ได้
    b.classList.add('dbsrc-live'); b.classList.remove('dbsrc-bad');
    b.querySelector('.dbsrc-txt').textContent = 'เช็ค…';
    b.title = 'กำลังตรวจการเชื่อมต่อ…';
    function snapAge() {
      try {
        var inf = DBX.snapshotInfo && DBX.snapshotInfo();
        if (!inf || !inf.ts) return '';
        var mins = Math.floor((Date.now() - inf.ts) / 60000);
        var t = mins < 60 ? (mins + ' นาที') : (Math.floor(mins / 60) + ' ชม.' + (mins % 60 ? ' ' + (mins % 60) + ' น.' : ''));
        return ' · ราคาเก่า ' + t + (inf.enc ? ' 🔒' : '');
      } catch (e) { return ''; }
    }
    DBX.testConnection().then(function (r) {
      var ok = !!(r && r.ok);
      b.classList.toggle('dbsrc-live', ok);
      b.classList.toggle('dbsrc-bad', !ok);
      var age = ok ? '' : snapAge();
      b.querySelector('.dbsrc-txt').textContent = ok ? 'จริง (Live)' : ('ออฟไลน์' + age);
      b.title = ok ? ('✅ เชื่อมเซิร์ฟเวอร์จริงได้' + (r.count != null ? ' · ' + r.count + ' รายการ' : '')) : ('❌ ต่อเซิร์ฟเวอร์ไม่ได้: ' + ((r && r.error) || '') + (age ? ' — กำลังใช้' + age : '') + ' — คลิกเพื่อตั้งค่า');
    }).catch(function () {
      b.classList.remove('dbsrc-live'); b.classList.add('dbsrc-bad');
      var age = snapAge();
      b.querySelector('.dbsrc-txt').textContent = 'ออฟไลน์' + age;
      b.title = '❌ ต่อเซิร์ฟเวอร์ไม่ได้' + (age ? ' — กำลังใช้' + age : '') + ' — คลิกเพื่อตั้งค่า';
    });
  }
  function setConnMode(mode) {
    document.querySelectorAll('#connMode button').forEach(function (b) { b.classList.toggle('on', b.dataset.mode === mode); });
    $('connHttpFields').style.display = mode === 'http' ? '' : 'none';
  }
  function readConnForm() {
    var mode = document.querySelector('#connMode button.on');
    return {
      adapter: mode ? mode.dataset.mode : 'mock',
      baseUrl: ($('connUrl').value || '').trim(),
      token: ($('connToken').value || '').trim(),
      username: ($('connUser') ? $('connUser').value : '').trim(),
      password: ($('connPass') ? $('connPass').value : '').trim(),
      flag: (($('connFlag') ? $('connFlag').value : '') || 'PRICE').trim(),
      useAuth: $('connUseAuth').checked,
      timeoutMs: (parseInt($('connTimeout').value, 10) || 12) * 1000
    };
  }

