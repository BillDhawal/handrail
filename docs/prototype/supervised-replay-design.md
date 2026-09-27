# Supervised Replay — Design

**Date:** 2026-09-02
**Status:** Approved for planning
**Builds on:** [2026-08-27-handrail-design.md](2026-08-27-handrail-design.md)

---

## 1. Purpose

Today a replay is deterministic and model-free. That is the right default, and it is also
brittle: the moment the application drifts past what the capability's locator ladders and
checkpoints can absorb, the run ends as a hard failure and a human re-discovers the flow.

Supervised replay keeps the deterministic engine as the driver and adds a **bounded model
supervisor** that is consulted only when a deterministic check fails. The supervisor may
drive the browser for a short stretch to reach the next checkpoint ("bridge"), name a
declared outcome the engine did not detect, or give up. The engine verifies every claim
deterministically before trusting it, counts every model call against a budget, and records
the whole excursion as evidence.

The invariants that matter do not change:

- With no supervisor configured, or with `max_llm_calls = 0`, behaviour is byte-identical to
  the current engine and `llm_calls` is `0`.
- The `handrail.replay` package still cannot import a model client. The structural audit in
  `tests/replay/test_no_llm.py` continues to pass unchanged.
- A run never ends with a bare exception. Every path still produces a typed `RunResult`.

### Why not check "at the midpoint"

The idea that prompted this design was a binary-search style check: verify state at step
n/2, fall back to n/4 on failure, with the model doing the checking. Two properties of UI
automation make that the wrong shape. First, there is no random access: reaching step *k*
means executing steps 0..*k*, so bisection buys no logarithmic saving. Second, the engine
already asserts after every step (checkpoints, outcome detectors, structural hash drift), so
the first failing step is known at step granularity for free. Model spend should scale with
breakage, not with step count. Hence: model on exception, never on schedule.

---

## 2. Scope

### In scope (this spec)

1. Schema additions: `Checkpoint.safe_restart`, `RecoveryPolicy.max_llm_calls`,
   `RunResult.bridges`, `StepReport.status = "bridged"`.
2. A `Supervisor` protocol in `handrail.replay` (types only) and the engine changes that
   consult it on eligible failures.
3. A `handrail.supervise` package holding the Anthropic-backed implementation, which reuses
   `DiscoveryLoop` and `AnthropicPlanner` to run a bridge.
4. Discovery loop support for starting from the current screen instead of the entry URL, and
   an extended `finish` tool for bridge runs.
5. Compiler inference of `safe_restart` and a warning when a capability enables supervision
   but has unmarked mutating steps.
6. CLI flag `--max-llm-calls` on `handrail replay`, and the report renderer showing bridges.
7. Tests for all of the above with the existing `NullSurface` and scripted planner.

### Delivered in two slices

- **Slice 1 — forward bridge.** Trigger, bridge to the nearest checkpoint ahead, outcome
  classification against declared `known_outcomes`, budget, evidence, CLI, report.
- **Slice 2 — rewind and proposals.** Bridge targets behind the failing step (limited to
  `safe_restart` checkpoints, never across an executed risky step), and `proposed_outcome`
  on give-up.

Slice 1 is independently shippable and proves the idea against the mock bank with an
injected drift.

### Explicit non-goals

- **Recompiling a repaired capability from a bridge trace.** The trace is written to disk in
  the same format as a discovery trace precisely so a later `compile --patch` can consume
  it. That command is a follow-up spec.
- **Scheduled or speculative model checks** while deterministic checks are passing.
- **Free-form model actions outside the discovery vocabulary.** A bridge runs through the
  same `act` / `assert_state` / `finish` tools as discovery, under the same policy.
- **Automatic promotion of a proposed outcome** into the job catalogue or the capability.
  Proposals are evidence for a human.

---

## 3. Architecture

```
ReplayEngine (handrail.replay)                 handrail.supervise
──────────────────────────────                 ──────────────────
step loop
  └─ HandrailError, eligible code ──────────▶  AnthropicSupervisor.bridge(request)
       and budget remaining                        │
                                                   ├─ builds a bridge job (sub-goal, context)
                                                   ├─ DiscoveryLoop.run(params, navigate=False)
                                                   │     AnthropicPlanner with BRIDGE_TOOLS
                                                   └─ returns BridgeResult
  ◀──────────────────────────────────────────────── (decision, turns, llm_calls, trace path)
  ├─ reached → evaluate checkpoint deterministically → resume, or escalate
  ├─ outcome → raise the declared known outcome
  └─ give_up → existing escalation / failure path
```

The dependency runs `supervise → discovery → replay`, never the reverse. `handrail.replay`
gains one module, `supervisor.py`, containing only a `Protocol` and dataclasses. The
concrete supervisor is injected by the CLI exactly as the discovery planner is today:
imported inside the command function so `handrail replay` without `--max-llm-calls` never
loads it.

---

## 4. Schema changes

All additions carry defaults, so every existing capability and result file remains valid.
`schema_version` is not bumped.

### `Checkpoint`

```python
safe_restart: bool = False
```

True means: re-entering the flow at this checkpoint is idempotent, because no step that
mutates application state has executed between the entry URL and this checkpoint. The
compiler infers it (section 8); an author may set it by hand to override in either
direction.

### `RecoveryPolicy`

```python
max_llm_calls: int = 0
```

The number of model calls a single replay may spend across all bridges. Zero, the default,
disables supervision even when a supervisor is injected. The CLI may override it.

### `StepReport`

`status` gains the literal `"bridged"`. A bridged step is one the engine could not execute
but whose target checkpoint the supervisor reached and the engine verified.

### `RunResult`

```python
bridges: list[BridgeReport] = Field(default_factory=list)
```

with

```python
class BridgeReport(BaseModel):
    from_step: str                # the step that failed
    trigger_code: ErrorCode       # why
    target_checkpoint: str | None # what the engine asked for
    decision: Literal["reached", "outcome", "give_up"]
    reached_checkpoint: str | None
    verified: bool                # the engine re-evaluated the checkpoint and it held
    outcome_id: str | None
    turns: int
    llm_calls: int
    trace: str | None             # evidence-relative path to bridge_<n>.trace.json
    proposed_outcome: ProposedOutcome | None = None   # slice 2
```

`RunResult.llm_calls` becomes the sum over `bridges`. Its comment changes from "invariant of
this path" to "zero unless a supervisor was consulted"; the test that pins it to zero on
unsupervised runs stays.

---

## 5. The trigger

The supervisor is consulted from one helper, `_bridge_or_raise`, called at the three places
inside `_execute_step` where a deterministic check can fail: a precondition checkpoint, the
action itself (after retries are exhausted), and a postcondition checkpoint. The helper
either raises a control-flow exception (`_ResumeAt`, `_TerminalOutcome` or
`_RestartCapability`) that the step loop in `run` already knows how to handle, or returns
so the original failure proceeds exactly as it does today.

**The model goes before the human.** `_bridge_or_raise` runs before `_maybe_escalate`.
This is not a preference; it is forced by the control state machine. An unattended
escalation transitions `SessionControl` to `PAUSED` and returns immediately, after which
`_await_control` would block every later step. Bridging first means the human is only
asked once the model has failed, and the control state stays `AUTOMATION_RUNNING` for the
bridge and the resumed steps. In an attended run the same order holds: the operator sees
an escalation only for a failure the supervisor could not fix.

`_TerminalOutcome`, `_SkipStep`, `_RetryStep`, `_RestartCapability` and `OperatorAbort` are
not bridgeable.

A failure is **eligible** when all of the following hold:

- a supervisor is configured and `remaining_llm_calls > 0`;
- the error code is one of `CHECKPOINT_MISMATCH`, `MISSING_CONTROL`, `AMBIGUOUS_CONTROL`,
  `TARGET_MISMATCH`, `UNEXPECTED_DIALOG`, `SLOW_LOAD`;
- the failing step has not already been bridged in this run (one bridge per step, so a
  flapping step cannot burn the budget).

Codes deliberately **not** eligible: `PERMISSION_DENIED`, `INVALID_INPUT`,
`VALIDATION_ERROR`, `APPLICATION_ERROR`, `POLICY_VIOLATION`, `SURFACE_INCOMPATIBLE`,
`ABORTED_BY_OPERATOR`, `SESSION_EXPIRED`. These are answers or refusals, not drift; a model
cannot make a teller into a supervisor and must not try.

When a failure is not eligible, the branch behaves exactly as it does today.

---

## 6. The bridge request

The engine builds a `BridgeRequest`:

| field | contents |
|---|---|
| `capability_ref`, `title`, `description` | orientation for the prompt |
| `failed_step` | id, intent, action type, the bound (redacted) target hint |
| `error` | code and message |
| `target` | the checkpoint the engine wants reached (id, description, condition in words) |
| `alternatives` | slice 2: `safe_restart` checkpoints behind the failing step that are legal to re-enter |
| `known_outcomes` | id, description and category of every declared outcome, so the planner can name one |
| `params` | the run's bound parameters, secrets as `{{input.NAME}}` tokens exactly as discovery sees them |
| `turn_budget` | `min(policy.max_steps, remaining_llm_calls)` |

**Choosing the target.** The engine walks forward from the failing step: the failing step's
own postconditions first, then each later step's preconditions then postconditions, and
takes the first checkpoint found. That is the nearest state the deterministic engine can
verify. If no checkpoint exists ahead, the failure is not bridgeable: the engine cannot
verify "the model finished the flow" without one, and a strict `_collect_outputs` on an
unverified screen would report the wrong thing. This is logged as
`bridge.skipped reason=no_checkpoint_ahead` and the failure proceeds normally.

**Resume index.** Each checkpoint id is mapped to the index of the step that lists it: the
step itself if it is a precondition, the following step if it is a postcondition. Reaching
a checkpoint resumes there.

**Rewind safety (slice 2).** A checkpoint behind the failing step is offered as an alternative
only if `safe_restart` is true **and** no step with `risk == "risky"` has executed since its
resume index. The engine computes this; the planner never sees an illegal target. If the
planner nevertheless names one, the engine treats it as `give_up`.

---

## 7. The bridge run

`AnthropicSupervisor.bridge` translates the request into a discovery job:

- `goal`: a generated instruction of the form *"The automated replay of `<title>` failed
  at `<intent>` with `<error>`. Get the application to the state `<target description>`,
  using the supplied inputs, and finish with `reached` naming it. If the screen is one of
  the DECLARED OUTCOMES, finish with `outcome` naming it instead. If you cannot, finish with
  `give_up`."*
- `inputs`: the capability's `InputSpec`s, rendered as discovery already renders them so
  secrets are typed as `{{input.NAME}}` tokens and never as values.
- `outputs`: empty. A bridge does not read outputs; the resumed replay does.
- `known_outcomes`: rendered into the prompt as a DECLARED OUTCOMES block (a small addition to
  `build_prompt`, ignored when the key is absent).

It then runs `DiscoveryLoop(surface, planner, policy, recorder, job).run(params,
navigate=False)`. Two changes to the loop support this:

1. `navigate: bool = True` on `run`. When false, the loop neither policy-checks nor visits
   `job["entry_url"]`; it observes the screen it is on.
2. The planner is constructed with `BRIDGE_TOOLS`, which is `TOOLS` with a wider `finish`:

   ```json
   {"status": {"enum": ["reached", "outcome", "give_up"]},
    "summary": {"type": "string"},
    "checkpoint_id": {"type": "string"},
    "outcome_id": {"type": "string"},
    "proposed_outcome": {"type": "object", ...}}   // slice 2
   ```

   The loop records the finish call's arguments on the trace as `finish_args` and sets
   `trace.status` to `reached` or `outcome` when the planner said so (any other finish
   status stays `gave_up`, so the compiler's `success`/`gave_up` contract for ordinary
   discovery is untouched). The supervisor reads both back. `trace.status` for a bridge
   is therefore one of `reached`, `outcome`, `gave_up`, `stuck`, or the max-steps
   fallthrough; the last three all map to `give_up`. The loop also takes a `trace_name`
   (default `trace.json`) so a bridge writes `bridge_<n>.trace.json`.

The bridge shares the engine's `RunRecorder`, so its per-turn screenshots and log lines land
in the same evidence directory under the same redactor. The trace is written as
`bridge_<n>.trace.json` rather than `trace.json` so a run with two bridges keeps both.

**Policy during a bridge.** The loop receives the engine's already-intersected policy, so
the capability's `safety` block binds the model exactly as it binds the engine. The loop's
existing refusal to mutate through an ambiguous hint still applies. `check_risky` is called
with `confirmed=True` inside `DiscoveryLoop._act` today because discovery is interactive by
definition; for a bridge the supervisor constructs the loop with `confirm_risky` taken from
the engine, so an unconfirmed risky action inside a bridge raises `PolicyViolation`, which
the loop records as a failed turn and the planner sees. This is a small parameter addition
to `DiscoveryLoop.__init__`.

**Model calls.** `AnthropicPlanner` gains a `calls` counter incremented per `decide`. The
supervisor reports it in `BridgeResult.llm_calls`; the engine subtracts it from the remaining
budget.

---

## 8. What the engine does with the result

```
reached(cp):
    if cp is not the target and not in alternatives → treat as give_up
    passed = surface.evaluate(bind(cp.condition), timeout_ms=cp.timeout_ms)
    log bridge.verified passed=...
    if not passed → treat as give_up (verified=False in the report)
    StepReport(from_step, status="bridged", note=f"reached {cp}")
    index = resume_index(cp); continue the loop

outcome(id):
    if id not in capability.known_outcomes → treat as give_up
    run the same dispatch as _raise_if_known_outcome for that one outcome:
    capture values, escalate/restart/terminal exactly as a detector firing

give_up:
    fall through to the existing failure handling for the original HandrailError,
    including _maybe_escalate; the BridgeReport is still recorded
```

Every branch appends a `BridgeReport` and decrements the budget. When the budget reaches
zero the supervisor is not consulted again in this run.

### Compiler inference of `safe_restart`

`compile_trace` marks a checkpoint `safe_restart=True` when no step preceding its resume
index carries `risk="risky"`. `MUTATING_ACTIONS` is deliberately not the signal: typing a
member number into a search box is a `type` action that changes nothing in the bank, and
using it would mark every checkpoint after sign-on unsafe. The `risk` field is what the
policy layer already uses to decide what needs confirmation, so it is the one place an
author states "this changes the world", and `safe_restart` follows from it. A hand-set
value in an existing capability file is never overwritten.

**A consequence found during implementation, recorded rather than smoothed over.**
`Policy.classify_risk` raises a mutating step to risky when its recorded intent contains
one of a blunt keyword list, and that list includes `submit`, `hold` and `post`. In the
compiled place-hold capability the sign-on step's own intent reads "submit the sign-on
form", so sign-on is already risky, and because the compiler attaches checkpoints only as
postconditions, every checkpoint in that flow resumes after it. The capability therefore
ends up with no safe re-entry point at all and slice 2's rewind can never fire on it. That
is the conservative failure direction and it stands: a checkpoint wrongly marked unsafe
costs one lost rewind, while one wrongly marked safe costs a re-posted hold. Making the
rewind useful on that flow means tightening the keyword heuristic, which changes safety
behaviour repo-wide and is deliberately out of scope here.

Because that inference is only as good as the risk marking, the **engine** appends a
warning to the run's `warnings` when the effective `max_llm_calls > 0` and any `click`,
`select` or `press` step is not marked `risk="risky"` and the policy's `classify_risk`
does not raise it either. The warning names the steps; it does not refuse. It lives in
the engine rather than the compiler because the compiler never sets `max_llm_calls`
(the default is zero and the budget is usually supplied on the command line), so a
compile-time check would never fire.

---

## 9. CLI and report

`handrail replay` gains:

```
--max-llm-calls N    let a model supervisor bridge drift, spending at most N calls
                     (default: the capability's recovery.max_llm_calls, usually 0)
```

When the effective budget is greater than zero the command requires `ANTHROPIC_API_KEY`,
refusing with the same wording `discover` uses. It constructs `AnthropicSupervisor` inside
the command function and passes it to `ReplayEngine`. `serve-console` accepts the same
flag; the console's `ConsoleSession` passes the supervisor through.

`handrail report run` renders a **Bridges** section after Steps when `result.bridges` is
non-empty: one row per bridge with the trigger, target, decision, verified flag, turns,
calls, and a link to the bridge trace. The run summary line already prints `llm_calls`.

`scripts/verify.sh` gains one check: replay `place-hold-quarrybrook` against Fernhollow
without the overlay and with `--max-llm-calls 12`, expecting `SUCCESS` with `llm_calls > 0`
and at least one bridge with `verified=true`. This is the injected-drift demonstration and
is skipped, and reported as skipped, when no key is present.

---

## 10. Error handling

| situation | behaviour |
|---|---|
| supervisor raises (network, SDK) | caught in `_try_bridge`; logged as `bridge.error`; treated as `give_up`; original failure proceeds |
| bridge trace cannot be written | logged; `BridgeReport.trace = None`; result still returned |
| planner names an unknown checkpoint or outcome | `give_up` |
| checkpoint claimed reached but evaluation false | `give_up`, `verified=False` |
| budget exhausted mid-bridge | the loop's `max_steps` is set from the budget, so the bridge ends as `max_steps` → `give_up` |
| operator pauses during a bridge | not supported in slice 1; `SessionControl` is not consulted inside `DiscoveryLoop`. Documented as a limitation. |

---

## 11. Testing

All engine tests run on `NullSurface` with a scripted supervisor and never touch a model.

**Engine (`tests/replay/test_supervised.py`)**

- no supervisor → identical `RunResult` to today, `llm_calls == 0`, `bridges == []`
- supervisor present, `max_llm_calls == 0` → supervisor never called
- ineligible code (`PERMISSION_DENIED`) → supervisor never called
- `reached` with the condition true → step reported `bridged`, replay resumes at the
  checkpoint's index, final `SUCCESS`, `llm_calls` equals the bridge's count
- `reached` with the condition false → `verified=False`, original failure returned
- `reached` naming a checkpoint that was not offered → `give_up`
- `outcome` naming a declared business outcome → `BUSINESS_OUTCOME` result with that id
- `outcome` naming an unknown id → `give_up`
- budget of 3 with a bridge costing 3 → a second eligible failure is not bridged
- one bridge per step: same step failing again after a bridge is not bridged
- supervisor raising → `bridge.error` logged, original failure returned
- slice 2: alternative behind an executed risky step is not offered; planner naming it → `give_up`

**Supervise (`tests/supervise/`)**

- `AnthropicSupervisor.bridge` with the scripted planner: builds the job, runs the loop
  without navigating, maps each `finish` shape to the right `BridgeResult`, counts calls,
  writes `bridge_1.trace.json`
- prompt contains the DECLARED OUTCOMES block and secret inputs as tokens

**Discovery**

- `run(navigate=False)` does not call `surface.navigate`
- `BRIDGE_TOOLS.finish` accepts the three statuses; `TOOLS.finish` unchanged

**Compiler**

- `safe_restart` inferred true for `at_desk`, false for a checkpoint after a risky click
- hand-set value preserved
- warning emitted for an unmarked mutating step when `max_llm_calls > 0`

**Schema and audit**

- existing capability and result fixtures still validate
- `test_no_llm.py` unchanged and passing; `handrail.supervise` is not in its
  `PRODUCTION_PACKAGES` list and is asserted to be the only package outside `discovery`
  that imports `discovery`

**CLI**

- `--max-llm-calls 5` without a key refuses with exit 5
- default budget 0 does not import `handrail.supervise` (assert via `sys.modules`)

---

## 12. Files touched

| file | change |
|---|---|
| `src/handrail/schema/capability.py` | `Checkpoint.safe_restart`, `RecoveryPolicy.max_llm_calls` |
| `src/handrail/schema/results.py` | `BridgeReport`, `ProposedOutcome`, `RunResult.bridges`, `StepReport.status` literal |
| `src/handrail/replay/supervisor.py` | new: `Supervisor` protocol, `BridgeRequest`, `BridgeResult` |
| `src/handrail/replay/engine.py` | `supervisor` parameter, `_try_bridge`, target/resume-index helpers, budget |
| `src/handrail/discovery/tools.py` | `BRIDGE_FINISH_TOOL`, `BRIDGE_TOOLS` |
| `src/handrail/discovery/loop.py` | `run(navigate=)`, `confirm_risky` |
| `src/handrail/discovery/planner.py` | `tools` parameter, `calls` counter, DECLARED OUTCOMES block in `build_prompt` |
| `src/handrail/supervise/__init__.py`, `bridge.py` | new: `AnthropicSupervisor` |
| `src/handrail/compile/compiler.py` | `safe_restart` inference, unmarked-mutation warning |
| `src/handrail/cli.py` | `--max-llm-calls`, supervisor construction |
| `src/handrail/console/session.py` | pass supervisor through |
| `src/handrail/report/trace_report.py` | Bridges section |
| `scripts/verify.sh` | injected-drift check |
| `docs/ARCHITECTURE.md`, `README.md`, `TESTING.md` | one section each |
| `tests/...` | as in section 11 |
