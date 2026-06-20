/* สำรอง/กู้คืนข้อมูลลงเครื่อง (.json) — แยกจาก index.html
   ใช้ global: $, SG, toast */
(function () {
  function $(id) { return document.getElementById(id); }
  // ---- สำรอง / กู้คืนข้อมูลลงเครื่อง (.json) — ฐานของ backup บน cloud ----
  function bkStamp() {
    var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + p(d.getHours()) + p(d.getMinutes());
  }
  function bkGather() {
    var data = {};
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k && k.indexOf('xls2') === 0) data[k] = localStorage.getItem(k);
    }
    return { _app: 'DPL-PriceList', _type: 'backup', _version: 1, exportedAt: new Date().toISOString(), data: data };
  }
  function bkDownload(obj, fname) {
    var blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = fname;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }
  $('btnBackup').onclick = function () {
    try { SG.save(); } catch (e) {}                       // เซฟล่าสุดก่อนสำรอง
    var obj = bkGather();
    var nSheets = 0; try { nSheets = (JSON.parse(obj.data.xls2_sheets || '[]') || []).length; } catch (e) {}
    bkDownload(obj, 'ราคายาง-สำรอง-' + bkStamp() + '.json');
    if (typeof toast === 'function') toast('💾 ดาวน์โหลดไฟล์สำรองแล้ว (' + nSheets + ' หมวด)');
  };
  $('btnRestore').onclick = function () { $('restoreFile').value = ''; $('restoreFile').click(); };
  $('btnGDrive').onclick = function () { if (window.GDrive) GDrive.openPanel(); };
  $('restoreFile').onchange = function (e) {
    var f = e.target.files && e.target.files[0]; if (!f) return;
    var rd = new FileReader();
    rd.onload = function () {
      var obj;
      try { obj = JSON.parse(rd.result); } catch (err) { alert('❌ อ่านไฟล์ไม่ได้ — ไฟล์อาจเสียหายหรือไม่ใช่ .json'); return; }
      if (!obj || obj._type !== 'backup' || !obj.data) { alert('❌ ไฟล์นี้ไม่ใช่ไฟล์สำรองของโปรแกรมราคายาง'); return; }
      var nSheets = 0; try { nSheets = (JSON.parse(obj.data.xls2_sheets || '[]') || []).length; } catch (e2) {}
      var when = obj.exportedAt ? new Date(obj.exportedAt).toLocaleString('th-TH') : '-';
      if (!confirm('กู้คืนข้อมูลจากไฟล์สำรอง?\n\n• วันที่สำรอง: ' + when + '\n• จำนวนหมวด: ' + nSheets + ' หมวด\n\n⚠️ ข้อมูลปัจจุบันทั้งหมดจะถูกแทนที่\nระบบจะดาวน์โหลดไฟล์สำรองของข้อมูลปัจจุบันให้อัตโนมัติก่อน (กันพลาด)')) return;
      try { bkDownload(bkGather(), 'ราคายาง-ก่อนกู้คืน-' + bkStamp() + '.json'); } catch (e3) {}   // สำรองสถานะปัจจุบันกันพลาด
      var rm = []; for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (k && k.indexOf('xls2') === 0) rm.push(k); }
      rm.forEach(function (k) { localStorage.removeItem(k); });
      Object.keys(obj.data).forEach(function (k) { localStorage.setItem(k, obj.data[k]); });
      alert('✅ กู้คืนข้อมูลเรียบร้อย — โปรแกรมจะโหลดใหม่');
      location.reload();
    };
    rd.readAsText(f);
  };
})();
