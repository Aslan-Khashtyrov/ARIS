import { argusAllowsAiProvider } from './argus.js';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { agentRegistry, routingPolicy } from './agents.js';
import { routeKind } from './router.js';

const NativeAi = registerPlugin('NativeAi');
export const nativeAiProviders = ['mistral', 'xai', 'google', 'openrouter'];
export const nativeAiAvailable = () => Capacitor.getPlatform() === 'android' && Capacitor.isNativePlatform();
export async function nativeAiCapabilities() {
  if (!nativeAiAvailable()) return Object.fromEntries(nativeAiProviders.map(id => [id, false]));
  try { return await NativeAi.capabilities(); } catch { return Object.fromEntries(nativeAiProviders.map(id => [id, false])); }
}
export async function nativeAiGenerate({ provider, model, prompt }) {
  if (!nativeAiAvailable() || !nativeAiProviders.includes(provider) || !argusAllowsAiProvider(provider)) throw new Error('argus_blocked');
  return NativeAi.generate({ provider, model, prompt });
}

export const nativeAiDefaults = Object.freeze({
  google: 'gemini-2.5-flash',
  mistral: 'mistral-small-latest',
  xai: 'grok-4.6',
  openrouter: 'openrouter/auto',
});

const liveAgentRoutes = Object.freeze({
  gpt: { provider: 'openrouter', model: 'openai/gpt-5.6-sol' },
  claude: { provider: 'openrouter', model: 'anthropic/claude-opus-4.8' },
  kimi: { provider: 'openrouter', model: 'moonshotai/kimi-k2.6' },
  gemini: { provider: 'google', model: nativeAiDefaults.google },
  mistral: { provider: 'mistral', model: nativeAiDefaults.mistral },
  grok: { provider: 'xai', model: nativeAiDefaults.xai },
});

export function nativeRouteForAgent(agentId) { return liveAgentRoutes[agentId] || null; }

export async function chooseLiveAgent(text) {
  const capabilities = await nativeAiCapabilities();
  const kind = routeKind(text);
  const chain = [...(routingPolicy[kind] || []), ...(routingPolicy.fallback || [])];
  for (const id of chain) {
    const route = nativeRouteForAgent(id);
    if (!route || capabilities?.[route.provider] !== true || !argusAllowsAiProvider(route.provider)) continue;
    const agent = agentRegistry.find(item => item.id === id);
    if (agent) return { agent, ...route, capabilities };
  }
  return { agent: null, provider: null, model: null, capabilities };
}

export async function chooseNativeProvider(preferred = ['google', 'openrouter', 'xai', 'mistral']) {
  const capabilities = await nativeAiCapabilities();
  const provider = preferred.find(id => capabilities?.[id] === true) || null;
  return provider ? { provider, model: nativeAiDefaults[provider], capabilities } : { provider: null, model: null, capabilities };
}

export async function nativeCouncilPlan(text = '') {
  const capabilities = await nativeAiCapabilities();
  const kind = routeKind(text);
  const chain = [...(routingPolicy[kind] || []), ...(routingPolicy.fallback || [])];
  const available = [];
  for (const id of chain) {
    if (available.some(item => item.agent.id === id)) continue;
    const route = nativeRouteForAgent(id);
    if (!route || capabilities?.[route.provider] !== true || !argusAllowsAiProvider(route.provider)) continue;
    const agent = agentRegistry.find(item => item.id === id);
    if (agent) available.push({ agent, ...route });
  }
  return { primary: available[0] || null, reviewer: available[1] || null, capabilities };
}

export async function nativeCouncilGenerate(prompt) {
  const plan = await nativeCouncilPlan(prompt);
  if (!plan.primary) throw new Error('native_ai_unavailable');
  const primary = await nativeAiGenerate({ provider: plan.primary.provider, model: plan.primary.model, prompt });
  if (!plan.reviewer) return { plan, primary, review: null };
  const reviewPrompt = `Независимо проверь ответ другого ИИ. Укажи конкретные ошибки, риски и затем дай улучшенный итог.\n\nЗАДАЧА:\n${prompt}\n\nОТВЕТ ДЛЯ ПРОВЕРКИ:\n${primary.text || ''}`;
  const review = await nativeAiGenerate({ provider: plan.reviewer.provider, model: plan.reviewer.model, prompt: reviewPrompt });
  return { plan, primary, review };
}
