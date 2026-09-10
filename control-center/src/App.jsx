import { useMemo, useState } from 'react';
import { Bot, Cpu, Globe2, LayoutDashboard, ListTodo, MessageSquare, ScrollText, Settings, ShieldCheck, TerminalSquare, WalletCards, Workflow, Wrench } from 'lucide-react';
import { getLocaleStrings } from './i18n.js';
import { configuredAgentCount } from './agents.js';
import { routeKind, routingPreview } from './router.js';
import { runLocalAgent } from './localBridge.js';
import { chooseLiveAgent, nativeAiGenerate, nativeCouncilGenerate } from './nativeAi.js';
import { loadState, saveState } from './storage.js';
import { downloadBackup, parseBackup } from './backup.js';
import { ErrorBoundary } from './ErrorBoundary.jsx';
import { AgentsScreen, ArisScreen, ChatScreen, HomeScreen, LogsScreen, MissionsScreen, SecurityScreen, ServicesScreen, SettingsScreen, TasksScreen, TerminalScreen, UsageScreen, WorkspaceScreen } from './Screens.jsx';
import './styles.css';

const nav = [
  ['home', LayoutDashboard], ['chat', MessageSquare], ['agents', Bot], ['terminal', TerminalSquare],
  ['services', Globe2], ['aris', Cpu], ['missions', Workflow], ['workspace', Wrench], ['tasks', ListTodo], ['security', ShieldCheck], ['logs', ScrollText], ['usage', WalletCards], ['settings', Settings],
];

function App() {
  const [tab, setTab] = useState('home');
  const [text, setText] = useState('');
  const [notice, setNotice] = useState('');
  const [liveAiBusy, setLiveAiBusy] = useState(false);
  const [councilBusy, setCouncilBusy] = useState(false);
  const [state, setState] = useState(() => loadState());
  const t = useMemo(() => getLocaleStrings(state.locale), [state.locale]);
  const configured = useMemo(() => configuredAgentCount(), []);

  function updateState(patchOrUpdater) {
    setState(current => {
      const patch = typeof patchOrUpdater === 'function' ? patchOrUpdater(current) : patchOrUpdater;
      const next = { ...current, ...patch };
      saveState(next);
      return next;
    });
  }
  function appendLog(logs, textValue) {
    const locale = state.locale === 'ru' ? 'ru-RU' : 'en-US';
    const entry = { id: `${Date.now()}-${Math.random()}`, time: new Date().toLocaleString(locale), text: textValue };
    return [...logs, entry].slice(-200);
  }

  async function runLocal(agent) {
    const value = text.trim();
    if (!value || liveAiBusy || !state.localBridgeEnabled) return false;
    setLiveAiBusy(true);
    try {
      const result = await runLocalAgent(state.bridgeUrl, agent, value);
      if (!result.ok) throw new Error(result.reason);
      updateState(current => ({ chatHistory: [...current.chatHistory, { kind: 'me', author: t.you, text: value }, { kind: 'agent', author: agent === 'codex' ? 'Codex' : 'Hermes', text: result.text || t.liveAiEmpty }].slice(-100), logs: appendLog(current.logs, t.logLocalAgentCompleted(agent)) }));
      setText(''); return true;
    } catch { updateState(current => ({ logs: appendLog(current.logs, t.logLocalAgentFailed(agent)) })); return false; }
    finally { setLiveAiBusy(false); }
  }

  async function runLiveAi() {
    const value = text.trim();
    if (!value || liveAiBusy) return false;
    setLiveAiBusy(true);
    const kind = routeKind(value);
    const localFirst = state.localBridgeEnabled && kind === 'coding';
    try {
      if (localFirst) {
        const local = await runLocalAgent(state.bridgeUrl, 'codex', value);
        if (local.ok) {
          updateState(current => ({ chatHistory: [...current.chatHistory, { kind: 'me', author: t.you, text: value }, { kind: 'agent', author: 'Codex', text: local.text || t.liveAiEmpty }].slice(-100), logs: appendLog(current.logs, t.logLocalAgentCompleted('codex')) }));
          setText(''); return true;
        }
      }
      const selected = await chooseLiveAgent(value);
      if (selected.provider) {
        try {
          const result = await nativeAiGenerate({ provider: selected.provider, model: selected.model, prompt: value });
          updateState(current => ({ chatHistory: [...current.chatHistory, { kind: 'me', author: t.you, text: value }, { kind: 'agent', author: selected.agent.name, text: result.text || t.liveAiEmpty }].slice(-100), logs: appendLog(current.logs, t.logLiveAiCompleted(selected.provider)) }));
          setText(''); return true;
        } catch {
          updateState(current => ({ logs: appendLog(current.logs, t.logLiveAiFailed(selected.provider)) }));
        }
      }
      if (state.localBridgeEnabled) {
        const fallback = await runLocalAgent(state.bridgeUrl, 'hermes', value);
        if (fallback.ok) {
          updateState(current => ({ chatHistory: [...current.chatHistory, { kind: 'me', author: t.you, text: value }, { kind: 'agent', author: 'Hermes', text: fallback.text || t.liveAiEmpty }].slice(-100), logs: appendLog(current.logs, t.logLocalAgentCompleted('hermes')) }));
          setText(''); return true;
        }
      }
      updateState(current => ({ logs: appendLog(current.logs, t.logLiveAiUnavailable) }));
      return false;
    } finally { setLiveAiBusy(false); }
  }

  async function runNativeCouncil() {
    const value = text.trim();
    if (!value || councilBusy || liveAiBusy) return false;
    setCouncilBusy(true);
    try {
      const result = await nativeCouncilGenerate(value);
      const messages = [{ kind: 'me', author: t.you, text: value }, { kind: 'agent', author: result.plan.primary.agent.name, text: result.primary.text || t.liveAiEmpty }];
      if (result.review) messages.push({ kind: 'agent', author: `${result.plan.reviewer.agent.name} · ${t.councilReviewer}`, text: result.review.text || t.liveAiEmpty });
      updateState(current => ({ chatHistory: [...current.chatHistory, ...messages].slice(-100), logs: appendLog(current.logs, t.logCouncilCompleted(result.review ? 2 : 1)) }));
      setText(''); return true;
    } catch {
      updateState(current => ({ logs: appendLog(current.logs, t.logCouncilFailed) })); return false;
    } finally { setCouncilBusy(false); }
  }

  function sendMessage() {
    const value = text.trim();
    if (!value) return;
    const route = routingPreview(value, t);
    updateState(current => ({
      chatHistory: [...current.chatHistory,
        { kind: 'me', author: t.you, text: value },
        { kind: 'agent', author: route.agent.name, text: route.message },
      ].slice(-100),
      logs: appendLog(current.logs, t.logChatRouted(route.agent.name)),
    }));
    setText('');
  }

  function addMission(textValue) {
    const value = String(textValue || '').trim();
    if (!value) return;
    const route = routingPreview(value, t);
    const mission = { id: `${Date.now()}-${Math.random()}`, text: value, agent: route.agent.name, status: 'prepared', createdAt: new Date().toISOString() };
    updateState(current => ({ missions: [...current.missions, mission].slice(-50), logs: appendLog(current.logs, t.logMissionPrepared(route.agent.name)) }));
  }
  function deleteMission(id) {
    updateState(current => ({ missions: current.missions.filter(item => item.id !== id), logs: appendLog(current.logs, t.logMissionDeleted) }));
  }

  function addTask(textValue) {
    const task = { id: `${Date.now()}-${Math.random()}`, text: textValue, done: false };
    updateState(current => ({ tasks: [...current.tasks, task].slice(-100), logs: appendLog(current.logs, t.logTaskAdded) }));
  }
  function toggleTask(id) {
    updateState(current => ({ tasks: current.tasks.map(task => task.id === id ? { ...task, done: !task.done } : task), logs: appendLog(current.logs, t.logTaskChanged) }));
  }  function deleteTask(id) {
    updateState(current => ({ tasks: current.tasks.filter(task => task.id !== id), logs: appendLog(current.logs, t.logTaskDeleted) }));
  }

  const common = { t };
  const screens = {
    home: <HomeScreen {...common} state={state} configured={configured} onNavigate={setTab}/>,
    chat: <ChatScreen {...common} text={text} setText={setText} history={state.chatHistory} onSend={sendMessage} onRunLiveAi={runLiveAi} onRunCodex={() => runLocal('codex')} onRunHermes={() => runLocal('hermes')} liveAiBusy={liveAiBusy} onRunCouncil={runNativeCouncil} councilBusy={councilBusy} onClear={() => updateState({ chatHistory: [] })}/>,
    agents: <AgentsScreen {...common} state={state} updateState={updateState}/>,
    terminal: <TerminalScreen {...common} state={state} updateState={updateState}/>,
    services: <ServicesScreen {...common} notice={notice} setNotice={setNotice}/>,
    aris: <ArisScreen {...common}/>,
    missions: <MissionsScreen {...common} state={state} addMission={addMission} deleteMission={deleteMission}/>,
    workspace: <WorkspaceScreen {...common} state={state}/>,
    tasks: <TasksScreen {...common} state={state} addTask={addTask} toggleTask={toggleTask} deleteTask={deleteTask}/>,
    security: <SecurityScreen {...common} state={state}/>,
    logs: <LogsScreen {...common} state={state}/>,
    usage: <UsageScreen {...common} state={state} updateState={updateState}/>,
    settings: <SettingsScreen {...common} state={state} updateState={updateState} onExport={() => downloadBackup(state)} onImport={(raw) => { const restored = parseBackup(raw); if (!restored) return false; updateState(restored); return true; }}/>,
  };

  return <div className="app-shell" lang={state.locale} data-safe-mode={state.safeMode ? 'on' : 'off'}>
    <aside className="rail"><div className="brand">P1</div>{nav.map(([id, Icon]) => <button key={id} className={tab === id ? 'nav active' : 'nav'} onClick={() => setTab(id)}><Icon size={20}/><span>{t.nav[id]}</span></button>)}</aside>
    <main className="main"><header className="topbar"><div><div className="eyebrow">{t.appSystem}</div><h1>Project One</h1></div><div className="status"><span className="dot"/> {configured} {t.agentsOnline}</div></header><ErrorBoundary t={t} resetKey={`${tab}:${state.locale}`}>{screens[tab]}</ErrorBoundary></main>
  </div>;
}

export default App;