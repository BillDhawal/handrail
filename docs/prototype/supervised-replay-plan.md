# Supervised Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a deterministic replay check fails, let a budgeted model supervisor drive the browser to the next checkpoint, name a declared outcome, or give up, with every claim verified by the engine and recorded as evidence.

**Architecture:** `handrail.replay` gains a `Supervisor` protocol (types only) and the engine consults it from `_execute_step` on eligible failures, resuming via a `_ResumeAt` control-flow exception. A new `handrail.supervise` package implements the supervisor on top of the existing `DiscoveryLoop` and `AnthropicPlanner`, run from the current screen with a bridge sub-goal and an extended `finish` tool. The compiler infers which checkpoints are safe to re-enter; the CLI exposes a call budget.

**Tech Stack:** Python 3.12, pydantic v2, pytest + pytest-asyncio (async tests are plain `async def`, no marker needed), uv, ruff, mypy. Run everything with `uv run ...`.

**Spec:** `docs/superpowers/specs/2026-09-02-supervised-replay-design.md`

## Global Constraints

- `handrail.replay`, `handrail.schema`, `handrail.surface`, `handrail.kernel` must never import `anthropic`, `openai`, `httpx`, `requests`, or anything under `handrail.discovery`. `tests/replay/test_no_llm.py` enforces this and must keep passing unchanged.
- Every schema addition carries a default. `SCHEMA_VERSION` is not bumped. Existing capability JSON under `artifacts/` and result JSON under `evidence/` must still validate.
- With no supervisor, or with `max_llm_calls == 0`, `RunResult` must be identical to today and `llm_calls == 0`.
- Bridge-eligible codes are exactly: `CHECKPOINT_MISMATCH`, `MISSING_CONTROL`, `AMBIGUOUS_CONTROL`, `TARGET_MISMATCH`, `UNEXPECTED_DIALOG`, `SLOW_LOAD`. Nothing else is ever bridged.
- The model is consulted before a human is (see spec §5). A bridge is attempted at most once per step per run.
- `make test` (ruff + mypy + pytest) must be green at every commit. Run `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src` before each commit.
- Commit messages: conventional commits, end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Never commit `.env`, evidence run directories, or anything under `evidence/runs/`.
- Persisted prose (docstrings, comments, docs, commit bodies) is normal English, matching the existing code's voice: say *why*, not *what*.

---

## File map

| file | responsibility |
|---|---|
| `src/handrail/schema/capability.py` | `Checkpoint.safe_restart`, `RecoveryPolicy.max_llm_calls`, `checkpoint_resume_index()` |
| `src/handrail/schema/results.py` | `ProposedOutcome`, `BridgeReport`, `RunResult.bridges`, `StepReport.status` literal |
| `src/handrail/replay/supervisor.py` | **new** — `Supervisor` protocol, `BridgeTarget`, `OutcomeSummary`, `BridgeRequest`, `BridgeResult`, `describe_condition()`, `BRIDGEABLE` |
| `src/handrail/replay/engine.py` | supervisor wiring, `_bridge_or_raise`, `_bridge_target`, `_dispatch_outcome`, `_ResumeAt`, budget, warnings |
| `src/handrail/discovery/tools.py` | `BRIDGE_FINISH_TOOL`, `BRIDGE_TOOLS` |
| `src/handrail/discovery/loop.py` | `run(navigate=)`, `confirm_risky`, `trace_name`, `finish_args`, bridge statuses |
| `src/handrail/discovery/planner.py` | `tools` / `system_prompt` parameters, `calls` counter, `BRIDGE_SYSTEM_PROMPT`, DECLARED OUTCOMES block |
| `src/handrail/supervise/__init__.py`, `bridge.py` | **new** — `AnthropicSupervisor`, `build_bridge_goal()`, `bridge_job()` |
| `src/handrail/compile/compiler.py` | `_mark_safe_restart()` |
| `src/handrail/cli.py` | `--max-llm-calls`, `_supervisor_for()` |
| `src/handrail/console/session.py` | pass `supervisor` and `max_llm_calls` through |
| `src/handrail/report/trace_report.py` | Bridges section |
| `scripts/verify.sh`, `README.md`, `docs/ARCHITECTURE.md`, `TESTING.md` | documentation and the live check |

---

### Task 1: Schema additions

**Files:**
- Modify: `src/handrail/schema/capability.py` (around `class Checkpoint` at line 314 and `class RecoveryPolicy` at line 372)
- Modify: `src/handrail/schema/results.py` (around `class StepReport` at line 52 and `class RunResult` at line 98)
- Modify: `src/handrail/schema/__init__.py`
- Test: `tests/schema/test_capability.py`, `tests/schema/test_results.py`

**Interfaces:**
- Produces: `Checkpoint.safe_restart: bool`, `RecoveryPolicy.max_llm_calls: int`, `checkpoint_resume_index(steps: list[Step], cp_id: str) -> int | None`, `ProposedOutcome`, `BridgeReport`, `RunResult.bridges: list[BridgeReport]`, `StepReport.status` accepting `"bridged"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/schema/test_capability.py`:

```python
from handrail.schema.capability import Checkpoint, RecoveryPolicy, Step, checkpoint_resume_index


def test_checkpoint_and_recovery_defaults_keep_old_files_valid():
    cp = Checkpoint(
        id="at_desk",
        description="d",
        condition={"kind": "url_matches", "value": ".*/desk$"},
    )
    assert cp.safe_restart is False
    assert RecoveryPolicy().max_llm_calls == 0


def _steps() -> list[Step]:
    return [
        Step.model_validate(
            {
                "id": "s1",
                "intent": "type",
                "action": {"type": "type", "text": "x"},
                "target": {"candidates": [{"strategy": "name", "value": "sval"}]},
                "postconditions": ["cp_a"],
            }
        ),
        Step.model_validate(
            {
                "id": "s2",
                "intent": "click",
                "action": {"type": "click"},
                "target": {"candidates": [{"strategy": "name", "value": "go"}]},
                "preconditions": ["cp_b"],
            }
        ),
    ]


def test_resume_index_is_the_step_after_a_postcondition_and_the_step_of_a_precondition():
    steps = _steps()
    assert checkpoint_resume_index(steps, "cp_a") == 1
    assert checkpoint_resume_index(steps, "cp_b") == 1
    assert checkpoint_resume_index(steps, "nope") is None
```

Append to `tests/schema/test_results.py`:

```python
from handrail.schema.results import BridgeReport, ProposedOutcome


def test_bridges_default_empty_and_a_bridged_step_status_is_accepted():
    assert _result().bridges == []
    assert StepReport(step_id="s1", status="bridged").status == "bridged"


def test_a_bridge_report_round_trips():
    report = BridgeReport(
        from_step="s2",
        trigger_code=ErrorCode.CHECKPOINT_MISMATCH,
        target_checkpoint="cp_open",
        decision="reached",
        reached_checkpoint="cp_open",
        verified=True,
        turns=3,
        llm_calls=4,
        trace="bridge_1.trace.json",
    )
    result = _result(bridges=[report], llm_calls=4)
    again = RunResult.model_validate_json(result.model_dump_json())
    assert again.bridges[0].verified is True
    assert again.llm_calls == 4


def test_a_proposed_outcome_carries_the_four_fields_a_reviewer_needs():
    proposed = ProposedOutcome(
        category=OutcomeCategory.BUSINESS_OUTCOME,
        code=ErrorCode.RECORD_NOT_FOUND,
        screen_text="NO MEMBER RECORD MATCHES THAT VALUE",
        description="the search matched nobody",
    )
    assert proposed.screen_text.startswith("NO MEMBER")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/schema -q`
Expected: FAIL with `ImportError` on `checkpoint_resume_index`, `BridgeReport`, `ProposedOutcome`.

- [ ] **Step 3: Implement the schema changes**

In `src/handrail/schema/capability.py`, change `Checkpoint`:

```python
class Checkpoint(Base):
    id: str
    description: str
    condition: Condition
    timeout_ms: int = 8000
    on_fail_code: ErrorCode = ErrorCode.CHECKPOINT_MISMATCH
    #: True when re-entering the flow here is idempotent: no step marked risky has
    #: run between the entry URL and this checkpoint. The compiler infers it; an
    #: author may override it in either direction. A supervisor may only steer a
    #: replay back to a checkpoint that says so.
    safe_restart: bool = False
```

Change `RecoveryPolicy` (add after `on_hash_mismatch`):

```python
    #: Model calls one replay may spend on bridging drift. Zero, the default, keeps
    #: the run model-free even when a supervisor is wired in. The CLI may override.
    max_llm_calls: int = 0
```

Add a module-level function after the `Step` class:

```python
def checkpoint_resume_index(steps: list[Step], cp_id: str) -> int | None:
    """Where replay picks up once ``cp_id`` holds.

    A precondition belongs to the step that declares it, so the run resumes at
    that step. A postcondition describes the screen the step produced, so the run
    resumes at the following step - or past the end when it was the last one.
    Both the engine and the compiler need the same answer, so it lives here.
    """
    for index, step in enumerate(steps):
        if cp_id in step.preconditions:
            return index
        if cp_id in step.postconditions:
            return index + 1
    return None
```

In `src/handrail/schema/results.py`, change `StepReport.status`:

```python
    status: Literal["ok", "skipped", "failed", "recovered", "bridged"]
```

Add before `class RunResult`:

```python
class ProposedOutcome(BaseModel):
    """A screen the supervisor met that no declared outcome names.

    Evidence for a human, never a decision: the run still ends on the original
    failure. Promoting this into the job catalogue or the capability is a review
    step, not something a replay does to itself.
    """

    model_config = ConfigDict(extra="forbid")

    category: OutcomeCategory
    code: ErrorCode
    screen_text: str
    description: str


class BridgeReport(BaseModel):
    """One consultation of the supervisor, whatever it decided."""

    model_config = ConfigDict(extra="forbid")

    from_step: str
    trigger_code: ErrorCode
    target_checkpoint: str | None = None
    decision: Literal["reached", "outcome", "give_up"]
    reached_checkpoint: str | None = None
    #: The engine re-evaluated the claimed checkpoint (or found the named
    #: outcome) and it held. A bridge the model reports as reached but the
    #: engine could not verify is recorded here with verified=False and treated
    #: as a give-up.
    verified: bool = False
    outcome_id: str | None = None
    turns: int = 0
    llm_calls: int = 0
    #: Evidence-relative path of the bridge trace, e.g. ``bridge_1.trace.json``.
    trace: str | None = None
    proposed_outcome: ProposedOutcome | None = None
```

In `RunResult`, replace the `llm_calls` lines with:

```python
    #: Zero unless a supervisor was consulted. Unsupervised replay keeps this at
    #: zero by construction, and tests/replay/test_no_llm.py asserts it.
    llm_calls: int = 0
    bridges: list[BridgeReport] = Field(default_factory=list)
```

In `src/handrail/schema/__init__.py`, add `checkpoint_resume_index` to the `.capability` import list (keep alphabetical order among functions: after `WaitAction,` add a line `checkpoint_resume_index,`).

- [ ] **Step 4: Run the tests and the full suite**

Run: `uv run pytest tests/schema tests/replay tests/compile tests/report -q`
Expected: all PASS (existing goldens unaffected because new fields default).

- [ ] **Step 5: Lint, type-check, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src
git add src/handrail/schema tests/schema
git commit -m "feat(schema): safe_restart, max_llm_calls and BridgeReport

Every field defaults, so existing capabilities and results stay valid.
checkpoint_resume_index lives in the schema because the engine and the
compiler must agree on where a checkpoint resumes.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: The Supervisor protocol (types only, inside `handrail.replay`)

**Files:**
- Create: `src/handrail/replay/supervisor.py`
- Modify: `tests/replay/test_no_llm.py` (add one test)
- Test: `tests/replay/test_supervisor_types.py`

**Interfaces:**
- Produces:

```python
BRIDGEABLE: frozenset[ErrorCode]
@dataclass(frozen=True) class BridgeTarget: checkpoint_id: str; description: str; condition: str; resume_index: int
@dataclass(frozen=True) class OutcomeSummary: id: str; category: str; description: str
@dataclass(frozen=True) class BridgeRequest: capability_ref, title, description, failed_step_id, failed_intent, failed_action, error_code, error_message, target: BridgeTarget, alternatives: tuple[BridgeTarget, ...], known_outcomes: tuple[OutcomeSummary, ...], inputs: tuple[dict[str, Any], ...], params: dict[str, Any], turn_budget: int, sequence: int
@dataclass(frozen=True) class BridgeResult: decision: Literal["reached","outcome","give_up"]; checkpoint_id: str | None = None; outcome_id: str | None = None; summary: str = ""; turns: int = 0; llm_calls: int = 0; trace: str | None = None; proposed_outcome: ProposedOutcome | None = None
class Supervisor(Protocol): name: str; async def bridge(self, surface: Surface, policy: Policy, recorder: RunRecorder, request: BridgeRequest) -> BridgeResult
def describe_condition(condition: Condition) -> str
```

- [ ] **Step 1: Write the failing tests**

Create `tests/replay/test_supervisor_types.py`:

```python
"""The supervisor seam is a protocol and some dataclasses: nothing here may reach a model."""

from handrail.replay.supervisor import (
    BRIDGEABLE,
    BridgeRequest,
    BridgeResult,
    BridgeTarget,
    OutcomeSummary,
    describe_condition,
)
from handrail.schema import Condition, TargetSpec
from handrail.schema.errors import ErrorCode


def test_bridgeable_is_exactly_the_drift_shaped_codes():
    assert BRIDGEABLE == frozenset(
        {
            ErrorCode.CHECKPOINT_MISMATCH,
            ErrorCode.MISSING_CONTROL,
            ErrorCode.AMBIGUOUS_CONTROL,
            ErrorCode.TARGET_MISMATCH,
            ErrorCode.UNEXPECTED_DIALOG,
            ErrorCode.SLOW_LOAD,
        }
    )
    assert ErrorCode.PERMISSION_DENIED not in BRIDGEABLE
    assert ErrorCode.INVALID_INPUT not in BRIDGEABLE


def test_describe_condition_speaks_in_words_and_keeps_bindings_as_tokens():
    text = describe_condition(
        Condition(kind="text_present", value="{{input.member_number}}", frame_path=["work"])
    )
    assert text == 'the text "{{input.member_number}}" is visible in frame work'
    assert describe_condition(Condition(kind="url_matches", value=".*/desk$")) == (
        "the URL matches the pattern .*/desk$"
    )
    visible = describe_condition(
        Condition(
            kind="element_visible",
            target=TargetSpec(
                description="the Hold link",
                candidates=[{"strategy": "role", "role": "link", "name_equals": "Hold"}],
            ),
        )
    )
    assert visible == "the control 'the Hold link' is visible"


def test_a_request_and_result_are_plain_frozen_data():
    target = BridgeTarget("cp_open", "record is open", 'the text "MEMBER RECORD" is visible', 2)
    request = BridgeRequest(
        capability_ref="x@1.0.0",
        title="t",
        description="d",
        failed_step_id="s2",
        failed_intent="read the balance",
        failed_action="read",
        error_code="CHECKPOINT_MISMATCH",
        error_message="checkpoint cp_open failed",
        target=target,
        alternatives=(),
        known_outcomes=(OutcomeSummary("no_member", "BUSINESS_OUTCOME", "nobody matched"),),
        inputs=({"name": "member_number", "type": "string"},),
        params={"member_number": "400118"},
        turn_budget=6,
        sequence=1,
    )
    assert request.target.resume_index == 2
    assert BridgeResult(decision="give_up").llm_calls == 0
```

Append to `tests/replay/test_no_llm.py`:

```python
def test_only_the_supervise_package_may_bridge_replay_to_discovery():
    """`handrail.supervise` is the one package outside discovery allowed to import it."""
    importers: set[str] = set()
    for path in SRC.rglob("*.py"):
        package = path.relative_to(SRC).parts[0]
        if package in ("discovery", "supervise") or path.name == "cli.py":
            continue
        for name in _imports(path):
            if "discovery" in name:
                importers.add(str(path.relative_to(SRC)))
    assert importers == set()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/replay/test_supervisor_types.py tests/replay/test_no_llm.py -q`
Expected: `test_supervisor_types` FAIL with `ModuleNotFoundError: handrail.replay.supervisor`. The new no-LLM test PASSES already (no `supervise` package yet); that is fine.

- [ ] **Step 3: Create the module**

Create `src/handrail/replay/supervisor.py`:

```python
"""The seam between the deterministic engine and a model that may help it.

Everything here is data and a protocol. The engine builds a ``BridgeRequest``
when a deterministic check fails, hands it to whatever ``Supervisor`` was
injected, and gets a ``BridgeResult`` back describing what the supervisor
claims. The engine then verifies the claim itself - a checkpoint is re-evaluated,
an outcome id is looked up - before acting on it.

No model client is imported here or anywhere under ``handrail.replay``; the
concrete supervisor lives in ``handrail.supervise`` and is injected by the CLI.
``tests/replay/test_no_llm.py`` keeps it that way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from ..kernel.evidence import RunRecorder
from ..kernel.policy import Policy
from ..schema import Condition
from ..schema.errors import ErrorCode
from ..schema.results import ProposedOutcome
from ..surface.base import Surface

#: Failures a supervisor may be asked about. Each one means "the screen is not
#: what the capability recorded", which a model can sometimes get past. Codes
#: that mean "the application said no" or "the caller was wrong" are absent on
#: purpose: a model cannot make a teller into a supervisor and must not try.
BRIDGEABLE: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.CHECKPOINT_MISMATCH,
        ErrorCode.MISSING_CONTROL,
        ErrorCode.AMBIGUOUS_CONTROL,
        ErrorCode.TARGET_MISMATCH,
        ErrorCode.UNEXPECTED_DIALOG,
        ErrorCode.SLOW_LOAD,
    }
)


@dataclass(frozen=True)
class BridgeTarget:
    """A checkpoint the supervisor may steer towards."""

    checkpoint_id: str
    description: str
    #: The condition in words, for the prompt. Bindings stay as ``{{...}}`` tokens.
    condition: str
    #: Where replay resumes once the checkpoint holds (see checkpoint_resume_index).
    resume_index: int


@dataclass(frozen=True)
class OutcomeSummary:
    id: str
    category: str
    description: str


@dataclass(frozen=True)
class BridgeRequest:
    capability_ref: str
    title: str
    description: str
    failed_step_id: str
    failed_intent: str
    failed_action: str
    error_code: str
    error_message: str
    target: BridgeTarget
    #: Safe checkpoints behind the failure the supervisor may fall back to.
    alternatives: tuple[BridgeTarget, ...]
    known_outcomes: tuple[OutcomeSummary, ...]
    #: The capability's InputSpecs, dumped, so secrets are rendered as tokens.
    inputs: tuple[dict[str, Any], ...]
    #: The caller's raw parameters, with ``{{env.NAME}}`` tokens unresolved.
    params: dict[str, Any]
    turn_budget: int
    #: 1 for the first bridge of a run; names the trace file.
    sequence: int


@dataclass(frozen=True)
class BridgeResult:
    decision: Literal["reached", "outcome", "give_up"]
    checkpoint_id: str | None = None
    outcome_id: str | None = None
    summary: str = ""
    turns: int = 0
    llm_calls: int = 0
    trace: str | None = None
    proposed_outcome: ProposedOutcome | None = None


class Supervisor(Protocol):
    name: str

    async def bridge(
        self,
        surface: Surface,
        policy: Policy,
        recorder: RunRecorder,
        request: BridgeRequest,
    ) -> BridgeResult: ...


def describe_condition(condition: Condition) -> str:
    """Render a checkpoint condition as a sentence the planner can act on."""
    where = f" in frame {'/'.join(condition.frame_path)}" if condition.frame_path else ""
    if condition.kind == "text_present":
        return f'the text "{condition.value}" is visible{where}'
    if condition.kind == "text_absent":
        return f'the text "{condition.value}" is no longer visible{where}'
    if condition.kind == "url_matches":
        return f"the URL matches the pattern {condition.value}"
    target = condition.target
    label = (
        target.description
        if target is not None and target.description
        else (target.candidates[0].strategy if target is not None and target.candidates else "?")
    )
    if condition.kind == "element_visible":
        return f"the control '{label}' is visible{where}"
    if condition.kind == "element_absent":
        return f"the control '{label}' is gone{where}"
    return f"exactly {condition.count} of '{label}' are on screen{where}"
```

Check `Condition` has `frame_path`, `target`, `count`, `value` attributes (it does: see `schema/capability.py` around line 164). If `frame_path` is typed `list[str]` with a default, the `'/'.join` is fine.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/replay -q`
Expected: all PASS, including every test in `test_no_llm.py`.

- [ ] **Step 5: Lint, type-check, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src
git add src/handrail/replay/supervisor.py tests/replay/test_supervisor_types.py tests/replay/test_no_llm.py
git commit -m "feat(replay): the Supervisor seam, as data and a protocol

Types only, so the deterministic package stays model-free. The engine
will build a BridgeRequest on drift and verify whatever comes back.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Engine — forward bridge, outcome classification, budget

**Files:**
- Modify: `src/handrail/replay/engine.py` (imports at 1-58; `__init__` at 86-118; `run` at 121-310; `_execute_step` at 320-415; `_raise_if_known_outcome` at 624-679)
- Test: `tests/replay/test_supervised.py`

**Interfaces:**
- Consumes: Task 1 schema, Task 2 types.
- Produces: `ReplayEngine(..., supervisor: Supervisor | None = None, max_llm_calls: int | None = None)`; `RunResult.bridges` and `llm_calls` populated; `_dispatch_outcome(capability, outcome, step)` (used only internally).

- [ ] **Step 1: Write the failing tests**

Create `tests/replay/test_supervised.py`:

```python
"""Supervised replay: the engine consults a model only on drift, and verifies it.

Every test drives the real engine on a NullSurface with a scripted supervisor.
No test here, or anywhere under tests/replay, reaches a model.
"""

from __future__ import annotations

from handrail.replay.engine import ReplayEngine
from handrail.replay.supervisor import BridgeRequest, BridgeResult
from handrail.schema.errors import ErrorCode, OutcomeCategory
from handrail.surface.null_surface import NullSurface

from .test_engine import capability, engine, happy_surface


class ScriptedSupervisor:
    """Answers each bridge with the next scripted result; may mutate the surface."""

    name = "scripted"

    def __init__(self, results: list[BridgeResult], on_bridge=None) -> None:
        self.results = list(results)
        self.requests: list[BridgeRequest] = []
        self.on_bridge = on_bridge

    async def bridge(self, surface, policy, recorder, request):
        self.requests.append(request)
        if self.on_bridge:
            self.on_bridge(surface)
        if not self.results:
            raise AssertionError("bridge called more times than scripted")
        return self.results.pop(0)


def drifted_surface() -> NullSurface:
    """The checkpoint text is absent until the supervisor 'fixes' the page."""
    return NullSurface(
        matches={("name", "sval"): 1, ("css", "bal"): 1},
        reads={"bal": "$42,100.50"},
        text_sequence=["SOMETHING ELSE", "MEMBER RECORD"],
    )


def supervised(tmp_path, surface, sup, budget=10) -> ReplayEngine:
    return engine(surface, tmp_path, supervisor=sup, max_llm_calls=budget)


def reached(cp="cp_open", calls=3) -> BridgeResult:
    return BridgeResult(
        decision="reached", checkpoint_id=cp, turns=2, llm_calls=calls, trace="bridge_1.trace.json"
    )


async def test_without_a_supervisor_nothing_changes(tmp_path):
    result = await engine(happy_surface(), tmp_path).run(capability(), {"member_number": "400118"})
    assert result.ok and result.llm_calls == 0 and result.bridges == []


async def test_a_zero_budget_never_consults_the_supervisor(tmp_path):
    sup = ScriptedSupervisor([reached()])
    result = await supervised(tmp_path, drifted_surface(), sup, budget=0).run(
        capability(), {"member_number": "400118"}
    )
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert sup.requests == [] and result.llm_calls == 0


async def test_the_capability_budget_is_used_when_the_caller_passes_none(tmp_path):
    sup = ScriptedSupervisor([reached()], on_bridge=lambda s: s.advance())
    cap = capability(recovery={"max_llm_calls": 5})
    result = await engine(drifted_surface(), tmp_path, supervisor=sup).run(
        cap, {"member_number": "400118"}
    )
    assert result.ok and result.llm_calls == 3


async def test_an_ineligible_code_is_never_bridged(tmp_path):
    cap = capability(
        known_outcomes=[
            {
                "id": "not_authorized",
                "description": "operator is not authorized",
                "detector": {"kind": "text_present", "value": "AUTHORIZATION FAILURE"},
                "result": {"category": "HARD_FAILURE", "code": "PERMISSION_DENIED"},
            }
        ]
    )
    surface = NullSurface(matches={("name", "sval"): 1, ("css", "bal"): 1}, text="AUTHORIZATION FAILURE")
    sup = ScriptedSupervisor([reached()])
    result = await supervised(tmp_path, surface, sup).run(cap, {"member_number": "400118"})
    assert result.code is ErrorCode.PERMISSION_DENIED
    assert sup.requests == []


async def test_a_verified_bridge_resumes_replay_and_counts_its_calls(tmp_path):
    sup = ScriptedSupervisor([reached()], on_bridge=lambda s: s.advance())
    result = await supervised(tmp_path, drifted_surface(), sup).run(
        capability(), {"member_number": "400118"}
    )
    assert result.ok
    assert result.outputs == {"share_balance": "$42,100.50"}
    assert result.llm_calls == 3
    assert [b.decision for b in result.bridges] == ["reached"]
    assert result.bridges[0].verified is True
    assert result.bridges[0].from_step == "s2"
    assert result.bridges[0].target_checkpoint == "cp_open"
    assert [s.status for s in result.steps] == ["ok", "bridged"]


async def test_the_request_names_the_failure_the_target_and_the_declared_outcomes(tmp_path):
    cap = capability(
        known_outcomes=[
            {
                "id": "no_member",
                "description": "nobody matched",
                "detector": {"kind": "text_present", "value": "NO MEMBER RECORD MATCHES"},
                "result": {"category": "BUSINESS_OUTCOME", "code": "RECORD_NOT_FOUND"},
            }
        ]
    )
    sup = ScriptedSupervisor([reached()], on_bridge=lambda s: s.advance())
    await supervised(tmp_path, drifted_surface(), sup, budget=4).run(cap, {"member_number": "400118"})
    request = sup.requests[0]
    assert request.failed_step_id == "s2"
    assert request.error_code == "CHECKPOINT_MISMATCH"
    assert request.target.checkpoint_id == "cp_open"
    assert request.target.condition == 'the text "MEMBER RECORD" is visible'
    assert request.target.resume_index == 2
    assert [o.id for o in request.known_outcomes] == ["no_member"]
    assert request.params == {"member_number": "400118"}
    assert request.turn_budget == 4
    assert request.sequence == 1


async def test_a_claimed_checkpoint_that_does_not_hold_is_a_give_up(tmp_path):
    sup = ScriptedSupervisor([reached()])  # never advances the surface
    result = await supervised(tmp_path, drifted_surface(), sup).run(
        capability(), {"member_number": "400118"}
    )
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert result.bridges[0].decision == "reached"
    assert result.bridges[0].verified is False
    assert result.llm_calls == 3


async def test_a_checkpoint_that_was_not_offered_is_a_give_up(tmp_path):
    sup = ScriptedSupervisor([reached(cp="somewhere_else")], on_bridge=lambda s: s.advance())
    result = await supervised(tmp_path, drifted_surface(), sup).run(
        capability(), {"member_number": "400118"}
    )
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert result.bridges[0].verified is False


async def test_naming_a_declared_business_outcome_ends_the_run_as_an_answer(tmp_path):
    cap = capability(
        known_outcomes=[
            {
                "id": "no_member",
                "description": "nobody matched",
                "detector": {"kind": "text_present", "value": "NO MEMBER RECORD MATCHES"},
                "result": {"category": "BUSINESS_OUTCOME", "code": "RECORD_NOT_FOUND"},
            }
        ]
    )
    sup = ScriptedSupervisor([BridgeResult(decision="outcome", outcome_id="no_member", llm_calls=2)])
    result = await supervised(tmp_path, drifted_surface(), sup).run(cap, {"member_number": "400118"})
    assert result.category is OutcomeCategory.BUSINESS_OUTCOME
    assert result.business_outcome.id == "no_member"
    assert result.bridges[0].verified is True
    assert result.llm_calls == 2


async def test_naming_an_unknown_outcome_is_a_give_up(tmp_path):
    sup = ScriptedSupervisor([BridgeResult(decision="outcome", outcome_id="made_up", llm_calls=1)])
    result = await supervised(tmp_path, drifted_surface(), sup).run(
        capability(), {"member_number": "400118"}
    )
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert result.bridges[0].verified is False


async def test_a_step_is_bridged_at_most_once(tmp_path):
    # The supervisor names a dismissable outcome, so the engine re-runs s2. Its
    # postcondition fails again; s2 has already been bridged, so the supervisor
    # is not asked a second time and the original failure stands.
    cap = capability(
        known_outcomes=[
            {
                "id": "notice",
                "description": "an acknowledgement notice",
                "detector": {"kind": "text_present", "value": "NOTICE"},
                "result": {
                    "category": "RECOVERABLE",
                    "code": "UNEXPECTED_DIALOG",
                    "recovery": "dismiss_and_continue",
                },
            }
        ]
    )
    sup = ScriptedSupervisor(
        [BridgeResult(decision="outcome", outcome_id="notice", llm_calls=1), reached()]
    )
    result = await supervised(tmp_path, drifted_surface(), sup).run(cap, {"member_number": "400118"})
    assert len(sup.requests) == 1
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert [s.status for s in result.steps] == ["ok", "bridged", "failed"]
    assert result.llm_calls == 1


async def test_the_budget_is_spent_across_bridges(tmp_path):
    cap = capability(
        steps=[
            {
                "id": "s1",
                "intent": "type the member number",
                "action": {"type": "type", "text": "{{input.member_number}}"},
                "target": {"candidates": [{"strategy": "name", "value": "sval"}]},
                "postconditions": ["cp_open"],
            },
            {
                "id": "s2",
                "intent": "read the balance",
                "action": {"type": "read", "binding": "text"},
                "target": {"candidates": [{"strategy": "css", "value": "bal"}]},
                "postconditions": ["cp_done"],
            },
        ],
        checkpoints=[
            {
                "id": "cp_open",
                "description": "member record is open",
                "condition": {"kind": "text_present", "value": "MEMBER RECORD"},
            },
            {
                "id": "cp_done",
                "description": "never true on this surface",
                "condition": {"kind": "text_present", "value": "NEVER"},
            },
        ],
    )
    surface = NullSurface(
        matches={("name", "sval"): 1, ("css", "bal"): 1},
        reads={"bal": "x"},
        text_sequence=["NOPE", "MEMBER RECORD"],
    )
    # s1 fails cp_open -> bridge 1 spends 3 of 3 -> reached and verified -> s2 runs
    # and fails cp_done. No budget remains, so s2 is not bridged.
    sup = ScriptedSupervisor([reached(calls=3)], on_bridge=lambda s: s.advance())
    result = await supervised(tmp_path, surface, sup, budget=3).run(cap, {"member_number": "400118"})
    assert len(sup.requests) == 1
    assert result.llm_calls == 3
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert result.error is not None and result.error.step_id == "s2"


async def test_a_supervisor_that_raises_leaves_the_original_failure_in_place(tmp_path):
    class Exploding:
        name = "exploding"

        async def bridge(self, surface, policy, recorder, request):
            raise RuntimeError("network down")

    result = await supervised(tmp_path, drifted_surface(), Exploding()).run(
        capability(), {"member_number": "400118"}
    )
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert result.bridges[0].decision == "give_up"
    assert result.llm_calls == 0


async def test_a_failure_with_no_checkpoint_ahead_is_not_bridged(tmp_path):
    cap = capability(
        steps=[
            {
                "id": "s1",
                "intent": "type the member number",
                "action": {"type": "type", "text": "{{input.member_number}}"},
                "target": {"candidates": [{"strategy": "name", "value": "sval"}]},
            },
            {
                "id": "s2",
                "intent": "read the balance",
                "action": {"type": "read", "binding": "text"},
                "target": {"candidates": [{"strategy": "css", "value": "bal"}]},
            },
        ],
        checkpoints=[],
    )
    surface = NullSurface(matches={}, text="MEMBER RECORD")  # s1: MISSING_CONTROL
    sup = ScriptedSupervisor([reached()])
    result = await supervised(tmp_path, surface, sup).run(cap, {"member_number": "400118"})
    assert result.code is ErrorCode.MISSING_CONTROL
    assert sup.requests == [] and result.bridges == []


async def test_unmarked_mutating_steps_are_warned_about_when_supervision_is_on(tmp_path):
    cap = capability(
        steps=[
            {
                "id": "s1",
                "intent": "open the row",
                "action": {"type": "click"},
                "target": {"candidates": [{"strategy": "name", "value": "sval"}]},
            },
            {
                "id": "s2",
                "intent": "read the balance",
                "action": {"type": "read", "binding": "text"},
                "target": {"candidates": [{"strategy": "css", "value": "bal"}]},
                "postconditions": ["cp_open"],
            },
        ]
    )
    sup = ScriptedSupervisor([])
    result = await supervised(tmp_path, happy_surface(), sup, budget=2).run(
        cap, {"member_number": "400118"}
    )
    assert result.ok
    assert any("s1" in w and "risky" in w for w in result.warnings)
    unsupervised = await engine(happy_surface(), tmp_path).run(cap, {"member_number": "400118"})
    assert unsupervised.warnings == []
```

Note on `test_the_budget_is_spent_across_bridges`: `advance_twice` is a leftover name; keep a single `s.advance()` and the three-state `text_sequence`. The scripted text sequence is `NOPE` (s1 postcondition fails), `MEMBER RECORD` (after the bridge advances; s1 postcondition re-check passes, s2 runs and reads), then s2's postcondition sees index 1 still (`MEMBER RECORD`) and passes. To force the second drift, change the surface to `text_sequence=["NOPE", "NOPE", "MEMBER RECORD"]`? No — simpler: assert only that a *second* eligible failure is not bridged by giving s2 a **different** checkpoint whose text is never present:

```python
        checkpoints=[
            {"id": "cp_open", "description": "open", "condition": {"kind": "text_present", "value": "MEMBER RECORD"}},
            {"id": "cp_done", "description": "done", "condition": {"kind": "text_present", "value": "NEVER"}},
        ],
```

with s2's `postconditions: ["cp_done"]` and `text_sequence=["NOPE", "MEMBER RECORD"]`. Then: s1 fails, bridge 1 (3 calls of 3) reaches cp_open, verified, s2 runs, cp_done fails, budget is 0 so no bridge, run ends `CHECKPOINT_MISMATCH` with `len(sup.requests) == 1` and `llm_calls == 3`. Write the test that way and drop `advance_twice`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/replay/test_supervised.py -q`
Expected: FAIL with `TypeError: ReplayEngine.__init__() got an unexpected keyword argument 'supervisor'`.

- [ ] **Step 3: Wire the engine**

In `src/handrail/replay/engine.py`:

1. Imports. Add `MUTATING_ACTIONS` and `checkpoint_resume_index` to the `..schema` import; add `BridgeReport` to the `..schema.results` import; add:

```python
from .supervisor import (
    BRIDGEABLE,
    BridgeRequest,
    BridgeTarget,
    OutcomeSummary,
    Supervisor,
    describe_condition,
)
```

2. Add a control-flow exception after `_RestartCapability`:

```python
class _ResumeAt(Exception):
    """A bridge reached a checkpoint the engine verified; continue from there."""

    def __init__(self, index: int, note: str) -> None:
        self.index = index
        self.note = note
```

3. `__init__`: add parameters and state.

```python
        confirm_risky: bool = False,
        escalation_timeout_s: float | None = 300.0,
        supervisor: Supervisor | None = None,
        max_llm_calls: int | None = None,
    ) -> None:
        ...
        self.supervisor = supervisor
        #: None means "use the capability's recovery.max_llm_calls".
        self.max_llm_calls = max_llm_calls
        self._llm_budget = 0
        self._bridges: list[BridgeReport] = []
        self._bridged_steps: set[str] = set()
        self._raw_params: dict[str, Any] = {}
        self._supervision_warnings: list[str] = []
```

4. `run()`: reset the new state alongside the others, compute the budget and the warning, and report bridges.

After `self._entry_url = None` add:

```python
        self._bridges = []
        self._bridged_steps = set()
        self._raw_params = dict(params)
        self._supervision_warnings = []
        self._llm_budget = (
            capability.recovery.max_llm_calls if self.max_llm_calls is None else self.max_llm_calls
        )
```

In the "1. surface compatibility and policy" block, immediately after
`self.policy = self.policy.intersect(capability.safety)` and inside the same `try`, add:

```python
            if self.supervisor is not None and self._llm_budget > 0:
                self._supervision_warnings = self._unmarked_mutations(capability)
```

(`classify_risk` does not depend on the intersection; placing it here keeps the order of
refusals unchanged.)

In `finish(...)`, replace `llm_calls=0,  # invariant of this path` and the `warnings=` line with:

```python
                llm_calls=sum(b.llm_calls for b in self._bridges),
                bridges=list(self._bridges),
                warnings=[*capability.warnings, *self._supervision_warnings],
```

In the step loop, add a handler **before** `except _RestartCapability`:

```python
            except _ResumeAt as resume:
                self._reports.append(
                    StepReport(step_id=step.id, status="bridged", note=resume.note)
                )
                index = resume.index
                continue
```

5. `_execute_step`: three call sites.

Precondition loop becomes:

```python
        for cp_id in step.preconditions:
            try:
                await self._assert_checkpoint(capability.checkpoint(cp_id), step.id, "precondition")
            except CheckpointFailed as exc:
                await self._bridge_or_raise(capability, step, exc)
                raise
```

The `if last_error is not None:` block becomes:

```python
        if last_error is not None:
            # The model goes before the human. An unattended escalation parks the
            # control state at PAUSED and returns, after which every later step
            # would block in _await_control; a bridge that runs first keeps the
            # session in automation's hands and only bothers an operator with a
            # failure the supervisor could not fix.
            await self._bridge_or_raise(capability, step, last_error)
            if not await self._maybe_escalate(capability, step, last_error):
                raise last_error
```

Postcondition loop becomes:

```python
        for cp_id in step.postconditions:
            try:
                await self._assert_checkpoint(capability.checkpoint(cp_id), step.id, "postcondition")
            except CheckpointFailed as exc:
                await self._bridge_or_raise(capability, step, exc)
                raise
```

6. Refactor `_raise_if_known_outcome` so one outcome can be dispatched on its own. Replace the method with:

```python
    async def _raise_if_known_outcome(self, capability: Capability, step: Step) -> None:
        for outcome in capability.known_outcomes:
            if outcome.after_steps and step.id not in outcome.after_steps:
                continue
            detector = bind_model(outcome.detector, self._params)
            if not await self._detector_fired(outcome, step, detector):
                continue
            self.recorder.log(
                "outcome.detected",
                outcome=outcome.id,
                step=step.id,
                code=outcome.result.code.value,
            )
            await self._dispatch_outcome(capability, outcome, step)

    async def _dispatch_outcome(
        self, capability: Capability, outcome: KnownOutcome, step: Step
    ) -> None:
        """Act on a declared outcome. Returns only when the run should carry on."""
        if outcome.result.recovery == "dismiss_and_continue":
            return
        if outcome.result.recovery == "restart_capability":
            raise _RestartCapability(outcome.result.code, outcome.description)
        await self._capture_outcome_values(capability, outcome)
        if outcome.result.recovery == "escalate":
            if await self._escalate_outcome(outcome, step):
                return
            refs = await self.recorder.capture(self.surface, f"escalated_{outcome.id}")
            raise _TerminalOutcome(
                outcome.result,
                error=ErrorDetail.of(
                    outcome.result.code,
                    outcome.result.message or outcome.description,
                    step_id=step.id,
                    evidence=Evidence(**refs),
                ),
            )
        if outcome.result.category is OutcomeCategory.BUSINESS_OUTCOME:
            raise _TerminalOutcome(
                outcome.result,
                business=BusinessOutcome(
                    id=outcome.id,
                    code=outcome.result.code,
                    description=outcome.description,
                ),
            )
        refs = await self.recorder.capture(self.surface, f"outcome_{outcome.id}")
        if outcome.result.category is OutcomeCategory.SUCCESS:
            # A declared success is still a terminal outcome, but it is not an
            # error. Filling `error` here would leave every successful run
            # carrying an ErrorDetail whose code is NONE - a caller checking
            # `result.error is not None` would treat a posted hold as a fault.
            raise _TerminalOutcome(outcome.result)
        raise _TerminalOutcome(
            outcome.result,
            error=ErrorDetail.of(
                outcome.result.code,
                outcome.result.message or outcome.description,
                step_id=step.id,
                evidence=Evidence(**refs),
            ),
        )
```

7. Add the bridge section (place it after the checkpoints/outcomes section):

```python
    # -- supervision ------------------------------------------------------

    def _bridge_eligible(self, step: Step, exc: HandrailError) -> bool:
        return (
            self.supervisor is not None
            and self._llm_budget > 0
            and exc.code in BRIDGEABLE
            and step.id not in self._bridged_steps
        )

    @staticmethod
    def _step_index(capability: Capability, step_id: str) -> int:
        return next(i for i, s in enumerate(capability.steps) if s.id == step_id)

    def _bridge_target(self, capability: Capability, step: Step) -> BridgeTarget | None:
        """The nearest checkpoint ahead: the first state the engine can verify."""
        start = self._step_index(capability, step.id)
        for index in range(start, len(capability.steps)):
            candidate = capability.steps[index]
            ordered = (
                candidate.postconditions
                if index == start
                else [*candidate.preconditions, *candidate.postconditions]
            )
            for cp_id in ordered:
                cp = capability.checkpoint(cp_id)
                resume = checkpoint_resume_index(capability.steps, cp_id)
                if resume is None:
                    continue
                return BridgeTarget(
                    checkpoint_id=cp.id,
                    description=cp.description,
                    condition=describe_condition(cp.condition),
                    resume_index=resume,
                )
        return None

    def _bridge_alternatives(self, capability: Capability, step: Step) -> tuple[BridgeTarget, ...]:
        # Slice 2 fills this in. Forward bridging offers no fallback targets.
        return ()

    def _bridge_request(
        self, capability: Capability, step: Step, exc: HandrailError, target: BridgeTarget
    ) -> BridgeRequest:
        return BridgeRequest(
            capability_ref=capability.ref,
            title=capability.title,
            description=capability.description,
            failed_step_id=step.id,
            failed_intent=step.intent,
            failed_action=step.action.type,
            error_code=exc.code.value,
            error_message=exc.message,
            target=target,
            alternatives=self._bridge_alternatives(capability, step),
            known_outcomes=tuple(
                OutcomeSummary(o.id, o.result.category.value, o.description)
                for o in capability.known_outcomes
            ),
            inputs=tuple(spec.model_dump(mode="json") for spec in capability.inputs),
            params=dict(self._raw_params),
            turn_budget=min(self.policy.max_steps, self._llm_budget),
            sequence=len(self._bridges) + 1,
        )

    async def _bridge_or_raise(
        self, capability: Capability, step: Step, exc: HandrailError
    ) -> None:
        """Consult the supervisor about a failed check.

        Raises ``_ResumeAt`` when a claimed checkpoint verifies, or whatever a
        declared outcome raises when the supervisor named one. Returns when the
        supervisor gave up, was wrong, or was not eligible - and the caller then
        proceeds exactly as an unsupervised run would.
        """
        if not self._bridge_eligible(step, exc):
            return
        assert self.supervisor is not None
        target = self._bridge_target(capability, step)
        if target is None:
            self.recorder.log("bridge.skipped", step=step.id, reason="no_checkpoint_ahead")
            return
        request = self._bridge_request(capability, step, exc, target)
        self._bridged_steps.add(step.id)
        self.recorder.log(
            "bridge.start",
            step=step.id,
            code=exc.code.value,
            target=target.checkpoint_id,
            budget=self._llm_budget,
            sequence=request.sequence,
        )
        report = BridgeReport(
            from_step=step.id,
            trigger_code=exc.code,
            target_checkpoint=target.checkpoint_id,
            decision="give_up",
        )
        try:
            result = await self.supervisor.bridge(self.surface, self.policy, self.recorder, request)
        except Exception as err:  # noqa: BLE001 - a broken supervisor must not replace the failure
            self.recorder.log("bridge.error", step=step.id, error=str(err))
            self._bridges.append(report)
            return

        self._llm_budget = max(0, self._llm_budget - result.llm_calls)
        report = report.model_copy(
            update={
                "decision": result.decision,
                "reached_checkpoint": result.checkpoint_id,
                "outcome_id": result.outcome_id,
                "turns": result.turns,
                "llm_calls": result.llm_calls,
                "trace": result.trace,
                "proposed_outcome": result.proposed_outcome,
            }
        )
        self.recorder.log(
            "bridge.finish",
            step=step.id,
            decision=result.decision,
            checkpoint=result.checkpoint_id,
            outcome=result.outcome_id,
            turns=result.turns,
            llm_calls=result.llm_calls,
            summary=result.summary[:200],
        )

        if result.decision == "reached":
            offered = {t.checkpoint_id: t for t in (target, *request.alternatives)}
            chosen = offered.get(result.checkpoint_id or "")
            if chosen is None:
                self.recorder.log("bridge.rejected", reason="checkpoint_not_offered")
                self._bridges.append(report)
                return
            cp = capability.checkpoint(chosen.checkpoint_id)
            passed = await self.surface.evaluate(
                bind_model(cp.condition, self._params), timeout_ms=cp.timeout_ms
            )
            self.recorder.log("bridge.verified", checkpoint=cp.id, passed=passed)
            self._bridges.append(report.model_copy(update={"verified": passed}))
            if not passed:
                return
            raise _ResumeAt(chosen.resume_index, f"bridged to {cp.id}")

        if result.decision == "outcome":
            outcome = next(
                (o for o in capability.known_outcomes if o.id == result.outcome_id), None
            )
            self._bridges.append(report.model_copy(update={"verified": outcome is not None}))
            if outcome is None:
                self.recorder.log("bridge.rejected", reason="outcome_not_declared")
                return
            self.recorder.log(
                "outcome.detected",
                outcome=outcome.id,
                step=step.id,
                code=outcome.result.code.value,
                via="bridge",
            )
            await self._dispatch_outcome(capability, outcome, step)
            # A dismissable outcome returns; run the same step again.
            raise _ResumeAt(self._step_index(capability, step.id), f"bridge dismissed {outcome.id}")

        self._bridges.append(report)

    def _unmarked_mutations(self, capability: Capability) -> list[str]:
        """Steps that change the page but are not declared risky.

        safe_restart is inferred from the risk marking, so a mutating step nobody
        marked would let a supervisor rewind across it. Say so, once, up front.
        """
        unmarked = [
            s.id
            for s in capability.steps
            if s.action.type in ("click", "select", "press")
            and s.risk != "risky"
            and self.policy.classify_risk(s.action.type, s.intent) != "risky"
        ]
        if not unmarked:
            return []
        return [
            "supervision is on and these state-changing steps are not marked risky: "
            + ", ".join(unmarked)
            + ". A supervisor may steer back across them; mark them risk=\"risky\" if "
            "they change anything in the application."
        ]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/replay -q`
Expected: all PASS, including every pre-existing engine test and `test_no_llm.py`.

- [ ] **Step 5: Lint, type-check, run the whole suite, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src && uv run pytest -q
git add src/handrail/replay/engine.py tests/replay/test_supervised.py
git commit -m "feat(replay): consult a supervisor on drift, verify what it claims

A bridge is attempted before a human is asked, at most once per step,
only for drift-shaped codes, and only while the call budget lasts. A
claimed checkpoint is re-evaluated by the engine; a named outcome must
be declared. Unsupervised runs are byte-identical to before.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: Discovery — start from the current screen, bridge finish tool, call counter

**Files:**
- Modify: `src/handrail/discovery/tools.py` (after `FINISH_TOOL`, line ~121)
- Modify: `src/handrail/discovery/loop.py` (`DiscoveryTrace` at 86; `__init__` at 264; `run` at 281; finish handling at ~290; `_act` at 458)
- Modify: `src/handrail/discovery/planner.py` (`build_prompt` at 76; `AnthropicPlanner` at 145)
- Test: `tests/discovery/test_loop.py`, `tests/discovery/test_planner.py`

**Interfaces:**
- Produces: `BRIDGE_TOOLS: list[dict]`, `BRIDGE_FINISH_TOOL`; `DiscoveryLoop(..., confirm_risky: bool = True, trace_name: str = "trace.json")`; `DiscoveryLoop.run(params, *, navigate: bool = True)`; `DiscoveryTrace.finish_args: dict[str, Any]`; `trace.status in {"success","gave_up","reached","outcome","stuck","incomplete"}`; `AnthropicPlanner(model, client, max_tokens, tools=TOOLS, system_prompt=SYSTEM_PROMPT)` with `.calls: int`; `BRIDGE_SYSTEM_PROMPT`; `build_prompt` renders `job["known_outcomes"]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/discovery/test_loop.py`:

```python
from handrail.discovery.tools import BRIDGE_TOOLS


def test_the_bridge_vocabulary_widens_only_finish():
    assert [t["name"] for t in BRIDGE_TOOLS] == ["act", "assert_state", "finish"]
    assert BRIDGE_TOOLS[0] is TOOLS[0] and BRIDGE_TOOLS[1] is TOOLS[1]
    finish = BRIDGE_TOOLS[2]["input_schema"]["properties"]
    assert finish["status"]["enum"] == ["reached", "outcome", "give_up"]
    assert {"checkpoint_id", "outcome_id", "proposed_outcome"} <= set(finish)
    assert TOOLS[2]["input_schema"]["properties"]["status"]["enum"] == ["success", "give_up"]


async def test_run_without_navigate_starts_on_the_current_screen(tmp_path):
    surface = _surface()
    planner = ScriptedPlanner([Planned("finish", {"status": "give_up", "summary": "x"})])
    trace = await _loop(surface, planner, tmp_path).run({}, navigate=False)
    assert surface.navigations == []
    assert planner.seen[0]["url"] == "http://127.0.0.1:8081/inquiry"
    assert trace.status == "gave_up"


async def test_bridge_finish_statuses_survive_on_the_trace(tmp_path):
    for status, expected in (("reached", "reached"), ("outcome", "outcome"), ("give_up", "gave_up")):
        planner = ScriptedPlanner(
            [Planned("finish", {"status": status, "summary": "s", "checkpoint_id": "cp_open"})]
        )
        trace = await _loop(_surface(), planner, tmp_path).run({}, navigate=False)
        assert trace.status == expected
        assert trace.finish_args["checkpoint_id"] == "cp_open"
        assert trace.to_dict()["finish"]["status"] == status


async def test_the_trace_file_name_is_configurable(tmp_path):
    planner = ScriptedPlanner([Planned("finish", {"status": "give_up", "summary": "x"})])
    loop = DiscoveryLoop(
        surface=_surface(),
        planner=planner,
        policy=Policy(allowed_hosts=["127.0.0.1:8081"]),
        recorder=RunRecorder("discovery_t", root=str(tmp_path)),
        job=_job(),
        trace_name="bridge_2.trace.json",
    )
    await loop.run({}, navigate=False)
    assert (loop.recorder.dir / "bridge_2.trace.json").exists()
    assert not (loop.recorder.dir / "trace.json").exists()


async def test_an_unconfirmed_risky_action_is_refused_inside_a_bridge(tmp_path):
    planner = ScriptedPlanner(
        [
            Planned(
                "act",
                {
                    "intent": "post the hold",
                    "action": "click",
                    "target_role": "button",
                    "target_name": "F5=Search",
                },
            ),
            Planned("finish", {"status": "give_up", "summary": "refused"}),
        ]
    )
    loop = DiscoveryLoop(
        surface=_surface(),
        planner=planner,
        policy=Policy(allowed_hosts=["127.0.0.1:8081"], require_confirmation=True),
        recorder=RunRecorder("discovery_t", root=str(tmp_path)),
        job=_job(),
        confirm_risky=False,
    )
    trace = await loop.run({}, navigate=False)
    assert trace.entries[0].status == "failed"
    assert "confirmation" in (trace.entries[0].error or "")
```

Append to `tests/discovery/test_planner.py`:

```python
from handrail.discovery.planner import BRIDGE_SYSTEM_PROMPT
from handrail.discovery.tools import BRIDGE_TOOLS


def test_declared_outcomes_are_rendered_when_the_job_names_them():
    job = {
        "goal": "g",
        "inputs": [],
        "outputs": [],
        "known_outcomes": [
            {"id": "no_member", "category": "BUSINESS_OUTCOME", "description": "nobody matched"}
        ],
    }
    prompt = build_prompt("g", job, _observation(), [])
    assert "DECLARED OUTCOMES" in prompt
    assert "no_member (BUSINESS_OUTCOME): nobody matched" in prompt
    assert "DECLARED OUTCOMES" not in build_prompt("g", {"goal": "g"}, _observation(), [])


async def test_the_planner_sends_the_tools_and_system_prompt_it_was_given_and_counts_calls():
    response = _Response(
        [_Block("tool_use", name="finish", input_={"status": "reached", "summary": "s"})]
    )
    client = FakeClient(response)
    planner = AnthropicPlanner(
        client=client, tools=BRIDGE_TOOLS, system_prompt=BRIDGE_SYSTEM_PROMPT
    )
    await planner.decide("g", {"goal": "g"}, _observation(), [])
    await planner.decide("g", {"goal": "g"}, _observation(), [])
    assert planner.calls == 2
    sent = client.messages.calls[0]
    assert sent["tools"] is BRIDGE_TOOLS
    assert sent["system"] == BRIDGE_SYSTEM_PROMPT
    assert "reached" in BRIDGE_SYSTEM_PROMPT and "checkpoint_id" in BRIDGE_SYSTEM_PROMPT
```

(`_Block`, `_Response`, `FakeClient`, `_observation`, `build_prompt`, `AnthropicPlanner` already exist in that test file.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/discovery -q`
Expected: FAIL on `BRIDGE_TOOLS` import and on `run() got an unexpected keyword argument 'navigate'`.

- [ ] **Step 3: Implement**

`src/handrail/discovery/tools.py`, after `TOOLS`:

```python
BRIDGE_FINISH_TOOL: dict[str, Any] = {
    "name": "finish",
    "description": (
        "Stop bridging. `reached` when the target state (or an offered fallback "
        "checkpoint) is now on screen - name it in checkpoint_id. `outcome` when the "
        "screen is one of the DECLARED OUTCOMES - name it in outcome_id. `give_up` "
        "otherwise; if the screen is a terminal message no declared outcome names, "
        "describe it in proposed_outcome so a reviewer can add it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["reached", "outcome", "give_up"]},
            "summary": {"type": "string"},
            "checkpoint_id": {"type": "string"},
            "outcome_id": {"type": "string"},
            "proposed_outcome": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["SUCCESS", "BUSINESS_OUTCOME", "RECOVERABLE", "HARD_FAILURE"],
                    },
                    "code": {"type": "string"},
                    "screen_text": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["category", "code", "screen_text", "description"],
            },
        },
        "required": ["status", "summary"],
    },
}

#: The bridge vocabulary: the same actions, a finish that can name what it found.
BRIDGE_TOOLS: list[dict[str, Any]] = [ACT_TOOL, ASSERT_TOOL, BRIDGE_FINISH_TOOL]
```

`src/handrail/discovery/loop.py`:

- `DiscoveryTrace`: add `finish_args: dict[str, Any] = field(default_factory=dict)` and `"finish": self.finish_args,` in `to_dict()`.
- `__init__`: add `confirm_risky: bool = True` and `trace_name: str = "trace.json"`, stored as `self.confirm_risky` and `self.trace_name`. Docstring the first: "Discovery is interactive by definition, so risky actions default to confirmed. A bridge inherits the replay's flag instead."
- `run(self, params, *, navigate: bool = True)`: wrap the two entry lines:

```python
        if navigate:
            self.policy.check_url(self.job["entry_url"])
            await self.surface.navigate(self.job["entry_url"])
```

- Finish handling: replace `trace.status = "success" if planned.args.get("status") == "success" else "gave_up"` with:

```python
                status = str(planned.args.get("status") or "")
                # `reached` and `outcome` are bridge statuses. Ordinary discovery
                # keeps its two-valued contract with the compiler.
                trace.status = status if status in ("success", "reached", "outcome") else "gave_up"
                trace.finish_args = dict(planned.args)
```

and set `trace.stop_reason = planned.stop_reason or (None if trace.status != "gave_up" else "planner_gave_up")`.

- `_act`: change `self.policy.check_risky(risk, f"turn{entry.seq}", confirmed=True)` to `confirmed=self.confirm_risky`.
- Final write: `self.recorder.write_json(self.trace_name, trace.to_dict())`.

`src/handrail/discovery/planner.py`:

- `build_prompt`: after the DECLARED OUTPUTS block add:

```python
    if job.get("known_outcomes"):
        lines.append("DECLARED OUTCOMES (finish with `outcome` and the id if the screen is one):")
        for outcome in job["known_outcomes"]:
            lines.append(
                f"  - {outcome['id']} ({outcome.get('category', '?')}): "
                f"{outcome.get('description', '')}"
            )
        lines.append("")
```

- Add after `SYSTEM_PROMPT`:

```python
BRIDGE_SYSTEM_PROMPT = (
    SYSTEM_PROMPT
    + """
You are not discovering a flow from scratch. An automated replay of a known \
flow failed partway, and you are bridging it back on track. The GOAL names the \
exact state to reach. When that state - or one of the fallback checkpoints the \
goal lists - is on screen, call `finish` with status `reached` and put the \
checkpoint id in `checkpoint_id`. If the screen is one of the DECLARED OUTCOMES, \
call `finish` with status `outcome` and its id in `outcome_id` instead of pressing \
on. Do not re-submit anything that looks already submitted. Stay within a few \
actions; if you cannot get there, `give_up` and say what you saw - and if the \
screen is a terminal message no declared outcome names, fill `proposed_outcome`.
"""
)
```

- `AnthropicPlanner.__init__(self, model=DEFAULT_MODEL, client=None, max_tokens=4096, tools=None, system_prompt=SYSTEM_PROMPT)`: store `self.tools = tools if tools is not None else TOOLS`, `self.system_prompt = system_prompt`, `self.calls = 0`. In `decide`, increment `self.calls += 1` before the request and pass `system=self.system_prompt, tools=self.tools`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/discovery tests/compile tests/cli -q`
Expected: all PASS. (`tests/cli/test_discover.py` fakes the loop with the old constructor signature; the new parameters default, so it still works.)

- [ ] **Step 5: Lint, type-check, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src
git add src/handrail/discovery tests/discovery
git commit -m "feat(discovery): run from the current screen with a bridge finish

The loop can skip the entry navigation, name its trace file, inherit a
replay's risky-confirmation flag, and record a finish that says reached
or outcome. The planner takes its tools and system prompt as parameters
and counts its calls. Ordinary discovery is unchanged.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: The `handrail.supervise` package

**Files:**
- Create: `src/handrail/supervise/__init__.py`, `src/handrail/supervise/bridge.py`
- Test: `tests/supervise/__init__.py` (empty), `tests/supervise/test_bridge.py`

**Interfaces:**
- Consumes: Task 2 types, Task 4 loop/planner/tools.
- Produces: `AnthropicSupervisor(planner_factory: Callable[[], Planner] | None = None, confirm_risky: bool = False)`; `build_bridge_goal(request: BridgeRequest) -> str`; `bridge_job(request: BridgeRequest) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/supervise/test_bridge.py`:

```python
"""The Anthropic supervisor, driven by a scripted planner: no key, no network."""

from __future__ import annotations

import dataclasses

from handrail.discovery.tools import Planned
from handrail.kernel.evidence import RunRecorder
from handrail.kernel.policy import Policy
from handrail.replay.supervisor import BridgeRequest, BridgeTarget, OutcomeSummary
from handrail.supervise import AnthropicSupervisor
from handrail.supervise.bridge import bridge_job, build_bridge_goal
from handrail.surface.null_surface import NullSurface


class ScriptedPlanner:
    name = "scripted"
    model = None

    def __init__(self, decisions: list[Planned]) -> None:
        self.decisions = list(decisions)
        self.calls = 0
        self.jobs: list[dict] = []

    async def decide(self, goal, job, observation, history):
        self.calls += 1
        self.jobs.append(job)
        return (
            self.decisions.pop(0)
            if self.decisions
            else Planned("finish", {"status": "give_up", "summary": "out of script"})
        )


def request(**over) -> BridgeRequest:
    base = dict(
        capability_ref="plumbline.read_share_balance@1.0.0",
        title="Read a share balance",
        description="d",
        failed_step_id="s2",
        failed_intent="read the balance",
        failed_action="read",
        error_code="CHECKPOINT_MISMATCH",
        error_message="checkpoint cp_open failed (postcondition of s2): member record is open",
        target=BridgeTarget("cp_open", "member record is open", 'the text "MEMBER RECORD" is visible', 2),
        alternatives=(BridgeTarget("at_desk", "the desk", "the URL matches .*/desk$", 1),),
        known_outcomes=(OutcomeSummary("no_member", "BUSINESS_OUTCOME", "nobody matched"),),
        inputs=(
            {"name": "member_number", "type": "string", "required": True},
            {"name": "password", "type": "string", "required": True, "sensitivity": "secret"},
        ),
        params={"member_number": "400118", "password": "{{env.PLUMBLINE_PASSWORD}}"},
        turn_budget=4,
        sequence=1,
    )
    base.update(over)
    return BridgeRequest(**base)


def test_the_goal_names_the_failure_the_target_and_the_fallbacks():
    goal = build_bridge_goal(request())
    assert "read the balance" in goal and "CHECKPOINT_MISMATCH" in goal
    assert 'cp_open: the text "MEMBER RECORD" is visible' in goal
    assert "at_desk: the URL matches .*/desk$" in goal
    assert "reached" in goal and "outcome" in goal


def test_the_job_carries_inputs_outcomes_and_no_outputs():
    job = bridge_job(request())
    assert job["outputs"] == []
    assert [i["name"] for i in job["inputs"]] == ["member_number", "password"]
    assert job["known_outcomes"] == [
        {"id": "no_member", "category": "BUSINESS_OUTCOME", "description": "nobody matched"}
    ]
    assert job["entry_url"] == ""


def _run(tmp_path, decisions, surface=None):
    planner = ScriptedPlanner(decisions)
    sup = AnthropicSupervisor(planner_factory=lambda: planner)
    surface = surface or NullSurface(text="MEMBER RECORD", url="http://127.0.0.1:8081/inquiry")
    recorder = RunRecorder("replay_t", root=str(tmp_path))
    policy = Policy(allowed_hosts=["127.0.0.1:8081"])
    return planner, surface, recorder, sup, policy


async def test_reached_maps_to_a_verified_looking_result_and_writes_the_trace(tmp_path):
    planner, surface, recorder, sup, policy = _run(
        tmp_path,
        [Planned("finish", {"status": "reached", "summary": "there", "checkpoint_id": "cp_open"})],
    )
    result = await sup.bridge(surface, policy, recorder, request())
    assert result.decision == "reached"
    assert result.checkpoint_id == "cp_open"
    assert result.llm_calls == 1
    assert result.turns == 0
    assert result.trace == "bridge_1.trace.json"
    assert (recorder.dir / "bridge_1.trace.json").exists()
    assert surface.navigations == []


async def test_outcome_and_give_up_map_and_a_proposal_is_parsed(tmp_path):
    planner, surface, recorder, sup, policy = _run(
        tmp_path,
        [Planned("finish", {"status": "outcome", "summary": "s", "outcome_id": "no_member"})],
    )
    result = await sup.bridge(surface, policy, recorder, request())
    assert result.decision == "outcome" and result.outcome_id == "no_member"

    planner, surface, recorder, sup, policy = _run(
        tmp_path,
        [
            Planned(
                "finish",
                {
                    "status": "give_up",
                    "summary": "a message I do not know",
                    "proposed_outcome": {
                        "category": "BUSINESS_OUTCOME",
                        "code": "RECORD_NOT_FOUND",
                        "screen_text": "NO SUCH SHARE",
                        "description": "the share id does not exist",
                    },
                },
            )
        ],
    )
    result = await sup.bridge(surface, policy, recorder, request(sequence=2))
    assert result.decision == "give_up"
    assert result.proposed_outcome is not None
    assert result.proposed_outcome.screen_text == "NO SUCH SHARE"
    assert result.trace == "bridge_2.trace.json"


async def test_a_malformed_proposal_is_dropped_not_fatal(tmp_path):
    planner, surface, recorder, sup, policy = _run(
        tmp_path,
        [Planned("finish", {"status": "give_up", "summary": "s", "proposed_outcome": {"category": "NOPE"}})],
    )
    result = await sup.bridge(surface, policy, recorder, request())
    assert result.decision == "give_up" and result.proposed_outcome is None


async def test_the_turn_budget_caps_the_loop(tmp_path):
    act = Planned("act", {"intent": "type", "action": "type", "text": "x", "target_name_attr": "sval"})
    planner, surface, recorder, sup, policy = _run(
        tmp_path,
        [act] * 10,
        surface=NullSurface(matches={("name", "sval"): 1}, text="MEMBER RECORD", url="http://127.0.0.1:8081/inquiry"),
    )
    result = await sup.bridge(surface, policy, recorder, request(turn_budget=2))
    assert result.decision == "give_up"
    assert result.turns == 2
    assert planner.calls == 2


async def test_the_planner_sees_the_bridge_job(tmp_path):
    planner, surface, recorder, sup, policy = _run(
        tmp_path, [Planned("finish", {"status": "give_up", "summary": "s"})]
    )
    await sup.bridge(surface, policy, recorder, request())
    assert planner.jobs[0]["known_outcomes"][0]["id"] == "no_member"
    assert dataclasses.is_dataclass(request())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/supervise -q`
Expected: FAIL with `ModuleNotFoundError: handrail.supervise`.

- [ ] **Step 3: Implement**

`src/handrail/supervise/__init__.py`:

```python
"""The model supervisor for replay. The one package outside ``discovery`` that may import it."""

from .bridge import AnthropicSupervisor

__all__ = ["AnthropicSupervisor"]
```

`src/handrail/supervise/bridge.py`:

```python
"""Bridging: a short model-driven excursion that gets a stuck replay back on track.

The supervisor does not have a vocabulary of its own. It turns the engine's
``BridgeRequest`` into a discovery job - a goal that names the exact state to
reach, the same inputs, and the declared outcomes - and runs the existing
``DiscoveryLoop`` from the screen the replay is stuck on. The loop's ``finish``
is widened so the planner can say *which* checkpoint it reached or *which*
outcome it recognised; the engine, not this module, decides whether to believe
it.

Model calls are counted here and reported back so the engine can spend a budget.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from ..discovery.loop import DiscoveryLoop, Planner
from ..discovery.planner import BRIDGE_SYSTEM_PROMPT, AnthropicPlanner
from ..discovery.tools import BRIDGE_TOOLS
from ..kernel.evidence import RunRecorder
from ..kernel.policy import Policy
from ..replay.supervisor import BridgeRequest, BridgeResult
from ..schema.results import ProposedOutcome
from ..surface.base import Surface


def build_bridge_goal(request: BridgeRequest) -> str:
    fallbacks = "".join(
        f"\n  - {t.checkpoint_id}: {t.condition} (fallback)" for t in request.alternatives
    )
    return (
        f"An automated replay of '{request.title}' ({request.capability_ref}) failed at the "
        f"step '{request.failed_intent}' ({request.failed_action}) with {request.error_code}: "
        f"{request.error_message}\n"
        f"Get the application to this state and then finish with status `reached` and the "
        f"checkpoint id:\n"
        f"  - {request.target.checkpoint_id}: {request.target.condition}"
        f"{fallbacks}\n"
        "Use the supplied inputs exactly. If the screen is one of the DECLARED OUTCOMES, "
        "finish with status `outcome` and its id instead. If you cannot reach any listed "
        "state, finish with `give_up`."
    )


def bridge_job(request: BridgeRequest) -> dict[str, Any]:
    return {
        "capability_id": request.capability_ref,
        "goal": build_bridge_goal(request),
        "entry_url": "",
        "inputs": list(request.inputs),
        "outputs": [],
        "known_outcomes": [dataclasses.asdict(o) for o in request.known_outcomes],
    }


def _default_planner() -> Planner:
    return AnthropicPlanner(tools=BRIDGE_TOOLS, system_prompt=BRIDGE_SYSTEM_PROMPT)


class AnthropicSupervisor:
    name = "anthropic"

    def __init__(
        self,
        planner_factory: Callable[[], Planner] | None = None,
        confirm_risky: bool = False,
    ) -> None:
        # A fresh planner per bridge keeps call counts per bridge honest.
        self._planner_factory = planner_factory or _default_planner
        self.confirm_risky = confirm_risky

    async def bridge(
        self,
        surface: Surface,
        policy: Policy,
        recorder: RunRecorder,
        request: BridgeRequest,
    ) -> BridgeResult:
        planner = self._planner_factory()
        trace_name = f"bridge_{request.sequence}.trace.json"
        loop = DiscoveryLoop(
            surface=surface,
            planner=planner,
            policy=dataclasses.replace(policy, max_steps=max(1, request.turn_budget)),
            recorder=recorder,
            job=bridge_job(request),
            confirm_risky=self.confirm_risky,
            trace_name=trace_name,
        )
        trace = await loop.run(dict(request.params), navigate=False)
        finish = trace.finish_args
        calls = int(getattr(planner, "calls", 0))
        turns = len(trace.entries)
        summary = str(trace.summary or finish.get("summary") or "")

        if trace.status == "reached":
            return BridgeResult(
                decision="reached",
                checkpoint_id=str(finish.get("checkpoint_id") or "") or None,
                summary=summary,
                turns=turns,
                llm_calls=calls,
                trace=trace_name,
            )
        if trace.status == "outcome":
            return BridgeResult(
                decision="outcome",
                outcome_id=str(finish.get("outcome_id") or "") or None,
                summary=summary,
                turns=turns,
                llm_calls=calls,
                trace=trace_name,
            )
        return BridgeResult(
            decision="give_up",
            summary=summary or f"bridge ended {trace.status}",
            turns=turns,
            llm_calls=calls,
            trace=trace_name,
            proposed_outcome=_proposal(finish.get("proposed_outcome")),
        )


def _proposal(raw: Any) -> ProposedOutcome | None:
    """The model's description of an unknown screen, if it is well-formed."""
    if not isinstance(raw, dict):
        return None
    try:
        return ProposedOutcome.model_validate(raw)
    except ValidationError:
        return None
```

`Planner` is a `Protocol` in `loop.py` (line 115) and is importable. `Policy` is a dataclass, so `dataclasses.replace` works.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/supervise tests/replay/test_no_llm.py -q`
Expected: all PASS. The no-LLM audit's new test allows `supervise` to import discovery.

- [ ] **Step 5: Lint, type-check, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src
git add src/handrail/supervise tests/supervise
git commit -m "feat(supervise): the Anthropic supervisor, a discovery loop with a sub-goal

Turns a BridgeRequest into a discovery job, runs the existing loop from
the current screen with the bridge finish tool, and reports what the
planner claimed along with the calls it spent.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Compiler infers `safe_restart`

**Files:**
- Modify: `src/handrail/compile/compiler.py` (after `steps = _synthesise_waits(...)` at ~line 455; add helper near `_checkpoint_from`)
- Test: `tests/compile/test_compiler.py`

**Interfaces:**
- Consumes: `checkpoint_resume_index` (Task 1), `Checkpoint.safe_restart`.
- Produces: `_mark_safe_restart(steps: list[Step], checkpoints: list[Checkpoint]) -> list[Checkpoint]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/compile/test_compiler.py`:

```python
# ---------------------------------------------------------------- safe_restart


def test_checkpoints_before_the_first_risky_step_are_safe_to_re_enter() -> None:
    capability = compiled(hold_posted_trace(), job=PLACE_HOLD)
    risky = [s.id for s in capability.steps if s.risk == "risky"]
    assert risky, "the hold flow must contain a risky post step for this test to mean anything"
    first_risky = min(capability.steps.index(capability.step(s)) for s in risky)
    for cp in capability.checkpoints:
        resume = next(
            i for i, s in enumerate(capability.steps) if cp.id in s.preconditions or cp.id in s.postconditions
        )
        if cp.id in capability.steps[resume].postconditions:
            resume += 1
        expected = resume <= first_risky
        assert cp.safe_restart is expected, f"{cp.id}: resume {resume}, first risky {first_risky}"


def test_at_least_one_checkpoint_is_safe_and_at_least_one_is_not() -> None:
    capability = compiled(hold_posted_trace(), job=PLACE_HOLD)
    flags = {cp.safe_restart for cp in capability.checkpoints}
    assert flags == {True, False}
```

Check `hold_posted_trace()` in `tests/compile/fixtures.py` (from line 458) has an `assert_state` turn *after* the `F10=Post Hold` click. If it does not, the second test has no `False` to find, so add one to the fixture's `entries` between the post-hold `act` and the final `read`/`finish`:

```python
assert_state(
    98,
    "hold_confirmed",
    "the post landed on the confirmation screen",
    "url_matches",
    r".*/hold/post$",
    url=f"{BASE}/hold/post",
    frame="work",
)
```

Use `url_matches`, not `text_present "HOLD POSTED"`: the compiler refuses a checkpoint whose text echoes a value the run read back (`CHECKPOINT_ECHOES_OUTPUT`), and the confirmation line is exactly such a value. Give the turn a `seq` that sits between its neighbours. If `tests/compile/test_goldens.py` compares whole capabilities, regenerate the golden with the command that file documents and confirm the diff is only the new checkpoint plus `safe_restart` flags.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/compile/test_compiler.py -q -k safe`
Expected: FAIL — `safe_restart` is `False` everywhere.

- [ ] **Step 3: Implement**

In `compiler.py`, add `checkpoint_resume_index` to the `..schema` import. After `steps = _synthesise_waits(steps, acted, entries, step_for_entry, warnings)` add:

```python
    checkpoints = _mark_safe_restart(steps, checkpoints)
```

Add the helper after `_checkpoint_from`:

```python
def _mark_safe_restart(steps: list[Step], checkpoints: list[Checkpoint]) -> list[Checkpoint]:
    """A checkpoint is safe to re-enter when nothing risky has happened before it.

    The signal is the step's ``risk`` marking, not whether its action mutates the
    DOM: typing a member number into a search box is a ``type`` action that changes
    nothing in the bank, and using MUTATING_ACTIONS here would mark every
    checkpoint after sign-on unsafe. ``risk`` is what the policy layer already uses
    to decide what needs confirmation, so it is the one place an author says "this
    changes the world"; ``safe_restart`` follows from it.
    """
    first_risky = next((i for i, s in enumerate(steps) if s.risk == "risky"), len(steps))
    marked: list[Checkpoint] = []
    for cp in checkpoints:
        resume = checkpoint_resume_index(steps, cp.id)
        safe = resume is not None and resume <= first_risky
        marked.append(cp.model_copy(update={"safe_restart": safe}))
    return marked
```

Note the boundary: a checkpoint whose resume index equals the first risky step's index is a *precondition* of that risky step, so re-entering there re-runs the risky step once, which has not yet happened. That is safe. A postcondition of the risky step resumes at `first_risky + 1`, which is not.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/compile tests/tenancy -q`
Expected: all PASS. If a golden differs only by the new `safe_restart` field, regenerate it as that test module instructs and inspect the diff: only `"safe_restart": true/false` lines should change.

- [ ] **Step 5: Lint, type-check, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src
git add src/handrail/compile tests/compile
git commit -m "feat(compile): infer which checkpoints are safe to re-enter

Safe means no step marked risky has run before the checkpoint's resume
point. Risk marking, not DOM mutation, is the signal: typing into a
search box changes nothing in the bank.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: CLI — `--max-llm-calls` on replay and serve-console

**Files:**
- Modify: `src/handrail/cli.py` (`cmd_replay` at 509, `_run_replay` at 540, parsers at 693-764)
- Modify: `src/handrail/console/session.py` (`ConsoleSession.__init__` at 76)
- Test: `tests/cli/test_replay.py`

**Interfaces:**
- Consumes: `ReplayEngine(supervisor=, max_llm_calls=)` (Task 3), `AnthropicSupervisor` (Task 5).
- Produces: `_supervisor_for(budget: int, confirm_risky: bool) -> Supervisor | None`; `ConsoleSession(..., supervisor=None, max_llm_calls=None)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/cli/test_replay.py`:

```python
# --------------------------------------------------------------------------- #
# Supervision: a budget needs a key, and a bridged run reports its calls.
# --------------------------------------------------------------------------- #


def test_a_positive_budget_without_a_key_refuses_before_touching_the_browser(
    run_cli, scripted_surface, tmp_path, permissive_policy
):
    cap = write_capability(tmp_path / "cap.json")
    surface = surface_success()
    scripted_surface(surface)
    run = run_cli(*_argv(cap, tmp_path, permissive_policy, "--max-llm-calls", "5"))
    assert run.code == 5
    assert "ANTHROPIC_API_KEY" in run.stderr
    assert surface.actions == []


def test_the_default_budget_never_imports_the_supervise_package(
    run_cli, scripted_surface, tmp_path, permissive_policy
):
    import sys

    sys.modules.pop("handrail.supervise", None)
    sys.modules.pop("handrail.supervise.bridge", None)
    cap = write_capability(tmp_path / "cap.json")
    scripted_surface(surface_success())
    run = run_cli(*_argv(cap, tmp_path, permissive_policy))
    assert run.code == 0
    assert "handrail.supervise" not in sys.modules
    assert json.loads(run.stdout)["llm_calls"] == 0


def test_a_bridged_replay_reports_its_calls(
    run_cli, scripted_surface, tmp_path, permissive_policy, monkeypatch
):
    from handrail.replay.supervisor import BridgeResult

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")

    class FakeSupervisor:
        name = "fake"

        def __init__(self, **_):
            pass

        async def bridge(self, surface, policy, recorder, request):
            surface.advance()
            return BridgeResult(decision="reached", checkpoint_id=request.target.checkpoint_id, llm_calls=2)

    monkeypatch.setattr("handrail.supervise.AnthropicSupervisor", FakeSupervisor)
    cap = write_capability(tmp_path / "cap.json")
    from handrail.surface.null_surface import NullSurface

    scripted_surface(
        NullSurface(
            matches={("name", "sval"): 1, ("css", "msg"): 1},
            reads={"msg": "HOLD POSTED"},
            text_sequence=["DRIFTED", "MEMBER RECORD"],
        )
    )
    run = run_cli(*_argv(cap, tmp_path, permissive_policy, "--max-llm-calls", "5"))
    assert run.code == 0, run.stderr
    payload = json.loads(run.stdout)
    assert payload["llm_calls"] == 2
    assert payload["bridges"][0]["verified"] is True
```

The fixture capability's `search` step has postcondition `on_record` whose condition is text `MEMBER RECORD` (see `tests/cli/fixtures.py`); confirm by reading lines 55-75 of that file before relying on it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/cli/test_replay.py -q -k "budget or bridged"`
Expected: FAIL with argparse `unrecognized arguments: --max-llm-calls`.

- [ ] **Step 3: Implement**

In `cli.py`:

Add a helper near `_recorder`:

```python
def _supervisor_for(budget: int, confirm_risky: bool) -> Any:
    """Build the model supervisor, or refuse when a budget cannot be honoured."""
    if budget <= 0:
        return None
    if not os.environ.get(_API_KEY_ENV):
        raise CliRefusal(
            f"--max-llm-calls {budget} asks a model to bridge drift, and {_API_KEY_ENV} is "
            "not set. Either export it (or put it in .env) or run without a budget - an "
            "unsupervised replay never needs a key."
        )
    # Imported here so a plain replay never loads the discovery package or the SDK.
    from .supervise import AnthropicSupervisor

    return AnthropicSupervisor(confirm_risky=confirm_risky)
```

In `cmd_replay`, after `_prepare_replay` and before the recorder:

```python
    budget = (
        capability.recovery.max_llm_calls if args.max_llm_calls is None else args.max_llm_calls
    )
    supervisor = _supervisor_for(budget, args.confirm_risky)
    if supervisor is not None:
        _say(f"supervised: up to {budget} model call(s) may be spent bridging drift")
```

Pass `supervisor=supervisor, max_llm_calls=budget` into `_run_replay`, and inside it into both `ConsoleSession(...)` and `ReplayEngine(...)`. Add the two parameters to `_run_replay`'s signature (`supervisor: Any = None, max_llm_calls: int | None = None`).

In both the `replay` and `serve-console` parsers add:

```python
    replay.add_argument(
        "--max-llm-calls",
        type=int,
        default=None,
        metavar="N",
        help=(
            "let a model supervisor bridge drift, spending at most N calls; default is "
            "the capability's recovery.max_llm_calls, usually 0 (never consult a model)"
        ),
    )
```

(and the same on `console`).

In `console/session.py`, add `supervisor: Any = None, max_llm_calls: int | None = None` to `ConsoleSession.__init__` (keyword-only, after `escalation_timeout_s`) and forward them to `ReplayEngine(...)`. Import `Any` if not already imported.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/cli tests/console -q`
Expected: all PASS.

- [ ] **Step 5: Lint, type-check, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src
git add src/handrail/cli.py src/handrail/console/session.py tests/cli/test_replay.py
git commit -m "feat(cli): --max-llm-calls lets a replay bridge drift with a model

Defaults to the capability's recovery.max_llm_calls, normally zero, so
an ordinary replay never imports the supervisor or needs a key. A
positive budget without a key refuses before the browser opens.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: Report — the Bridges section

**Files:**
- Modify: `src/handrail/report/trace_report.py` (`render_run_report` at 90, `_run_facts` at 121)
- Test: `tests/report/test_run_report.py`

**Interfaces:**
- Consumes: `RunResult.bridges`, `BridgeReport`.

- [ ] **Step 1: Write the failing test**

Append to `tests/report/test_run_report.py`:

```python
from handrail.schema.results import BridgeReport


def test_a_bridged_run_gets_a_bridges_section_and_an_honest_llm_line():
    result = RunResult(
        run_id=RUN_ID,
        capability_id="plumbline.place_share_hold",
        capability_version="1.2.0",
        started_at="2026-08-30T10:15:00+00:00",
        duration_ms=9000,
        category=OutcomeCategory.SUCCESS,
        steps=[StepReport(step_id="open-share", status="bridged", note="bridged to share_open")],
        llm_calls=4,
        bridges=[
            BridgeReport(
                from_step="open-share",
                trigger_code=ErrorCode.MISSING_CONTROL,
                target_checkpoint="share_open",
                decision="reached",
                reached_checkpoint="share_open",
                verified=True,
                turns=3,
                llm_calls=4,
                trace="bridge_1.trace.json",
            )
        ],
    )
    text = render_run_report(result, Path("/tmp/evidence/x"))
    assert "## Bridges" in text
    assert "| `open-share` | MISSING_CONTROL | `share_open` | reached | `share_open` | yes | 3 | 4 |" in text
    assert "bridge_1.trace.json" in text
    assert "4 across 1 bridge" in text and "AI-free" not in text
    plain = render_run_report(RunResult(
        run_id=RUN_ID,
        capability_id="c",
        capability_version="1.0.0",
        started_at="2026-08-30T10:15:00+00:00",
        duration_ms=1,
        category=OutcomeCategory.SUCCESS,
    ))
    assert "## Bridges" not in plain
    assert "0 (replay is AI-free by construction)" in plain
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/report/test_run_report.py -q -k bridged`
Expected: FAIL — no Bridges section.

- [ ] **Step 3: Implement**

In `_run_facts`, replace the `("LLM calls", ...)` pair with:

```python
        (
            "LLM calls",
            f"{result.llm_calls} (replay is AI-free by construction)"
            if not result.bridges
            else f"{result.llm_calls} across {len(result.bridges)} bridge"
            + ("" if len(result.bridges) == 1 else "s"),
        ),
```

In `render_run_report`, after `out += _steps_section(result)` add `out += _bridges_section(result, evidence_dir)`. Add:

```python
def _bridges_section(result: RunResult, evidence_dir: Path | None) -> list[str]:
    """Every consultation of the supervisor, verified or not.

    Absent from an unsupervised run: a section that always prints "none" would
    teach readers to skip it, and the whole point is that a bridge is unusual.
    """
    if not result.bridges:
        return []
    out = [
        "## Bridges",
        "",
        "A deterministic check failed and a model supervisor was consulted. `Verified` "
        "means the engine re-evaluated the claimed checkpoint (or found the named "
        "outcome) itself; an unverified bridge was treated as a give-up.",
        "",
    ]
    rows: list[list[Any]] = []
    for bridge in result.bridges:
        trace = bridge.trace or "-"
        if bridge.trace and evidence_dir is not None:
            trace = f"[{bridge.trace}]({bridge.trace})"
        rows.append(
            [
                f"`{bridge.from_step}`",
                bridge.trigger_code.value,
                f"`{bridge.target_checkpoint}`" if bridge.target_checkpoint else "-",
                bridge.decision,
                f"`{bridge.reached_checkpoint}`" if bridge.reached_checkpoint else (
                    f"`{bridge.outcome_id}`" if bridge.outcome_id else "-"
                ),
                "yes" if bridge.verified else "no",
                bridge.turns,
                bridge.llm_calls,
                trace,
            ]
        )
    out += _table(
        ["From step", "Trigger", "Target", "Decision", "Claimed", "Verified", "Turns", "Calls", "Trace"],
        rows,
    )
    proposals = [b.proposed_outcome for b in result.bridges if b.proposed_outcome]
    if proposals:
        out += ["", "The supervisor met screens no declared outcome names:", ""]
        for p in proposals:
            out.append(
                f"- **{p.category.value}/{p.code.value}** `{p.screen_text}` - {p.description}"
            )
    return out + [""]
```

Check how `_table` renders cells (look at its definition in the same file) so the expected row in the test matches exactly; adjust the assertion string to the renderer's spacing, not the other way round.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/report -q`
Expected: all PASS, goldens unchanged (no bridges in them).

- [ ] **Step 5: Lint, type-check, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src
git add src/handrail/report/trace_report.py tests/report/test_run_report.py
git commit -m "feat(report): show bridges, and stop calling a bridged run AI-free

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Docs and the live drift check

**Files:**
- Modify: `README.md` (after "Human takes over"), `docs/ARCHITECTURE.md` (section 6 bullet "On failure it stops"), `TESTING.md` (new section after 3), `scripts/verify.sh` (after step 6)

- [ ] **Step 1: README**

Insert after the "Human takes over" section:

```markdown
## When the bank drifts

```bash
uv run handrail replay artifacts/capabilities/place-hold-quarrybrook.json \
  --tenant fernhollow --max-llm-calls 12 \
  --input operator_id=dcolewell --input member_number=400118 \
  --input share_id=400118-S0001 --input reason=LEGAL --input notes=None
```

Replay is model-free by default, and stays that way until a deterministic check
fails. With a budget, a **supervisor** may then drive the browser for a few
turns to reach the next checkpoint the capability declares, or name a declared
outcome it recognises. The engine re-evaluates every claim itself before
trusting it, counts every model call, and writes the excursion to the run's
evidence as `bridge_<n>.trace.json`. `llm_calls` in the result says exactly what
was spent; a budget of zero (the default) is today's guarantee, unchanged.

The model goes before the human: an operator is only escalated to for a failure
the supervisor could not fix. Bridges never cross a step marked risky.
```

- [ ] **Step 2: ARCHITECTURE**

Replace the bullet beginning "**On failure it stops.**" in section 6 with:

```markdown
- **On failure it stops - unless you give it a budget.** By default it never
  re-plans and never calls a model mid-run. With `--max-llm-calls N`, a
  *supervisor* may be consulted when a checkpoint or locator fails: it drives
  the browser for a few turns towards the next checkpoint the recipe declares,
  and the engine then checks that checkpoint itself before carrying on. Every
  call is counted, every bridge is recorded as evidence, and a claim the engine
  cannot verify is treated as a give-up. Model spend scales with breakage, not
  with step count; the green path stays at zero.
```

- [ ] **Step 3: TESTING**

Insert after section 3:

```markdown
## 3b. Supervised replay — drift, bridged

Needs `ANTHROPIC_API_KEY`. Replay the Quarrybrook capability at Fernhollow
*without* its overlay, so the field names do not match, and let a supervisor
bridge the gap:

```bash
uv run handrail replay artifacts/capabilities/place-hold-quarrybrook.json \
  --tenant fernhollow --max-llm-calls 12 --headed --slow-mo 300 \
  --input operator_id=dcolewell --input member_number=400118 \
  --input share_id=400118-S0001 --input reason=LEGAL --input notes=None
```

Expect `SUCCESS` with `llm_calls` greater than zero and, in `result.json`, a
`bridges` entry with `"verified": true`. The evidence directory holds
`bridge_1.trace.json` and a screenshot per bridge turn. Run the same command
with `--max-llm-calls 0` to see the unsupervised failure it started from.
```

- [ ] **Step 4: verify.sh**

After step 6's `fi`, add:

```bash
# ------------------------------------------------------------- supervision
step "6b. Supervised replay (a model bridges an injected drift)"

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  curl -sf -o /dev/null -X POST "$FH/__test/reset" || true
  OUT=$(mktemp -d)/result.json
  "${HANDRAIL[@]}" replay artifacts/capabilities/place-hold-quarrybrook.json \
      --tenant fernhollow --base-url "$FH" --max-llm-calls 12 \
      --input operator_id=dcolewell --input member_number=400118 \
      --input share_id=400118-S0001 --input reason=LEGAL --input notes=None \
      >"$OUT" 2>"$LOG"
  CODE=$?
  VERDICT=$(python3 -c "import json;d=json.load(open('$OUT'));b=d.get('bridges',[]);print(d['category'],d['llm_calls'],sum(1 for x in b if x.get('verified')))" 2>/dev/null || echo "? ? ?")
  set -- $VERDICT
  if [ "$CODE" = "0" ] && [ "${3:-0}" -ge 1 ]; then
    pass "the Quarrybrook capability replayed at Fernhollow with no overlay: $2 model call(s), $3 verified bridge(s)"
  elif [ "$CODE" = "0" ] && [ "${2:-0}" = "0" ]; then
    skip "the capability replayed at Fernhollow without drifting, so no bridge was exercised"
  else
    fail "supervised replay ended $1 with $2 model call(s) and $3 verified bridge(s)"
    tail -10 "$LOG" | sed 's/^/        /'
  fi
else
  skip "ANTHROPIC_API_KEY is not set - a bridge needs a model"
fi
```

Confirm the reset endpoint path by grepping `targetapp/` for the route the existing `run_replay` helper in this script uses, and use that exact path.

- [ ] **Step 5: Run the docs-adjacent checks and commit**

Run: `bash -n scripts/verify.sh && uv run pytest -q`
Expected: syntax OK, suite green.

```bash
git add README.md docs/ARCHITECTURE.md TESTING.md scripts/verify.sh
git commit -m "docs: supervised replay - when the bank drifts, and how to prove it

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10 (slice 2): Rewind targets and the risky-step guard

**Files:**
- Modify: `src/handrail/replay/engine.py` (`_bridge_alternatives`, `_execute_step` end, `run` state)
- Test: `tests/replay/test_supervised.py`

**Interfaces:**
- Consumes: `Checkpoint.safe_restart`, `checkpoint_resume_index`.
- Produces: `_bridge_alternatives` returns `safe_restart` checkpoints behind the failing step whose resume index is not preceded by an executed risky step.

- [ ] **Step 1: Write the failing tests**

Append to `tests/replay/test_supervised.py`:

```python
S1_SEARCH = {
    "id": "s1",
    "intent": "type the member number",
    "action": {"type": "type", "text": "{{input.member_number}}"},
    "target": {"candidates": [{"strategy": "name", "value": "sval"}]},
    "postconditions": ["cp_searched"],
}
S2_OPEN = {
    "id": "s2",
    "intent": "open the record",
    "action": {"type": "click"},
    "target": {"candidates": [{"strategy": "name", "value": "open"}]},
}
S2_POST = {
    "id": "s2",
    "intent": "post the hold",
    "action": {"type": "click"},
    "target": {"candidates": [{"strategy": "name", "value": "post"}]},
    "risk": "risky",
}
S3_READ = {
    "id": "s3",
    "intent": "read the balance",
    "action": {"type": "read", "binding": "text"},
    "target": {"candidates": [{"strategy": "css", "value": "bal"}]},
    "postconditions": ["cp_open"],
}
CP_SEARCHED_SAFE = {
    "id": "cp_searched",
    "description": "the search ran",
    "condition": {"kind": "text_present", "value": "SEARCHED"},
    "safe_restart": True,
}
CP_SEARCHED_UNSAFE = {**CP_SEARCHED_SAFE, "safe_restart": False}
CP_OPEN = {
    "id": "cp_open",
    "description": "member record is open",
    "condition": {"kind": "text_present", "value": "MEMBER RECORD"},
}


def three_steps(second: dict, searched: dict = CP_SEARCHED_SAFE):
    return capability(steps=[S1_SEARCH, second, S3_READ], checkpoints=[searched, CP_OPEN])


def three_step_surface(*texts: str) -> NullSurface:
    return NullSurface(
        matches={("name", "sval"): 1, ("name", "open"): 1, ("name", "post"): 1, ("css", "bal"): 1},
        reads={"bal": "x"},
        text_sequence=list(texts),
    )


async def test_safe_checkpoints_behind_the_failure_are_offered_as_fallbacks(tmp_path):
    # s3's postcondition fails. cp_searched sits behind it, is safe, and no risky
    # step has run, so it is offered. The supervisor falls back to it, the engine
    # verifies it, and replay resumes at s2.
    surface = three_step_surface("SEARCHED", "SEARCHED MEMBER RECORD")
    sup = ScriptedSupervisor([reached("cp_searched")], on_bridge=lambda s: s.advance())
    result = await supervised(tmp_path, surface, sup).run(
        three_steps(S2_OPEN), {"member_number": "400118"}
    )
    request = sup.requests[0]
    assert request.target.checkpoint_id == "cp_open"
    assert [t.checkpoint_id for t in request.alternatives] == ["cp_searched"]
    assert request.alternatives[0].resume_index == 1
    assert result.ok
    assert result.bridges[0].verified is True
    assert [s.status for s in result.steps] == ["ok", "ok", "bridged", "ok", "ok"]


async def test_a_fallback_behind_an_executed_risky_step_is_never_offered(tmp_path):
    surface = three_step_surface("SEARCHED")  # cp_open never holds
    sup = ScriptedSupervisor([reached("cp_searched")])
    result = await supervised(tmp_path, surface, sup).run(
        three_steps(S2_POST), {"member_number": "400118"}
    )
    assert sup.requests[0].alternatives == ()
    # Naming it anyway is a give-up, not a rewind across the posted hold.
    assert result.bridges[0].verified is False
    assert result.code is ErrorCode.CHECKPOINT_MISMATCH
    assert surface.actions.count(("click", None)) == 1


async def test_an_unsafe_checkpoint_is_not_a_fallback_even_before_any_risky_step(tmp_path):
    surface = three_step_surface("SEARCHED")
    sup = ScriptedSupervisor([BridgeResult(decision="give_up")])
    await supervised(tmp_path, surface, sup).run(
        three_steps(S2_OPEN, searched=CP_SEARCHED_UNSAFE), {"member_number": "400118"}
    )
    assert sup.requests[0].alternatives == ()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/replay/test_supervised.py -q -k "fallback or unsafe"`
Expected: the first FAILS (alternatives empty); the other two may already pass, which is fine.

- [ ] **Step 3: Implement**

In `engine.py`:

- Add state in `__init__`: `self._executed_risky: set[int] = set()`; reset in `run()`; also reset on `_RestartCapability` (next to `self._step_values.clear()`).
- At the end of `_execute_step`, after `self._reports.append(report)`, add:

```python
        if risk == "risky":
            self._executed_risky.add(self._step_index(capability, step.id))
```

(`risk` is the local computed at the top of `_execute_step`, which the policy may have raised.)

- Replace `_bridge_alternatives`:

```python
    def _bridge_alternatives(self, capability: Capability, step: Step) -> tuple[BridgeTarget, ...]:
        """Safe checkpoints behind the failure the supervisor may fall back to.

        Two gates, both the engine's: the checkpoint must say safe_restart, and no
        step marked risky may have executed at or after its resume point. A
        planner never sees a target that would replay a posted hold.
        """
        failing = self._step_index(capability, step.id)
        offered: list[BridgeTarget] = []
        for cp in capability.checkpoints:
            if not cp.safe_restart:
                continue
            resume = checkpoint_resume_index(capability.steps, cp.id)
            if resume is None or resume >= failing:
                continue
            if any(resume <= executed < failing for executed in self._executed_risky):
                continue
            offered.append(
                BridgeTarget(
                    checkpoint_id=cp.id,
                    description=cp.description,
                    condition=describe_condition(cp.condition),
                    resume_index=resume,
                )
            )
        return tuple(offered)
```

The `reached` branch of `_bridge_or_raise` already accepts any offered target, so no change there.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/replay -q`
Expected: all PASS.

- [ ] **Step 5: Lint, type-check, full suite, commit**

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src && uv run pytest -q
git add src/handrail/replay/engine.py tests/replay/test_supervised.py
git commit -m "feat(replay): offer safe checkpoints behind a failure as bridge fallbacks

Only checkpoints marked safe_restart, and never across a risky step that
has already run. The engine computes the list; the planner cannot name
a target it was not given.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Self-review against the spec

| spec section | task |
|---|---|
| §4 schema | 1 |
| §3 boundary, no-LLM audit | 2 (audit test), 5 |
| §5 trigger, model-before-human | 3 |
| §6 request, target choice, resume index | 3 (target), 10 (alternatives, risky guard) |
| §7 bridge run, `navigate=False`, `BRIDGE_TOOLS`, `finish_args`, `trace_name`, `confirm_risky`, call counting | 4, 5 |
| §8 engine handling, `safe_restart` inference, unmarked-mutation warning | 3, 6 |
| §9 CLI, report, verify.sh | 7, 8, 9 |
| §10 error handling table | 3 (`bridge.error`, unknown ids, unverified), 5 (malformed proposal) |
| §11 tests | each task |
| §12 files | file map above |

Known deviations from the spec, both deliberate: the unmarked-mutation warning is produced by the engine at run time (spec §8 was amended to say so), and `proposed_outcome` parsing ships in Task 5 rather than waiting for slice 2 because it is three lines and the schema already exists.
