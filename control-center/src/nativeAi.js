import { Capacitor, registerPlugin } from '@capacitor/core';

const NativeAi = registerPlugin('NativeAi');
export const nativeAiProviders = ['mistral', 'xai', 'google'];
export const nativeAiAvailable = () => Capacitor.getPlatform() === 'android' && Capacitor.isNativePlatform();
export async function nativeAiCapabilities() {
  if (!nativeAiAvailable()) return Object.fromEntries(nativeAiProviders.map(id => [id, false]));
  try { return await NativeAi.capabilities(); } catch { return Object.fromEntries(nativeAiProviders.map(id => [id, false])); }
}
export async function nativeAiGenerate({ provider, model, prompt }) {
  if (!nativeAiAvailable() || !nativeAiProviders.includes(provider)) throw new Error('native_ai_unavailable');
  return NativeAi.generate({ provider, model, prompt });
}

export const nativeAiDefaults = Object.freeze({
  google: 'gemini-2.5-flash',
  mistral: 'mistral-small-latest',
  xai: 'grok-4.6',
});

export async function chooseNativeProvider(preferred = ['google', 'xai', 'mistral']) {
  const capabilities = await nativeAiCapabilities();
  const provider = preferred.find(id => capabilities?.[id] === true) || null;
  return provider ? { provider, model: nativeAiDefaults[provider], capabilities } : { provider: null, model: null, capabilities };
}
