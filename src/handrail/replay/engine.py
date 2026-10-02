"""The replay engine: a cook following a recipe card, step by step, checking as it goes.

The recipe is the capability. The cook never improvises. Before every step it
checks it is standing at the right counter (the screen matches), finds the one
utensil the step names (resolve), writes "starting step" in the ledger if the
step changes anything (journal), does the step (act), waits for the visible
sign that it landed (settle), writes "done" in the ledger (journal again), and
checks the counter it expected to end up at (expect). If any check fails it
stops and says exactly which check, on which step, expected what, saw what.

No model is consulted anywhere in this file. The two counters in the result,
``classifier_calls`` and ``llm_calls``, are zero for every run that goes
through here, and an import guard makes sure this package cannot reach one.

The one rule the cook will not break, even if told to: a commit written as
"starting" in the ledger with no "done" beside it is never repeated. It is
refused with UNSAFE_TO_RETRY, and finding out what happened is somebody else's
job - a read-only probe in a later milestone, or a person. A stage step is
different: re-typing a field or re-selecting an option is harmless by
definition, so on a resumed run a stage is simply done again.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from ..kernel.evidence import Recorder
from ..schema.bindings import BindingError, bind_target, bind_text
from ..schema.capability import Capability, Step
from ..schema.effects import EffectClass
from ..schema.errors import ErrorCode, HandrailError, OutcomeCategory
from ..schema.results import Drift, ErrorDetail, RunResult, StepReport
from ..surface.base import Observation, Resolution, Surface
from .journal import Journal
from .validate import validate_inputs

DEFAULT_SETTLE_TIMEOUT_MS = 8000


def observed_signature(observation: Observation) -> str:
    """Milestone 1: the surface's structure joined. Milestone 5 replaces this."""
    return "|".join(observation.structure)


class _Finished(Exception):
    """The run reached an outcome screen; raised to unwind the step loop cleanly."""

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome


class ReplayEngine:
    def __init__(
        self,
        surface: Surface,
        recorder: Recorder,
        env: Mapping[str, str] | None = None,
        poll_interval_s: float = 0.25,
        settle_timeout_ms: int = DEFAULT_SETTLE_TIMEOUT_MS,
    ) -> None:
        self.surface = surface
        self.recorder = recorder
        self.env = dict(env or {})
        self.poll_interval_s = poll_interval_s
        self.settle_timeout_ms = settle_timeout_ms

    async def run(
        self, capability: Capability, inputs: dict[str, Any], journal: Journal | None = None
    ) -> RunResult:
        started, clock = datetime.now(UTC), time.monotonic()
        # Per-run state lives here, not on self, so a reused engine cannot mix two runs.
        journal = journal or Journal()
        reports: list[StepReport] = []
        drift = Drift()
        read_values: dict[str, str] = {}
        outcome: str | None = None
        error: ErrorDetail | None = None

        def finish(category: OutcomeCategory, code: ErrorCode) -> RunResult:
            outputs = self._outputs(capability, outcome, read_values) if outcome else {}
            result = RunResult(
                run_id=self.recorder.run_id,
                capability_id=capability.id,
                capability_version=capability.version,
                started_at=started.isoformat(),
                duration_ms=int((time.monotonic() - clock) * 1000),
                category=category,
                code=code,
                outcome=outcome,
                outputs=outputs,
                error=error,
                steps=reports,
                drift=drift,
            )
            self.recorder.write_json("result.json", result)
            self.recorder.log("replay.finish", category=category.value, code=code.value)
            return result

        try:
            params = self._prepare(capability, inputs)
            await self.surface.open(bind_text(capability.surface.entry, params, self.env))
            for step in capability.steps:
                await self._run_step(capability, step, params, journal, reports, drift, read_values)
            final = await self._screen(capability)
            if final not in capability.outcomes:
                raise HandrailError(
                    f"the run ended on {final!r}, which is not an outcome",
                    ErrorCode.SCREEN_MISMATCH,
                )
            raise _Finished(final)
        except _Finished as done:
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

    def _prepare(self, capability: Capability, inputs: dict[str, Any]) -> dict[str, Any]:
        if self.surface.kind not in ("null", capability.surface.kind):
            raise HandrailError(
                f"capability needs a {capability.surface.kind} surface, got {self.surface.kind}",
                ErrorCode.SURFACE_INCOMPATIBLE,
            )
        params = validate_inputs(capability, inputs)
        for spec in capability.inputs:
            if spec.sensitivity == "secret" and spec.name in params:
                self.recorder.add_secret(str(params[spec.name]))
        try:
            entry = bind_text(capability.surface.entry, params, self.env)
        except BindingError as exc:
            raise HandrailError(str(exc), ErrorCode.INVALID_INPUT) from exc
        self.recorder.log("replay.start", capability=capability.ref, entry=entry, inputs=params)
        return params

    # -- one step -----------------------------------------------------------------

    async def _run_step(
        self,
        capability: Capability,
        step: Step,
        params: dict[str, Any],
        journal: Journal,
        reports: list[StepReport],
        drift: Drift,
        read_values: dict[str, str],
    ) -> None:
        clock = time.monotonic()
        self.recorder.log("step.start", step=step.id, verb=step.op.verb, effect=step.effect.kind)

        await self._expect_screen(capability, step.screen, step.id)
        journal.reached(step.screen)

        if step.effect.kind is EffectClass.COMMIT:
            if journal.already_done(step.id):
                reports.append(StepReport(step_id=step.id, status="already_done"))
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
            drift.steps_resolved += 1
            if resolution.rung == capability.targets[step.target].ladder[0].rung:
                drift.first_choice += 1

        value = bind_text(step.op.value, params, self.env) if step.op.value else None
        if step.effect.is_mutating:
            journal.dispatch(step.id)  # on disk before the surface is touched
        result = await self.surface.act(resolution, step.op.verb, value)
        if step.op.verb == "read" and result.value is not None:
            read_values[step.id] = result.value

        if not await self._settled(capability, step, params):
            raise HandrailError(
                f"{step.settle.kind} never came true after {step.id}", ErrorCode.SLOW_LOAD, step.id
            )
        if step.effect.is_mutating:
            journal.observe(step.id)

        if step.expect is not None:
            seen = await self._screen(capability)
            if seen not in step.expect.screen_in:
                raise HandrailError(
                    f"after {step.id} expected one of {step.expect.screen_in}, saw {seen!r}",
                    ErrorCode.SCREEN_MISMATCH,
                    step.id,
                )
            self._finish_if_outcome(capability, seen)

        reports.append(
            StepReport(
                step_id=step.id,
                status="ok",
                rung=resolution.rung if resolution else None,
                rung_cost=resolution.rung_cost if resolution else None,
            )
        )
        self.recorder.log("step.ok", step=step.id, ms=int((time.monotonic() - clock) * 1000))

    # -- screens ------------------------------------------------------------------

    async def _screen(self, capability: Capability) -> str:
        """Name the screen we are on, or return the raw signature if it is none we know."""
        sig = observed_signature(await self.surface.observe())
        for name, screen in capability.screens.items():
            if screen.signature == sig:
                return name
        return sig

    async def _expect_screen(self, capability: Capability, expected: str, step_id: str) -> None:
        seen = await self._screen(capability)
        if seen == expected:
            return
        # The application may have answered early: "already held" instead of the form.
        self._finish_if_outcome(capability, seen)
        raise HandrailError(
            f"step {step_id} needs screen {expected!r}, but the application shows {seen!r}",
            ErrorCode.SCREEN_MISMATCH,
            step_id,
        )

    def _finish_if_outcome(self, capability: Capability, seen: str) -> None:
        declared = capability.outcomes.get(seen)
        if declared is not None and declared.category is not OutcomeCategory.SUCCESS:
            raise _Finished(seen)

    async def _settled(self, capability: Capability, step: Step, params: dict[str, Any]) -> bool:
        s = step.settle
        if s.kind == "target_present":
            nxt = capability.step(s.step or step.id)
            target = bind_target(capability.targets[nxt.target or ""], params, self.env)
            condition = f"target_present:{target.name.eq if target.name else target.role}"
        elif s.kind == "screen_is":
            condition = f"screen_is:{capability.screens[s.screen or step.screen].signature}"
        else:
            condition = "keyboard_unlocked"
        deadline = time.monotonic() + self.settle_timeout_ms / 1000
        while True:
            if await self.surface.evaluate(condition):
                return True
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(self.poll_interval_s)

    # -- outputs ------------------------------------------------------------------

    @staticmethod
    def _outputs(
        capability: Capability, outcome: str, read_values: dict[str, str]
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for spec in capability.outputs:
            if spec.produced_on and outcome not in spec.produced_on:
                continue
            raw = read_values.get(spec.source.step)
            if raw is None:
                continue
            if spec.source.extract:
                found = re.search(spec.source.extract, raw)
                out[spec.name] = found.group(1) if found else None
            else:
                out[spec.name] = raw
        return out
