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
    return url.protocol === 'https:' && allowedHosts.has(url.hostname);
  } catch {
    return false;
  }
}
