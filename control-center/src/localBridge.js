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

export async function checkBridge(raw, timeoutMs = 2000) {
  const base = normalizeBridgeUrl(raw);
  if (!base) return { ok: false, reason: 'invalid' };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${base}/health`, {
      method: 'GET', signal: controller.signal, cache: 'no-store',
      credentials: 'omit', redirect: 'error', referrerPolicy: 'no-referrer',
    });
    return { ok: response.ok, reason: response.ok ? 'ok' : 'http' };
  } catch {
    return { ok: false, reason: 'offline' };
  } finally {
    clearTimeout(timer);
  }
}
