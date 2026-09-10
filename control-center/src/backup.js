import { defaultState } from './storage.js';
const FORMAT = 'project-one-backup';
const VERSION = 1;
const MAX_IMPORT_CHARS = 512 * 1024;
export function createBackup(state) {
  const safe = { ...state, safeMode: true, localBridgeEnabled: false, bridgeUrl: defaultState.bridgeUrl };
  return JSON.stringify({ format: FORMAT, version: VERSION, createdAt: new Date().toISOString(), state: safe }, null, 2);
}
export function parseBackup(raw) {
  if (typeof raw !== 'string' || raw.length > MAX_IMPORT_CHARS) return null;
  try {
    const data = JSON.parse(raw);
    if (data?.format !== FORMAT || data?.version !== VERSION || !data.state || typeof data.state !== 'object' || Array.isArray(data.state)) return null;
    return { ...data.state, safeMode: true, localBridgeEnabled: false, bridgeUrl: defaultState.bridgeUrl };
  } catch { return null; }
}
export function downloadBackup(state) {
  const blob = new Blob([createBackup(state)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = `project-one-backup-${new Date().toISOString().slice(0,10)}.json`; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
