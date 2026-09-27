# Handoff — where things stand

**Written:** 2026-09-27, at the end of milestone 1.
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
  replay/     validate, journal, engine                                milestone 1
  kernel/     evidence (hash-chained log, masking at the writer)       milestone 1
  compile/ escalate/ author/ serve/                                    empty, named
targetapp/    PLUMBLINE, the mock bank from the prototype (two tenants)
tests/        141 passing; the invariants live in tests/invariants/
docs/         DESIGN.md, PLAN.md, this file, prototype/
```

The engine replays the factory capability (`tests/factory.py`, a place-hold flow) on the
scripted surface and returns `SUCCESS` with `confirmation=HX-829120`, both model counters zero.
The test to read first is `tests/replay/test_engine.py::test_a_step_in_doubt_is_never_repeated_across_runs`:
the double-post bug from the prototype, made impossible by the journal.

## One design choice made during milestone 1

The "never re-execute a dispatched step" rule applies to **commit** steps. A **stage** step
(typing a field, choosing an option) is redone on a resumed run, because re-doing a reversible
draft is harmless by definition. Without this, a run resumed after a crash would skip typing the
member number into a fresh, empty form. The journal still records stage steps so rewind targets
stay conservative. Recorded in `replay/engine.py`'s docstring.

## What is next — milestone 2, the browser surface

Files, in order, each with a test first (details in `docs/PLAN.md`):

1. `surface/browser/operations.py` — build the numbered operations table from Playwright's
   accessibility tree. This is the central idea from the Jev projects: the model picks a row.
2. `surface/browser/locators.py` — from a resolved element, generate ladder rungs and probe each
   one for uniqueness on the live page. Only rungs matching exactly one element survive.
3. `surface/browser/fingerprint.py` — the structural hash, with the two exclusions the prototype
   learned (a submit button's `value` is its label; a `read` step's own text is not drift).
4. `surface/browser/surface.py` — Playwright behind the six verbs. `evaluate` never waits.
5. `capabilities/plumbline-place-hold.json` — a hand-written capability against PLUMBLINE.
6. A tiny `cli.py` with `handrail replay <capability> --input k=v` so the demo is one command.

Demo at the end: `make up`, then replay the hand-written capability against the real mock bank
and get `llm_calls=0`. PLUMBLINE is deliberately hostile: framesets, no ids, per-render tokens,
so this milestone is where the ladder and the fingerprint earn their keep.

After that: 3 authoring and the compiler (with the store-time verification gate), 4 the terminal
surface, 5 screen signatures and the classifier rung, 6 bridge and human takeover, 7 MCP server,
8 macOS accessibility.

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
