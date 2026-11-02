// The ledger of every run, newest first, filterable, exportable as evidence.
import { h, api, fmt } from '../app.js';
import { pageHead, table, catChip, download } from './_bits.js';

const CATS = ['SUCCESS', 'BUSINESS_OUTCOME', 'RECOVERABLE', 'HARD_FAILURE'];

export default async function render(root) {
  const runs = await api('/api/runs?limit=100');
  const f = { cap: '', cat: '', esc: false };
  const list = h('div');
  const caps = [...new Set(runs.map((r) => r.capability_id))];
  const view = () => runs.filter((r) => (!f.cap || r.capability_id === f.cap)
    && (!f.cat || r.category === f.cat) && (!f.esc || r.escalated_to_human));
  const cols = [
    { label: 'Run', cell: (r) => h('a', { class: 'mono', href: `#/runs/${r.run_id}` }, String(r.run_id).replace('replay_', '')) },
    { label: 'Capability', cell: (r) => h('span', { class: 'mono' }, `${r.capability_id}@${r.capability_version}`) },
    { label: 'Started', cell: (r) => fmt.date(r.started_at) },
    { label: 'Duration', cell: (r) => fmt.ms(r.duration_ms), cls: 'mono' },
    { label: 'Result', cell: (r) => catChip(r.category) },
    { label: 'Code', cell: (r) => r.code, cls: 'mono' },
    { label: 'Classifier', cell: (r) => r.classifier_calls, cls: 'mono' },
    { label: 'LLM', cell: (r) => r.llm_calls, cls: 'mono' },
    { label: 'Person', cell: (r) => (r.escalated_to_human ? h('b', { class: 'chip chip-brass' }, 'a person') : '') },
    { label: 'Drift', cell: (r) => (r.drift ? `first choice ${r.drift.first_choice} of ${r.drift.steps_resolved}` : '-'), cls: 'small' },
  ];
  const draw = () => list.replaceChildren(table(cols, view(), 'No runs match these filters.'));
  const sel = (opts, key, any) => h('select', { 'aria-label': any, onchange: (e) => { f[key] = e.target.value; draw(); } },
    h('option', { value: '' }, any), opts.map((o) => h('option', { value: o }, o)));
  root.append(
    pageHead('Run history', 'Every replay, with its category, version and who stepped in.',
      h('button', { class: 'btn', onclick: () => download('handrail-runs.json', view()) }, 'Export JSON')),
    h('div', { class: 'row' }, sel(caps, 'cap', 'All capabilities'), sel(CATS, 'cat', 'All results'),
      h('label', { class: 'inline' }, h('input', { type: 'checkbox', onchange: (e) => { f.esc = e.target.checked; draw(); } }), 'Escalated only')),
    h('div', { class: 'card' }, list));
  draw();
}
