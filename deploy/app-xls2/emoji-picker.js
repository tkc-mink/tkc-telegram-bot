/* ตัวเลือกอีโมจิ/ไอคอน (openEmojiPicker + custom icons + ค้นไอคอนเวกเตอร์จากเน็ต)
   ใช้ global: $, promptDialog, makeDraggable, PopupStack, IconKit · เปิด global: openEmojiPicker */
(function () {
  function $(id) { return document.getElementById(id); }
  function ihtml(v) { return (window.IconKit ? IconKit.html(v) : (String(v || '') + '\uFE0E')); }
  // ---------- แปลคำค้นไทย → คำไอคอนอังกฤษ (Iconify มีแต่คำอังกฤษ) ----------
  function hasThai(s) { return /[\u0E00-\u0E7F]/.test(String(s || '')); }
  var TH_EN = {
    // รถ / ยาง / ขนส่ง
    'รถ': 'car', 'รถยนต์': 'car', 'รถเก๋ง': 'car', 'รถบรรทุก': 'truck', 'บรรทุก': 'truck', 'รถกระบะ': 'pickup truck', 'กระบะ': 'pickup truck',
    'ยาง': 'tire', 'ยางรถ': 'car tire', 'ยางรถยนต์': 'car tire', 'ล้อ': 'wheel', 'ขอบล้อ': 'wheel rim', 'รถจักรยานยนต์': 'motorcycle', 'มอเตอร์ไซค์': 'motorcycle',
    'จักรยาน': 'bicycle', 'รถตู้': 'van', 'รถบัส': 'bus', 'รถแทรกเตอร์': 'tractor', 'แทรกเตอร์': 'tractor', 'เรือ': 'ship', 'เครื่องบิน': 'airplane', 'ขนส่ง': 'shipping', 'จัดส่ง': 'delivery', 'ส่งของ': 'delivery truck',
    // คลัง / สินค้า
    'กล่อง': 'box', 'พัสดุ': 'package', 'คลัง': 'warehouse', 'คลังสินค้า': 'warehouse', 'สินค้า': 'product', 'สต็อก': 'inventory', 'โรงงาน': 'factory', 'ร้านค้า': 'store', 'รถเข็น': 'cart', 'ตะกร้า': 'basket',
    // สถานะ / เครื่องหมาย
    'ถูก': 'check', 'เช็ค': 'check', 'เครื่องหมายถูก': 'check', 'ผ่าน': 'check circle', 'ผิด': 'close', 'กากบาท': 'close', 'ยกเลิก': 'cancel', 'ห้าม': 'block', 'เตือน': 'warning', 'แจ้งเตือน': 'alert', 'ข้อมูล': 'info', 'คำถาม': 'help',
    'ดาว': 'star', 'หัวใจ': 'heart', 'ธง': 'flag', 'หมุด': 'pin', 'ปักหมุด': 'map pin', 'ระฆัง': 'bell', 'กุญแจ': 'key', 'ล็อก': 'lock', 'ปลดล็อก': 'lock open',
    // ราคา / เงิน
    'เงิน': 'money', 'ราคา': 'price tag', 'ป้ายราคา': 'price tag', 'บาท': 'currency baht', 'เหรียญ': 'coin', 'บัตร': 'credit card', 'บัตรเครดิต': 'credit card', 'ส่วนลด': 'discount', 'โปรโมชั่น': 'sale', 'ลดราคา': 'sale', 'ใบเสร็จ': 'receipt', 'กระเป๋าเงิน': 'wallet', 'เพชร': 'diamond', 'มงกุฎ': 'crown', 'ถ้วยรางวัล': 'trophy', 'เหรียญรางวัล': 'medal',
    // ไฟ / สภาพ / เวลา
    'ไฟ': 'fire', 'เปลวไฟ': 'fire', 'ระเบิด': 'explosion', 'สายฟ้า': 'flash', 'ไฟฟ้า': 'bolt', 'น้ำ': 'water', 'หยดน้ำ': 'water drop', 'หิมะ': 'snowflake', 'เย็น': 'snowflake', 'ร้อน': 'thermometer', 'อุณหภูมิ': 'thermometer', 'แดด': 'sun', 'พระอาทิตย์': 'sun', 'พระจันทร์': 'moon', 'ฝน': 'rain',
    'นาฬิกา': 'clock', 'เวลา': 'clock', 'นาฬิกาทราย': 'hourglass', 'ปฏิทิน': 'calendar', 'รอ': 'hourglass',
    // ทิศทาง / ลูกศร
    'ลูกศร': 'arrow', 'ขึ้น': 'arrow up', 'ลง': 'arrow down', 'ซ้าย': 'arrow left', 'ขวา': 'arrow right', 'รีเฟรช': 'refresh', 'รีโหลด': 'refresh', 'หมุน': 'rotate',
    // เครื่องมือ / คน / ทั่วไป
    'เครื่องมือ': 'tools', 'ประแจ': 'wrench', 'ค้อน': 'hammer', 'ไขควง': 'screwdriver', 'เฟือง': 'gear', 'ตั้งค่า': 'settings', 'คน': 'person', 'ผู้ใช้': 'user', 'ช่าง': 'mechanic', 'มือ': 'hand', 'ตา': 'eye',
    'บ้าน': 'home', 'อาคาร': 'building', 'โทรศัพท์': 'phone', 'อีเมล': 'email', 'แผนที่': 'map', 'กล้อง': 'camera', 'รูป': 'image', 'รูปภาพ': 'image', 'พิมพ์': 'print', 'ดาวน์โหลด': 'download', 'อัปโหลด': 'upload', 'ค้นหา': 'search', 'ตะกร้าขยะ': 'delete', 'ลบ': 'delete', 'ถังขยะ': 'trash', 'แก้ไข': 'edit', 'ดินสอ': 'pencil', 'บันทึก': 'save',
    'กราฟ': 'chart', 'แผนภูมิ': 'chart', 'เอกสาร': 'document', 'ไฟล์': 'file', 'โฟลเดอร์': 'folder', 'แท็ก': 'tag', 'หลอดไฟ': 'lightbulb', 'แบตเตอรี่': 'battery', 'น้ำมัน': 'oil', 'ปั๊มน้ำมัน': 'gas station'
  };
  // แปลแบบพจนานุกรม: ทั้งวลีก่อน → ไม่เจอค่อยแยกทีละคำ
  function dictTranslate(s) {
    var k = String(s || '').trim();
    if (TH_EN[k]) return TH_EN[k];
    return k.split(/\s+/).map(function (w) { return TH_EN[w] || w; }).join(' ').trim();
  }
  // แปลไทย→อังกฤษ: 1) พจนานุกรมในตัว (เร็ว/ออฟไลน์)  2) ถ้ายังเหลือไทย ลองแปลออนไลน์
  function translateTh(s) {
    var d = dictTranslate(s);
    if (!hasThai(d)) return Promise.resolve(d);
    var ac = new AbortController(); var to = setTimeout(function () { ac.abort(); }, 6000);
    return fetch('https://translate.googleapis.com/translate_a/single?client=gtx&sl=th&tl=en&dt=t&q=' + encodeURIComponent(s), { signal: ac.signal })
      .then(function (r) { clearTimeout(to); return r.json(); })
      .then(function (j) {
        var t = ((j && j[0]) || []).map(function (x) { return x[0]; }).join('').trim();
        return t || d;
      })
      .catch(function () { clearTimeout(to); return d; });
  }
  // ---------- ตัวเลือกอีโมจิแยกหมวด (คลิกไอคอนสถานะ) ----------
  var EMOJI_CATS = [
    { name: 'สถานะ / จุดสี', list: ['🟢','🔴','🟠','🟡','🔵','🟣','⚫','⚪','🟤','🟩','🟥','🟧','🟨','🟦','🟪','⬛','⬜','🔶','🔷','🔸','🔹','🔺','🔻','▲','▼','◆','●','○','■','□','★','☆','✦','✱','✳️','❇️','⭐','🌟'] },
    { name: 'เครื่องหมาย / ถูก-ผิด', list: ['✅','❌','✔️','✖️','☑️','✗','✓','⛔','🚫','❎','➕','➖','➗','✚','➰','〰️','⁉️','‼️','❓','❔','❗','❕','⚠️','🔆','🔅','♻️','🆕','🆖','🆗','🆒','🆙','🔱','⚜️','🈵','🈳','🅿️'] },
    { name: 'ขนส่ง / คลัง / โรงงาน', list: ['🚚','🚛','🚐','🛻','🚗','🚙','🏎️','🚜','📦','📫','📮','🏬','🏭','🏗️','🏠','🏢','🏪','🛒','🛍️','🧰','🧱','📥','📤','📨','🗃️','🗄️','🗂️','📋','📑','⚓','⛴️','🚢','✈️','🛩️','🚀','🪜','🔩','⛓️'] },
    { name: 'ราคา / เงิน / โปรโมชั่น', list: ['💰','💵','💴','💶','💷','💸','🪙','💳','🧾','🏷️','🔖','🎁','🎀','🎯','🎊','🎉','📉','📈','📊','💹','🤑','💲','💱','🏧','⚖️','🛎️','🔔','💎','👑','🥇'] },
    { name: 'ดาว / รางวัล / เด่น', list: ['⭐','🌟','✨','💫','🏆','🥇','🥈','🥉','👑','💎','🔱','🎖️','🏅','🎗️','🌠','🔆','❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💯','🆗','🔥','⚡','🌈'] },
    { name: 'แจ้งเตือน / ไฟ / สภาพ', list: ['🔥','💥','⚡','❄️','💧','🩸','💦','🌡️','☀️','🌙','⛅','🌧️','⛈️','🌪️','🚨','🔊','🔇','📢','📣','🔔','🔕','⏰','⏳','⌛','🕐','📅','📆','🗓️','⏱️','⏲️'] },
    { name: 'ลูกศร / ทิศทาง', list: ['⬆️','⬇️','⬅️','➡️','↗️','↘️','↙️','↖️','↕️','↔️','🔼','🔽','⏫','⏬','▶️','◀️','⏩','⏪','🔄','🔃','🔁','🔂','↩️','↪️','⤴️','⤵️','🔀','➰','〽️','✳️'] },
    { name: 'มือ / คน / เครื่องมือ', list: ['👍','👎','👌','👏','🙌','✋','🤚','🖐️','🤝','👀','👁️','💪','🧑‍🔧','👷','🧑‍💼','🛠️','🔧','🔨','⚙️','🔩','🪛','⛏️','🔗','🔒','🔓','🔑','🗝️','📌','📍','📎','🖇️','✏️','🖊️','🖍️','📝'] },
    { name: 'สินค้า / ยาง / รถ', list: ['🛞','🚗','🚙','🚐','🛻','🚛','🏍️','🛵','🚲','🦽','🛺','🚓','🚑','🚒','🏎️','🚘','🚖','🧨','🛢️','⛽','🔋','🔌','🧯','🪫','🔦','💡','🔭','🔬','🧲','⚗️'] },
    { name: 'ทั่วไป / สัญลักษณ์', list: ['📁','📂','🗒️','📊','📈','📉','🗂️','🏁','🚩','🎌','🏳️','🏴','🔰','〽️','©️','®️','™️','🔟','#️⃣','*️⃣','0️⃣','1️⃣','2️⃣','3️⃣','🅰️','🅱️','🆎','🅾️','ℹ️','🔣'] }
  ];
  var CUSTOM_ICON_KEY = 'dpl_custom_icons';
  function customIcons() { try { var v = JSON.parse(localStorage.getItem(CUSTOM_ICON_KEY)); return Array.isArray(v) ? v : []; } catch (e) { return []; } }
  function saveCustomIcons(a) { localStorage.setItem(CUSTOM_ICON_KEY, JSON.stringify(a.slice(0, 60))); }
  // อีโมจิ/สัญลักษณ์ตัด 8 ตัวอักษร · token ไอคอนเน็ต (ico:/URL) เก็บเต็ม
  function capIcon(v) { v = (v || '').trim(); return (window.IconKit && IconKit.isImg(v)) ? v : v.slice(0, 8); }
  function addCustomIcon(v) { v = capIcon(v); if (!v) return; var a = customIcons().filter(function (x) { return x !== v; }); a.unshift(v); saveCustomIcons(a); }
  function removeCustomIcon(v) { saveCustomIcons(customIcons().filter(function (x) { return x !== v; })); }
  var emojiPickEl = null;
  function openEmojiPicker(anchor, current, onPick) {
    if (!emojiPickEl) { emojiPickEl = document.createElement('div'); emojiPickEl.className = 'emoji-pick'; document.body.appendChild(emojiPickEl); }
    function catHtml(name, items, isCustom) {
      var seen = {}; items = items.filter(function (e) { if (!e || seen[e]) return false; seen[e] = 1; return true; });
      var tiles = items.map(function (e) {
        return '<button type="button" class="emoji-it' + (e === current ? ' on' : '') + (isCustom ? ' emoji-custom' : '') + '" data-e="' + String(e).replace(/"/g, '&quot;') + '" title="' + (isCustom ? 'คลิกเลือก · คลิกขวาลบ' : 'คลิกเลือก') + '">' + ihtml(e) + '</button>';
      }).join('');
      if (isCustom) tiles += '<button type="button" class="emoji-it emoji-add" data-add="1" title="เพิ่มไอคอนเอง (วางอีโมจิ/สัญลักษณ์จากที่ไหนก็ได้)">＋</button>';
      return '<div class="emoji-cat">' + name + '</div><div class="emoji-grid">' + tiles + '</div>';
    }
    function render(filter) {
      var f = (filter || '').trim();
      var html = '';
      var cust = customIcons();
      if (!f && cust.length || !f) html += catHtml('⭐ ของฉัน / เพิ่มเอง', cust, true);
      EMOJI_CATS.forEach(function (cat) {
        var items = cat.list.filter(function (e) { return e && e.length <= 5; });
        if (f) items = items.filter(function (e) { return e.indexOf(f) >= 0; });
        if (items.length) html += catHtml(cat.name, items, false);
      });
      emojiPickEl.querySelector('.emoji-body').innerHTML = html || '<div class="emoji-empty">ไม่พบ — กด Enter เพื่อใช้ตัวที่พิมพ์/วาง</div>';
    }
    emojiPickEl.innerHTML = '<div class="emoji-head">เลือกไอคอน <span class="emoji-head-hint">(ลากแถบนี้เพื่อย้าย)</span><span class="emoji-x">✕</span></div>' +
      '<input class="emoji-q" placeholder="🔍 พิมพ์/วางอีโมจิ แล้ว Enter เพื่อใช้ทันที">' +
      '<div class="emoji-body"></div>' +
      '<div class="emoji-net" style="display:none;"></div>' +
      '<div class="emoji-foot"><button type="button" class="btn emoji-netbtn">🌐 ค้นไอคอนจากเน็ต</button><button type="button" class="btn emoji-addbtn">＋ เพิ่มเอง</button><button type="button" class="btn emoji-clear">ล้างไอคอน</button></div>';
    render('');
    var q = emojiPickEl.querySelector('.emoji-q');
    q.oninput = function () { render(q.value); };
    q.onkeydown = function (e) { if (e.key === 'Enter') { e.preventDefault(); var v = capIcon(q.value); if (v) { addCustomIcon(v); onPick(v); close(); } } };
    function promptAdd() {
      promptDialog('เพิ่มไอคอนเอง', 'วาง/พิมพ์อีโมจิหรือสัญลักษณ์ใดก็ได้ (คัดลอกจากเว็บ/แอปอื่น)', '', function (v) {
        if (v == null) return; v = capIcon(v); if (!v) return;
        addCustomIcon(v); render(q.value);
      });
    }
    emojiPickEl.querySelector('.emoji-body').onclick = function (e) {
      var add = e.target.closest('[data-add]'); if (add) { promptAdd(); return; }
      var b = e.target.closest('.emoji-it'); if (!b) return;
      if (b.dataset.e && b.classList.contains('emoji-custom')) addCustomIcon(b.dataset.e);
      onPick(b.dataset.e); close();
    };
    emojiPickEl.querySelector('.emoji-body').oncontextmenu = function (e) {
      var b = e.target.closest('.emoji-custom'); if (!b) return;
      e.preventDefault(); removeCustomIcon(b.dataset.e); render(q.value);
    };
    emojiPickEl.querySelector('.emoji-addbtn').onclick = promptAdd;
    emojiPickEl.querySelector('.emoji-netbtn').onclick = function () { openNet(onPick); };
    emojiPickEl.querySelector('.emoji-clear').onclick = function () { onPick(''); close(); };
    emojiPickEl.querySelector('.emoji-x').onclick = close;
    // ตำแหน่ง: ใต้ปุ่มไอคอน ไม่หลุดจอ
    var r = anchor.getBoundingClientRect();
    emojiPickEl.style.display = 'flex';
    setNetMode(false);
    var w = emojiPickEl.offsetWidth, h = emojiPickEl.offsetHeight;
    var left = Math.min(r.left, window.innerWidth - w - 10);
    var top = (r.bottom + h + 8 < window.innerHeight) ? r.bottom + 6 : Math.max(8, window.innerHeight - h - 10);
    emojiPickEl.style.left = Math.max(8, left) + 'px';
    emojiPickEl.style.top = Math.max(8, top) + 'px';
    emojiPickEl.style.right = 'auto'; emojiPickEl.style.transform = 'none';
    makeDraggable(emojiPickEl, emojiPickEl.querySelector('.emoji-head'));
    PopupStack.push(emojiPickEl, function () { close(); });
    setTimeout(function () { q.focus(); }, 30);
    function close() { emojiPickEl.style.display = 'none'; PopupStack.remove(emojiPickEl); document.removeEventListener('mousedown', outside, true); document.removeEventListener('keydown', onKey, true); }
    function outside(ev) { if (!ev.target.closest('.emoji-pick') && !ev.target.closest('.stdef-icon')) close(); }
    // กด Esc เพื่อปิดตัวเลือกไอคอน
    function onKey(ev) {
      if (ev.key !== 'Escape' && ev.key !== 'Esc') return;
      ev.preventDefault(); close();
    }
    setTimeout(function () { document.addEventListener('mousedown', outside, true); document.addEventListener('keydown', onKey, true); }, 0);

    // ---------- ค้นไอคอนเวกเตอร์จากเน็ต (Iconify — ฟรี คมชัด ปรับสีได้) ----------
    function setNetMode(on) {
      emojiPickEl.querySelector('.emoji-body').style.display = on ? 'none' : '';
      emojiPickEl.querySelector('.emoji-q').style.display = on ? 'none' : '';
      emojiPickEl.querySelector('.emoji-net').style.display = on ? 'flex' : 'none';
    }
    function openNet(pick) {
      var net = emojiPickEl.querySelector('.emoji-net');
      net.innerHTML =
        '<div class="enet-bar"><button type="button" class="btn enet-back" title="กลับไปอีโมจิ">←</button>' +
        '<input class="enet-q" placeholder="พิมพ์คำค้น ไทยหรืออังกฤษ เช่น รถบรรทุก, truck, ไฟ, check…">' +
        '<button type="button" class="btn primary enet-go">ค้นหา</button></div>' +
        '<div class="enet-hint">ไอคอนเวกเตอร์ฟรีจาก Iconify · พิมพ์ไทยได้ (ระบบจะแปลเป็นคำอังกฤษให้) · คลิกเพื่อใช้ทันที</div>' +
        '<div class="enet-note" style="display:none;"></div>' +
        '<div class="enet-grid"><div class="enet-msg">พิมพ์คำค้น (ไทยก็ได้) แล้วกด “ค้นหา”</div></div>';
      setNetMode(true);
      var qi = net.querySelector('.enet-q'), grid = net.querySelector('.enet-grid');
      net.querySelector('.enet-back').onclick = function () { setNetMode(false); q.focus(); };
      net.querySelector('.enet-go').onclick = function () { netSearch(qi.value.trim(), grid); };
      qi.onkeydown = function (e) { if (e.key === 'Enter') { e.preventDefault(); netSearch(qi.value.trim(), grid); } };
      grid.onclick = function (e) {
        var b = e.target.closest('.enet-it'); if (!b) return;
        var tok = b.dataset.tok; addCustomIcon(tok); pick(tok); close();
      };
      setTimeout(function () { qi.focus(); }, 30);
    }
    var netCtl = null;
    function netSearch(query, grid) {
      var noteEl = grid.parentNode.querySelector('.enet-note');
      function setNote(html) { if (!noteEl) return; noteEl.innerHTML = html || ''; noteEl.style.display = html ? 'block' : 'none'; }
      if (!query) { setNote(''); grid.innerHTML = '<div class="enet-msg">พิมพ์คำค้นก่อน</div>'; return; }
      if (netCtl) netCtl.abort();
      var th = hasThai(query);
      setNote('');
      grid.innerHTML = '<div class="enet-msg">' + (th ? '⏳ กำลังแปลคำค้น…' : '⏳ กำลังค้น “' + query.replace(/</g, '&lt;') + '”…') + '</div>';
      // ไทย → แปลเป็นคำค้นอังกฤษก่อน (Iconify มีแต่คำอังกฤษ)
      (th ? translateTh(query) : Promise.resolve(query)).then(function (en) {
        en = (en || query).trim();
        netCtl = new AbortController();
        if (th) setNote('ค้นจากคำอังกฤษ: <b>' + en.replace(/</g, '&lt;') + '</b> · แปลจาก “' + query.replace(/</g, '&lt;') + '”');
        var api = (window.IconKit && IconKit.API) || 'https://api.iconify.design';
        return fetch(api + '/search?query=' + encodeURIComponent(en) + '&limit=90', { signal: netCtl.signal })
          .then(function (r) { return r.json(); })
          .then(function (j) {
            var icons = (j && j.icons) || [];
            if (!icons.length) { grid.innerHTML = '<div class="enet-msg">ไม่พบไอคอนสำหรับ “' + en.replace(/</g, '&lt;') + '” — ลองคำอื่น</div>'; return; }
            grid.innerHTML = icons.map(function (ic) {
              var tok = 'ico:' + ic;
              return '<button type="button" class="enet-it" data-tok="' + tok.replace(/"/g, '&quot;') + '" title="' + ic.replace(/"/g, '&quot;') + '">' + ihtml(tok) + '</button>';
            }).join('');
          });
      }).catch(function (e) {
        if (e && e.name === 'AbortError') return;
        grid.innerHTML = '<div class="enet-msg">ค้นไม่สำเร็จ — ตรวจอินเทอร์เน็ต แล้วลองใหม่</div>';
      });
    }
  }

  window.openEmojiPicker = openEmojiPicker;
})();
