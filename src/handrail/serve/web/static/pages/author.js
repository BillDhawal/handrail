// Authoring is the one evening the model drives. You watch, you can stop it,
// and at the end you say which buttons cannot be undone.
import { h, api, ws, fmt } from '../app.js';
import { pageHead, effectChip, frameView, empty, chip } from './_bits.js';

const field = (label, el) => h('label', null, label, el);

function inputRows() {
  const box = h('div', { class: 'stack' });
  const rows = [];
  const add = (k = '', v = '', secret = false) => {
    const r = { k: h('input', { placeholder: 'name', value: k, 'aria-label': 'Input name' }), v: h('input', { placeholder: 'example value', value: v, 'aria-label': 'Input value' }), s: h('input', { type: 'checkbox', checked: secret }) };
    rows.push(r);
    box.append(h('div', { class: 'row' }, h('div', { style: 'flex:1 1 120px' }, r.k), h('div', { style: 'flex:2 1 160px' }, r.v), h('label', { class: 'inline' }, r.s, 'secret')));
  };
  add();
  return { box, add, read: () => rows.filter((r) => r.k.value.trim()) };
}

function confirmPanel(p, reload) {
  const who = h('input', { placeholder: 'Your name', 'aria-label': 'Your name' });
  const msg = h('p', { class: 'err' });
  const go = (decision) => async () => {
    if (!who.value.trim()) { msg.textContent = 'Put your name in the box first.'; return; }
    try { await api('/api/author/confirm', { body: { decision, by: who.value.trim() } }); await reload(); } catch (e) { msg.textContent = e.message; }
  };
  const btn = (d, cls) => h('button', { class: `btn ${cls}`, onclick: go(d) }, d);
  return h('section', { class: 'card brass stack' }, h('h2', null, 'Is this one of the buttons that cannot be undone?'),
    h('p', null, h('b', null, p.what), ` on screen `, h('span', { class: 'mono' }, p.screen)),
    h('div', { class: 'row' }, btn('commit', 'btn-danger'), btn('navigate', ''), btn('stage', ''), btn('deny', '')),
    field('Your name, carried on the card', who), msg);
}

export default async function render(root) {
  const form = { goal: h('textarea', { rows: 3, placeholder: 'Sign on, find the member, open the hold form, post the hold' }), entry: h('input', { value: 'http://127.0.0.1:8081/signon' }),
    allow: h('input', { value: '127.0.0.1:8081' }), id: h('input', { placeholder: 'plumbline.place_hold' }), out: h('input', { placeholder: 'capabilities/plumbline-place-hold.json' }) };
  const rows = inputRows();
  const msg = h('p', { class: 'err' });
  const rail = h('div', { class: 'rail' });
  const side = h('div', { class: 'stack' });
  const drawer = h('section', { class: 'card' });
  const screen = frameView('read-only to you');
  const stopMsg = h('span', { class: 'muted small' });
  let timer;

  const draw = (s) => {
    rail.replaceChildren(...(s.turns.length ? s.turns.map((t) => h('div', { class: 'item' },
      h('div', { class: 'row' }, h('b', { class: 'mono' }, `${t.index}`), h('span', null, t.intent), effectChip(t.effect)),
      h('div', { class: 'small muted' }, `${t.verb} ${t.target || ''}  on `, h('span', { class: 'mono' }, t.screen || '-')))) : [empty('No steps yet. Fill in the goal and start.')]));
    side.replaceChildren(s.pending_confirm ? confirmPanel(s.pending_confirm, poll) : '');
    drawer.replaceChildren(h('h2', null, 'Evidence'), h('div', { class: 'row' },
      h('span', { class: 'mono' }, `model_calls = ${s.model_calls}`), chip(s.finished ? 'success' : 'draft', s.finished ? 'finished' : s.active ? 'recording' : 'idle'),
      s.outcome ? h('span', null, `outcome: ${s.outcome}`) : null,
      s.compiled ? h('a', { class: 'mono', href: `#/cards/${encodeURIComponent(s.compiled)}` }, `compiled: ${s.compiled}`) : h('span', { class: 'muted' }, 'not compiled yet')),
    ...(s.error ? [h('p', { class: 'err' }, s.error)] : []));
    screen.mode(s.pending_confirm ? 'paused' : s.active ? '' : 'aborted', s.active ? 'the model is driving, read-only to you' : 'not recording');
    if (s.active && !timer) timer = setInterval(poll, 2000);
    if (!s.active && timer) { clearInterval(timer); timer = null; }
  };
  async function poll() { try { draw(await api('/api/author')); } catch (e) { msg.textContent = e.message; } }

  const start = async () => {
    msg.textContent = '';
    const r = rows.read();
    try {
      await api('/api/author/start', { body: { goal: form.goal.value, entry: form.entry.value,
        allow: form.allow.value.split(',').map((x) => x.trim()).filter(Boolean),
        inputs: Object.fromEntries(r.map((x) => [x.k.value.trim(), x.v.value])), secrets: r.filter((x) => x.s.checked).map((x) => x.k.value.trim()),
        id: form.id.value, out: form.out.value, model: null } });
      await poll();
    } catch (e) { msg.textContent = e.message; }
  };
  const stop = async () => { try { await api('/api/author/stop', { body: {} }); stopMsg.textContent = 'Stopping.'; } catch (e) { stopMsg.textContent = e.message; } };

  root.append(pageHead('Author', 'The model works the task out once, here, while you watch.',
    stopMsg, h('button', { class: 'btn btn-danger btn-big', onclick: stop }, 'Stop')),
  h('div', { class: 'split-even' },
    h('div', { class: 'stack' },
      h('section', { class: 'card stack' }, h('h2', null, 'Goal'), field('What should it learn to do?', form.goal), field('Entry URL', form.entry),
        field('Allowed hosts, comma separated', form.allow), h('h3', null, 'Inputs'), rows.box,
        h('div', { class: 'row' }, h('button', { class: 'btn', onclick: () => rows.add() }, 'Add input')),
        field('Card id', form.id), field('Output file', form.out),
        h('div', { class: 'row' }, h('button', { class: 'btn btn-primary', onclick: start }, 'Start authoring')), msg),
      h('section', { class: 'card' }, h('h2', null, 'Steps'), rail)),
    h('div', { class: 'stack' }, h('section', { class: 'card' }, h('h2', null, 'The legacy screen'), screen.el,
      h('p', { class: 'muted small' }, 'Read-only to you. Only the model touches it until you stop.')), side, drawer)));
  await poll();
  const close = ws((m) => { if (m.type === 'frame') screen.set(m); });
  return () => { close(); clearInterval(timer); };
}
