export const services = [
  {
    id: 'github',
    name: 'GitHub',
    url: 'https://github.com/Aslan-Khashtyrov/ARIS',
    host: 'github.com',
  },
  {
    id: 'pocketoption',
    name: 'Pocket Option',
    url: 'https://m.pocketoption.com/ru/cabinet/demo-quick-high-low/',
    host: 'm.pocketoption.com',
  },
];

export const allowedHosts = new Set(services.map(service => service.host));
export const allowedServiceUrls = new Set(services.map(service => new URL(service.url).href));

export function isAllowedServiceUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    if (url.protocol !== 'https:') return false;
    if (!allowedHosts.has(url.hostname)) return false;
    if (url.username || url.password || url.port) return false;
    if (url.search || url.hash) return false;
    return allowedServiceUrls.has(url.href);
  } catch {
    return false;
  }
}
