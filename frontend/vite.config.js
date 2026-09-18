import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  // GitHub Pages serves a project repo under /<repo>/; the Pages workflow sets this.
  base: process.env.FP_BASE || '/',
  plugins: [react(), tailwindcss()],
  server: {
    // The Flask API runs separately; proxying keeps the frontend origin-relative.
    proxy: { '/api': 'http://localhost:5001' },
  },
})
