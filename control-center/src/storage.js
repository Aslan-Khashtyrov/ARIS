import { DEFAULT_LOCALE, isSupportedLocale } from './i18n.js';

const KEY = 'project-one-state-v1';
const MAX_STATE_CHARS = 512 * 1024;

export const defaultState = {
  locale: DEFAULT_LOCALE,
  safeMode: true,
  localBridgeEnabled: false,
  bridgeUrl: 'http://127.0.0.1:8765',
  monthlyBudget: 0,
  providerBudgets: { openai: 0, anthropic: 0, openrouter: 0 },
  chatHistory: [], missions: [], tasks: [], logs: [],
};

const finiteNonNegative = value => Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : 0;
const text = (value, max = 4000) => String(value ?? '').slice(0, max);
const list = value => Array.isArray(value) ? value : [];

function sanitize(saved = {}) {
  if (!saved || typeof saved !== 'object' || Array.isArray(saved)) saved = {};
  return {
    ...defaultState,
    locale: isSupportedLocale(saved.locale) ? saved.locale : DEFAULT_LOCALE,
    safeMode: true,
    localBridgeEnabled: saved.localBridgeEnabled === true,
    bridgeUrl: text(saved.bridgeUrl || defaultState.bridgeUrl, 200),
    monthlyBudget: finiteNonNegative(saved.monthlyBudget),
    providerBudgets: {
      openai: finiteNonNegative(saved.providerBudgets?.openai),
      anthropic: finiteNonNegative(saved.providerBudgets?.anthropic),
      openrouter: finiteNonNegative(saved.providerBudgets?.openrouter),
    },
    chatHistory: list(saved.chatHistory).slice(-100).map(item => ({ kind: item?.kind === 'me' ? 'me' : 'agent', author: text(item?.author, 80), text: text(item?.text) })),
    missions: list(saved.missions).slice(-50).map(item => ({ id: text(item?.id, 120), text: text(item?.text, 1600), agent: text(item?.agent, 80), status: 'prepared', createdAt: text(item?.createdAt, 80) })),
    tasks: list(saved.tasks).slice(-100).map(item => ({ id: text(item?.id, 120), text: text(item?.text, 1000), done: item?.done === true })),
    logs: list(saved.logs).slice(-200).map(item => ({ id: text(item?.id, 120), time: text(item?.time, 80), text: text(item?.text, 1000) })),
  };
}

export function loadState() {
  try {
    const raw = localStorage.getItem(KEY) || '{}';
    if (raw.length > MAX_STATE_CHARS) return sanitize();
    return sanitize(JSON.parse(raw));
  }
  catch { return { ...defaultState, providerBudgets: { ...defaultState.providerBudgets } }; }
}

export function saveState(state) {
  try { localStorage.setItem(KEY, JSON.stringify(sanitize(state))); return true; }
  catch { return false; }
}