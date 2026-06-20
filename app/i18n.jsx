/* ============================================================
   i18n.jsx — bilingual helper + tiny shared UI primitives
   ============================================================ */

// translate helper: tr(lang, thaiString, englishString)
function tr(lang, th, en) { return lang === 'en' ? en : th; }

// big string table for chrome / nav / labels
const STR = {
  appName:      { th:'TKC Dynamic Pricelist', en:'TKC Dynamic Pricelist' },
  org:          { th:'TKC AUTO PLUS · อุดรธานี', en:'TKC AUTO PLUS · Udon Thani' },
  // nav
  nav_dashboard:{ th:'หน้าแรก', en:'Dashboard' },
  nav_viewer:   { th:'ดูราคา', en:'Pricelist' },
  nav_editor:   { th:'แก้ไขราคา', en:'Editor' },
  nav_mobile:   { th:'มุมมองมือถือ', en:'Mobile View' },
  nav_settings: { th:'ตั้งค่าระบบ', en:'Settings' },
  group_main:   { th:'การทำงาน', en:'Workspace' },
  group_admin:  { th:'ผู้ดูแลระบบ', en:'Admin' },
  // topbar
  search_ph:    { th:'ค้นหา ขนาด / ยี่ห้อ / รุ่น …', en:'Search size / brand / model …' },
  viewAs:       { th:'ดูในบทบาท', en:'View as' },
  // common
  edit:         { th:'แก้ไข', en:'Edit' },
  save:         { th:'บันทึก', en:'Save' },
  cancel:       { th:'ยกเลิก', en:'Cancel' },
  close:        { th:'ปิด', en:'Close' },
  all:          { th:'ทั้งหมด', en:'All' },
  baht:         { th:'บาท', en:'THB' },
};
function S(lang, key) { const e = STR[key]; return e ? (lang==='en'?e.en:e.th) : key; }

// --- tiny inline icon set (stroke icons, no external deps) ---
const Icon = ({ d, size=18, fill='none', stroke='currentColor', sw=1.7, style }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke}
       strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" style={style}>
    {Array.isArray(d) ? d.map((p,i)=><path key={i} d={p}/>) : <path d={d}/>}
  </svg>
);
const ICONS = {
  grid:    'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  list:    ['M8 6h13','M8 12h13','M8 18h13','M3 6h.01','M3 12h.01','M3 18h.01'],
  table:   ['M3 3h18v18H3z','M3 9h18','M3 15h18','M9 3v18','M15 3v18'],
  edit:    ['M12 20h9','M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z'],
  phone:   ['M5 2h14v20H5z','M9 18h6'],
  settings:['M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z','M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.1A1.6 1.6 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H1a2 2 0 0 1 0-4h.1A1.6 1.6 0 0 0 2.6 7a1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H7a1.6 1.6 0 0 0 1-1.5V1a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V7a1.6 1.6 0 0 0 1.5 1H23a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1Z'],
  search:  ['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z','M21 21l-4.3-4.3'],
  bell:    ['M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9','M10.3 21a1.9 1.9 0 0 0 3.4 0'],
  mic:     ['M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3Z','M19 10a7 7 0 0 1-14 0','M12 19v3'],
  chevron: 'M9 18l6-6-6-6',
  chevDown:'M6 9l6 6 6-6',
  check:   'M20 6L9 17l-5-5',
  plus:    ['M12 5v14','M5 12h14'],
  filter:  'M3 4h18l-7 8v6l-4 2v-8Z',
  share:   ['M4 12v8h16v-8','M16 6l-4-4-4 4','M12 2v14'],
  print:   ['M6 9V2h12v7','M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2','M6 14h12v8H6z'],
  download:['M12 3v12','M7 10l5 5 5-5','M5 21h14'],
  user:    ['M20 21a8 8 0 1 0-16 0','M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z'],
  shield:  ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z'],
  key:     ['M15.5 7.5a4.5 4.5 0 1 1-6.4 4.1L3 18v3h3l1-1h2l1-1v-2l1.4-1.4a4.5 4.5 0 0 0 5.1-7.7Z'],
  box:     ['M21 8l-9-5-9 5 9 5 9-5Z','M3 8v8l9 5 9-5V8','M12 13v8'],
  sync:    ['M21 2v6h-6','M3 12a9 9 0 0 1 15-6.7L21 8','M3 22v-6h6','M21 12a9 9 0 0 1-15 6.7L3 16'],
  database:['M12 8a8 4 0 1 0 0-8 8 4 0 0 0 0 8Z','M4 6v6a8 4 0 0 0 16 0V6','M4 12v6a8 4 0 0 0 16 0v-6'],
  activity:'M22 12h-4l-3 9L9 3l-3 9H2',
  tag:     ['M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8Z','M7 7h.01'],
  truck:   ['M1 3h15v13H1z','M16 8h4l3 3v5h-7','M5.5 18.5a2 2 0 1 0 0 .01','M18.5 18.5a2 2 0 1 0 0 .01'],
  globe:   ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z','M2 12h20','M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20'],
  moon:    'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z',
  logout:  ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4','M16 17l5-5-5-5','M21 12H9'],
  copy:    ['M9 9h11v11H9z','M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1'],
  clock:   ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z','M12 6v6l4 2'],
  cpu:     ['M5 5h14v14H5z','M9 9h6v6H9z','M9 1v3','M15 1v3','M9 20v3','M15 20v3','M1 9h3','M1 15h3','M20 9h3','M20 15h3'],
  warning: ['M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z','M12 9v4','M12 17h.01'],
};

Object.assign(window, { tr, STR, S, Icon, ICONS });
