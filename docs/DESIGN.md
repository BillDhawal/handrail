# Handrail as a product — design

**Date:** 2026-09-19
**Status:** Draft for review
**Supersedes, for new work:** [2026-08-27-handrail-design.md](2026-08-27-handrail-design.md) and
[2026-09-02-supervised-replay-design.md](2026-09-02-supervised-replay-design.md). Those describe
the take-home prototype, which stays in this repository as a reference implementation and as
the source of the safety tests this design ports first.

**Working name:** Handrail. The name is not a decision this document makes.

---

## 1. What this is

A computer-use system built on one claim: **being able to do a task once tells you nothing
about doing it a hundred times.** A model works out how to perform a task in some application
one time. That run is compiled into a typed, versioned, human-reviewable artifact called a
**capability**. From then on the capability replays deterministically with no model in the
loop. When a replay check fails, the system climbs a ladder: a cheap closed-set classifier,
then a bounded model excursion, then a human who takes over the same live session. Every rung
only proposes; the engine verifies before it acts.

The pitch is ordered **repeatability, latency, audit, cost**. Cost comes last on purpose:
prompt caching has eaten most of the per-step saving, while measured repeat-run reliability of
frontier agents remains poor (on OSWorld, success on at least one of ten runs for about 78% of
tasks, success on all ten for about 36%; arXiv:2604.17849).

### What this is not

- Not a general autonomous agent that re-reasons every run.
- Not pixel automation. Where there is no structured view of the application, version 0.1 does
  not operate.
- Not a rewrite for its own sake. The prototype's safety invariants are ported as failing tests
  before any feature code exists (section 9).

### Prior art the design must be honest about

- **OpenAdapt** (MIT) ships "show the task once, it becomes a small program", with versioned
  programs, review gates, effect verifiers and halting escalation. Read it before building. The
  claims this design still makes beyond it, to be checked against its source rather than
  assumed: the write-ahead step journal, a calibrated closed-set classifier rung, and a typed
  agent-facing tool interface.
- **PreAct** (arXiv:2606.17929) published the compile-then-verified-replay architecture in June
  2026 and measured that replay with verification disabled collapses to 0% warm success as bad
  programs accumulate. Store-time verification is therefore mandatory here (section 7).
- **Four retreats from runtime AI repair** in 2026 (mabl, Google Mariner Teach & Repeat,
  Playwright MCP record/replay, AWS trajectory replay left as sample code) are the evidence for
  a replayer that refuses rather than improvises.

---

## 2. Decisions taken on 2026-09-19

| decision | choice | consequence |
|---|---|---|
| First wedge | Browser surface first, then a 3270/5250 terminal surface | "Computer use, not just browser" is delivered by the terminal surface, which is genuine legacy banking, deterministic, text-only, and buildable on macOS (`x3270` via Homebrew; `py3270` or `tnz` from PyPI, verified available). The macOS accessibility surface is a learning milestone, not the product claim. |
| App shell | After milestone 7 | Library, CLI, takeover console and MCP server come first. |
| Where runs execute | The developer's real Mac, behind an allowlist of hosts and app bundle ids | A VM per run is deferred. Human-touch detection (section 8) is required from the first desktop milestone. |
| Authoring harness | Hand-rolled loop | `deepagents` appears only in `examples/` as a caller of capabilities. |
| Classifier | Jev behind a `Classifier` port, with a cheap-LLM second implementation | Jev is an optimisation, never a pillar. Pin `jev-1.13.0`. |
| Who writes the code | The author, by hand, file by file | Files stay small. Each milestone ends in a runnable demo. |

Explicitly out of version 0.1: pixel or vision grounding, Windows, Citrix/RDP/VDI, Java Access
Bridge, a hosted service, `compile --patch`, tenant overlays, the app shell.

---

## 3. Architecture

```
        AUTHORING  (models, once)                     REPLAY  (no model on the green path)
        ─────────────────────────                     ────────────────────────────────────
 goal ─▶ author/loop.py                                capability + inputs
           planner (LLM)  states an intent              │
           classifier     picks an index                ▼
           scribe (LLM)   writes text to type          replay/engine.py ── replay/journal.py
           recorder       writes before next call        │  screen match → resolve → act → verify
           │                                             ▼
           ▼                                           escalate/ladder.py
         trace ─▶ compile/ ─▶ capability (draft)          1 classifier  (closed set)
                                │                          2 bridge      (bounded LLM)
                        verify/ store-time gate            3 human       (same live session)
                                ▼                        │
                        capability (verified)            ▼
                                                       RunResult ─▶ episodes.db, evidence/

     everything stands on:   surface/   the only code that touches an application
                             kernel/    policy · redaction · control · evidence · hash chain
                             schema/    Capability v2 · RunResult · ErrorCode · Effect
     agent-facing:           serve/mcp.py   one typed tool per approved capability
```

Dependency rule, enforced by an import-graph test: `replay`, `schema`, `surface`, `kernel` and
`compile` may not import a model client. `escalate` holds the only `Classifier` and `Bridge`
ports; concrete model-backed implementations live in `author/` and `escalate/backends/` and are
injected by the CLI.

---

## 4. The Surface protocol

Six verbs, unchanged in spirit from the prototype. What changes is that nothing about them is
DOM-shaped.

```
open(target)                       a URL, an app bundle id, or a host:port for a terminal
observe()      -> Observation      screen text + the indexed operations table + signature inputs
resolve(target_spec) -> Resolution exactly one element, or a typed refusal
act(resolution, op)  -> ActResult
evaluate(condition)  -> bool
evidence()     -> EvidenceBundle
```

**The indexed operations table** is the central idea borrowed from the Jev projects. `observe`
returns a numbered list of *legal* operations on *present* elements: a disabled button is not
in it, a checkbox is never offered as a place to type. Every model in the system chooses an
index from this table. No model output ever becomes a selector, a coordinate, a path or code.

**Verbs, not gestures.** The operation vocabulary is `invoke`, `set_value`, `select`, `toggle`,
`press_key`, `read`, `scroll`, `wait`. A surface maps each to its own mechanism: DOM click,
`AXPress`, a 3270 field write plus AID key. Because backends differ in what a verb takes (UIA
`SetValue(double)` versus a flat AX action string), each surface declares typed arity per verb.

**A settle condition is mandatory on every step**, not optional, because the macOS accessibility
API is synchronous IPC with per-element timeouts and a terminal has an explicit keyboard-locked
state. The default is "the next step's target exists"; a terminal uses "keyboard unlocked".

Surfaces in scope:

| surface | element identity | notes |
|---|---|---|
| `browser` (Playwright) | role, accessible name, test id, `name` attribute, css | port of the prototype |
| `terminal` (3270/5250 via `s3270` or `tnz`) | field by row/column and attributes, label text to its left | the screen is a fixed character buffer; signatures are exact |
| `macos_ax` (pyobjc) | `AXIdentifier`, role plus title, role plus sibling index | learning milestone; re-check TCC permissions every run |

---

## 5. Capability schema v2

```jsonc
{ "schema": "capability/2",
  "id": "bank.place_hold", "version": "1.0.0",
  "lifecycle": { "state": "draft|verified|approved|deprecated",
                 "approved_by": null, "reliability": { "replays": 0, "clean": 0 } },
  "surface": { "kind": "browser|terminal|macos_ax", "entry": "{{env.BASE_URL}}/signon",
               "requires": ["role_query"] },
  "inputs":  [ { "name": "member_number", "type": "string", "pattern": "^[0-9]{6}$" } ],
  "outputs": [ { "name": "confirmation", "type": "string",
                 "source": { "step": "read_result", "extract": "CONFIRMATION\\s+(\\S+)" },
                 "produced_on": ["hold_posted"] } ],
  "screens": { "review": { "signature": "…", "label": "the hold review screen" } },
  "targets": { "post_button": { /* below */ } },
  "steps":   [ { "id": "post_hold", "intent": "Post the hold", "screen": "review",
                 "op": { "verb": "invoke" }, "target": "post_button",
                 "effect": { "class": "commit", "confirmed_by": "…", "probe": "hold_exists" },
                 "settle": { "kind": "target_present", "step": "read_result" },
                 "expect": { "screen_in": ["posted", "already_held", "not_authorised"] } } ],
  "outcomes": { "posted":       { "category": "SUCCESS" },
                "already_held": { "category": "BUSINESS_OUTCOME", "code": "ALREADY_PROCESSED" } },
  "safety": { "allowed_hosts": [], "allowed_apps": [], "allowed_verbs": [] },
  "provenance": { } }
```

One target, surface-neutral:

```jsonc
"post_button": {
  "role": "button", "name": { "eq": "F10=Post Hold" },
  "supports": { "invoke": [] },
  "scope": [ { "role": "frame", "name": "work" } ],
  "ladder": [ { "rung": "stable_id", "cost": 1 },
              { "rung": "role_name", "cost": 100 },
              { "rung": "native", "surface": "browser", "css": "input[value='F10=Post Hold']",
                "cost": 10000000 } ],
  "fingerprint": { "over": ["role", "name", "supports", "ancestor_roles"], "value": "…" } }
```

Changes from the prototype, each fixing something that hurt:

1. **Outputs live only in `outputs`.** The prototype hid them in an outcome's `capture` block.
2. **`screen` is a mandatory precondition of every step.** A cache keyed on the instruction
   alone replays the wrong action on the wrong screen.
3. **Every step carries an effect class** (section 6). An unclassified step fails validation.
4. **Ladder rungs carry a cost, lowest wins**, using Playwright's published scale. Rungs are
   tried in order and never raced: racing hides drift, and the rung that resolved is reported in
   every result.
5. **Targets are a named repository**, so two steps on one control share one definition.
6. **No `safe_restart` flag.** Rewind legality is computed from the journal at run time.

Carried over verbatim from the prototype: the compiler refuses rather than guesses; the four
outcome categories with `BUSINESS_OUTCOME` never a failure; the closed `{{input.x}}` /
`{{env.X}}` binding grammar; the structural fingerprint with both of its exclusions; drift
measured on every run.

### Screen signatures

A screen is recognised by structure, not by text. The signature follows the Stoat
attribute-path abstraction: two screens are the same when the sets of attribute paths of their
actionable elements match, with list rows stripped ("keep the chrome, ignore the rows"). On a
terminal the signature is simply the set of protected-field positions and texts.

Matching is tiered and the artifact stores only data: (1) exact signature; (2) Jaccard
similarity at or above 0.85; (3) the classifier chooses among the step's declared
`expect.screen_in` labels plus `none_of_these`; (4) bridge; (5) human. Text literals may raise
confidence; they are never the primary detector.

---

## 6. Effects, the journal, and the one invariant

**Effect classes.** Every step is one of `read`, `navigate`, `stage` (a reversible draft: a
half-filled form) or `commit` (externally visible and not freely reversible). At authoring time
the planner proposes a class and the classifier scores it independently. Any disagreement, and
every `commit`, requires a named human to confirm before the capability can leave `draft`. The
artifact records who confirmed and when. Replay never infers an effect. The prototype's keyword
list is deleted.

**The write-ahead step journal.** Before a `stage` or `commit` step touches the surface, the
engine appends `dispatched` to the run's journal. After the step's effect is confirmed it
appends `observed`.

> **Invariant.** A step journalled `dispatched` and not `observed` is never re-executed.

From that state the only legal moves are: run the step's read-only `probe`; if the effect is
present, mark `observed`, return `ALREADY_PROCESSED`, and continue past the step; if the probe
is conclusive that the effect is absent, re-execution is permitted; otherwise, a human. A
commit without a probe is never retried. Rewind targets are the latest screen with no `stage`
or `commit` entry after it in the journal.

This single mechanism replaces `safe_restart`, `_executed_risky`, and the two separate guards
the prototype needed after it posted a hold twice on two different code paths.

**Out-of-band verification.** A checkpoint declares `verification: screen | out_of_band`. On-
screen confirmation is known to mislead (ERPBench: 85% "saved", 3% correct). A `commit` step in
an `approved` capability should carry an out-of-band probe where the application offers any
independent read path.

---

## 7. Lifecycle and store-time verification

`draft` → `verified` → `approved` → `deprecated`.

- **draft**: compiled from a trace. Never runs unattended.
- **verified**: replayed N≥3 times from a clean start with different inputs, and an independent
  check confirmed the task was really done each time. This is the gate PreAct showed separates
  a working system from one that degrades to zero; it specifically catches capabilities that
  replay to their last step and leave the task undone.
- **approved**: a named human signed the effect classes and the safety block.
- **deprecated**: replayable for audit, refused for new runs.

Expect the fallback path to be the common path early: published cache-miss rates are 50–67%,
and verification costs two to three times the wall time of the run it verifies.

Every escalation is written as a row in `episodes.db` (SQLite): what failed, what the
classifier returned, what the bridge did, whether it worked, whether a human reviewed it.
Reliability, drift rate and bridge rate are queries over that table.

---

## 8. The escalation ladder

| rung | decides | may it act | trust rule |
|---|---|---|---|
| 0 engine | deterministic match | yes | n/a |
| 1 classifier | picks among options the capability declares | no | a verdict selects a declared screen or target; the engine re-checks; it never returns outputs and never authorises a `commit` on its own |
| 2 bridge | bounded LLM using the authoring vocabulary | `read`, `navigate`, `stage` only | must end by naming a declared screen, which the engine then verifies |
| 3 human | a person on the same live session | yes | every human action is recorded; hand-back is explicit |

**The `Classifier` port** has one method: given a state and named closed-set questions, return
a probability per option. Two implementations ship: Jev (`POST
https://api.typesafe.ai/v1/systemone`, model pinned to `jev-1.13.0`, text only, 32k-token
state) and a cheap LLM with constrained output. Thresholds are per question and empirical:
accept at top probability ≥ 0.80 with a margin ≥ 0.20; anything touching a `commit` needs a
human regardless. Every call is logged with its eventual ground truth so a reliability diagram
can be drawn and the thresholds re-tuned when the pinned version changes.

Screen text is untrusted input. It can steer which option a classifier picks, so the design
never lets a classifier verdict stand in for a deterministic check.

**Control transfer.** Ownership is a single token with states `AUTOMATION_RUNNING`, `PAUSED`,
`HUMAN_CONTROL`, `ABORTED`, as in the prototype. On a native desktop the agent tags every input
event it posts; a low-level event tap treats any untagged keyboard or mouse event as a human
taking the machine and pauses the run immediately. macOS Secure Input (any focused password
field) blocks event taps system-wide, so its presence is detected and handed to a human rather
than waited out.

---

## 9. Invariants ported first

These exist as failing tests before any feature code. They are the reasons the prototype's code
looks the way it does, and a rewrite that loses them has lost the point.

1. No model client is importable from `replay`, `schema`, `surface`, `kernel` or `compile`
   (import-graph walk, module poisoning, and a socket trap).
2. A `dispatched`-not-`observed` step is never re-executed, on any path: retry, rewind, restart,
   dismissed dialog, or a bridge that reports it reached a checkpoint.
3. A forward bridge never moves the run backwards.
4. A rung's claim is verified deterministically before it is acted on; an undeclared screen or
   outcome is a give-up.
5. An ambiguous match refuses for anything that is not `read`.
6. Secrets are masked at the boundary (surface, logger, evidence writer, serialiser), never at
   call sites. A password field receives only a declared binding.
7. The binding grammar is closed and single-pass; residue is a compile-time refusal.
8. The entry target is bound exactly once, so the policy-checked string is the visited string.
9. The four outcome categories stay distinct.
10. A run never ends in a bare exception; every path yields a typed `RunResult`.
11. Engine state is per run.
12. `RunResult` reports `llm_calls` and `classifier_calls` separately, and both are zero on the
    green path.
13. Evidence entries are hash-chained, so an edited file breaks verification of what follows.

---

## 10. Milestones

Each ends in something runnable. Files are kept small enough to type and understand in a
sitting.

| # | build | demo |
|---|---|---|
| 0 | schema v2 models; the thirteen invariants as failing tests | the suite runs and fails for the right reasons |
| 1 | `Surface` protocol, `NullSurface`, journal, replay engine | a scripted flow replays; invariants 2, 3, 9, 10, 11 pass |
| 2 | `browser` surface, indexed operations table, ladder, fingerprint | a hand-written capability replays against a real site |
| 3 | authoring loop, recorder, compiler, store-time verification | discover once, replay one hundred times, zero model calls |
| 4 | `terminal` surface | the same engine and schema drive a 3270 session |
| 5 | screen signatures, `Classifier` port with two backends, `episodes.db` | a reworded screen still classifies; a calibration curve is published |
| 6 | bridge, control transfer, evidence hash chain | drift injected mid-run is bridged; a human takes over and hands back |
| 7 | MCP server; `examples/` caller using `deepagents` | an agent invokes a capability as a typed tool and handles "already held" without retrying |
| 8 | `macos_ax` surface (learning) | a note typed and saved in TextEdit with no coordinates |

The app shell follows milestone 7.

---

## 11. Open questions

- **A demo target for the terminal surface.** A public or local 3270 host that offers a
  multi-screen transaction with a commit and a business refusal. Hercules with a sample CICS
  application is the likely answer; unverified.
- **What OpenAdapt already does** in the three places this design claims novelty. To be settled
  by reading its source before milestone 1.
- **Jev's default data retention** outside an enterprise agreement is undocumented. Until it is
  known, only redacted text leaves the machine.
- **Classifier positional bias** with many options is untested. Permute option order during the
  milestone 5 calibration run.
