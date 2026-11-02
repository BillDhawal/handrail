// The front desk: a hash router, a fetch helper, a socket that keeps redialling.
// Pages are small modules under pages/; each default-exports render(root, ctx).
import { API_BASE, WS_URL } from './config.js';

const ENT = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const escape = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ENT[c]);

/** h('div', {class:'x', onclick}, child, [children], 'text') builds nodes, never parses HTML. */
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  let value;
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'value') value = v;
    else if (k === 'checked' || k === 'disabled' || k === 'selected') el[k] = true;
    else el.setAttribute(k, v === true ? '' : v);
  }
  const add = (c) => {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(add);
    else el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  };
  children.forEach(add);
  if (value !== undefined) el.value = value;
  return el;
}

const pad = (n) => String(n).padStart(2, '0');
export const fmt = {
  date(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    const mon = d.toLocaleString(undefined, { month: 'short' });
    return `${d.getDate()} ${mon}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  },
  time(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  },
  ms(n) {
    if (n == null) return '-';
    return n < 1000 ? `${Math.round(n)} ms` : `${(n / 1000).toFixed(1)} s`;
  },
  rate(r) { return r == null ? '-' : `${Math.round(r * 100)}%`; },
  clock(secs) { return `${pad(Math.floor(secs / 60))}:${pad(Math.floor(secs % 60))}`; },
};

// One door for every API address, so a split deploy changes one place.
export const apiUrl = (path) => `${API_BASE}${path}`;

// ---- backend: real by default, swapped for fixtures with ?demo ----
async function realApi(path, opts = {}) {
  const init = { method: opts.method || 'GET', headers: {}, credentials: 'omit' };
  if (opts.body !== undefined) {
    init.method = opts.method || 'POST';
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(opts.body);
  }
  const res = await fetch(apiUrl(path), init);
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok || (data && data.error && !Array.isArray(data))) {
    throw new Error((data && data.error) || `${res.status} ${res.statusText}`);
  }
  return data;
}

function realWs(onMessage) {
  let sock, stopped = false, wait = 500, timer;
  const open = () => {
    sock = new WebSocket(WS_URL);
    sock.onopen = () => { wait = 500; };
    sock.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch { /* ignore */ } };
    sock.onclose = () => {
      if (stopped) return;
      timer = setTimeout(open, wait);
      wait = Math.min(wait * 2, 8000);
    };
  };
  open();
  return () => { stopped = true; clearTimeout(timer); sock && sock.close(); };
}

const backend = { api: realApi, ws: realWs, fileUrl: (run, name) => apiUrl(`/api/runs/${run}/files/${name}`) };
export const api = (path, opts) => backend.api(path, opts);
export const ws = (onMessage) => backend.ws(onMessage);
export const fileUrl = (run, name) => backend.fileUrl(run, name);
window.handrail = { api, ws };

if (new URLSearchParams(location.search).has('demo')) {
  const demo = await import('./dev-data.js');
  Object.assign(backend, demo.backend);
}

// ---- router ----
const ROUTES = [
  [/^$|^\/$/, 'home', 'home'],
  [/^\/author$/, 'author', 'author'],
  [/^\/cards\/(.+)$/, 'card', 'catalog'],
  [/^\/runs$/, 'history', 'runs'],
  [/^\/runs\/(.+)$/, 'run', 'runs'],
  [/^\/live$/, 'live', 'live'],
  [/^\/drift$/, 'drift', 'drift'],
  [/^\/catalog$/, 'catalog', 'catalog'],
];
const view = document.getElementById('view');
let cleanup = null, token = 0;

function parseHash() {
  const [path, qs] = location.hash.replace(/^#/, '').split('?');
  return { path: path || '/', query: new URLSearchParams(qs || '') };
}

async function route() {
  const my = ++token;
  if (cleanup) { try { cleanup(); } catch { /* ignore */ } cleanup = null; }
  const { path, query } = parseHash();
  let hit = null;
  for (const [re, mod, nav] of ROUTES) {
    const m = path.match(re);
    if (m) { hit = { mod, nav, args: m.slice(1).map(decodeURIComponent) }; break; }
  }
  document.querySelectorAll('.nav a[data-nav]').forEach((a) => {
    a.classList.toggle('active', !!hit && a.dataset.nav === hit.nav);
  });
  view.replaceChildren();
  if (!hit) {
    view.append(h('h1', null, 'Not found'), h('p', { class: 'muted' }, `No page at ${path}.`));
    return;
  }
  try {
    const page = await import(`./pages/${hit.mod}.js`);
    if (my !== token) return;
    const fn = await page.default(view, { args: hit.args, query });
    if (my !== token) { if (fn) fn(); return; }
    cleanup = fn || null;
  } catch (e) {
    if (my !== token) return;
    view.replaceChildren(h('h1', null, 'Something went wrong'),
      h('div', { class: 'card' }, h('p', { class: 'err' }, e.message)));
  }
}

window.addEventListener('hashchange', route);
route();
