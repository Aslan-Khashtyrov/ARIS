import { useEffect, useState } from 'react';
import { Bot, CheckCircle2, Code2, Gauge, Globe2, ShieldCheck, TerminalSquare, Workflow, XCircle } from 'lucide-react';
import { supportedLanguages } from './i18n.js';
import { agentRegistry, routingPolicy } from './agents.js';
import { councilPreview } from './router.js';
import { isAllowedServiceUrl, services } from './services.js';
import { openProtectedService } from './protectedWeb.js';
import { checkBridge, normalizeBridgeUrl } from './localBridge.js';
import { runSecurityDiagnostics } from './securityDiagnostics.js';
import { deleteProviderSecret, listSecureProviders, secureProviderIds, storeProviderSecret, vaultAvailable } from './secureVault.js';
import { nativeAiAvailable, nativeAiCapabilities, nativeRouteForAgent } from './nativeAi.js';
import { prepareExecutionCapsule } from './executorPolicy.js';


export function HomeScreen({ t, state, configured, onNavigate }) {
  const completed = state.tasks.filter(task => task.done).length;
  const security = runSecurityDiagnostics(state);
  return <section className="dashboard">
    <div className="hero-card home-hero"><div className="hero-copy"><span className="pill">{t.homeKicker}</span><h2>{t.homeTitle}</h2><p>{t.homeDescription}</p></div><div className="shield-mark">P1</div></div>
    <div className="metric-grid">
      <button className="panel metric-card" onClick={() => onNavigate('agents')}><span>{t.homeAgents}</span><b>{configured}</b><small>{t.homeAgentsHint}</small></button>
      <button className="panel metric-card" onClick={() => onNavigate('aris')}><span>{t.homeAris}</span><b>{t.homeSafe}</b><small>real_trading=false</small></button>
      <button className="panel metric-card" onClick={() => onNavigate('tasks')}><span>{t.homeTasks}</span><b>{completed}/{state.tasks.length}</b><small>{t.homeTasksHint}</small></button>
      <button className="panel metric-card" onClick={() => onNavigate('terminal')}><span>{t.homeBridge}</span><b>{state.localBridgeEnabled ? t.homeAllowed : t.homeDisabled}</b><small>{t.homeBridgeHint}</small></button>
    </div>
    <button className={'panel security-strip ' + (security.ok ? 'secure' : 'warning')} onClick={() => onNavigate('security')}><ShieldCheck size={22}/><div><b>{security.ok ? t.securityProtected : t.securityAttention}</b><span>{security.passed}/{security.total} {t.securityChecksPassed}</span></div><span className="security-open">{t.homeSecurityOpen}</span></button>
    <div className="panel quick-panel"><div><span className="kicker">{t.homeQuick}</span><h3>{t.homeQuickTitle}</h3></div><div className="quick-actions"><button onClick={() => onNavigate('chat')}>{t.homeOpenChat}</button><button onClick={() => onNavigate('missions')}>{t.homeOpenMissions}</button><button onClick={() => onNavigate('security')}>{t.homeOpenSecurity}</button><button onClick={() => onNavigate('services')}>{t.homeOpenServices}</button><button onClick={() => onNavigate('settings')}>{t.homeOpenSettings}</button></div></div>
  </section>;
}

export function ChatScreen({ t, text, setText, history, onSend, onRunLiveAi, onRunCodex, onRunHermes, liveAiBusy, onRunCouncil, councilBusy, onClear }) {
  return <section className="dashboard">
    <div className="hero-card"><div className="hero-copy"><span className="pill">{t.autoRouting}</span><h2>{t.hero}</h2><p>{t.heroDescription}</p></div><Gauge size={64}/></div>
    <div className="grid"><section className="panel chat-panel">
      <div className="panel-head"><div><span className="kicker">{t.unifiedChat}</span><h3>{t.mainChat}</h3></div><Code2 size={20}/></div>
      <div className="messages">{history.length ? history.map((item, i) => <div className={'bubble ' + item.kind} key={i}><b>{item.author}</b><span>{item.text}</span></div>) : <div className="bubble system"><span>{t.readyMessage}</span></div>}</div>
      <div className="composer"><input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && onSend()} placeholder={t.inputPlaceholder}/><button onClick={onSend}>{t.send}</button><button className="secondary" disabled={liveAiBusy || councilBusy} onClick={onRunLiveAi}>{liveAiBusy ? t.liveAiRunning : t.runLiveAi}</button><button className="secondary" disabled={liveAiBusy || councilBusy} onClick={onRunCodex}>{t.runCodex}</button><button className="secondary" disabled={liveAiBusy || councilBusy} onClick={onRunHermes}>{t.runHermes}</button><button className="secondary" disabled={councilBusy || liveAiBusy} onClick={onRunCouncil}>{councilBusy ? t.councilRunning : t.runCouncil}</button><button className="secondary" onClick={onClear}>{t.clear}</button></div>
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
  const [nativeCaps, setNativeCaps] = useState({});
  useEffect(() => { if (nativeAiAvailable()) nativeAiCapabilities().then(setNativeCaps).catch(() => setNativeCaps({})); }, []);
  const examples = [[t.routeLabels.coding, councilPreview('android code', t)], [t.routeLabels.reasoning, councilPreview('explain idea', t)], [t.routeLabels.review, councilPreview('security review', t)]];
  return <section className="services-view"><Header t={t} id="agents"/><div className="panel council-panel"><span className="kicker">{t.councilKicker}</span><h3>{t.councilTitle}</h3><p>{t.councilDescription}</p><div className="council-grid">{examples.map(([label, plan]) => <div className="council-card" key={label}><b>{label}</b><span>{t.councilPrimary}: {plan.primary.name}</span><span>{t.councilReviewer}: {plan.reviewer?.name || t.councilNone}</span><span>{t.councilArbiter}: {plan.arbiter?.name || t.councilNone}</span></div>)}</div></div><div className="panel"><div className="agent-list">
    {agentRegistry.map(agent => { const route = nativeRouteForAgent(agent.id); const ready = route ? nativeCaps[route.provider] === true : false; return <div className="agent-row large" key={agent.id}><div className="rank">{agent.priority}</div><div className="agent-meta"><b>{agent.name}</b><span>{t.roles[agent.roleKey]}</span></div><div className={'agent-state ' + (ready ? 'configured' : agent.mode)}>{ready ? t.nativeReady : t.modes[agent.mode]}</div></div>; })}
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
    <Budget t={t} label={t.usageKimi} value={budgets.kimi} onChange={v => setBudget('kimi', v)}/>
    <Budget t={t} label={t.usageGoogle} value={budgets.google} onChange={v => setBudget('google', v)}/>
    <Budget t={t} label={t.usageMistral} value={budgets.mistral} onChange={v => setBudget('mistral', v)}/>
    <Budget t={t} label={t.usageXai} value={budgets.xai} onChange={v => setBudget('xai', v)}/>
  </div><div className="panel budget-summary"><b>{t.budgetSummary}</b><span>{Object.values(budgets).reduce((sum, value) => sum + (Number(value) || 0), 0)} / {Number(state.monthlyBudget) || 0} ₽</span><progress max={Math.max(Number(state.monthlyBudget) || 0, 1)} value={Math.min(Object.values(budgets).reduce((sum, value) => sum + (Number(value) || 0), 0), Math.max(Number(state.monthlyBudget) || 0, 1))}/></div><div className="notice">{t.localBudgetNote}</div></section>;
}

function Budget({ t, label, value, onChange }) {
  return <label className="panel budget-card"><span>{label}</span><input type="number" min="0" step="1" value={value} onChange={e => onChange(e.target.value)}/><small>{t.budgetUnit}</small></label>;
}

export function SettingsScreen({ t, state, updateState, onExport, onImport }) {
  return <section className="services-view"><Header t={t} id="settings"/><div className="panel form-panel">
    <label className="switch-line"><input type="checkbox" checked={true} disabled/><span>{t.safeModeLocked}</span></label>
    <div className="setting-row language-row"><div><b>{t.languageTitle}</b><small>{t.languageHint}</small></div><select value={state.locale} onChange={e => updateState({ locale: e.target.value })}>{supportedLanguages.map(language => <option value={language.id} key={language.id}>{language.label}</option>)}</select></div>
    <div className="setting-row"><b>{t.realTradesLabel}</b><span>{t.realTradesValue}</span></div>
    <div className="setting-row"><b>{t.secretsLabel}</b><span>{t.secretsValue}</span></div>
    <SecureVault t={t}/>
    <div className="setting-row"><b>{t.backupTitle}</b><span>{t.backupHint}</span><div className="quick-actions"><button type="button" onClick={onExport}>{t.backupExport}</button><label className="import-button">{t.backupImport}<input type="file" accept="application/json,.json" onChange={async e => { const file=e.target.files?.[0]; if (!file) return; const ok=onImport(await file.text()); e.target.value=''; alert(ok ? t.backupImported : t.backupInvalid); }}/></label></div></div>
      <div className="setting-row"><b>{t.versionLabel}</b><span>{t.versionValue}</span></div>
  </div></section>;
}
function SecureVault({ t }) {
  const [present, setPresent] = useState({});
  const [drafts, setDrafts] = useState({});
  const supported = vaultAvailable();
  async function refresh() {
    if (!supported) return setPresent({});
    const providers = await listSecureProviders();
    setPresent(Object.fromEntries(secureProviderIds.map(id => [id, providers.includes(id)])));
  }
  useEffect(() => { refresh(); }, [supported]);
  async function save(id) {
    const value = drafts[id] || '';
    if (!value) return;
    if (await storeProviderSecret(id, value)) { setDrafts(current => ({ ...current, [id]: '' })); await refresh(); }
  }
  async function remove(id) { if (await deleteProviderSecret(id)) await refresh(); }
  return <div className="setting-row secure-vault"><div><b>{t.vaultTitle}</b><span>{t.vaultHint}</span></div>{!supported ? <div className="notice">{t.vaultAndroidOnly}</div> : <div className="vault-grid">{secureProviderIds.map(id => <div className="vault-row" key={id}><div><b>{t.secretProviders[id]}</b><small>{present[id] ? t.vaultStored : t.vaultNotStored}</small></div><input type="password" autoComplete="off" spellCheck="false" value={drafts[id] || ''} onChange={e => setDrafts(current => ({ ...current, [id]: e.target.value }))} placeholder={t.vaultPlaceholder}/><button type="button" onClick={() => save(id)}>{t.vaultSave}</button>{present[id] && <button type="button" className="secondary" onClick={() => remove(id)}>{t.vaultDelete}</button>}</div>)}</div>}</div>;
}



export function ServicesScreen({ t, notice, setNotice }) {
  async function openService(service) {
    if (!isAllowedServiceUrl(service.url)) return setNotice(t.blockedUrl);
    setNotice(t.openingService(service.name));
    if (!await openProtectedService(service)) setNotice(t.openFailed);
  }
  return <section className="services-view"><div className="section-title"><span className="kicker">{t.servicesKicker}</span><h2>{t.servicesTitle}</h2><p>{t.servicesDescription}</p></div><div className="service-grid">
    {services.map(service => <button className="service-card" key={service.id} onClick={() => openService(service)}><Globe2 size={28}/><div><b>{service.name}</b><span>{t.serviceDescriptions[service.id]}</span></div><small>{service.host}</small></button>)}
  </div>{notice && <div className="notice">{notice}</div>}</section>;
}

function Header({ t, id }) {
  const screen = t.screens[id];
  return <div className="section-title"><span className="kicker">{screen.kicker}</span><h2>{screen.title}</h2><p>{screen.description}</p></div>;
}

export function MissionsScreen({ t, state, addMission, deleteMission }) {
  const [draft, setDraft] = useState('');
  function submit() { const value = draft.trim(); if (!value) return; addMission(value); setDraft(''); }
  return <section className="services-view">
    <div className="section-title"><span className="kicker">{t.missionsKicker}</span><h2>{t.missionsTitle}</h2><p>{t.missionsDescription}</p></div>
    <div className="panel mission-compose"><div className="mission-icon"><Workflow size={26}/></div><div><b>{t.missionsNew}</b><span>{t.missionsHint}</span></div><div className="composer mission-input"><input value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} placeholder={t.missionsPlaceholder}/><button onClick={submit}>{t.missionsPrepare}</button></div></div>
    <div className="mission-list">{state.missions.length ? [...state.missions].reverse().map(item => <article className="panel mission-card" key={item.id}><div className="mission-card-head"><div><span className="pill">{t.missionsPrepared}</span><h3>{item.text}</h3></div><button className="small" onClick={() => deleteMission(item.id)}>{t.delete}</button></div><div className="mission-meta"><span>{t.missionsAgent}: <b>{item.agent}</b></span><span>{t.missionsExecutionPending}</span></div></article>) : <div className="panel empty-state">{t.noMissions}</div>}</div>
  </section>;
}

export function SecurityScreen({ t, state }) {
  const [result, setResult] = useState(() => runSecurityDiagnostics(state));
  const run = () => setResult(runSecurityDiagnostics(state));
  return <section className="services-view">
    <div className="section-title"><span className="kicker">{t.securityKicker}</span><h2>{t.securityTitle}</h2><p>{t.securityDescription}</p></div>
    <div className={'panel security-summary ' + (result.ok ? 'secure' : 'warning')}><div className="security-orb"><ShieldCheck size={30}/></div><div><span>{t.securityStatus}</span><h3>{result.ok ? t.securityProtected : t.securityAttention}</h3><small>{result.passed}/{result.total} {t.securityChecksPassed}</small></div><button className="action-button" onClick={run}>{t.securityRun}</button></div>
    <div className="security-grid">{result.checks.map(check => <div className="panel security-check" key={check.id}>{check.ok ? <CheckCircle2 size={21}/> : <XCircle size={21}/>}<div><b>{t.securityChecks[check.id]}</b><span>{check.ok ? t.securityOk : t.securityFailed}</span></div></div>)}</div>
    <div className="notice">{t.securityNote}</div>
  </section>;
}


export function WorkspaceScreen({ t, state }) {
  const capsule = prepareExecutionCapsule();
  return <section className="services-view">
    <Header t={t} id="workspace"/>
    <div className="panel executor-summary"><div><span className="kicker">{t.executorGuard}</span><h3>{t.executorReady}</h3><p>{t.executorDescription}</p></div><ShieldCheck size={34}/></div>
    <div className="executor-grid">
      <div className="panel executor-card"><b>{t.executorScope}</b><span>{capsule.workspace}</span></div>
      <div className="panel executor-card"><b>{t.executorMode}</b><span>{t.executorGuarded}</span></div>
      <div className="panel executor-card"><b>{t.executorTakeover}</b><span>{capsule.takeover ? t.executorAlways : t.executorUnavailable}</span></div>
      <div className="panel executor-card"><b>{t.executorChannel}</b><span>{state.localBridgeEnabled ? t.executorBridgeEnabled : t.executorBridgeDisabled}</span></div>
    </div>
    <div className="panel executor-actions"><b>{t.executorAllowed}</b><div>{capsule.allowedActions.map(action => <span className="pill" key={action}>{action}</span>)}</div></div>
    <div className="notice">{t.executorNotice}</div>
  </section>;
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