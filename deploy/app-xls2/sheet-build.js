/* ============================================================
   sheet-build.js — สร้างชีตเริ่มต้น (โมเดลเซลล์จริงแบบ Excel)
   จากข้อมูล window.PICKUP01 → doc {cells, merges, colW, rowH}
   คอลัมน์ A..W ตรงกับไฟล์ Excel ต้นฉบับ
   ============================================================ */
(function () {
  function build() {
    var src = window.PICKUP01;
    var rows = src.rows;
    var colW = [92, 33, 41, 84, 36, 31, 71, 66, 26, 26, 71, 66, 30, 71, 66, 62, 71, 66, 62, 71, 66, 62, 101];
    var d = {
      name: 'ราคายาง ปิคอัพ-01',
      meta: JSON.parse(JSON.stringify(src.meta)),
      nCols: 23, nRows: 0,
      cells: {}, merges: {},
      colW: colW, rowH: [],
      adminRows: {},
      adminCols: { 6: 1, 10: 1, 13: 1, 15: 1, 16: 1, 18: 1, 19: 1, 21: 1 }
    };
    function setC(r, c, cell) { d.cells[r + ':' + c] = cell; }

    // ----- title band -----
    d.merges['0:0'] = { rs: 1, cs: 21 };
    setC(0, 0, { v: 'ราคา' + src.meta.title + ' ประจำเดือน ' + src.meta.month + ' (ชั่วคราว)', t: 'text', s: { bg: 'FFFF99', fc: '0000FF', b: 1, fs: 15, al: 'center' } });
    d.merges['0:21'] = { rs: 1, cs: 2 };
    setC(0, 21, { v: 'หน้า ' + src.meta.sheet, t: 'text', s: { fc: '0000FF', b: 1, al: 'center' } });
    d.rowH[0] = 30;
    d.merges['1:0'] = { rs: 1, cs: 23 };
    setC(1, 0, { v: src.meta.category, t: 'text', s: { fc: '0000FF', b: 1, fs: 18, al: 'center' } });
    d.rowH[1] = 28;

    var HEAD = ['ขนาด', 'ชั้น', 'ยี่ห้อ', 'รุ่น', 'D\nDOT', 'ขอบ\nสี', 'ทุน\nCOST', 'ราคา\nตั้ง', 's', 'DT', 'Margin', 'COGS\nรหัสทุน', 'W\nปกน.', 'SUB-B\nราคา', 'B\nรหัส', '+/−', 'SUB-A\nราคา', 'A\nรหัส', '+/−', 'SUB-S\nราคา', 'S\nรหัส', '+/−', 'หมายเหตุ'];
    var CIPH = { 11: 1, 14: 1, 17: 1, 20: 1 };

    var R = 2, lastRim = null, i = 0;
    while (i < rows.length) {
      var row = rows[i];
      if (row.rim !== lastRim) {
        lastRim = row.rim;
        // section row
        d.merges[R + ':0'] = { rs: 1, cs: 2 };
        setC(R, 0, { v: row.rim, t: 'text', s: { bg: 'FFC000', b: 1, al: 'center', fs: 12 } });
        d.merges[R + ':2'] = { rs: 1, cs: 4 };
        setC(R, 2, { v: row.series || '', t: 'text', s: { bg: 'FFF2CC', fc: 'C0392B', b: 1, al: 'center' } });
        d.merges[R + ':13'] = { rs: 1, cs: 9 };
        setC(R, 13, { v: 'Dealer (ราคาส่ง · รหัสลับ)', t: 'text', s: { bg: 'DDEBF7', fc: '0000FF', b: 1, al: 'center' } });
        d.rowH[R] = 20; R++;
        // header row
        for (var c = 0; c < 23; c++) {
          var hs = { bg: 'FFF2CC', b: 1, al: 'center', fs: 9 };
          if (CIPH[c]) hs.bg = 'FCE4D6';
          if (c === 6 || c === 7) hs.bg = 'FFE699';
          setC(R, c, { v: HEAD[c], t: 'text', s: hs });
        }
        d.rowH[R] = 26; R++;
      }
      // group of rows sharing size
      var g = row.gid, glen = 0, j = i;
      while (j < rows.length && rows[j].gid === g && rows[j].rim === row.rim) { glen++; j++; }
      d.merges[R + ':0'] = { rs: glen, cs: 1 };
      setC(R, 0, { v: row.size + (row.diameter ? '\n' + row.diameter : ''), t: 'text', s: { bg: 'F2F2F2', fc: '0000FF', b: 1, al: 'center' } });
      for (var k = 0; k < glen; k++) {
        var rw = rows[i + k], rr = R + k, n = rr + 1;
        setC(rr, 1, { v: rw.ply, t: 'text', s: { al: 'center' } });
        var bs = { b: 1, al: 'center' }; if (rw.brandColor) bs.fc = rw.brandColor; if (rw.fill) bs.bg = rw.fill;
        setC(rr, 2, { v: rw.brand, t: 'text', s: bs });
        setC(rr, 3, { v: rw.model, t: 'text', s: { fc: '0000FF', al: 'center' } });
        setC(rr, 4, { v: rw.dot, t: 'text', s: { fc: '008000', b: 1, al: 'center' } });
        setC(rr, 5, { v: rw.side, t: 'text', s: { al: 'center' } });
        setC(rr, 6, { v: rw.cost, t: 'num', s: { b: 1, al: 'center' } });
        setC(rr, 7, { v: rw.retail, t: 'num', s: { fc: 'C00000', b: 1, al: 'center' } });
        setC(rr, 8, { v: rw.sFlag, t: 'text', s: { al: 'center' } });
        setC(rr, 9, { v: rw.dt, t: 'text', s: { al: 'center' } });
        setC(rr, 10, { f: '=H' + n + '-G' + n, t: 'num', s: { pm: 1, cond: 'pn', fs: 9, al: 'center' } });
        setC(rr, 11, { f: '=COGS(G' + n + ')', t: 'text', s: { bg: 'FFF7EF', fc: 'B15C00', b: 1, mn: 1, al: 'center' } });
        var ws = { b: 1, al: 'center' }; if (rw.warrantyColor) ws.fc = rw.warrantyColor;
        setC(rr, 12, { v: rw.warranty, t: 'text', s: ws });
        setC(rr, 13, { v: rw.priceB, t: 'num', s: { al: 'center' } });
        setC(rr, 14, { f: '=DEALER(N' + n + ')', t: 'text', s: { bg: 'FFF7EF', fc: 'B15C00', b: 1, mn: 1, al: 'center' } });
        setC(rr, 15, { f: '=N' + n + '-G' + n, t: 'num', s: { pm: 1, fc: '2E7D32', fs: 9, al: 'center' } });
        setC(rr, 16, { v: rw.priceA, t: 'num', s: { al: 'center' } });
        setC(rr, 17, { f: '=DEALER(Q' + n + ')', t: 'text', s: { bg: 'FFF7EF', fc: 'B15C00', b: 1, mn: 1, al: 'center' } });
        setC(rr, 18, { f: '=Q' + n + '-G' + n, t: 'num', s: { pm: 1, fc: '2E7D32', fs: 9, al: 'center' } });
        setC(rr, 19, { v: rw.priceS, t: 'num', s: { al: 'center' } });
        setC(rr, 20, { f: '=DEALER(T' + n + ')', t: 'text', s: { bg: 'FFF7EF', fc: 'B15C00', b: 1, mn: 1, al: 'center' } });
        setC(rr, 21, { f: '=T' + n + '-G' + n, t: 'num', s: { pm: 1, fc: '2E7D32', fs: 9, al: 'center' } });
        setC(rr, 22, { v: rw.note, t: 'text', s: { fc: '555555', fs: 9, al: 'left' } });
        d.rowH[rr] = 19;
      }
      R += glen; i = j;
    }
    d.nRows = R;
    return d;
  }
  window.XL2Build = { fromPickup01: build };
})();
