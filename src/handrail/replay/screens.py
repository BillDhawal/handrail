"""Which counter am I standing at? Exact, then similar, then ask the referee, then say so.

The cook looks at the counter before every step and after the ones that are
supposed to move. Naming it is tiered: the furniture matches exactly; or it
matches closely enough that one moved chair does not count; or, when a
referee was handed in and there is a short list of counters it could be, the
referee is asked and the answer is checked against the furniture; or, when a
scout was handed in too, the scout is sent and its report is checked the same
way. If none of that names it, the raw signature is returned, and the caller
decides what that means: a mismatch, or an outcome the application reached early.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..kernel.evidence import Recorder
from ..kernel.signature import match, take
from ..schema.bindings import bind_target
from ..schema.capability import Capability, Step
from ..schema.errors import ErrorCode, HandrailError, OutcomeCategory
from ..surface.base import Surface
from .rungs import RungOne, RungThree, RungTwo


class Finished(Exception):
    """The run reached an outcome screen; raised to unwind the step loop cleanly."""

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome


class Screens:
    def __init__(
        self,
        surface: Surface,
        recorder: Recorder,
        capability: Capability,
        rung1: RungOne | None,
        rung2: RungTwo | None = None,
        rung3: RungThree | None = None,
    ) -> None:
        self.surface = surface
        self.recorder = recorder
        self.capability = capability
        self.rung1 = rung1
        self.rung2 = rung2
        self.rung3 = rung3
        self.inputs: dict[str, Any] = {}
        self.env: dict[str, str] = {}

    async def name(self, candidates: list[str], step_id: str | None) -> str:
        """The screen's label, or its raw signature if it is none we know."""
        observation = await self.surface.observe()
        screens = self.capability.screens
        found = match(
            observation.structure, {n: (scr.signature, scr.paths) for n, scr in screens.items()}
        )
        if found.tier == "similar":
            self.recorder.log("screen.similar", screen=found.label, score=round(found.score, 3))
        if found.label:
            return found.label
        if self.rung1 is not None and candidates:
            named = await self.rung1.screen(observation, candidates, step_id)
            if named is not None:
                return named
        if self.rung2 is not None and candidates:
            named = await self.rung2.screen(candidates, self.inputs, self.env, step_id)
            if named is not None:
                return named
        if self.rung3 is not None and candidates:
            named = await self.rung3.screen(self.surface, candidates, step_id)
            if self.rung3.baton.aborted:
                raise HandrailError(
                    "aborted at the console", ErrorCode.ABORTED_BY_OPERATOR, step_id
                )
            if named is not None:
                return named
        return take(observation.structure).value

    async def expect(self, expected: str, step_id: str) -> None:
        """The step's precondition. An outcome reached early ends the run instead."""
        seen = await self.name([expected, *self.capability.outcomes], step_id)
        if seen == expected:
            return
        self.finish_if_outcome(seen)
        raise HandrailError(
            f"step {step_id} needs screen {expected!r}, but the application shows {seen!r}",
            ErrorCode.SCREEN_MISMATCH,
            step_id,
        )

    def finish_if_outcome(self, seen: str) -> None:
        declared = self.capability.outcomes.get(seen)
        if declared is not None and declared.category is not OutcomeCategory.SUCCESS:
            raise Finished(seen)

    async def settled(
        self, step: Step, params: dict[str, Any], timeout_ms: int, poll_s: float
    ) -> bool:
        """Poll the settle condition deterministically; at the deadline, one word from the referee.

        A referee is asked once, not on every poll.
        """
        capability, s, screens = self.capability, step.settle, self
        if s.kind == "target_present":
            nxt = capability.step(s.step or step.id)
            target = bind_target(capability.targets[nxt.target or ""], params, self.env)
            condition = f"target_present:{target.name.eq if target.name else target.role}"
        elif s.kind == "screen_is":
            condition = f"screen:{s.screen or step.screen}"
        else:
            condition = "keyboard_unlocked"
        deadline = time.monotonic() + timeout_ms / 1000
        while True:
            if condition.startswith("screen:"):
                settled = await screens.name([], None) == condition[len("screen:") :]
            else:
                settled = await self.surface.evaluate(condition)
            if settled:
                return True
            if time.monotonic() >= deadline:
                break
            await asyncio.sleep(poll_s)
        if condition.startswith("screen:"):
            wanted = condition[len("screen:") :]
            return await screens.name([wanted], step.id) == wanted
        return False
