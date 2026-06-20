/* ============================================================
   photopea-edit.js — เปิดแก้รูปด้วย Photopea (ฝังในแอป) แล้วเซฟกลับเข้าตาราง
   ------------------------------------------------------------
   • PhotopeaEdit.open(dataURL, onSave) → เปิดหน้าต่าง Photopea เต็มจอ พร้อมรูป
   • ผู้ใช้แก้ด้วยมือ (ครบเครื่องเหมือน Photoshop) → กด "บันทึกกลับ"
   • Photopea ส่งไฟล์ PNG กลับมาทาง postMessage → คืนเป็น dataURL ให้ onSave()
   ฟรี ไม่ต้องตั้งค่า · เอกสาร API: https://www.photopea.com/api/
   ============================================================ */
(function () {
  var overlay = null, iframe = null, onSaveCb = null, awaitingSave = false;

  function ensure() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.className = 'ppx-overlay';
    overlay.innerHTML =
      '<div class="ppx-bar">' +
        '<span class="ppx-title">🎨 แก้รูปด้วย Photopea</span>' +
        '<span class="ppx-hint">แก้เสร็จแล้วกด “บันทึกกลับเข้าตาราง”</span>' +
        '<span class="ppx-actions">' +
          '<button class="btn ppx-save">✓ บันทึกกลับเข้าตาราง</button>' +
          '<button class="btn ppx-close">✕ ปิด (ไม่บันทึก)</button>' +
        '</span>' +
      '</div>' +
      '<div class="ppx-frame"></div>';
    document.body.appendChild(overlay);
    overlay.querySelector('.ppx-close').onclick = close;
    overlay.querySelector('.ppx-save').onclick = requestSave;
    window.addEventListener('message', onMsg);
  }

  function toast(s) { if (window.SG && SG.toast) SG.toast(s); }

  function onMsg(e) {
    if (!iframe || e.source !== iframe.contentWindow) return;
    var d = e.data;
    // ผลลัพธ์ไฟล์ PNG กลับมาเป็น ArrayBuffer (เฉพาะตอนเรากดบันทึก)
    if (awaitingSave && d instanceof ArrayBuffer && d.byteLength > 0) {
      awaitingSave = false;
      var blob = new Blob([d], { type: 'image/png' });
      var fr = new FileReader();
      fr.onload = function () { var url = fr.result; var cb = onSaveCb; close(); if (cb) cb(url); toast('✅ บันทึกรูปจาก Photopea แล้ว'); };
      fr.readAsDataURL(blob);
    }
  }

  function requestSave() {
    if (!iframe) return;
    toast('⏳ กำลังดึงรูปจาก Photopea…');
    awaitingSave = true;
    // รวมเลเยอร์เป็นภาพเดียว แล้วส่งออกเป็น PNG (รักษาความโปร่งใส)
    iframe.contentWindow.postMessage('app.activeDocument.saveToOE("png");', '*');
  }

  function open(dataURL, onSave) {
    ensure();
    onSaveCb = onSave; awaitingSave = false;
    var wrap = overlay.querySelector('.ppx-frame');
    wrap.innerHTML = '';
    iframe = document.createElement('iframe');
    // เปิด Photopea พร้อมโหลดรูปทันที (config.files รับ dataURL ได้)
    var cfg = { files: [dataURL], environment: { vmode: 0 } };
    iframe.src = 'https://www.photopea.com#' + encodeURIComponent(JSON.stringify(cfg));
    iframe.allow = 'clipboard-read; clipboard-write';
    wrap.appendChild(iframe);
    overlay.style.display = 'flex';
  }

  function close() {
    if (!overlay) return;
    overlay.style.display = 'none';
    overlay.querySelector('.ppx-frame').innerHTML = '';
    iframe = null; awaitingSave = false; onSaveCb = null;
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && overlay && overlay.style.display !== 'none') close();
  });

  window.PhotopeaEdit = { open: open };
})();
