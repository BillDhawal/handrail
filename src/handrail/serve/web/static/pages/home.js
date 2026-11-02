// Home is the front door of the restaurant: how busy it is, what is on the menu,
// and a bell that rings when a person is needed in the kitchen.
import { h, api, fmt } from '../app.js';
import { pageHead, stat, table, stateChip, catChip, empty } from './_bits.js';

export default async function render(root) {
  const [sum, caps] = await Promise.all([api('/api/summary'), api('/api/capabilities')]);
  const open = sum.escalations_open;
  const cols = [
    { label: 'Capability', cell: (c) => h('a', { href: `#/cards/${encodeURIComponent(c.file)}` }, h('b', { class: 'mono' }, `${c.id}@${c.version}`), h('div', { class: 'muted small' }, (c.title || '').slice(0, 90) + ((c.title || '').length > 90 ? '...' : ''))) },
    { label: 'State', cell: (c) => stateChip(c.state) },
    { label: 'Approver', cell: (c) => c.approved_by || '-' },
    { label: 'Success rate', cell: (c) => h('span', { class: 'mono' }, fmt.rate(c.success_rate)) },
    { label: 'Last run', cell: (c) => (c.last_run ? h('a', { href: `#/runs/${c.last_run.run_id}` }, catChip(c.last_run.category)) : h('span', { class: 'muted' }, 'never run')) },
  ];
  const need = sum.needs_a_person || [];
  const rail = h('aside', { class: 'card' }, h('h2', null, 'Needs a person now'),
    need.length ? h('div', { class: 'stack' }, need.map((n) => h('div', { class: 'card brass' },
      h('b', null, `Run ${String(n.run_id).slice(-6)} paused at ${n.step}`),
      h('p', { class: 'small' }, `Waiting for: ${(n.expected || []).join(', ') || 'a person'}`),
      h('p', { class: 'mono small' }, `since ${fmt.time(n.since)}`),
      h('a', { class: 'btn btn-primary', href: '#/live' }, 'View details'))))
      : empty('Nothing is waiting for a person. The handrail is holding.'));
  root.append(
    pageHead('Capabilities', 'What the bank has approved a machine to do, and how it is going.'),
    h('div', { class: 'grid cols-4' },
      stat(sum.approved, 'Approved capabilities', `${sum.capabilities} on disk`),
      stat(sum.runs_today, 'Replays today'),
      stat(sum.model_calls_on_replay, 'Model calls on replay', '= 0 on the ordinary path'),
      stat(open, 'Escalations open', null, open ? 'brass' : '')),
    h('div', { class: 'split' },
      h('section', { class: 'card' }, h('h2', null, 'Capabilities'),
        table(cols, caps, 'No capabilities yet. Author one and it will show up here.')),
      rail));
}
