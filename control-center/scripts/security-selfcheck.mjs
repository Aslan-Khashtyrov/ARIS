import fs from 'node:fs';
import { isAllowedServiceUrl } from '../src/services.js';
import { normalizeBridgeUrl } from '../src/localBridge.js';

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
  if (actual !== expected) {
    console.error(`FAIL URL: ${url} -> ${actual}, ожидалось ${expected}`); failed++;
  }
}

const bridgeCases = [
  ['http://127.0.0.1:8765', true], ['http://localhost:8765', true],
  ['https://evil.example:8765', false], ['http://0.0.0.0:8765', false],
  ['http://user:pass@127.0.0.1:8765', false], ['javascript:alert(1)', false],
];
for (const [url, expected] of bridgeCases) {
  const actual = Boolean(normalizeBridgeUrl(url));
  if (actual !== expected) { console.error(`FAIL BRIDGE: ${url}`); failed++; }
}

const root = new URL('../src/', import.meta.url);
const read = name => fs.readFileSync(new URL(name, root), 'utf8');
const i18n = read('i18n.js');
const app = read('App.jsx');
const screens = read('Screens.jsx');
const services = read('services.js');

if (!i18n.includes('export const russianSource')) {
  console.error('FAIL LANG: русский источник не объявлен основным'); failed++;
}
if (/\ben\s*:/.test(i18n) || i18n.includes('PERSONAL AI SYSTEM')) {
  console.error('FAIL LANG: найден параллельный английский каталог'); failed++;
}
for (const id of ['chat','agents','terminal','services','aris','tasks','logs','usage','settings']) {
  if (!app.includes(`${id}: <`)) { console.error(`FAIL NAV: экран ${id} не подключён`); failed++; }
}
if (/[А-Яа-яЁё]/.test(app) || /[А-Яа-яЁё]/.test(screens)) {
  console.error('FAIL LANG: пользовательский русский текст найден вне русского источника'); failed++;
}
if (!services.includes("url.username || url.password") || !services.includes("url.port")) {
  console.error('FAIL URL: защита userinfo/портов отсутствует'); failed++;
}
if (!screens.includes('real_trading=false')) {
  console.error('FAIL ARIS: paper-only индикатор потерян'); failed++;
}

if (failed) process.exit(1);
console.log('PASS: русский источник, навигация, paper-only, bridge и URL-защита проверены.');
