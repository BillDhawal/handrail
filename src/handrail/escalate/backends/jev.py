"""The expert at the call centre: accurate, takes a long list, but the text leaves the building.

Jev is TypeSafe's hosted classifier, reached through their SDK. It is the
accurate referee (JevBench rank 1) and it takes up to 255 options, which the
``which_control`` question needs on a long menu. The model is pinned so a
verdict today and a verdict next year come from the same referee, and the
thresholds on the card were tuned against it.

Two things never change here. Only text goes out, never a screenshot. And
until TypeSafe's data retention outside an enterprise agreement is known,
the state handed over must already be redacted; this file does not redact,
the recorder's masking does, so pass it masked text.

Unverified against the live service: there is no TYPESAFE_API_KEY in this
repository yet. The request shape follows the SDK's own types.
"""

from __future__ import annotations

import os
from typing import Any

from ..classifier import ClassifierUnavailable, normalise
from ..questions import Question, Verdict

PINNED_MODEL = "jev-1.13.0"
STATE_LIMIT = 32_000


def to_choice(question: Question) -> dict[str, Any]:
    """The card as TypeSafe's `Choice` question: criteria is option -> hint."""
    return {
        "type": "choice",
        "instructions": question.prompt,
        "criteria": {opt: hint or opt for opt, hint in question.options.items()},
    }


class JevClassifier:
    name = "jev"

    def __init__(self, api_key: str | None = None, model: str = PINNED_MODEL, client: Any = None):
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        self.model = model
        self._client = client

    def _sdk(self) -> Any:
        if self._client is None:
            if not self.api_key:
                raise ClassifierUnavailable("jev: no TYPESAFE_API_KEY")
            from typesafe_sdk import AsyncTypeSafeClient  # type: ignore[import-not-found]

            self._client = AsyncTypeSafeClient(api_key=self.api_key, model=self.model)
        return self._client

    async def ask(self, state: str, question: Question) -> Verdict:
        try:
            response = await self._sdk().system_one(
                state[:STATE_LIMIT], {question.name: to_choice(question)}, model=self.model
            )
            answer = response.answers[question.name]
            raw = dict(answer.probabilities)
        except ClassifierUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - no referee, never a guess
            raise ClassifierUnavailable(f"jev: {type(exc).__name__}: {exc}") from exc
        return normalise(question, raw)
