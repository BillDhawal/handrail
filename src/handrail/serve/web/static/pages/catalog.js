// The catalog is the shop window other agents see over MCP: approved cards only,
// and only those with a description and a reliability figure to put on the label.
import { h, api, fmt } from '../app.js';
import { pageHead, chip, catChip, empty, download } from './_bits.js';

function missing(c) {
  const m = [];
  if (!c.description) m.push('a description');
  if (!c.reliability || !c.reliability.replays) m.push('a reliability figure');
  return m;
}

function tile(c) {
  const gaps = missing(c);
  const rel = c.reliability || {};
  return h('article', { class: `card${gaps.length ? ' grey' : ''}` },
    h('div', { class: 'row' }, h('h3', { class: 'mono' }, c.id), chip(c.read_or_write || 'read', (c.read_or_write || 'read').toUpperCase())),
    h('p', { class: 'small' }, c.description || h('i', null, 'No description.')),
    h('dl', { class: 'kv' },
      h('dt', null, 'Approved'), h('dd', null, `${c.approved_by || '-'}, ${fmt.date(c.approved_at)}`),
      h('dt', null, 'Success'), h('dd', null, rel.replays ? `${fmt.rate(c.success_rate ?? rel.clean / rel.replays)} of ${rel.replays} replays` : '-'),
      h('dt', null, 'Last run'), h('dd', null, c.last_run ? [catChip(c.last_run.category), ' ', fmt.date(c.last_run.started_at)] : 'never'),
      h('dt', null, 'MCP tool'), h('dd', { class: 'mono' }, c.id.replace(/\./g, '_'))),
    gaps.length ? h('p', { class: 'err small' }, `Not listed: missing ${gaps.join(' and ')}.`) : null,
    h('div', { class: 'row' },
      h('a', { class: 'btn btn-primary', href: `#/live?file=${encodeURIComponent(c.file)}` }, 'Try it'),
      h('button', { class: 'btn', onclick: async () => download(`${c.id}.json`, await api(`/api/capabilities/${encodeURIComponent(c.file)}`)) }, 'Export'),
      h('a', { class: 'btn', href: `#/cards/${encodeURIComponent(c.file)}` }, 'Review')));
}

export default async function render(root) {
  const all = (await api('/api/capabilities')).filter((c) => c.state === 'approved');
  root.append(
    pageHead('Catalog', 'What other agents see over MCP. Only approved cards appear here.'),
    h('p', { class: 'muted small' }, 'A card cannot be listed without a description and a reliability figure. Cards missing either are greyed, with the missing thing named.'),
    all.length ? h('div', { class: 'cat-grid' }, all.map(tile)) : empty('No approved capabilities yet. Approve a card and it will be listed here.'));
}
