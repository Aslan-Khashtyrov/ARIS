import { useMemo, useState } from 'react';
import { Browser } from '@capacitor/browser';
import { Bot, Code2, Cpu, Gauge, Globe2, MessageSquare, Settings, TerminalSquare, WalletCards } from 'lucide-react';
import { russianSource as t } from './i18n.js';
import { isAllowedServiceUrl, services } from './services.js';
import './styles.css';

const agents = [
  { name: 'Codex', roleKey: 'codex', state: 'ready' },
  { name: 'GPT', roleKey: 'gpt', state: 'ready' },
  { name: 'Claude', roleKey: 'claude', state: 'standby' },
  { name: 'Hermes', roleKey: 'hermes', state: 'ready' },
];

const nav = [
  ['chat', MessageSquare], ['agents', Bot], ['terminal', TerminalSquare],
  ['services', Globe2], ['aris', Cpu], ['usage', WalletCards], ['settings', Settings],
];

function PlaceholderScreen({ id }) {
  const screen = t.screens[id];
  return <section className="services-view">
    <div className="section-title"><span className="kicker">{screen.kicker}</span><h2>{screen.title}</h2><p>{screen.description}</p></div>
    <div className="panel placeholder-panel"><p>{t.screenNotReady}</p><small>{t.nativeLanguage}</small></div>
  </section>;
}

function App() {
  const [tab, setTab] = useState('chat');
  const [text, setText] = useState('');
  const [notice, setNotice] = useState('');
  const online = useMemo(() => agents.filter(a => a.state === 'ready').length, []);
  async function openService(service) {
    if (!isAllowedServiceUrl(service.url)) {
      setNotice(t.blockedUrl);
      return;
    }
    setNotice(t.openingService(service.name));
    try {
      await Browser.open({ url: service.url, presentationStyle: 'fullscreen' });
    } catch {
      setNotice(t.openFailed);
    }
  }

  function renderServices() {
    return <section className="services-view">
      <div className="section-title"><span className="kicker">{t.servicesKicker}</span><h2>{t.servicesTitle}</h2><p>{t.servicesDescription}</p></div>
      <div className="service-grid">
        {services.map(service => <button className="service-card" key={service.id} onClick={() => openService(service)}>
          <Globe2 size={28}/><div><b>{service.name}</b><span>{service.description}</span></div><small>{service.host}</small>
        </button>)}
      </div>
      {notice && <div className="notice">{notice}</div>}
    </section>;
  }

  function renderHome() {
    return <section className="dashboard">
      <div className="hero-card">
        <div className="hero-copy"><span className="pill">{t.autoRouting}</span><h2>{t.hero}</h2><p>{t.heroDescription}</p></div>
        <Gauge size={64}/>
      </div>      <div className="grid">
        <section className="panel chat-panel">
          <div className="panel-head"><div><span className="kicker">{t.unifiedChat}</span><h3>{t.mainChat}</h3></div><Code2 size={20}/></div>
          <div className="messages">
            <div className="bubble system">{t.readyMessage}</div>
            <div className="bubble agent"><b>Codex</b><span>{t.codexReady}</span></div>
          </div>
          <div className="composer"><input value={text} onChange={e => setText(e.target.value)} placeholder={t.inputPlaceholder}/><button>{t.send}</button></div>
        </section>
        <section className="panel agents-panel">
          <div className="panel-head"><div><span className="kicker">{t.router}</span><h3>{t.agents}</h3></div><Bot size={20}/></div>
          <div className="agent-list">{agents.map((agent, i) => <div className="agent-row" key={agent.name}>
            <div className="rank">{i + 1}</div><div className="agent-meta"><b>{agent.name}</b><span>{t.roles[agent.roleKey]}</span></div>
            <div className={'agent-state ' + agent.state}>{t.states[agent.state]}</div>
          </div>)}</div>
        </section>
        <section className="panel terminal-panel">
          <div className="panel-head"><div><span className="kicker">{t.codeWorkspace}</span><h3>{t.terminalTitle}</h3></div><TerminalSquare size={20}/></div>
          <pre><span>$</span> codex{"\n"}<em>{t.workspaceReady}</em>{"\n"}<span>›</span> {t.waitingTask}</pre>
        </section>
      </div>
    </section>;
  }

  const content = tab === 'chat' ? renderHome() : tab === 'services' ? renderServices() : <PlaceholderScreen id={tab}/>;
  return <div className="app-shell" lang="ru">
    <aside className="rail">
      <div className="brand">P1</div>
      {nav.map(([id, Icon]) => <button key={id} className={tab === id ? 'nav active' : 'nav'} onClick={() => setTab(id)}>
        <Icon size={20}/><span>{t.nav[id]}</span>
      </button>)}
    </aside>
    <main className="main">
      <header className="topbar">
        <div><div className="eyebrow">{t.appSystem}</div><h1>Project One</h1></div>
        <div className="status"><span className="dot"/> {online} {t.agentsOnline}</div>
      </header>
      {content}
    </main>
  </div>;
}

export default App;
