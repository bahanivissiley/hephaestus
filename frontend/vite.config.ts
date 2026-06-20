import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Autorise l'accès via le nom de service Docker (captures Playwright, tests inter-conteneurs)
    allowedHosts: ['frontend'],
  },
})
