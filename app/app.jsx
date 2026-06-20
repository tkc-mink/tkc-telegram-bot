/* ============================================================
   app.jsx — root: state, routing, render
   ============================================================ */

function App() {
  const [lang, setLang]   = React.useState(() => localStorage.getItem('tkc_lang') || 'th');
  const [role, setRole]   = React.useState(() => localStorage.getItem('tkc_role') || 'admin');
  const [route, setRoute] = React.useState(() => localStorage.getItem('tkc_route') || 'dashboard');

  React.useEffect(()=>{ localStorage.setItem('tkc_lang', lang); document.documentElement.lang = lang; }, [lang]);
  React.useEffect(()=>{ localStorage.setItem('tkc_role', role); }, [role]);
  React.useEffect(()=>{ localStorage.setItem('tkc_route', route); }, [route]);

  // non-admin roles can't reach editor/settings — bounce to viewer
  React.useEffect(()=>{
    if (role!=='admin' && (route==='editor'||route==='settings')) setRoute('viewer');
  }, [role, route]);

  const screen = (() => {
    switch (route) {
      case 'dashboard': return <Dashboard lang={lang} setRoute={setRoute} role={role} />;
      case 'viewer':    return <Viewer lang={lang} role={role} />;
      case 'editor':    return <Editor lang={lang} />;
      case 'settings':  return <Settings lang={lang} />;
      case 'mobile':    return <MobileViewer lang={lang} />;
      default:          return <Dashboard lang={lang} setRoute={setRoute} role={role} />;
    }
  })();

  return (
    <div style={{ display:'flex', minHeight:'100vh' }}>
      <Sidebar lang={lang} route={route} setRoute={setRoute} role={role} />
      <div style={{ flex:1, minWidth:0, display:'flex', flexDirection:'column' }}>
        <Topbar lang={lang} setLang={setLang} role={role} setRole={setRole} onSearch={()=>setRoute('viewer')} />
        <main style={{ flex:1, minWidth:0 }} key={route+role+lang}>{screen}</main>
      </div>
      <Chatbot lang={lang} role={role} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
