"""Each backend turns the card into its own question shape and never lets a bad answer through."""

from __future__ import annotations

import pytest

from handrail.escalate.backends.jev import JevClassifier, to_choice
from handrail.escalate.backends.laya import LayaClassifier, to_question
from handrail.escalate.classifier import ClassifierUnavailable
from handrail.escalate.questions import NONE, which_screen

Q = which_screen({"posted": "the hold was posted", "held": "already under hold"})


def test_jev_asks_a_choice_question_with_the_cards_hints_as_criteria():
    assert to_choice(Q) == {
        "type": "choice",
        "instructions": Q.prompt,
        "criteria": {
            "posted": "the hold was posted",
            "held": "already under hold",
            NONE: "none of the above",
        },
    }


def test_laya_asks_a_single_choice_question_with_the_cards_options():
    assert to_question(Q)[Q.name]["options"] == ["posted", "held", NONE]


async def test_jev_without_a_key_is_unavailable_not_a_guess(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(ClassifierUnavailable, match="no TYPESAFE_API_KEY"):
        await JevClassifier().ask("HOLD POSTED", Q)


async def test_jev_normalises_the_answer_it_is_given():
    class Answer:
        probabilities = {"posted": 0.8, "held": 0.1, NONE: 0.1}

    class Response:
        answers = {Q.name: Answer()}

    class Fake:
        async def system_one(self, state, questions, model=None):
            assert questions[Q.name]["type"] == "choice" and model == "jev-1.13.0"
            return Response()

    verdict = await JevClassifier(api_key="k", client=Fake()).ask("HOLD POSTED", Q)
    assert verdict.chosen == "posted" and verdict.accepted_by(Q)


async def test_laya_refuses_a_menu_longer_than_it_can_handle():
    from handrail.escalate.questions import which_control

    rows = [(i, "invoke", "link", f"row {i}") for i in range(30)]
    with pytest.raises(ClassifierUnavailable, match="too many"):
        await LayaClassifier(agent=object()).ask("x", which_control(rows, "anything"))


async def test_claude_numbers_the_options_so_labels_with_spaces_make_a_valid_sheet():
    from handrail.escalate.backends.claude import ClaudeClassifier

    seen: dict = {}

    class Sheet:
        def __init__(self, cls):
            self.cls = cls

        async def ainvoke(self, prompt):
            seen["fields"] = list(self.cls.model_fields)
            seen["prompt"] = prompt
            return self.cls(option_1=0.9, option_2=0.05, option_3=0.05)

    class Model:
        def with_structured_output(self, cls):
            return Sheet(cls)

    q = which_screen({"Hold Result": "the result", "Member Record": "the record"})
    verdict = await ClaudeClassifier(model=Model()).ask("HOLD POSTED", q)
    assert seen["fields"] == ["option_1", "option_2", "option_3"]  # identifiers, not labels
    assert "option_1 = Hold Result" in seen["prompt"]
    assert verdict.chosen == "Hold Result" and verdict.accepted_by(q)
