export const agentRegistry = [
  { id: 'codex', name: 'Codex', roleKey: 'codex', priority: 1, mode: 'configured', enabled: true },
  { id: 'gpt', name: 'GPT', roleKey: 'gpt', priority: 2, mode: 'configured', enabled: true },
  { id: 'claude', name: 'Claude', roleKey: 'claude', priority: 3, mode: 'planned', enabled: false },
  { id: 'kimi', name: 'Kimi', roleKey: 'kimi', priority: 4, mode: 'planned', enabled: false },
  { id: 'hermes', name: 'Hermes', roleKey: 'hermes', priority: 5, mode: 'configured', enabled: true },
];

export const routingPolicy = {
  coding: ['codex', 'gpt', 'claude', 'hermes'],
  reasoning: ['gpt', 'claude', 'kimi', 'codex', 'hermes'],
  review: ['claude', 'gpt', 'kimi', 'codex', 'hermes'],
  fallback: ['hermes'],
};

export function configuredAgentCount() {
  return agentRegistry.filter(agent => agent.mode === 'configured' && agent.enabled).length;
}
