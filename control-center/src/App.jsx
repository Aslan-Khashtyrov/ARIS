import { useMemo, useState } from 'react';
import { Bot, Code2, Cpu, Gauge, MessageSquare, Settings, TerminalSquare, WalletCards } from 'lucide-react';
import './styles.css';

const agents = [
  { name: 'Codex', role: 'Code & terminal', state: 'ready' },
  { name: 'GPT', role: 'Reasoning & planning', state: 'ready' },
  { name: 'Claude', role: 'Review & long context', state: 'standby' },
  { name: 'Hermes', role: 'Fallback operator', state: 'ready' }
];

const nav = [
  ['chat', MessageSquare, 'Chat'],
  ['agents', Bot, 'Agents'],
  ['terminal', TerminalSquare, 'Terminal'],
  ['aris', Cpu, 'ARIS'],
  ['usage', WalletCards, 'Usage'],
  ['settings', Settings, 'Settings']
];
function App() {
  const [tab, setTab] = useState('chat');
  const [text, setText] = useState('');
  const online = useMemo(() => agents.filter(a => a.state === 'ready').length, []);

  return <div className="app-shell">
    <aside className="rail">
      <div className="brand">P1</div>
      {nav.map(([id, Icon, label]) => <button key={id} className={tab === id ? 'nav active' : 'nav'} onClick={() => setTab(id)}>
        <Icon size={20}/><span>{label}</span>
      </button>)}
    </aside>

    <main className="main">
      <header className="topbar">
        <div><div className="eyebrow">PERSONAL AI SYSTEM</div><h1>Project One</h1></div>
        <div className="status"><span className="dot"/> {online} agents online</div>
      </header>

      <section className="dashboard">
        <div className="hero-card">
          <div className="hero-copy"><span className="pill">AUTO ROUTING</span><h2>One chat. Best available intelligence.</h2>
          <p>Система сама выбирает сильнейшего доступного агента и переключается на резерв без потери задачи.</p></div>
          <Gauge size={64}/>
        </div>
        <div className="grid">
          <section className="panel chat-panel">
            <div className="panel-head"><div><span className="kicker">UNIFIED CHAT</span><h3>Главный чат</h3></div><Code2 size={20}/></div>
            <div className="messages">
              <div className="bubble system">Готов. Напиши задачу — я выберу подходящего агента.</div>
              <div className="bubble agent"><b>Codex</b><span>Основной агент для разработки сейчас доступен.</span></div>
            </div>
            <div className="composer"><input value={text} onChange={e => setText(e.target.value)} placeholder="Напиши задачу одному ИИ..."/><button>Отправить</button></div>
          </section>

          <section className="panel agents-panel">
            <div className="panel-head"><div><span className="kicker">ROUTER</span><h3>Агенты</h3></div><Bot size={20}/></div>
            <div className="agent-list">{agents.map((agent, i) => <div className="agent-row" key={agent.name}>
              <div className="rank">{i + 1}</div><div className="agent-meta"><b>{agent.name}</b><span>{agent.role}</span></div>
              <div className={'agent-state ' + agent.state}>{agent.state}</div>
            </div>)}</div>
          </section>

          <section className="panel terminal-panel">
            <div className="panel-head"><div><span className="kicker">CODE WORKSPACE</span><h3>Codex Terminal</h3></div><TerminalSquare size={20}/></div>
            <pre><span>$</span> codex{"\n"}<em>Project workspace ready.</em>{"\n"}<span>›</span> waiting for task_</pre>
          </section>
        </div>
      </section>
    </main>
  </div>;
}

export default App;