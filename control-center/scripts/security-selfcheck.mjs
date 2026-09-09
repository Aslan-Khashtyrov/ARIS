import fs from 'node:fs';
import { isAllowedServiceUrl } from '../src/services.js';
import { normalizeBridgeUrl } from '../src/localBridge.js';
import { chooseAgent } from '../src/router.js';
import { loadState, saveState } from '../src/storage.js';
import { DEFAULT_LOCALE, getLocaleStrings, russianSource } from '../src/i18n.js';

let failed = 0;
const urlCases = [
  ['https://github.com/Aslan-Khashtyrov/ARIS', true],
  ['https://m.pocketoption.com/ru/cabinet/demo-quick-high-low/', true],
  ['https://evil.example@github.com/x', false],
  ['https://github.com:444/x', false],
  ['http://github.com/x', false],
  ['https://evil.github.com/x', false],
  ['javascript:alert(1)', false],
];
for (const [url, expected] of urlCases) {
  const actual = isAllowedServiceUrl(url);
  if (actual !== expected) { console.error(`FAIL URL: ${url}`); failed++; }
}

const bridgeCases = [
  ['http://127.0.0.1:8765', true], ['http://localhost:8765', true],
  ['https://evil.example:8765', false], ['http://0.0.0.0:8765', false],
  ['http://user:pass@127.0.0.1:8765', false], ['javascript:alert(1)', false],
];
for (const [url, expected] of bridgeCases) {
  if (Boolean(normalizeBridgeUrl(url)) !== expected) { console.error(`FAIL BRIDGE: ${url}`); failed++; }
}
for (const [prompt, expected] of [['собери android код','codex'], ['проведи аудит безопасности','gpt'], ['объясни идею','gpt']]) {
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

if (DEFAULT_LOCALE !== 'ru' || getLocaleStrings('ru') !== russianSource) {
  console.error('FAIL LANG: русский не является исходным языком'); failed++;
}
const english = getLocaleStrings('en');
if (english.nav.settings !== 'Settings' || english.nativeLanguage !== russianSource.nativeLanguage) {
  console.error('FAIL LANG: перевод или русский fallback работают неверно'); failed++;
}
const unknown = getLocaleStrings('zz');
if (unknown.hero !== russianSource.hero) { console.error('FAIL LANG: неизвестный язык не откатывается на русский'); failed++; }
const root = new URL('../src/', import.meta.url);
const read = name => fs.readFileSync(new URL(name, root), 'utf8');
const i18n = read('i18n.js');
const app = read('App.jsx');
const screens = read('Screens.jsx');
const services = read('services.js');

if (!i18n.includes('export const russianSource') || !i18n.includes("export const DEFAULT_LOCALE = 'ru'")) {
  console.error('FAIL LANG: русский источник не объявлен основным'); failed++;
}
for (const id of ['chat','agents','terminal','services','aris','tasks','logs','usage','settings']) {
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
if (!screens.includes('real_trading=false')) {
  console.error('FAIL ARIS: paper-only индикатор потерян'); failed++;
}

if (failed) process.exit(1);
console.log('PASS: русский источник, смена языка, русский fallback, навигация, router, storage, paper-only, bridge и URL-защита проверены.');