import { defineConfig } from 'vite';
// Dev: the browser calls /api on its own address and Vite forwards it to the backend, so there is no CORS to configure.
// API_TARGET overrides the backend address, for example when it runs on another port.
export default defineConfig({ base: './', server: { proxy: { '/api': process.env.API_TARGET ?? 'http://localhost:8000' } } });
