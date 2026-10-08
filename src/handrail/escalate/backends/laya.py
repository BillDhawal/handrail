"""The colleague at the next desk: not the sharpest, but nothing leaves the room.

Laya is an Apache-2.0, on-device decision model (``convaiinnovations/laya``
on Hugging Face). It runs under a gigabyte on Apple Silicon and the screen
text never leaves the machine, which is the whole point for a bank. It gets
shaky above about twenty options, so it serves the small questions: which of
these screens, is this a dialog, has the session expired. The long
``which_control`` menu goes to Jev when Jev is reachable.

The checkpoint is downloaded on first use. Unverified on this machine: the
disk was full when the download was attempted, so the call shape follows the
library's own ``decide`` signature and nothing more is claimed.
"""

from __future__ import annotations

from typing import Any

from ..classifier import ClassifierUnavailable, normalise
from ..questions import Question, Verdict

MAX_OPTIONS = 20


def to_question(question: Question) -> dict[str, Any]:
    return {
        question.name: {
            "type": "single_choice",
            "question": question.prompt,
            "options": list(question.options),
        }
    }


class LayaClassifier:
    name = "laya"

    def __init__(self, agent: Any = None, model: str = "convaiinnovations/laya") -> None:
        self._agent = agent
        self.model = model

    def _runner(self) -> Any:
        if self._agent is None:
            try:
                import laya  # type: ignore[import-not-found]

                self._agent = laya.Agent(self.model)
            except Exception as exc:  # noqa: BLE001 - cannot load means no referee
                raise ClassifierUnavailable(f"laya: {type(exc).__name__}: {exc}") from exc
        return self._agent

    async def ask(self, state: str, question: Question) -> Verdict:
        if len(question.options) > MAX_OPTIONS:
            raise ClassifierUnavailable(f"laya: {len(question.options)} options is too many")
        try:
            import laya

            details = laya.decide(
                self._runner(), state, questions=to_question(question), return_details=True
            )
            raw = dict(details.probabilities[question.name])
        except ClassifierUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ClassifierUnavailable(f"laya: {type(exc).__name__}: {exc}") from exc
        return normalise(question, {k: float(v) for k, v in raw.items()})
