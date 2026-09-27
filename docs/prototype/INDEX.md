# The prototype, for reference

These files are copied unchanged from `/Users/dhawal/work/interface_ai`, the browser-only
prototype built for the interface.ai take-home in August and September 2026. Nothing in the
new repo imports it. It is here because its design write-up and its two later specs explain
*why* the invariants in `tests/invariants/` exist, and because the mock bank in `targetapp/`
came from it.

| file | what it is |
|---|---|
| `README.md` | the prototype's front page: setup, demo path, exit codes |
| `REPORT.md` | the design write-up: architecture, schema, determinism, tenancy, escalation, safety, cuts |
| `ARCHITECTURE.md` | the same system in plain language, component by component |
| `supervised-replay-design.md` | the spec that added the model bridge on drift (2026-09-02) |
| `supervised-replay-plan.md` | the ten-task plan that implemented it, with the review findings |

What the prototype got right and the new design keeps: the compiler refuses rather than
guesses; four outcome categories with "the bank said no" never a failure; a closed binding
grammar; a structural fingerprint per control; drift measured on every run.

What it got wrong and the new design fixes: risk inferred from intent keywords (replaced by
declared effect classes a person signs); `safe_restart` as a compile-time flag (replaced by the
write-ahead journal); screen detectors as text literals (replaced by structural signatures);
outputs hidden inside an outcome's `capture` block (now only in `outputs`); a DOM-shaped target
(now role, name, verbs and a ladder, the same on every surface).

The bug that shaped the most: the prototype posted a bank hold twice, on two separate code
paths, and both were found only by adversarial review after the code was "done". The journal
invariant in `replay/journal.py` exists so that class of bug cannot be written.
