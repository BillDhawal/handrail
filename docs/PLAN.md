# Build plan

This is the order we build Handrail in, and why. [DESIGN.md](DESIGN.md) is the architecture; this
file is the path through it. Each milestone ends in something you can run. Each file is small
enough to read in one sitting, and its docstring says why it exists, not what it does.

## The frameworks, and what each one is for

Three decisions, each answering "why not just hand-roll it" or "why not just use a framework".

| layer | choice | reason |
|---|---|---|
| Replay engine, journal, schema, surfaces | **Hand-written, no framework** | This is the product. It must be deterministic, auditable and model-free, and a framework in the loop would be the thing an auditor asks you to explain. About 1,500 lines total. |
| Authoring loop (the one-time model-driven run) | **LangChain `create_agent` with middleware** | The loop itself is commodity. What we need from it is three things LangChain ships: a closed tool list, `wrap_tool_call` middleware to intercept every action before it executes, and `HumanInTheLoopMiddleware` to pause on a commit. Writing those by hand teaches nothing new. `deepagents` is not used here; its filesystem, shell and sub-agent tools are exactly what a closed vocabulary does not want. |
| Closed-set decisions (which element, which screen, is this a commit) | **`Classifier` port with two backends: Jev hosted, Laya on-device** | Jev is the accurate one (JevBench rank 1) and takes 255 options, which the indexed operations table needs. Laya is Apache-2.0, runs under 1 GB on Apple Silicon, and never sends screen text off the machine; it degrades above about 20 options, so it serves the small questions and the offline case. Neither is a pillar: the port is one method, and a run with both backends unreachable still finishes by refusing, not by guessing. |
| Agent-facing interface | **MCP server** | One typed tool per approved capability. `deepagents` appears once, in `examples/`, as a caller that shows an agent handling "already held" without retrying. |

Packages, all on PyPI as of 2026-09-26: `langchain` 1.4, `langchain-typesafe` 0.0.1a3 (alpha:
pin it), `typesafe-sdk` 0.7, `laya`, `playwright` 1.63, `py3270` 0.3. Jev's promotional pricing
ended on 2026-09-25; it now costs $0.042 per million input tokens, output free.

## How a run works, in one paragraph each

**Authoring.** You give a goal and an entry point. Each turn the surface returns a numbered table
of legal operations on present controls. The planner model states an intent in words. The
classifier picks the table index and the verb, and says whether the step looks like a commit. A
small model writes text only when the verb is `set_value`. The executor probes every way it could
find that control again and records the ones that match exactly one thing. The recorder writes
the turn to disk before the next model call. A `commit` pauses for you to confirm. `finish`
names the outcome screen. The compiler turns the trace into a capability in `draft`.

**Verification.** The draft replays three times from a clean start with different inputs. An
independent check confirms each time that the task really happened. Only then is it `verified`,
and only a named person moves it to `approved`.

**Replay.** Inputs are validated. The entry is bound once. For each step: confirm the screen
signature matches, resolve the target down the ladder, journal `dispatched` if the step mutates,
act, settle, journal `observed`, check the expected screens. A step journalled `dispatched` and
not `observed` is never re-executed. No model is consulted on this path; `classifier_calls` and
`llm_calls` are both zero in the result.

**Escalation.** A screen or target that does not match climbs a ladder. Rung 1: the classifier
chooses among the screens or controls the capability already declares; the engine re-checks its
answer. Rung 2: a bounded model excursion using the authoring vocabulary, denied `commit`, which
must end by naming a declared screen. Rung 3: you, on the same live session, with every action
recorded. Every escalation is a row in `episodes.db`.

## Milestones

### 0. Schema and the first invariants — done

What it proves: the artifact refuses to be inconsistent, and the core cannot reach a model.

| file | what it teaches |
|---|---|
| `schema/errors.py` | Four outcome categories; one table decides which category every code belongs to |
| `schema/bindings.py` | The closed `{{input.x}}` / `{{env.X}}` grammar, single pass, residue refused |
| `schema/effects.py` | `read` / `navigate` / `stage` / `commit`; a commit without a probe is never retried |
| `schema/target.py` | One target shape for every surface; a ranked ladder that is never raced |
| `schema/capability.py` | The artifact, and seven validators, each a sentence the engine relies on |
| `schema/results.py` | What a caller gets back; two model counters, both zero by default |
| `tests/factory.py` | A valid capability as a dict, so each test breaks exactly one thing |
| `tests/invariants/test_no_model_in_the_core.py` | Reads every import in the core and refuses model clients |

Run: `uv run pytest -q` — 50 passed.

### 1. The engine on a fake surface — done

What it proves: replay is deterministic and the journal invariant holds on every path.

| file | what it teaches |
|---|---|
| `surface/base.py` | The six verbs and the `Observation` with its numbered operations table |
| `surface/null_surface.py` | A scripted surface: a test says what is on screen and what each locator matches |
| `replay/journal.py` | Append-only `dispatched` / `observed` log; computes the legal rewind targets |
| `replay/validate.py` | Typed input validation against `InputSpec` |
| `replay/engine.py` | The step loop: screen check, resolve, journal, act, settle, expect |
| `kernel/evidence.py` | Per-run directory, `log.jsonl`, and a hash chain over entries |
| `tests/replay/test_engine.py` | The happy path, a business outcome, each failure code |
| `tests/invariants/test_journal.py` | A dispatched-not-observed step is never re-run: retry, restart, rewind, dialog |

Run: `make test` — 141 passed. The factory capability replays on `NullSurface`; a commit in
doubt is refused on a second run and the click count across both runs is one.

### 2. The browser surface — done

What it proves: the same engine drives a real, hostile page with zero model calls.

| file | what it teaches |
|---|---|
| `surface/browser/operations.py` | The numbered menu: one row per legal verb on each present, enabled control |
| `surface/browser/locators.py` | A rung survives only if it finds exactly one element, and it is the right one |
| `surface/browser/fingerprint.py` | The structural hash, with the two exclusions the prototype learned |
| `surface/browser/walk.py` | One JavaScript walk per frame: controls, captions, and the screen signature |
| `surface/browser/queries.py` | A `Query` into a Playwright locator; authoring and replay ask the same question |
| `surface/browser/surface.py` | Playwright behind the six verbs; `evaluate` never waits, `resolve` may |
| `capabilities/plumbline-place-hold.json` | Eleven steps, nine screens, three outcomes, signatures from a live walk |
| `cli.py` | `handrail replay` and `handrail observe`; the exit code is the outcome category |

Run: `make test` — 204 passed, about ten seconds, ten of them on a real Chromium against
PLUMBLINE started inside the test. Demo:

```bash
make up
BASE_URL=http://127.0.0.1:8081 uv run handrail replay capabilities/plumbline-place-hold.json \
  --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400118 --input share_id=400118-S0005 --input reason=LEGAL
```

Prints `SUCCESS`, the confirmation, `llm_calls=0 classifier_calls=0`, drift 11/11 first-choice.

Three things the live page taught, each now a test: bindings are needed inside targets ("the
Hold link in the row for *this* share"); the settle check must bind its target too; and after a
click that submits a form in a frame, the old document is still visible until the new one
commits, so the surface waits for the frame navigation before the engine asks which screen it is.

### 3. Authoring and the compiler — done

What it proves: a model is used once, by picking rows from the menu, and what it produced is a
card that replays with no model at all.

| file | what it teaches |
|---|---|
| `schema/trace.py` | A `Turn`: one line of the order book, pure data, so the compiler can read it |
| `author/tools.py` | Three tools: `act(index, verb, value)`, `assert_screen(label)`, `finish(outcome)` |
| `author/middleware.py` | The guard: probe rungs, classify the effect, ask the owner on a commit, record |
| `author/agent.py` | LangChain `create_agent` with the three tools; refusals come back as text |
| `author/recorder.py` | Every turn on disk, masked and hash-chained, before the next model call |
| `author/run.py` | `handrail author` and `handrail verify`; the owner's "yes" is a terminal prompt |
| `compile/compiler.py` | The book into a card; refuses by line and reports every hole |
| `compile/verify.py` | Three plates from a cold kitchen, judged against the record store |

Run: `make test` — 266 passed, about fifteen seconds. The whole evening also runs offline in
`tests/author/test_run.py` with a scripted guest on the real mock bank. Demo, live, 2026-10-08:

```bash
make up
BASE_URL=http://127.0.0.1:8081 uv run handrail author --goal "..." --id plumbline.place_hold \
  --entry http://127.0.0.1:8081/signon --entry-template '{{env.BASE_URL}}/signon' \
  --allow 127.0.0.1:8081 --out capabilities/plumbline-place-hold.authored.json \
  --input operator_id=dcolewell --input password=plumbline-demo --secret password \
  --input member_number=400118 --input share_id=400118-S0001 --input reason=LEGAL --by dhawal
BASE_URL=http://127.0.0.1:8081 uv run handrail verify capabilities/plumbline-place-hold.authored.json \
  --env BASE_URL=http://127.0.0.1:8081 --trial ... --trial ... --trial ...
```

claude-sonnet-5 authored the flow in 19 turns and 12 model calls; the compiler wrote 11 steps
and 7 screens the model named itself; the gate passed three plates for three other members;
100 replays then ran with `llm_calls=0`, `classifier_calls=0`, drift 11/11 on every one.

Four things the live run taught, each now a test or a rule:

- Claude sends several tool calls in one message and LangChain runs them concurrently. "Fill,
  fill, click" fired at once clicks an empty form. The guard holds a lock: one guest speaks at a
  time, in the order the words came out.
- Two links called Hold meant no rung survived for either. The walker now records the row a
  control sits in (only in a real grid, one with a header row), the probe looks inside that row,
  and the compiler writes the row into the target's scope, as a blank when it equals an input.
- A link named 400118 had its name in the fingerprint, so member 400337 mismatched. When the
  compiler turns a name into a blank it retakes the fingerprint without the name.
- Reading back a field you typed into is not an output. Only a read-only control is.

Not done, on purpose: the default classifier is cautious, so every button press is a commit until
the owner says otherwise at the prompt. `--confirm commit` answers for all of them up front and is
honest about it; the card then carries four commits where one would do. The classifier rung in
milestone 5 is where this gets smarter.

### 4. The terminal surface

| file | what it teaches |
|---|---|
| `surface/terminal/screen.py` | A 3270 screen as a fixed buffer of fields; the signature is exact |
| `surface/terminal/surface.py` | `py3270` behind the same six verbs; settle is "keyboard unlocked" |

Demo: the same engine and the same schema drive a green-screen session. This is the "computer
use, not just browser" milestone, and the legacy-banking wedge.

### 5. Screen signatures and the classifier rung — done

What it proves: a screen that changed is still recognised, by structure first and by a referee
second, and the referee's call is checked before it is believed.

| file | what it teaches |
|---|---|
| `kernel/signature.py` | Stoat-style path sets; tiers: exact, similar at Jaccard 0.85, none |
| `escalate/questions.py` | The closed card: which screen, which control, is it a commit, is it done, is it a dialog, session expired; `none_of_these` always on it |
| `escalate/classifier.py` | The port: `ask(state, question) -> Verdict`; `normalise` refuses options not on the card |
| `escalate/backends/claude.py` | A model with the answer sheet enforced; the one that is always reachable |
| `escalate/backends/jev.py` | TypeSafe's hosted referee, pinned `jev-1.13.0`; unverified, no key yet |
| `escalate/backends/laya.py` | On-device; unverified, the download did not fit on the disk |
| `kernel/episodes.py` | SQLite notebook: every whistle, settled by the run's outcome, binned for calibration |
| `replay/rungs.py` | Rung one: ask, then re-check the chosen screen's furniture at overlap 0.5 before believing |
| `replay/screens.py`, `replay/prepare.py` | Split out of the engine so it stays under 250 lines |

Run: `make test` — 299 passed. Demo, live, 2026-10-08, on the re-authored card (now with paths):

```bash
handrail replay capabilities/plumbline-place-hold.authored.json --classifier claude --episodes episodes.db ...
handrail episodes episodes.db
```

| scenario | result |
|---|---|
| no drift | SUCCESS, classifier_calls 0 |
| banner on every page | sign-on recognised at tier 2 (0.857); the frameset pages went to the referee, 6 calls, one per distinct screen, all held; SUCCESS |
| result line reworded and reclassed | SUCCESS, referee named "Hold Result" at 0.95, furniture overlap 0.8 |
| reworded, share already held | SUCCESS by the card's single outcome; the authored card never saw "already held" |
| reworded, no referee | RECOVERABLE SLOW_LOAD: the ladder stops at rung 0, as it should |

Every verdict is a row in `episodes.db` with `held=1` once the run succeeded; the calibration
table bins them by confidence.

What it taught:

- Option labels with spaces are not valid property names for a structured answer sheet. The
  Claude backend numbers the options and maps back.
- The engine checks the screen before a step, while settling, and after it, so one reworded
  page was asked about three times. A referee is asked once per screen per run now.
- A card authored before paths existed cannot climb: there is nothing to re-check against.
  Re-authoring took the same 19 turns and wrote 7 screens with paths.
- The control rung (`which_control`) is on the card but not wired into resolve yet; its
  deterministic re-check needs the surface to describe a menu row, which only authoring has.

### 6. The bridge and the human

| file | what it teaches |
|---|---|
| `escalate/bridge.py` | A bounded authoring run from the current screen, `commit` denied |
| `kernel/control.py` | Ownership token: `AUTOMATION_RUNNING`, `PAUSED`, `HUMAN_CONTROL`, `ABORTED` |
| `serve/console.py` | The smallest page that pauses, takes over, and hands back |

Demo: inject drift mid-run; the bridge recovers it; then a worse drift, and you take over.

### 7. Agents as callers

| file | what it teaches |
|---|---|
| `serve/mcp.py` | One typed tool per approved capability; results say `retryable` and why not |
| `examples/agent_caller.py` | A `deepagents` agent invokes a capability and handles "already held" |

### 8. macOS accessibility surface (learning)

Type and save a note in TextEdit with no coordinates. Proves the schema is surface-neutral.

## Working agreement

- Every milestone starts with its tests failing and ends with them passing. A test names the
  sentence it protects.
- No file over about 250 lines. When one grows past that, it is doing two jobs.
- A model is never consulted on the replay path. The import guard enforces it; the two counters
  in `RunResult` report it.
- When something surprises us in a live run, the fix comes with a test, and the docstring says
  what the surprise was.
