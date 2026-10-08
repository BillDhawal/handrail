"""The replay engine: a cook following a recipe card, step by step, checking as it goes.

The recipe is the capability. The cook never improvises. Before every step it
checks it is standing at the right counter (the screen matches), finds the one
utensil the step names (resolve), writes "starting step" in the ledger if the
step changes anything (journal), does the step (act), waits for the visible
sign that it landed (settle), writes "done" in the ledger (journal again), and
checks the counter it expected to end up at (expect). If any check fails it
stops and says exactly which check, on which step, expected what, saw what.

No model is consulted anywhere in this file. The two counters in the result,
``classifier_calls`` and ``llm_calls``, are zero for every run that stays on
the ordinary path, and an import guard makes sure this package cannot reach
one. When a screen check fails and a referee was handed in, rung one
(``rungs.py``) may be asked which declared screen this is; the engine checks
the answer against the stored furniture before believing it, and counts it.

The one rule the cook will not break, even if told to: a commit written as
"starting" in the ledger with no "done" beside it is never repeated. It is
refused with UNSAFE_TO_RETRY, and finding out what happened is somebody else's
job - a read-only probe in a later milestone, or a person. A stage step is
different: re-typing a field or re-selecting an option is harmless by
definition, so on a resumed run a stage is simply done again.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..escalate.bridge import Bridge
from ..escalate.classifier import Classifier
from ..kernel.episodes import Episodes
from ..kernel.evidence import Recorder
from ..schema.bindings import bind_target, bind_text
from ..schema.capability import Capability, Step
from ..schema.effects import EffectClass
from ..schema.errors import ErrorCode, HandrailError, OutcomeCategory
from ..schema.results import Drift, ErrorDetail, RunResult, StepReport
from ..surface.base import Resolution, Surface
from .journal import Journal
from .prepare import outputs, prepare
from .rungs import RungOne, RungThree, RungTwo
from .screens import Finished, Screens

DEFAULT_SETTLE_TIMEOUT_MS = 8000


@dataclass
class _Run:
    """Everything one run accumulates. Built fresh in `run`, so a reused engine never mixes two."""

    capability: Capability
    journal: Journal
    params: dict[str, Any] = field(default_factory=dict)
    reports: list[StepReport] = field(default_factory=list)
    drift: Drift = field(default_factory=Drift)
    read_values: dict[str, str] = field(default_factory=dict)
    rung1: RungOne | None = None
    rung2: RungTwo | None = None
    rung3: RungThree | None = None
    screens: Screens | None = None


class ReplayEngine:
    def __init__(
        self,
        surface: Surface,
        recorder: Recorder,
        env: Mapping[str, str] | None = None,
        poll_interval_s: float = 0.25,
        settle_timeout_ms: int = DEFAULT_SETTLE_TIMEOUT_MS,
        classifier: Classifier | None = None,
        episodes: Episodes | None = None,
        bridge: Bridge | None = None,
        console: Any = None,
        human_wait_s: float | None = None,
    ) -> None:
        self.surface = surface
        self.recorder = recorder
        self.env = dict(env or {})
        self.poll_interval_s = poll_interval_s
        self.settle_timeout_ms = settle_timeout_ms
        self.classifier = classifier
        self.episodes = episodes
        self.bridge = bridge
        self.console = console
        self.human_wait_s = human_wait_s

    async def run(
        self, capability: Capability, inputs: dict[str, Any], journal: Journal | None = None
    ) -> RunResult:
        started, clock = datetime.now(UTC), time.monotonic()
        run = _Run(capability, journal or Journal())
        if self.classifier is not None:
            run.rung1 = RungOne(self.classifier, self.recorder, capability, self.episodes)
        if self.bridge is not None:
            run.rung2 = RungTwo(self.bridge, self.surface, self.recorder, capability, self.episodes)
        if self.console is not None:
            run.rung3 = RungThree(
                self.console, self.recorder, capability, self.episodes, self.human_wait_s
            )
        screens = Screens(self.surface, self.recorder, capability, run.rung1, run.rung2, run.rung3)
        run.screens = screens
        outcome: str | None = None
        error: ErrorDetail | None = None

        def finish(category: OutcomeCategory, code: ErrorCode) -> RunResult:
            produced = outputs(capability, outcome, run.read_values) if outcome else {}
            result = RunResult(
                run_id=self.recorder.run_id,
                capability_id=capability.id,
                capability_version=capability.version,
                started_at=started.isoformat(),
                duration_ms=int((time.monotonic() - clock) * 1000),
                category=category,
                code=code,
                outcome=outcome,
                outputs=produced,
                error=error,
                steps=run.reports,
                drift=run.drift,
                classifier_calls=run.rung1.calls if run.rung1 else 0,
                llm_calls=run.rung2.model_calls if run.rung2 else 0,
                escalated_to_human=bool(run.rung3 and run.rung3.escalations),
            )
            self.recorder.write_json("result.json", result)
            self.recorder.log("replay.finish", category=category.value, code=code.value)
            if self.episodes is not None:
                held = category in (OutcomeCategory.SUCCESS, OutcomeCategory.BUSINESS_OUTCOME)
                self.episodes.settle(self.recorder.run_id, category.value, held)
            return result

        try:
            self._compatible(capability)
            run.params = prepare(capability, inputs, self.recorder, self.env)
            screens.inputs, screens.env = run.params, self.env
            await self.surface.open(bind_text(capability.surface.entry, run.params, self.env))
            for step in capability.steps:
                await self._run_step(run, step)
            final = await screens.name(list(capability.outcomes), None)
            if final not in capability.outcomes:
                raise HandrailError(
                    f"the run ended on {final!r}, which is not an outcome",
                    ErrorCode.SCREEN_MISMATCH,
                )
            raise Finished(final)
        except Finished as done:
            outcome = done.outcome
            declared = capability.outcomes[outcome]
            return finish(declared.category, declared.code)
        except HandrailError as exc:
            refs = await self.recorder.capture(self.surface, f"fail_{exc.step_id or 'run'}")
            self.recorder.log("replay.error", code=exc.code.value, message=exc.message, **refs)
            error = ErrorDetail(code=exc.code, message=exc.message, step_id=exc.step_id)
            return finish(exc.category, exc.code)
        except Exception as exc:  # noqa: BLE001 - a run never ends in a bare exception
            await self.recorder.capture(self.surface, "crash")
            error = ErrorDetail(
                code=ErrorCode.APPLICATION_ERROR, message=f"{type(exc).__name__}: {exc}"
            )
            return finish(OutcomeCategory.HARD_FAILURE, ErrorCode.APPLICATION_ERROR)

    # -- before the first step ----------------------------------------------------

    def _compatible(self, capability: Capability) -> None:
        if self.surface.kind not in ("null", capability.surface.kind):
            raise HandrailError(
                f"capability needs a {capability.surface.kind} surface, got {self.surface.kind}",
                ErrorCode.SURFACE_INCOMPATIBLE,
            )

    # -- one step -----------------------------------------------------------------

    async def _run_step(self, run: _Run, step: Step) -> None:
        clock = time.monotonic()
        capability, journal, params = run.capability, run.journal, run.params
        self.recorder.log("step.start", step=step.id, verb=step.op.verb, effect=step.effect.kind)

        screens = run.screens
        assert screens is not None
        if run.rung3 is not None and not run.rung3.baton.automation_may_act:
            if not await run.rung3.baton.wait_until_automation_may_act(self.human_wait_s):
                raise HandrailError(
                    "aborted at the console", ErrorCode.ABORTED_BY_OPERATOR, step.id
                )
        await screens.expect(step.screen, step.id)
        journal.reached(step.screen)

        if step.effect.kind is EffectClass.COMMIT:
            if journal.already_done(step.id):
                run.reports.append(StepReport(step_id=step.id, status="already_done"))
                return
            if journal.in_doubt(step.id):
                raise HandrailError(
                    f"{step.id} was started before and never confirmed; it will not be repeated",
                    ErrorCode.UNSAFE_TO_RETRY,
                    step.id,
                )

        resolution: Resolution | None = None
        if step.target is not None:
            try:
                target = bind_target(capability.targets[step.target], params, self.env)
                resolution = await self.surface.resolve(target, self.settle_timeout_ms)
            except HandrailError as exc:
                raise HandrailError(exc.message, exc.code, step.id) from exc
            run.drift.steps_resolved += 1
            if resolution.rung == capability.targets[step.target].ladder[0].rung:
                run.drift.first_choice += 1

        value = bind_text(step.op.value, params, self.env) if step.op.value else None
        if step.effect.is_mutating:
            journal.dispatch(step.id)  # on disk before the surface is touched
        result = await self.surface.act(resolution, step.op.verb, value)
        if step.op.verb == "read" and result.value is not None:
            run.read_values[step.id] = result.value

        settled = await screens.settled(
            step, run.params, self.settle_timeout_ms, self.poll_interval_s
        )
        if not settled:
            raise HandrailError(
                f"{step.settle.kind} never came true after {step.id}", ErrorCode.SLOW_LOAD, step.id
            )
        if step.effect.is_mutating:
            journal.observe(step.id)

        if step.expect is not None:
            seen = await screens.name(step.expect.screen_in, step.id)
            if seen not in step.expect.screen_in:
                raise HandrailError(
                    f"after {step.id} expected one of {step.expect.screen_in}, saw {seen!r}",
                    ErrorCode.SCREEN_MISMATCH,
                    step.id,
                )
            screens.finish_if_outcome(seen)

        run.reports.append(
            StepReport(
                step_id=step.id,
                status="ok",
                rung=resolution.rung if resolution else None,
                rung_cost=resolution.rung_cost if resolution else None,
            )
        )
        self.recorder.log("step.ok", step=step.id, ms=int((time.monotonic() - clock) * 1000))
