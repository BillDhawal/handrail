"""Rung one: the referee is asked, and the engine checks the call before acting.

See the package docstring for the rules; this file is the first rung only.
"""

from __future__ import annotations

from ...escalate.classifier import Classifier, ClassifierUnavailable
from ...escalate.questions import which_screen
from ...kernel.episodes import Episodes
from ...kernel.evidence import Recorder
from ...kernel.signature import jaccard, take
from ...schema.capability import Capability
from ...surface.base import Observation

#: The chosen screen must share at least this much furniture with the page. Below the
#: "similar" tier on purpose: the referee narrows the question, the furniture confirms it.
RECHECK = 0.5


class RungOne:
    def __init__(
        self,
        classifier: Classifier,
        recorder: Recorder,
        capability: Capability,
        episodes: Episodes | None = None,
    ) -> None:
        self.classifier = classifier
        self.recorder = recorder
        self.capability = capability
        self.episodes = episodes
        self.calls = 0
        #: page furniture -> (the candidates asked about, what the referee named, or None)
        self._memo: dict[str, tuple[frozenset[str], str | None]] = {}

    async def screen(
        self, observation: Observation, candidates: list[str], step_id: str | None
    ) -> str | None:
        """Which of `candidates` is showing? The label, or None if nobody can say for sure."""
        key = take(observation.structure).value
        if key in self._memo:
            asked, named = self._memo[key]
            if named in candidates:
                return named  # the same page, named before, and still on the list
            if named is None and set(candidates) <= asked:
                return None  # already said "none of these" to a list at least this long
        named = await self._ask(observation, candidates, step_id)
        self._memo[key] = (frozenset(candidates), named)
        return named

    async def _ask(
        self, observation: Observation, candidates: list[str], step_id: str | None
    ) -> str | None:
        screens = self.capability.screens
        question = which_screen({c: screens[c].label for c in candidates if c in screens})
        self.calls += 1
        try:
            verdict = await self.classifier.ask(observation.text, question)
        except ClassifierUnavailable as exc:
            self.recorder.log("rung1.unavailable", step=step_id, why=str(exc))
            self._note(step_id, question.name, None, 0.0, 0.0, {}, accepted=False)
            return None
        accepted = verdict.accepted_by(question)
        overlap = 0.0
        if accepted:
            stored = screens[verdict.chosen].paths
            overlap = jaccard(observation.structure, stored) if stored else 0.0
        held = accepted and overlap >= RECHECK
        self.recorder.log(
            "rung1.screen",
            step=step_id,
            chosen=verdict.chosen,
            confidence=round(verdict.confidence, 3),
            margin=round(verdict.margin, 3),
            overlap=round(overlap, 3),
            accepted=held,
        )
        self._note(
            step_id,
            question.name,
            verdict.chosen,
            verdict.confidence,
            verdict.margin,
            dict(verdict.probabilities),
            accepted=held,
        )
        return verdict.chosen if held else None

    def _note(
        self,
        step_id: str | None,
        question: str,
        chosen: str | None,
        confidence: float,
        margin: float,
        probabilities: dict[str, float],
        accepted: bool,
    ) -> None:
        if self.episodes is None:
            return
        self.episodes.record(
            run_id=self.recorder.run_id,
            capability=self.capability.ref,
            failed="screen",
            rung=1,
            step_id=step_id,
            question=question,
            backend=self.classifier.name,
            chosen=chosen,
            confidence=confidence,
            margin=margin,
            probabilities=probabilities,
            accepted=accepted,
        )
