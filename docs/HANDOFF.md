# Handoff — where things stand

**Written:** 2026-10-08, at the end of milestone 6 (milestone 4, the terminal, is skipped until a 3270 host is at hand).
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
- 2026-10-08: milestone 3 done. 266 tests. claude-sonnet-5 authored the place-hold flow once,
  the compiler wrote the card, the gate verified it, 100 replays ran with zero model calls.
  The author extra (LangChain 1.4) is installed; `ANTHROPIC_API_KEY` lives in `.env`.
- 2026-10-08, later: milestone 5 done. 299 tests. Signatures are tiered, the classifier port
  has three backends (Claude live, Jev and Laya unverified), rung one names a reworded screen
  and re-checks it, every whistle lands in `episodes.db`. Milestone 4 was skipped: no 3270 host.
- 2026-10-08, later still: milestone 6 done. 321 tests. Laya verified on-device. The scout
  (rung two) crossed a reworded result in one turn; the console (rung three) took a person's
  hand-back on a page nothing else could place. The classify extra is installed.

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
  schema/     errors, bindings, effects, target, capability, results, trace   milestones 0, 3
  surface/    base (six verbs), null_surface (scripted stage set)            milestone 1
  surface/browser/  operations, locators, fingerprint, walk, queries, surface  milestone 2
  replay/     validate, journal, engine, prepare, screens, rungs/{one,two,three}  1, 5, 6
  kernel/     evidence, signature, episodes, control (the baton)             milestones 1, 5, 6
  author/     tools, middleware, agent, recorder, run, bridge (the scout)     milestones 3, 6
  compile/    compiler, verify                                                milestone 3
  escalate/   questions, classifier, bridge (ports), backends/{claude,jev,laya}  milestones 5, 6
  serve/      console (the stop button and the telephone)                     milestone 6
  cli.py      replay (--classifier, --bridge, --console), observe, author, verify, episodes
capabilities/ plumbline-place-hold.json (hand-written), .authored.json (model, verified, with paths)
targetapp/    PLUMBLINE: two tenants, /__test__/share/<id>, faults drift_minor, drift_reword, drift_major
tests/        321 passing; the invariants live in tests/invariants/
docs/         DESIGN.md, PLAN.md, this file, the site (index, five-pictures, as-built), prototype/
```

The engine replays the factory capability (`tests/factory.py`, a place-hold flow) on the
scripted surface and returns `SUCCESS` with `confirmation=HX-829120`, both model counters zero.
The test to read first is `tests/replay/test_engine.py::test_a_step_in_doubt_is_never_repeated_across_runs`:
the double-post bug from the prototype, made impossible by the journal.

## Design choices made during milestones 1 to 6

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
- **The guard is the middleware.** PLAN named LangChain's `wrap_tool_call`; the `Guard` in
  `author/middleware.py` already probes, classifies, confirms and records before the model hears
  the answer, and the three tools call it directly. A second fence around the same field was not
  built.
- **Tool calls run one at a time.** A lock in the guard, because the model batches calls and the
  loop runs them concurrently. Without it the sign-on form was clicked empty seven times.
- **`Turn` lives in `schema/trace.py`.** The compiler must never import from `author/`; the
  invariant test caught the first draft doing exactly that.
- **Cautious effect classification.** A button press is a commit until a person says otherwise.
  The owner may answer commit, navigate, stage or deny at the prompt, and the name is written in.
- **Row keys come only from real grids.** A table with a header row is a grid; a layout table's
  first cell is the field's caption and belongs to the label rung.
- **A blanked name leaves the fingerprint.** The compiler retakes it over role, supports and
  ancestor roles; that is what makes "the link for this member" the same control for every member.
- **A verdict is never believed on its own.** Rung one accepts a referee's answer only above
  the card's threshold *and* when the chosen screen's stored paths overlap the page at 0.5 or
  more. A screen with no stored paths cannot be re-checked, so no verdict for it is ever acted on.
- **A referee is asked once per screen per run.** The memo lives in `replay/rungs.py`.
- **`held` means the run ended well.** An accepted verdict is marked held when the run ends in
  SUCCESS or a business outcome; that is the ground truth the calibration table uses.
- **The Claude backend numbers its options.** Labels are free text; schema keys are not.
- **The scout's report is checked like the referee's.** Named screen must be a candidate (never
  backwards) and the furniture must overlap at 0.5. The scout's leash is four turns.
- **A person's word is final, but only where the machine cannot tell.** A hand-back must name a
  candidate; and if the page matches another declared screen exactly, that match wins.
- **The baton lives in `kernel/control.py` and the console only moves it.** The engine checks it
  before every step and waits while a person holds it; abort is final.
- **Rungs are a package.** One file per rung, each with the same per-page memo.

## What is next — milestone 7, agents as callers

Files, in order, each with a test first (details in `docs/PLAN.md`):

1. `serve/mcp.py` — one typed tool per approved capability. The tool's input schema is the
   card's inputs; the result says the outcome category, the outputs, and whether a retry is safe
   (`RunResult.retryable`). An agent never drives the screens; it calls the tool.
2. `examples/agent_caller.py` — a `deepagents` caller that invokes place_hold and handles
   "already held" without retrying.

Needs: a lifecycle step that moves a verified card to `approved` with a named person (nothing
grants that today; a `handrail approve CAP --by NAME` is the natural home), and the MCP SDK.

Still pending: wire `which_control` into resolve (the control rung); a Playwright event tap
so a person's clicks during `HUMAN_CONTROL` are recorded; milestone 4 when a 3270 host exists.

## Open questions, deliberately not guessed

- Which 3270 host to demo the terminal surface against. Hercules with a sample CICS
  application is the likely answer; unverified. Milestone 4 waits on this.
- Jev is written against the TypeSafe SDK's `system_one` and untested: no `TYPESAFE_API_KEY`.
  Laya is verified on-device (loads in about a minute, answers in about a tenth of a second).
- What OpenAdapt (MIT, `github.com/OpenAdaptAI/OpenAdapt`) already does in the three places
  this design claims to be new. README-level answer, 2026-10-07: their README mentions no
  write-ahead journal and no classifier rung; it does have an agent-facing run tool
  (`openadapt-agent serve --allow-run`) and an independent check of the record store after a run,
  much like our verify gate. So the journal and the classifier rung still look new; the typed
  agent interface does not. Source not read yet; do that before milestone 7.
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
- Truncating a log file with `: > file` while a server still writes to it leaves a hole of NUL
  bytes, and `grep` then prints nothing. Use `strings file | grep`, or restart the server.
- `STORE` in `targetapp` is one object per process. Two test modules that each start PLUMBLINE in
  a thread share it; a hold placed by one is seen by the next. Each bank fixture calls
  `STORE.reset()` first.
- A scripted fake chat model needs a unique id on every tool call, or LangGraph's router loses
  its way and raises `KeyError: 'model'`.
- Claude batches tool calls and LangChain runs them concurrently. Without the guard's lock the
  sign-on form was clicked empty seven times. The bank's own request log is what showed it.
- `targetapp.ARMED` is one dict per process, like `STORE`. A test that arms a fault with
  `once=false` must reset it, or the next test module replays against a drifted bank.
- A structured-output schema's property names must be identifiers. "Hold Result" is not.
- A card without stored paths cannot climb the ladder. Anything authored before 2026-10-08 needs
  re-authoring, or `paths` filled in from a live walk.
- Laya's question type is `choice` with `criteria`, the same shape as TypeSafe's; `single_choice`
  does not exist.
- A scout with eight turns and no commits still walked the application backwards. Four turns.
- `zsh` does not word-split `$VAR`; a flag string in a variable is one argument. Use `${=VAR}`.
