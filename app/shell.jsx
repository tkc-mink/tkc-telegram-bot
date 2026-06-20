/* ============================================================
   shell.jsx — AppShell (sidebar + topbar), Logo, RoleSwitcher
   ============================================================ */

const TkcLogo = ({ size=30 }) => (
  <div style={{ width:size, height:size, borderRadius:8, background:'var(--yellow)',
    display:'grid', placeItems:'center', flexShrink:0, boxShadow:'0 2px 8px -2px var(--yellow-ghost)' }}>
    <svg width={size*0.62} height={size*0.62} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="var(--on-yellow)" strokeWidth="2.2"/>
      <circle cx="12" cy="12" r="3.2" fill="var(--on-yellow)"/>
      <path d="M12 3v3.5M12 17.5V21M3 12h3.5M17.5 12H21" stroke="var(--on-yellow)" strokeWidth="2.2" strokeLinecap="round"/>
    </svg>
  </div>
);

function NavItem({ icon, label, sub, active, onClick, badge }) {
  return (
    <button onClick={onClick} className="focusable" style={{
      display:'flex', alignItems:'center', gap:11, width:'100%', textAlign:'left',
      padding:'9px 12px', borderRadius:'var(--r-md)', cursor:'pointer',
      border:'1px solid transparent',
      background: active ? 'var(--yellow-ghost)' : 'transparent',
      color: active ? 'var(--yellow)' : 'var(--text-dim)',
      fontFamily:'inherit', fontSize:13.5, fontWeight: active?600:500,
      transition:'all .13s',
    }}
    onMouseEnter={e=>{ if(!active){ e.currentTarget.style.background='var(--surface-2)'; e.currentTarget.style.color='var(--text)'; }}}
    onMouseLeave={e=>{ if(!active){ e.currentTarget.style.background='transparent'; e.currentTarget.style.color='var(--text-dim)'; }}}>
      <Icon d={icon} size={18} />
      <span style={{ flex:1 }}>{label}</span>
      {sub && <span style={{ fontSize:10, fontFamily:'var(--font-mono)', color:'var(--text-faint)' }}>{sub}</span>}
      {badge && <span className="badge badge-yellow" style={{padding:'1px 6px'}}>{badge}</span>}
    </button>
  );
}

function Sidebar({ lang, route, setRoute, role }) {
  const isAdmin = role === 'admin';
  return (
    <aside style={{
      width:'var(--sidebar-w)', flexShrink:0, height:'100vh', position:'sticky', top:0,
      background:'var(--surface-1)', borderRight:'1px solid var(--border-soft)',
      display:'flex', flexDirection:'column', padding:'16px 12px', gap:4,
    }}>
      {/* brand */}
      <div style={{ display:'flex', alignItems:'center', gap:11, padding:'4px 8px 14px' }}>
        <TkcLogo />
        <div style={{ lineHeight:1.2 }}>
          <div style={{ fontWeight:700, fontSize:14.5, letterSpacing:'-0.01em' }}>TKC <span className="yellow">Pricelist</span></div>
          <div className="mono" style={{ fontSize:9.5, color:'var(--text-faint)', letterSpacing:'0.08em' }}>DYNAMIC · v1.0</div>
        </div>
      </div>

      <div className="eyebrow" style={{ padding:'8px 10px 4px' }}>{S(lang,'group_main')}</div>
      <NavItem icon={ICONS.grid}  label={S(lang,'nav_dashboard')} active={route==='dashboard'} onClick={()=>setRoute('dashboard')} />
      <NavItem icon={ICONS.table} label={S(lang,'nav_viewer')}    active={route==='viewer'}    onClick={()=>setRoute('viewer')} sub="2,629" />
      <NavItem icon={ICONS.phone} label={S(lang,'nav_mobile')}    active={route==='mobile'}    onClick={()=>setRoute('mobile')} />

      {isAdmin && <>
        <div className="eyebrow" style={{ padding:'14px 10px 4px' }}>{S(lang,'group_admin')}</div>
        <NavItem icon={ICONS.edit}     label={S(lang,'nav_editor')}   active={route==='editor'}   onClick={()=>setRoute('editor')} />
        <NavItem icon={ICONS.settings} label={S(lang,'nav_settings')} active={route==='settings'} onClick={()=>setRoute('settings')} />
      </>}

      <div style={{ flex:1 }} />

      {/* AIO sync status pill */}
      <div className="card" style={{ padding:'11px 12px', display:'flex', alignItems:'center', gap:10, background:'var(--surface-2)' }}>
        <span style={{ width:8, height:8, borderRadius:99, background:'var(--green)', boxShadow:'0 0 0 3px var(--green-ghost)' }} />
        <div style={{ lineHeight:1.25 }}>
          <div style={{ fontSize:12, fontWeight:600 }}>AIO Sync</div>
          <div className="mono" style={{ fontSize:10, color:'var(--text-faint)' }}>{tr(lang,'อัปเดต 14 นาทีที่แล้ว','synced 14m ago')}</div>
        </div>
      </div>
    </aside>
  );
}

function RoleSwitcher({ lang, role, setRole }) {
  const [open, setOpen] = React.useState(false);
  const r = ROLES[role];
  return (
    <div style={{ position:'relative' }}>
      <button className="btn btn-sm" onClick={()=>setOpen(o=>!o)} style={{ background:'var(--surface-1)' }}>
        <span style={{ fontSize:13 }}>{r.icon}</span>
        <span style={{ display:'flex', flexDirection:'column', alignItems:'flex-start', lineHeight:1.1 }}>
          <span style={{ fontSize:9, color:'var(--text-faint)' }}>{S(lang,'viewAs')}</span>
          <span style={{ fontWeight:600, fontSize:12.5 }}>{tr(lang, r.th, r.en)}</span>
        </span>
        <Icon d={ICONS.chevDown} size={14} style={{ color:'var(--text-faint)' }} />
      </button>
      {open && <>
        <div onClick={()=>setOpen(false)} style={{ position:'fixed', inset:0, zIndex:40 }} />
        <div className="card pop-in" style={{ position:'absolute', top:'calc(100% + 6px)', right:0, zIndex:41,
          width:240, padding:6, boxShadow:'var(--shadow-3)', background:'var(--surface-2)' }}>
          <div className="eyebrow" style={{ padding:'8px 10px 6px' }}>{tr(lang,'จำลองสิทธิ์การมองเห็น','Simulate visibility')}</div>
          {Object.values(ROLES).map(opt => (
            <button key={opt.id} onClick={()=>{ setRole(opt.id); setOpen(false); }} style={{
              display:'flex', alignItems:'center', gap:10, width:'100%', padding:'9px 10px',
              borderRadius:8, border:'none', cursor:'pointer', textAlign:'left',
              background: opt.id===role ? 'var(--yellow-ghost)' : 'transparent',
              color: opt.id===role ? 'var(--yellow)' : 'var(--text)', fontFamily:'inherit', fontSize:13,
            }}
            onMouseEnter={e=>{ if(opt.id!==role) e.currentTarget.style.background='var(--surface-3)'; }}
            onMouseLeave={e=>{ if(opt.id!==role) e.currentTarget.style.background='transparent'; }}>
              <span style={{ fontSize:15 }}>{opt.icon}</span>
              <div style={{ flex:1, lineHeight:1.2 }}>
                <div style={{ fontWeight:600 }}>{tr(lang, opt.th, opt.en)}</div>
                <div style={{ fontSize:10.5, color:'var(--text-faint)' }}>{opt.id==='admin'?tr(lang,'เห็นทุกคอลัมน์','All columns'):opt.id==='btire'?tr(lang,'ราคาขายเท่านั้น','Retail only'):opt.id==='dealer'?tr(lang,'รหัส B/A/S','B/A/S code'):tr(lang,'ผสม + CR','Mixed + CR')}</div>
              </div>
              {opt.id===role && <Icon d={ICONS.check} size={15} />}
            </button>
          ))}
        </div>
      </>}
    </div>
  );
}

function Topbar({ lang, setLang, role, setRole, onSearch }) {
  return (
    <header style={{
      height:'var(--topbar-h)', flexShrink:0, position:'sticky', top:0, zIndex:30,
      background:'color-mix(in oklch, var(--bg) 82%, transparent)', backdropFilter:'blur(12px)',
      borderBottom:'1px solid var(--border-soft)',
      display:'flex', alignItems:'center', gap:14, padding:'0 22px',
    }}>
      {/* search */}
      <div style={{ position:'relative', flex:1, maxWidth:440 }}>
        <Icon d={ICONS.search} size={16} style={{ position:'absolute', left:12, top:10, color:'var(--text-faint)' }} />
        <input className="input" placeholder={S(lang,'search_ph')} onClick={onSearch} readOnly
          style={{ paddingLeft:36, paddingRight:64, cursor:'pointer' }} />
        <span className="mono" style={{ position:'absolute', right:10, top:9, fontSize:10, color:'var(--text-faint)',
          border:'1px solid var(--border)', borderRadius:5, padding:'2px 6px' }}>⌘K</span>
      </div>

      <div style={{ flex:1 }} />

      <RoleSwitcher lang={lang} role={role} setRole={setRole} />

      {/* language toggle */}
      <div style={{ display:'flex', background:'var(--surface-1)', borderRadius:'var(--r-md)', padding:3, border:'1px solid var(--border-soft)' }}>
        {['th','en'].map(l => (
          <button key={l} onClick={()=>setLang(l)} style={{
            padding:'5px 11px', borderRadius:7, border:'none', cursor:'pointer', fontFamily:'var(--font-mono)',
            fontSize:11.5, fontWeight:600, letterSpacing:'0.04em',
            background: lang===l ? 'var(--yellow)' : 'transparent',
            color: lang===l ? 'var(--on-yellow)' : 'var(--text-faint)', transition:'all .13s',
          }}>{l.toUpperCase()}</button>
        ))}
      </div>

      <button className="btn btn-icon btn-ghost" style={{ position:'relative' }}>
        <Icon d={ICONS.bell} size={18} />
        <span style={{ position:'absolute', top:6, right:6, width:7, height:7, borderRadius:99, background:'var(--yellow)', border:'1.5px solid var(--bg)' }} />
      </button>

      <div style={{ display:'flex', alignItems:'center', gap:9, paddingLeft:10, borderLeft:'1px solid var(--border-soft)', flexShrink:0 }}>
        <div style={{ width:32, height:32, borderRadius:99, background:'linear-gradient(135deg,var(--surface-3),var(--surface-2))',
          display:'grid', placeItems:'center', fontSize:13, fontWeight:700, color:'var(--yellow)', border:'1px solid var(--border)', flexShrink:0 }}>ชบ</div>
        <div style={{ lineHeight:1.15, whiteSpace:'nowrap' }}>
          <div style={{ fontSize:12.5, fontWeight:600 }}>ชิบะน้อย</div>
          <div className="mono" style={{ fontSize:9.5, color:'var(--text-faint)' }}>{role==='admin'?'ADMIN':'STAFF'}</div>
        </div>
      </div>
    </header>
  );
}

Object.assign(window, { TkcLogo, Sidebar, Topbar, RoleSwitcher, NavItem });
