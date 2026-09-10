import { agentRegistry, routingPolicy } from './agents.js';
import { russianSource } from './i18n.js';

const codeHints = /код|ошибк|репозитор|git|github|terminal|терминал|android|react|python|javascript|typescript|build|сборк/i;
const reviewHints = /проверь|аудит|review|уязв|безопас|архитект|длинн|документ/i;

function firstAvailable(chain) {
  return chain.map(id => agentRegistry.find(agent => agent.id === id))
    .find(agent => agent?.enabled && agent.mode === 'configured');
}

function routeKind(text) {
  const normalized = String(text || '').trim();
  return reviewHints.test(normalized) ? 'review' : codeHints.test(normalized) ? 'coding' : 'reasoning';
}

export function chooseAgent(text) {
  const route = routeKind(text);
  return firstAvailable(routingPolicy[route]) || firstAvailable(routingPolicy.fallback) || agentRegistry.find(agent => agent.enabled) || agentRegistry[0];
}

export function councilPreview(text, strings = russianSource) {
  const route = routeKind(text);
  const chain = [...routingPolicy[route], ...routingPolicy.fallback];
  const available = chain.map(id => agentRegistry.find(agent => agent.id === id)).filter((agent, index, list) => agent?.enabled && agent.mode === 'configured' && list.findIndex(item => item?.id === agent.id) === index);
  const primary = available[0] || chooseAgent(text);
  const reviewer = available.find(agent => agent.id !== primary.id) || null;
  const arbiter = available.find(agent => agent.id !== primary.id && agent.id !== reviewer?.id) || null;
  return { route, primary, reviewer, arbiter, message: strings.councilPrepared(primary.name, reviewer?.name, arbiter?.name) };
}

export function routingPreview(text, strings = russianSource) {
  const council = councilPreview(text, strings);
  return { agent: council.primary, council, message: council.message };
}
