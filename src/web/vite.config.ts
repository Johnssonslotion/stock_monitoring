import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = process.env.VITE_API_TARGET || env.VITE_API_TARGET || 'http://localhost:8000'; // Prioritize Process Env

  console.log(`🚀 Vite Proxy Target: ${apiTarget} (Mode: ${mode})`);

  return {
    plugins: [react()],
    server: {
      host: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
          headers: {
            'x-api-key': 'super-secret-key' // Required for API authentication
          }
        },
        '/system': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
        '/candles': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
        '/orderbook': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
        '/executions': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        }
      },
    },
  }
})
