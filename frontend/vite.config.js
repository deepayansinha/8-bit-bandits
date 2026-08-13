import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/ask': 'http://localhost:8000',
    },
  },
})
