// Fixtures for ?demo, built from the real shapes (evidence/examples and capabilities/).
// Installs a fake api and a fake socket so every page can be looked at with no server.
const HOUR = 3600e3, now = Date.now(), iso = (ms) => new Date(ms).toISOString();

const svgB64 = (title, lines = [], bad = false) => btoa(`<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420"><rect width="640" height="420" fill="#d9dcd6"/><rect x="40" y="30" width="560" height="360" fill="#e9ebe5" stroke="#555"/><rect x="40" y="30" width="560" height="26" fill="${bad ? '#8a2a20' : '#1c2c8c'}"/><text x="320" y="48" fill="#fff" font-family="monospace" font-size="15" text-anchor="middle">PLUMBLINE ${title.toUpperCase()}</text>${lines.map((l, i) => `<text x="64" y="${100 + i * 30}" font-family="monospace" font-size="16" fill="#222">${l}</text>`).join('')}<text x="64" y="370" font-family="monospace" font-size="13" fill="#444">F1=Help  F3=Exit  F5=Search  F8=Next</text></svg>`);
const svg = (...a) => `data:image/svg+xml;base64,${svgB64(...a)}`;

const PH = ['s01_set_value_operator_id', 's02_set_value_password', 's03_invoke_f5_sign_on', 's04_select_search_by', 's05_set_value_value', 's06_invoke_f5_search', 's07_invoke_400118', 's08_invoke_hold', 's09_select_reason', 's10_invoke_f8_review', 's11_invoke_f10_post_hold'];
const RB = ['s01_set_value_operator_id', 's02_set_value_password', 's03_invoke_f5_sign_on', 's04_set_value_value', 's05_invoke_f5_search', 's06_invoke_member', 's07_invoke_open', 's08_read_balance'];
const SCREENS = ['Operator Sign On', 'Member Inquiry', 'Member Search Results', 'Member Record'];
const eff = (id) => (/f5_sign_on|f10_post_hold|f8_review|f5_search/.test(id) ? 'commit' : /400118|open|member|hold$/.test(id) ? 'navigate' : /read/.test(id) ? 'read' : 'stage');
const verb = (id) => (/read/.test(id) ? 'read' : /set_value/.test(id) ? 'set_value' : /select/.test(id) ? 'select' : 'invoke');

const mkCard = (id, version, state, ids, outputs) => ({
  schema_version: 'capability/2', id, version, title: id === 'plumbline.place_hold' ? 'Sign on as the operator, find the member by number, open the hold form and post a hold on the given share.' : 'Sign on as the operator, search for the member, open the record and return the balance of the given share.',
  lifecycle: { state, approved_by: state === 'approved' ? 'dhawal' : null, approved_at: state === 'approved' ? '2026-10-12T03:13:19+00:00' : null, note: '', reliability: { replays: state === 'approved' ? 3 : 0, clean: state === 'approved' ? 3 : 0 } },
  surface: { kind: 'browser', entry: '{{env.BASE_URL}}/signon', requires: [] },
  inputs: [{ name: 'operator_id', type: 'string', required: true, sensitivity: 'low' }, { name: 'password', type: 'string', required: true, sensitivity: 'secret' }, { name: 'member_number', type: 'string', required: true, sensitivity: 'low' }, { name: 'share_id', type: 'string', required: true, sensitivity: 'low' }],
  outputs, screens: Object.fromEntries(SCREENS.map((s) => [s, { label: s, signature: 'sha256:2784006a9f88b7ec', paths: [] }])),
  targets: Object.fromEntries(ids.map((i) => [`t_${i}`, { role: 'button', ladder: [{ rung: 'label', cost: 140, value: i.replace(/^s\d+_/, '') }, { rung: 'role_name', cost: 100, value: 'button' }, { rung: 'native', cost: 10000000, surface: 'browser', value: `[name="${i.slice(4, 9)}"]` }] }])),
  steps: ids.map((i, n) => ({ id: i, intent: i.replace(/^s\d+_/, '').replace(/_/g, ' '), screen: SCREENS[Math.min(3, Math.floor(n / 3))], op: { verb: verb(i) }, target: `t_${i}`, effect: { kind: eff(i), proposed_by: 'model' } })),
  safety: { allowed_hosts: ['127.0.0.1:8081'], allowed_apps: [], allowed_verbs: ['invoke', 'read', 'select', 'set_value'] },
});
const CARDS = {
  'plumbline-place-hold.json': mkCard('plumbline.place_hold', '0.1.0', 'approved', PH, [{ name: 'confirmation', type: 'string', source: { step: PH[10] }, produced_on: ['Hold Result'] }]),
  'plumbline-read-balance.json': mkCard('plumbline.read_balance', '0.1.0', 'approved', RB, [{ name: 'balance', type: 'string', source: { step: RB[7] }, produced_on: ['Member Record'] }]),
  'plumbline-place-hold.authored.json': mkCard('plumbline.place_hold', '0.2.0', 'verified', PH.slice(0, 10), []),
};
CARDS['plumbline-place-hold.authored.json'].steps[3].effect.kind = 'commit';
const VERSIONS = [{ file: 'plumbline-place-hold.authored.json', version: '0.2.0', state: 'verified' }, { file: 'plumbline-place-hold.json', version: '0.1.0', state: 'approved' }];

const run = (id, cap, status, steps, extra) => ({ run_id: id, capability_id: cap, capability_version: '0.1.0', started_at: iso(now - status.ago * HOUR), duration_ms: status.ms, category: status.cat, code: status.code, outcome: status.outcome || null, outputs: status.outputs || {}, error: status.error || null,
  steps: steps.map((s, i) => ({ step_id: s, status: status.failAt === i ? 'failed' : 'ok', rung: /f\d|invoke|search/.test(s) ? 'role_name' : 'label', rung_cost: /f\d|invoke|search/.test(s) ? 100 : 140, note: status.failAt === i ? 'no rung found the control' : null })).slice(0, status.failAt != null ? status.failAt + 1 : 99),
  drift: { steps_resolved: status.failAt ?? steps.length, first_choice: status.failAt ?? steps.length }, classifier_calls: status.cc || 0, llm_calls: 0, escalated_to_human: !!status.human, steps_ok: status.failAt ?? steps.length, steps_total: steps.length, ...extra });
const RUNS = [
  run('replay_20261012T031500Z_a1b2c3', 'plumbline.read_balance', { ago: 1, ms: 3100, cat: 'HARD_FAILURE', code: 'TARGET_NOT_FOUND', failAt: 7, error: { code: 'TARGET_NOT_FOUND', message: 'no locator rung found cell_balance_work_input_share_id', step_id: RB[7], expected: 'cell Balance in row 400118-S0001', observed: 'row 400118-S0001 has no Balance cell' } }, RB),
  run('replay_20261010T180816Z_7c0de1', 'plumbline.place_hold', { ago: 3, ms: 15400, cat: 'SUCCESS', code: 'NONE', outcome: 'Hold Result', human: true, cc: 1 }, PH),
  run('replay_20261010T180723Z_788ad9', 'plumbline.place_hold', { ago: 5, ms: 8800, cat: 'RECOVERABLE', code: 'SLOW_LOAD', failAt: 5, error: { code: 'SLOW_LOAD', message: 'screen_is never came true after open_hold', step_id: 'open_hold', expected: null, observed: null } }, PH),
  run('replay_20261010T180720Z_93d318', 'plumbline.place_hold', { ago: 6, ms: 1499, cat: 'SUCCESS', code: 'NONE', outcome: 'Hold Result' }, PH),
  run('replay_20261012T030239Z_5a5a5a', 'plumbline.read_balance', { ago: 30, ms: 972, cat: 'SUCCESS', code: 'NONE', outcome: 'Member Record', outputs: { balance: '$750.00' } }, RB),
];
const logFor = (r) => {
  let n = 0; const ev = (event, o = {}) => ({ seq: ++n, at: iso(Date.parse(r.started_at) + n * 90), event, ...o, prev: 'x', hash: 'y' });
  const out = [ev('replay.start', { capability: `${r.capability_id}@0.1.0`, inputs: { operator_id: 'dcolewell', password: '[secret]', member_number: '400118', share_id: '400118-S0001' } })];
  r.steps.forEach((s) => { out.push(ev('step.start', { step: s.step_id, verb: 'invoke', effect: 'stage' }), ev('step.ok', { step: s.step_id, ms: 40 + n })); });
  if (r.escalated_to_human) out.push(ev('rung1.screen', { step: PH[10], chosen: 'none_of_these', confidence: 0.95, accepted: false }), ev('rung3.paused', { step: PH[10], expected: ['Hold Result'] }), ev('rung3.handed_back', { step: PH[10], named: 'Hold Result', by: 'dhawal', accepted: true }));
  if (r.error) out.push(ev('replay.error', { code: r.error.code, message: r.error.message, screenshot: 'fail_step.png' }));
  return [...out, ev('replay.finish', { category: r.category, code: r.code })];
};
const detail = (r) => ({ result: r, events: logFor(r), journal: r.steps.flatMap((s, i) => [{ seq: 3 * i + 1, kind: 'screen', name: SCREENS[0] }, { seq: 3 * i + 2, kind: 'dispatched', name: s.step_id }, { seq: 3 * i + 3, kind: 'observed', name: s.step_id }]),
  chain: { ok: true, lines: logFor(r).length }, files: [], screenshots: [{ label: 'before', png: 'before.png' }, { label: 'after', png: 'after.png' }, ...(r.error ? [{ label: 'fail_step', png: 'fail_step.png' }] : [])] });

const CAP_ROWS = [['plumbline-place-hold.json', 'write', 0.99, 3, 'Places a legal or administrative hold on one share.'], ['plumbline-read-balance.json', 'read', 0.67, 3, null], ['plumbline-place-hold.authored.json', 'write', null, 0, null]].map(([file, rw, sr, n, d]) => {
  const c = CARDS[file], last = RUNS.find((r) => r.capability_id === c.id);
  return { id: c.id, version: c.version, title: c.title, state: c.lifecycle.state, approved_by: c.lifecycle.approved_by, approved_at: c.lifecycle.approved_at, reliability: c.lifecycle.reliability, read_or_write: rw, inputs: c.inputs, outputs: c.outputs, file, description: d, success_rate: sr, last_run: last && sr != null ? { run_id: last.run_id, category: last.category, started_at: last.started_at } : null };
});

const LIVE = { active: true, run_id: 'replay_20261102T090000Z_e5e5e5', capability_id: 'plumbline.place_hold', state: 'paused', baton: { owner: 'PAUSED', history: [{ action: 'pause', by: 'engine' }] }, expected: ['Hold Result'], headed: false, result: null };
const AUTHOR = { active: true, turns: PH.slice(0, 5).map((s, i) => ({ index: i + 1, intent: s.replace(/^s\d+_/, '').replace(/_/g, ' '), screen: SCREENS[Math.min(3, Math.floor(i / 2))], verb: verb(s), target: `t_${s}`, effect: eff(s) })), pending_confirm: { index: 6, what: 'invoke F10=Post Hold', screen: 'Hold Review' }, model_calls: 7, finished: false, outcome: null, compiled: null, error: null };

const ROUTES = {
  'GET /api/summary': () => ({ capabilities: 3, approved: 2, runs_today: 412, model_calls_on_replay: 0, escalations_open: 1, needs_a_person: [{ run_id: LIVE.run_id, step: PH[10], expected: ['Hold Result'], since: iso(now - 252e3) }] }),
  'GET /api/capabilities': () => CAP_ROWS,
  'GET /api/drift': () => ({ rungs: [{ capability_id: 'plumbline.place_hold', step_id: PH[0], rung: 'label', count: 28, last_run: RUNS[3].run_id }, { capability_id: 'plumbline.place_hold', step_id: PH[2], rung: 'role_name', count: 28, last_run: RUNS[3].run_id }, { capability_id: 'plumbline.read_balance', step_id: RB[7], rung: 'native', count: 3, last_run: RUNS[0].run_id }],
    healing: [{ run_id: RUNS[1].run_id, step_id: PH[10], rung: 'rung3', accepted: true }, { run_id: RUNS[0].run_id, step_id: RB[7], rung: 'rung1', accepted: false }],
    calibration: [{ question: 'which screen is this', lo: 0.9, hi: 1.0, n: 14, accepted: 13, rate: 0.93 }, { question: 'which screen is this', lo: 0.5, hi: 0.9, n: 4, accepted: 1, rate: 0.25 }] }),
  'GET /api/live': () => LIVE,
  'GET /api/author': () => AUTHOR,
};
const state = { author: AUTHOR };
const wait = (v) => new Promise((r) => setTimeout(() => r(JSON.parse(JSON.stringify(v))), 120));

async function api(path, opts = {}) {
  const method = opts.method || (opts.body !== undefined ? 'POST' : 'GET'), url = path.split('?')[0];
  let m;
  if (ROUTES[`${method} ${url}`]) return wait(ROUTES[`${method} ${url}`]());
  if ((m = url.match(/^\/api\/runs$/))) return wait(RUNS);
  if ((m = url.match(/^\/api\/runs\/([^/]+)$/))) { const r = RUNS.find((x) => x.run_id === decodeURIComponent(m[1])); if (!r) throw new Error('no such run'); return wait(detail(r)); }
  if ((m = url.match(/^\/api\/capabilities\/([^/]+)\/checklist$/))) { const ok = decodeURIComponent(m[1]) !== 'plumbline-place-hold.authored.json'; return wait({ verified: ok, commits_confirmed: ok, no_secret_literals: true, allowed_hosts: ['127.0.0.1:8081'], plates: ok ? 3 : 1, reasons: ok ? [] : ['verify: 1 of 3 plates clean', 'commit: s04_select_search_by is not confirmed by a person'], approvable: ok }); }
  if ((m = url.match(/^\/api\/capabilities\/([^/]+)\/(approve|deprecate)$/))) { const c = CARDS[decodeURIComponent(m[1])]; c.lifecycle.state = m[2] === 'approve' ? 'approved' : 'deprecated'; c.lifecycle.approved_by = opts.body.by; c.lifecycle.approved_at = iso(now); return wait(c); }
  if ((m = url.match(/^\/api\/capabilities\/([^/]+)$/))) { const c = CARDS[decodeURIComponent(m[1])]; if (!c) throw new Error('no such card'); return wait({ ...c, versions: c.id === 'plumbline.place_hold' ? VERSIONS : [{ file: m[1], version: c.version, state: c.lifecycle.state }] }); }
  if (url === '/api/live/act') { const a = opts.body.action; if (a === 'take_over') { LIVE.baton = { owner: 'HUMAN_CONTROL', history: [] }; } else { LIVE.state = 'finished'; LIVE.active = false; LIVE.baton = { owner: a === 'abort' ? 'ABORTED' : 'AUTOMATION_RUNNING', history: [] }; LIVE.result = { ...RUNS[1], run_id: LIVE.run_id }; } return wait({ ok: true }); }
  if (url === '/api/live/start') { Object.assign(LIVE, { active: true, state: 'running', baton: { owner: 'AUTOMATION_RUNNING', history: [] }, result: null }); return wait({ run_id: LIVE.run_id }); }
  if (url === '/api/author/confirm') { AUTHOR.pending_confirm = null; AUTHOR.finished = true; AUTHOR.active = false; AUTHOR.compiled = 'plumbline-place-hold.authored.json'; AUTHOR.outcome = 'Hold Result'; return wait({ ok: true }); }
  if (url === '/api/author/start') throw new Error('no model key is configured (demo)');
  if (url === '/api/author/stop') throw new Error('404 not found (demo)');
  throw new Error(`demo: no fixture for ${method} ${url}`);
}

function ws(onMessage) {
  const t = [];
  const at = (ms, fn) => t.push(setTimeout(fn, ms));
  const frame = (title, lines) => onMessage({ type: 'frame', mime: 'image/svg+xml', jpeg: svgB64(title, lines), at: iso(Date.now()) });
  const ev = (event, o = {}) => onMessage({ type: 'event', event, at: iso(Date.now()), seq: 0, ...o });
  at(300, () => frame('Hold Form', ['MEMBER: 400118', 'SHARE:  S0001', 'REASON: LEGAL']));
  at(800, () => ev('step.start', { step: PH[9], verb: 'invoke', effect: 'commit' }));
  at(1300, () => ev('rung1.screen', { step: PH[10], chosen: 'none_of_these', confidence: 0.95, accepted: false }));
  at(1800, () => ev('rung3.paused', { step: PH[10], expected: ['Hold Result'] }));
  at(2300, () => frame('Transaction Summary', ['REQUEST ACCEPTED']));
  return () => t.forEach(clearTimeout);
}

export const backend = { api, ws, fileUrl: (run, name) => svg(name.replace('.png', ''), ['MEMBER: 400118', 'SHARE: S0001'], /fail/.test(name)) };
