import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Served by Flask as /static/goita_app/*
  base: '/static/goita_app/',
  build: {
    outDir: path.resolve(__dirname, '../static/goita_app'),
    emptyOutDir: true,
  },
})
