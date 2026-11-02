// One run, told straight: did the app say no, or is the capability wrong? Then the receipts.
import { h, api, fmt, fileUrl } from '../app.js';
import { pageHead, catChip, chip, table, empty, filmstrip } from './_bits.js';

export function verdict(res) {
  const code = String(res.code || '');
  if (res.category === 'SUCCESS') return ['Completed.', 'The run finished and the outcome matched the card.'];
  if (res.category === 'RECOVERABLE' || res.category === 'BUSINESS_OUTCOME') {
    return ['Application said so.', `${code}: the application answered, and the capability handled it.`];
  }
  if (/TARGET|LOCATOR|SCREEN/.test(code)) return ['Capability misconfiguration.', `${code}: the card no longer matches the screen.`];
  return ['Hard failure, cause not classified.', code];
}

const RUNG = /^rung[123]/;
const brief = (e) => Object.entries(e).filter(([k]) => !['seq', 'at', 'event', 'prev', 'hash'].includes(k))
  .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' ');

function statusBar(res, d) {
  const ok = (res.steps || []).filter((s) => s.status === 'ok').length;
  const cell = (t, good, label) => h('div', { class: 'stat' }, h('b', { class: good === false ? 'err' : '', style: 'font-size:18px;white-space:nowrap' }, t), h('span', null, label));
  return h('div', { class: 'grid cols-4' },
    cell(`llm_calls = ${res.llm_calls}`, res.llm_calls === 0 ? true : false, res.llm_calls === 0 ? 'no model on replay' : 'model was called'),
    cell(d.chain.ok ? `chain verified, ${d.chain.lines} lines` : 'chain NOT verified', d.chain.ok, 'hash chain over the log'),
    cell(`${ok} of ${(res.steps || []).length || res.steps_total || 0}`, null, 'steps ok'),
    cell(`classifier_calls = ${res.classifier_calls}`, null, 'cheap classifier asks'));
}

export default async function render(root, { args }) {
  const id = args[0];
  const d = await api(`/api/runs/${encodeURIComponent(id)}`);
  const res = d.result, ev = d.events || [];
  const [head, why] = verdict(res);
  const start = ev.find((e) => e.event === 'replay.start') || {};
  const fail = (d.screenshots || []).find((s) => /^fail/.test(s.label) || /^fail/.test(s.png));
  const steps = [
    { label: 'Step', cell: (s) => s.step_id, cls: 'mono' },
    { label: 'Status', cell: (s) => chip(s.status === 'ok' ? 'success' : 'hard', s.status) },
    { label: 'Rung', cell: (s) => s.rung || '-', cls: 'mono' }, { label: 'Cost', cell: (s) => s.rung_cost ?? '-', cls: 'mono' },
    { label: 'Note', cell: (s) => s.note || '' }];
  const evs = [
    { label: 'Seq', cell: (e) => e.seq, cls: 'mono' }, { label: 'Time', cell: (e) => fmt.time(e.at), cls: 'mono' },
    { label: 'Event', cell: (e) => h('b', { class: 'mono' }, e.event) },
    { label: 'Detail', cell: (e) => h('span', { class: 'mono small' }, brief(e)) }];
  const outs = Object.entries(res.outputs || {});
  const err = res.error ? h('section', { class: 'card brass stack' },
    h('h2', null, 'The check that failed'),
    h('blockquote', { style: 'margin:0', class: 'mono' }, res.error.message),
    h('dl', { class: 'kv' }, h('dt', null, 'step'), h('dd', { class: 'mono' }, res.error.step_id || '-'),
      h('dt', null, 'expected'), h('dd', { class: 'mono' }, JSON.stringify(res.error.expected)),
      h('dt', null, 'observed'), h('dd', { class: 'mono' }, JSON.stringify(res.error.observed))),
    fail ? h('a', { href: fileUrl(id, fail.png), target: '_blank', rel: 'noopener' }, h('img', { class: 'shot', src: fileUrl(id, fail.png), alt: 'Screen at the moment it broke' })) : empty('No screenshot was captured at the failure.')) : null;
  root.append(
    pageHead(`Run ${String(res.run_id).replace('replay_', '')}`, `${res.capability_id}@${res.capability_version}, ${fmt.date(res.started_at)}, ${fmt.ms(res.duration_ms)}`,
      catChip(res.category), res.escalated_to_human ? chip('brass', 'a person stepped in') : null),
    h('div', { class: 'card' }, h('h2', null, head), h('p', { class: 'muted' }, why)),
    statusBar(res, d), ...(err ? [err] : []),
    h('div', { class: 'split' },
      h('section', { class: 'card' }, h('h2', null, 'Steps'), table(steps, res.steps, 'No steps ran.')),
      h('div', { class: 'stack' },
        h('section', { class: 'card' }, h('h2', null, 'Outputs'),
          outs.length ? h('dl', { class: 'kv' }, outs.map(([k, v]) => [h('dt', { class: 'mono' }, k), h('dd', { class: 'mono' }, String(v))])) : empty('No outputs.')),
        h('section', { class: 'card' }, h('h2', null, 'Inputs'),
          h('dl', { class: 'kv' }, Object.entries(start.inputs || {}).map(([k, v]) => [h('dt', { class: 'mono' }, k), h('dd', { class: 'mono' }, String(v))]))),
        h('section', { class: 'card' }, h('h2', null, 'Journal'),
          (d.journal || []).length ? h('ul', { class: 'plain log' }, d.journal.map((j) => h('li', null, h('b', null, j.kind), ' ', j.name))) : empty('The journal is empty.')))),
    h('section', { class: 'card' }, h('h2', null, 'Screenshots'), filmstrip(id, d.screenshots)),
    h('section', { class: 'card' }, h('h2', null, 'Event log'),
      table(evs, ev, 'No events were recorded.', { rowClass: (e) => (RUNG.test(e.event) ? 'hl' : '') })));
}
