"""The referee's whistle: one method, one closed question, a probability per option.

The engine does not know whether the referee is a person at a desk (Jev,
hosted), a colleague in the room (Laya, on-device), or a model asked for a
constrained answer (Claude). It knows one thing: hand over the state and the
card, get back a number per option. That is the port.

Three rules that hold for every backend:

- Only options on the card come back, every one of them, summing to one. A
  backend that returns an option the card did not list is a bug, and
  ``normalise`` refuses it.
- The state is text the application showed. It is untrusted: it can steer the
  verdict. So the engine never lets a verdict stand in for a deterministic
  check; it re-checks every answer before acting on it.
- A backend that cannot answer raises ``ClassifierUnavailable``. The engine
  then climbs past the rung. A run with no referee reachable still finishes
  by refusing, never by guessing.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from .questions import Question, Verdict


class ClassifierUnavailable(RuntimeError):
    """The referee could not be reached or could not answer. Climb past this rung."""


class Classifier(Protocol):
    name: str

    async def ask(self, state: str, question: Question) -> Verdict: ...


def normalise(question: Question, raw: Mapping[str, float]) -> Verdict:
    """Every option on the card, nothing else, summing to one. Refuses anything else."""
    unknown = set(raw) - set(question.options)
    if unknown:
        raise ClassifierUnavailable(f"{question.name}: options not on the card: {sorted(unknown)}")
    scores = {opt: max(0.0, float(raw.get(opt, 0.0))) for opt in question.options}
    total = sum(scores.values())
    if total <= 0:
        raise ClassifierUnavailable(f"{question.name}: no probability mass")
    return Verdict(question.name, {k: v / total for k, v in scores.items()})
