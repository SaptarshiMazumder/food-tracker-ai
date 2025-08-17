import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: true, // listen on 0.0.0.0
    port: 4200,
    // allow all trycloudflare subdomains (works across runs)
    allowedHosts: ['.trycloudflare.com'],
    // helps HMR over HTTPS tunnel
    hmr: {
      clientPort: 443,
      protocol: 'wss',
    },
  },
});
