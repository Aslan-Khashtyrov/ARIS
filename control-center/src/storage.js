const KEY = 'project-one-state-v1';

export const defaultState = {
  safeMode: true,
  localBridgeEnabled: false,
  bridgeUrl: 'http://127.0.0.1:8765',
  monthlyBudget: 0,
  providerBudgets: { openai: 0, anthropic: 0, openrouter: 0 },
  chatHistory: [],
};

export function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '{}');
    return {
      ...defaultState,
      ...saved,
      providerBudgets: { ...defaultState.providerBudgets, ...(saved.providerBudgets || {}) },
      chatHistory: Array.isArray(saved.chatHistory) ? saved.chatHistory.slice(-100) : [],
    };
  } catch {
    return defaultState;
  }
}

export function saveState(state) {
  localStorage.setItem(KEY, JSON.stringify(state));
}
