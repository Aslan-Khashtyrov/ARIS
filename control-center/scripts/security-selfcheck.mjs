import fs from 'node:fs';
import { isAllowedServiceUrl } from '../src/services.js';
import { checkBridge, normalizeBridgeUrl } from '../src/localBridge.js';
import { chooseAgent } from '../src/router.js';
import { loadState, saveState } from '../src/storage.js';
import { DEFAULT_LOCALE, getLocaleStrings, russianSource } from '../src/i18n.js';
import { runSecurityDiagnostics } from '../src/securityDiagnostics.js';

let failed = 0;
const urlCases = [
  ['https://github.com/Aslan-Khashtyrov/ARIS', true],
  ['https://m.pocketoption.com/ru/cabinet/demo-quick-high-low/', true],
  ['https://evil.example@github.com/x', false],
  ['https://github.com:444/x', false],
  ['http://github.com/x', false],
  ['https://evil.github.com/x', false],
  ['javascript:alert(1)', false],
  ['https://github.com/evil/arbitrary/path?token=x#frag', false],
  ['https://github.com/Aslan-Khashtyrov/ARIS?x=1', false],
];
for (const [url, expected] of urlCases) {
  const actual = isAllowedServiceUrl(url);
  if (actual !== expected) { console.error(`FAIL URL: ${url}`); failed++; }
}

const bridgeCases = [
  ['http://127.0.0.1:8765', true], ['http://localhost:8765', true],
  ['https://evil.example:8765', false], ['http://0.0.0.0:8765', false],
  ['http://user:pass@127.0.0.1:8765', false], ['javascript:alert(1)', false],
  ['http://[::1]:8765', false], ['http://0x7f000001:8765', false], ['http://2130706433:8765', false], ['http://localhost.:8765', false],
];
for (const [url, expected] of bridgeCases) {
  if (Boolean(normalizeBridgeUrl(url)) !== expected) { console.error(`FAIL BRIDGE: ${url}`); failed++; }
}

let bridgeFetch = null;
globalThis.fetch = async (url, options) => { bridgeFetch = { url, options }; return { ok: true }; };
const bridgeHealth = await checkBridge('http://127.0.0.1:8765');
if (!bridgeHealth.ok || bridgeFetch?.url !== 'http://127.0.0.1:8765/health' || bridgeFetch?.options?.redirect !== 'error' || bridgeFetch?.options?.credentials !== 'omit' || bridgeFetch?.options?.referrerPolicy !== 'no-referrer') {
  console.error('FAIL BRIDGE: health-check может следовать редиректам или передавать лишние данные'); failed++;
}
if (!fs.readFileSync(new URL('../src/agents.js', import.meta.url), 'utf8').includes("id: 'kimi'")) { console.error('FAIL AGENTS: Kimi не зарегистрирован'); failed++; }
for (const [prompt, expected] of [['собери android код','codex'], ['проведи аудит безопасности','gpt'], ['проверь код приложения на уязвимости и сделай security review','gpt'], ['объясни идею','gpt']]) {
  const agent = chooseAgent(prompt);
  if (agent?.id !== expected) { console.error(`FAIL ROUTER: ${prompt} -> ${agent?.id}`); failed++; }
}

globalThis.localStorage = {
  value: '',
  getItem() { return this.value; },
  setItem(_key, value) { this.value = value; },
};
localStorage.value = JSON.stringify({ locale: 'xx', safeMode: 'no', monthlyBudget: -5, chatHistory: [{ kind: 'x', author: 'A'.repeat(200), text: 'B'.repeat(5000) }] });
const safeState = loadState();
if (safeState.locale !== DEFAULT_LOCALE || safeState.safeMode !== true || safeState.monthlyBudget !== 0 || safeState.chatHistory[0].author.length > 80 || safeState.chatHistory[0].text.length > 4000) {
  console.error('FAIL STORAGE: сохранённое состояние не санитизируется'); failed++;
}
if (!saveState(safeState)) { console.error('FAIL STORAGE: безопасное состояние не сохраняется'); failed++; }
localStorage.value = JSON.stringify({ missions: Array.from({ length: 70 }, (_, i) => ({ id: `m${i}`, text: 'X'.repeat(3000), agent: 'A'.repeat(200), status: 'running', createdAt: 'Z'.repeat(200) })) });
const missionState = loadState();
if (missionState.missions.length !== 50 || missionState.missions[0].text.length > 1600 || missionState.missions[0].agent.length > 80 || missionState.missions[0].status !== 'prepared') {
  console.error('FAIL STORAGE: поручения не ограничены или не санитизируются'); failed++;
}
const diagnostics = runSecurityDiagnostics({ ...safeState, safeMode: true });
if (!diagnostics.ok || diagnostics.passed !== diagnostics.total || diagnostics.total < 6) {
  console.error('FAIL SECURITY CENTER: базовые защитные проверки не проходят'); failed++;
}

localStorage.value = JSON.stringify({ safeMode: false, locale: 'en' });
if (loadState().safeMode !== true) { console.error('FAIL STORAGE: safe mode можно отключить через сохранённое состояние'); failed++; }
localStorage.value = 'x'.repeat(600 * 1024);
const oversizedState = loadState();
if (oversizedState.locale !== DEFAULT_LOCALE || oversizedState.safeMode !== true || oversizedState.chatHistory.length !== 0) {
  console.error('FAIL STORAGE: слишком большое сохранённое состояние не отбрасывается'); failed++;
}

if (DEFAULT_LOCALE !== 'ru' || getLocaleStrings('ru') !== russianSource) {
  console.error('FAIL LANG: русский не является исходным языком'); failed++;
}
const english = getLocaleStrings('en');
if (english.nav.settings !== 'Settings' || english.nativeLanguage !== russianSource.nativeLanguage) {
  console.error('FAIL LANG: перевод или русский fallback работают неверно'); failed++;
}
for (const locale of ['zz', 'constructor', '__proto__', 'toString']) {
  const unknown = getLocaleStrings(locale);
  if (unknown !== russianSource || unknown.hero !== russianSource.hero) { console.error(`FAIL LANG: неизвестный язык ${locale} не откатывается на русский`); failed++; }
}
const root = new URL('../src/', import.meta.url);
const read = name => fs.readFileSync(new URL(name, root), 'utf8');
const i18n = read('i18n.js');
const app = read('App.jsx');
const screens = read('Screens.jsx');
const services = read('services.js');
const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const manifest = fs.readFileSync(new URL('../android/app/src/main/AndroidManifest.xml', import.meta.url), 'utf8');
const networkSecurity = fs.readFileSync(new URL('../android/app/src/main/res/xml/network_security_config.xml', import.meta.url), 'utf8');
const filePaths = fs.readFileSync(new URL('../android/app/src/main/res/xml/file_paths.xml', import.meta.url), 'utf8');

if (!i18n.includes('export const russianSource') || !i18n.includes("export const DEFAULT_LOCALE = 'ru'")) {
  console.error('FAIL LANG: русский источник не объявлен основным'); failed++;
}
for (const id of ['home','chat','agents','terminal','services','aris','missions','tasks','security','logs','usage','settings']) {
  if (!app.includes(`${id}: <`)) { console.error(`FAIL NAV: экран ${id} не подключён`); failed++; }
}
if (/[А-Яа-яЁё]/.test(app) || /[А-Яа-яЁё]/.test(screens)) {
  console.error('FAIL LANG: пользовательский русский текст найден вне русского источника'); failed++;
}
if (!screens.includes('supportedLanguages.map') || !screens.includes('state.locale')) {
  console.error('FAIL LANG: выбор языка в настройках не подключён'); failed++;
}
if (!services.includes("url.username || url.password") || !services.includes("url.port")) {
  console.error('FAIL URL: защита userinfo/портов отсутствует'); failed++;
}
if (services.includes('description:') || screens.includes('service.description')) {
  console.error('FAIL LANG: описание сервиса обходит русский источник локализации'); failed++;
}
if (!screens.includes('real_trading=false')) {
  console.error('FAIL ARIS: paper-only индикатор потерян'); failed++;
}

if (html.includes("style-src 'self' 'unsafe-inline'") || !html.includes("base-uri 'none'") || !html.includes("form-action 'none'")) {
  console.error('FAIL CSP: политика контента ослаблена'); failed++;
}

if (!manifest.includes('android:allowBackup="false"') || !manifest.includes('android:networkSecurityConfig="@xml/network_security_config"')) {
  console.error('FAIL ANDROID: backup или network security настроены небезопасно'); failed++;
}
const permissions = [...manifest.matchAll(/<uses-permission android:name="([^"]+)"/g)].map(match => match[1]);
if (permissions.length !== 1 || permissions[0] !== 'android.permission.INTERNET') {
  console.error(`FAIL ANDROID: лишние разрешения: ${permissions.join(', ')}`); failed++;
}
if (!networkSecurity.includes('<base-config cleartextTrafficPermitted="false"') || !networkSecurity.includes('>localhost</domain>') || !networkSecurity.includes('>127.0.0.1</domain>')) {
  console.error('FAIL ANDROID: cleartext должен быть закрыт везде кроме loopback'); failed++;
}
if (filePaths.includes('<external-path') || !filePaths.includes('path="shared/"')) {
  console.error('FAIL ANDROID: FileProvider имеет слишком широкий доступ'); failed++;
}

if (failed) process.exit(1);
console.log('PASS: русский источник, смена языка, русский fallback, навигация, router, storage, paper-only, bridge и URL-защита проверены.');