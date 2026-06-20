/* ============================================================
   dashboard.jsx — Module picker + at-a-glance ops
   ============================================================ */

function StatCard({ label, value, unit, trend, trendColor, icon }) {
  return (
    <div className="card" style={{ padding:'16px 18px', flex:1, minWidth:0 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <div className="eyebrow">{label}</div>
        <Icon d={icon} size={16} style={{ color:'var(--text-faint)' }} />
      </div>
      <div style={{ display:'flex', alignItems:'baseline', gap:6, marginTop:10 }}>
        <span className="mono" style={{ fontSize:28, fontWeight:600, letterSpacing:'-0.02em' }}>{value}</span>
        {unit && <span style={{ fontSize:12, color:'var(--text-faint)' }}>{unit}</span>}
      </div>
      {trend && <div style={{ marginTop:6, fontSize:11.5, color:trendColor||'var(--text-dim)', display:'flex', gap:5 }}>{trend}</div>}
    </div>
  );
}

function ModuleCard({ icon, title, desc, status, accent, onClick, disabled }) {
  return (
    <button onClick={disabled?undefined:onClick} disabled={disabled} style={{
      textAlign:'left', cursor: disabled?'not-allowed':'pointer', position:'relative', overflow:'hidden',
      background:'var(--surface-1)', border:'1px solid var(--border-soft)', borderRadius:'var(--r-lg)',
      padding:'20px', fontFamily:'inherit', color:'var(--text)', opacity: disabled?0.5:1,
      transition:'all .16s', display:'flex', flexDirection:'column', gap:13, minHeight:150,
    }}
    onMouseEnter={e=>{ if(!disabled){ e.currentTarget.style.borderColor='var(--border)'; e.currentTarget.style.transform='translateY(-2px)'; e.currentTarget.style.boxShadow='var(--shadow-2)'; }}}
    onMouseLeave={e=>{ e.currentTarget.style.borderColor='var(--border-soft)'; e.currentTarget.style.transform='none'; e.currentTarget.style.boxShadow='none'; }}>
      <div style={{ position:'absolute', top:0, left:0, width:'100%', height:3, background:accent, opacity:disabled?0.3:0.9 }} />
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <div style={{ width:46, height:46, borderRadius:12, display:'grid', placeItems:'center',
          background:`color-mix(in oklch, ${accent} 16%, var(--surface-2))`, fontSize:22 }}>{icon}</div>
        {status && <span className={`badge ${status.cls}`}>{status.txt}</span>}
      </div>
      <div>
        <div style={{ fontSize:15.5, fontWeight:600, marginBottom:3 }}>{title}</div>
        <div style={{ fontSize:12.5, color:'var(--text-dim)', lineHeight:1.45 }}>{desc}</div>
      </div>
    </button>
  );
}

function Dashboard({ lang, setRoute, role }) {
  const isAdmin = role==='admin';
  const greeting = tr(lang, 'สวัสดี ชิบะน้อย', 'Welcome back, ชิบะน้อย');
  const today = tr(lang, 'วันจันทร์ที่ 9 มิถุนายน 2569', 'Monday, 9 June 2026');
  return (
    <div className="screen-in" style={{ padding:'28px 32px', maxWidth:1280, margin:'0 auto' }}>
      {/* header */}
      <div style={{ marginBottom:24 }}>
        <div className="eyebrow" style={{ marginBottom:8 }}>{today}</div>
        <h1 style={{ fontSize:26, fontWeight:700, letterSpacing:'-0.02em' }}>{greeting} 👋</h1>
        <p className="dim" style={{ marginTop:6, fontSize:14 }}>
          {tr(lang,'ภาพรวมระบบราคาวันนี้ — ทุกอย่างทำงานปกติ','Today\u2019s pricelist overview — all systems nominal')}
        </p>
      </div>

      {/* stats */}
      <div style={{ display:'flex', gap:14, marginBottom:26, flexWrap:'wrap' }}>
        <StatCard label={tr(lang,'รายการทั้งหมด','Total items')} value="2,629" icon={ICONS.box}
          trend={<><span className="yellow">7 {tr(lang,'หมวด','categories')}</span> · 64 {tr(lang,'ชีต','sheets')}</>} />
        <StatCard label={tr(lang,'แก้ราคาวันนี้','Edited today')} value="38" unit={tr(lang,'รายการ','items')} icon={ICONS.edit}
          trend={<span style={{color:'var(--green)'}}>↑ 12 {tr(lang,'จากเมื่อวาน','vs yesterday')}</span>} />
        <StatCard label={tr(lang,'AIO Sync','AIO Sync')} value="99.8" unit="%" icon={ICONS.sync}
          trend={<span style={{color:'var(--green)'}}>● {tr(lang,'ออนไลน์ · queue 1','online · queue 1')}</span>} />
        <StatCard label={tr(lang,'ใบเสนอราคา 7 วัน','Quotes (7d)')} value="146" icon={ICONS.tag}
          trend={<><span className="yellow">฿2.1M</span> {tr(lang,'มูลค่ารวม','total value')}</>} />
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1.6fr 1fr', gap:22, alignItems:'start' }}>
        {/* modules */}
        <div>
          <h3 style={{ fontSize:13, fontWeight:600, color:'var(--text-dim)', marginBottom:13, textTransform:'uppercase', letterSpacing:'0.04em' }}>
            {tr(lang,'โมดูลของคุณ','Your modules')}
          </h3>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14 }}>
            <ModuleCard icon="💰" accent="var(--yellow)" title={tr(lang,'ดูราคา (Pricelist)','Pricelist Viewer')}
              desc={tr(lang,'ตารางราคาเรียลไทม์ · ค้นหา · รายละเอียดสต็อก/DOT','Real-time price table · search · stock/DOT details')}
              status={{cls:'badge-green', txt:tr(lang,'พร้อมใช้','Live')}} onClick={()=>setRoute('viewer')} />
            <ModuleCard icon="📱" accent="var(--blue)" title={tr(lang,'มุมมองมือถือ','Mobile View')}
              desc={tr(lang,'สำหรับเซลล์หน้างาน · ค้นหาด้วยเสียง · แชร์ใบเสนอราคา','For field sales · voice search · share quotes')}
              status={{cls:'badge-green', txt:'PWA'}} onClick={()=>setRoute('mobile')} />
            {isAdmin && <ModuleCard icon="✏️" accent="var(--green)" title={tr(lang,'แก้ไขราคา','Price Editor')}
              desc={tr(lang,'แก้แบบ spreadsheet · cipher อัตโนมัติ · batch save','Spreadsheet edit · auto-cipher · batch save')}
              status={{cls:'badge-yellow', txt:'Admin'}} onClick={()=>setRoute('editor')} />}
            {isAdmin && <ModuleCard icon="⚙️" accent="var(--amber)" title={tr(lang,'ตั้งค่าระบบ','Settings Hub')}
              desc={tr(lang,'ผู้ใช้ · สิทธิ์ · cipher · อุปกรณ์ · สุขภาพระบบ','Users · roles · cipher · devices · health')}
              status={{cls:'badge-yellow', txt:'Admin'}} onClick={()=>setRoute('settings')} />}
            <ModuleCard icon="📍" accent="var(--surface-3)" title={tr(lang,'เช็คอินหน้าร้าน','Check-in')}
              desc={tr(lang,'บันทึกการเข้าพบลูกค้า · GPS','Visit logging · GPS')}
              status={{cls:'badge', txt:'Phase 3'}} disabled />
            <ModuleCard icon="🎙️" accent="var(--surface-3)" title={tr(lang,'รายงานเสียง','Voice Report')}
              desc={tr(lang,'อัดเสียง · ถอดข้อความ AI','Record · AI transcribe')}
              status={{cls:'badge', txt:'Phase 3'}} disabled />
          </div>
        </div>

        {/* activity */}
        <div>
          <h3 style={{ fontSize:13, fontWeight:600, color:'var(--text-dim)', marginBottom:13, textTransform:'uppercase', letterSpacing:'0.04em' }}>
            {tr(lang,'กิจกรรมล่าสุด','Recent activity')}
          </h3>
          <div className="card" style={{ padding:6 }}>
            {ACTIVITY.map((a,i) => (
              <div key={i} style={{ display:'flex', gap:11, padding:'11px 12px', borderRadius:10,
                borderBottom: i<ACTIVITY.length-1?'1px solid var(--border-soft)':'none' }}>
                <div style={{ width:30, height:30, borderRadius:8, background:'var(--surface-2)', display:'grid', placeItems:'center', fontSize:14, flexShrink:0 }}>{a.icon}</div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ fontSize:12.5, lineHeight:1.4 }}>{tr(lang, a.th, a.en)}</div>
                  <div className="mono" style={{ fontSize:10, color:'var(--text-faint)', marginTop:2 }}>{a.user} · {a.time}{tr(lang,'ที่แล้ว',' ago')}</div>
                </div>
                <span style={{ width:6, height:6, borderRadius:99, marginTop:6, flexShrink:0,
                  background: a.sev==='green'?'var(--green)':a.sev==='amber'?'var(--amber)':a.sev==='blue'?'var(--blue)':'var(--text-faint)' }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Dashboard });
