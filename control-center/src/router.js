import { agentRegistry } from './agents.js';
import { russianSource } from './i18n.js';

const codeHints = /код|ошибк|репозитор|git|github|terminal|терминал|android|react|python|javascript|typescript|build|сборк/i;
const reviewHints = /проверь|аудит|review|уязв|безопас|архитект|длинн|документ/i;

export function chooseAgent(text) {
  const normalized = String(text || '').trim();
  const preferred = codeHints.test(normalized) ? 'codex' : reviewHints.test(normalized) ? 'gpt' : 'gpt';
  const primary = agentRegistry.find(agent => agent.id === preferred && agent.enabled);
  if (primary) return primary;
  return agentRegistry.find(agent => agent.enabled) || agentRegistry[0];
}

export function routingPreview(text, strings = russianSource) {
  const agent = chooseAgent(text);
  return { agent, message: strings.routingPrepared(agent.name) };
}