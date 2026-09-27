# Handrail — design write-up

## 1. Architecture

Three phases with deliberately asymmetric requirements. Discovery is allowed to
be slow, expensive and supervised. Compilation is pure code. Replay must be
fast, deterministic and honest about failure.

```
DISCOVERY (LLM, once)  ──trace──▶  COMPILER (no LLM)  ──▶  REPLAY (no LLM, ever)
      │                                                          │
      └── PlaywrightDomSurface ◀── Surface protocol ──────────────┘
                    kernel: policy · redaction · control · evidence
```

**The load-bearing seam is the `Surface` protocol** — a small verb set
(`navigate`, `resolve`, `act`, `evaluate`, `observe`, `evidence`) that is the
only thing allowed to touch a live application. Everything above it is written
against that protocol, which is why the replay engine can be tested exhaustively
against a scripted `NullSurface` with no browser, and why a desktop or
accessibility-tree surface is an addition rather than a rewrite.

**Key decision: the planner never writes selectors.** It describes controls the
way a person would (`target_role: "button", target_name: "F5=Sign On"`), and the
loop measures which machine-durable descriptions are actually unambiguous on the
live page. That inverts the usual arrangement, where a model emits a selector
nobody has verified. It also means the artifact's quality does not depend on the
model's selector taste.

**Key decision: the compiler is pure code.** Skyvern and workflow-use both put a
model inside their "deterministic" compile step — to name parameters, to guess
selectors — and both then need a second apparatus to catch its hallucinations.
Handrail's compiler can only use locators that were probed against the live DOM
during discovery, so inventing one is not a thing it can do. `compile/` imports
nothing that can reach a model, and a test asserts it.

**Trade-off I accepted:** discovery and replay share the Surface but not the
targeting path — discovery resolves the planner's *hints*, replay resolves the
artifact's *ladder*. Two code paths where one might do. The alternative,
replaying through the hint resolver, would let a replay match by "first of
several", which is precisely what must never happen when the action mutates
state.

**Stack:** Python 3.12, Pydantic v2 for the schemas, async Playwright, Anthropic
SDK in discovery only, ruff + mypy + pytest (661 tests). The target app is Flask
and Jinja2 — an intentionally period-appropriate choice for a mock legacy system.

## 2. Artifact schema

A `Capability` is typed JSON, not code. It carries `capability_id` + semver
`version`, `provenance` (which model discovered it, when, from which trace),
`surface` requirements, `safety` constraints, typed `inputs` and `outputs`,
ordered `steps`, `checkpoints`, `known_outcomes`, and a `recovery` policy.

**Data, not code.** Skyvern compiles agent runs into generated Python;
Playwright's test-agents emit TypeScript specs. Both are hard to diff, redact,
version-pin or overlay. A JSON document can be reviewed by a human, checked into
git, adjusted per institution without touching logic, and refused by a schema
when it is malformed. The whole `workflow_script_service` + script-reviewer
apparatus Skyvern needs (~10k lines) exists because code is its artifact.

**Every target carries a ranked ladder, not one locator.** At the moment an
action succeeds, the loop describes the element, generates every plausible
locator, probes each against the live DOM, and keeps only those matching exactly
one element — ranked `testid 0.95 → role 0.90 → name 0.88 → label 0.85 →
placeholder 0.70 → text 0.60 → css 0.30`. `name` ranks third deliberately:
legacy servers read it on submit, so it is the identifier the application cannot
change casually. Every surveyed system stores a single identifier instead —
usually an absolute indexed XPath — and answers brittleness by calling the model
again.

**Each target also carries a structural fingerprint**: a position-independent
hash of tag, stable attributes and leading text. A ladder answers "did something
match"; only the fingerprint answers "is it the same thing". Two corrections
came from live runs: a submit button's `value` *is* its label, so excluding it
made every button in the app hash identically; and a `read` step's element text
*is* the value being read, so fingerprinting it reports drift on the one
difference that is not drift.

**Bindings are a closed grammar** — `{{input.name}}` and `{{env.NAME}}`, nothing
else, single-pass, no expression evaluation. A brace pair the grammar does not
claim is a compile-time refusal, not a value typed verbatim into a bank.

**The compiler refuses rather than emitting a doubtful artifact**:
`NO_SURVIVING_LOCATOR`, `UNBOUND_REQUIRED_INPUT`, `SECRET_LITERAL_IN_TRACE`,
`CHECKPOINT_ECHOES_OUTPUT`, `TRACE_INCOMPLETE`, `BINDING_RESIDUE`. The
checkpoint rule matters more than it looks: an assertion on a value the run
itself produced passes trivially and proves nothing. A live discovery run wrote
exactly that (`assert HOLD POSTED CONFIRMATION HX-856301`) and the compiler
scrubbed the code out.

## 3. Determinism & error handling

**Zero model calls in replay is enforced, not promised.** `tests/replay/` walks
the engine's entire import graph and separately poisons any module that could
reach a model. `RunResult.llm_calls` is carried in every result. This is where I
part company with the prior art: Stagehand self-heals by re-invoking the model on
a cache miss, Skyvern bakes `ai='proactive'` calls into "cached" runs, and
workflow-use's schema *mandates* a final model-driven extract step. All three
give up determinism exactly when it matters.

**On failure the engine stops.** It never silently re-plans. A locator that no
longer resolves, a checkpoint that fails, an element whose fingerprint does not
match — each produces a structured result naming the step, what was expected and
what was observed.

**Four outcomes, from module-level dispatch tables:**

| Outcome | Meaning | Behavior |
|---|---|---|
| `SUCCESS` | the application confirmed the change | done, with typed outputs |
| `BUSINESS_OUTCOME` | the world said no ("already under hold") | done — **not** a failure |
| `RECOVERABLE` | timeout, maintenance page, unexpected dialog | bounded retry / dismiss / restart |
| `HARD_FAILURE` | authorisation denied, app error, checkpoint miss | stop; escalate if attended |

Conflating the second with the fourth is, as the brief says, the common mistake.
Skyvern arrived at the same distinction independently (`terminated` ≠ `failed`,
and a terminated block counts as replay success) which I take as confirmation.

**Drift is measured, not merely survived.** Every step records which rung of its
ladder resolved it; a run scores `first_choice / steps_resolved`. A capability
still working but landing on rung two is telling you the application moved,
before anything breaks. None of the six systems I tore down does this — drift
surfaces only as failure.

**Waiting:** after acting, the engine polls for the *next* step's control to
appear. The next target's presence is the ground truth that the page settled,
which beats a fixed sleep or a network-idle guess.

## 4. Heterogeneity & multi-tenant

**Surfaces.** The artifact declares required `SurfaceFeature`s and the surface
declares what it provides; a mismatch is refused before the run starts rather
than failing halfway through a money-touching flow. The feature vocabulary
already names `coordinates`, `screenshot` and `a11y_tree` alongside `dom_query`,
so a screenshot-and-coordinates surface for a desktop app implements the same
six verbs and reuses the engine, kernel and compiler unchanged. What would need
work: `candidate_locators` is DOM-shaped, so a desktop surface needs its own
descriptor→candidate function. That is the seam, and it is one function wide.

I did not build that surface. The 2026 consensus — and Anthropic's own GA
browser tooling — is hybrid: structure first, vision only where the tree is
useless. My locator ladder sits on the structural side of that split by design.

**Tenants.** One capability plus a small per-institution **overlay**. Quarrybrook
and Fernhollow run the same product with different frame names, field names,
button labels and screen headers; the overlay renames those in about 30 lines and
nothing about the flow changes. Both replay green from one artifact.

All three catalogued flows — place a hold, member inquiry, sign-on smoke — were
discovered live, compiled and replayed; the committed evidence has a real trace
for each. The inquiry flow is the one that shows typed extraction properly,
returning the member's name, branch and two share balances.

Two decisions carry the weight:

- **Overlays are locator-matched, not step-id-matched.** An overlay says "the
  candidate identifying the search field by `name=sval` becomes `srchval`", not
  "step 3's first candidate". Edit the base capability so that candidate no
  longer exists and the overlay fails loudly instead of silently re-pointing
  whichever control now sits at that index.
- **Overlays may rename and re-point, may *narrow* safety, and may never change
  behavior.** Enforced at the write, not merely audited. In particular they
  cannot re-point a URL — that would let an overlay redirect a capability to a
  different host, which is what safety-narrowing exists to prevent. Hosts come
  from `{{env.BASE_URL}}` plus `--base-url`.

Overlays are pinned to an exact capability version: a re-recorded recipe is a
different recipe and its overlay must be re-reviewed, not inherited.

**Version drift** is what the drift score is for. A tenant whose score slips from
1.00 is telling you its build has moved before its automation fails.

## 5. Escalation & handoff

A formal control-ownership state machine, with a single token:

```
AUTOMATION_RUNNING ──escalate/pause──▶ PAUSED ──take_control──▶ HUMAN_CONTROL
        ▲                                                            │
        └──────────────── resume(decision) ──────────────────────────┘
                                          abort ──▶ ABORTED
```

Owner is `automation`, `human`, or `nobody`. The engine awaits the token before
every mutating action, so **a handoff is not a restart**: same page, same
cookies, same half-filled form. The operator drives that same `Surface`, so their
actions land in the same audit trail, under the same policy, as automated ones.

Detection is threefold: an escalatable error code, an ambiguous or missing
control, or the discovery stuck-detector (three identical turns at one URL).
An intervention request carries the capability, the step, the reason code, the
URL and a screenshot.

The console is a plain Flask page — deliberately minimal, per the scope note —
but the mechanism is real: it pauses a live replay, transfers control, records
what the human did, and resumes on the same session. One non-obvious detail it
forced: `SessionControl` waits on an `asyncio.Event`, so a web worker calling
`resume()` directly sets the flag without waking the sleeping run, which would
sit until its 900-second timeout. All console access is marshalled onto the
replay's event loop.

An operator pause is recorded distinctly from a fault escalation (`origin`), so a
report can say "a human looked at this" rather than "this run broke" — and
retry/skip are refused after a pause, because nothing failed and there is no step
to retry.

## 6. Safety

**Allowlist.** Scheme, host and action type are checked before anything is
touched. The capability's declared needs are *intersected* with the deployment
policy; disjoint sets refuse up front rather than failing mid-flow.

**Risky actions** are classified from action type and intent keywords. Policy can
block them outright or require explicit confirmation; steps can be named in
`confirm_steps`. A hold post is `risky` in the shipped artifact.

**Secrets never reach the model, the artifact, the logs or the evidence.**
Password and hidden field values are masked as `[opaque]` at the surface, before
anything else sees them. Redaction runs at the boundaries — logger, evidence
writer, serializer — never at call sites, so one forgotten call site cannot leak.
A credential arrives as `{{env.NAME}}` and is resolved inside the executor.
`make verify` greps the evidence tree for the password as its last check.

Three of these were found by live runs rather than by design, which is the honest
account: the surface masked hidden inputs but **not passwords**, so a typed
credential came back to the model in clear text; discovery typed a literal
`{{env.…}}` into a password field when the variable was unset, and the model
responded to the rejection by **inventing passwords and trying them**; and
loading `.env` inside `main()` made the test suite adopt a real key and start
calling the API. Now: a password field only ever receives a value that came from
a declared binding, and the machinery refuses rather than the prompt discouraging.

**Determinism is itself a security property.** Prompt injection is the
acknowledged unsolved problem for browser agents — malicious page text can talk a
model into new actions. A compiled artifact has no model to talk to. The
injection surface is one supervised discovery run, not every production
invocation.

**Ambiguity is refused for anything that mutates.** On a member holding two share
accounts, `link "Hold"` matches twice; taking the first would decide which
account gets frozen by document order. Reads may still explore freely — reading
the wrong one of two identical labels costs a wrong value, clicking it costs a
hold on the wrong account.

## 7. Cuts

**Deliberately not built:**

- **A desktop or vision surface.** The protocol and feature negotiation are
  designed for it and the engine is surface-agnostic, but only `dom` is
  implemented. Next: a screenshot+coordinates surface, and a
  descriptor→candidate function for it.
- **Screenshot pixel redaction.** Text is redacted everywhere; a screenshot of a
  screen showing a balance is not. Real work, and I would do it with an
  element-bounds mask driven by the same `redact_paths`.
- **`{{env.NAME}}` has no allowlist.** An artifact can name any environment
  variable. It should be constrained to a declared set.
- **One engine per run.** `policy`, `control` and the recorder's `run_id` are set
  at construction; a second `run()` on the same engine would mix evidence. Fine
  for a CLI, wrong for a server, and the fix is a per-run context object.
- **Assisted fallback, multi-run stability scoring, and an agent-facing tool
  catalogue** — all listed as stretch goals; I built cross-tenant reuse instead
  and left the rest. `verify_capability` is the beginning of the confidence
  story: a freshly compiled artifact is replayed once before it is trusted.
- **`discovery/` is excluded from mypy.** That exclusion hid a real protocol
  mismatch (`AnthropicPlanner.model: str` vs `Planner.model: str | None`) which
  is currently papered over with a documented cast.

**What I would do next, in order:** close the mypy exclusion and the protocol
mismatch; put an allowlist on `env` bindings; make
the per-run context object real; then the vision surface, because that is the
one that changes what the system can automate rather than how well it does it.

**A note on method.** Nearly every defect above was found by running the thing
against a live application, not by reading it. The password leak, the
double-submitted form (which would have posted a hold **twice**), the ambiguous
Hold link, the missing entry-navigate, the inert fingerprint, the credential
guessing — none surfaced in 659 passing tests. That is the argument for the
evidence directory being a deliverable rather than a formality.
