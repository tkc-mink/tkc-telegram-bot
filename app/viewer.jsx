/* ============================================================
   viewer.jsx — Pricelist Viewer (desktop)
   Column-level permissions + cipher + DOT + click popups + CR
   ============================================================ */

// short DOT label: single -> "26", multi -> "23-26"
function DotShort({ dot }) {
  if (!dot || !dot.length) return <span className="faint">—</span>;
  const yrs = [...new Set(dot.map(d=>d.yy))].sort((a,b)=>a-b);
  const label = yrs.length===1 ? String(yrs[0]) : `${yrs[0]}-${yrs[yrs.length-1]}`;
  const oldest = yrs[0];
  return <span className="mono" style={{ fontWeight:600, color:dotColor(oldest) }}>{label}</span>;
}

function statusCell(lang, status) {
  if (status==='-') return { bg:'transparent', el:<span className="faint">–</span> };
  if (status==='+') return { bg:'var(--amber-ghost)', el:<span className="mono" style={{color:'var(--amber)', fontWeight:600}}>+</span>, title:tr(lang,'ต้องเบิก','restock') };
  if (status==='C') return { bg:'transparent', el:<span className="badge badge-red">C</span>, title:'Clearance' };
  return { bg:'transparent', el:<span className="mono" style={{color:'var(--red)', fontWeight:600}}>{status}</span> };
}

// ---- detail popup (10s auto-dismiss like PRD) ----
function DetailPopup({ lang, role, row, onClose }) {
  const perm = COL_PERMS[role];
  const [left, setLeft] = React.useState(10);
  React.useEffect(()=>{ const t=setInterval(()=>setLeft(s=>{ if(s<=1){clearInterval(t); onClose(); return 0;} return s-1; }),1000); return ()=>clearInterval(t); },[]);
  const avail = row.stock.total - row.stock.pending;
  return (
    <div onClick={onClose} style={{ position:'fixed', inset:0, zIndex:60, background:'rgba(0,0,0,.5)', backdropFilter:'blur(3px)', display:'grid', placeItems:'center' }}>
      <div className="card pop-in" onClick={e=>e.stopPropagation()} style={{ width:470, maxWidth:'92vw', maxHeight:'90vh', display:'flex', flexDirection:'column', background:'var(--surface-2)', boxShadow:'var(--shadow-3)', overflow:'hidden' }}>
        {/* header */}
        <div style={{ padding:'16px 18px', background:'var(--surface-1)', borderBottom:'1px solid var(--border)', flexShrink:0 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
            <div>
              <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                {row.oem && <span title="OEM" style={{color:'var(--yellow)'}}>★</span>}
                <span className="mono" style={{ fontSize:17, fontWeight:600 }}>{row.size}</span>
                {row.ply && <span className="chip" style={{padding:'1px 7px', fontSize:10}}>{row.ply}</span>}
              </div>
              <div className="dim" style={{ fontSize:13, marginTop:3 }}>{row.brand} · {row.model}</div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <span className="mono" style={{ fontSize:10, color:'var(--text-faint)' }}>{left}s</span>
              <button className="btn btn-icon btn-ghost btn-sm" onClick={onClose}><Icon d="M6 6l12 12M18 6L6 18" size={15}/></button>
            </div>
          </div>
        </div>

        <div style={{ padding:'16px 18px', display:'flex', flexDirection:'column', gap:16, overflowY:'auto' }}>
          {/* stock */}
          <div>
            <div className="eyebrow" style={{marginBottom:8}}>📊 {tr(lang,'สต็อก','Stock')}</div>
            <div style={{ display:'flex', gap:10 }}>
              {[[tr(lang,'ทั้งหมด','Total'),row.stock.total,'var(--text)'],[tr(lang,'ค้างส่ง','Pending'),row.stock.pending,'var(--amber)'],[tr(lang,'คงเหลือ','Available'),avail,'var(--green)']].map((s,i)=>(
                <div key={i} style={{ flex:1, background:'var(--surface-1)', borderRadius:10, padding:'10px 12px' }}>
                  <div className="mono tnum" style={{ fontSize:18, fontWeight:600, color:s[2] }}>{fmt(s[1])}</div>
                  <div style={{ fontSize:10.5, color:'var(--text-faint)' }}>{s[0]}</div>
                </div>
              ))}
            </div>
          </div>

          {/* DOT breakdown */}
          <div>
            <div className="eyebrow" style={{marginBottom:8}}>📅 DOT {tr(lang,'รายสัปดาห์','by week')}</div>
            <div style={{ display:'flex', flexDirection:'column', gap:4 }}>
              {row.dot.map((d,i)=>(
                <div key={i} style={{ display:'flex', alignItems:'center', gap:10, fontSize:13 }}>
                  <span className="mono" style={{ fontWeight:600, color:dotColor(d.yy), width:54 }}>DOT {d.yy}</span>
                  <span className="mono faint">⇒ {d.ww}</span>
                  <div style={{ flex:1, height:5, background:'var(--surface-1)', borderRadius:9, overflow:'hidden' }}>
                    <div style={{ height:'100%', width:`${Math.min(100, d.qty/Math.max(...row.dot.map(x=>x.qty))*100)}%`, background:dotColor(d.yy), opacity:.55 }} />
                  </div>
                  <span className="mono tnum" style={{ minWidth:70, textAlign:'right', whiteSpace:'nowrap' }}>{fmt(d.qty)} {tr(lang,'เส้น','pcs')}</span>
                </div>
              ))}
            </div>
          </div>

          {/* price ladder — each tier is a SET: number + code + margin */}
          {(() => {
            // which columns the role may see
            const showNum    = perm.retail || perm.basReal;       // ตัวเลขจริง
            const showCode   = perm.basCode;                       // โค้ด (cipher)
            const showMargin = perm.margin;                        // กำไร (= ราคา − ทุน)
            const cols = ['label', showNum && 'num', showCode && 'code', showMargin && 'margin'].filter(Boolean);
            const gridCols = cols.map(c => c==='label' ? '74px' : c==='margin' ? '76px' : '1fr').join(' ');
            const m = (price) => row.cost!=null ? price - row.cost : null;

            // tier rows visible to this role
            const tiers = [];
            if (perm.retail) tiers.push({ key:'retail', label:tr(lang,'ขายปลีก','Retail'), num:row.retail, code:null, accent:'var(--yellow)', strong:true });
            if (perm.retail && row.cr>0) tiers.push({ key:'credit', label:tr(lang,'เครดิต','Credit'), num:row.credit, code:null, accent:'var(--amber)', note:`+CR${fmt(row.cr)}` });
            if (showCode || perm.basReal) {
              ['B','A','S'].forEach(t => tiers.push({ key:t, label:t, num:row.bas[t], code:whole2code(row.bas[t]), accent:'var(--blue)' }));
            }

            const Cell = ({ children, align='right', style }) => (
              <div style={{ textAlign:align, minWidth:0, ...style }}>{children}</div>
            );

            return (
              <div>
                <div className="eyebrow" style={{ marginBottom:8 }}>💵 {tr(lang,'ราคา (ต่อระดับ: เลข · โค้ด · กำไร)','Price ladder (number · code · margin)')}</div>
                <div style={{ background:'var(--surface-1)', borderRadius:10, padding:'6px 12px 10px' }}>
                  {/* header */}
                  <div style={{ display:'grid', gridTemplateColumns:gridCols, gap:10, padding:'6px 0', borderBottom:'1px solid var(--border-soft)' }}>
                    <Cell align="left"><span className="eyebrow" style={{fontSize:9.5}}>{tr(lang,'ระดับ','Tier')}</span></Cell>
                    {showNum    && <Cell><span className="eyebrow" style={{fontSize:9.5}}>{tr(lang,'ตัวเลข','Number')}</span></Cell>}
                    {showCode   && <Cell><span className="eyebrow" style={{fontSize:9.5}}>{tr(lang,'โค้ด','Code')}</span></Cell>}
                    {showMargin && <Cell><span className="eyebrow" style={{fontSize:9.5}}>{tr(lang,'กำไร','Margin')}</span></Cell>}
                  </div>
                  {/* tier rows */}
                  {tiers.map(t => {
                    const mg = (t.key==='credit') ? m(t.num) : m(t.num);
                    return (
                      <div key={t.key} style={{ display:'grid', gridTemplateColumns:gridCols, gap:10, alignItems:'center', padding:'7px 0', borderBottom:'1px solid var(--border-soft)' }}>
                        <Cell align="left">
                          <div style={{ display:'flex', flexDirection:'column', gap:3, alignItems:'flex-start' }}>
                            <span style={{ display:'inline-flex', alignItems:'center', justifyContent:'center', minWidth:22, height:20, padding:'0 7px', borderRadius:6,
                              background:`color-mix(in oklch, ${t.accent} 16%, transparent)`, color:t.accent, fontWeight:700, fontSize:11.5,
                              fontFamily: t.key.length===1?'var(--font-mono)':'inherit' }}>{t.label}</span>
                            {t.note && <span className="badge badge-amber" style={{ padding:'1px 5px', fontSize:9.5 }}>{t.note}</span>}
                          </div>
                        </Cell>
                        {showNum && <Cell>
                          {t.num!=null
                            ? <span className="mono tnum" style={{ fontWeight:t.strong?700:600, fontSize:t.strong?16:13.5, color:t.strong?'var(--yellow)':'var(--text)' }}>{fmt(t.num)}</span>
                            : <span className="faint">—</span>}
                        </Cell>}
                        {showCode && <Cell>
                          {t.code
                            ? <span className="mono" style={{ fontWeight:600, letterSpacing:'0.08em', color:'var(--blue)', fontSize:12.5 }}>{t.code}</span>
                            : <span className="faint">—</span>}
                        </Cell>}
                        {showMargin && <Cell>
                          {mg!=null
                            ? <span className="mono tnum" style={{ fontWeight:600, color: mg>=0?'var(--green)':'var(--red)', fontSize:12.5 }}>{mg>=0?'+':''}{fmt(mg)}</span>
                            : <span className="faint">—</span>}
                        </Cell>}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}

          {/* admin: cost basis */}
          {perm.costReal && <div style={{ background:'var(--yellow-ghost)', borderRadius:10, padding:'12px 14px', border:'1px solid color-mix(in oklch, var(--yellow) 25%, transparent)' }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:10 }}>
              <span style={{ display:'flex', alignItems:'center', gap:6, color:'var(--yellow)', fontWeight:600, fontSize:13 }}><Icon d={ICONS.shield} size={14}/> {tr(lang,'ทุน (เฉพาะแอดมิน)','Cost (Admin only)')}</span>
              <span style={{ display:'flex', alignItems:'baseline', gap:8 }}>
                <span className="mono tnum" style={{fontWeight:700, fontSize:15}}>{fmt(row.cost)}</span>
                <span className="mono" style={{color:'var(--yellow)', letterSpacing:'0.1em', fontSize:12.5}}>{cost2code(row.cost)}</span>
              </span>
            </div>
          </div>}

          {row.note && <div style={{ fontSize:12, color:'var(--text-dim)', display:'flex', gap:7 }}><span>📝</span>{row.note}</div>}
        </div>
      </div>
    </div>
  );
}

function Viewer({ lang, role }) {
  const perm = COL_PERMS[role];
  const [cat, setCat] = React.useState('all');
  const [q, setQ] = React.useState('');
  const [credit, setCredit] = React.useState(false); // CR cash/credit toggle
  const [sel, setSel] = React.useState(null);

  // subsequence matching (PRD §6.6)
  const subseq = (text, query) => {
    const p = text.toLowerCase().replace(/[^a-z0-9]/g,''); const s = query.toLowerCase().replace(/[^a-z0-9]/g,'');
    if(!s) return true; let i=0; for(const c of p){ if(i<s.length && c===s[i]) i++; } return i===s.length;
  };
  const rows = PRODUCTS.filter(r => (cat==='all'||r.cat===cat) && subseq(r.size+r.brand+r.model, q));
  const catObj = CATEGORIES.find(c=>c.id===cat);

  return (
    <div className="screen-in" style={{ display:'flex', flexDirection:'column', height:'calc(100vh - var(--topbar-h))' }}>
      {/* sub header */}
      <div style={{ padding:'18px 28px 14px', borderBottom:'1px solid var(--border-soft)' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:12 }}>
          <div>
            <h1 style={{ fontSize:20, fontWeight:700 }}>{catObj ? tr(lang,catObj.th,catObj.en) : tr(lang,'ราคายางทั้งหมด','All pricelists')}</h1>
            <div className="dim" style={{ fontSize:12.5, marginTop:3 }}>
              {tr(lang,'ประจำวันที่','As of')} 9 {tr(lang,'มิถุนายน','Jun')} {tr(lang,'2569','2026')} · {rows.length} {tr(lang,'รายการ','items')}
              {catObj && <> · {tr(lang,'หน้า','p.')} {catObj.page}</>}
            </div>
          </div>
          <div style={{ display:'flex', gap:8 }}>
            {(perm.crToggle) && (
              <div style={{ display:'flex', background:'var(--surface-1)', borderRadius:'var(--r-md)', padding:3, border:'1px solid var(--border-soft)' }}>
                {[[false,tr(lang,'เงินสด','Cash')],[true,tr(lang,'เครดิต','Credit')]].map(([v,l])=>(
                  <button key={String(v)} onClick={()=>setCredit(v)} style={{ padding:'6px 13px', borderRadius:7, border:'none', cursor:'pointer',
                    fontFamily:'inherit', fontSize:12, fontWeight:600,
                    background: credit===v?'var(--yellow)':'transparent', color: credit===v?'var(--on-yellow)':'var(--text-faint)' }}>{l}</button>
                ))}
              </div>
            )}
            <button className="btn btn-sm"><Icon d={ICONS.print} size={15}/> {tr(lang,'พิมพ์ A4','Print')}</button>
            <button className="btn btn-sm"><Icon d={ICONS.filter} size={15}/> {tr(lang,'ตัวกรอง','Filters')}</button>
          </div>
        </div>

        {/* category chips */}
        <div style={{ display:'flex', gap:7, marginTop:14, overflowX:'auto', paddingBottom:2 }}>
          <button className={`chip ${cat==='all'?'active':''}`} onClick={()=>setCat('all')}>{S(lang,'all')}</button>
          {CATEGORIES.map(c=>(
            <button key={c.id} className={`chip ${cat===c.id?'active':''}`} onClick={()=>setCat(c.id)} style={{whiteSpace:'nowrap'}}>
              {tr(lang,c.th,c.en)} <span className="mono" style={{fontSize:10, opacity:.6}}>{c.count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* inline search */}
      <div style={{ padding:'12px 28px', borderBottom:'1px solid var(--border-soft)', display:'flex', gap:10, alignItems:'center' }}>
        <div style={{ position:'relative', flex:1, maxWidth:380 }}>
          <Icon d={ICONS.search} size={15} style={{ position:'absolute', left:11, top:9, color:'var(--text-faint)' }} />
          <input className="input" value={q} onChange={e=>setQ(e.target.value)} placeholder={tr(lang,'เช่น 21515mk … (จับลำดับตัวอักษร)','e.g. 21515mk … (subsequence)')} style={{ paddingLeft:34, height:34, padding:'6px 12px 6px 34px' }} />
        </div>
        <span className="mono faint" style={{ fontSize:11 }}>{tr(lang,'พิมพ์ติดกันได้ เช่น','try')} <span className="yellow">21515mk</span>, <span className="yellow">michpilot</span></span>
      </div>

      {/* table */}
      <div style={{ flex:1, overflow:'auto' }}>
        <table className="pl">
          <thead>
            <tr>
              <th style={{width:30}}></th>
              <th>{tr(lang,'ขนาด','Size')}</th>
              <th>{tr(lang,'ยี่ห้อ / รุ่น','Brand / Model')}</th>
              <th style={{width:54}}>DT</th>
              <th style={{width:54, textAlign:'center'}}>DOT</th>
              {perm.costReal && <th style={{textAlign:'right'}}>{tr(lang,'ทุน','Cost')}</th>}
              {perm.costCode && <th style={{textAlign:'right'}}>{tr(lang,'ทุน','Cost')} <span style={{color:'var(--yellow)'}}>⚿</span></th>}
              {perm.retail && <th style={{textAlign:'right'}}>{credit?tr(lang,'ราคาเครดิต','Credit'):tr(lang,'ราคาขาย','Retail')}</th>}
              {perm.basCode && <th style={{textAlign:'right'}}>B / A / S <span style={{color:'var(--blue)'}}>⚿</span></th>}
              {perm.basReal && <th style={{textAlign:'right'}}>B / A / S</th>}
              {perm.margin && <th style={{textAlign:'right'}}>Margin</th>}
              <th style={{width:44, textAlign:'center'}}>s</th>
              <th style={{textAlign:'right'}}>{tr(lang,'สต็อก','Stock')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r=>{
              const sc = statusCell(lang, r.status);
              const price = credit ? r.credit : r.retail;
              const avail = r.stock.total - r.stock.pending;
              return (
                <tr key={r.id} onClick={()=>setSel(r)}>
                  <td style={{textAlign:'center'}}>{r.oem && <span title="OEM" style={{color:'var(--yellow)', fontSize:13}}>★</span>}</td>
                  <td><span className="mono" style={{ fontWeight:600 }}>{r.size}</span>{r.ply && <span className="faint mono" style={{fontSize:10, marginLeft:5}}>{r.ply}</span>}</td>
                  <td><span style={{fontWeight:500}}>{r.brand}</span> <span className="faint">{r.model}</span></td>
                  <td>{r.dt && <span className="chip" style={{padding:'1px 7px', fontSize:10}}>{r.dt}</span>}</td>
                  <td style={{textAlign:'center'}}><DotShort dot={r.dot}/></td>
                  {perm.costReal && <td className="cell-num">{fmt(r.cost)}</td>}
                  {perm.costCode && <td className="cell-num" style={{color:'var(--yellow)', letterSpacing:'0.08em'}}>{cost2code(r.cost)}</td>}
                  {perm.retail && <td className="cell-num" style={{ fontWeight:700, color: credit&&r.cr>0?'var(--amber)':'var(--text)' }}>{fmt(price)}</td>}
                  {perm.basCode && <td className="cell-num" style={{color:'var(--blue)', letterSpacing:'0.06em'}}>{whole2code(r.bas.B)}/{whole2code(r.bas.A)}/{whole2code(r.bas.S)}</td>}
                  {perm.basReal && <td className="cell-num">{fmt(r.bas.B)}/{fmt(r.bas.A)}/{fmt(r.bas.S)}</td>}
                  {perm.margin && <td className="cell-num" style={{color:'var(--green)'}}>+{fmt(r.margin)}</td>}
                  <td style={{ textAlign:'center', background:sc.bg }} title={sc.title||''}>{sc.el}</td>
                  <td className="cell-num"><span style={{fontWeight:600}}>{fmt(avail)}</span>{r.stock.pending>0 && <span className="faint" style={{fontSize:10.5, marginLeft:4}}>/{fmt(r.stock.total)}</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length===0 && <div style={{ padding:60, textAlign:'center', color:'var(--text-faint)' }}>{tr(lang,'ไม่พบรายการ','No results')}</div>}
      </div>

      {/* footer legend */}
      <div style={{ padding:'10px 28px', borderTop:'1px solid var(--border-soft)', display:'flex', gap:18, fontSize:11, color:'var(--text-faint)', flexWrap:'wrap', background:'var(--surface-1)' }}>
        <span><span style={{color:'var(--yellow)'}}>★</span> OEM</span>
        <span><span style={{color:'var(--amber)'}}>+</span> {tr(lang,'ต้องเบิก','restock')}</span>
        <span><span className="badge badge-red" style={{padding:'0 5px'}}>C</span> Clearance</span>
        <span><span style={{color:'var(--green)'}}>●</span> DOT {tr(lang,'1 ปี','1yr')}</span>
        <span><span style={{color:'var(--red)'}}>●</span> DOT {tr(lang,'เก่า ≥2 ปี','old ≥2yr')}</span>
        <span style={{marginLeft:'auto'}}>⚿ {tr(lang,'รหัสลับ (cipher)','cipher code')}</span>
        <span>{tr(lang,'คลิกแถวเพื่อดูรายละเอียด','click row for details')}</span>
      </div>

      {sel && <DetailPopup lang={lang} role={role} row={sel} onClose={()=>setSel(null)} />}
    </div>
  );
}

Object.assign(window, { Viewer });
