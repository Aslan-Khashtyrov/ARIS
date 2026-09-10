const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost']);

export function normalizeBridgeUrl(raw) {
  try {
    const input = String(raw || '').trim();
    const literal = input.match(/^(https?):\/\/([^\/:?#]+)(?::(\d+))?\/?$/i);
    if (!literal) return null;
    const literalHost = literal[2].toLowerCase();
    if (!LOOPBACK_HOSTS.has(literalHost)) return null;
    const url = new URL(input);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    if (!LOOPBACK_HOSTS.has(url.hostname)) return null;
    if (url.username || url.password || url.search || url.hash) return null;
    if (url.pathname !== '/' && url.pathname !== '') return null;
    const port = url.port ? Number(url.port) : (url.protocol === 'https:' ? 443 : 80);
    if (!Number.isInteger(port) || port < 1 || port > 65535) return null;
    return `${url.protocol}//${url.host}`;
  } catch {
    return null;
  }
}

export async function bridgeRequest(raw, path, body = null, timeoutMs = 120000) {
  const base = normalizeBridgeUrl(raw);
  if (!base || !['/health', '/v1/agent'].includes(path)) return { ok: false, reason: 'invalid' };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${base}${path}`, { method: body ? 'POST' : 'GET', signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error', referrerPolicy: 'no-referrer', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
    const data = typeof response.json === 'function' ? await response.json().catch(() => ({})) : {};
    return { ok: response.ok, reason: response.ok ? 'ok' : (data.error || 'http'), ...data };
  } catch { return { ok: false, reason: 'offline' }; } finally { clearTimeout(timer); }
}

export async function runLocalAgent(raw, agent, prompt) {
  if (!['codex', 'hermes'].includes(agent)) return { ok: false, reason: 'agent_blocked' };
  const value = String(prompt || '').trim();
  if (!value || value.length > 16000) return { ok: false, reason: 'prompt_invalid' };
  return bridgeRequest(raw, '/v1/agent', { agent, prompt: value });
}

export async function checkBridge(raw, timeoutMs = 2000) {
  const base = normalizeBridgeUrl(raw);
  if (!base) return { ok: false, reason: 'invalid' };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const result = await bridgeRequest(base, '/health', null, timeoutMs);
    return { ok: result.ok, reason: result.reason, agents: Array.isArray(result.agents) ? result.agents : [], mode: result.mode || null };
  } catch {
    return { ok: false, reason: 'offline' };
  } finally {
    clearTimeout(timer);
  }
}
