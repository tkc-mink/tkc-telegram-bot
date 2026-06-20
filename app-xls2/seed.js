/* ============================================================
   seed.js — สร้างชีตเริ่มต้นจาก PICKUP01 (ผัง + สูตร + สี)
   คอลัมน์: A=ขนาด B=ชั้น C=ยี่ห้อ D=รุ่น E=DOT F=ขอบสี G=ทุน H=ราคาตั้ง
   I=s J=DT K=Margin L=COGS M=W N=SUB-B O=รหัสB P=+/- Q=SUB-A R=รหัสA
   S=+/- T=SUB-S U=รหัสS V=+/- W=หมายเหตุ
   ============================================================ */
(function () {
  var X = window.XL2;
  var NC = 23;
  var COLW = [92, 33, 41, 84, 40, 31, 71, 66, 26, 28, 71, 66, 30, 71, 66, 62, 71, 66, 62, 71, 66, 62, 101];
  var HEADS = ['ขนาด', 'ชั้น', 'ยี่ห้อ', 'รุ่น', 'D\nDOT', 'ขอบ\nสี', 'ทุน\nCOST', 'ราคา\nตั้ง', 's', 'DT', 'Margin', 'COGS\nรหัสทุน', 'W\nปกน.', 'SUB-B\nราคา', 'B\nรหัส', '+/−', 'SUB-A\nราคา', 'A\nรหัส', '+/−', 'SUB-S\nราคา', 'S\nรหัส', '+/−', 'หมายเหตุ'];
  // คอลัมน์เฉพาะแอดมิน (ทุน, Margin, SUB-B/A/S, ส่วนต่าง)
  var ADMIN_COLS = { 6: 1, 10: 1, 13: 1, 15: 1, 16: 1, 18: 1, 19: 1, 21: 1 };

  function buildSheet() {
    var src = window.PICKUP01, rows = src.rows;
    // นับแถว: title + cat + (sect+head)ต่อขอบ + data
    var sh = X.newSheet(0, NC);
    sh.colW = COLW.slice();
    sh.meta = { name: 'ราคายาง ปิคอัพ-01', title: src.meta.title, month: src.meta.month, category: src.meta.category, sheet: src.meta.sheet };
    sh.adminCols = JSON.parse(JSON.stringify(ADMIN_COLS));
    sh.secretCols = JSON.parse(JSON.stringify(ADMIN_COLS));

    var r = 0;
    function addRow(kind, h, gid) {
      sh.rowH.push(h); sh.rowKind.push(kind); sh.rowGid.push(gid != null ? gid : null); sh.nR++;
      return sh.nR - 1;
    }
    function set(r, c, v, s, f, t) {
      var cell = X.ensure(sh, r, c);
      cell.v = v == null ? '' : String(v);
      if (f) cell.f = f;
      if (t) cell.t = t;
      if (s) cell.s = s;
      return cell;
    }

    // ---- แถว 1: title ----
    r = addRow('title', 34);
    set(r, 0, 'ราคา' + src.meta.title + ' ประจำเดือน ' + src.meta.month + ' (ชั่วคราว)', { bg: 'FFFF99', fc: '0000FF', b: 1, fs: 15, al: 'center' }, null, 'text');
    set(r, 21, 'หน้า ' + src.meta.sheet, { fc: '0000FF', b: 1, fs: 11, al: 'center' }, null, 'text');
    X.addMerge(sh, r, 0, 1, 21);
    X.addMerge(sh, r, 21, 1, 2);
    // ---- แถว 2: หมวด ----
    r = addRow('cat', 30);
    set(r, 0, src.meta.category, { fc: '0000FF', b: 1, fs: 18, al: 'center' }, null, 'text');
    X.addMerge(sh, r, 0, 1, NC);

    // ---- sections ----
    var lastRim = null;
    rows.forEach(function (row) {
      if (row.rim !== lastRim) {
        lastRim = row.rim;
        // section header
        r = addRow('sect', 24);
        set(r, 0, row.rim, { bg: 'FFC000', b: 1, fs: 13, al: 'center' }, null, 'text');
        X.addMerge(sh, r, 0, 1, 2);
        set(r, 2, row.series || '', { bg: 'FFF2CC', fc: 'C0392B', b: 1, al: 'center' }, null, 'text');
        X.addMerge(sh, r, 2, 1, 4);
        set(r, 12, 'Dealer (ราคาส่ง · รหัสลับ)', { bg: 'DDEBF7', fc: '0000FF', b: 1, al: 'center' }, null, 'text');
        X.addMerge(sh, r, 12, 1, 11);
        // column header
        r = addRow('head', 32);
        for (var c = 0; c < NC; c++) {
          var hbg = 'FFF2CC';
          if (c === 6 || c === 7) hbg = 'FFE699';
          if (c === 11 || c === 14 || c === 17 || c === 20) hbg = 'FCE4D6';
          set(r, c, HEADS[c], { bg: hbg, b: 1, fs: 10, al: 'center' }, null, 'text');
        }
      }
      // data row
      r = addRow('data', 24, row.gid);
      var n = r + 1; // เลขแถว excel
      var szTxt = row.size + (row.diameter ? '\n' + row.diameter : '');
      set(r, 0, szTxt, { bg: 'F2F2F2', fc: '0000FF', b: 1, fs: 11, al: 'center' }, null, 'text');
      set(r, 1, row.ply, { al: 'center' });
      set(r, 2, row.brand, { fc: row.brandColor || null, bg: row.fill || null, b: 1, al: 'center' }, null, 'text');
      set(r, 3, row.model, { fc: '0000FF', b: 1, al: 'center' }, null, 'text');
      set(r, 4, row.dot, { fc: '008000', b: 1, al: 'center' });
      set(r, 5, row.side, { al: 'center' }, null, 'text');
      set(r, 6, row.cost, { b: 1, al: 'center' }, null, 'num');
      set(r, 7, row.retail, { fc: 'C00000', b: 1, al: 'center' }, null, 'num');
      set(r, 8, row.sFlag, { al: 'center' }, null, 'text');
      set(r, 9, row.dt, { al: 'center' }, null, 'text');
      set(r, 10, '', { al: 'center', fc: '666666' }, '=H' + n + '-G' + n, 'num');
      set(r, 11, '', { bg: 'FFF7EF', fc: 'B15C00', b: 1, al: 'center' }, '=COGS(G' + n + ')', 'text');
      set(r, 12, row.warranty, { fc: row.warrantyColor || null, b: 1, al: 'center' }, null, 'text');
      set(r, 13, row.priceB, { al: 'center' }, null, 'num');
      set(r, 14, '', { bg: 'FFF7EF', fc: 'B15C00', b: 1, al: 'center' }, '=DEALER(N' + n + ')', 'text');
      set(r, 15, '', { al: 'center', fc: '2E7D32', fs: 9 }, '=N' + n + '-G' + n, 'num');
      set(r, 16, row.priceA, { al: 'center' }, null, 'num');
      set(r, 17, '', { bg: 'FFF7EF', fc: 'B15C00', b: 1, al: 'center' }, '=DEALER(Q' + n + ')', 'text');
      set(r, 18, '', { al: 'center', fc: '2E7D32', fs: 9 }, '=Q' + n + '-G' + n, 'num');
      set(r, 19, row.priceS, { al: 'center' }, null, 'num');
      set(r, 20, '', { bg: 'FFF7EF', fc: 'B15C00', b: 1, al: 'center' }, '=DEALER(T' + n + ')', 'text');
      set(r, 21, '', { al: 'center', fc: '2E7D32', fs: 9 }, '=T' + n + '-G' + n, 'num');
      set(r, 22, row.note, { al: 'left', fc: '555555', fs: 9 }, null, 'text');
    });

    X.rebuildSizeMerges(sh);
    return sh;
  }

  // ---- mock DB (รอเชื่อม server จริง) — คีย์ = รุ่น ----
  function buildDB() {
    var db = {};
    (window.PICKUP01.rows || []).forEach(function (row) {
      if (row.model && !db[row.model]) {
        db[row.model] = { dot: row.dot, cost: row.cost, retail: row.retail, size: row.size, brand: row.brand };
      }
    });
    window.TIRE_DB = db;
  }
  buildDB();

  window.XL2_SEED = { buildSheet: buildSheet, ADMIN_COLS: ADMIN_COLS, HEADS: HEADS };
})();
