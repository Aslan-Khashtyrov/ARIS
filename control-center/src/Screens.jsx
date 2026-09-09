import { useState } from 'react';
import { Bot, Code2, Gauge, Globe2, TerminalSquare } from 'lucide-react';
import { Browser } from '@capacitor/browser';
import { supportedLanguages } from './i18n.js';
import { agentRegistry, routingPolicy } from './agents.js';
import { isAllowedServiceUrl, services } from './services.js';
import { checkBridge, normalizeBridgeUrl } from './localBridge.js';


export function HomeScreen({ t, state, configured, onNavigate }) {
  const completed = state.tasks.filter(task => task.done).length;
  return <section className="dashboard">
    <div className="hero-card home-hero"><div className="hero-copy"><span className="pill">{t.homeKicker}</span><h2>{t.homeTitle}</h2><p>{t.homeDescription}</p></div><div className="shield-mark">P1</div></div>
    <div className="metric-grid">
      <button className="panel metric-card" onClick={() => onNavigate('agents')}><span>{t.homeAgents}</span><b>{configured}</b><small>{t.homeAgentsHint}</small></button>
      <button className="panel metric-card" onClick={() => onNavigate('aris')}><span>{t.homeAris}</span><b>{t.homeSafe}</b><small>real_trading=false</small></button>
      <button className="panel metric-card" onClick={() => onNavigate('tasks')}><span>{t.homeTasks}</span><b>{completed}/{state.tasks.length}</b><small>{t.homeTasksHint}</small></button>
      <button className="panel metric-card" onClick={() => onNavigate('terminal')}><span>{t.homeBridge}</span><b>{state.localBridgeEnabled ? t.homeAllowed : t.homeDisabled}</b><small>{t.homeBridgeHint}</small></button>
    </div>
    <div className="panel quick-panel"><div><span className="kicker">{t.homeQuick}</span><h3>{t.homeQuickTitle}</h3></div><div className="quick-actions"><button onClick={() => onNavigate('chat')}>{t.homeOpenChat}</button><button onClick={() => onNavigate('services')}>{t.homeOpenServices}</button><button onClick={() => onNavigate('settings')}>{t.homeOpenSettings}</button></div></div>
  </section>;
}

export function ChatScreen({ t, text, setText, history, onSend, onClear }) {
  return <section className="dashboard">
    <div className="hero-card"><div className="hero-copy"><span className="pill">{t.autoRouting}</span><h2>{t.hero}</h2><p>{t.heroDescription}</p></div><Gauge size={64}/></div>
    <div className="grid"><section className="panel chat-panel">
      <div className="panel-head"><div><span className="kicker">{t.unifiedChat}</span><h3>{t.mainChat}</h3></div><Code2 size={20}/></div>
      <div className="messages">{history.length ? history.map((item, i) => <div className={'bubble ' + item.kind} key={i}><b>{item.author}</b><span>{item.text}</span></div>) : <div className="bubble system"><span>{t.readyMessage}</span></div>}</div>
      <div className="composer"><input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && onSend()} placeholder={t.inputPlaceholder}/><button onClick={onSend}>{t.send}</button><button className="secondary" onClick={onClear}>{t.clear}</button></div>
    </section>
    <AgentsCompact t={t}/><TerminalCompact t={t}/></div>
  </section>;
}

function AgentsCompact({ t }) {
  return <section className="panel agents-panel"><div className="panel-head"><div><span className="kicker">{t.router}</span><h3>{t.agents}</h3></div><Bot size={20}/></div><div className="agent-list">
    {agentRegistry.map(agent => <div className="agent-row" key={agent.id}><div className="rank">{agent.priority}</div><div className="agent-meta"><b>{agent.name}</b><span>{t.roles[agent.roleKey]}</span></div><div className={'agent-state ' + agent.mode}>{t.modes[agent.mode]}</div></div>)}
  </div></section>;
}function TerminalCompact({ t }) {
  return <section className="panel terminal-panel"><div className="panel-head"><div><span className="kicker">{t.codeWorkspace}</span><h3>{t.terminalTitle}</h3></div><TerminalSquare size={20}/></div><pre><span>$</span> bridge status{"\n"}<em>{t.workspaceReady}</em>{"\n"}<span>›</span> {t.waitingTask}</pre></section>;
}

export function AgentsScreen({ t }) {
  return <section className="services-view"><Header t={t} id="agents"/><div className="panel"><div className="agent-list">
    {agentRegistry.map(agent => <div className="agent-row large" key={agent.id}><div className="rank">{agent.priority}</div><div className="agent-meta"><b>{agent.name}</b><span>{t.roles[agent.roleKey]}</span></div><div className={'agent-state ' + agent.mode}>{t.modes[agent.mode]}</div></div>)}
  </div></div><div className="route-grid">
    {Object.entries(routingPolicy).map(([key, chain]) => <div className="panel route-card" key={key}><b>{t.routeLabels[key]}</b><span>{chain.join(' → ')}</span></div>)}
  </div></section>;
}

export function TerminalScreen({ t, state, updateState }) {
  const [bridgeNotice, setBridgeNotice] = useState('');
  async function testBridge() {
    if (!normalizeBridgeUrl(state.bridgeUrl)) return setBridgeNotice(t.bridgeInvalid);
    setBridgeNotice(t.bridgeChecking);
    const result = await checkBridge(state.bridgeUrl);
    setBridgeNotice(result.ok ? t.bridgeOk : t.bridgeOffline);
  }
  return <section className="services-view"><Header t={t} id="terminal"/><div className="panel form-panel">
    <label>{t.bridgeAddress}<input value={state.bridgeUrl} onChange={e => updateState({ bridgeUrl: e.target.value })}/></label>
    <label className="switch-line"><input type="checkbox" checked={state.localBridgeEnabled} onChange={e => updateState({ localBridgeEnabled: e.target.checked })}/><span>{t.bridgeEnable}</span></label>
    <button className="action-button" onClick={testBridge}>{t.checkBridge}</button>
    {bridgeNotice && <div className="notice">{bridgeNotice}</div>}
    <div className="notice">{t.bridgeWarning}</div><pre className="terminal-preview">$ bridge status{"\n"}{state.localBridgeEnabled ? t.bridgeAllowedUnchecked : t.bridgeDisabled}</pre>
  </div></section>;
}export function ArisScreen({ t }) {
  return <section className="services-view"><Header t={t} id="aris"/><div className="status-grid"><div className="panel status-card good"><b>{t.arisPaper}</b><span>ARIS</span></div><div className="panel status-card safe"><b>{t.arisTrading}</b><span>real_trading=false</span></div></div></section>;
}

export function UsageScreen({ t, state, updateState }) {
  const budgets = state.providerBudgets;
  const setBudget = (key, value) => updateState({ providerBudgets: { ...budgets, [key]: Number(value) || 0 } });
  return <section className="services-view"><Header t={t} id="usage"/><div className="budget-grid">
    <Budget t={t} label={t.usageMonthly} value={state.monthlyBudget} onChange={v => updateState({ monthlyBudget: Number(v) || 0 })}/>
    <Budget t={t} label={t.usageOpenAI} value={budgets.openai} onChange={v => setBudget('openai', v)}/>
    <Budget t={t} label={t.usageAnthropic} value={budgets.anthropic} onChange={v => setBudget('anthropic', v)}/>
    <Budget t={t} label={t.usageOpenRouter} value={budgets.openrouter} onChange={v => setBudget('openrouter', v)}/>
  </div><div className="notice">{t.localBudgetNote}</div></section>;
}

function Budget({ t, label, value, onChange }) {
  return <label className="panel budget-card"><span>{label}</span><input type="number" min="0" step="1" value={value} onChange={e => onChange(e.target.value)}/><small>{t.budgetUnit}</small></label>;
}

export function SettingsScreen({ t, state, updateState }) {
  return <section className="services-view"><Header t={t} id="settings"/><div className="panel form-panel">
    <label className="switch-line"><input type="checkbox" checked={true} disabled/><span>{t.safeModeLocked}</span></label>
    <div className="setting-row language-row"><div><b>{t.languageTitle}</b><small>{t.languageHint}</small></div><select value={state.locale} onChange={e => updateState({ locale: e.target.value })}>{supportedLanguages.map(language => <option value={language.id} key={language.id}>{language.label}</option>)}</select></div>
    <div className="setting-row"><b>{t.realTradesLabel}</b><span>{t.realTradesValue}</span></div>
    <div className="setting-row"><b>{t.secretsLabel}</b><span>{t.secretsValue}</span></div>
    <div className="setting-row"><b>{t.versionLabel}</b><span>{t.versionValue}</span></div>
  </div></section>;
}export function ServicesScreen({ t, notice, setNotice }) {
  async function openService(service) {
    if (!isAllowedServiceUrl(service.url)) return setNotice(t.blockedUrl);
    setNotice(t.openingService(service.name));
    try { await Browser.open({ url: service.url, presentationStyle: 'fullscreen' }); }
    catch { setNotice(t.openFailed); }
  }
  return <section className="services-view"><div className="section-title"><span className="kicker">{t.servicesKicker}</span><h2>{t.servicesTitle}</h2><p>{t.servicesDescription}</p></div><div className="service-grid">
    {services.map(service => <button className="service-card" key={service.id} onClick={() => openService(service)}><Globe2 size={28}/><div><b>{service.name}</b><span>{t.serviceDescriptions[service.id]}</span></div><small>{service.host}</small></button>)}
  </div>{notice && <div className="notice">{notice}</div>}</section>;
}

function Header({ t, id }) {
  const screen = t.screens[id];
  return <div className="section-title"><span className="kicker">{screen.kicker}</span><h2>{screen.title}</h2><p>{screen.description}</p></div>;
}

export function TasksScreen({ t, state, addTask, toggleTask, deleteTask }) {
  const [draft, setDraft] = useState('');
  function submit() { if (!draft.trim()) return; addTask(draft.trim()); setDraft(''); }
  return <section className="services-view">
    <div className="section-title"><span className="kicker">{t.tasksKicker}</span><h2>{t.tasksTitle}</h2><p>{t.tasksDescription}</p></div>
    <div className="panel task-panel"><div className="composer"><input value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} placeholder={t.taskPlaceholder}/><button onClick={submit}>{t.addTask}</button></div>
    <div className="task-list">{state.tasks.length ? state.tasks.map(task => <div className={'task-row ' + (task.done ? 'done' : '')} key={task.id}><label><input type="checkbox" checked={task.done} onChange={() => toggleTask(task.id)}/><span>{task.text}</span></label><button className="secondary small" onClick={() => deleteTask(task.id)}>{t.delete}</button></div>) : <div className="empty-state">{t.noTasks}</div>}</div></div>
  </section>;
}

export function LogsScreen({ t, state }) {
  return <section className="services-view">
    <div className="section-title"><span className="kicker">{t.logsKicker}</span><h2>{t.logsTitle}</h2><p>{t.logsDescription}</p></div>
    <div className="panel log-list">{state.logs.length ? [...state.logs].reverse().map(item => <div className="log-row" key={item.id}><span>{item.time}</span><b>{item.text}</b></div>) : <div className="empty-state">{t.noLogs}</div>}</div>
  </section>;
}