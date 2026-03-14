import { defineConfig } from 'vite';

export default defineConfig({
  base: '/industry_by_size/',
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
  },
});
