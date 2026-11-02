// The address book: where the API lives. Same origin unless a deployer says otherwise.
// Order: window.HANDRAIL_API, then <meta name="handrail-api">, then "" (same origin).
const meta = document.querySelector('meta[name="handrail-api"]');
const raw = window.HANDRAIL_API || (meta && meta.content) || '';

export const API_BASE = raw.replace(/\/+$/, '');

export const WS_URL = API_BASE
  ? `${API_BASE.replace(/^http/, 'ws')}/ws`
  : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
