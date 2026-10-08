"""The scout: the same card with commit struck off, a short leash, and only landmarks on the map."""

from __future__ import annotations

import pytest

pytest.importorskip("langchain")

from handrail.author.bridge import LangChainBridge, bridge_prompt  # noqa: E402
from handrail.escalate.questions import Verdict  # noqa: E402
from handrail.schema.capability import Capability  # noqa: E402

from ..factory import place_hold  # noqa: E402
from .test_agent import call, scripted  # noqa: E402
from .test_middleware import AuthorableCounter  # noqa: E402


def capability() -> Capability:
    cap = place_hold()
    cap["screens"]["inquiry"]["signature"] = "sig:form"
    cap["screens"]["posted"]["signature"] = "sig:result"
    return Capability.model_validate(cap)


class SaysNotCommit:
    name = "fake"

    async def ask(self, state, question):
        return Verdict(question.name, {"not_commit": 0.95, "commit": 0.05})


class SaysCommit(SaysNotCommit):
    async def ask(self, state, question):
        return Verdict(question.name, {"commit": 0.95, "not_commit": 0.05})


def test_the_scouts_orders_name_the_landmarks_and_the_blanks_only():
    text = bridge_prompt({"posted": "the hold was posted"}, "Place a hold", ["member_number"])
    assert "- posted: the hold was posted" in text and "{{input.member_number}}" in text
    assert "400118" not in text


async def test_the_scout_presses_a_harmless_button_and_names_the_landmark():
    surface = AuthorableCounter()
    model = scripted(call("act", index=3, verb="invoke"), call("finish", outcome="posted"))
    scout = LangChainBridge(model, surface, classifier=SaysNotCommit())
    crossing = await scout.cross(surface, capability(), ["posted", "already_held"], {}, {}, "s1")
    assert crossing.named == "posted" and crossing.model_calls == 3
    assert surface.acts == [("invoke", "h-search", None)]


async def test_a_button_the_referee_calls_a_commit_is_refused_and_the_scout_reports_nothing():
    surface = AuthorableCounter()
    model = scripted(call("act", index=3, verb="invoke"), call("finish", outcome="posted"))
    scout = LangChainBridge(model, surface, classifier=SaysCommit())
    crossing = await scout.cross(surface, capability(), ["posted"], {}, {}, "s1")
    assert surface.acts == []  # the press never happened
    # The scout still says "posted": lenient finish accepts any declared label. That is fine,
    # because the engine checks the furniture before believing a scout, never the scout's word.
    assert crossing.named == "posted"


async def test_without_a_referee_every_button_is_a_commit_to_the_scout():
    surface = AuthorableCounter()
    model = scripted(call("act", index=3, verb="invoke"))
    scout = LangChainBridge(model, surface)
    crossing = await scout.cross(surface, capability(), ["posted"], {}, {}, None)
    assert surface.acts == [] and crossing.named is None


async def test_the_scout_cannot_invent_a_landmark():
    surface = AuthorableCounter()
    model = scripted(call("finish", outcome="somewhere new"))
    scout = LangChainBridge(model, surface)
    crossing = await scout.cross(surface, capability(), ["posted"], {}, {}, None)
    assert crossing.named is None
