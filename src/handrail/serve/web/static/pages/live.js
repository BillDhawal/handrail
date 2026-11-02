// The live run is the telephone: watch the screen, see which rung of the ladder is being tried,
// and when the engine rings for a person, take the call.
import { h, api, ws, fmt } from '../app.js';
import { pageHead, frameView, chip, catChip, empty } from './_bits.js';

const field = (label, el) => h('label', null, label, el);
const OWNER = { AUTOMATION_RUNNING: ['', 'automation is driving'], PAUSED: ['paused', 'paused, waiting for a person'],
  HUMAN_CONTROL: ['human', 'you are driving'], ABORTED: ['aborted', 'aborted'] };
const SKIP = ['type', 'event', 'seq', 'at', 'prev', 'hash'];

async function startForm(root, query) {
  const caps = (await api('/api/capabilities')).filter((c) => c.state !== 'deprecated');
  const pick = h('select', { 'aria-label': 'Capability' }, caps.map((c) => h('option', { value: c.file, selected: c.file === query.get('file') }, `${c.id}@${c.version} (${c.state})`)));
  const inputs = h('div', { class: 'stack' }), env = h('div', { class: 'stack' });
  const headed = h('input', { type: 'checkbox' });
  const cls = h('select', { 'aria-label': 'Classifier' }, ['', 'claude', 'laya'].map((v) => h('option', { value: v }, v || 'none')));
  const msg = h('p', { class: 'err' });
  const kv = (k, v) => h('div', { class: 'row' }, h('input', { value: k, 'aria-label': 'name', placeholder: 'NAME', style: 'flex:1 1 120px' }),
    h('input', { value: v, 'aria-label': 'value', placeholder: 'value', style: 'flex:2 1 160px' }));
  const fill = async () => {
    inputs.replaceChildren();
    if (!pick.value) return;
    const card = await api(`/api/capabilities/${encodeURIComponent(pick.value)}`);
    inputs.append(...(card.inputs || []).map((i) => h('label', null, h('span', null, i.name, ' ', i.sensitivity === 'secret' ? chip('hard', 'secret') : ''),
      h('input', { name: i.name, type: i.sensitivity === 'secret' ? 'password' : 'text', autocomplete: 'off' }))));
    if (!(card.inputs || []).length) inputs.append(empty('This capability takes no inputs.'));
  };
  env.append(kv('BASE_URL', 'http://127.0.0.1:8081'));
  pick.addEventListener('change', fill);
  await fill();
  const go = async () => {
    msg.textContent = '';
    const body = { file: pick.value, inputs: Object.fromEntries([...inputs.querySelectorAll('input')].map((i) => [i.name, i.value])),
      env: Object.fromEntries([...env.children].map((r) => [r.children[0].value, r.children[1].value]).filter(([k]) => k)),
      headed: headed.checked, classifier: cls.value || null, console: true };
    try { await api('/api/live/start', { body }); root.replaceChildren(); await render(root, { query }); } catch (e) { msg.textContent = e.message; }
  };
  const idle = frameView('nothing running', 'The live screen appears here once a replay starts.');
  idle.mode('quiet', 'nothing running');
  root.append(pageHead('Live', 'Nothing is running. Start a replay and watch it here.'),
    h('div', { class: 'split-even' }, h('section', { class: 'card stack' }, caps.length ? [field('Capability', pick), h('h3', null, 'Inputs'), inputs, h('h3', null, 'Environment'), env,
      h('div', { class: 'row' }, h('button', { class: 'btn', onclick: () => env.append(kv('', '')) }, 'Add variable')),
      h('label', { class: 'inline' }, headed, 'Headed: show a real browser window'), field('Classifier rung', cls),
      h('div', { class: 'row' }, h('button', { class: 'btn btn-primary', onclick: go }, 'Start replay')), msg] : empty('No capabilities to run yet.')),
    h('section', { class: 'card' }, h('h2', null, 'Live screen'), idle.el,
      h('p', { class: 'muted small' }, 'A screenshot twice a second while the engine drives. Tick Headed for a real window.'))));
}

export default async function render(root, ctx) {
  let live = await api('/api/live');
  if (!live.active && live.state !== 'finished') return startForm(root, ctx.query);
  const screen = frameView('automation is driving');
  const ladder = h('div', { class: 'stack' }, h('p', { class: 'muted small' }, 'Rung events appear here as they happen. Every rung only proposes.'));
  const stream = h('div', { class: 'log' }), top = h('div', { class: 'stack' });
  const timerEl = h('span', { class: 'timer' });
  let pausedAt = null, paused = null, timer, tick, name = '';
  const act = (action, screenName, by) => async () => {
    try { await api('/api/live/act', { body: { action, by: by.value.trim() || 'someone', screen: screenName ? screenName() : undefined } }); await poll(); }
    catch (e) { top.querySelector('.err').textContent = e.message; }
  };
  let sig = '';
  const drawTop = () => {
    const now = [live.state, (live.baton || {}).owner, (live.expected || []).join()].join('|');
    if (now === sig) return;
    sig = now;
    if (live.pause && live.pause.step) { paused = live.pause; pausedAt = Date.parse(live.pause.at) || pausedAt; }
    const by = h('input', { placeholder: 'Your name', 'aria-label': 'Your name', value: name, oninput: (e) => { name = e.target.value; } });
    const sel = h('select', { 'aria-label': 'Hand back as screen' }, (live.expected || []).map((s) => h('option', { value: s }, s)));
    top.replaceChildren();
    if (live.state === 'paused') {
      top.append(h('div', { class: 'banner-brass' }, h('p', null, 'The engine could not name this screen after step ', h('b', null, paused ? paused.step : '?'),
        '. Expected: ', h('b', null, (live.expected || []).join(', ')), '. Please bring the application to that screen, then hand back.'), timerEl),
      h('div', { class: 'card stack' }, field('Your name, written to the journal', by), h('div', { class: 'row' },
        h('button', { class: 'btn btn-brass', onclick: act('take_over', null, by) }, 'Take over'), sel,
        h('button', { class: 'btn btn-primary', onclick: act('hand_back', () => sel.value, by) }, 'Hand back'),
        h('button', { class: 'btn btn-danger', onclick: act('abort', null, by) }, 'Abort')), h('p', { class: 'err' })));
    }
    if (live.state === 'finished' && live.result) {
      const r = live.result;
      top.append(h('section', { class: 'card stack' }, h('h2', null, 'Finished'),
        h('div', { class: 'row' }, catChip(r.category), h('span', { class: 'mono' }, `${r.code}, ${fmt.ms(r.duration_ms)}, llm_calls = ${r.llm_calls}`)),
        Object.keys(r.outputs || {}).length ? h('dl', { class: 'kv' }, Object.entries(r.outputs).flatMap(([k, v]) => [h('dt', null, k), h('dd', { class: 'mono' }, String(v))])) : h('p', { class: 'muted' }, 'No outputs on this card.'),
        r.error ? h('p', { class: 'mono' }, r.error.message) : null,
        h('div', { class: 'row' }, h('a', { class: 'btn btn-primary', href: `#/runs/${live.run_id}` }, 'Open the run'))));
    }
  };
  const draw = () => {
    const [cls, text] = live.state === 'finished' ? ['', 'finished, last frame'] : (OWNER[(live.baton || {}).owner] || ['', live.state]);
    screen.mode(cls, text);
    if (live.state === 'paused' && !pausedAt) pausedAt = Date.now();
    if (live.state !== 'paused') pausedAt = null;
    drawTop();
  };
  async function poll() { live = await api('/api/live'); draw(); }
  const addEvent = (e) => {
    if (/^rung/.test(e.event)) {
      ladder.append(h('div', { class: 'card brass small' }, h('b', { class: 'mono' }, e.event),
        h('div', { class: 'mono' }, Object.entries(e).filter(([k]) => !SKIP.includes(k)).map(([k, v]) => `${k}=${v}`).join(' '))));
      if (e.event === 'rung3.paused') { paused = e; pausedAt = Date.parse(e.at) || Date.now(); poll(); }
      if (e.event === 'rung3.handed_back') poll();
    }
    if (e.event === 'replay.finish') poll();
    stream.append(h('div', null, `${fmt.time(e.at)} ${e.event} ${e.step || ''}`)); stream.scrollTop = stream.scrollHeight;
  };
  root.append(pageHead('Live', `${live.capability_id || ''} run ${String(live.run_id || '').replace('replay_', '')}`), top,
    h('div', { class: 'split-even' }, h('div', { class: 'stack' }, h('section', { class: 'card' }, h('h2', null, 'Ladder'), ladder),
      h('section', { class: 'card' }, h('h2', null, 'Events'), stream)), h('section', { class: 'card' }, h('h2', null, 'Live screen'), screen.el)));
  if (live.state === 'paused') api('/api/summary').then((m) => { const n = (m.needs_a_person || []).find((x) => x.run_id === live.run_id); if (n && !paused) { paused = { step: n.step }; pausedAt = Date.parse(n.since) || pausedAt; sig = ''; draw(); } }).catch(() => {});
  draw();
  const close = ws((m) => { if (m.type === 'frame') screen.set(m); else if (m.type === 'event') addEvent(m); else if (m.type === 'baton') { live.baton = { owner: m.owner, history: m.history }; draw(); } });
  timer = setInterval(() => poll().catch(() => {}), 2000);
  tick = setInterval(() => { timerEl.textContent = pausedAt ? `${fmt.clock((Date.now() - pausedAt) / 1000)} waiting` : ''; }, 500);
  return () => { close(); clearInterval(timer); clearInterval(tick); };
}
