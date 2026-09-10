import { argusAllowsAiProvider } from './argus.js';
import { Capacitor, registerPlugin } from '@capacitor/core';

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

export async function chooseNativeProvider(preferred = ['google', 'openrouter', 'xai', 'mistral']) {
  const capabilities = await nativeAiCapabilities();
  const provider = preferred.find(id => capabilities?.[id] === true) || null;
  return provider ? { provider, model: nativeAiDefaults[provider], capabilities } : { provider: null, model: null, capabilities };
}

export async function nativeCouncilPlan(preferred = ['google', 'openrouter', 'xai', 'mistral']) {
  const capabilities = await nativeAiCapabilities();
  const available = preferred.filter(id => capabilities?.[id] === true);
  return { primary: available[0] ? { provider: available[0], model: nativeAiDefaults[available[0]] } : null, reviewer: available[1] ? { provider: available[1], model: nativeAiDefaults[available[1]] } : null, capabilities };
}

export async function nativeCouncilGenerate(prompt, preferred) {
  const plan = await nativeCouncilPlan(preferred);
  if (!plan.primary) throw new Error('native_ai_unavailable');
  const primary = await nativeAiGenerate({ ...plan.primary, prompt });
  if (!plan.reviewer) return { plan, primary, review: null };
  const reviewPrompt = `Независимо проверь ответ другого ИИ. Укажи конкретные ошибки, риски и затем дай улучшенный итог.\n\nЗАДАЧА:\n${prompt}\n\nОТВЕТ ДЛЯ ПРОВЕРКИ:\n${primary.text || ''}`;
  const review = await nativeAiGenerate({ ...plan.reviewer, prompt: reviewPrompt });
  return { plan, primary, review };
}
