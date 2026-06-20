/* ============================================================
   settings.jsx — Settings Hub (Admin)
   ============================================================ */

const SETTINGS_USERS = [
  { name:'ชิบะน้อย', role:'admin', th:'ผู้ดูแลระบบ', en:'Admin', devices:3, last:'ออนไลน์', online:true, groups:['Admin'] },
  { name:'สมชาย ก.', role:'btire', th:'เซลล์ยางใหญ่', en:'B-Tire Sales', devices:2, last:'5 นาที', online:true, groups:['เซลล์ยางใหญ่'] },
  { name:'วิภา ส.', role:'dealer', th:'เซลล์ดูแลร้านค้า', en:'Dealer Sales', devices:1, last:'1 ชม.', online:false, groups:['เซลล์ดูแลร้านค้า'] },
  { name:'หน้าร้าน (Shared)', role:'counter', th:'พนักงานหน้าร้าน', en:'Counter', devices:4, last:'ออนไลน์', online:true, groups:['พนักงานหน้าร้าน'], shared:true },
];

function SettingsRow({ label, desc, children }) {
  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:20, padding:'14px 0', borderBottom:'1px solid var(--border-soft)' }}>
      <div style={{ minWidth:0 }}>
        <div style={{ fontSize:13.5, fontWeight:500 }}>{label}</div>
        {desc && <div className="faint" style={{ fontSize:12, marginTop:2 }}>{desc}</div>}
      </div>
      <div style={{ flexShrink:0 }}>{children}</div>
    </div>
  );
}

function Toggle({ on, onClick }) {
  return (
    <span onClick={onClick} style={{ width:38, height:21, borderRadius:99, background:on?'var(--yellow)':'var(--surface-3)', position:'relative', cursor:'pointer', display:'inline-block', transition:'.15s' }}>
      <span style={{ position:'absolute', top:2.5, left:on?19:2.5, width:16, height:16, borderRadius:99, background:'#fff', transition:'.15s' }} />
    </span>
  );
}

function UsersSection({ lang }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
        <h3 style={{ fontSize:15, fontWeight:600 }}>{tr(lang,'ผู้ใช้และกลุ่มสิทธิ์','Users & Groups')}</h3>
        <button className="btn btn-primary btn-sm"><Icon d={ICONS.plus} size={15}/> {tr(lang,'เพิ่มผู้ใช้','Add user')}</button>
      </div>
      <div className="card" style={{ overflow:'hidden' }}>
        {SETTINGS_USERS.map((u,i)=>{
          const r = ROLES[u.role];
          return (
            <div key={i} style={{ display:'flex', alignItems:'center', gap:14, padding:'14px 16px', borderBottom: i<SETTINGS_USERS.length-1?'1px solid var(--border-soft)':'none' }}>
              <div style={{ width:38, height:38, borderRadius:10, background:'var(--surface-2)', display:'grid', placeItems:'center', fontSize:16 }}>{r.icon}</div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                  <span style={{ fontWeight:600, fontSize:13.5 }}>{u.name}</span>
                  {u.shared && <span className="badge badge-blue">SHARED</span>}
                </div>
                <div className="faint" style={{ fontSize:12, marginTop:1 }}>{tr(lang,u.th,u.en)} · {u.groups.join(', ')}</div>
              </div>
              <div className="mono" style={{ fontSize:11.5, color:'var(--text-faint)', textAlign:'right' }}>
                <div>{u.devices} {tr(lang,'อุปกรณ์','devices')}</div>
                <div style={{ display:'flex', alignItems:'center', gap:5, justifyContent:'flex-end', marginTop:2 }}>
                  <span style={{ width:6, height:6, borderRadius:99, background:u.online?'var(--green)':'var(--text-faint)' }} />
                  {u.online?tr(lang,'ออนไลน์','online'):u.last}
                </div>
              </div>
              <button className="btn btn-icon btn-ghost btn-sm"><Icon d={ICONS.chevron} size={16}/></button>
            </div>
          );
        })}
      </div>
      {/* permission matrix */}
      <h3 style={{ fontSize:15, fontWeight:600, marginTop:18, marginBottom:8 }}>{tr(lang,'เมทริกซ์สิทธิ์ตามคอลัมน์ (Pricelist)','Column permission matrix (Pricelist)')}</h3>
      <div className="card" style={{ overflow:'auto' }}>
        <table className="pl">
          <thead><tr><th>{tr(lang,'คอลัมน์','Column')}</th>{Object.values(ROLES).map(r=><th key={r.id} style={{textAlign:'center'}}>{r.icon} {tr(lang,r.th,r.en)}</th>)}</tr></thead>
          <tbody>
            {[['ทุน (จริง)','costReal'],['ทุน รหัสลับ','costCode'],['ราคาขาย','retail'],['B/A/S รหัสลับ','basCode'],['Margin','margin'],['CR toggle','crToggle'],['แก้ไขราคา','edit']].map(([lbl,key])=>(
              <tr key={key} style={{cursor:'default'}}>
                <td style={{fontWeight:500}}>{lbl}</td>
                {Object.values(ROLES).map(r=>(
                  <td key={r.id} style={{textAlign:'center'}}>
                    {COL_PERMS[r.id][key] ? <Icon d={ICONS.check} size={15} style={{color:'var(--green)'}}/> : <span className="faint">·</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CipherSection({ lang }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div>
        <h3 style={{ fontSize:15, fontWeight:600 }}>{tr(lang,'รหัสลับ (Cipher) — Pricelist','Cipher — Pricelist')}</h3>
        <p className="dim" style={{ fontSize:12.5, marginTop:4 }}>{tr(lang,'เปลี่ยน cipher กระทบเฉพาะการแสดงผล ไม่กระทบข้อมูลจริงในฐานข้อมูล','Changing cipher affects display only — never the stored numbers')}</p>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
        {[['Cipher #1 — ทุน (Cost)','var(--yellow)',CIPHER1,tr(lang,'เฉพาะแอดมิน','Admin only')],['Cipher #2 — ราคาส่ง (Wholesale)','var(--blue)',CIPHER2,tr(lang,'เซลล์ขึ้นไป','Sales & up')]].map(([nm,col,ciph,scope])=>(
          <div key={nm} className="card" style={{ padding:'18px' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
              <div style={{ fontSize:13.5, fontWeight:600, color:col }}>{nm}</div>
              <span className="badge" style={{background:'var(--surface-2)', color:'var(--text-faint)'}}>{scope}</span>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(10,1fr)', gap:5 }}>
              {ciph.map((ch,i)=>(
                <div key={i} style={{ textAlign:'center' }}>
                  <div className="mono" style={{ fontSize:11, color:'var(--text-faint)', marginBottom:4 }}>{i}</div>
                  <div className="mono" style={{ fontSize:16, fontWeight:700, color:col, padding:'8px 0', background:'var(--surface-2)', borderRadius:7, border:'1px solid var(--border-soft)' }}>{ch}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop:14, padding:'10px 12px', background:'var(--surface-2)', borderRadius:9, fontSize:12 }}>
              <span className="faint">{tr(lang,'ตัวอย่าง','Example')}: </span>
              <span className="mono">{col===CIPHER1?'1818':'2500'}</span> → <span className="mono" style={{fontWeight:700, color:col, letterSpacing:'0.1em'}}>{col===CIPHER1?cost2code(1818):whole2code(2500)}</span>
            </div>
          </div>
        ))}
      </div>
      <div style={{ display:'flex', gap:10 }}>
        <button className="btn"><Icon d={ICONS.download} size={15}/> {tr(lang,'ดาวน์โหลดการ์ดสำรอง (PDF)','Download backup card (PDF)')}</button>
        <button className="btn"><Icon d={ICONS.print} size={15}/> {tr(lang,'พิมพ์การ์ดสำรอง','Print backup card')}</button>
        <button className="btn" style={{ marginLeft:'auto', color:'var(--red)', borderColor:'var(--red-ghost)' }}><Icon d={ICONS.key} size={15}/> {tr(lang,'เปลี่ยน Cipher (ต้องระบุเหตุผล)','Change cipher (reason required)')}</button>
      </div>
    </div>
  );
}

function SecuritySection({ lang }) {
  const [auto, setAuto] = React.useState({admin:60, btire:30, dealer:30, counter:15});
  const opts = [5,10,15,30,60,120];
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:18 }}>
      <div className="card" style={{ padding:'4px 18px' }}>
        <div style={{ padding:'14px 0 4px', fontSize:14, fontWeight:600 }}>🔒 {tr(lang,'นโยบายรหัสผ่าน','Password policy')}</div>
        <SettingsRow label={tr(lang,'ความยาวขั้นต่ำ','Min length')} desc={tr(lang,'จำนวนตัวอักษร','characters')}><span className="chip">8</span></SettingsRow>
        <SettingsRow label={tr(lang,'ห้ามซ้ำ 3 รหัสล่าสุด','No reuse of last 3')}><Toggle on={true}/></SettingsRow>
        <SettingsRow label={tr(lang,'ล็อกหลังพิมพ์ผิด 5 ครั้ง / 5 นาที','Lockout after 5 fails / 5 min')}><Toggle on={true}/></SettingsRow>
      </div>
      <div className="card" style={{ padding:'4px 18px' }}>
        <div style={{ padding:'14px 0 4px', fontSize:14, fontWeight:600 }}>⏰ {tr(lang,'ออกจากระบบอัตโนมัติ (ตามบทบาท)','Auto-logout per role')}</div>
        {Object.values(ROLES).map((r,i)=>(
          <SettingsRow key={r.id} label={<span>{r.icon} {tr(lang,r.th,r.en)}</span>}>
            <div style={{ display:'flex', gap:4 }}>
              {opts.map(o=>(
                <button key={o} onClick={()=>setAuto(a=>({...a,[r.id]:o}))} style={{ padding:'4px 9px', borderRadius:6, border:'1px solid var(--border-soft)', cursor:'pointer', fontFamily:'var(--font-mono)', fontSize:11.5, fontWeight:600,
                  background: auto[r.id]===o?'var(--yellow)':'var(--surface-2)', color: auto[r.id]===o?'var(--on-yellow)':'var(--text-faint)' }}>{o}</button>
              ))}
              <span className="faint" style={{ fontSize:11, alignSelf:'center', marginLeft:4 }}>{tr(lang,'นาที','min')}</span>
            </div>
          </SettingsRow>
        ))}
      </div>
    </div>
  );
}

function HealthSection({ lang }) {
  const sparks = [
    { nm:'Spark #1 · Web/DB', metric:'CPU 23% · RAM 45/128GB', ok:true },
    { nm:'Spark #2 · AI', metric:'GPU 12%', ok:true },
    { nm:'Spark #3 · Training', metric:tr(lang,'ว่าง','Idle'), ok:true },
    { nm:'Spark #4 · Vision', metric:'CPU 5%', ok:true },
    { nm:'Mac Mini M4 · Agent', metric:tr(lang,'พอร์ช ออนไลน์','พอร์ช online'), ok:true },
  ];
  const svc = [
    { nm:'PostgreSQL 16', v:'7.2 GB', ok:true },{ nm:'Redis 7', v:'212 MB', ok:true },
    { nm:'AIO MySQL Sync', v:tr(lang,'14 นาที','14m'), ok:true },{ nm:'Synology NAS', v:'1.8 / 4 TB', ok:true },
    { nm:'Cloudflare Tunnel', v:tr(lang,'เชื่อมต่อ','connected'), ok:true },{ nm:'Telegram Bot', v:tr(lang,'พร้อม','ready'), ok:true },
  ];
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:18 }}>
      <div>
        <h3 style={{ fontSize:15, fontWeight:600, marginBottom:10 }}>🖥️ {tr(lang,'หน่วยประมวลผล','Compute')}</h3>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
          {sparks.map((s,i)=>(
            <div key={i} className="card" style={{ padding:'13px 16px', display:'flex', alignItems:'center', gap:11 }}>
              <Icon d={ICONS.cpu} size={18} style={{ color:'var(--text-faint)' }}/>
              <div style={{ flex:1 }}>
                <div style={{ fontSize:13, fontWeight:500 }}>{s.nm}</div>
                <div className="mono faint" style={{ fontSize:11 }}>{s.metric}</div>
              </div>
              <span style={{ width:8, height:8, borderRadius:99, background:'var(--green)', boxShadow:'0 0 0 3px var(--green-ghost)' }} />
            </div>
          ))}
        </div>
      </div>
      <div>
        <h3 style={{ fontSize:15, fontWeight:600, marginBottom:10 }}>🔄 {tr(lang,'บริการ & พื้นที่จัดเก็บ','Services & storage')}</h3>
        <div className="card" style={{ overflow:'hidden' }}>
          {svc.map((s,i)=>(
            <div key={i} style={{ display:'flex', alignItems:'center', gap:11, padding:'12px 16px', borderBottom: i<svc.length-1?'1px solid var(--border-soft)':'none' }}>
              <span style={{ width:8, height:8, borderRadius:99, background:'var(--green)' }} />
              <span style={{ flex:1, fontSize:13, fontWeight:500 }}>{s.nm}</span>
              <span className="mono faint" style={{ fontSize:12 }}>{s.v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Settings({ lang }) {
  const [tab, setTab] = React.useState('users');
  const tabs = [
    { k:'users', icon:ICONS.user, th:'ผู้ใช้ & กลุ่ม', en:'Users & Groups' },
    { k:'cipher', icon:ICONS.key, th:'รหัสลับ', en:'Cipher' },
    { k:'security', icon:ICONS.shield, th:'ความปลอดภัย', en:'Security' },
    { k:'health', icon:ICONS.activity, th:'สุขภาพระบบ', en:'System Health' },
  ];
  return (
    <div className="screen-in" style={{ display:'flex', height:'calc(100vh - var(--topbar-h))' }}>
      {/* settings sub-nav */}
      <div style={{ width:210, flexShrink:0, borderRight:'1px solid var(--border-soft)', padding:'20px 12px', background:'var(--surface-1)' }}>
        <div className="eyebrow" style={{ padding:'0 10px 12px' }}>{tr(lang,'ตั้งค่าระบบ','Settings Hub')}</div>
        {tabs.map(t=>(
          <NavItem key={t.k} icon={t.icon} label={tr(lang,t.th,t.en)} active={tab===t.k} onClick={()=>setTab(t.k)} />
        ))}
        <div className="eyebrow" style={{ padding:'18px 10px 8px' }}>{tr(lang,'อื่นๆ','More')}</div>
        {[['📱',tr(lang,'อุปกรณ์','Devices')],['🔔',tr(lang,'การแจ้งเตือน','Notifications')],['📋',tr(lang,'Audit Log','Audit Log')],['📡','NAS'],['🤖',tr(lang,'AI Agents','AI Agents')],['🎨',tr(lang,'แบรนด์','Branding')]].map(([ic,lb],i)=>(
          <div key={i} style={{ display:'flex', alignItems:'center', gap:11, padding:'9px 12px', color:'var(--text-faint)', fontSize:13 }}>
            <span style={{ width:18, textAlign:'center' }}>{ic}</span>{lb}
          </div>
        ))}
      </div>
      <div style={{ flex:1, overflow:'auto', padding:'24px 30px', maxWidth:900 }}>
        {tab==='users' && <UsersSection lang={lang}/>}
        {tab==='cipher' && <CipherSection lang={lang}/>}
        {tab==='security' && <SecuritySection lang={lang}/>}
        {tab==='health' && <HealthSection lang={lang}/>}
      </div>
    </div>
  );
}

Object.assign(window, { Settings });
