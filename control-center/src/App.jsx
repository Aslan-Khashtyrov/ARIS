import { useMemo, useState } from 'react';
import { Bot, Cpu, Globe2, ListTodo, MessageSquare, ScrollText, Settings, TerminalSquare, WalletCards } from 'lucide-react';
import { russianSource as t } from './i18n.js';
import { configuredAgentCount } from './agents.js';
import { routingPreview } from './router.js';
import { loadState, saveState } from './storage.js';
import { AgentsScreen, ArisScreen, ChatScreen, LogsScreen, ServicesScreen, SettingsScreen, TasksScreen, TerminalScreen, UsageScreen } from './Screens.jsx';
import './styles.css';

const nav = [
  ['chat', MessageSquare], ['agents', Bot], ['terminal', TerminalSquare],
  ['services', Globe2], ['aris', Cpu], ['tasks', ListTodo], ['logs', ScrollText], ['usage', WalletCards], ['settings', Settings],
];

function App() {
  const [tab, setTab] = useState('chat');
  const [text, setText] = useState('');
  const [notice, setNotice] = useState('');
  const [state, setState] = useState(() => loadState());
  const configured = useMemo(() => configuredAgentCount(), []);

  function updateState(patchOrUpdater) {
    setState(current => {
      const patch = typeof patchOrUpdater === 'function' ? patchOrUpdater(current) : patchOrUpdater;
      const next = { ...current, ...patch };
      saveState(next);
      return next;
    });
  }

  function appendLog(logs, text) {
    const entry = { id: `${Date.now()}-${Math.random()}`, time: new Date().toLocaleString('ru-RU'), text };
    return [...logs, entry].slice(-200);
  }

  function sendMessage() {
    const value = text.trim();
    if (!value) return;
    const route = routingPreview(value);
    updateState(current => ({
      chatHistory: [...current.chatHistory,
        { kind: 'me', author: t.you, text: value },
        { kind: 'agent', author: route.agent.name, text: route.message },
      ].slice(-100),
      logs: appendLog(current.logs, t.logChatRouted(route.agent.name)),
    }));
    setText('');
  }


  function addTask(textValue) {
    const task = { id: `${Date.now()}-${Math.random()}`, text: textValue, done: false };
    updateState(current => ({ tasks: [...current.tasks, task].slice(-100), logs: appendLog(current.logs, t.logTaskAdded) }));
  }
  function toggleTask(id) {
    updateState(current => ({ tasks: current.tasks.map(task => task.id === id ? { ...task, done: !task.done } : task), logs: appendLog(current.logs, t.logTaskChanged) }));
  }
  function deleteTask(id) {
    updateState(current => ({ tasks: current.tasks.filter(task => task.id !== id), logs: appendLog(current.logs, t.logTaskDeleted) }));
  }

  const screens = {
    chat: <ChatScreen text={text} setText={setText} history={state.chatHistory} onSend={sendMessage} onClear={() => updateState({ chatHistory: [] })}/>,
    agents: <AgentsScreen/>,
    terminal: <TerminalScreen state={state} updateState={updateState}/>,
    services: <ServicesScreen notice={notice} setNotice={setNotice}/>,
    aris: <ArisScreen/>,
    tasks: <TasksScreen state={state} addTask={addTask} toggleTask={toggleTask} deleteTask={deleteTask}/>,
    logs: <LogsScreen state={state}/>,
    usage: <UsageScreen state={state} updateState={updateState}/>,
    settings: <SettingsScreen state={state} updateState={updateState}/>,
  };

  return <div className="app-shell" lang="ru">
    <aside className="rail"><div className="brand">P1</div>{nav.map(([id, Icon]) => <button key={id} className={tab === id ? 'nav active' : 'nav'} onClick={() => setTab(id)}><Icon size={20}/><span>{t.nav[id]}</span></button>)}</aside>
    <main className="main"><header className="topbar"><div><div className="eyebrow">{t.appSystem}</div><h1>Project One</h1></div><div className="status"><span className="dot"/> {configured} {t.agentsOnline}</div></header>{screens[tab]}</main>
  </div>;
}

export default App;
