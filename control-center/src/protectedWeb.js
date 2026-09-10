import { Capacitor, registerPlugin } from '@capacitor/core';
import { Browser } from '@capacitor/browser';
import { isAllowedServiceUrl } from './services.js';

const ProtectedWeb = registerPlugin('ProtectedWeb');
const serviceIds = new Set(['github', 'pocketoption']);

export async function openProtectedService(service) {
  if (!service || !serviceIds.has(service.id) || !isAllowedServiceUrl(service.url)) return false;
  try {
    if (Capacitor.getPlatform() === 'android') {
      const result = await ProtectedWeb.open({ service: service.id });
      return result?.opened === true;
    }
    await Browser.open({ url: service.url, presentationStyle: 'fullscreen' });
    return true;
  } catch {
    return false;
  }
}
