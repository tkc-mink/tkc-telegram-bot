/* แถบกรอง/ค้นหา (renderFltBar) — แยกจาก index.html
   ใช้ global: $, SG · เปิด global: renderFltBar */
(function () {
  function $(id) { return document.getElementById(id); }
  // ---- filter / search bar ----
  function renderFltBar() {
    var host = $('fltbar'), isAdmin = SG.getMode() === 'admin';
    var op = SG.filterOptions();
    function opts(arr, label) { return '<option value="">' + label + '</option>' + arr.map(function (v) { return '<option>' + v.replace(/</g, '&lt;') + '</option>'; }).join(''); }
    if (isAdmin) {
      host.innerHTML = '<span class="flt-ic">🔍</span>' +
        '<input id="fq" class="flt-q" placeholder="ค้นหาทันที… ขนาด / ยี่ห้อ / รุ่น / ราคา / หมายเหตุ (พิมพ์แล้วกรองเลย)" />' +
        '<button class="btn" id="fclr" title="ล้างคำค้นหา กลับมาแสดงทั้งหมด" style="display:none;">✕ ล้างค้นหา</button><span class="flt-count" id="fcount"></span>';
      var t;
      $('fq').addEventListener('input', function () {
        $('fclr').style.display = $('fq').value.trim() ? '' : 'none';
        clearTimeout(t); var v = this.value;
        t = setTimeout(function () {
          var n = SG.setFilter({ q: v, applied: true });
          $('fcount').textContent = v.trim() ? ('พบ ' + n + ' รายการ') : '';
        }, 180);
      });
      $('fclr').onclick = function () { SG.clearFilter(); renderFltBar(); };
    } else {
      host.innerHTML = '<span class="flt-ic">🔍</span>' +
        '<select id="fcat" class="flt-sel"><option>ยางปิคอัพ</option></select>' +
        '<select id="frim" class="flt-sel">' + opts(op.rims.map(function (v) { return v + '″'; }), 'ขอบ · ทั้งหมด') + '</select>' +
        '<select id="fwidth" class="flt-sel">' + opts(op.widths, 'หน้ากว้าง · ทั้งหมด') + '</select>' +
        '<select id="fseries" class="flt-sel">' +
          '<option value="">ซีรี่ส์ · ทั้งหมด</option>' +
          op.seriesList.map(function (v) { return '<option value="' + v + '">ซีรี่ส์ ' + v + '</option>'; }).join('') +
          (op.hasFullSeries ? '<option value="full">ไม่ระบุซีรี่ส์ (เต็ม)</option>' : '') +
        '</select>' +
        '<select id="fheight" class="flt-sel">' +
          '<option value="">ความสูง · ทั้งหมด</option>' +
          (op.heights || []).map(function (cm) {
            var inch = (parseFloat(cm) / 2.54).toFixed(1);
            return '<option value="' + cm + '">' + inch + '″ · ' + cm + ' cm</option>';
          }).join('') +
        '</select>' +
        '<select id="fbrand" class="flt-sel">' + opts(op.brands, 'ยี่ห้อ · ทั้งหมด') + '</select>' +
        '<input id="fq" class="flt-q" placeholder="คำค้นเพิ่มเติมฯ" style="max-width:130px;" />' +
        '<button class="btn primary" id="fgo">🔍 ค้นหา</button>' +
        '<button class="btn" id="fclr" title="ล้างเงื่อนไขค้นหา" style="display:none;">✕ ล้างค้นหา</button><span class="flt-count" id="fcount"></span>';
      function go() {
        var n = SG.setFilter({
          q: $('fq').value, brand: $('fbrand').value,
          rim: $('frim').value.replace('″', ''), width: $('fwidth').value,
          series: $('fseries').value, height: $('fheight').value, hUnit: 'cm',
          applied: true
        });
        if (SG.isTooMany()) {
          $('fcount').innerHTML = '<span style="color:#c0392b;">⚠️ พบ ' + n + ' รายการ — ระบุเงื่อนไขเพิ่ม</span>';
        } else {
          $('fcount').textContent = 'พบ ' + n + ' รายการ';
        }
      }
      function go2done() { $('fclr').style.display = ''; }
      $('fgo').onclick = function () { go(); go2done(); };
      $('fq').addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
      $('fclr').onclick = function () { SG.clearFilter(); renderFltBar(); };
    }
  }

  window.renderFltBar = renderFltBar;
})();
