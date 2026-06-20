/* ============================================================
   data.jsx — mock data + cipher engine for TKC Pricelist
   ============================================================ */

// --- Cipher keys (LOCKED per PRD) ---
const CIPHER1 = ['X','T','N','S','F','V','L','C','B','K']; // ทุน (cost) — Admin only
const CIPHER2 = ['O','I','Z','M','D','E','H','Y','P','R']; // ราคาส่ง (wholesale) — Sales+

// encode a number using a cipher; 'A' = repeat marker (toggles on consecutive equal digits)
function encode(num, cipher) {
  if (num == null || num === '') return '';
  const digits = String(Math.round(Number(num)));
  let out = '', prev = null, alt = false;
  for (const ch of digits) {
    if (ch === prev) alt = !alt; else alt = false;
    out += alt ? 'A' : cipher[+ch];
    prev = ch;
  }
  return out;
}
const cost2code = (n) => encode(n, CIPHER1);
const whole2code = (n) => encode(n, CIPHER2);

// thousands format
const fmt = (n) => (n == null ? '—' : Number(n).toLocaleString('en-US'));

// --- DOT color logic. Current year 2026 -> "26" black; "25" green (1y); <=24 red (2+y)
const CUR_YY = 26;
function dotColor(yy) {
  if (yy >= CUR_YY) return 'var(--text)';        // current — neutral
  if (yy === CUR_YY - 1) return 'var(--green)';   // 1 year
  return 'var(--red)';                            // 2+ years (old)
}

// ============================================================
//  Roles  — drive column-level visibility (PRD §2.2)
// ============================================================
const ROLES = {
  admin:   { id:'admin',   th:'ผู้ดูแลระบบ',        en:'Admin',         icon:'🔧', color:'var(--yellow)' },
  btire:   { id:'btire',   th:'เซลล์ยางใหญ่',       en:'B-Tire Sales',  icon:'🛞', color:'var(--blue)'   },
  dealer:  { id:'dealer',  th:'เซลล์ดูแลร้านค้า',   en:'Dealer Sales',  icon:'🏪', color:'var(--green)'  },
  counter: { id:'counter', th:'พนักงานหน้าร้าน',    en:'Counter',       icon:'🛒', color:'var(--amber)'  },
};

// column visibility per role: which data columns are shown
// columns: size, ply, brand, model, dot, cost(real+code), retail, status, dt, margin, warranty, BAS(real), BAScode, stock
const COL_PERMS = {
  admin:   { costReal:true,  costCode:true,  retail:true,  basReal:true,  basCode:true, margin:true,  crToggle:true,  edit:true  },
  btire:   { costReal:false, costCode:false, retail:true,  basReal:false, basCode:false,margin:false, crToggle:false, edit:false }, // B2C: ราคาขายเท่านั้น
  dealer:  { costReal:false, costCode:false, retail:false, basReal:false, basCode:true, margin:false, crToggle:false, edit:false }, // B2B: B/A/S code, ซ่อนราคาขาย
  counter: { costReal:false, costCode:false, retail:true,  basReal:false, basCode:true, margin:false, crToggle:true,  edit:false }, // mixed + CR
};

// ============================================================
//  Categories / Sheets
// ============================================================
const CATEGORIES = [
  { id:'car',    code:'PC',  th:'ยางเก๋ง',        en:'Passenger',  page:'1–14',  count: 642 },
  { id:'pickup', code:'LT',  th:'ยางกระบะ',       en:'Pickup / LT',page:'15–28', count: 588 },
  { id:'truck',  code:'TBR', th:'ยางบรรทุก',      en:'Truck (TBR)',page:'29–40', count: 401 },
  { id:'moto',   code:'MC',  th:'ยางมอเตอร์ไซค์', en:'Motorcycle', page:'41–48', count: 333 },
  { id:'batt',   code:'BAT', th:'แบตเตอรี่',      en:'Battery',    page:'49–55', count: 210 },
  { id:'tube',   code:'TB',  th:'ยางใน / รองขอบ', en:'Tube / Flap',page:'56–60', count: 287 },
  { id:'oil',    code:'OIL', th:'น้ำมัน / จาระบี',en:'Oil / Grease',page:'61–64',count: 168 },
];

// helper to build a product row
let _rid = 0;
function P(o) {
  _rid++;
  const retail = o.retail;
  const credit = retail + (o.cr || 0);
  return {
    id: 'r' + _rid,
    cat: o.cat,
    size: o.size, ply: o.ply || '', brand: o.brand, model: o.model,
    oem: !!o.oem,
    dot: o.dot,                  // [{yy, ww, qty}]
    edge: o.edge || '',
    cost: o.cost,                // ทุน (real)
    retail, cr: o.cr || 0, credit,
    status: o.status || '-',     // '-', '+', 'C', or discount code
    dt: o.dt || '',
    warranty: o.warranty || '',
    bas: o.bas,                  // {B,A,S}
    stock: o.stock,              // {total, pending}
    note: o.note || '',
    margin: o.cost != null ? retail - o.cost : null,
  };
}

const PRODUCTS = [
  // ---- ยางเก๋ง ----
  P({cat:'car', size:'185/65R15', brand:'Michelin', model:'Energy XM2+', dt:'HP', warranty:'5Y',
     cost:1818, retail:2150, cr:100, bas:{B:1990,A:1950,S:1920}, status:'-', oem:true,
     dot:[{yy:26,ww:'08',qty:48},{yy:26,ww:'05',qty:20}], stock:{total:68,pending:0}, edge:'ด'}),
  P({cat:'car', size:'195/55R16', brand:'Bridgestone', model:'Turanza T005', dt:'HP', warranty:'5Y',
     cost:2240, retail:2690, cr:200, bas:{B:2490,A:2440,S:2400}, status:'+',
     dot:[{yy:26,ww:'12',qty:32}], stock:{total:32,pending:8}, edge:'ด'}),
  P({cat:'car', size:'205/55R16', brand:'Goodyear', model:'Assurance TripleMax 2', dt:'HP', warranty:'4Y',
     cost:2410, retail:2890, cr:200, bas:{B:2690,A:2640,S:2590}, status:'-',
     dot:[{yy:26,ww:'03',qty:54},{yy:25,ww:'40',qty:12}], stock:{total:66,pending:0}, edge:'ด'}),
  P({cat:'car', size:'215/45R17', brand:'Continental', model:'UltraContact UC6', dt:'HP', warranty:'5Y',
     cost:2980, retail:3590, cr:300, bas:{B:3290,A:3240,S:3190}, status:'C',
     dot:[{yy:25,ww:'22',qty:16}], stock:{total:16,pending:0}, edge:'ข'}),
  P({cat:'car', size:'225/45R18', brand:'Michelin', model:'Pilot Sport 4', dt:'HP', warranty:'5Y',
     cost:4120, retail:4990, cr:300, bas:{B:4590,A:4520,S:4450}, status:'-', oem:true,
     dot:[{yy:26,ww:'06',qty:24}], stock:{total:24,pending:4}, edge:'ด'}),
  P({cat:'car', size:'235/40R19', brand:'Bridgestone', model:'Potenza Sport', dt:'RC', warranty:'4Y',
     cost:5680, retail:6790, cr:300, bas:{B:6290,A:6190,S:6090}, status:'+',
     dot:[{yy:24,ww:'18',qty:8}], stock:{total:8,pending:0}, edge:'ข', note:'ปียางเก่า เคลียร์สต็อก'}),

  // ---- ยางกระบะ ----
  P({cat:'pickup', size:'215/70R15C', ply:'8PR', brand:'Otani', model:'MK2000', dt:'AT', warranty:'3Y',
     cost:1818, retail:1950, cr:100, bas:{B:1850,A:1820,S:1790}, status:'-',
     dot:[{yy:26,ww:'08',qty:1019},{yy:26,ww:'05',qty:20}], stock:{total:1069,pending:50}, edge:'ด'}),
  P({cat:'pickup', size:'265/65R17', brand:'Maxxis', model:'AT-771 Bravo', dt:'AT', warranty:'4Y',
     cost:3450, retail:4150, cr:300, bas:{B:3890,A:3820,S:3750}, status:'-', oem:true,
     dot:[{yy:26,ww:'10',qty:88},{yy:25,ww:'44',qty:24}], stock:{total:112,pending:0}, edge:'ด'}),
  P({cat:'pickup', size:'265/70R16', brand:'BFGoodrich', model:'All-Terrain T/A KO2', dt:'AT', warranty:'5Y',
     cost:5120, retail:6290, cr:300, bas:{B:5890,A:5790,S:5690}, status:'+',
     dot:[{yy:26,ww:'02',qty:40}], stock:{total:40,pending:12}, edge:'ด'}),
  P({cat:'pickup', size:'31x10.5R15', ply:'6PR', brand:'Cooper', model:'Discoverer AT3', dt:'MT', warranty:'4Y',
     cost:4680, retail:5690, cr:300, bas:{B:5290,A:5190,S:5090}, status:'C',
     dot:[{yy:25,ww:'30',qty:18}], stock:{total:18,pending:0}, edge:'ด'}),
  P({cat:'pickup', size:'235/75R15', ply:'6PR', brand:'Dunlop', model:'Grandtrek AT5', dt:'AT', warranty:'4Y',
     cost:2980, retail:3590, cr:200, bas:{B:3390,A:3340,S:3290}, status:'-',
     dot:[{yy:26,ww:'07',qty:64}], stock:{total:64,pending:0}, edge:'ด'}),

  // ---- ยางบรรทุก ----
  P({cat:'truck', size:'1000R20', ply:'18PR', brand:'Aeolus', model:'HN08', dt:'HT', warranty:'2Y',
     cost:8900, retail:10500, cr:1000, bas:{B:9900,A:9700,S:9500}, status:'-',
     dot:[{yy:26,ww:'04',qty:120}], stock:{total:120,pending:24}, edge:'ด'}),
  P({cat:'truck', size:'11R22.5', ply:'16PR', brand:'Double Coin', model:'RR680', dt:'HT', warranty:'2Y',
     cost:9800, retail:11900, cr:1000, bas:{B:11200,A:11000,S:10800}, status:'+',
     dot:[{yy:25,ww:'38',qty:60}], stock:{total:60,pending:0}, edge:'ด'}),
  P({cat:'truck', size:'295/80R22.5', brand:'Sailun', model:'S917', dt:'MT', warranty:'2Y',
     cost:11200, retail:13500, cr:1000, bas:{B:12700,A:12500,S:12300}, status:'-',
     dot:[{yy:26,ww:'01',qty:44}], stock:{total:44,pending:8}, edge:'ด'}),

  // ---- มอเตอร์ไซค์ ----
  P({cat:'moto', size:'90/80-17', brand:'IRC', model:'NR73', dt:'HP', warranty:'1Y',
     cost:480, retail:650, cr:0, bas:{B:590,A:570,S:550}, status:'-',
     dot:[{yy:26,ww:'14',qty:210}], stock:{total:210,pending:0}, edge:'ด'}),
  P({cat:'moto', size:'120/70-17', brand:'Michelin', model:'Pilot Street 2', dt:'HP', warranty:'2Y',
     cost:1280, retail:1690, cr:100, bas:{B:1550,A:1520,S:1490}, status:'-', oem:true,
     dot:[{yy:26,ww:'09',qty:96}], stock:{total:96,pending:0}, edge:'ด'}),

  // ---- แบตเตอรี่ ----
  P({cat:'batt', size:'DIN65 12V', brand:'GS', model:'LN3 MF', dt:'', warranty:'18M',
     cost:2680, retail:3290, cr:200, bas:{B:3050,A:3000,S:2950}, status:'-', note:'คืนหม้อเก่า -200',
     dot:[{yy:26,ww:'11',qty:54}], stock:{total:54,pending:0}, edge:''}),
  P({cat:'batt', size:'NS60 12V 45Ah', brand:'FB', model:'Premium Gold', dt:'', warranty:'24M',
     cost:1980, retail:2490, cr:200, bas:{B:2290,A:2240,S:2190}, status:'+', note:'คืนหม้อเก่า -150',
     dot:[{yy:26,ww:'08',qty:80}], stock:{total:80,pending:10}, edge:''}),

  // ---- ยางใน / รองขอบ ----
  P({cat:'tube', size:'750-16 TR15', brand:'TKC', model:'Heavy Tube', dt:'', warranty:'',
     cost:180, retail:260, cr:0, bas:{B:220,A:210,S:200}, status:'-',
     dot:[{yy:26,ww:'13',qty:540}], stock:{total:540,pending:0}, edge:''}),

  // ---- น้ำมัน ----
  P({cat:'oil', size:'5W-30 4L', brand:'PTT', model:'Performa Synthetic', dt:'', warranty:'',
     cost:680, retail:890, cr:0, bas:{B:790,A:770,S:750}, status:'-',
     dot:[{yy:26,ww:'05',qty:144}], stock:{total:144,pending:0}, edge:''}),
];

// ============================================================
//  Bundles (Mix by Rim / Standard) — for quote demo
// ============================================================
const BUNDLES = [
  { id:'b1', name:'ชุดยางเก๋ง 4 เส้น + ตั้งศูนย์', items:['205/55R16 × 4','ตั้งศูนย์ถ่วงล้อ','เติมลม N2'],
    retail: 11560, sales: 10760 },
  { id:'b2', name:'ชุดกระบะ 4 เส้น + ยกสูง', items:['265/65R17 × 4','ค่าใส่','สลับยาง 1 ครั้งฟรี'],
    retail: 16600, sales: 15280 },
];

// ============================================================
//  Recent activity / notifications for dashboard
// ============================================================
const ACTIVITY = [
  { icon:'💰', th:'แก้ราคา 215/70R15C OT MK2000 → 1,950', en:'Price edit 215/70R15C OT MK2000 → 1,950', time:'2 นาที', user:'ชิบะน้อย', sev:'info' },
  { icon:'🔄', th:'AIO sync สำเร็จ · 2,629 รายการ', en:'AIO sync OK · 2,629 items', time:'14 นาที', user:'system', sev:'green' },
  { icon:'📅', th:'ตั้งเวลาปรับราคา ยางบรรทุก +3% (พรุ่งนี้ 08:00)', en:'Scheduled +3% Truck (tmr 08:00)', time:'1 ชม.', user:'ชิบะน้อย', sev:'amber' },
  { icon:'🔒', th:'อนุมัติอุปกรณ์ใหม่ Samsung S24 (เซลล์ B)', en:'Approved device Samsung S24', time:'2 ชม.', user:'ชิบะน้อย', sev:'blue' },
  { icon:'⚠️', th:'Sync queue ค้าง 1 รายการ · กำลัง retry', en:'Sync queue 1 pending · retrying', time:'3 ชม.', user:'system', sev:'amber' },
];

// expose globally
Object.assign(window, {
  CIPHER1, CIPHER2, cost2code, whole2code, fmt, dotColor, CUR_YY,
  ROLES, COL_PERMS, CATEGORIES, PRODUCTS, BUNDLES, ACTIVITY,
});
