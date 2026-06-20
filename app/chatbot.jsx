/* ============================================================
   chatbot.jsx — "น้องพอร์ช" AI assistant (robot FAB, bottom-right)
   ถาม-ตอบข้อมูลในระบบจริง · เคารพสิทธิ์ตาม role
   ============================================================ */

// --- robot avatar (inline SVG, brand yellow) ---
const RobotFace = ({ size=24, color='var(--on-yellow)' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4.5" y="7.5" width="15" height="11" rx="3.2"/>
    <path d="M12 7.5V4M12 4a1.4 1.4 0 1 0 0-.01"/>
    <circle cx="9" cy="12.5" r="1.25" fill={color} stroke="none"/>
    <circle cx="15" cy="12.5" r="1.25" fill={color} stroke="none"/>
    <path d="M9.5 15.5h5"/>
    <path d="M4.5 11.5H3M21 11.5h-1.5"/>
  </svg>
);

// ============================================================
//  Tiny "NLU" — answer questions from PRODUCTS, role-aware
// ============================================================
function botAnswer(text, role, lang) {
  const perm = COL_PERMS[role];
  const q = text.toLowerCase().trim();
  const T = (th,en)=>tr(lang,th,en);
  const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g,'');
  const nq = norm(q);

  // helper: find products by loose match
  const findRows = () => PRODUCTS.filter(r => {
    const hay = norm(r.size+r.brand+r.model);
    // match if query contains a token that's a subsequence of product
    const toks = q.split(/[\s,]+/).map(norm).filter(t=>t.length>=2);
    return toks.some(t => { let i=0; for(const c of hay){ if(i<t.length&&c===t[i])i++; } return i===t.length && t.length>=3; });
  });

  // intent: greeting
  if (/^(hi|hello|สวัสดี|หวัดดี|ดี|hey)/.test(q))
    return { text: T('สวัสดีครับ! ผมน้องพอร์ช 🤖 ถามราคา สต็อก หรือ DOT ของยางรุ่นไหนได้เลยครับ','Hi! I\u2019m Porsche 🤖 Ask me about any tyre\u2019s price, stock, or DOT.'), rows:[] };

  // intent: help / what can you do
  if (/(ทำอะไร|ช่วยอะไร|help|คำสั่ง|what can)/.test(q))
    return { text: T('ผมช่วยได้เช่น:\n• "ราคา 215/70R15"\n• "สต็อก michelin"\n• "ยาง DOT เก่า"\n• "ยางเก๋งทั้งหมด"\n• "ยางใกล้หมด"','I can help with:\n• "price 215/70R15"\n• "stock michelin"\n• "old DOT tyres"\n• "all passenger tyres"\n• "low stock"'), rows:[] };

  // intent: cipher question
  if (/(รหัส|cipher|ลับ|encode)/.test(q))
    return { text: perm.costCode||perm.basCode
      ? T('รหัสลับเปลี่ยนตัวเลขเป็นตัวอักษรครับ เช่นทุน 1818 → TBTB (ดูตารางได้ที่ ตั้งค่า › รหัสลับ)','Cipher maps digits to letters, e.g. cost 1818 → TBTB. See Settings › Cipher.')
      : T('คุณยังไม่มีสิทธิ์ดูข้อมูลรหัสลับครับ','You don\u2019t have access to cipher data.'), rows:[] };

  // intent: old DOT
  if (/(dot.*เก่า|เก่า.*dot|ยางเก่า|old dot|old tyre|ค้างสต็อก)/.test(q)) {
    const rows = PRODUCTS.filter(r => Math.min(...r.dot.map(d=>d.yy)) <= CUR_YY-2);
    return { text: T(`เจอยาง DOT เก่า (≥2 ปี) ${rows.length} รายการ ควรเร่งระบายครับ 🔴`,`Found ${rows.length} tyres with old DOT (≥2yr) — clear these soon 🔴`), rows };
  }

  // intent: low stock
  if (/(ใกล้หมด|สต็อกน้อย|low stock|เหลือน้อย|ต้องเบิก|restock)/.test(q)) {
    const rows = PRODUCTS.filter(r => (r.stock.total-r.stock.pending) < 30 || r.status==='+');
    return { text: T(`มี ${rows.length} รายการที่สต็อกน้อย/ต้องเบิกครับ ⚠️`,`${rows.length} items are low or need restock ⚠️`), rows };
  }

  // intent: category listing (match Thai/English name in raw query, guard empty)
  for (const c of CATEGORIES) {
    const th = c.th.toLowerCase(), en = c.en.toLowerCase(), code = c.code.toLowerCase();
    if ((th && q.includes(th)) || (en && q.includes(en)) || (code.length>1 && q.includes(code))) {
      const rows = PRODUCTS.filter(r=>r.cat===c.id);
      return { text: T(`${tr(lang,c.th,c.en)} มี ${c.count} รายการ (โชว์ตัวอย่าง ${rows.length})`,`${tr(lang,c.th,c.en)}: ${c.count} items (showing ${rows.length})`), rows };
    }
  }

  // intent: clearance
  if (/(clearance|เคลียร์|ลดล้าง|ตัว c)/.test(q)) {
    const rows = PRODUCTS.filter(r=>r.status==='C');
    return { text: T(`รายการ Clearance ${rows.length} รายการครับ`,`${rows.length} clearance items`), rows };
  }

  // default: product search
  const rows = findRows();
  if (rows.length) {
    const head = rows.length===1 ? T('เจอ 1 รายการครับ 👇','Found 1 item 👇') : T(`เจอ ${rows.length} รายการครับ 👇`,`Found ${rows.length} items 👇`);
    return { text: head, rows: rows.slice(0,5) };
  }

  return { text: T('ขอโทษครับ ไม่เจอข้อมูลที่ตรง ลองพิมพ์ขนาดยาง ยี่ห้อ หรือพิมพ์ "ช่วยอะไรได้บ้าง"','Sorry, no match. Try a tyre size, brand, or type "help".'), rows:[] };
}

// --- message bubble that can embed product result rows ---
function BotRows({ role, rows, lang }) {
  const perm = COL_PERMS[role];
  if (!rows.length) return null;
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:6, marginTop:8 }}>
      {rows.map(r=>{
        const avail = r.stock.total - r.stock.pending;
        const oldest = Math.min(...r.dot.map(d=>d.yy));
        return (
          <div key={r.id} style={{ background:'var(--surface-1)', border:'1px solid var(--border-soft)', borderRadius:9, padding:'9px 11px' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', gap:8 }}>
              <span style={{ minWidth:0 }}>
                {r.oem && <span style={{color:'var(--yellow)', fontSize:11, marginRight:3}}>★</span>}
                <span className="mono" style={{ fontWeight:700, fontSize:12.5 }}>{r.size}</span>
                <span className="faint" style={{ fontSize:11.5, marginLeft:5 }}>{r.brand}</span>
              </span>
              {perm.retail
                ? <span className="mono" style={{ fontWeight:700, color:'var(--yellow)', fontSize:13, whiteSpace:'nowrap' }}>{fmt(r.retail)}</span>
                : perm.basCode && <span className="mono" style={{ fontWeight:600, color:'var(--blue)', fontSize:11, letterSpacing:'0.05em', whiteSpace:'nowrap' }}>{whole2code(r.bas.A)}</span>}
            </div>
            <div style={{ display:'flex', gap:9, marginTop:6, fontSize:10.5 }}>
              <span style={{ color: avail<30?'var(--amber)':'var(--green)' }}>● {tr(lang,'คงเหลือ','stock')} {fmt(avail)}</span>
              <span className="mono" style={{ color: dotColor(oldest) }}>DOT {[...new Set(r.dot.map(d=>d.yy))].join(',')}</span>
              {perm.costCode && <span className="mono" style={{ color:'var(--yellow)', letterSpacing:'0.06em' }}>{tr(lang,'ทุน','cost')} {cost2code(r.cost)}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Chatbot({ lang, role }) {
  const [open, setOpen] = React.useState(false);
  const [input, setInput] = React.useState('');
  const [typing, setTyping] = React.useState(false);
  const [msgs, setMsgs] = React.useState(()=>[
    { from:'bot', text: tr(lang,'สวัสดีครับ! ผมน้องพอร์ช 🤖 ผู้ช่วยข้อมูลราคา ถามอะไรก็ได้เลยครับ','Hi! I\u2019m Porsche 🤖 your pricelist assistant. Ask me anything.'), rows:[] }
  ]);
  const scrollRef = React.useRef(null);
  const r = ROLES[role];

  React.useEffect(()=>{ if(scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [msgs, typing, open]);

  const suggestions = lang==='en'
    ? ['price 215/70R15','low stock','old DOT tyres','passenger tyres']
    : ['ราคา 215/70R15','ยางใกล้หมด','ยาง DOT เก่า','ยางเก๋งทั้งหมด'];

  const send = (txt) => {
    const text = (txt ?? input).trim();
    if (!text) return;
    setMsgs(m=>[...m, { from:'user', text }]);
    setInput('');
    setTyping(true);
    setTimeout(()=>{
      const ans = botAnswer(text, role, lang);
      setTyping(false);
      setMsgs(m=>[...m, { from:'bot', text:ans.text, rows:ans.rows }]);
    }, 520);
  };

  return (
    <>
      {/* ---- Floating robot button ---- */}
      <button onClick={()=>setOpen(o=>!o)} aria-label="AI assistant" style={{
        position:'fixed', right:24, bottom:24, zIndex:80, width:58, height:58, borderRadius:'50%',
        background:'var(--yellow)', border:'none', cursor:'pointer', display:'grid', placeItems:'center',
        boxShadow:'0 8px 28px -6px rgba(0,0,0,.5), 0 0 0 4px var(--yellow-ghost)',
        transition:'transform .16s', transform: open?'scale(0.92)':'scale(1)',
      }}
      onMouseEnter={e=>{ if(!open) e.currentTarget.style.transform='scale(1.06)'; }}
      onMouseLeave={e=>{ e.currentTarget.style.transform= open?'scale(0.92)':'scale(1)'; }}>
        {open ? <Icon d="M6 6l12 12M18 6L6 18" size={22} stroke="var(--on-yellow)"/> : <RobotFace size={28} />}
        {!open && <span style={{ position:'absolute', top:2, right:2, width:13, height:13, borderRadius:99, background:'var(--green)', border:'2.5px solid var(--yellow)' }} />}
      </button>

      {/* ---- Chat panel ---- */}
      {open && (
        <div className="pop-in" style={{
          position:'fixed', right:24, bottom:94, zIndex:80, width:372, maxWidth:'calc(100vw - 32px)',
          height:560, maxHeight:'calc(100vh - 130px)', display:'flex', flexDirection:'column',
          background:'var(--surface-2)', border:'1px solid var(--border)', borderRadius:'var(--r-xl)',
          boxShadow:'var(--shadow-3)', overflow:'hidden',
        }}>
          {/* header */}
          <div style={{ padding:'14px 16px', background:'var(--surface-1)', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', gap:11 }}>
            <div style={{ width:38, height:38, borderRadius:11, background:'var(--yellow)', display:'grid', placeItems:'center', flexShrink:0 }}>
              <RobotFace size={23}/>
            </div>
            <div style={{ flex:1, lineHeight:1.25 }}>
              <div style={{ fontWeight:700, fontSize:14 }}>{tr(lang,'น้องพอร์ช','Porsche AI')}</div>
              <div style={{ fontSize:10.5, color:'var(--green)', display:'flex', alignItems:'center', gap:5 }}>
                <span style={{ width:6, height:6, borderRadius:99, background:'var(--green)' }}/>
                {tr(lang,'ผู้ช่วยข้อมูลราคา · ออนไลน์','Pricelist assistant · online')}
              </div>
            </div>
            <span className="chip" style={{ padding:'2px 8px', fontSize:10 }}>{r.icon} {tr(lang,r.th,r.en)}</span>
          </div>

          {/* messages */}
          <div ref={scrollRef} style={{ flex:1, overflowY:'auto', padding:'14px 14px', display:'flex', flexDirection:'column', gap:11 }}>
            {msgs.map((m,i)=>(
              <div key={i} style={{ display:'flex', justifyContent: m.from==='user'?'flex-end':'flex-start' }}>
                <div style={{ maxWidth:'86%' }}>
                  <div style={{
                    padding:'9px 13px', borderRadius: m.from==='user'?'14px 14px 4px 14px':'14px 14px 14px 4px',
                    background: m.from==='user'?'var(--yellow)':'var(--surface-3)',
                    color: m.from==='user'?'var(--on-yellow)':'var(--text)',
                    fontSize:13, lineHeight:1.5, whiteSpace:'pre-line', fontWeight: m.from==='user'?500:400,
                  }}>{m.text}</div>
                  {m.from==='bot' && m.rows && <BotRows role={role} rows={m.rows} lang={lang} />}
                </div>
              </div>
            ))}
            {typing && (
              <div style={{ display:'flex', gap:4, padding:'10px 14px', background:'var(--surface-3)', borderRadius:'14px 14px 14px 4px', width:'fit-content' }}>
                {[0,1,2].map(i=><span key={i} style={{ width:6, height:6, borderRadius:99, background:'var(--text-faint)', animation:`screenIn .6s ${i*0.15}s infinite alternate` }}/>)}
              </div>
            )}
          </div>

          {/* suggestion chips */}
          <div style={{ padding:'8px 12px 0', display:'flex', gap:6, flexWrap:'wrap' }}>
            {suggestions.map((s,i)=>(
              <button key={i} onClick={()=>send(s)} className="chip" style={{ cursor:'pointer', fontSize:11, padding:'4px 9px' }}>{s}</button>
            ))}
          </div>

          {/* input */}
          <div style={{ padding:'10px 12px 12px', display:'flex', gap:8, alignItems:'center' }}>
            <input className="input" value={input} onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>{ if(e.key==='Enter') send(); }}
              placeholder={tr(lang,'พิมพ์คำถาม…','Type a question…')} style={{ height:40 }} />
            <button onClick={()=>send()} className="btn btn-primary btn-icon" style={{ height:40, width:40, flexShrink:0 }} aria-label="send">
              <Icon d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z" size={17} stroke="var(--on-yellow)"/>
            </button>
          </div>
        </div>
      )}
    </>
  );
}

Object.assign(window, { Chatbot, RobotFace });
