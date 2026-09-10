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
