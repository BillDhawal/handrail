// The review desk: read the compiled card, compare versions, tick the checklist, sign.
import { h, api, fmt } from '../app.js';
import { pageHead, stateChip, stepper, effectChip, table, empty, chip } from './_bits.js';

const enc = encodeURIComponent;

function ladder(card, id) {
  const t = (card.targets || {})[id];
  if (!t) return h('span', { class: 'muted' }, 'no locator');
  return h('details', null, h('summary', { class: 'mono' }, id),
    h('ol', { class: 'small' }, (t.ladder || []).map((r) => h('li', null,
      h('b', null, r.rung), ` cost ${r.cost} `, h('code', null, String(r.value))))));
}

function cardTab(card) {
  const ins = [
    { label: 'Input', cell: (i) => i.name, cls: 'mono' }, { label: 'Type', cell: (i) => i.type },
    { label: 'Sensitivity', cell: (i) => chip(i.sensitivity === 'secret' ? 'hard' : 'draft', i.sensitivity || 'low') },
    { label: 'Required', cell: (i) => (i.required ? 'yes' : 'no') }];
  const outs = [
    { label: 'Output', cell: (o) => o.name, cls: 'mono' }, { label: 'Type', cell: (o) => o.type },
    { label: 'Source step', cell: (o) => (o.source || {}).step, cls: 'mono' },
    { label: 'On screen', cell: (o) => (o.produced_on || []).join(', ') }];
  const steps = [
    { label: 'Step', cell: (s) => s.id, cls: 'mono' }, { label: 'Screen', cell: (s) => s.screen },
    { label: 'Verb', cell: (s) => (s.op || {}).verb, cls: 'mono' },
    { label: 'Target and locator ladder', cell: (s) => ladder(card, s.target) },
    { label: 'Effect', cell: (s) => effectChip((s.effect || {}).kind) }];
  const screens = Object.values(card.screens || {});
  return h('div', { class: 'stack' },
    h('div', { class: 'grid cols-2' },
      h('section', { class: 'card' }, h('h2', null, 'Inputs'), table(ins, card.inputs, 'This capability takes no inputs.')),
      h('section', { class: 'card' }, h('h2', null, 'Outputs'), table(outs, card.outputs, 'This capability returns nothing.'))),
    h('section', { class: 'card' }, h('h2', null, 'Screens'),
      screens.length ? h('div', { class: 'row' }, screens.map((s) => chip('draft', s.label))) : empty('No screens recorded.')),
    h('section', { class: 'card' }, h('h2', null, 'Steps'), table(steps, card.steps, 'No steps.')));
}

function diffTab(card, versions) {
  const pick = (id, def) => h('select', { id, 'aria-label': id }, versions.map((v) => h('option', { value: v.file, selected: v.file === def }, `${v.version} (${v.state})`)));
  const a = pick('va', (versions[1] || versions[0] || {}).file), b = pick('vb', (versions[0] || {}).file);
  const out = h('div');
  const run = async () => {
    const [x, y] = await Promise.all([a.value, b.value].map((f) => api(`/api/capabilities/${enc(f)}`)));
    const mx = Object.fromEntries((x.steps || []).map((s) => [s.id, (s.effect || {}).kind]));
    const my = Object.fromEntries((y.steps || []).map((s) => [s.id, (s.effect || {}).kind]));
    const ids = [...new Set([...Object.keys(mx), ...Object.keys(my)])];
    const kind = (i) => (!(i in mx) ? 'add' : !(i in my) ? 'del' : mx[i] !== my[i] ? 'chg' : '');
    out.replaceChildren(table([
      { label: 'Step', cell: (i) => i, cls: 'mono' }, { label: x.version, cell: (i) => mx[i] || '-' },
      { label: y.version, cell: (i) => my[i] || '-' },
      { label: 'Change', cell: (i) => ({ add: 'added', del: 'removed', chg: 'effect changed' }[kind(i)] || 'same') }],
    ids, 'Neither version has steps.', { rowClass: (i) => (kind(i) ? `diff-${kind(i)}` : '') }));
  };
  [a, b].forEach((s) => s.addEventListener('change', run));
  if (versions.length) run();
  return h('section', { class: 'card stack' }, h('h2', null, 'Versions'),
    versions.length > 1 ? h('div', { class: 'row' }, 'Compare', a, 'with', b) : h('p', { class: 'muted' }, 'Only one version of this capability exists.'), out);
}

function approveTab(file, card, cl, reload) {
  const who = h('input', { placeholder: 'Your name', 'aria-label': 'Your name' });
  const why = h('input', { placeholder: 'Why it is being retired', 'aria-label': 'Reason' });
  const msg = h('p', { class: 'err' });
  const act = (path, body) => async () => {
    msg.textContent = '';
    if (!who.value.trim()) { msg.textContent = 'Put your name in the box first.'; return; }
    try { await api(`/api/capabilities/${enc(file)}/${path}`, { body: { by: who.value.trim(), ...body } }); await reload(); }
    catch (e) { msg.textContent = e.message; }
  };
  const item = (ok, text, why_) => h('li', null, h('span', { class: ok ? 'ok' : 'err' }, ok ? '✓ ' : '✗ '), text,
    !ok && why_ ? h('ul', { class: 'small muted' }, why_.map((r) => h('li', null, r))) : null);
  const reasons = cl.reasons || [];
  const states = card.lifecycle.state;
  return h('div', { class: 'grid cols-2' },
    h('section', { class: 'card stack' }, h('h2', null, 'Approval checklist'),
      h('ul', { class: 'plain' },
        item(cl.verified, 'Three clean plates: verify runs all passed', reasons.filter((r) => /verif|plate|trial/i.test(r))),
        item(cl.commits_confirmed, 'Every commit confirmed by a named person', reasons.filter((r) => /commit|confirm/i.test(r))),
        item(cl.no_secret_literals, 'No secret literals in the card', reasons.filter((r) => /secret/i.test(r)))),
      h('dl', { class: 'kv' }, h('dt', null, 'Allowed hosts'), h('dd', { class: 'mono' }, (cl.allowed_hosts || []).join(', ') || 'none'),
        h('dt', null, 'Plates'), h('dd', { class: 'mono' }, cl.plates)),
      reasons.length && !cl.approvable ? h('p', { class: 'small muted' }, `Reasons: ${reasons.join('; ')}`) : null,
      states === 'approved' ? h('p', { class: 'ok' }, `Approved by ${card.lifecycle.approved_by} on ${fmt.date(card.lifecycle.approved_at)}.`) : null,
      h('label', null, 'Your name', who),
      h('div', { class: 'row' }, h('button', { class: 'btn btn-primary', disabled: !cl.approvable || states === 'approved', onclick: act('approve', {}) }, 'Approve as me')), msg),
    h('section', { class: 'card stack' }, h('h2', null, 'Deprecate'),
      h('p', { class: 'muted small' }, 'Retire this version. It leaves the catalog and nothing new will run it.'),
      h('label', null, 'Reason', why),
      h('div', { class: 'row' }, h('button', { class: 'btn btn-danger', disabled: states === 'deprecated', onclick: act('deprecate', { why: why.value }) }, 'Deprecate'))));
}

export default async function render(root, { args, query }) {
  const file = args[0];
  const tab = query.get('tab') || 'card';
  const [card, cl] = await Promise.all([api(`/api/capabilities/${enc(file)}`), api(`/api/capabilities/${enc(file)}/checklist`)]);
  const reload = async () => { root.replaceChildren(); await render(root, { args, query }); };
  const lc = card.lifecycle || {};
  const tabs = [['card', 'Card'], ['versions', 'Versions'], ['approve', 'Approve']];
  root.append(
    pageHead(card.id, null, h('a', { class: 'btn btn-primary', href: `#/live?file=${enc(file)}` }, 'Try it')),
    h('p', { class: 'row' }, h('span', { class: 'mono muted' }, `${card.id}@${card.version}`), stateChip(lc.state)),
    h('p', { class: 'small' }, card.title),
    stepper(lc.state),
    h('p', { class: 'muted small' }, lc.approved_by ? `Approved by ${lc.approved_by}, ${fmt.date(lc.approved_at)}` : 'Not approved yet.'),
    h('nav', { class: 'tabs' }, tabs.map(([k, l]) => h('a', { class: tab === k ? 'on' : '', href: `#/cards/${enc(file)}?tab=${k}` }, l))),
    tab === 'versions' ? diffTab(card, card.versions || []) : tab === 'approve' ? approveTab(file, card, cl, reload) : cardTab(card));
}
