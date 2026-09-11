import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.aslan.personalai',
  appName: 'Project One',
  webDir: 'dist',
  server: {
    androidScheme: 'https'
  }
};

export default config;