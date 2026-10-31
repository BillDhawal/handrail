# Handrail — design write-up

**What it does, in one paragraph.** A bank has old screens with no API. Handrail lets an AI
model work through a task on those screens once, while a person watches. That one run is turned
into a small, typed file called a **capability**. From then on the task is replayed from the
file, with no model involved, in about a second. When a replay hits a screen it does not
recognise, it climbs a ladder: first a cheap classifier, then a model on a short leash that may
not commit anything, then a person who takes over the same browser. Each rung only suggests; the
engine checks the suggestion before acting on it.

The target is PLUMBLINE, a fake core-banking app I built to be as awkward as the real ones:
framesets, no ids, no labels, table layouts, form tokens that change every page, terse mainframe
messages, two tenants with different markup, and faults I can switch on. Everything in this
write-up was run for real; the runs are in `/evidence/examples/`.

Where to look: the code is at https://github.com/BillDhawal/handrail. A user guide with
screenshots of every command is at [docs/HANDRAIL-GUIDE.pdf](docs/HANDRAIL-GUIDE.pdf). Two
illustrated walkthroughs are at https://billdhawal.github.io/handrail/.

## 1. Architecture

Think of a restaurant. The **schema** (`schema/`) is the recipe card and the receipt. The
**replay engine** (`replay/`, `kernel/`) is the kitchen: it cooks from the card and never talks
to a model. The **surface** (`surface/`) is the waiter, the only code that touches the
application, through six verbs: `open`, `observe`, `resolve`, `act`, `evaluate`, `evidence`. The
**author** package is the one evening a chef is in the kitchen, and the **escalate** package
holds the referees the engine may ask when it is lost.

One rule holds it together: nothing in `schema`, `replay`, `surface`, `kernel` or `compile` can
import a model client. A test reads every import and fails if one appears. Models live only in
`author/` and `escalate/backends/`, and the command line hands them in.

The idea everything rests on is the **numbered menu**. When the model looks at a page, it is not
shown raw HTML and told "click anywhere". It gets a list of legal moves on controls that really
exist: `7: invoke button 'F5=Sign On'`. A disabled button is not on the list. A checkbox is never
offered as a place to type. The model answers with a row number, so nothing a model says ever
becomes a selector, a coordinate, or code. The same menu is used for discovery, for the model on
a leash, and for the classifier's questions.

Trade-offs. The engine, journal, schema and surfaces are hand-written with no framework, because
that is the product and the part an auditor will ask about. The discovery loop uses LangChain's
`create_agent`, because a fixed list of tools and a hook on each tool call are commodity. One
process, no queue: one run is one browser and one engine. The ladder is ordered cheap to
expensive: a classifier call costs a fraction of a cent, a model excursion a few cents, a person
costs minutes.

## 2. Artifact schema

The capability is a Pydantic model in `schema/capability.py` with seventeen checks. Each check is
one sentence the engine relies on, such as "every step names a screen that exists". The parts:

- **inputs**: typed, with patterns and allowed values. A `sensitivity: secret` flag means the
  value is masked everywhere it could appear.
- **outputs**: each is tied to a `read` step, with an optional pattern to pull out the value, and
  the outcomes it is produced on.
- **screens**: recognised by their structure, never by their text. Each stores a hash and the set
  of element paths it was computed from.
- **targets**: one named entry per control, so two steps on the same button share one definition.
- **steps**, **outcomes**, **safety**, **lifecycle**.

A **target** is described the way a screen reader would describe it: a role, a name, the verbs it
supports, a scope (which frame, which table row), and a cost-ordered list of ways to find it
again, called a ladder. Rungs are tried cheapest first and never in parallel. Every run reports
which rung found each control, so a capability that starts needing rung two is the early warning
that the application changed. A **fingerprint** of role, name, verbs and ancestors answers "is
this the same control?", which a ladder alone cannot.

Every **step** carries the screen it expects and an **effect class**: `read`, `navigate`, `stage`
(a draft you can discard) or `commit` (something you cannot freely undo). Effects are declared,
never guessed. My earlier prototype guessed from keywords; it flagged "submit the sign-on form"
as dangerous and would have let "freeze the account" through. A commit must be confirmed by a
named person before the card can leave `draft`. Blanks use a tiny grammar, `{{input.x}}` and
`{{env.X}}`, and may appear inside a target too, so one card can say "the Hold link in the row
for *this* share" and serve every member.

**Lifecycle**: `draft`, then `verified` (three clean replays from a cold start, each checked
against the bank's record store, never the screen), then `approved` (a named person signs; no
code in the repo can forge the name), then `deprecated`. Only approved cards are offered to
agents.

## 3. Determinism & error handling

Replay checks the inputs, binds the entry URL once, and for each step: confirm the screen, find
the control down its ladder, write `dispatched` to the journal if the step changes anything,
act, wait for the settle condition, write `observed`, check the next screen. No model is asked.
The result carries two counters, `classifier_calls` and `llm_calls`, and on this path both are
zero. A hundred replays of the model-written card ran this way, every control on its first-choice
rung, mean 747 ms.

The **result** has four categories:

| category | meaning | may retry |
|---|---|---|
| `SUCCESS` | done, outputs attached | no need |
| `BUSINESS_OUTCOME` | the bank said no: `ALREADY_PROCESSED`, `RECORD_NOT_FOUND`. An answer, not a failure | no |
| `RECOVERABLE` | `MISSING_CONTROL`, `SLOW_LOAD`, `UNEXPECTED_DIALOG`, `SESSION_EXPIRED` | yes |
| `HARD_FAILURE` | `SCREEN_MISMATCH`, `TARGET_MISMATCH`, `POLICY_VIOLATION`, `UNSAFE_TO_RETRY` | no |

One table says which category each code belongs to, and the result refuses to disagree with it.
A failure says which step, what was expected, what was seen, and the recorder takes a screenshot.

**The one rule that never bends.** A commit step journalled `dispatched` but not `observed` is
never run again, on any path: retry, restart, resume, after a dialog, or because a model claims it
reached a checkpoint. The journal is written to disk before the browser is touched. My prototype
once posted a hold twice; the test that makes that impossible is the first one worth reading.

**Screens** are recognised by structure, not words: the set of element paths (tag, classes, name
attribute, never a value). Matching has three tiers: an exact hash; then a similarity score of
0.85 or more, so a new banner is a moved chair and not a new room; then the ladder. **Settling**
is required on every step: the next control is present, or the named screen is showing. The
engine polls; the surface only ever reports what is true right now.

## 4. Heterogeneity & multi-tenant

The seam is the surface protocol. Nothing in the engine, the schema or the ladder knows what a
DOM is. A target's role, name and scope mean the same thing for a web button, a macOS `AXButton`
and a field on a 3270 terminal screen. A terminal would report its protected-field positions as
its paths and needs nothing else from the signature code; its settle condition, "keyboard
unlocked", is already in the schema. The browser surface works out role and name itself instead
of trusting the accessibility snapshot, because PLUMBLINE's fields have no labels: a nameless
field is named from the caption to its left, which is also how the `label` rung finds it again.

Multi-tenant reuse is designed, not built. PLUMBLINE's two tenants differ in frame names, field
names, button labels and headers. Because the capability is data, not code, the plan is one base
card per vendor product plus a small per-tenant **overlay** that overrides target ladders and
screen signatures by name and nothing else. Drift is measured on every run from data already in
the result: which rung found each control, which tier matched each screen, and every ladder
climb as a row in `episodes.db`. A tenant whose runs start landing on rung two gets re-verified,
not re-recorded.

## 5. Escalation & handoff

"Stuck" means a deterministic check failed and the ladder could not fix it.

**Rung one** asks a classifier a closed question: "which of these screens is this?", with the
screens the step expects plus `none_of_these`. An answer is accepted only above a confidence
threshold with a margin, *and* only if the chosen screen's stored structure overlaps the page by
at least half. Screen text is untrusted; structure cannot be talked into anything. Three
classifiers sit behind one interface: Claude with a forced answer sheet, Laya running on the
machine so nothing leaves it (tested: it said "not sure" at 0.46 on a reworded line, which is the
right answer), and TypeSafe's Jev, written but not run.

**Rung two** sends the discovery model back in with `commit` removed from its tools and a
four-turn limit. It must end by naming an expected screen, which the engine then checks the same
way. If it names a screen the run already passed, it is ignored: a bridge goes forward or not at
all.

**Rung three** is the baton, in `kernel/control.py`: one token with four states,
`AUTOMATION_RUNNING`, `PAUSED`, `HUMAN_CONTROL`, `ABORTED`, passed only by name and reason. The
engine pauses, saves a screenshot, and a small web page (`serve/console.py`, localhost only)
shows the expected screens and three buttons: take over, hand back naming a screen, abort. The
person drives the same browser the run was using. On hand-back the engine records who and when,
takes another screenshot, and continues; the result says `escalated_to_human`. A person's word is
final only where the machine cannot tell: a hand-back naming a screen the page clearly
contradicts is a mismatch, not a recovery. That was tested live.

## 6. Safety

An **allowlist** of hosts is enforced twice: opening a URL outside it is refused, and every
request the browser makes to any other host is dropped. The verbs a card may use are a closed
list. Risk is the declared effect class: a commit asks a named person at discovery time, is never
retried without an independent check, and is never run twice when in doubt. During discovery a
button press is treated as a commit until the owner says otherwise.

**Secrets** are masked at the boundaries, never at call sites: inputs marked secret are given to
the recorder, which replaces them in everything it writes; the discovery trace stores blanks like
`{{input.password}}`, never values; the compiler refuses a typed literal that belongs to an
input; the MCP tool's schema never shows a secret input, and the server fills it from its own
environment. Limits: masking is by exact value, so a transformed secret would pass; there is no
sandbox per run, only the allowlist; a person's actions during takeover are recorded as a
screenshot before and after, not as individual clicks.

## 7. Cuts

Left out, on purpose: the terminal surface (no 3270 host to test against), the macOS
accessibility surface, the tenant overlay, the control rung (the classifier's "which menu row"
question exists but is not wired into resolve), recording a person's clicks during takeover, a
sandbox per run, and running Jev live (no key). The model-written place-hold card has one
outcome because discovery saw one path; the hand-written card also declares `already_held` and
`no_match`, and is the one the example agent uses. A second model-written card, read a share's
balance, was authored, verified and approved after submission work began, and exposed two gaps
that are now fixed: table cells were not on the menu, and the verify gate had one hard-wired
check.

Next, in order: the tenant overlay against PLUMBLINE's second tenant; the control rung; a small
TN3270 mock so the terminal surface can be built the way the browser one was; then the macOS
input tap that pauses the run the moment a human touches the keyboard.
