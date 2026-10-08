"""Rung two: the scout is sent, and believed only after the furniture agrees."""

from __future__ import annotations

from typing import Any

from ...escalate.bridge import Bridge
from ...kernel.episodes import Episodes
from ...kernel.evidence import Recorder
from ...kernel.signature import jaccard, take
from ...schema.capability import Capability
from ...surface.base import Surface
from .one import RECHECK


class RungTwo:
    """The scout. Sent only after rung one; believed only after the furniture agrees."""

    def __init__(
        self,
        bridge: Bridge,
        surface: Surface,
        recorder: Recorder,
        capability: Capability,
        episodes: Episodes | None = None,
    ) -> None:
        self.bridge = bridge
        self.surface = surface
        self.recorder = recorder
        self.capability = capability
        self.episodes = episodes
        self.model_calls = 0
        self.crossings = 0
        #: page furniture -> what a crossing named for it; a scout is sent once per screen.
        self._memo: dict[str, str | None] = {}

    async def screen(
        self,
        candidates: list[str],
        inputs: dict[str, Any],
        env: dict[str, str],
        step_id: str | None,
    ) -> str | None:
        before = await self.surface.observe()
        key = take(before.structure).value
        if key in self._memo:
            named = self._memo[key]
            return named if named in candidates else None
        self.crossings += 1
        crossing = await self.bridge.cross(
            self.surface, self.capability, candidates, inputs, env, step_id
        )
        self.model_calls += crossing.model_calls
        named, overlap = crossing.named, 0.0
        forward = named in candidates  # a landmark behind the cook is not a crossing
        after = await self.surface.observe()
        if forward and named is not None:
            stored = self.capability.screens[named].paths
            overlap = jaccard(after.structure, stored) if stored else 0.0
        held = forward and overlap >= RECHECK
        self._memo[key] = named if held else None
        if held and named is not None:
            # The page the scout left us on is that screen too, from now on.
            self._memo[take(after.structure).value] = named
        self.recorder.log(
            "rung2.screen",
            step=step_id,
            named=named,
            forward=forward,
            overlap=round(overlap, 3),
            model_calls=crossing.model_calls,
            turns=crossing.turns,
            accepted=held,
        )
        if self.episodes is not None:
            self.episodes.record(
                run_id=self.recorder.run_id,
                capability=self.capability.ref,
                failed="screen",
                rung=2,
                step_id=step_id,
                question="bridge",
                backend=self.bridge.name,
                chosen=named,
                confidence=1.0 if named else 0.0,
                margin=0.0,
                probabilities={named: 1.0} if named else {},
                accepted=held,
            )
        return named if held else None
