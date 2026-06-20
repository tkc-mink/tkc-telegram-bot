/* ============================================================
   engine.js — cipher, calc, column model, palette, storage
   No framework. Pure helpers on window.XLS
   ============================================================ */
(function () {
  // ---- Cipher maps (LOCKED per CLAUDE.md) ----
  // #1 ทุน/COGS : 0..9 = X T N S F V L C B K
  // #2 ขายส่ง   : 0..9 = O I Z M D E H Y P R
  // A = ตัวเลขซ้ำตัวก่อนหน้า (ใช้ติดกันได้ครั้งเดียว — ไม่มี AA)
  // เช่น 10050007788899000 → IOAEOAOYAPAPRAOAO
  var C1 = ['X','T','N','S','F','V','L','C','B','K'];
  var C2 = ['O','I','Z','M','D','E','H','Y','P','R'];

  function encode(numStr, map) {
    var s = String(numStr == null ? '' : numStr).replace(/[^0-9]/g, '');
    if (!s) return '';
    var out = '', prev = null, lastWasA = false;
    for (var i = 0; i < s.length; i++) {
      var ch = s[i];
      if (ch === prev && !lastWasA) { out += 'A'; lastWasA = true; }
      else { out += map[+ch]; lastWasA = false; }
      prev = ch;
    }
    return out;
  }
  function decode(code, map) {
    var inv = {}; map.forEach(function (l, d) { inv[l] = d; });
    var s = String(code || '').toUpperCase(), out = '', prev = null;
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (c === 'A') { out += (prev == null ? '' : prev); }
      else if (inv[c] != null) { out += inv[c]; prev = String(inv[c]); }
    }
    return out;
  }
  var cogs   = function (n) { return encode(n, C1); };  // ต้นทุน
  var dealer = function (n) { return encode(n, C2); };  // ขายส่ง

  function num(v) { var n = parseFloat(String(v).replace(/[^0-9.\-]/g, '')); return isNaN(n) ? 0 : n; }
  function fmt(v) { if (v === '' || v == null) return ''; var n = num(v); return n ? n.toLocaleString('en-US') : String(v); }

  // ---- Column model (A..W exactly like Excel) ----
  // type: txt | int | calc | cipher | sizegroup | flag
  // w = px width (Excel width * 6 + 6, Arial 10)
  var COLS = [
    { k:'size',      L:'ขนาด',    sub:'',     w:92,  t:'sizegroup', a:'center', ed:true,  cls:'c-size' },
    { k:'ply',       L:'ชั้น',     sub:'',     w:33,  t:'txt',  a:'center', ed:true },
    { k:'brand',     L:'ยี่ห้อ',   sub:'',     w:41,  t:'txt',  a:'center', ed:true,  cls:'c-brand' },
    { k:'model',     L:'รุ่น',     sub:'',     w:84,  t:'txt',  a:'center', ed:true,  cls:'c-model' },
    { k:'dot',       L:'D',       sub:'DOT',  w:36,  t:'txt',  a:'center', ed:true,  cls:'c-dot' },
    { k:'side',      L:'ขอบ',     sub:'สี',    w:31,  t:'txt',  a:'center', ed:true },
    { k:'cost',      L:'ทุน',     sub:'COST', w:71,  t:'int',  a:'center', ed:true,  cls:'c-cost', secret:true },
    { k:'retail',    L:'ราคา',    sub:'ตั้ง',  w:66,  t:'int',  a:'center', ed:true,  cls:'c-retail' },
    { k:'sFlag',     L:'s',       sub:'',     w:26,  t:'flag', a:'center', ed:true },
    { k:'dt',        L:'DT',      sub:'',     w:26,  t:'flag', a:'center', ed:true },
    { k:'margin',    L:'Margin',  sub:'',     w:71,  t:'calc', a:'center', ed:false, cls:'c-margin', f:'retail-cost', secret:true },
    { k:'cogs',      L:'COGS',    sub:'รหัสทุน', w:66, t:'cipher', a:'center', ed:false, cls:'c-cipher', f:'cogs:cost' },
    { k:'warranty',  L:'W',       sub:'ปกน.', w:30,  t:'txt',  a:'center', ed:true,  cls:'c-warr' },
    { k:'priceB',    L:'SUB-B',   sub:'ราคา', w:71,  t:'int',  a:'center', ed:true,  cls:'c-pB', secret:true },
    { k:'cipherB',   L:'B',       sub:'รหัส',  w:66,  t:'cipher', a:'center', ed:false, cls:'c-cipher', f:'dealer:priceB' },
    { k:'subB',      L:'+/−',     sub:'',     w:62,  t:'calc', a:'center', ed:false, cls:'c-sub', f:'priceB-cost', secret:true },
    { k:'priceA',    L:'SUB-A',   sub:'ราคา', w:71,  t:'int',  a:'center', ed:true,  cls:'c-pA', secret:true },
    { k:'cipherA',   L:'A',       sub:'รหัส',  w:66,  t:'cipher', a:'center', ed:false, cls:'c-cipher', f:'dealer:priceA' },
    { k:'subA',      L:'+/−',     sub:'',     w:62,  t:'calc', a:'center', ed:false, cls:'c-sub', f:'priceA-cost', secret:true },
    { k:'priceS',    L:'SUB-S',   sub:'ราคา', w:71,  t:'int',  a:'center', ed:true,  cls:'c-pS', secret:true },
    { k:'cipherS',   L:'S',       sub:'รหัส',  w:66,  t:'cipher', a:'center', ed:false, cls:'c-cipher', f:'dealer:priceS' },
    { k:'subS',      L:'+/−',     sub:'',     w:62,  t:'calc', a:'center', ed:false, cls:'c-sub', f:'priceS-cost', secret:true },
    { k:'note',      L:'หมายเหตุ', sub:'',    w:101, t:'txt',  a:'left',   ed:true,  cls:'c-note' }
  ];
  var COLKEY = {}; COLS.forEach(function (c, i) { c.idx = i; COLKEY[c.k] = c; });

  // compute a calc/cipher cell value from a row
  function compute(col, row) {
    if (col.t === 'cipher') {
      var parts = col.f.split(':'); // cogs:cost or dealer:priceB
      var fn = parts[0] === 'cogs' ? cogs : dealer;
      return fn(row[parts[1]]);
    }
    if (col.t === 'calc') { // a-b
      var m = col.f.split('-');
      var d = num(row[m[0]]) - num(row[m[1]]);
      return d ? String(d) : '';
    }
    return row[col.k];
  }

  // ---- Fill palette (Excel-like) ----
  var PALETTE = [
    { n:'ไม่มีสี',  c:null },
    { n:'เหลือง',  c:'FFFF00' }, { n:'เหลืองอ่อน', c:'FFFF99' }, { n:'ครีม', c:'FFFFCC' },
    { n:'ส้ม',    c:'FF9900' }, { n:'ส้มอ่อน', c:'FDE9D9' }, { n:'พีช', c:'FFCC99' },
    { n:'เขียว',  c:'92D050' }, { n:'เขียวอ่อน', c:'CCFFCC' }, { n:'มิ้นต์', c:'CCFF99' },
    { n:'ฟ้า',    c:'00B0F0' }, { n:'ฟ้าอ่อน', c:'CCFFFF' }, { n:'ฟ้าน้ำเงิน', c:'00FFFF' },
    { n:'ชมพู',   c:'FF99CC' }, { n:'ชมพูอ่อน', c:'FFCCFF' }, { n:'ม่วงอ่อน', c:'E5DFEC' },
    { n:'เทา',    c:'D8D8D8' }, { n:'เทาเข้ม', c:'BFBFBF' }, { n:'แดง', c:'FF6666' }
  ];

  // ---- Font color palette (Excel-like) ----
  var FONT_PALETTE = [
    { n:'ค่าเริ่มต้น', c:null },
    { n:'ดำ',     c:'000000' }, { n:'เทา',    c:'808080' }, { n:'ขาว',   c:'FFFFFF' },
    { n:'แดง',    c:'FF0000' }, { n:'แดงเข้ม', c:'C00000' }, { n:'ส้ม',   c:'FF6600' },
    { n:'ทอง',    c:'BF8F00' }, { n:'เขียว',  c:'008000' }, { n:'เขียวสด', c:'00B050' },
    { n:'ฟ้า',    c:'00B0F0' }, { n:'น้ำเงิน', c:'0000FF' }, { n:'ม่วง',  c:'7030A0' },
    { n:'ชมพูบานเย็น', c:'FF00FF' }, { n:'ชมพู', c:'FF33CC' }
  ];

  // ---- Storage (versions) ----
  var LS = window.localStorage;
  var K_CUR = 'xlsedit_current';
  var K_VERS = 'xlsedit_versions';
  function loadVersions() { try { return JSON.parse(LS.getItem(K_VERS) || '[]'); } catch (e) { return []; } }
  function saveVersions(v) { LS.setItem(K_VERS, JSON.stringify(v)); }
  function loadCurrent() { try { return JSON.parse(LS.getItem(K_CUR) || 'null'); } catch (e) { return null; } }
  function saveCurrent(doc) { LS.setItem(K_CUR, JSON.stringify(doc)); }
  function loadVersion(id) { try { return JSON.parse(LS.getItem('xlsedit_v_' + id) || 'null'); } catch (e) { return null; } }
  function saveVersionDoc(id, doc) { LS.setItem('xlsedit_v_' + id, JSON.stringify(doc)); }
  function deleteVersion(id) {
    LS.removeItem('xlsedit_v_' + id);
    saveVersions(loadVersions().filter(function (x) { return x.id !== id; }));
  }

  window.XLS = {
    C1: C1, C2: C2, cogs: cogs, dealer: dealer, encode: encode, decode: decode,
    num: num, fmt: fmt, COLS: COLS, COLKEY: COLKEY, compute: compute, PALETTE: PALETTE, FONT_PALETTE: FONT_PALETTE,
    store: {
      loadVersions: loadVersions, saveVersions: saveVersions,
      loadCurrent: loadCurrent, saveCurrent: saveCurrent,
      loadVersion: loadVersion, saveVersionDoc: saveVersionDoc, deleteVersion: deleteVersion
    }
  };
})();
