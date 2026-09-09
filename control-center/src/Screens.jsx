import { useState } from 'react';
import { Bot, Code2, Gauge, Globe2, TerminalSquare } from 'lucide-react';
import { Browser } from '@capacitor/browser';
import { russianSource as t } from './i18n.js';
import { agentRegistry, routingPolicy } from './agents.js';
import { isAllowedServiceUrl, services } from './services.js';
import { checkBridge, normalizeBridgeUrl } from './localBridge.js';

export function ChatScreen({ text, setText, history, onSend, onClear }) {
  return <section className="dashboard">
    <div className="hero-card"><div className="hero-copy"><span className="pill">{t.autoRouting}</span><h2>{t.hero}</h2><p>{t.heroDescription}</p></div><Gauge size={64}/></div>
    <div className="grid"><section className="panel chat-panel">
      <div className="panel-head"><div><span className="kicker">{t.unifiedChat}</span><h3>{t.mainChat}</h3></div><Code2 size={20}/></div>
      <div className="messages">{history.length ? history.map((item, i) => <div className={'bubble ' + item.kind} key={i}><b>{item.author}</b><span>{item.text}</span></div>) : <div className="bubble system"><span>{t.readyMessage}</span></div>}</div>
      <div className="composer"><input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && onSend()} placeholder={t.inputPlaceholder}/><button onClick={onSend}>{t.send}</button><button className="secondary" onClick={onClear}>{t.clear}</button></div>
    </section>
    <AgentsCompact/><TerminalCompact/></div>
  </section>;
}

function AgentsCompact() {
  return <section className="panel agents-panel"><div className="panel-head"><div><span className="kicker">{t.router}</span><h3>{t.agents}</h3></div><Bot size={20}/></div><div className="agent-list">
    {agentRegistry.map(agent => <div className="agent-row" key={agent.id}><div className="rank">{agent.priority}</div><div className="agent-meta"><b>{agent.name}</b><span>{t.roles[agent.roleKey]}</span></div><div className={'agent-state ' + agent.mode}>{t.modes[agent.mode]}</div></div>)}
  </div></section>;
}
function TerminalCompact() {
  return <section className="panel terminal-panel"><div className="panel-head"><div><span className="kicker">{t.codeWorkspace}</span><h3>{t.terminalTitle}</h3></div><TerminalSquare size={20}/></div><pre><span>$</span> bridge status{"\n"}<em>{t.workspaceReady}</em>{"\n"}<span>›</span> {t.waitingTask}</pre></section>;
}

export function AgentsScreen() {
  return <section className="services-view"><Header id="agents"/><div className="panel"><div className="agent-list">
    {agentRegistry.map(agent => <div className="agent-row large" key={agent.id}><div className="rank">{agent.priority}</div><div className="agent-meta"><b>{agent.name}</b><span>{t.roles[agent.roleKey]}</span></div><div className={'agent-state ' + agent.mode}>{t.modes[agent.mode]}</div></div>)}
  </div></div><div className="route-grid">
    {Object.entries(routingPolicy).map(([key, chain]) => <div className="panel route-card" key={key}><b>{t.routeLabels[key]}</b><span>{chain.join(' → ')}</span></div>)}
  </div></section>;
}

export function TerminalScreen({ state, updateState }) {
  const [bridgeNotice, setBridgeNotice] = useState('');
  async function testBridge() {
    if (!normalizeBridgeUrl(state.bridgeUrl)) return setBridgeNotice(t.bridgeInvalid);
    setBridgeNotice(t.bridgeChecking);
    const result = await checkBridge(state.bridgeUrl);
    setBridgeNotice(result.ok ? t.bridgeOk : t.bridgeOffline);
  }
  return <section className="services-view"><Header id="terminal"/><div className="panel form-panel">
    <label>{t.bridgeAddress}<input value={state.bridgeUrl} onChange={e => updateState({ bridgeUrl: e.target.value })}/></label>
    <label className="switch-line"><input type="checkbox" checked={state.localBridgeEnabled} onChange={e => updateState({ localBridgeEnabled: e.target.checked })}/><span>{t.bridgeEnable}</span></label>
    <button className="action-button" onClick={testBridge}>{t.checkBridge}</button>
    {bridgeNotice && <div className="notice">{bridgeNotice}</div>}
    <div className="notice">{t.bridgeWarning}</div><pre className="terminal-preview">$ bridge status{"\n"}{state.localBridgeEnabled ? t.bridgeAllowedUnchecked : t.bridgeDisabled}</pre>
  </div></section>;
}

export function ArisScreen() {
  return <section className="services-view"><Header id="aris"/><div className="status-grid"><div className="panel status-card good"><b>{t.arisPaper}</b><span>ARIS</span></div><div className="panel status-card safe"><b>{t.arisTrading}</b><span>real_trading=false</span></div></div></section>;
}
export function UsageScreen({ state, updateState }) {
  const budgets = state.providerBudgets;
  const setBudget = (key, value) => updateState({ providerBudgets: { ...budgets, [key]: Number(value) || 0 } });
  return <section className="services-view"><Header id="usage"/><div className="budget-grid">
    <Budget label={t.usageMonthly} value={state.monthlyBudget} onChange={v => updateState({ monthlyBudget: Number(v) || 0 })}/>
    <Budget label={t.usageOpenAI} value={budgets.openai} onChange={v => setBudget('openai', v)}/>
    <Budget label={t.usageAnthropic} value={budgets.anthropic} onChange={v => setBudget('anthropic', v)}/>
    <Budget label={t.usageOpenRouter} value={budgets.openrouter} onChange={v => setBudget('openrouter', v)}/>
  </div><div className="notice">{t.localBudgetNote}</div></section>;
}

function Budget({ label, value, onChange }) {
  return <label className="panel budget-card"><span>{label}</span><input type="number" min="0" step="1" value={value} onChange={e => onChange(e.target.value)}/><small>{t.budgetUnit}</small></label>;
}

export function SettingsScreen({ state, updateState }) {
  return <section className="services-view"><Header id="settings"/><div className="panel form-panel">
    <label className="switch-line"><input type="checkbox" checked={state.safeMode} onChange={e => updateState({ safeMode: e.target.checked })}/><span>{state.safeMode ? t.safeModeOn : t.safeModeOff}</span></label>
    <div className="setting-row"><b>{t.languageLabel}</b><span>{t.languageValue}</span></div>
    <div className="setting-row"><b>{t.realTradesLabel}</b><span>{t.realTradesValue}</span></div>
    <div className="setting-row"><b>{t.secretsLabel}</b><span>{t.secretsValue}</span></div>
  </div></section>;
}

export function ServicesScreen({ notice, setNotice }) {
  async function openService(service) {
    if (!isAllowedServiceUrl(service.url)) return setNotice(t.blockedUrl);
    setNotice(t.openingService(service.name));
    try { await Browser.open({ url: service.url, presentationStyle: 'fullscreen' }); }
    catch { setNotice(t.openFailed); }
  }
  return <section className="services-view"><div className="section-title"><span className="kicker">{t.servicesKicker}</span><h2>{t.servicesTitle}</h2><p>{t.servicesDescription}</p></div><div className="service-grid">
    {services.map(service => <button className="service-card" key={service.id} onClick={() => openService(service)}><Globe2 size={28}/><div><b>{service.name}</b><span>{service.description}</span></div><small>{service.host}</small></button>)}
  </div>{notice && <div className="notice">{notice}</div>}</section>;
}

function Header({ id }) {
  const screen = t.screens[id];
  return <div className="section-title"><span className="kicker">{screen.kicker}</span><h2>{screen.title}</h2><p>{screen.description}</p></div>;
}
