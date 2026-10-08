"""Which counter am I standing at? Exact, then similar, then ask the referee, then say so.

The cook looks at the counter before every step and after the ones that are
supposed to move. Naming it is tiered: the furniture matches exactly; or it
matches closely enough that one moved chair does not count; or, when a
referee was handed in and there is a short list of counters it could be, the
referee is asked and the answer is checked against the furniture. If none of
that names it, the raw signature is returned, and the caller decides what
that means: a mismatch, or an outcome the application reached early.
"""

from __future__ import annotations

from ..kernel.evidence import Recorder
from ..kernel.signature import match, take
from ..schema.capability import Capability
from ..schema.errors import ErrorCode, HandrailError, OutcomeCategory
from ..surface.base import Surface
from .rungs import RungOne


class Finished(Exception):
    """The run reached an outcome screen; raised to unwind the step loop cleanly."""

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome


class Screens:
    def __init__(
        self, surface: Surface, recorder: Recorder, capability: Capability, rung1: RungOne | None
    ) -> None:
        self.surface = surface
        self.recorder = recorder
        self.capability = capability
        self.rung1 = rung1

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
