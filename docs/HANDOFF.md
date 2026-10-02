# Handoff — where things stand

**Written:** 2026-10-02, at the end of milestone 2.
**For:** the next Claude session working in this folder, and for Dhawal coming back after a break.

## What this is, in three sentences

Handrail turns one model-driven run through an application into a typed, versioned, reviewable
**capability**, then replays it deterministically with zero model calls. When a replay check
fails it climbs a ladder: a cheap closed-set classifier, then a bounded model excursion, then a
person on the same live session. It is being built as a product, aimed first at legacy
back-office software (banks and credit unions), not as the take-home it started as.

## How we got here

- August 2026: a browser-only prototype at `/Users/dhawal/work/interface_ai` for the
  interface.ai take-home. It worked, and it taught us five things that are now design rules.
  Its documents are copied to `docs/prototype/`.
- 2026-09-19: decision to rebuild from scratch as a product, desktop and browser, with Dhawal
  typing every file to learn it. Six research agents produced the design in `docs/DESIGN.md`.
- 2026-09-26: this repo created beside the old one. Framework decisions settled (below).
- 2026-09-27: milestones 0 and 1 done. 141 tests, ruff and mypy strict clean.
- 2026-10-02: milestone 2 done. 204 tests. The hand-written capability replays on PLUMBLINE
  with both model counters zero. The browser extra and Chromium are installed in `.venv`.

## Decisions already made — do not reopen

| decision | choice |
|---|---|
| Replay engine, journal, schema, surfaces | hand-written, no framework; this is the product |
| Authoring loop | LangChain `create_agent` plus middleware, closed three-tool vocabulary; `deepagents` only as a demo caller in `examples/` |
| Closed-set decisions | `Classifier` port with two backends: Jev (TypeSafe, hosted, pinned `jev-1.13.0`, $0.042/1M input tokens, text only) and Laya (Apache-2.0, on-device, nothing leaves the machine) |
| First surfaces, in order | browser (Playwright), then 3270/5250 terminal (`py3270`), then macOS accessibility as a learning milestone |
| Where runs execute | Dhawal's real Mac behind an allowlist; a VM per run deferred |
| App shell (chat left, live app right) | after milestone 7 |
| Out of version 0.1 | pixel/vision grounding, Windows, Citrix/RDP, Java Access Bridge, hosted service, tenant overlays, `compile --patch` |

## What exists

```
src/handrail/
  schema/     errors, bindings, effects, target, capability, results   milestone 0
  surface/    base (six verbs), null_surface (scripted stage set)     milestone 1
  surface/browser/  operations, locators, fingerprint, walk, queries, surface   milestone 2
  replay/     validate, journal, engine                                milestone 1
  kernel/     evidence (hash-chained log, masking at the writer)       milestone 1
  cli.py      handrail replay, handrail observe                        milestone 2
  compile/ escalate/ author/ serve/                                    empty, named
capabilities/ plumbline-place-hold.json, hand-written, draft          milestone 2
targetapp/    PLUMBLINE, the mock bank from the prototype (two tenants)
tests/        204 passing; the invariants live in tests/invariants/
docs/         DESIGN.md, PLAN.md, this file, prototype/
```

The engine replays the factory capability (`tests/factory.py`, a place-hold flow) on the
scripted surface and returns `SUCCESS` with `confirmation=HX-829120`, both model counters zero.
The test to read first is `tests/replay/test_engine.py::test_a_step_in_doubt_is_never_repeated_across_runs`:
the double-post bug from the prototype, made impossible by the journal.

## Design choices made during milestones 1 and 2

- **Stage steps are redone on a resumed run; commit steps never are.** Re-typing a field is
  harmless by definition. Without this a run resumed after a crash would skip typing the member
  number into a fresh, empty form. Recorded in `replay/engine.py`'s docstring.
- **Bindings are allowed inside targets.** A target's name, a scope name or a rung value may say
  `{{input.share_id}}`. It is the only way to say "the Hold link in the row for *this* share".
  The validator refuses an undeclared input there too; `bind_target` fills the blanks at run time
  and the artifact is never changed. In `schema/bindings.py`.
- **The milestone 2 screen signature is a hash over structural paths**: tag, classes and `name`
  attribute, never text or values. "HOLD POSTED" and "SHARE ALREADY UNDER HOLD" differ by one
  class on the message line, and that is enough. Milestone 5 replaces this with the tiered match.
- **The walker computes role and name itself** rather than reading Playwright's accessibility
  snapshot, because PLUMBLINE's fields have no labels and its messages are plain divs: the
  snapshot would show almost nothing. A nameless field is named from the caption to its left.
- **A click waits for the frame it navigated.** Otherwise the engine asks "which screen" while
  the old document is still showing. `NAVIGATION_GRACE_MS` in `surface/browser/surface.py`.
- **No `position` rung is ever proposed.** "The third link" breaks the day a row is added.

## What is next — milestone 3, authoring and the compiler

Files, in order, each with a test first (details in `docs/PLAN.md`):

1. `author/tools.py` — three tools: `act(index, verb, value)`, `assert_screen(label)`,
   `finish(outcome)`. The model only ever says a row number from the menu.
2. `author/middleware.py` — `wrap_tool_call`: probe locators with `locators.surviving` and
   `queries.FrameProbe`, classify the effect, pause on a commit, record the turn.
3. `author/agent.py` — `create_agent(model, tools, middleware=[...])`, about 40 lines.
4. `author/recorder.py` — the trace entry is on disk before the next model call.
5. `compile/compiler.py` — trace to `Capability`; refuses on unbound input, secret literal, no
   surviving locator. Copies `operations.supports_for` into each target.
6. `compile/verify.py` — the store-time gate: three clean replays with an independent check.

Demo at the end: discover the place-hold flow once on PLUMBLINE, verify, replay 100 times with
zero model calls. Needs `ANTHROPIC_API_KEY` in `.env`; the first file that touches a model.

Before starting: read OpenAdapt's source for the three places this design claims novelty (open
question below). Milestone 3 is where the comparison starts to matter.

After that: 4 the terminal surface, 5 screen signatures and the classifier rung, 6 bridge and
human takeover, 7 MCP server, 8 macOS accessibility.

## Open questions, deliberately not guessed

- Which 3270 host to demo the terminal surface against. Hercules with a sample CICS
  application is the likely answer; unverified.
- What OpenAdapt (MIT, `github.com/OpenAdaptAI/OpenAdapt`) already does in the three places
  this design claims to be new: the write-ahead journal, the classifier rung, the typed
  agent-facing interface. Read its source before milestone 5.
- Jev's default data retention outside an enterprise agreement. Until known, only redacted text
  leaves the machine.

## Things that bit us, so they do not bite again

- An editor paste can drop the trailing newline; `make lint` fixes it.
- A scoped test run once hid a red suite for two tasks. Always run the full `make test`.
- Popping a module from `sys.modules` in a test leaves the package attribute stale and breaks
  `monkeypatch` in the next test. Restore in a `finally`.
- The prototype's risk-keyword list marked "submit the sign-on form" as dangerous and left the
  rewind feature inert on the flagship capability. Effect classes are declared, never inferred.
- `frame.locator("body").inner_text()` on a frameset's top document waits a full second for a
  body that will never exist, on every observe. Use `evaluate` and tolerate "not there".
- A scratch clone's `uv sync` once left `handrail` unimportable; `uv sync --reinstall-package
  handrail` fixed it. Check `python -c "import handrail"` before trusting a green run there.
- Playwright's text engine reads a submit button's `value` as its text, so the `text` rung does
  survive on `F5=Sign On`. The live page beat the assumption; the test was corrected.
