/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The platform admin lives at /admin/ and calls /api/console/ on its own origin,
// signed in with a session cookie. In development Vite forwards /api to Django
// (override with API_TARGET). The Host header is kept so Django's CSRF origin
// check sees the same origin the browser does.
const apiTarget = process.env.API_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  base: '/admin/',
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': { target: apiTarget },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
