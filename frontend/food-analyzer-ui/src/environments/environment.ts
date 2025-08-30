const host = typeof window !== 'undefined' && window.location?.hostname
  ? window.location.hostname
  : '127.0.0.1';

export const environment = {
  production: false,
  // Use the host serving the frontend so phones on LAN hit your PC's IP
  apiBase: `http://${host}:5000`,
};
