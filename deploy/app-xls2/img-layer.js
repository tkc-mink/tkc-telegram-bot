/* ============================================================
   img-layer.js — รูปภาพลอยบนตาราง (แบบ Excel)
   แนบไฟล์ / วางจากคลิปบอร์ด (ก๊อบจาก Google) / ลากไฟล์มาวาง
   ย้าย-ย่อขยาย-หมุน-ตัดภาพ (crop) - เรียงชั้นหน้า/หลัง
   คลิกขวามีเมนู · Copy/Cut/Paste/Delete ด้วยคีย์ลัด
   เก็บใน doc.images → บันทึก/สลับหมวดตามชีตอัตโนมัติ
   ============================================================ */
(function () {
  var layer = null, gw = null;
  var selId = null, clipObj = null, clipCut = false;
  var drag = null;   // {mode:'move|resize|rotate|crop-t/r/b/l', id, sx, sy, orig}
  var rotPending = null;   // {id, prevRot} — สำหรับ Esc คืนองศาหลังหมุน (ยังไม่คลิกที่อื่น)
  var ctxEl = null;

  function doc() { return SG.getDoc(); }
  function imgs() { var d = doc(); if (!d.images) d.images = []; return d.images; }
  function byId(id) { return imgs().find(function (i) { return i.id === id; }); }
  function uid() { return 'i' + Date.now() + Math.floor(Math.random() * 999); }
  function persist() { SG.save(); }
  function pu() { if (SG.pushUndo) SG.pushUndo(); }   // จุด undo ร่วมกับตาราง (Ctrl+Z ย้อนได้)
  function maxZ() { return imgs().reduce(function (m, i) { return Math.max(m, i.z || 0); }, 0); }
  function minZ() { return imgs().reduce(function (m, i) { return Math.min(m, i.z || 0); }, 0); }

  // ---------- เพิ่มรูป ----------
  function addImage(src, x, y) {
    var im = new Image();
    im.onload = function () {
      var w = im.naturalWidth, h = im.naturalHeight;
      var cap = 320;
      if (w > cap) { h = h * cap / w; w = cap; }
      if (h > cap) { w = w * cap / h; h = cap; }
      var sc = gw ? gw.scrollLeft : 0, st = gw ? gw.scrollTop : 0;
      var o = { id: uid(), src: src, x: (x != null ? x : sc + 120), y: (y != null ? y : st + 120),
        w: Math.round(w), h: Math.round(h), rot: 0, z: maxZ() + 1, crop: { t: 0, r: 0, b: 0, l: 0 } };
      pu();
      imgs().push(o);
      selId = o.id;
      persist(); render();
      toast('🖼️ แนบรูปแล้ว — ลากย้าย/มุมย่อขยาย · คลิกขวาดูเมนู');
    };
    im.src = src;
  }
  function addFromFile(file, x, y) {
    if (!file || !/^image\//.test(file.type)) return;
    var rd = new FileReader();
    rd.onload = function () { addImage(rd.result, x, y); };
    rd.readAsDataURL(file);
  }
  function pickFile() {
    var inp = document.createElement('input');
    inp.type = 'file'; inp.accept = 'image/*';
    inp.onchange = function () { addFromFile(inp.files[0]); };
    inp.click();
  }
  // ---------- ค้นรูปในตัวโปรแกรม (แสดงผล + เลือกหลายรูป นำเข้าทันที) ----------
  var dlg = null, picked = {}, results = [], extFilter = 'all', lastQ = '';
  var pageIdx = 0;
  var PAGE_SIZE = 8;
  function extOf(u) {
    var m = /\.(png|jpe?g|gif|webp|svg|bmp|avif)(\?|#|$)/i.exec(String(u || ''));
    if (!m) return 'other';
    var e = m[1].toLowerCase();
    return e === 'jpeg' ? 'jpg' : e;
  }
  function renderResults() {
    var grid = dlg.querySelector('.is-grid');
    var pager = dlg.querySelector('.is-pager');
    var list = results.map(function (x, i) { x._k = i; return x; }).filter(function (x) {
      var e = extOf(x.url || x.thumb);
      if (extFilter === 'all') return true;
      if (extFilter === 'other') return ['png', 'jpg', 'webp', 'gif', 'svg'].indexOf(e) < 0;
      return e === extFilter;
    });
    var total = list.length;
    var pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (pageIdx >= pages) pageIdx = pages - 1;
    if (pageIdx < 0) pageIdx = 0;
    var pageItems = list.slice(pageIdx * PAGE_SIZE, pageIdx * PAGE_SIZE + PAGE_SIZE);
    grid.innerHTML = pageItems.length ? pageItems.map(function (x) {
      var e = extOf(x.url || x.thumb).toUpperCase();
      return '<div class="is-it' + (picked[x._k] ? ' sel' : '') + '" data-k="' + x._k + '" title="' + (x.title || '').replace(/"/g, '') + '"><img loading="lazy" src="' + x.thumb + '" /><span class="is-ext">' + e + '</span><span class="is-chk">✓</span></div>';
    }).join('') : '<div class="is-msg">ไม่มีรูปนามสกุลนี้ในผลลัพธ์ — ลอง ทั้งหมด</div>';
    if (pager) {
      if (total > 0) {
        var from = pageIdx * PAGE_SIZE + 1;
        var to = Math.min(total, (pageIdx + 1) * PAGE_SIZE);
        pager.innerHTML =
          '<button class="is-pg is-prev"' + (pageIdx <= 0 ? ' disabled' : '') + ' title="หน้าก่อนหน้า">‹</button>' +
          '<span class="is-pgcount"><b>' + total + '</b> รูป · แสดง ' + from + '–' + to + ' · หน้า ' + (pageIdx + 1) + '/' + pages + '</span>' +
          '<button class="is-pg is-next"' + (pageIdx >= pages - 1 ? ' disabled' : '') + ' title="หน้าถัดไป">›</button>';
        pager.style.display = 'flex';
      } else {
        pager.innerHTML = ''; pager.style.display = 'none';
      }
    }
  }
  function googleSearch() { openSearchDlg(); }
  function openSearchDlg() {
    if (!dlg) {
      dlg = document.createElement('div');
      dlg.className = 'imgsearch';
      dlg.innerHTML =
        '<div class="is-head">🔎 ค้นหารูปภาพ<span class="is-x" title="ปิด">✕</span></div>' +
        '<div class="is-bar"><input class="is-q" placeholder="พิมพ์คำค้น เช่น tire, ยางรถยนต์…" />' +
        '<button class="btn primary is-go">ค้นหา</button>' +
        '<button class="btn is-open" title="เปิดผลค้นรูปในเบราว์เซอร์ (DuckDuckGo) — คลิกขวารูป คัดลอกรูปภาพ แล้วกลับมาวาง Ctrl+V">เปิดเว็บ ↗</button></div>' +
        '<div class="is-exts"><span class="is-extlab">นามสกุล:</span>' +
        ['all|ทั้งหมด', 'png|PNG', 'jpg|JPG', 'webp|WEBP', 'gif|GIF', 'svg|SVG', 'other|อื่นๆ'].map(function (p, i) {
          var a = p.split('|');
          return '<span class="is-extchip' + (i === 0 ? ' on' : '') + '" data-ext="' + a[0] + '">' + a[1] + '</span>';
        }).join('') + '</div>' +
        '<div class="is-grid"></div>' +
        '<div class="is-pager" style="display:none;"></div>' +
        '<div class="is-foot"><span class="is-note">คลิกรูปเพื่อเลือกได้หลายรูป · <span class="is-setw" style="cursor:pointer;text-decoration:underline;">⚙ ตั้งค่าพร็อกซี</span></span>' +
        '<button class="btn primary is-import" disabled>นำเข้า 0 รูป</button></div>';
      document.body.appendChild(dlg);
      dlg.querySelector('.is-x').onclick = function () { dlg.style.display = 'none'; };
      dlg.querySelector('.is-go').onclick = function () { doSearch(dlg.querySelector('.is-q').value.trim()); };
      dlg.querySelector('.is-q').addEventListener('keydown', function (e) { if (e.key === 'Enter') doSearch(this.value.trim()); });
      dlg.querySelector('.is-open').onclick = function () {
        var q = dlg.querySelector('.is-q').value.trim();
        if (!q) { dlg.querySelector('.is-q').focus(); return; }
        window.open('https://duckduckgo.com/?q=' + encodeURIComponent(q) + '&iax=images&ia=images', '_blank', 'noopener');
        toast('เปิดผลค้นในแท็บใหม่ — คลิกขวารูป “คัดลอกรูปภาพ” แล้วกลับมาวาง Ctrl+V บนตาราง');
      };
      dlg.querySelector('.is-setw').onclick = function () {
        var cur = localStorage.getItem('xls2_ddgw') || '';
        var apply = function (v) {
          if (v === null) return;
          v = v.trim();
          localStorage.setItem('xls2_ddgw', v);
          toast(v ? '✅ ตั้งค่าพร็อกซีแล้ว — ค้นทั่วเว็บได้เลย เร็วและเสถียร' : 'ปิดพร็อกซีแล้ว');
          var q = dlg.querySelector('.is-q').value.trim();
          if (v && q) doSearch(q);
        };
        if (window.AppDialog) AppDialog.prompt('ตั้งค่าพร็อกซีค้นรูป', 'วาง URL ของ Cloudflare Worker เช่น https://ddg-img.บัญชี.workers.dev<br>(เว้นว่าง = ปิดพร็อกซี กลับไปใช้คลังเสรี)', cur, apply);
        else apply(prompt('วาง URL ของ Cloudflare Worker (พร็อกซีค้นรูป)', cur));
      };
      dlg.querySelector('.is-grid').onclick = function (e) {
        var it = e.target.closest('.is-it'); if (!it) return;
        openPreview(+it.dataset.k);   // คลิกรูป 1 ครั้ง → ดูรูปเต็มก่อน แล้วค่อยเลือก
      };
      dlg.querySelector('.is-pager').onclick = function (e) {
        var b = e.target.closest('.is-pg'); if (!b || b.disabled) return;
        pageIdx += b.classList.contains('is-next') ? 1 : -1;
        renderResults();
        var g = dlg.querySelector('.is-grid'); if (g) g.scrollTop = 0;
      };
      dlg.querySelector('.is-import').onclick = importPicked;
      dlg.querySelector('.is-exts').onclick = function (e) {
        var c = e.target.closest('.is-extchip'); if (!c) return;
        extFilter = c.dataset.ext;
        pageIdx = 0;
        dlg.querySelectorAll('.is-extchip').forEach(function (x) { x.classList.toggle('on', x === c); });
        renderResults();   // แค่กรองผลที่ค้นมาแล้ว ไม่ค้นใหม่ (ค้นใหม่เฉพาะกด Enter/ปุ่มค้นหา)
      };
      document.addEventListener('keydown', function (e) {
        if (!dlg || dlg.style.display === 'none') return;
        if (e.key === 'Escape') { dlg.style.display = 'none'; return; }   // Esc = ปิด
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          if (document.activeElement === dlg.querySelector('.is-q')) return;   // กำลังพิมพ์ในช่องค้น → ไม่เปลี่ยนหน้า
          var btn = dlg.querySelector(e.key === 'ArrowRight' ? '.is-next' : '.is-prev');
          if (btn && !btn.disabled) {
            pageIdx += (e.key === 'ArrowRight' ? 1 : -1);
            renderResults();
            var g = dlg.querySelector('.is-grid'); if (g) g.scrollTop = 0;
            e.preventDefault();
          }
        }
      });
      // ---------- ลากหน้าต่างย้ายตำแหน่งได้ (จับที่แถบหัว) ----------
      (function () {
        var head = dlg.querySelector('.is-head');
        head.style.cursor = 'move';
        head.addEventListener('mousedown', function (e) {
          if (e.target.closest('.is-x')) return;   // ปุ่มปิดไม่ถือเป็นการลาก
          var rect = dlg.getBoundingClientRect();
          dlg.style.left = rect.left + 'px';
          dlg.style.top = rect.top + 'px';
          dlg.style.transform = 'none';
          var ox = e.clientX - rect.left, oy = e.clientY - rect.top;
          function mv(ev) {
            var x = Math.max(0, Math.min(ev.clientX - ox, window.innerWidth - dlg.offsetWidth));
            var y = Math.max(0, Math.min(ev.clientY - oy, window.innerHeight - dlg.offsetHeight));
            dlg.style.left = x + 'px'; dlg.style.top = y + 'px';
          }
          function up() { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); }
          document.addEventListener('mousemove', mv);
          document.addEventListener('mouseup', up);
          e.preventDefault();
        });
      })();
    }
    dlg.style.display = 'flex';
    setTimeout(function () { dlg.querySelector('.is-q').focus(); }, 50);
  }
  function openPreview(k) {
    var x = results[k]; if (!x) return;
    var pv = document.createElement('div');
    pv.className = 'is-preview';
    var on = !!picked[k];
    pv.innerHTML = '<div class="isp-box">' +
      '<img src="' + (x.url || x.thumb) + '" />' +
      '<div class="isp-bar"><span class="isp-t">' + (x.title || '').replace(/</g, '&lt;') + '</span>' +
      '<span class="isp-act"><button class="btn isp-cancel">ยกเลิก (Esc)</button>' +
      '<button class="btn primary isp-pick">' + (on ? '✓ เลือกแล้ว — เอาออก' : '✓ เลือกรูปนี้') + '</button></span></div></div>';
    document.body.appendChild(pv);
    pv._esc = function (e) { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
    function close() { document.removeEventListener('keydown', pv._esc, true); pv.remove(); }
    pv.querySelector('.isp-box').onclick = function (e) { e.stopPropagation(); };
    pv.onclick = close;
    pv.querySelector('.isp-cancel').onclick = close;
    pv.querySelector('.isp-pick').onclick = function () {
      if (picked[k]) delete picked[k]; else picked[k] = results[k];
      var it = dlg.querySelector('.is-it[data-k="' + k + '"]');
      if (it) it.classList.toggle('sel', !!picked[k]);
      updImport();
      close();
    };
    document.addEventListener('keydown', pv._esc, true);
  }
  function updImport() {
    var n = Object.keys(picked).length;
    var b = dlg.querySelector('.is-import');
    b.disabled = !n;
    b.textContent = 'นำเข้า ' + n + ' รูป';
  }
  // ---------- ค้นหาอัจฉริยะ: ผสมคำ / แยกคำ / ขยายคำพ้อง + dedupe + จัดลำดับความตรง ----------
  var SYN = { otani: 'otani tire', ยาง: 'tire', ยางรถ: 'car tire', รถยนต์: 'car', ล้อ: 'wheel', ขอบ: 'tire rim', โลโก้: 'logo', ปิคอัพ: 'pickup truck', กระบะ: 'truck' };
  function expandWord(w) { return SYN[w.toLowerCase()] || w; }
  function buildQueries(raw) {
    var s = String(raw || '').trim().replace(/\s+/g, ' ');
    if (!s) return [];
    var words = s.split(' ');
    var qs = [];
    qs.push(s);                                           // 1) ทั้งวลีตามที่พิมพ์
    var expanded = words.map(expandWord).join(' ');
    if (expanded !== s) qs.push(expanded);               // 2) ขยายศัพท์ (otani→otani tire)
    if (words.length > 1) {
      qs.push(words.join(' OR '));                       // 3) แยกคำ OR (เจออย่างน้อยคำหนึ่ง)
      // 4) แยกทีละคำ (ขยายศัพท์ด้วย) — จับผลแม้คำใดคำหนึ่งไม่มีในคลัง
      words.forEach(function (w) { if (w.length > 1) { qs.push(w); var ex = expandWord(w); if (ex !== w) qs.push(ex); } });
    }
    // ตัดซ้ำ
    var seen = {}; return qs.filter(function (q) { q = q.trim(); if (!q || seen[q]) return false; seen[q] = 1; return true; });
  }
  function scoreOf(title, words) {
    var t = String(title || '').toLowerCase();
    var hit = 0; words.forEach(function (w) { if (w.length > 1 && t.indexOf(w.toLowerCase()) >= 0) hit++; });
    return hit;
  }
  function ovImages(q, extQ) {
    return fetch('https://api.openverse.org/v1/images/?q=' + encodeURIComponent(q) + '&page_size=40' + extQ)
      .then(function (r) { return r.json(); })
      .then(function (j) { return (j.results || []).map(function (x) { return { thumb: x.thumbnail, url: x.url, title: x.title || '' }; }); })
      .catch(function () { return []; });
  }
  // ค่าตั้ง Google Custom Search (key + cx) — ใส่ครั้งเดียวเก็บถาวร
  function gcfg() { try { return JSON.parse(localStorage.getItem('xls2_gcse') || '{}'); } catch (e) { return {}; } }
  function gImages(q) {
    var c = gcfg();
    var typ = (['png', 'jpg', 'gif', 'bmp', 'svg'].indexOf(extFilter) >= 0) ? '&fileType=' + (extFilter === 'jpg' ? 'jpg' : extFilter) : '';
    return fetch('https://www.googleapis.com/customsearch/v1?searchType=image&num=10&key=' + encodeURIComponent(c.key) + '&cx=' + encodeURIComponent(c.cx) + typ + '&q=' + encodeURIComponent(q))
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.error) throw j.error.message || 'gerror';
        return (j.items || []).map(function (x) {
          return { thumb: (x.image && x.image.thumbnailLink) || x.link, url: x.link, title: x.title || '' };
        });
      });
  }
  // ---------- Cloudflare Worker (พร็อกซีของผู้ใช้เอง — เร็ว/เสถียรสุด) ----------
  function wurl() { return (localStorage.getItem('xls2_ddgw') || '').trim().replace(/\/$/, ''); }
  // ค้นผ่าน Worker: ยิงครั้งเดียว Worker ทำ 2 สเต็ปฝั่งเซิร์ฟเวอร์ให้ → คืน JSON results
  function ddgViaWorker(q) {
    var w = wurl(); if (!w) return Promise.reject('no-worker');
    var ac = new AbortController(); var to = setTimeout(function () { ac.abort(); }, 12000);
    return fetch(w + (w.indexOf('?') >= 0 ? '&' : '?') + 'q=' + encodeURIComponent(q), { signal: ac.signal })
      .then(function (r) { clearTimeout(to); if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        if (j && j.error && !(j.results && j.results.length)) throw j.error;
        return ((j && j.results) || []).map(function (x) {
          return { thumb: x.thumb || x.url, url: x.url || x.thumb, title: x.title || '' };
        }).filter(function (x) { return x.url; });
      }).catch(function (e) { clearTimeout(to); throw e; });
  }
  // ---------- DuckDuckGo: ค้นทั่วเว็บผ่าน CORS proxy (สำรอง ถ้าไม่ได้ตั้ง Worker) ----------
  // หมายเหตุ: DDG ไม่มี API ทางการและไม่ส่ง CORS header จึงต้องผ่าน proxy 2 ขั้น
  //   1) ดึงหน้า HTML เพื่อหา token (vqd)  2) เรียก i.js เอาผลลัพธ์ JSON
  // proxy แต่ละตัว: mk=สร้าง url, wrap=true ถ้าผลห่อใน {contents} (allorigins /get)
  var DDG_PROXIES = [
    { wrap: true, mk: function (u) { return 'https://api.allorigins.win/get?url=' + encodeURIComponent(u); } },
    { wrap: false, mk: function (u) { return 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u); } },
    { wrap: false, mk: function (u) { return 'https://thingproxy.freeboard.io/fetch/' + u; } }
  ];
  // ดึงข้อความผ่าน proxy ทีละตัว · แต่ละตัวมี timeout 7 วิ (กันค้าง) · คืน text เสมอ
  function proxyText(url, pi) {
    pi = pi || 0;
    if (pi >= DDG_PROXIES.length) return Promise.reject('proxy-fail');
    var p = DDG_PROXIES[pi];
    var ac = new AbortController();
    var to = setTimeout(function () { ac.abort(); }, 7000);
    return fetch(p.mk(url), { signal: ac.signal }).then(function (r) {
      clearTimeout(to);
      if (!r.ok) throw 0;
      return p.wrap ? r.json().then(function (j) { return j.contents || ''; }) : r.text();
    }).catch(function () { clearTimeout(to); return proxyText(url, pi + 1); });
  }
  // โหลดรูปเป็น Blob — ลองตรงก่อน ถ้าโดน CORS บล็อกค่อยวิ่งผ่าน Worker/พร็อกซี (timeout 8 วิ/ตัว)
  function blobFrom(url) {
    if (!url) return Promise.reject('no-url');
    var w = wurl();
    var tries = [url];
    if (w) tries.push(w + (w.indexOf('?') >= 0 ? '&' : '?') + 'url=' + encodeURIComponent(url));
    tries.push('https://api.allorigins.win/raw?url=' + encodeURIComponent(url));
    tries.push('https://thingproxy.freeboard.io/fetch/' + url);
    var i = 0;
    function attempt() {
      if (i >= tries.length) return Promise.reject('blob-fail');
      var ac = new AbortController(); var to = setTimeout(function () { ac.abort(); }, 8000);
      return fetch(tries[i++], { signal: ac.signal }).then(function (r) {
        clearTimeout(to); if (!r.ok) throw 0; return r.blob();
      }).catch(function () { clearTimeout(to); return attempt(); });
    }
    return attempt();
  }
  function ddgImages(q) {
    // ถ้าตั้ง Worker ไว้ → ใช้ Worker ก่อน (เร็ว/เสถียร) · ล้มเหลวค่อยตกไปพร็อกซีสาธารณะ
    if (wurl()) return ddgViaWorker(q).catch(function () { return ddgProxy(q); });
    return ddgProxy(q);
  }
  function ddgProxy(q) {
    var tok = 'https://duckduckgo.com/?q=' + encodeURIComponent(q) + '&iar=images&iax=images&ia=images';
    return proxyText(tok).then(function (html) {
      var m = String(html).match(/vqd=['"]?([-0-9a-z]+)['"]?/i);
      if (!m) throw 'no-vqd';
      var img = 'https://duckduckgo.com/i.js?l=us-en&o=json&q=' + encodeURIComponent(q) + '&vqd=' + encodeURIComponent(m[1]) + '&f=,,,&p=1';
      return proxyText(img);
    }).then(function (txt) {
      var j = {}; try { j = JSON.parse(txt); } catch (e) { throw 'bad-json'; }
      return ((j && j.results) || []).map(function (x) {
        return { thumb: x.thumbnail || x.image, url: x.image || x.thumbnail, title: x.title || '' };
      }).filter(function (x) { return x.url; });
    });
  }
  function ddgSearch(q, extQ, words, grid) {
    grid.innerHTML = '<div class="is-msg">⏳ กำลังค้นทั่วเว็บ' + (wurl() ? ' (Cloudflare)' : ' (DuckDuckGo)') + '…</div>';
    ddgImages(q).then(function (list) {
      if (list && list.length) {
        list.forEach(function (x) { x._score = scoreOf(x.title, words); });
        list.sort(function (a, b) { return (b._score || 0) - (a._score || 0); });
        results = list.slice(0, 80);
        renderResults();
      } else { ovSearch(q, extQ, words, grid); }
    }).catch(function () { ovSearch(q, extQ, words, grid); });
  }
  function doSearch(q) {
    if (!q) return;
    lastQ = q;
    pageIdx = 0;
    var grid = dlg.querySelector('.is-grid');
    grid.innerHTML = '<div class="is-msg">⏳ กำลังค้นหา…</div>';
    picked = {}; results = []; updImport();
    var extQ = (['png', 'jpg', 'webp', 'gif', 'svg'].indexOf(extFilter) >= 0) ? '&extension=' + (extFilter === 'jpg' ? 'jpg' : extFilter) : '';
    var words = q.replace(/\s+/g, ' ').split(' ');
    // ค้นทั่วเว็บผ่าน Worker/DuckDuckGo · ถ้าล้ม fallback ไปคลังเสรี
    ddgSearch(q, extQ, words, grid);
  }
  function ovSearch(q, extQ, words, grid) {
    var queries = buildQueries(q);
    Promise.all(queries.map(function (qq) { return ovImages(qq, extQ); })).then(function (lists) {
      // รวมผลตามลำดับความสำคัญ (คิวแรกได้น้ำหนักกว่า) + ตัดซ้ำด้วย url
      var seen = {}, merged = [];
      lists.forEach(function (list, qi) {
        list.forEach(function (x) {
          var key = x.url || x.thumb; if (!key || seen[key]) return; seen[key] = 1;
          x._score = scoreOf(x.title, words) * 10 - qi;   // คำตรงชื่อ + มาจากคิวตรงก่อน
          merged.push(x);
        });
      });
      merged.sort(function (a, b) { return (b._score || 0) - (a._score || 0); });
      results = merged.slice(0, 60);
      if (results.length) renderResults();
      else wikiFallback(q, grid);
    });
  }
  function wikiFallback(q, grid) {
    fetch('https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=' + encodeURIComponent(q) + '&gsrnamespace=6&gsrlimit=30&prop=imageinfo&iiprop=url&iiurlwidth=300&format=json&origin=*')
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var pages = (j.query && j.query.pages) || {};
        results = Object.keys(pages).map(function (k) {
          var ii = pages[k].imageinfo && pages[k].imageinfo[0];
          return ii ? { thumb: ii.thumburl, url: ii.url, title: pages[k].title } : null;
        }).filter(Boolean);
        if (results.length) renderResults();
        else grid.innerHTML = '<div class="is-msg">ไม่พบรูปสำหรับ “' + (lastQ || '').replace(/</g, '&lt;') + '”<br>ลองพิมพ์ให้จำเพาะขึ้น เช่น <b>otani sa3000</b> · หรือกด <b>เปิดเว็บ ↗</b> แล้วคัดลอกรูปมาวาง Ctrl+V</div>';
      })
      .catch(function () { grid.innerHTML = '<div class="is-msg">ค้นไม่สำเร็จ — ตรวจอินเทอร์เน็ต/พร็อกซี หรือกด <b>เปิดเว็บ ↗</b> แล้วคัดลอกรูปมาวาง Ctrl+V</div>'; });
  }
  function importPicked() {
    var list = Object.keys(picked).map(function (k) { return picked[k]; });
    if (!list.length) return;
    toast('⏳ กำลังนำเข้า ' + list.length + ' รูป…');
    var off = 0;
    list.forEach(function (x) {
      var myOff = off; off += 30;
      // พยายามโหลดไฟล์เต็มก่อน (คมชัดเต็มรูป) · ถ้าต้นทางบล็อก ลองผ่าน proxy แล้วค่อยใช้ภาพย่อแทน
      blobFrom(x.url).catch(function () { return blobFrom(x.thumb); })
        .then(function (b) {
          var rd = new FileReader();
          rd.onload = function () { addImage(rd.result, (gw ? gw.scrollLeft : 0) + 130 + myOff, (gw ? gw.scrollTop : 0) + 130 + myOff); };
          rd.readAsDataURL(b);
        }).catch(function () { toast('⚠️ นำเข้าบางรูปไม่สำเร็จ'); });
    });
    picked = {}; updImport();
    dlg.style.display = 'none';
  }

  function toast(s) { if (window.SG && SG.toast) SG.toast(s); else { var t = document.getElementById('toast'); if (t) { t.textContent = s; t.classList.add('show'); clearTimeout(t._tm); t._tm = setTimeout(function () { t.classList.remove('show'); }, 2600); } } }

  // ---------- AI ตกแต่งรูป (เรียกผ่านระบบหลายผู้ให้บริการ + สำรอง) ----------
  // ---------- AI ตกแต่งรูป (เรียกผ่านระบบหลายผู้ให้บริการ + สำรอง) ----------
  function ppxEdit(o) {
    if (!window.PhotopeaEdit) { toast('Photopea ยังไม่พร้อม'); return; }
    var id = o.id;   // แก้เฉพาะรูปนี้รูปเดียว
    PhotopeaEdit.open(o.src, function (newSrc) {
      var im = byId(id); if (!im) return;
      pu(); im.src = newSrc; persist(); render();
    });
  }
  function aiRun(o, task, promptText) {
    if (!window.AIImage) { toast('โมดูล AI ยังไม่พร้อม'); return; }
    AIImage.editImage(o.src, task, promptText).then(function (newSrc) {
      pu(); o.src = newSrc; persist(); render();
      toast('✅ AI แก้รูปเสร็จแล้ว (Ctrl+Z ย้อนได้)');
    }).catch(function (err) {
      toast('⚠️ AI ไม่สำเร็จ: ' + (err && err.message || err));
    });
  }

  // ---------- render ----------
  function render() {
    if (!layer) return;
    var isAdmin = SG.getMode() === 'admin';
    layer.innerHTML = imgs().slice().sort(function (a, b) { return (a.z || 0) - (b.z || 0); }).map(function (o) {
      var cr = o.crop || { t: 0, r: 0, b: 0, l: 0 };
      var on = o.id === selId;
      var cropping = on && isAdmin && cropTarget === o.id;
      var marks = (on ? ' on' : '') + (cropping ? ' cropping' : '') + (clipObj && clipObj.id === o.id ? (clipCut ? ' cutmark' : ' copymark') : '');
      if (cropping) {
        // โหมดตัดภาพ: กล่องเท่ารูปเต็ม เพื่อเห็นภาพทั้งหมด + เลือกกรอบครอป
        var head = '<div class="imgw' + marks + '" data-img="' + o.id + '"' +
          ' style="left:' + o.x + 'px;top:' + o.y + 'px;width:' + o.w + 'px;height:' + o.h + 'px;transform:rotate(' + (o.rot || 0) + 'deg);z-index:' + (10 + (o.z || 0)) + ';">';
        var L = cr.l, T = cr.t, R = cr.r, B = cr.b, W = 100 - cr.l - cr.r, H = 100 - cr.t - cr.b;
        return head +
          '<img src="' + o.src + '" draggable="false" class="cropfull" />' +
          '<div class="crop-shade" style="left:0;top:0;width:100%;height:' + T + '%;"></div>' +
          '<div class="crop-shade" style="left:0;bottom:0;width:100%;height:' + B + '%;"></div>' +
          '<div class="crop-shade" style="left:0;top:' + T + '%;width:' + L + '%;height:' + H + '%;"></div>' +
          '<div class="crop-shade" style="right:0;top:' + T + '%;width:' + R + '%;height:' + H + '%;"></div>' +
          '<div class="crop-box" data-h="cp-pan" title="ลากเพื่อเลื่อนเลือกส่วนของรูป" style="left:' + L + '%;top:' + T + '%;width:' + W + '%;height:' + H + '%;">' +
          '<span class="cg v1"></span><span class="cg v2"></span><span class="cg h1"></span><span class="cg h2"></span>' +
          ['nw', 'ne', 'sw', 'se'].map(function (d) { return '<span class="ch c ' + d + '" data-h="cp-' + d + '"></span>'; }).join('') +
          ['t', 'b', 'l', 'r'].map(function (d) { return '<span class="ch e ' + d + '" data-h="cp-' + d + '"></span>'; }).join('') +
          '</div>' +
          '</div>';
      }
      // แสดงผลปกติ: กล่องหดเหลือเท่าส่วนที่ครอปไว้ · รูปเลื่อนให้เต็มกล่องพอดี (ไม่บิดเบี้ยว)
      var kw = Math.max(0.02, 1 - (cr.l + cr.r) / 100), kh = Math.max(0.02, 1 - (cr.t + cr.b) / 100);
      var bx = o.x + (cr.l / 100) * o.w, by = o.y + (cr.t / 100) * o.h, bw = o.w * kw, bh = o.h * kh;
      return '<div class="imgw' + marks + '" data-img="' + o.id + '"' +
        ' style="left:' + bx + 'px;top:' + by + 'px;width:' + bw + 'px;height:' + bh + 'px;transform:rotate(' + (o.rot || 0) + 'deg);z-index:' + (10 + (o.z || 0)) + ';">' +
        '<div class="imgclip"><img src="' + o.src + '" draggable="false" style="position:absolute;left:' + (-(cr.l / 100) * o.w) + 'px;top:' + (-(cr.t / 100) * o.h) + 'px;width:' + o.w + 'px;height:' + o.h + 'px;max-width:none;" /></div>' +
        (on && isAdmin ? '<span class="imh rot" data-h="rotate" title="ลากเพื่อหมุนภาพ (กด Shift = ทีละ 15°)">↻</span>' +
          ['nw', 'ne', 'sw', 'se'].map(function (d) { return '<span class="imh rs ' + d + '" data-h="rs-' + d + '"></span>'; }).join('')
          : '') +
        '</div>';
    }).join('');
  }
  var cropTarget = null;   // id ที่อยู่ในโหมดตัดภาพ
  function renderAll() { render(); }

  // ---------- เมนูคลิกขวา ----------
  function closeMenu() { if (ctxEl) ctxEl.style.display = 'none'; }
  function openMenu(o, x, y) {
    if (!ctxEl) { ctxEl = document.createElement('div'); ctxEl.className = 'sg-ctx'; document.body.appendChild(ctxEl); }
    var reg = [];
    function it(ic, t, fn) { reg.push(fn); return '<div class="ctx-it" data-i="' + (reg.length - 1) + '"><span class="ctx-ic">' + ic + '</span><span class="ctx-tx">' + t + '</span></div>'; }
    function sep() { return '<div class="ctx-sep"></div>'; }
    ctxEl.innerHTML =
      it('✂️', 'ตัด (Ctrl+X)', function () { clipObj = JSON.parse(JSON.stringify(o)); clipCut = true; render(); }) +
      it('📋', 'คัดลอก (Ctrl+C)', function () { clipObj = JSON.parse(JSON.stringify(o)); clipCut = false; render(); toast('คัดลอกรูปแล้ว — Ctrl+V วาง'); }) +
      sep() +
      it('🖼️', cropTarget === o.id ? 'เสร็จสิ้นการตัดภาพ' : 'ตัดภาพ (crop)…', function () {
        cropTarget = (cropTarget === o.id) ? null : o.id;
        drag = cropTarget ? { cropMode: o.id } : null;
        render();
        if (cropTarget) toast('โหมดตัดภาพ (เหมือน Excel): ลากมุม/ขอบกรอบเพื่อย่อ · ลากกลางกรอบเพื่อเลื่อนเลือกส่วนรูป · คลิกขวา → เสร็จสิ้น');
      }) +
      it('♻️', 'รีเซ็ตการตัดภาพ', function () { pu(); o.crop = { t: 0, r: 0, b: 0, l: 0 }; persist(); render(); }) +
      it('↻', 'หมุน 90°', function () { pu(); o.rot = ((o.rot || 0) + 90) % 360; persist(); render(); }) +
      it('↺', 'หมุน −90°', function () { pu(); o.rot = ((o.rot || 0) - 90 + 360) % 360; persist(); render(); }) +
      sep() +
      it('🪄', 'AI: ลบพื้นหลัง (ทำพื้นใส)', function () { aiRun(o, 'removebg', ''); }) +
      it('🤖', 'AI: พิมพ์คำสั่งแก้รูป…', function () {
        var apply = function (p) { if (p && p.trim()) aiRun(o, 'edit', p.trim()); };
        if (window.AppDialog) AppDialog.prompt('สั่ง AI แก้รูป', 'พิมพ์คำสั่ง เช่น ทำพื้นหลังให้ใส · เปลี่ยนพื้นหลังเป็นสีขาว · ลบวัตถุที่ไม่ต้องการ', '', apply);
        else apply(prompt('สั่ง AI แก้รูป'));
      }) +
      it('⚙', 'ตั้งค่า AI (ลำดับ/ลิงก์)…', function () { if (window.AIImage) AIImage.openSettings(); }) +
      it('🎨', 'เปิดแก้ใน Photopea (แต่งเอง ฟรี)…', function () { ppxEdit(o); }) +
      sep() +
      it('⬆️', 'มาหน้าสุด', function () { pu(); o.z = maxZ() + 1; persist(); render(); }) +
      it('🔼', 'ขึ้นหนึ่งชั้น', function () { pu(); o.z = (o.z || 0) + 1.5; normZ(); persist(); render(); }) +
      it('🔽', 'ลงหนึ่งชั้น', function () { pu(); o.z = (o.z || 0) - 1.5; normZ(); persist(); render(); }) +
      it('⬇️', 'ไปหลังสุด', function () { pu(); o.z = minZ() - 1; persist(); render(); }) +
      sep() +
      it('🗑️', 'ลบรูป (Delete)', function () { removeImg(o.id); });
    ctxEl.style.display = 'block';
    var vw = window.innerWidth, vh = window.innerHeight;
    ctxEl.style.left = Math.min(x, vw - ctxEl.offsetWidth - 8) + 'px';
    var mh = ctxEl.offsetHeight;
    ctxEl.style.top = Math.max(8, Math.min(y > vh / 2 ? y - mh - 6 : y + 6, vh - mh - 8)) + 'px';
    ctxEl.onclick = function (e) {
      var el = e.target.closest('[data-i]'); if (!el) return;
      closeMenu(); reg[+el.dataset.i]();
    };
  }
  function normZ() {
    imgs().slice().sort(function (a, b) { return (a.z || 0) - (b.z || 0); }).forEach(function (o, i) { o.z = i + 1; });
  }
  function removeImg(id) {
    pu();
    var d = doc();
    d.images = imgs().filter(function (i) { return i.id !== id; });
    if (selId === id) selId = null;
    if (cropTarget === id) { cropTarget = null; drag = null; }
    persist(); render();
  }

  // ---------- ปฏิสัมพันธ์ ----------
  function onDown(e) {
    var w = e.target.closest ? e.target.closest('.imgw') : null;
    var hEl = e.target.closest ? e.target.closest('[data-h]') : null;
    if (!hEl && !w) { if (selId != null && !e.target.closest('.sg-ctx')) { selId = null; cropTarget = null; rotPending = null; render(); } return; }
    if (SG.getMode() !== 'admin') return;
    var id = w ? w.dataset.img : (hEl && hEl.closest('.imgw') ? hEl.closest('.imgw').dataset.img : null);
    var o = byId(id); if (!o) return;
    e.preventDefault(); e.stopPropagation();
    if (e.button === 2) { selId = id; render(); return; }   // contextmenu จะตามมา
    if (rotPending && rotPending.id !== id) rotPending = null;   // เลือกรูปอื่น = ปิดการคืนค่าหมุนของรูปก่อนหน้า
    selId = id;
    var base = { x: o.x, y: o.y, w: o.w, h: o.h, rot: o.rot || 0, crop: JSON.parse(JSON.stringify(o.crop || { t: 0, r: 0, b: 0, l: 0 })) };
    var mode = hEl ? hEl.dataset.h : 'move';
    // ยังไม่ pu()/persist ตอนนี้ — คลิกเฉยๆ = แค่เลือกรูป (ไม่เซฟ) · จะเซฟตอนขยับ/ย่อ/หมุนจริงเท่านั้น
    drag = { id: id, mode: mode, sx: e.clientX, sy: e.clientY, orig: base, cropMode: cropTarget, moved: false };
    render();
  }
  function onMove(e) {
    if (!drag || !drag.mode) return;
    var o = byId(drag.id); if (!o) return;
    var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy, b = drag.orig;
    // ขยับจริงครั้งแรก → ตั้งจุด undo ครั้งเดียว (คลิกเฉยๆ ไม่ขยับ จะไม่ถูกนับว่าแก้ไข)
    if (!drag.moved && (Math.abs(dx) > 1 || Math.abs(dy) > 1)) { drag.moved = true; pu(); }
    if (drag.mode === 'move') { o.x = b.x + dx; o.y = b.y + dy; }
    else if (drag.mode === 'rotate') {
      var el = layer.querySelector('.imgw[data-img="' + o.id + '"]');
      var r = el.getBoundingClientRect();
      var ang = Math.atan2(e.clientY - (r.top + r.height / 2), e.clientX - (r.left + r.width / 2)) * 180 / Math.PI + 90;
      o.rot = e.shiftKey ? Math.round(ang / 15) * 15 : Math.round(ang);
    }
    else if (/^rs-/.test(drag.mode)) {
      var d = drag.mode.slice(3);
      var ratio = b.w / b.h;
      var nw = b.w + (/e/.test(d) ? dx : -dx);
      nw = Math.max(24, nw);
      var nh = e.shiftKey ? Math.max(24, b.h + (/s/.test(d) ? dy : -dy)) : nw / ratio;
      if (/w/.test(d)) o.x = b.x + (b.w - nw);
      if (/n/.test(d)) o.y = b.y + (b.h - nh);
      o.w = Math.round(nw); o.h = Math.round(nh);
    }
    else if (drag.mode === 'cp-pan') {
      // ลากกลางกรอบ = เลื่อนกรอบไปตามเคอร์เซอร์ (ขนาดกรอบคงเดิม) — เหมือนเลื่อนรูปข้างใน
      var cc = o.crop, bc = b.crop;
      var winW = 100 - bc.l - bc.r, winH = 100 - bc.t - bc.b;
      var nl = bc.l + dx / b.w * 100; nl = Math.max(0, Math.min(100 - winW, nl));
      var nt = bc.t + dy / b.h * 100; nt = Math.max(0, Math.min(100 - winH, nt));
      cc.l = Math.round(nl); cc.r = Math.round(100 - winW - nl);
      cc.t = Math.round(nt); cc.b = Math.round(100 - winH - nt);
    }
    else if (/^cp-/.test(drag.mode)) {
      var m = drag.mode.slice(3), c = o.crop;
      if (m === 't' || m === 'nw' || m === 'ne') c.t = clampPct(b.crop.t + dy / b.h * 100, c.b);
      if (m === 'b' || m === 'sw' || m === 'se') c.b = clampPct(b.crop.b - dy / b.h * 100, c.t);
      if (m === 'l' || m === 'nw' || m === 'sw') c.l = clampPct(b.crop.l + dx / b.w * 100, c.r);
      if (m === 'r' || m === 'ne' || m === 'se') c.r = clampPct(b.crop.r - dx / b.w * 100, c.l);
    }
    render();
  }
  function clampPct(v, opposite) { return Math.max(0, Math.min(92 - (opposite || 0), Math.round(v))); }
  function onUp() {
    if (drag && drag.mode) {
      // หมุนเสร็จ → จำองศาเดิมไว้ เผื่อกด Esc คืนค่า (ตราบที่ยังเลือกรูปนี้อยู่)
      if (drag.mode === 'rotate' && drag.moved) rotPending = { id: drag.id, prevRot: drag.orig.rot };
      // ย้าย/ย่อ/หมุน/ครอปรูป: อัปเดตในหน่วยความจำเท่านั้น — ไม่เซฟไฟล์ทุกครั้งที่ขยับ
      drag = cropTarget ? { cropMode: cropTarget } : null; render();
    }
  }

  // ---------- คีย์ลัด + คลิปบอร์ด ----------
  function onKey(e) {
    var t = e.target;
    if (t && /INPUT|TEXTAREA|SELECT/.test(t.tagName)) return;
    if (e.key === 'Escape') {
      if (ctxEl && ctxEl.style.display === 'block') { closeMenu(); e.stopPropagation(); return; }   // Esc ปิดเมนูคลิกขวาก่อน (กดครั้งเดียว)
      if (drag && drag.mode === 'rotate') { var od = byId(drag.id); if (od) od.rot = drag.orig.rot; drag = cropTarget ? { cropMode: cropTarget } : null; render(); e.stopPropagation(); return; }   // กำลังหมุนอยู่ → ยกเลิก คืนองศาเดิม
      if (rotPending && selId === rotPending.id) { var orr = byId(selId); if (orr) orr.rot = rotPending.prevRot; rotPending = null; render(); e.stopPropagation(); return; }   // หมุนเสร็จยังไม่คลิกที่อื่น → Esc คืนองศาเดิม
      if (cropTarget || selId || clipObj) { cropTarget = null; clipCut = false; clipObj = null; selId = null; drag = null; rotPending = null; render(); }
      return;
    }
    if (!selId) return;
    var o = byId(selId); if (!o) return;
    var meta = e.ctrlKey || e.metaKey;
    var k = e.key.toLowerCase();
    if (k.length === 1 && !/[a-z]/.test(k) && /^Key[A-Z]$/.test(e.code || '')) k = e.code.slice(3).toLowerCase();
    if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); e.stopPropagation(); removeImg(selId); }
    else if (meta && k === 'c') { e.preventDefault(); e.stopPropagation(); clipObj = JSON.parse(JSON.stringify(o)); clipCut = false; render(); toast('คัดลอกรูปแล้ว — Ctrl+V วาง · Esc ยกเลิก'); }
    else if (meta && k === 'x') { e.preventDefault(); e.stopPropagation(); clipObj = JSON.parse(JSON.stringify(o)); clipCut = true; render(); toast('ตัดรูปแล้ว — Ctrl+V วาง (Esc ยกเลิก)'); }
  }
  function onKeyPaste(e) {
    var meta = e.ctrlKey || e.metaKey;
    var k = e.key.toLowerCase();
    if (k.length === 1 && !/[a-z]/.test(k) && /^Key[A-Z]$/.test(e.code || '')) k = e.code.slice(3).toLowerCase();
    if (!(meta && k === 'v') || !clipObj) return;
    var t = e.target;
    if (t && /INPUT|TEXTAREA|SELECT/.test(t.tagName)) return;
    // วางรูปภายใน (สำเนา/ย้าย)
    e.preventDefault(); e.stopPropagation();
    var src = byId(clipObj.id);
    pu();
    if (clipCut && src) { src.x += 26; src.y += 26; src.z = maxZ() + 1; selId = src.id; clipCut = false; clipObj = null; }
    else {
      var copy = JSON.parse(JSON.stringify(clipObj));
      copy.id = uid(); copy.x += 26; copy.y += 26; copy.z = maxZ() + 1;
      imgs().push(copy); selId = copy.id;
    }
    persist(); render();
  }
  // วางรูปจากภายนอก (Google / โปรแกรมอื่น)
  function onPaste(e) {
    var t = e.target;
    if (t && /INPUT|TEXTAREA|SELECT/.test(t.tagName)) return;
    var items = (e.clipboardData && e.clipboardData.items) || [];
    for (var i = 0; i < items.length; i++) {
      if (/^image\//.test(items[i].type)) {
        e.preventDefault();
        addFromFile(items[i].getAsFile());
        return;
      }
    }
  }

  // ---------- init ----------
  function init() {
    gw = document.getElementById('gridwrap');
    if (!gw || !window.SG) return;
    layer = document.createElement('div');
    layer.id = 'imgLayer';
    gw.appendChild(layer);
    layer.addEventListener('mousedown', onDown, true);
    gw.addEventListener('mousedown', function (e) { if (!e.target.closest('.imgw') && selId != null) { selId = null; cropTarget = null; rotPending = null; render(); } });
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    layer.addEventListener('contextmenu', function (e) {
      var w = e.target.closest ? e.target.closest('.imgw') : null;
      if (!w) return;
      e.preventDefault(); e.stopPropagation();
      var o = byId(w.dataset.img); if (!o) return;
      selId = o.id; render();
      openMenu(o, e.clientX, e.clientY);
    }, true);
    document.addEventListener('mousedown', function (e) { if (ctxEl && !e.target.closest('.sg-ctx')) closeMenu(); });
    document.addEventListener('keydown', onKey, true);
    document.addEventListener('keydown', onKeyPaste, true);
    document.addEventListener('paste', onPaste);
    // ลากไฟล์รูปจากเครื่องมาปล่อยบนตาราง
    gw.addEventListener('dragover', function (e) { if (e.dataTransfer && [].some.call(e.dataTransfer.items || [], function (i) { return /^image\//.test(i.type); })) e.preventDefault(); });
    gw.addEventListener('drop', function (e) {
      var fs = e.dataTransfer && e.dataTransfer.files;
      if (!fs || !fs.length || !/^image\//.test(fs[0].type)) return;
      e.preventDefault(); e.stopPropagation();
      var r = gw.getBoundingClientRect();
      addFromFile(fs[0], gw.scrollLeft + e.clientX - r.left - 60, gw.scrollTop + e.clientY - r.top - 40);
    });
    // สลับหมวด → วาดรูปของหมวดใหม่
    var oReload = SG.reloadSheet;
    SG.reloadSheet = function () { var r = oReload.apply(SG, arguments); selId = null; cropTarget = null; render(); return r; };
    // undo/redo ของตาราง → วาดรูปใหม่ด้วย (รวม undo การครอป/ย้าย/หมุนรูป)
    var oUndo = SG.undo, oRedo = SG.redo;
    SG.undo = function () { var r = oUndo.apply(SG, arguments); render(); return r; };
    SG.redo = function () { var r = oRedo.apply(SG, arguments); render(); return r; };
    render();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.ImgLayer = { render: render, addImage: addImage, pickFile: pickFile, googleSearch: googleSearch, _state: function () { return { selId: selId, cropTarget: cropTarget, hasClip: !!clipObj }; } };
})();
