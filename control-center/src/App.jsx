import { useMemo, useState } from 'react';
import { Bot, Code2, Cpu, Gauge, MessageSquare, Settings, TerminalSquare, WalletCards } from 'lucide-react';
import { DEFAULT_LOCALE, localeCatalog } from './i18n.js';
import './styles.css';

const agents = [
  { name: 'Codex', roleKey: 'codex', state: 'ready' },
  { name: 'GPT', roleKey: 'gpt', state: 'ready' },
  { name: 'Claude', roleKey: 'claude', state: 'standby' },
  { name: 'Hermes', roleKey: 'hermes', state: 'ready' }
];

const nav = [
  ['chat', MessageSquare],
  ['agents', Bot],
  ['terminal', TerminalSquare],
  ['aris', Cpu],
  ['usage', WalletCards],
  ['settings', Settings]
];

function App() {
  const [tab, setTab] = useState('chat');
  const [text, setText] = useState('');
  const [locale, setLocale] = useState(DEFAULT_LOCALE);
  const t = localeCatalog[locale] || localeCatalog.ru;
  const online = useMemo(() => agents.filter(a => a.state === 'ready').length, []);
  return <div className="app-shell" lang={locale}>
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

      <section className="dashboard">
        <div className="hero-card">
          <div className="hero-copy"><span className="pill">{t.autoRouting}</span><h2>{t.hero}</h2>
          <p>Система сама выбирает сильнейшего доступного агента и переключается на резерв без потери задачи.</p></div>
          <Gauge size={64}/>
        </div>
        <div className="grid">
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
            <div className="panel-head"><div><span className="kicker">{t.codeWorkspace}</span><h3>Codex Terminal</h3></div><TerminalSquare size={20}/></div>
            <pre><span>$</span> codex{"\n"}<em>{t.workspaceReady}</em>{"\n"}<span>›</span> {t.waitingTask}</pre>
          </section>
        </div>
      </section>

      <select value={locale} onChange={e => setLocale(e.target.value)} aria-label="Язык">
        <option value="ru">Русский</option>
        <option value="en">English</option>
      </select>
    </main>
  </div>;
}

export default App;
