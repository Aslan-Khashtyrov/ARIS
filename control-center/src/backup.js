import { defaultState } from './storage.js';
const FORMAT = 'project-one-backup';
const VERSION = 1;
const MAX_IMPORT_CHARS = 512 * 1024;
const SAFE_KEYS = ['locale','monthlyBudget','providerBudgets','chatHistory','missions','tasks','logs'];
function backupState(state = {}) {
  const safe = {};
  for (const key of SAFE_KEYS) if (Object.prototype.hasOwnProperty.call(state, key)) safe[key] = state[key];
  return { ...safe, safeMode: true, localBridgeEnabled: false, bridgeUrl: defaultState.bridgeUrl };
}
export function createBackup(state) {
  return JSON.stringify({ format: FORMAT, version: VERSION, createdAt: new Date().toISOString(), state: backupState(state) }, null, 2);
}
export function parseBackup(raw) {
  if (typeof raw !== 'string' || raw.length > MAX_IMPORT_CHARS) return null;
  try {
    const data = JSON.parse(raw);
    if (data?.format !== FORMAT || data?.version !== VERSION || !data.state || typeof data.state !== 'object' || Array.isArray(data.state)) return null;
    return backupState(data.state);
  } catch { return null; }
}
export function downloadBackup(state) {
  const blob = new Blob([createBackup(state)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = `project-one-backup-${new Date().toISOString().slice(0,10)}.json`; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
