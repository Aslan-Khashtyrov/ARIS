export const agentRegistry = [
  { id: 'codex', name: 'Codex', roleKey: 'codex', priority: 1, mode: 'configured', enabled: true },
  { id: 'gpt', name: 'GPT', roleKey: 'gpt', priority: 2, mode: 'configured', enabled: true },
  { id: 'claude', name: 'Claude', roleKey: 'claude', priority: 3, mode: 'planned', enabled: false },
  { id: 'kimi', name: 'Kimi', roleKey: 'kimi', priority: 4, mode: 'planned', enabled: false },
  { id: 'gemini', name: 'Gemini', roleKey: 'gemini', priority: 5, mode: 'planned', enabled: false },
  { id: 'mistral', name: 'Mistral', roleKey: 'mistral', priority: 6, mode: 'planned', enabled: false },
  { id: 'grok', name: 'Grok', roleKey: 'grok', priority: 7, mode: 'planned', enabled: false },
  { id: 'hermes', name: 'Hermes', roleKey: 'hermes', priority: 8, mode: 'configured', enabled: true },
];

export const routingPolicy = {
  coding: ['codex', 'gpt', 'claude', 'kimi', 'gemini', 'mistral', 'grok', 'hermes'],
  reasoning: ['gpt', 'gemini', 'kimi', 'claude', 'mistral', 'grok', 'codex', 'hermes'],
  review: ['claude', 'gpt', 'gemini', 'mistral', 'kimi', 'grok', 'codex', 'hermes'],
  fallback: ['hermes'],
};

export function configuredAgentCount() {
  return agentRegistry.filter(agent => agent.mode === 'configured' && agent.enabled).length;
}
