import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  envDir: '../',
  build: {
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.js',
    include: ['src/__tests__/**/*.test.jsx'],
  },
})
