export const services = [
  {
    id: 'github',
    name: 'GitHub',
    description: 'Репозитории, задачи и сборки проекта',
    url: 'https://github.com/Aslan-Khashtyrov/ARIS',
    host: 'github.com',
  },
  {
    id: 'pocketoption',
    name: 'Pocket Option',
    description: 'Терминал наблюдения и демо-режим',
    url: 'https://m.pocketoption.com/ru/cabinet/demo-quick-high-low/',
    host: 'm.pocketoption.com',
  },
];

export const allowedHosts = new Set(services.map(service => service.host));

export function isAllowedServiceUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    if (url.protocol !== 'https:') return false;
    if (!allowedHosts.has(url.hostname)) return false;
    if (url.username || url.password) return false;
    if (url.port) return false;
    return true;
  } catch {
    return false;
  }
}
