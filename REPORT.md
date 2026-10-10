# Handrail — design write-up

Handrail turns one model-driven run through a legacy application into a typed, versioned,
reviewable **capability**, then replays it with no model in the loop. When a replay check fails it
climbs a ladder: a closed-set classifier, then a bounded model excursion with commits denied, then
a person on the same live session. Every rung only proposes; the engine verifies before acting.
The target is PLUMBLINE, a mock core-banking app I built to be hostile the way real ones are:
framesets, no ids, no labels, table layout, per-render form tokens, terse mainframe messages, two
tenants with different markup, and faults armed on demand. Everything below was run live; the
runs are in `/evidence/examples/`.

## 1. Architecture

Three layers, one rule between them. **Schema** (`schema/`) is the artifact and the result
contract. **Replay** (`replay/`, `kernel/`) is the deterministic core: the engine, the journal,
the evidence recorder, screen signatures, the ladder's rungs. **Surface** (`surface/`) is the only
code that touches an application, behind six verbs: `open`, `observe`, `resolve`, `act`,
`evaluate`, `evidence`. The rule, enforced by `tests/invariants/test_no_model_in_the_core.py`,
which reads every import: none of those packages can reach a model client. Model-backed code
lives only in `author/` and `escalate/backends/` and is injected by the CLI.

The central idea borrowed from the Jev projects is the **numbered operations table**. `observe`
does not hand a model a page and say "point at anything". It returns a menu of legal operations
on controls that are actually present: `7: invoke button 'F5=Sign On'`. A disabled button is not
on it; a checkbox is never offered as a place to type. Every model in the system can only say a
row number, so no model output ever becomes a selector, a coordinate or code. The same menu
serves authoring, the bridge, and the classifier's `which_control` question.

Key trade-offs. The engine, journal, schema and surfaces are hand-written with no framework,
because this is the product and the thing an auditor asks about. The authoring loop is LangChain
`create_agent`, because a closed tool list and tool-call interception are commodity. Single
process, no queue: a run is one browser and one engine. The three-rung ladder is cheap before
expensive: a classifier call costs a fraction of a cent, a model excursion costs a few cents, a
person costs minutes.

## 2. Artifact schema

`schema/capability.py`, a Pydantic model with seventeen validators, each a sentence the engine
relies on. The shape: `inputs` (typed, with patterns and enums, and a `sensitivity` so a password
is masked everywhere), `outputs` (each tied to a `read` step with an extraction pattern and the
outcomes it is produced on), `screens` (a structural signature and the paths it was taken over,
never a text literal), `targets` (a named repository, so two steps on one control share one
definition), `steps`, `outcomes`, `safety`, `lifecycle`.

A **target** is described the way assistive technology describes it: role, accessible name, the
verbs it supports, a scope (frame, then table row), and a cost-ranked **ladder** of ways to find
it again. Rungs are tried cheapest first and never raced, and the rung that resolved is reported
on every run, so a capability that starts landing on rung two is the early warning that the
application moved. A **fingerprint** over role, name, verbs and ancestor roles answers "is this the
same control", which a ladder alone cannot. Two corrections from the prototype are baked in: a
submit button's `value` is its label, and a `read` step's own text is not drift.

Every **step** carries a screen precondition and an **effect class**: `read`, `navigate`, `stage`
(a reversible draft) or `commit` (not freely reversible). Effects are declared, never inferred;
the prototype's keyword guesser marked "submit the sign-on form" dangerous and would have let
"freeze the account" through. A commit must be confirmed by a named person before the card can
leave `draft`. Bindings are a closed grammar, `{{input.x}}` and `{{env.X}}`, single pass, residue
refused at load, allowed in step values and inside targets so one card can say "the Hold link in
the row for *this* share" and serve every member.

**Lifecycle**: `draft` → `verified` (three clean replays from a cold start, each confirmed by an
independent read of the record store, never the screen) → `approved` (a named person's
signature; nothing in the repository can forge it) → `deprecated`. Only approved cards are served
to agents.

## 3. Determinism & error handling

Replay validates inputs, binds the entry once, and for each step: confirm the screen, resolve the
control down the ladder, journal `dispatched` if the step mutates, act, settle, journal
`observed`, check the expected screens. No model is consulted; `classifier_calls` and `llm_calls`
in the result are both zero on this path, and a hundred replays of the model-authored card ran
that way, 11 of 11 controls on their first-choice rung every time, mean 747 ms.

The **result contract** has four categories. `SUCCESS` with typed outputs. `BUSINESS_OUTCOME`:
the application said no, an answer, never a failure, with a code such as `ALREADY_PROCESSED` or
`RECORD_NOT_FOUND`. `RECOVERABLE`: `MISSING_CONTROL`, `SLOW_LOAD`, `UNEXPECTED_DIALOG`,
`SESSION_EXPIRED`, the only category where `retryable` is true. `HARD_FAILURE`:
`SCREEN_MISMATCH`, `TARGET_MISMATCH`, `POLICY_VIOLATION`, `UNSAFE_TO_RETRY`. One table decides
which category every code belongs to, and the result refuses to disagree with it. A failure says
which step, what was expected and what was seen, and the recorder photographs the screen.

**The one invariant.** A commit step journalled `dispatched` and not `observed` is never
re-executed, on any path: retry, restart, rewind, dialog, or a bridge that claims it reached a
checkpoint. The journal is append-only and on disk before the surface is touched. The prototype
double-posted a hold once; the test that makes that impossible is the first one to read.

**Screens** are recognised by structure, not text: the set of attribute paths of the elements
(tag, classes, `name` attribute, never a value). Matching is tiered: exact hash; then Jaccard at
0.85 or above, so a new banner is a moved chair and not a new room; then the ladder. **Settling**
is a mandatory condition on every step: the next step's control is present, or the named screen
is showing, polled by the engine while the surface answers only what is true now.

## 4. Heterogeneity & multi-tenant

The seam is the surface protocol. Nothing in the engine, the schema or the ladder is DOM-shaped.
A target's role, name and scope mean the same thing for a DOM button, an `AXButton` and a field
on a 3270 screen; a terminal reports protected-field positions as its paths and needs nothing
else from the signature code; its settle condition is "keyboard unlocked", already in the schema.
The browser surface's walker computes role and name itself rather than trusting the accessibility
snapshot, because PLUMBLINE's fields have no labels and its messages are plain divs: a nameless
field is named from the caption to its left, which is also how the `label` rung finds it again.
A `native` rung carries a CSS selector that only that surface can follow, at the highest cost.

Multi-tenant reuse is designed, not built. PLUMBLINE's two tenants differ in frame names, field
names, button labels and headers. The artifact is already data, not code, so the plan is a base
capability per vendor product plus a per-tenant **overlay** that overrides target ladders and
screen signatures by name and nothing else; the compiler's existing refusals apply to the merged
result. Drift is measured on every run from data already in the result: the rung that resolved,
the signature tier, and every ladder climb as a row in `episodes.db`. A tenant whose runs start
landing on rung two gets a re-verification, not a re-recording.

## 5. Escalation & handoff

"Stuck" is a failed deterministic check that the ladder cannot resolve. Rung one asks a
**classifier** a closed question, `which_screen` among the screens the step expects plus
`none_of_these`, and accepts an answer only above a threshold with a margin *and* when the chosen
screen's stored furniture overlaps the page at 0.5. Screen text is untrusted; furniture cannot be
talked into anything. Three backends behind one port: Claude with the answer sheet enforced, Laya
on-device so nothing leaves the machine (verified: it abstained honestly at 0.46 on a reworded
line), and TypeSafe's Jev, written but not run. Rung two sends a **scout**: the authoring agent on
the same three-line card with `commit` struck off and a four-turn leash, which must end by naming
an expected screen the engine then checks the same way. A scout naming a screen behind the run is
ignored: a bridge goes forward or not at all.

Rung three is the **baton** (`kernel/control.py`): one token, `AUTOMATION_RUNNING`, `PAUSED`,
`HUMAN_CONTROL`, `ABORTED`, exchanged only by name and reason. The engine pauses, records the
screen, and the **console** (`serve/console.py`, a few dozen lines over localhost) shows the
expected screens and three buttons: take over, hand back naming a screen, abort. The person
drives the same headed browser the run was using. On hand-back the engine records who and when,
photographs the screen again, and continues; the result says `escalated_to_human`. A person's
word is final only where the machine cannot tell: a hand-back naming a screen the page visibly
contradicts is a mismatch, not a recovery, and that was tested live.

## 6. Safety

An **allowlist** of hosts is enforced twice: `open` refuses an entry outside it, and a route
handler drops every request to any other host. Allowed verbs are a closed list on the card. Risk
is the declared effect class: a commit pauses for a named person at authoring time, is never
retried without a probe, and is never re-executed when in doubt. During authoring a button press
is a commit until the owner says otherwise. **Secrets** are masked at four boundaries, never at
call sites: inputs marked secret are registered with the recorder and replaced in everything it
writes; the trace stores blanks, never values; the compiler refuses a typed literal that belongs
to an input; the MCP tool's schema never shows a secret input and the server fills it from its
own environment. Limits: masking is by value, so a secret that appears transformed would pass;
there is no VM per run, only the allowlist; a person's actions during takeover are recorded as
before-and-after evidence, not as individual clicks.

## 7. Cuts

Cut: the terminal surface (no 3270 host to run against), the macOS accessibility surface, the
tenant overlay, the control rung (`which_control` is on the card but not wired into resolve),
recording a person's clicks during takeover, a VM per run, and Jev live (no key). The authored
card has one outcome because authoring saw one path; the hand-written card declares `already_held`
and `no_match` as business outcomes and is the one served to the example agent. Next, in order:
the tenant overlay against PLUMBLINE's second tenant, the control rung, a TN3270 mock so the
terminal surface can be built the way the browser one was, then the input-event tap on macOS that
flips the baton when a human touches the keyboard.
