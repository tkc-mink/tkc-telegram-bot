/* แท็บสำรอง/กู้คืน + กฎราคา/VAT + สีประจำแท็บ + ปุ่มลัดตั้งค่า
   — ส่วนของ app-main (de-IIFE, global scope) · โหลดต่อเนื่องตามลำดับก่อน price-update.js */
  // ---------- แท็บสำรอง/กู้คืน [#3] ----------
  function buildBackupTab() {
    if (!window.DBX || !$('bkExport')) return;
    $('bkInfo').textContent = (DBX.allStorageKeys().length) + ' รายการตั้งค่าพร้อมสำรอง';
    $('bkExport').onclick = function () {
      var blob = DBX.exportSettingsBlob();
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'pricelist-settings-' + new Date().toISOString().slice(0, 10) + '.json';
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 100);
      $('bkInfo').textContent = '✅ ดาวน์โหลดแล้ว (' + DBX.allStorageKeys().length + ' รายการ)';
    };
    $('bkImport').onclick = function () {
      var f = $('bkFile').files && $('bkFile').files[0];
      var info = $('bkRestoreInfo');
      if (!f) { info.className = 'bk-info err'; info.textContent = '⚠️ เลือกไฟล์สำรองก่อน'; return; }
      var mode = $('bkMode').value;
      var rd = new FileReader();
      rd.onload = function () {
        var obj; try { obj = JSON.parse(rd.result); } catch (e) { info.className = 'bk-info err'; info.textContent = '❌ ไฟล์ไม่ใช่ JSON ที่ถูกต้อง'; return; }
        confirmDialog('กู้คืนการตั้งค่า?', (mode === 'replace' ? 'จะ<b>ลบค่าเดิมทั้งหมด</b>แล้วแทนที่ด้วยไฟล์นี้' : 'จะ<b>เขียนทับเฉพาะค่าที่มีในไฟล์</b>') + '<br>ระบบจะรีโหลดหลังกู้คืน', function () {
          try {
            var n = DBX.importSettings(obj, mode);
            info.className = 'bk-info ok'; info.textContent = '✅ กู้คืน ' + n + ' รายการ · กำลังรีโหลด…';
            setTimeout(function () { location.reload(); }, 900);
          } catch (e) { info.className = 'bk-info err'; info.textContent = '❌ ' + e.message; }
        });
      };
      rd.readAsText(f);
    };
  }

  function buildPricingTab() {
    if (!window.DBX || !$('prVat')) return;
    var r = DBX.pricingRules();
    var f2 = function (n) { return (Math.round((+n || 0) * 100) / 100).toFixed(2); };
    $('prVat').value = f2((r.vatRate || 0) * 100);
    $('prStep').value = f2(r.roundStep || 10);
    function byUpTo(a, b) { return (a.upTo == null ? Infinity : a.upTo) - (b.upTo == null ? Infinity : b.upTo); }
    function collectBkts() {
      var rows = [].slice.call($('prBkts').querySelectorAll('.pr-bkt'));
      var arr = rows.map(function (row) {
        var up = row.querySelector('.pr-bkt-upto');
        return { upTo: up ? (up.value === '' ? null : parseFloat(up.value)) : null, add: parseFloat(row.querySelector('.pr-bkt-add').value) || 0 };
      });
      // ให้มีแถว ∞ (upTo=null) เพียงแถวเดียว = แถวสุดท้าย
      var finite = arr.filter(function (b) { return b.upTo != null && !isNaN(b.upTo); }).sort(byUpTo);
      var inf = arr.filter(function (b) { return b.upTo == null || isNaN(b.upTo); });
      var infAdd = inf.length ? inf[inf.length - 1].add : 0;
      return finite.concat([{ upTo: null, add: infAdd }]);
    }
    function saveBkts() { DBX.setPricingRules({ creditBrackets: collectBkts() }); updPrev(); }
    function buildBkts() {
      var host = $('prBkts'); if (!host) return;
      var bs = DBX.pricingRules().creditBrackets.slice().sort(byUpTo);
      var lower = 0, html = '';
      bs.forEach(function (b, i) {
        var isInf = (b.upTo == null);
        html += '<div class="pr-bkt" data-i="' + i + '">' +
          '<span class="pr-bkt-from">' + XL2.fmtNum(lower) + '</span>' +
          '<span class="pr-bkt-dash">–</span>' +
          (isInf ? '<span class="pr-bkt-inf">ขึ้นไป</span>' : '<input type="number" class="pr-bkt-upto" value="' + b.upTo + '" min="0" step="1">') +
          '<span class="pr-bkt-plus">+</span>' +
          '<input type="number" class="pr-bkt-add" value="' + (b.add || 0) + '" min="0" step="1">' +
          '<span class="pr-bkt-baht">฿</span>' +
          '<button class="pr-bkt-del" title="ลบช่วง"' + (bs.length <= 1 ? ' disabled' : '') + '>✕</button>' +
          '</div>';
        if (!isInf) lower = (+b.upTo || 0) + 1;
      });
      host.innerHTML = html;
    }
    function updPrev() {
      var v = $('prVat').value, demos = [800, 4500, 25000];
      var rowsHtml = demos.map(function (d) {
        var p = DBX.computePricing(d);
        return '<div class="pr-prow">เครดิต <b>' + XL2.fmtNum(d) + '</b> → +' + XL2.fmtNum(p.bracketAdd) + ' → +VAT ' + v + '% → ปัดขึ้น = <b style="color:#15A34A">' + XL2.fmtNum(p.creditVatRounded) + '</b></div>';
      }).join('');
      $('prPreview').innerHTML = rowsHtml;
    }
    function saveTopFields() {
      DBX.setPricingRules({ vatRate: (parseFloat($('prVat').value) || 0) / 100, creditMarkup: parseFloat($('prMarkup').value) || 0, roundStep: parseFloat($('prStep').value) || 10 });
      updPrev();
    }
    ['prVat', 'prStep'].forEach(function (id) {
      $(id).oninput = saveTopFields;
      $(id).onblur = function () { if (this.value !== '') this.value = f2(this.value); };
    });
    var host = $('prBkts');
    host.oninput = function (e) { if (e.target.closest('.pr-bkt-upto, .pr-bkt-add')) { DBX.setPricingRules({ creditBrackets: collectBkts() }); updPrev(); } };
    host.onchange = function (e) { if (e.target.closest('.pr-bkt-upto')) { saveBkts(); buildBkts(); } };
    host.onclick = function (e) {
      var del = e.target.closest('.pr-bkt-del'); if (!del) return;
      var row = del.closest('.pr-bkt'); row.parentNode.removeChild(row);
      saveBkts(); buildBkts();
    };
    $('prBktAdd').onclick = function () {
      var bs = DBX.pricingRules().creditBrackets.slice().sort(byUpTo);
      var lastFinite = bs.filter(function (b) { return b.upTo != null; }).pop();
      var newUp = lastFinite ? (+lastFinite.upTo || 0) + 1000 : 1000;
      var arr = bs.filter(function (b) { return b.upTo != null; }).concat([{ upTo: newUp, add: 0 }]);
      var inf = bs.filter(function (b) { return b.upTo == null; })[0] || { upTo: null, add: 0 };
      arr.push(inf);
      DBX.setPricingRules({ creditBrackets: arr }); buildBkts(); updPrev();
    };
    $('prBktReset').onclick = function () { confirmDialog('คืนค่าเริ่มต้น?', 'คืนตารางบวกเครดิตเป็นค่าเริ่มต้น', function () { DBX.resetCreditBrackets(); buildBkts(); updPrev(); }); };
    buildBkts();
    updPrev();
  }
  (function () {
    var addBtn = document.getElementById('statIconAdd'), resetBtn = document.getElementById('statIconReset'), saveBtn = document.getElementById('statIconSave');
    function curDefs() { return ((statWork && statWork.length) ? statWork : window.DBX.statusDefs()).slice(); }
    if (addBtn) addBtn.onclick = function () {
      if (!window.DBX) return;
      var defs = curDefs();
      defs.push({ key: 'custom' + Date.now(), kind: 'icon', cond: '', icon: '🏷️', color: '888888', label: 'สถานะใหม่', popup: '', enabled: true, priority: defs.length + 1 });
      statWork = defs; buildStatIconList();
    };
    if (resetBtn) resetBtn.onclick = function () {
      if (!window.DBX) return;
      confirmDialog('คืนค่าไอคอนเริ่มต้น?', 'คืนค่าไอคอนสถานะทั้งหมดเป็นค่าเริ่มต้น (กดบันทึกเพื่อใช้งาน)', function () {
        window.DBX.resetStatusDefs(); statWork = window.DBX.statusDefs().slice(); buildStatIconList();
      });
    };
    if (saveBtn) saveBtn.onclick = function () {
      if (!window.DBX) return;
      if (statWork) window.DBX.saveStatusDefs(statWork);
      statWork = null; if (window.SG) { if (SG.clearDbCache) SG.clearDbCache(); SG.render(); }
      if (typeof toast === 'function') toast('✓ บันทึกไอคอนสถานะแล้ว');
      $('mCond').classList.remove('open');   // บันทึกเสร็จ → ปิดหน้าต่าง
    };
  })();
  document.querySelectorAll('#mCond .settab').forEach(function (b) {
    b.onclick = function () { switchSetTab(b.dataset.tab); };
  });
  function saveTabOrder() {}
  // สีประจำแท็บ: ปิดการใช้งานในเลย์เอาต์ sidebar (ใช้สไตล์มาตรฐานสะอาดตา)
  function colorizeTabs() {
    document.querySelectorAll('#mCond .settab').forEach(function (b) { b.style.background = ''; b.style.color = ''; b.style.outline = ''; b.style.outlineOffset = ''; });
  }
  function openTabColor() { /* เลิกใช้แล้ว — เปลี่ยนเป็นเมนูหมวดด้านข้าง (sidebar) */ }
  (function loadTabOrder() {
    // เลย์เอาต์ใหม่จัดกลุ่มตามหมวด — ไม่เรียงลำดับเองอีกต่อไป (ล้างค่าที่บันทึกไว้)
    try { localStorage.removeItem('xls2_settaborder'); } catch (e) {}
  })();
  colorizeTabs();
  // Enter ในช่องตั้งค่า → ไปช่องถัดไป · ช่องสุดท้าย Enter = บันทึก + ปิด
  $('mCond').addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || e.target.tagName === 'TEXTAREA') return;
    if (!/INPUT|SELECT/.test(e.target.tagName)) {
      // Enter ขณะโฟกัสอยู่นอกช่องกรอก (ปุ่ม/รายการ) → กดปุ่มบันทึกที่กำลังแสดง
      var sv0 = $('statIconSave');
      if (sv0 && sv0.offsetParent) { e.preventDefault(); sv0.click(); }
      else { var ok0 = $('condOk'); if (ok0 && ok0.offsetParent) { e.preventDefault(); ok0.click(); } }
      return;
    }
    if (e.target.type === 'color') return;
    e.preventDefault();
    var pane = e.target.closest('.settab-pane') || $('mCond');
    var fields = [].slice.call(pane.querySelectorAll('input:not([type=color]):not([disabled]), select')).filter(function (el) { return el.offsetParent !== null; });
    var i = fields.indexOf(e.target);
    if (i >= 0 && i < fields.length - 1) { var n = fields[i + 1]; n.focus(); if (n.select) { try { n.select(); } catch (er) {} } }
    else { var sv = $('statIconSave'); if (sv && sv.offsetParent) sv.click(); else $('condOk').click(); }
  });
  $('condOk').onclick = function () {
    setUndoSnap = snapshotSettings();   // เก็บค่าก่อนหน้าไว้ให้ Undo ย้อนได้
    Object.keys(pend).forEach(function (k) { localStorage.setItem(k, pend[k]); });
    pend = {};
    SG.setCondColors({ pos: condSel.pos, neg: condSel.neg });
    applyMarkColors(); applyHdrColors(); applyAdmStyle(); applyDbLinkColors();
    if (typeof toast === 'function') toast('✓ บันทึกการตั้งค่าแล้ว (Undo เพื่อย้อน)');
    $('mCond').classList.remove('open');
  };
  // ยกเลิกในแท็บสี = ทิ้ง pending (ไม่มีผลจริง เพราะยังไม่ได้ apply)
  $('mCond').querySelectorAll('[data-close]').forEach(function (b) { b.addEventListener('click', function () { pend = {}; }); });
  // ปุ่มลัดในแต่ละแท็บ
  function wireSetBtn(id, fn) { var el = $(id); if (el) el.onclick = function () { $('mCond').classList.remove('open'); setTimeout(fn, 60); }; }
  wireSetBtn('setAutosave', function () { $('saveState').click(); });
  wireSetBtn('setApi', function () { $('btnApi') && $('btnApi').click(); });
  wireSetBtn('setTheme', function () { $('btnTheme') && $('btnTheme').click(); });
  wireSetBtn('setKeys', function () { $('btnKeys') && $('btnKeys').click(); });

