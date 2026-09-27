# Handrail — Architecture, In Plain Language

This document explains what Handrail is made of, why each piece exists, and how we
are building it. It pairs with [APPROACH.md](APPROACH.md) (the short story) and
[the PR breakdown](superpowers/plans/2026-08-30-pr-breakdown.md) (the build plan).

## The one-sentence version

An AI drives an old banking website once, we write down exactly what worked as a
small readable file, and from then on a simple machine replays that file — fast,
cheap, predictable, and with no AI involved at all.

## The big picture

```
                     PHASE 1: DISCOVERY (AI, once)
┌──────────────────────────────────────────────────────────────────┐
│   AI planner ── "click this, type that" ──▶ real browser          │
│        ▲                                        │                 │
│        └──── what the page looks like ◀─────────┘                 │
│                        │                                          │
│                        ▼                                          │
│                  trace.json  (a diary of everything that happened)│
└──────────────────────────────────────────────────────────────────┘
                         │
                         ▼
                     THE COMPILER
        turns the diary into a recipe: capability.json
                         │
                         ▼
                     PHASE 2: REPLAY (no AI, forever)
┌──────────────────────────────────────────────────────────────────┐
│   replay engine reads the recipe + your inputs (member #, etc.)   │
│   → drives the browser step by step                               │
│   → checks it is on the right screen before every move            │
│   → reports one of four outcomes + evidence + an early-warning    │
│     "drift" score                                                 │
│                                                                   │
│   safety kernel underneath everything: what sites/actions are     │
│   allowed, secrets scrubbed, human can take over, all evidence    │
│   recorded                                                        │
└──────────────────────────────────────────────────────────────────┘
```

## The pieces, one by one

### 1. The practice bank — PLUMBLINE (`targetapp/`) — BUILT

You cannot demo bank automation without a bank. So we built one: a deliberately
old-fashioned web app styled like a 1990s core-banking terminal, run by two
fictional credit unions (Quarrybrook on port 8081, Fernhollow on 8082) from the
same code with different labels and layouts.

It is deliberately *hostile*, because real legacy systems are:

- The pages are split into frames (an old-web technique that confuses automation).
- No element has an ID or a test hook — nothing is conveniently labeled for robots.
- Every page carries a security token that changes on every load, so you cannot
  just replay a URL.
- Messages are terse mainframe shouting: "NO MEMBER RECORD MATCHES THAT VALUE".
- A hidden test endpoint lets us inject failures on demand — timeouts, maintenance
  pages, surprise dialogs — so we can *prove* recovery works, repeatably. Faults
  are armed on the server, never through the URL, so a replayed URL is identical
  whether or not a trap is waiting.

**How it's implemented:** Python + Flask + server-rendered templates — an
intentionally legacy-appropriate stack. All data lives in memory with a reset
endpoint, so every demo starts from the same known state.

### 2. The hands — the Surface (`src/handrail/surface/`) — BUILT

The only code in the whole system allowed to touch a browser. Everything else
talks to it through a small fixed menu of verbs: navigate, resolve (find an
element), act (click/type/select), evaluate (is this true on screen?), observe
(describe the page), evidence (screenshot + snapshot).

Two implementations exist: the real one (driving Chromium through Playwright) and
a fake one for tests (scripted pages, no browser — so the whole engine can be
tested in milliseconds).

Two details matter a lot:

- **Feature handshake.** A recipe declares what it needs ("I need frames"); a
  surface declares what it provides. Mismatch = refuse before starting, not fail
  halfway through a money-touching flow.
- **Secrets never leave the browser.** Password and hidden fields are masked as
  `[opaque]` at the source — before the AI, the logs, or the saved evidence ever
  see them. We found and fixed a real leak here during review: typed passwords
  were coming back to the AI in clear text. Now they cannot.

### 3. The explorer — Discovery (`src/handrail/discovery/`) — BUILT

The AI phase. Claude is given a goal ("place a hold on this member's share") and
exactly three tools: *act*, *check the screen*, *finish*. Nothing else. It sees a
compact text description of the page's controls — never raw HTML, never secrets —
and decides one step at a time.

The clever part happens at the moment a step *succeeds*: we look at the element
the AI just used and generate every plausible way of finding it again — by its
role and label, by its name, by its placeholder text, by its position — then test
each description against the live page. Descriptions that match more than one
element are thrown away (ambiguity is how automations click the wrong thing).
The survivors are ranked from most durable to most fragile and recorded. We call
this the **locator ladder**.

Guardrails: a stuck-detector (the AI repeating the same move on the same page gets
cut off), a turn budget, and validation of everything the model sends back — an
unrecognized tool name is rejected at the boundary instead of crashing the run.

Everything is written to `trace.json`: every turn, every probe, every hesitation.

### 4. The recipe writer — the Compiler (`src/handrail/compile/`) — NEXT UP (PR 3)

Turns the diary into the recipe. Crucially, it is **pure code — no AI**. Several
well-known systems put an AI inside their "deterministic" compile step (to name
parameters, to guess selectors) and then need a second apparatus to catch its
hallucinations. We avoid the whole problem: the compiler can only use locators
that were actually probed against the live page during discovery. It cannot
invent anything.

**How it will work:**

- One recipe step per successful AI action, carrying its locator ladder.
- Values the operator supplied (member number, amount) are recognized in the
  trace and replaced with fill-in-the-blank slots — `{{input.member_number}}`.
  Matching is longest-first with a minimum length, and secret-shaped parameters
  are never matched by value: if a real secret shows up literally in the trace,
  the compiler refuses outright, because that means discovery leaked.
- Pauses the AI naturally took between steps become explicit small "wait" steps.
- Screen checks the AI made become **checkpoints** — "the page must say MEMBER
  RECORD here" — that gate replay progress.
- The compiler *refuses* to produce a doubtful recipe (no surviving locator, a
  required input never used, a checkpoint that just echoes data it read) rather
  than emitting something that would fail mysteriously later.
- Optionally, a fresh recipe is verified by replaying it once against the live
  app before it is saved — learn, then prove, then trust.

### 5. The recipe itself — the Capability (`capability.json`) — SCHEMA BUILT

A typed, versioned JSON document — deliberately *data, not code*. Comparable
systems compile agent runs into generated Python or opaque cache blobs; both are
hard to review, diff, or redact. A JSON recipe can be read by a human, checked
into git, version-pinned, and adjusted per bank without touching any logic.

What's inside: the inputs it needs (with types), the steps (each with its intent
in plain English, its action, its locator ladder, its timeout, its risk level),
the checkpoints, the known outcomes it may produce, what it requires from a
surface, and its provenance (which model discovered it, when).

The fill-in-the-blank grammar is deliberately tiny: `{{input.name}}` and
`{{env.NAME}}`, nothing else — no expressions, no code execution, resolved in a
single pass so a value can never re-expand into something unexpected.

### 6. The player — the Replay engine (`src/handrail/replay/`) — BUILT

A deliberately dumb interpreter. Reads the recipe, walks the steps, and for each
one tries the locator ladder top-down. Zero AI calls — and that is *enforced by
a test*, which audits the engine's entire import graph and poisons any path that
could reach a model. It is a proven property, not a promise.

- **Drift, the early warning.** Every time a step is found by rung 1 of its
  ladder, great. Found by rung 2 or 3? It still works — but the engine records
  the descent, and the run's drift score drops below 1.0. That tells you the
  bank's screens are shifting *before* anything actually breaks, for free.
- **Four honest outcomes.** SUCCESS (did it), BUSINESS_OUTCOME (the bank said no
  — e.g. "SHARE ALREADY UNDER HOLD"; that's an answer, not a failure),
  RECOVERABLE (timeout/maintenance — bounded retry), HARD_FAILURE (stop and tell
  a human). Callers always know which one they got, as structured data.
- **On failure it stops — unless you give it a budget.** By default it never
  re-plans and never calls a model mid-run. With `--max-llm-calls N`, a
  *supervisor* may be consulted when a checkpoint or locator fails: it drives
  the browser for a few turns towards the next checkpoint the recipe declares,
  and the engine then checks that checkpoint itself before carrying on. Every
  call is counted, every bridge is recorded as evidence, and a claim the engine
  cannot verify is treated as a give-up. Model spend scales with breakage, not
  with step count; the green path stays at zero.
- **Two things a bridge still cannot do.** An operator cannot pause one: the
  discovery loop a bridge borrows never consults `SessionControl`, so a bridge in
  flight runs its handful of turns to the end and only then hands the session
  back to a human who asked for it sooner. And a bridge that carries the run
  *past* a `read` step will fail strict output collection at the end — the step
  was skipped over, so the value it would have captured was never read, and a
  required output with nothing behind it is a failed run rather than a
  successful one with a hole in it.

**Being added in PR 2** (informed by our teardown of six open-source systems):
a structural fingerprint check — each step remembers a position-independent hash
of the element it expects, and the engine verifies the element it found matches,
catching "the locator resolved, but to the wrong thing"; an occurrence index so
two identical-looking buttons can be told apart; and a smarter page-settled
signal — after acting, wait until the *next* step's element appears, because its
presence is the ground truth that the page finished loading.

### 7. The safety kernel (`src/handrail/kernel/`) — BUILT

Four small pieces that sit under everything:

- **Policy** — an allowlist of hosts and actions. The recipe's needs are
  intersected with the runtime's policy before anything runs; if they don't
  overlap, the run refuses up front.
- **Redaction** — secrets and card numbers are scrubbed at the *boundaries*
  (the logger, the evidence writer, the serializer), not at each call site — so
  one forgotten call site cannot leak.
- **Control** — a formal state machine for who is in charge: automation, a
  human, or nobody. Pause, take over, hand back, abort — every transition
  recorded with who and when.
- **Evidence** — every run writes a per-run folder: steps, outcomes, screenshots,
  page snapshots (with tokens and passwords masked), so any run can be audited
  after the fact.

One more safety property falls out of the design for free: a compiled recipe
**cannot be prompt-injected**. Malicious text on a webpage can trick an AI; it
cannot trick a JSON file. Determinism is itself a security feature.

### 8. One recipe, many banks — Overlays (`src/handrail/tenancy/`) — PR 4

Quarrybrook and Fernhollow run the same product with different labels, frame
names, and field names. Instead of two recipes, we keep one plus a small
per-bank **overlay**: "at Fernhollow the search field is `srchval`, the button
says PF5 Find, the header reads MEMBER MASTER."

Overlays are applied by a pure function — recipe in, adjusted recipe out — and
obey strict rules: they may rename and re-point, they may *tighten* safety, they
may never change what the recipe does, and they are pinned to an exact recipe
version so an edited recipe fails loudly instead of being silently mis-aliased.

### 9. Jobs, reports, console, CLI — PRs 5–7

- **Job catalogue** (PR 5): the business tasks defined once — goal, inputs,
  expected outcomes mapped to the exact screen messages.
- **Reports** (PR 5): human-readable write-ups of any run — what happened, what
  drifted, who took control, with evidence links.
- **Operator console** (PR 6): a small web page where a person watches an
  attended replay live, can pause it, take the keyboard, and hand control back —
  driving the control state machine from a browser.
- **CLI** (PR 7): one `handrail` command tying it together — `discover`,
  `compile`, `replay`, `report`, `serve-console` — with exit codes that mirror
  the four outcomes, so scripts and schedulers get honest answers too.

## How we're building it

Work proceeds as small, independently reviewed pull requests
([full breakdown](superpowers/plans/2026-08-30-pr-breakdown.md)):

| PR | What | State |
|----|------|-------|
| 1 | Foundation: everything above marked BUILT (54 commits, 268 tests) | done, to merge |
| 2 | Replay hardening: fingerprint check, occurrence index, settle wait | ready to start |
| 3 | The compiler | after PR 2 |
| 4 | Tenant overlays | parallel |
| 5 | Jobs, outcomes, reports | parallel |
| 6 | Operator console | parallel |
| 7 | CLI | integrates 3–6 |
| 8 | Real discovery runs + committed evidence (needs an API key) | after 7 |
| 9 | Submission docs | last |

PRs 2, 4, 5 and 6 touch disjoint files by design, so separate agents build them in
parallel against a set of frozen interface contracts written into the breakdown.
Every PR must pass the full gate (lint, types, tests) on its committed tree, and
every one gets an adversarial review before merge — a process that has already
caught two false "all green" reports and one real password leak.

## Why not just use an existing framework?

We surveyed and tore down the six most relevant open-source systems (Stagehand,
Skyvern, browser-use, workflow-use, Playwright MCP, agent-browser). The
learn-once-replay-forever idea is the industry's convergent pattern — but every
implementation is unfinished exactly where it counts: each stores a single
brittle element locator (ours keeps a ranked ladder), none measures drift (ours
scores it every run), none enforces checkpoints (ours gate every step), and all
three "deterministic" replayers quietly call an AI again when things go wrong
(ours refuses — and is tested to be unable to). We borrowed their best individual
tricks, with credit, and built the layer none of them ship.

## Stack

Practice bank: Python 3.12, Flask, Jinja2 (legacy on purpose).
Agent: Python 3.12 + uv, Pydantic v2 (typed schemas), async Playwright/Chromium,
Anthropic SDK (discovery only — the replay side is audited AI-free), ruff, mypy,
pytest.
