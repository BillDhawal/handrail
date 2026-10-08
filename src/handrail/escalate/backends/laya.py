"""The colleague at the next desk: not the sharpest, but nothing leaves the room.

Laya is an Apache-2.0, on-device decision model (``convaiinnovations/laya``
on Hugging Face). It runs under a gigabyte on Apple Silicon and the screen
text never leaves the machine, which is the whole point for a bank. It gets
shaky above about twenty options, so it serves the small questions: which of
these screens, is this a dialog, has the session expired. The long
``which_control`` menu goes to Jev when Jev is reachable.

The checkpoint is downloaded on first use (about a minute; then each
question takes about a tenth of a second). Verified on 2026-10-08: posted at
0.88, already held at 0.91, the inquiry screen "none of these" at 0.65, and
an honest 0.46 on a reworded result line, which the card's threshold rejects.
That abstention is exactly what sends a run up to rung two.
"""

from __future__ import annotations

from typing import Any

from ..classifier import ClassifierUnavailable, normalise
from ..questions import Question, Verdict

MAX_OPTIONS = 20


def to_question(question: Question) -> dict[str, Any]:
    """Laya's `choice` question: criteria maps each option to its one-line hint."""
    return {
        question.name: {
            "type": "choice",
            "instructions": question.prompt,
            "criteria": {opt: hint or opt for opt, hint in question.options.items()},
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
                import laya

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
