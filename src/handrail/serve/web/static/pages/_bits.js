// Shared widgets: the small parts more than one page needs.
import { h, fmt, fileUrl } from '../app.js';

export const chip = (kind, text) => h('span', { class: `chip chip-${kind}` }, text);
export const stateChip = (s) => chip(s || 'draft', s || 'draft');
const CAT = { SUCCESS: 'success', BUSINESS_OUTCOME: 'business', RECOVERABLE: 'recoverable', HARD_FAILURE: 'hard' };
export const catChip = (c) => (c ? chip(CAT[c] || 'draft', c) : h('span', { class: 'muted' }, '-'));
export const effectChip = (k) => chip(k || 'read', k || 'read');
export const empty = (text) => h('p', { class: 'empty' }, text);

export function pageHead(title, sub, ...actions) {
  return h('div', { class: 'head' }, h('h1', null, title), h('div', { class: 'row' }, actions),
    sub ? h('p', { class: 'sub' }, sub) : null);
}

export const stat = (value, label, note, cls = '') =>
  h('div', { class: `stat ${cls}` }, h('b', null, value), h('span', null, label),
    note ? h('small', null, note) : null);

/** table([{label, cell: row => node, cls}], rows, emptyText, {rowClass}) */
export function table(cols, rows, emptyText, opts = {}) {
  if (!rows || !rows.length) return empty(emptyText);
  return h('div', { class: 'scroll' }, h('table', { class: 'table' },
    h('thead', null, h('tr', null, cols.map((c) => h('th', { class: c.cls }, c.label)))),
    h('tbody', null, rows.map((r) => h('tr', { class: opts.rowClass ? opts.rowClass(r) : null },
      cols.map((c) => h('td', { class: c.cls }, c.cell(r))))))));
}

const LIFE = ['draft', 'verified', 'approved', 'deprecated'];
export function stepper(state) {
  const at = LIFE.indexOf(state);
  return h('div', { class: 'stepper' }, LIFE.map((s, i) =>
    h('span', { class: i === at ? `on${s === 'deprecated' ? ' bad' : ''}` : i < at ? 'done' : '' },
      (i < at ? '✓ ' : '') + s)));
}

export function filmstrip(runId, shots) {
  if (!shots || !shots.length) return empty('No screenshots were kept for this run.');
  return h('div', { class: 'filmstrip' }, shots.map((s) => {
    const url = fileUrl(runId, s.png);
    return h('a', { href: url, target: '_blank', rel: 'noopener', title: 'Open full size' },
      h('img', { src: url, alt: s.label, loading: 'lazy' }), h('span', null, s.label));
  }));
}

/** The live legacy screen. set(msg) paints a frame message; wait text shows until one arrives. */
export function frameView(caption, waitText = 'Waiting for the first frame') {
  const wait = h('div', { class: 'frame-wait' }, waitText);
  const img = h('img', { class: 'shot', alt: 'Live screen', hidden: true });
  const who = h('div', { class: 'who' }, caption);
  const el = h('div', { class: 'frame-border' }, who, wait, img);
  return {
    el, who,
    set(msg) {
      img.src = `data:${msg.mime || 'image/jpeg'};base64,${msg.jpeg}`;
      img.hidden = false; wait.hidden = true;
    },
    mode(cls, text) { el.className = `frame-border ${cls}`; who.textContent = text; },
  };
}

export const when = (iso) => (iso ? fmt.date(iso) : '-');
export const download = (name, data) => {
  const a = h('a', { href: URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })), download: name });
  a.click();
};
