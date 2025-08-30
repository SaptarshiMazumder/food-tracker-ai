// vite.config.ts
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: true,
    port: 4200,
    allowedHosts: true, 
  }
})
