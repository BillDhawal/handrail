"""Rung three: a person on the same live session. The baton changes hands; the engine waits."""

from __future__ import annotations

from typing import Any

from ...kernel.control import Baton
from ...kernel.episodes import Episodes
from ...kernel.evidence import Recorder
from ...kernel.signature import take
from ...schema.capability import Capability
from ...surface.base import Surface


class RungThree:
    """A person on the same live session. The baton is handed over; the engine waits.

    The person's word is final: whoever holds the baton may act, and when they hand it
    back naming a screen, that is the screen. It is recorded, not re-checked. What is
    checked is that the name is one the run was hoping for: a person cannot hand back
    "inquiry" after the hold was posted, because that would move the run backwards.
    """

    def __init__(
        self,
        console: Any,
        recorder: Recorder,
        capability: Capability,
        episodes: Episodes | None = None,
        wait_s: float | None = None,
    ) -> None:
        self.console = console
        self.baton: Baton = console.baton
        self.recorder = recorder
        self.capability = capability
        self.episodes = episodes
        self.wait_s = wait_s
        self.escalations = 0
        #: page furniture -> what a person said it was; nobody is asked twice about one page.
        self._memo: dict[str, str | None] = {}

    async def screen(
        self, surface: Surface, candidates: list[str], step_id: str | None
    ) -> str | None:
        before = await surface.observe()
        key = take(before.structure).value
        if key in self._memo:
            named = self._memo[key]
            return named if named in candidates else None
        self.escalations += 1
        self.console.offer(candidates)
        self.baton.exchange("pause", "engine", f"could not name the screen at {step_id}")
        await self.recorder.capture(surface, f"human_before_{step_id or 'end'}")
        self.recorder.log(
            "rung3.paused", step=step_id, console=self.console.url, expected=candidates
        )
        resumed = await self.baton.wait_until_automation_may_act(self.wait_s)
        await self.recorder.capture(surface, f"human_after_{step_id or 'end'}")
        named = self.console.handed_back if resumed else None
        held = named in candidates
        self._memo[key] = named if held else None
        if held:
            after = await surface.observe()
            self._memo[take(after.structure).value] = named
        self.recorder.log(
            "rung3.handed_back",
            step=step_id,
            named=named,
            by=self.baton.history[-1].by if self.baton.history else None,
            aborted=self.baton.aborted,
            accepted=held,
        )
        if self.episodes is not None:
            self.episodes.record(
                run_id=self.recorder.run_id,
                capability=self.capability.ref,
                failed="screen",
                rung=3,
                step_id=step_id,
                question="hand_back",
                backend="human",
                chosen=named,
                confidence=1.0 if named else 0.0,
                margin=0.0,
                probabilities={named: 1.0} if named else {},
                accepted=held,
            )
        return named if held else None
