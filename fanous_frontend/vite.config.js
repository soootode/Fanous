import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        auth: resolve(__dirname, 'auth.html'),
        about: resolve(__dirname, 'about.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        profile: resolve(__dirname, 'profile.html'),
        scenario: resolve(__dirname, 'scenario.html'),
        resetPassword: resolve(__dirname, 'reset-password.html')
      }
    }
  }
});
