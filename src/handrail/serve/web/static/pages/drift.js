// Drift is the wear on the stairs: which rung found each control, even on runs that passed.
import { h, api } from '../app.js';
import { pageHead, table, chip } from './_bits.js';

export default async function render(root) {
  const d = await api('/api/drift');
  const rungs = [
    { label: 'Capability', cell: (r) => r.capability_id, cls: 'mono' },
    { label: 'Step', cell: (r) => r.step_id, cls: 'mono' },
    { label: 'Rung', cell: (r) => chip(r.rung === 'native' ? 'brass' : 'green', r.rung) },
    { label: 'Count', cell: (r) => r.count, cls: 'mono' },
    { label: 'Last run', cell: (r) => h('a', { class: 'mono', href: `#/runs/${r.last_run}` }, String(r.last_run).replace('replay_', '')) },
  ];
  const heal = [
    { label: 'Run', cell: (r) => h('a', { class: 'mono', href: `#/runs/${r.run_id}` }, String(r.run_id).replace('replay_', '')) },
    { label: 'Step', cell: (r) => r.step_id, cls: 'mono' },
    { label: 'Rung', cell: (r) => r.rung, cls: 'mono' },
    { label: 'Accepted', cell: (r) => (r.accepted ? h('span', { class: 'ok' }, '✓ accepted') : h('span', { class: 'err' }, '✗ refused')) },
  ];
  const cal = [
    { label: 'Question', cell: (r) => r.question },
    { label: 'Confidence bin', cell: (r) => `${r.lo.toFixed(1)} - ${r.hi.toFixed(1)}`, cls: 'mono' },
    { label: 'n', cell: (r) => r.n, cls: 'mono' },
    { label: 'Accepted', cell: (r) => r.accepted, cls: 'mono' },
    { label: 'Rate', cell: (r) => `${Math.round(r.rate * 100)}%`, cls: 'mono' },
  ];
  root.append(
    pageHead('Drift', 'Drift is raised even when the run succeeded.'),
    h('section', { class: 'card' }, h('h2', null, 'Locator rungs'),
      h('p', { class: 'muted small' }, 'Rung 1 is the first choice. The further down, the more the screen has moved.'),
      table(rungs, d.rungs, 'No locator data yet. Replay a capability and the rungs will be counted.')),
    h('section', { class: 'card' }, h('h2', null, 'Healing proposals'),
      table(heal, d.healing, 'Nothing has needed healing. Every control was found where it was left.')),
    h('section', { class: 'card' }, h('h2', null, 'Classifier calibration'),
      table(cal, d.calibration, 'The classifier has not been asked anything yet.')));
}
