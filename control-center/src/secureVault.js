import { Capacitor, registerPlugin } from '@capacitor/core';

const SecureVault = registerPlugin('SecureVault');
export const secureProviderIds = ['openai','anthropic','openrouter','kimi','google','mistral','xai'];
const validProvider = value => secureProviderIds.includes(value);

export function vaultAvailable() { return Capacitor.getPlatform() === 'android'; }
export async function storeProviderSecret(provider, secret) {
  if (!vaultAvailable() || !validProvider(provider) || typeof secret !== 'string' || !secret || secret.length > 8192) return false;
  try { const result = await SecureVault.storeSecret({ provider, secret }); return result?.stored === true; } catch { return false; }
}
export async function deleteProviderSecret(provider) {
  if (!vaultAvailable() || !validProvider(provider)) return false;
  try { const result = await SecureVault.deleteSecret({ provider }); return result?.deleted === true; } catch { return false; }
}
export async function listSecureProviders() {
  if (!vaultAvailable()) return [];
  try { const result = await SecureVault.listProviders(); return (result?.providers || []).filter(validProvider); } catch { return []; }
}
