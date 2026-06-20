/* ============================================================
   editor.jsx — Admin spreadsheet-style price editor
   Live cipher preview, dirty-cell tracking, batch save
   ============================================================ */

function Editor({ lang }) {
  const cols = [
    { k:'size',   label:tr(lang,'ขนาด','Size'), w:120, type:'text', mono:true },
    { k:'brand',  label:tr(lang,'ยี่ห้อ','Brand'), w:120, type:'text' },
    { k:'model',  label:tr(lang,'รุ่น','Model'), w:160, type:'text' },
    { k:'cost',   label:tr(lang,'ทุน','Cost'), w:100, type:'num', cipher:1 },
    { k:'retail', label:tr(lang,'ราคาขาย','Retail'), w:100, type:'num' },
    { k:'B',      label:'B', w:88, type:'num', cipher:2, bas:true },
    { k:'A',      label:'A', w:88, type:'num', cipher:2, bas:true },
    { k:'S',      label:'S', w:88, type:'num', cipher:2, bas:true },
    { k:'status', label:'s', w:54, type:'text' },
  ];
  // local editable model
  const init = PRODUCTS.filter(p=>p.cat==='car'||p.cat==='pickup').slice(0,10).map(p=>({
    id:p.id, size:p.size, brand:p.brand, model:p.model, cost:p.cost, retail:p.retail,
    B:p.bas.B, A:p.bas.A, S:p.bas.S, status:p.status,
  }));
  const [data, setData] = React.useState(init);
  const [dirty, setDirty] = React.useState({});  // `${rowId}:${col}` -> true
  const [active, setActive] = React.useState(null); // {r,c}
  const [showCipher, setShowCipher] = React.useState(true);

  const setCell = (rid, k, v) => {
    setData(d=>d.map(row=>row.id===rid?{...row,[k]:v}:row));
    setDirty(dd=>({...dd, [`${rid}:${k}`]:true}));
  };
  const dirtyCount = Object.keys(dirty).length;
  const codeFor = (col, val) => col.cipher===1 ? cost2code(val) : col.cipher===2 ? whole2code(val) : '';

  return (
    <div className="screen-in" style={{ display:'flex', flexDirection:'column', height:'calc(100vh - var(--topbar-h))' }}>
      {/* toolbar */}
      <div style={{ padding:'14px 28px', borderBottom:'1px solid var(--border-soft)', display:'flex', alignItems:'center', gap:14, flexWrap:'wrap' }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:9 }}>
            <h1 style={{ fontSize:19, fontWeight:700 }}>{tr(lang,'แก้ไขราคา','Price Editor')}</h1>
            <span className="badge badge-yellow">Admin</span>
          </div>
          <div className="dim" style={{ fontSize:12, marginTop:2 }}>{tr(lang,'ยางเก๋ง + กระบะ · ชีต P1','Passenger + Pickup · Sheet P1')}</div>
        </div>
        <div style={{ flex:1 }} />
        <label style={{ display:'flex', alignItems:'center', gap:7, fontSize:12.5, color:'var(--text-dim)', cursor:'pointer' }}>
          <span onClick={()=>setShowCipher(s=>!s)} style={{ width:36, height:20, borderRadius:99, background: showCipher?'var(--yellow)':'var(--surface-3)', position:'relative', transition:'.15s', flexShrink:0 }}>
            <span style={{ position:'absolute', top:2, left: showCipher?18:2, width:16, height:16, borderRadius:99, background:'#fff', transition:'.15s' }} />
          </span>
          {tr(lang,'แสดงรหัสลับ','Show cipher')}
        </label>
        <button className="btn btn-sm"><Icon d={ICONS.sync} size={15}/> {tr(lang,'ดึงรหัส AIO','AIO lookup')}</button>
        <button className="btn btn-sm" disabled={!dirtyCount} style={{opacity:dirtyCount?1:.5}}>{tr(lang,'ยกเลิก','Discard')}</button>
        <button className="btn btn-primary btn-sm" disabled={!dirtyCount} style={{opacity:dirtyCount?1:.5}}>
          <Icon d={ICONS.check} size={15}/> {tr(lang,'บันทึก','Save')} {dirtyCount>0 && `(${dirtyCount})`}
        </button>
      </div>

      {/* batch-mode banner */}
      {dirtyCount>0 && (
        <div style={{ padding:'8px 28px', background:'var(--yellow-ghost)', borderBottom:'1px solid color-mix(in oklch,var(--yellow) 25%,transparent)', fontSize:12.5, color:'var(--yellow)', display:'flex', alignItems:'center', gap:8 }}>
          <Icon d={ICONS.edit} size={14}/> {tr(lang,`โหมด Batch · แก้ ${dirtyCount} ช่อง · ทุกการแก้ไขจะถูกบันทึก audit log`,`Batch mode · ${dirtyCount} cells changed · all edits go to audit log`)}
        </div>
      )}

      {/* sheet */}
      <div style={{ flex:1, overflow:'auto', padding:'0 0 40px' }}>
        <table className="pl" style={{ minWidth:980 }}>
          <thead>
            <tr>
              <th style={{ width:40, textAlign:'center', background:'var(--surface-3)' }}>#</th>
              {cols.map(c=>(
                <th key={c.k} style={{ width:c.w, textAlign: c.type==='num'?'right':'left' }}>
                  {c.label}{c.cipher && <span style={{color:c.cipher===1?'var(--yellow)':'var(--blue)', marginLeft:3}}>⚿</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row,ri)=>(
              <tr key={row.id} style={{ cursor:'default' }}>
                <td style={{ textAlign:'center', color:'var(--text-faint)', background:'var(--surface-2)', fontFamily:'var(--font-mono)', fontSize:11 }}>{ri+1}</td>
                {cols.map((c,ci)=>{
                  const isDirty = dirty[`${row.id}:${c.k}`];
                  const isActive = active && active.r===ri && active.c===ci;
                  const val = row[c.k];
                  return (
                    <td key={c.k} onClick={()=>setActive({r:ri,c:ci})} style={{
                      padding:0, position:'relative',
                      background: isActive ? 'color-mix(in oklch,var(--yellow) 10%,var(--surface-1))' : isDirty ? 'var(--green-ghost)' : 'transparent',
                      boxShadow: isActive ? 'inset 0 0 0 2px var(--yellow)' : 'none',
                    }}>
                      <div style={{ display:'flex', flexDirection:'column' }}>
                        <input value={val} onChange={e=>setCell(row.id, c.k, c.type==='num'? e.target.value.replace(/[^0-9]/g,'') : e.target.value)}
                          onFocus={()=>setActive({r:ri,c:ci})}
                          style={{ border:'none', background:'transparent', color: c.cipher&&showCipher?'var(--text-faint)':'var(--text)',
                            fontFamily: c.mono||c.type==='num'?'var(--font-mono)':'inherit', fontSize:13, fontWeight: c.type==='num'?600:400,
                            padding:'8px 12px', width:'100%', outline:'none', textAlign: c.type==='num'?'right':'left',
                            fontVariantNumeric:'tabular-nums' }} />
                        {c.cipher && showCipher && val!=='' && (
                          <div style={{ padding:'0 12px 5px', textAlign:'right', fontFamily:'var(--font-mono)', fontSize:11, fontWeight:700, letterSpacing:'0.1em',
                            color: c.cipher===1?'var(--yellow)':'var(--blue)' }}>{codeFor(c, val)}</div>
                        )}
                      </div>
                      {isDirty && <span style={{ position:'absolute', top:4, right:4, width:5, height:5, borderRadius:99, background:'var(--green)' }} />}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        {/* live cipher legend */}
        <div style={{ margin:'18px 28px', padding:'14px 18px', background:'var(--surface-1)', borderRadius:'var(--r-lg)', border:'1px solid var(--border-soft)', maxWidth:760 }}>
          <div className="eyebrow" style={{ marginBottom:10 }}>{tr(lang,'ตารางรหัสลับ (อ้างอิง)','Cipher reference')}</div>
          <div style={{ display:'flex', gap:28, flexWrap:'wrap' }}>
            {[['#1 ทุน','var(--yellow)',CIPHER1],['#2 ราคาส่ง','var(--blue)',CIPHER2]].map(([nm,col,ciph])=>(
              <div key={nm}>
                <div style={{ fontSize:12, fontWeight:600, color:col, marginBottom:6 }}>{nm}</div>
                <div style={{ display:'flex', gap:3 }}>
                  {ciph.map((ch,i)=>(
                    <div key={i} style={{ textAlign:'center' }}>
                      <div className="mono" style={{ fontSize:10, color:'var(--text-faint)' }}>{i}</div>
                      <div className="mono" style={{ fontSize:13, fontWeight:700, color:col, width:20, padding:'2px 0', background:'var(--surface-2)', borderRadius:4, marginTop:2 }}>{ch}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <div style={{ alignSelf:'center', fontSize:11.5, color:'var(--text-faint)', maxWidth:160 }}>
              <span className="mono" style={{color:'var(--text-dim)'}}>A</span> = {tr(lang,'เลขซ้ำตำแหน่งก่อนหน้า เช่น','repeat marker, e.g.')} <span className="mono yellow">1818→TBTB</span>, <span className="mono yellow">1111→TATA</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Editor });
