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

### 1. The engine on a fake surface

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

Demo: `uv run pytest tests/replay -q`. The factory capability replays on `NullSurface`.

### 2. The browser surface

| file | what it teaches |
|---|---|
| `surface/browser/operations.py` | Building the indexed operations table from the accessibility tree |
| `surface/browser/locators.py` | Turning a resolved element into ladder rungs, probing each for uniqueness |
| `surface/browser/fingerprint.py` | The structural hash, with the two exclusions the prototype learned |
| `surface/browser/surface.py` | Playwright behind the six verbs |
| `capabilities/example.json` | A hand-written capability against a public demo site |

Demo: `handrail replay capabilities/example.json --input ...` against a real page, `llm_calls=0`.

### 3. Authoring and the compiler

| file | what it teaches |
|---|---|
| `author/tools.py` | Three tools: `act(index, verb, value)`, `assert_screen(label)`, `finish(outcome)` |
| `author/middleware.py` | `wrap_tool_call`: probe locators, classify effect, pause on commit, record |
| `author/agent.py` | `create_agent(model, tools, middleware=[...])`, about 40 lines |
| `author/recorder.py` | Writes the trace entry before the next model call |
| `compile/compiler.py` | Trace to `Capability`; refuses on unbound input, secret literal, no surviving locator |
| `compile/verify.py` | The store-time gate: three clean replays with an independent check |

Demo: discover once on the demo site, verify, replay 100 times with zero model calls.

### 4. The terminal surface

| file | what it teaches |
|---|---|
| `surface/terminal/screen.py` | A 3270 screen as a fixed buffer of fields; the signature is exact |
| `surface/terminal/surface.py` | `py3270` behind the same six verbs; settle is "keyboard unlocked" |

Demo: the same engine and the same schema drive a green-screen session. This is the "computer
use, not just browser" milestone, and the legacy-banking wedge.

### 5. Screen signatures and the classifier rung

| file | what it teaches |
|---|---|
| `kernel/signature.py` | Stoat-style attribute-path sets: keep the chrome, ignore the rows |
| `escalate/classifier.py` | The port: `ask(state, questions) -> probabilities` |
| `escalate/backends/jev.py` | Hosted, pinned to `jev-1.13.0`, text only |
| `escalate/backends/laya.py` | On-device, nothing leaves the machine |
| `escalate/questions.py` | The six question definitions: which screen, which control, is it a commit... |
| `kernel/episodes.py` | SQLite rows for every escalation |

Demo: reword a screen's message; rung 1 still classifies it; a calibration curve is plotted.

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
