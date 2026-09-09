import fs from 'node:fs';
import { isAllowedServiceUrl } from '../src/services.js';

const urlCases = [
  ['https://github.com/Aslan-Khashtyrov/ARIS', true],
  ['https://m.pocketoption.com/ru/cabinet/demo-quick-high-low/', true],
  ['https://evil.example@github.com/x', false],
  ['https://github.com:444/x', false],
  ['http://github.com/x', false],
  ['https://evil.github.com/x', false],
  ['javascript:alert(1)', false],
];

let failed = 0;
for (const [url, expected] of urlCases) {
  const actual = isAllowedServiceUrl(url);
  if (actual !== expected) {
    console.error(`FAIL URL: ${url} -> ${actual}, ожидалось ${expected}`);
    failed++;
  }
}

const i18n = fs.readFileSync(new URL('../src/i18n.js', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8');

if (!i18n.includes('export const russianSource')) {
  console.error('FAIL LANG: русский источник не объявлен основным');
  failed++;
}
if (/\ben\s*:/.test(i18n) || i18n.includes('PERSONAL AI SYSTEM')) {
  console.error('FAIL LANG: найден параллельный английский каталог');
  failed++;
}
if (!app.includes("tab === 'chat'") || !app.includes("tab === 'services'") || !app.includes('PlaceholderScreen')) {
  console.error('FAIL NAV: отдельные экраны навигации не рендерятся');
  failed++;
}
if (app.includes('Система сама выбирает сильнейшего доступного агента')) {
  console.error('FAIL LANG: русский интерфейсный текст захардкожен вне русского источника');
  failed++;
}

if (failed) process.exit(1);
console.log('PASS: проверки русского источника, навигации и URL-защиты пройдены.');
