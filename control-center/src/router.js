import { agentRegistry, routingPolicy } from './agents.js';

const codeHints = /код|ошибк|репозитор|git|github|terminal|терминал|android|react|python|javascript|typescript|build|сборк/i;
const reviewHints = /проверь|аудит|review|уязв|безопас|архитект|длинн|документ/i;

function intentFor(text) {
  const normalized = String(text || '').trim();
  if (codeHints.test(normalized)) return 'coding';
  if (reviewHints.test(normalized)) return 'review';
  return 'reasoning';
}

export function chooseAgent(text) {
  const chain = routingPolicy[intentFor(text)] || routingPolicy.fallback;
  for (const id of chain) {
    const agent = agentRegistry.find(item => item.id === id && item.enabled && item.mode === 'configured');
    if (agent) return agent;
  }
  return agentRegistry.find(item => item.enabled && item.mode === 'configured') || null;
}

export function routingPreview(text) {
  const agent = chooseAgent(text);
  return agent
    ? { agent, message: `Задача подготовлена для ${agent.name}. Живое выполнение включится после подключения безопасного моста или официального API.` }
    : { agent: { name: 'Project One' }, message: 'Нет настроенного агента. Задача сохранена локально и не отправлена наружу.' };
}
