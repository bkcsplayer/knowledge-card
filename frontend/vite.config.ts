import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Required for Docker
    port: 5173,
    watch: {
      usePolling: true,  // Required for hot-reload in Docker on Linux
    },
    hmr: {
      port: 5173,
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
  },
})

