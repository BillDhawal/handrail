"""A model asked a multiple-choice question with the answer sheet enforced.

Not the accurate referee (that is Jev) and not the private one (Laya); the
one that is always reachable with the key we already have. The model is told
the card and must fill in one probability per option through a structured
answer, so free text never reaches the engine. Cheap and fast enough for a
rung that fires only when a deterministic check has already failed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, create_model

from ..classifier import ClassifierUnavailable, normalise
from ..questions import Question, Verdict

DEFAULT_MODEL = "anthropic:claude-haiku-4-5-20251001"
STATE_LIMIT = 12_000  # characters of screen text handed over; more is noise


class ClaudeClassifier:
    name = "claude"

    def __init__(self, model: Any = None, model_name: str = DEFAULT_MODEL) -> None:
        self._model = model
        self.model_name = model_name

    def _chat(self) -> Any:
        if self._model is None:
            from langchain.chat_models import init_chat_model

            self._model = init_chat_model(self.model_name, temperature=0)
        return self._model

    async def ask(self, state: str, question: Question) -> Verdict:
        # Option labels are free text ("Hold Result"); the answer sheet's keys must be
        # identifiers. Number them on the way out and map back on the way in.
        keys = {f"option_{i}": opt for i, opt in enumerate(question.options, 1)}
        fields: dict[str, Any] = {
            key: (float, Field(ge=0, le=1, description=f"{opt}: {question.options[opt]}"))
            for key, opt in keys.items()
        }
        sheet: type[BaseModel] = create_model("AnswerSheet", **fields)
        card = "\n".join(f"- {key} = {opt}: {question.options[opt]}" for key, opt in keys.items())
        prompt = (
            f"{question.prompt}\nOptions:\n{card}\n\n"
            "Give a probability for every option; they should sum to 1.\n\n"
            f"Screen text:\n{state[:STATE_LIMIT]}"
        )
        try:
            answer = await self._chat().with_structured_output(sheet).ainvoke(prompt)
        except Exception as exc:  # noqa: BLE001 - any failure here is "no referee", never a guess
            raise ClassifierUnavailable(f"claude: {type(exc).__name__}: {exc}") from exc
        raw = {keys[k]: v for k, v in answer.model_dump().items() if k in keys}
        return normalise(question, raw)
