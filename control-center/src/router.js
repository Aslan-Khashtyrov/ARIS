import { agentRegistry, routingPolicy } from './agents.js';
import { russianSource } from './i18n.js';

const codeHints = /код|ошибк|репозитор|git|github|terminal|терминал|android|react|python|javascript|typescript|build|сборк/i;
const reviewHints = /проверь|аудит|review|уязв|безопас|архитект|длинн|документ/i;

function firstAvailable(chain) {
  return chain.map(id => agentRegistry.find(agent => agent.id === id))
    .find(agent => agent?.enabled && agent.mode === 'configured');
}

export function chooseAgent(text) {
  const normalized = String(text || '').trim();
  const route = reviewHints.test(normalized) ? 'review' : codeHints.test(normalized) ? 'coding' : 'reasoning';
  return firstAvailable(routingPolicy[route]) || firstAvailable(routingPolicy.fallback) || agentRegistry.find(agent => agent.enabled) || agentRegistry[0];
}

export function routingPreview(text, strings = russianSource) {
  const agent = chooseAgent(text);
  return { agent, message: strings.routingPrepared(agent.name) };
}
