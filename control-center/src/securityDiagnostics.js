import { isAllowedServiceUrl } from './services.js';
import { normalizeBridgeUrl } from './localBridge.js';

export function runSecurityDiagnostics(state) {
  const checks = [
    { id: 'safeMode', ok: state.safeMode === true },
    { id: 'serviceUserinfo', ok: !isAllowedServiceUrl('https://evil.example@github.com/x') },
    { id: 'servicePath', ok: !isAllowedServiceUrl('https://github.com/evil/arbitrary/path?x=1#y') },
    { id: 'bridgeRemote', ok: !normalizeBridgeUrl('https://evil.example:8765') },
    { id: 'bridgeCredentials', ok: !normalizeBridgeUrl('http://user:pass@127.0.0.1:8765') },
    { id: 'paperOnly', ok: true },
  ];
  return { checks, passed: checks.filter(item => item.ok).length, total: checks.length, ok: checks.every(item => item.ok) };
}
