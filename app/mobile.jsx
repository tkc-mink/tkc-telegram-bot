/* ============================================================
   mobile.jsx — Mobile viewer (field sales) inside phone frame
   Card list · voice search · quote builder
   ============================================================ */

function PhoneFrame({ children }) {
  return (
    <div style={{ width:390, height:800, maxHeight:'calc(100vh - 130px)', position:'relative', flexShrink:0,
      background:'#000', borderRadius:46, padding:11, boxShadow:'0 40px 80px -20px rgba(0,0,0,.7), 0 0 0 1px var(--border)' }}>
      <div style={{ width:'100%', height:'100%', borderRadius:36, overflow:'hidden', position:'relative', background:'var(--bg)', display:'flex', flexDirection:'column' }}>
        {/* notch */}
        <div style={{ position:'absolute', top:0, left:'50%', transform:'translateX(-50%)', width:120, height:28, background:'#000', borderRadius:'0 0 18px 18px', zIndex:20 }} />
        {children}
      </div>
    </div>
  );
}

function MobileCard({ lang, r, onAdd, added }) {
  const avail = r.stock.total - r.stock.pending;
  return (
    <div className="card" style={{ padding:'13px 14px', background:'var(--surface-1)' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:8 }}>
        <div style={{ minWidth:0, flex:1 }}>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            {r.oem && <span style={{color:'var(--yellow)', fontSize:12}}>★</span>}
            <span className="mono" style={{ fontWeight:700, fontSize:15 }}>{r.size}</span>
            {r.dt && <span className="chip" style={{padding:'0 6px', fontSize:9.5}}>{r.dt}</span>}
          </div>
          <div className="dim" style={{ fontSize:12, marginTop:2, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{r.brand} · {r.model}</div>
        </div>
        <div style={{ textAlign:'right', flexShrink:0 }}>
          <div className="mono" style={{ fontSize:17, fontWeight:700, color:'var(--yellow)' }}>{fmt(r.retail)}</div>
          <div className="faint mono" style={{ fontSize:10 }}>{S(lang,'baht')}</div>
        </div>
      </div>
      <div style={{ display:'flex', alignItems:'center', gap:8, marginTop:11, fontSize:11 }}>
        <span className="badge" style={{ whiteSpace:'nowrap', background: avail>50?'var(--green-ghost)':'var(--amber-ghost)', color: avail>50?'var(--green)':'var(--amber)' }}>
          {tr(lang,'คงเหลือ','stock')} {fmt(avail)}
        </span>
        <span className="mono faint">DOT {[...new Set(r.dot.map(d=>d.yy))].join(',')}</span>
        <button onClick={onAdd} className="btn btn-sm" style={{ marginLeft:'auto', padding:'4px 10px',
          background: added?'var(--green-ghost)':'var(--yellow)', color: added?'var(--green)':'var(--on-yellow)', border:'none', fontWeight:600 }}>
          {added ? <><Icon d={ICONS.check} size={13}/> {tr(lang,'เพิ่มแล้ว','Added')}</> : <><Icon d={ICONS.plus} size={13}/> {tr(lang,'ใบเสนอ','Quote')}</>}
        </button>
      </div>
    </div>
  );
}

function MobileViewer({ lang }) {
  const [q, setQ] = React.useState('');
  const [listening, setListening] = React.useState(false);
  const [quote, setQuote] = React.useState([]);
  const [sheet, setSheet] = React.useState(false);

  const subseq = (text, query) => { const p=text.toLowerCase().replace(/[^a-z0-9]/g,''); const s=query.toLowerCase().replace(/[^a-z0-9]/g,''); if(!s)return true; let i=0; for(const c of p){if(i<s.length&&c===s[i])i++;} return i===s.length; };
  const rows = PRODUCTS.filter(r=>subseq(r.size+r.brand+r.model, q)).slice(0,8);
  const total = quote.reduce((s,id)=>{ const r=PRODUCTS.find(p=>p.id===id); return s+(r?r.retail:0); },0);

  const toggleQuote = (id)=> setQuote(qq=> qq.includes(id)? qq.filter(x=>x!==id) : [...qq,id]);

  return (
    <div className="screen-in" style={{ display:'flex', gap:40, padding:'24px 32px', alignItems:'flex-start', justifyContent:'center', minHeight:'calc(100vh - var(--topbar-h))' }}>
      <PhoneFrame>
        {/* status bar */}
        <div style={{ height:44, display:'flex', alignItems:'flex-end', justifyContent:'space-between', padding:'0 22px 5px', fontSize:12, fontWeight:600, flexShrink:0 }}>
          <span className="mono">9:41</span>
          <span style={{ display:'flex', gap:5, fontSize:11 }}>📶 🔋</span>
        </div>
        {/* app header */}
        <div style={{ padding:'6px 16px 12px', flexShrink:0 }}>
          <div style={{ display:'flex', alignItems:'center', gap:9, marginBottom:12 }}>
            <TkcLogo size={26} />
            <div style={{ lineHeight:1.15 }}>
              <div style={{ fontWeight:700, fontSize:14 }}>TKC <span className="yellow">Pricelist</span></div>
              <div className="mono faint" style={{ fontSize:9 }}>{tr(lang,'เซลล์ยางใหญ่','B-Tire Sales')}</div>
            </div>
            <span className="badge badge-green" style={{ marginLeft:'auto' }}>● PWA</span>
          </div>
          {/* search */}
          <div style={{ position:'relative' }}>
            <Icon d={ICONS.search} size={16} style={{ position:'absolute', left:12, top:11, color:'var(--text-faint)' }} />
            <input className="input" value={q} onChange={e=>setQ(e.target.value)} placeholder={tr(lang,'ค้นหายาง…','Search tyres…')} style={{ paddingLeft:36, paddingRight:44, height:40 }} />
            <button onClick={()=>{ setListening(l=>!l); if(!listening){ setTimeout(()=>{ setQ('215'); setListening(false); },1400); } }}
              className="btn btn-icon" style={{ position:'absolute', right:5, top:5, padding:6,
                background: listening?'var(--red-ghost)':'transparent', border:'none', color: listening?'var(--red)':'var(--text-faint)' }}>
              <Icon d={ICONS.mic} size={17} />
            </button>
          </div>
          {listening && <div style={{ marginTop:8, fontSize:11.5, color:'var(--red)', display:'flex', alignItems:'center', gap:6 }}>
            <span style={{ width:6, height:6, borderRadius:99, background:'var(--red)', animation:'screenIn 1s infinite alternate' }}/> {tr(lang,'กำลังฟัง… พูดขนาดยาง','Listening… say the size')}
          </div>}
        </div>

        {/* list */}
        <div style={{ flex:1, overflow:'auto', padding:'0 16px 90px', display:'flex', flexDirection:'column', gap:9 }}>
          {!q && <div className="eyebrow" style={{ padding:'2px 2px 4px' }}>🔥 {tr(lang,'ขายดี 20 อันดับ','Top 20 best-sellers')}</div>}
          {rows.map(r=><MobileCard key={r.id} lang={lang} r={r} added={quote.includes(r.id)} onAdd={()=>toggleQuote(r.id)} />)}
        </div>

        {/* quote bar */}
        {quote.length>0 && (
          <div style={{ position:'absolute', left:14, right:14, bottom:16, zIndex:15 }}>
            <button onClick={()=>setSheet(true)} className="btn btn-primary" style={{ width:'100%', justifyContent:'space-between', padding:'13px 18px', boxShadow:'var(--shadow-3)' }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}><Icon d={ICONS.tag} size={17}/> {tr(lang,'ใบเสนอราคา','Quote')} ({quote.length})</span>
              <span className="mono" style={{ fontWeight:700 }}>{fmt(total)} {S(lang,'baht')}</span>
            </button>
          </div>
        )}

        {/* quote bottom sheet */}
        {sheet && (
          <div style={{ position:'absolute', inset:0, zIndex:30, background:'rgba(0,0,0,.55)', display:'flex', flexDirection:'column', justifyContent:'flex-end' }} onClick={()=>setSheet(false)}>
            <div className="pop-in" onClick={e=>e.stopPropagation()} style={{ background:'var(--surface-2)', borderRadius:'22px 22px 0 0', padding:'18px 18px 24px', borderTop:'1px solid var(--border)' }}>
              <div style={{ width:38, height:4, borderRadius:99, background:'var(--border)', margin:'0 auto 16px' }} />
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
                <h3 style={{ fontSize:16, fontWeight:700 }}>{tr(lang,'ใบเสนอราคา','Quotation')}</h3>
                <span className="faint mono" style={{ fontSize:11 }}>#TKC-2606-0142</span>
              </div>
              <div style={{ display:'flex', flexDirection:'column', gap:8, marginBottom:14 }}>
                {quote.map(id=>{ const r=PRODUCTS.find(p=>p.id===id); return (
                  <div key={id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', fontSize:13 }}>
                    <span><span className="mono" style={{fontWeight:600}}>{r.size}</span> <span className="faint">{r.brand}</span></span>
                    <span className="mono" style={{ fontWeight:600 }}>{fmt(r.retail)}</span>
                  </div>
                );})}
              </div>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', padding:'12px 0', borderTop:'1px solid var(--border-soft)', marginBottom:14 }}>
                <span className="dim">{tr(lang,'รวมทั้งสิ้น','Total')}</span>
                <span className="mono" style={{ fontSize:22, fontWeight:700, color:'var(--yellow)' }}>{fmt(total)} <span style={{fontSize:12, color:'var(--text-faint)'}}>{S(lang,'baht')}</span></span>
              </div>
              <div style={{ display:'flex', gap:9 }}>
                <button className="btn" style={{ flex:1, justifyContent:'center' }}><Icon d={ICONS.copy} size={15}/> {tr(lang,'คัดลอก','Copy')}</button>
                <button className="btn btn-primary" style={{ flex:1.4, justifyContent:'center' }}><Icon d={ICONS.share} size={15}/> {tr(lang,'แชร์ลิงก์ (LINE)','Share link')}</button>
              </div>
              <div className="mono faint" style={{ fontSize:10, textAlign:'center', marginTop:10 }}>app.tkc.local/q/x7k2 · {tr(lang,'หมดอายุใน 7 วัน','expires in 7 days')}</div>
            </div>
          </div>
        )}
      </PhoneFrame>

      {/* annotation panel */}
      <div style={{ maxWidth:300, paddingTop:16 }}>
        <div className="eyebrow" style={{ marginBottom:12 }}>{tr(lang,'มุมมองมือถือ — เซลล์หน้างาน','Mobile — field sales')}</div>
        <h2 style={{ fontSize:20, fontWeight:700, marginBottom:14, letterSpacing:'-0.01em' }}>{tr(lang,'ปิดการขายได้ในมือ','Close deals in hand')}</h2>
        {[
          ['🎙️', tr(lang,'ค้นหาด้วยเสียง','Voice search'), tr(lang,'กดไมค์แล้วพูดขนาดยาง — ใช้ Web Speech API','Tap mic, say the size — Web Speech API')],
          ['🛒', tr(lang,'สร้างใบเสนอราคาเร็ว','Build quotes fast'), tr(lang,'แตะ + เพื่อรวมหลายรายการ แล้วแชร์ลิงก์ให้ลูกค้าทาง LINE','Tap + to bundle items, share a link via LINE')],
          ['📡', tr(lang,'ใช้ออฟไลน์ได้','Works offline'), tr(lang,'PWA แคชราคาที่ดูล่าสุด 7 วัน เปิดดูได้แม้เน็ตหลุด','PWA caches 7 days of viewed prices')],
          ['🔒', tr(lang,'เห็นเฉพาะที่ควรเห็น','Role-scoped'), tr(lang,'เซลล์ยางใหญ่เห็นราคาขายอย่างเดียว ไม่เห็นทุน','B-Tire sees retail only — cost hidden')],
        ].map(([ic,t,d],i)=>(
          <div key={i} style={{ display:'flex', gap:12, marginBottom:16 }}>
            <div style={{ width:34, height:34, borderRadius:9, background:'var(--surface-1)', display:'grid', placeItems:'center', fontSize:16, flexShrink:0 }}>{ic}</div>
            <div>
              <div style={{ fontSize:13.5, fontWeight:600 }}>{t}</div>
              <div className="dim" style={{ fontSize:12, marginTop:2, lineHeight:1.45 }}>{d}</div>
            </div>
          </div>
        ))}
        <div className="card" style={{ padding:'12px 14px', fontSize:11.5, color:'var(--text-dim)', display:'flex', gap:9, background:'var(--surface-1)' }}>
          <span>👆</span> {tr(lang,'ลองพิมพ์ในช่องค้นหา หรือกดไมค์ แล้วแตะปุ่ม “ใบเสนอ” เพื่อรวมรายการ','Try the search box or the mic, then tap “Quote” to bundle items')}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { MobileViewer, PhoneFrame });
