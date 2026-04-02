import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Set output directory to land exactly inside the Python package
    outDir: path.resolve(__dirname, '../src/vata/frontend_dist'),
    emptyOutDir: true,
  },
  server: {
    // Proxy API requests to FastAPI during development
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
