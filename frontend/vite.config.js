import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development the browser talks ONLY to http://localhost:5173.
// Vite forwards anything starting with /api to the FastAPI server, so the
// browser sees one origin and the session cookie works without CORS surprises.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  test: { environment: 'node' },
})
