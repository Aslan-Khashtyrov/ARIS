export const agentRegistry = [
  { id: 'codex', name: 'Codex', roleKey: 'codex', priority: 1, mode: 'configured' },
  { id: 'gpt', name: 'GPT', roleKey: 'gpt', priority: 2, mode: 'configured' },
  { id: 'claude', name: 'Claude', roleKey: 'claude', priority: 3, mode: 'planned' },
  { id: 'hermes', name: 'Hermes', roleKey: 'hermes', priority: 4, mode: 'configured' },
];

export const routingPolicy = {
  coding: ['codex', 'gpt', 'claude', 'hermes'],
  reasoning: ['gpt', 'claude', 'codex', 'hermes'],
  fallback: ['hermes'],
};

export function configuredAgentCount() {
  return agentRegistry.filter(agent => agent.mode === 'configured').length;
}
