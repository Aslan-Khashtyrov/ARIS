const TRUSTED_AI_PROVIDERS = Object.freeze(['google', 'mistral', 'xai']);
const HARD_BLOCKS = Object.freeze([
  'secret.export', 'secret.log', 'finance.real_trade', 'finance.transfer',
  'finance.deposit', 'finance.withdraw', 'bridge.remote', 'shell.arbitrary', 'network.unknown',
]);
const CONFIRM = Object.freeze(['config.critical_write', 'process.control', 'billing.change']);

export const argusPolicy = Object.freeze({
  trustedAiProviders: TRUSTED_AI_PROVIDERS,
  hardBlocks: HARD_BLOCKS,
  confirmationRequired: CONFIRM,
});

export function argusDecision(action) {
  const value = String(action || '').trim().toLowerCase();
  if (HARD_BLOCKS.includes(value)) return Object.freeze({ decision: 'deny', action: value });
  if (CONFIRM.includes(value)) return Object.freeze({ decision: 'confirm', action: value });
  return Object.freeze({ decision: 'allow', action: value });
}

export function argusAllowsAiProvider(provider) {
  return TRUSTED_AI_PROVIDERS.includes(String(provider || '').toLowerCase());
}
