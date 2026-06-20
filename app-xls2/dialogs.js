/* ชุดไดอะล็อก/ป๊อปอัป (แยกจาก index.html)
   เปิดเป็น global: window.PopupStack, window.makeDraggable,
   window.AppDialog, window.alertDialog, window.confirmDialog, window.promptDialog */
(function () {
  // ---- ระบบชั้นป๊อปอัป (Popup Layer Stack): Esc ปิดทีละชั้นจากบนสุดลงล่าง ----
  // ป๊อปอัปทุกตัว register เข้าสแต็กตอนเปิด · Esc ปิดชั้นบนสุดก่อน แล้วค่อยชั้นถัดไป
  var PopupStack = (function () {
    var stack = [];
    function clean() {
      for (var i = stack.length - 1; i >= 0; i--) {
        var el = stack[i].el;
        if (!el || !document.body.contains(el) || el.style.display === 'none' || getComputedStyle(el).display === 'none') stack.splice(i, 1);
      }
    }
    function push(el, close) { if (!el) return; remove(el); stack.push({ el: el, close: close }); }
    function remove(el) { for (var i = stack.length - 1; i >= 0; i--) if (stack[i].el === el) stack.splice(i, 1); }
    // จับ Esc ก่อนตัวจัดการอื่นทั้งหมด (capture, ลงทะเบียนเป็นตัวแรก) — ปิดชั้นบนสุดทีละชั้น
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      clean();
      if (!stack.length) return;
      e.preventDefault(); e.stopImmediatePropagation();
      var t = stack.pop();
      try { t.close(); } catch (_) {}
    }, true);
    return { push: push, remove: remove, clean: clean, get size() { clean(); return stack.length; } };
  })();
  window.PopupStack = PopupStack;

  // ---- ลากย้ายป๊อปอัปด้วยส่วนหัว (reusable) ----
  function makeDraggable(panel, handle) {
    if (!panel || !handle) return;
    handle.style.cursor = 'move';
    handle.addEventListener('mousedown', function (e) {
      if (e.target.closest('button, input, select, .emoji-x, .pk-x')) return;
      e.preventDefault();
      var rect = panel.getBoundingClientRect();
      panel.style.left = rect.left + 'px'; panel.style.top = rect.top + 'px';
      panel.style.right = 'auto'; panel.style.transform = 'none';
      var dx = e.clientX - rect.left, dy = e.clientY - rect.top;
      function mv(ev) {
        var L = Math.max(4, Math.min(window.innerWidth - panel.offsetWidth - 4, ev.clientX - dx));
        var T = Math.max(4, Math.min(window.innerHeight - panel.offsetHeight - 4, ev.clientY - dy));
        panel.style.left = L + 'px'; panel.style.top = T + 'px';
      }
      function up() { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); }
      document.addEventListener('mousemove', mv); document.addEventListener('mouseup', up);
    });
  }
  window.makeDraggable = makeDraggable;

  // ---- ไดอะล็อกกลางสไตล์เดียว (แทน alert/confirm/prompt) [#5] · เข้า PopupStack ----
  function baseDialog(opts) {
    var ov = document.createElement('div'); ov.className = 'cdlg-ov';
    var box = document.createElement('div'); box.className = 'cdlg';
    var icon = opts.icon || '';
    box.innerHTML = '<div class="cdlg-h">' + (icon ? '<span class="cdlg-ic">' + icon + '</span>' : '') + '<span>' + (opts.title || '') + '</span></div>' +
      '<div class="cdlg-b">' + (opts.body || '') + '</div>' +
      (opts.input != null ? '<input class="cdlg-input" type="text">' : '') +
      '<div class="cdlg-f"></div>';
    ov.appendChild(box); document.body.appendChild(ov);
    var inp = box.querySelector('.cdlg-input');
    if (inp != null) { inp.value = opts.input || ''; setTimeout(function () { inp.focus(); inp.select(); }, 30); }
    var foot = box.querySelector('.cdlg-f');
    function close() { ov.remove(); if (window.PopupStack) PopupStack.remove(ov); }
    (opts.buttons || []).forEach(function (b) {
      var btn = document.createElement('button');
      btn.className = 'btn' + (b.primary ? ' primary' : '') + (b.danger ? ' cdlg-danger' : '');
      btn.textContent = b.label;
      btn.onclick = function () { var v = inp ? inp.value : undefined; close(); if (b.onClick) b.onClick(v); };
      foot.appendChild(btn);
    });
    if (window.PopupStack) PopupStack.push(ov, close);
    // Enter = ปุ่มหลัก (ถ้ามี input ก็ submit)
    box.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { var pr = (opts.buttons || []).filter(function (b) { return b.primary; })[0]; if (pr) { e.preventDefault(); var v = inp ? inp.value : undefined; close(); if (pr.onClick) pr.onClick(v); } }
    });
    ov.addEventListener('mousedown', function (e) { if (e.target === ov && opts.dismissable !== false) close(); });
    return close;
  }
  function alertDialog(title, body, cb) {
    baseDialog({ icon: 'ℹ️', title: title, body: body, buttons: [{ label: 'ตกลง', primary: true, onClick: cb }] });
  }
  function confirmDialog(title, body, onYes, onNo) {
    baseDialog({ icon: '❓', title: title, body: body, buttons: [
      { label: 'ยกเลิก', onClick: onNo }, { label: 'ยืนยัน', primary: true, onClick: onYes }
    ] });
  }
  function promptDialog(title, body, defVal, onOk) {
    baseDialog({ icon: '✏️', title: title, body: body, input: defVal || '', buttons: [
      { label: 'ยกเลิก' }, { label: 'ตกลง', primary: true, onClick: function (v) { if (onOk) onOk(v); } }
    ] });
  }
  window.baseDialog = baseDialog;
  window.alertDialog = alertDialog;
  window.confirmDialog = confirmDialog;
  window.promptDialog = promptDialog;
  window.AppDialog = { alert: alertDialog, confirm: confirmDialog, prompt: promptDialog };
})();
