/* ============================================================
   border-overlay.js — เส้นขอบแบบ Excel ด้วย SVG overlay (v2)
   วาดเส้นขอบที่ผู้ใช้ตีไว้ (cell.s.bd) เป็นเส้นเวกเตอร์คมชัด
   ทับบนตาราง แทนการใช้ border-collapse ของ <td> โดยตรง
   เหตุผล:
     • border-collapse ทำให้เส้นสีชนกับเส้นตารางสีเทา (ความหนาเท่ากัน → เทาชนะบางเบราว์เซอร์)
     • เส้นหนา (thick) ของ td เดียวถูกวาดเยื้องไปข้างเดียว ดูไม่ตรงกลางเส้นแบ่ง
     • เส้นประ/จุด ของช่องติดกันไม่ต่อเนื่องกัน
     • ขอบเซลล์ที่ผสาน (merge) ถูกตัดขาด
   SVG overlay วาดทุกเส้นบนพิกัดขอบเซลล์จริง → คมชัด ต่อเนื่อง ตรงแบบ Excel
   depends: ถูกเรียกจาก sheet-grid.js render() · ใช้ doc.cells[r:c].s.bd
   exposes window.BorderOverlay
   ============================================================ */
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var last = null;   // { rootEl, doc, zoom } สำหรับวาดซ้ำตอน print/resize

  // แปลงค่าที่เก็บไว้ "w|style|color" หรือเลข 1/2 → อ็อบเจกต์
  function parseBd(v) {
    if (v == null) return null;
    if (typeof v === 'number' || /^[\d.]+$/.test(String(v))) {
      return { w: (parseFloat(v) || 1), style: 'solid', color: '000000' };
    }
    var p = String(v).split('|');
    return { w: (parseFloat(p[0]) || 1), style: (p[1] || 'solid'), color: (p[2] || '000000') };
  }

  // ลายเส้น → stroke-dasharray (สเกลตามความหนา ให้สัดส่วนสวยทุกขนาด)
  function dashArr(style, sw) {
    if (style === 'dashed') return (sw * 3.2).toFixed(1) + ' ' + (sw * 2).toFixed(1);
    if (style === 'dotted') return sw.toFixed(1) + ' ' + (sw * 1.7).toFixed(1);
    return null;
  }

  // โหมดมืด: ถ้าสีเส้นเข้มจนจมพื้นมืด → ดันให้สว่างขึ้นเฉพาะตอนแสดงผล (ไม่แก้ข้อมูล)
  function displayColor(hex, dark) {
    if (!dark) return '#' + hex;
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var r = parseInt(h.substr(0, 2), 16), g = parseInt(h.substr(2, 2), 16), b = parseInt(h.substr(4, 2), 16);
    if (isNaN(r) || isNaN(g) || isNaN(b)) return '#' + hex;
    var lum = 0.299 * r + 0.587 * g + 0.114 * b;
    if (lum >= 120) return '#' + hex;                         // สว่างพออยู่แล้ว
    function f(c) { var v = Math.round(c + (255 - c) * 0.6).toString(16); return v.length < 2 ? '0' + v : v; }
    return '#' + f(r) + f(g) + f(b);
  }

  function seg(out, xa, ya, xb, yb, color, sw, dash) {
    out.push('<line x1="' + xa + '" y1="' + ya + '" x2="' + xb + '" y2="' + yb +
      '" stroke="' + color + '" stroke-width="' + sw + '"' +
      (dash ? ' stroke-dasharray="' + dash + '"' : '') +
      ' stroke-linecap="butt" />');
  }
  // จัดเส้นให้คมแบบ Excel: เส้นความหนาคี่ (1px) ต้องอยู่บนครึ่งพิกเซล (x+0.5) ให้เต็มพอดี 1 พิกเซล
  // (ถ้าวางบนเลขเต็ม เส้นจะคร่อม 2 พิกเซล แล้วถูก anti-alias → ดูหนา/ซ้อนกว่าเส้นตารางปกติ)
  function snap(coord, sw) { return (sw % 2) ? (Math.round(coord) + 0.5) : Math.round(coord); }

  function bdKey(horiz, fixed, a, b) { return (horiz ? 'h' : 'v') + ':' + fixed + ':' + Math.min(a, b) + ':' + Math.max(a, b); }
  // เก็บขอบลง map · ถ้าตำแหน่งเดียวกัน (เหลื่อม ±1px) ซ้ำ → นับเป็นเส้นเดียว เก็บเส้นที่หนาที่สุดไว้ (ใช้สไตล์+สีของเส้นที่ชนะ)
  function addEdge(map, x0, y0, x1, y1, v) {
    var o = parseBd(v); if (!o) return;
    var horiz = (y0 === y1);
    var fixed = horiz ? y0 : x0;
    var a = horiz ? x0 : y0, b = horiz ? x1 : y1;
    var keys = [bdKey(horiz, fixed, a, b), bdKey(horiz, fixed - 1, a, b), bdKey(horiz, fixed + 1, a, b)];
    for (var i = 0; i < keys.length; i++) {
      var ex = map[keys[i]];
      if (ex) { if (o.w > ex.o.w) { ex.o = o; ex.x0 = x0; ex.y0 = y0; ex.x1 = x1; ex.y1 = y1; } return; }
    }
    map[keys[0]] = { x0: x0, y0: y0, x1: x1, y1: y1, o: o, horiz: horiz };
  }
  // วาดขอบหนึ่งเส้นจาก record (เดี่ยว · ประ/จุด · หรือ double = สองเส้นขนาน)
  function drawEdge(out, rec, zoom, dark) {
    var o = rec.o, col = displayColor(o.color, dark);
    var sw = o.w * Math.max(1, zoom); sw = sw >= 1 ? Math.round(sw) : 0.5;   // รองรับเส้นบางพิเศษ (0.5px) ถึงหนาพิเศษ
    if (o.style === 'double') {
      var g = Math.max(1, Math.round(zoom));                     // ระยะห่างสองเส้น
      if (rec.horiz) { var yt = snap(rec.y0 - g, 1), yb2 = snap(rec.y0 + g, 1); seg(out, rec.x0, yt, rec.x1, yt, col, 1, null); seg(out, rec.x0, yb2, rec.x1, yb2, col, 1, null); }
      else { var xl = snap(rec.x0 - g, 1), xr = snap(rec.x0 + g, 1); seg(out, xl, rec.y0, xl, rec.y1, col, 1, null); seg(out, xr, rec.y0, xr, rec.y1, col, 1, null); }
      return;
    }
    if (rec.horiz) { var y = snap(rec.y0, sw); seg(out, rec.x0, y, rec.x1, y, col, sw, dashArr(o.style, sw)); }
    else { var x = snap(rec.x0, sw); seg(out, x, rec.y0, x, rec.y1, col, sw, dashArr(o.style, sw)); }
  }

  function draw(rootEl, doc, view) {
    if (!rootEl || !doc) return;
    var zoom = (view && view.zoom) || 1;
    last = { rootEl: rootEl, doc: doc, zoom: zoom };
    var dark = !!(document.body && document.body.classList.contains('dark'));

    var svg = rootEl.querySelector('#bdSvg');
    if (!svg) {
      svg = document.createElementNS(NS, 'svg');
      svg.setAttribute('id', 'bdSvg');
      svg.setAttribute('shape-rendering', 'geometricPrecision');
      svg.setAttribute('aria-hidden', 'true');
      rootEl.appendChild(svg);
    } else if (svg.parentNode !== rootEl) {
      rootEl.appendChild(svg);   // render() เคลียร์ innerHTML — ผูกกลับเข้าไปใหม่
    }

    var W = rootEl.scrollWidth || rootEl.offsetWidth || 0;
    var H = rootEl.scrollHeight || rootEl.offsetHeight || 0;
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

    var gr = rootEl.getBoundingClientRect();
    var out = [];
    var emap = {};
    var cells = rootEl.querySelectorAll('td.sg-c');
    for (var i = 0; i < cells.length; i++) {
      var td = cells[i];
      var r = +td.getAttribute('data-r'), c = +td.getAttribute('data-c');
      var cell = doc.cells[r + ':' + c];
      if (!cell || !cell.s || !cell.s.bd) continue;
      var bd = cell.s.bd;
      var rect = td.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;       // ช่องที่ถูกซ่อน/ผสานปิดอยู่
      // ปัดเป็นจำนวนเต็มเพื่อเส้นคมชัด (snap ไปขอบพิกเซล)
      var x0 = Math.round(rect.left - gr.left), y0 = Math.round(rect.top - gr.top);
      var x1 = Math.round(rect.right - gr.left), y1 = Math.round(rect.bottom - gr.top);
      if (bd.t) addEdge(emap, x0, y0, x1, y0, bd.t);
      if (bd.b) addEdge(emap, x0, y1, x1, y1, bd.b);
      if (bd.l) addEdge(emap, x0, y0, x0, y1, bd.l);
      if (bd.r) addEdge(emap, x1, y0, x1, y1, bd.r);
    }
    Object.keys(emap).forEach(function (k) { drawEdge(out, emap[k], zoom, dark); });
    svg.innerHTML = out.join('');
  }

  function redraw() { if (last) draw(last.rootEl, last.doc, { zoom: last.zoom }); }

  // วาดซ้ำตอนเปลี่ยนขนาดหน้าต่าง และก่อน/หลังพิมพ์ (พิกัดอาจขยับ)
  var rt;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(redraw, 80); });
  window.addEventListener('beforeprint', redraw);
  window.addEventListener('afterprint', redraw);

  window.BorderOverlay = { draw: draw, redraw: redraw };
})();
