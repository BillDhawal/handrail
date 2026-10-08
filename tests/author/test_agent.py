"""The guest is seated with three lines on the card, and the card is the whole vocabulary."""

from __future__ import annotations

import itertools
from collections.abc import Iterator

import pytest

pytest.importorskip("langchain")

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from handrail.author.agent import author, build_tools, opening_message  # noqa: E402
from handrail.author.middleware import Decision, Guard, MemorySink  # noqa: E402
from handrail.author.tools import Session  # noqa: E402
from handrail.schema.effects import EffectClass  # noqa: E402

from .test_middleware import AuthorableCounter, Owner  # noqa: E402


class Scripted(GenericFakeChatModel):
    """Says exactly what the test wrote, one message per model call."""

    def bind_tools(self, tools, **kwargs):  # type: ignore[no-untyped-def]
        return self


_ids = itertools.count(1)


def call(name: str, **args: object) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"c{next(_ids)}"}])


def scripted(*messages: AIMessage) -> Scripted:
    script: Iterator[AIMessage] = iter([*messages, AIMessage(content="done")])
    return Scripted(messages=script)


async def guard() -> tuple[Guard, AuthorableCounter, MemorySink]:
    surface = AuthorableCounter()
    session = Session(surface, inputs={"member_number": "400118", "password": "hunter2"})
    sink = MemorySink()
    owner = Owner(Decision(EffectClass.COMMIT, "dhawal"))
    return Guard(session, surface, owner, sink), surface, sink


def test_the_card_has_exactly_three_lines():
    g = Guard(Session(AuthorableCounter()), AuthorableCounter(), Owner(Decision(None, "x")))
    assert [t.name for t in build_tools(g)] == ["act", "assert_screen", "finish"]


def test_the_opening_names_the_blanks_but_never_the_values():
    text = opening_message("place a hold", ["member_number", "password"], "1: invoke button 'Go'")
    assert "{{input.password}}" in text and "{{input.member_number}}" in text
    assert "hunter2" not in text and "400118" not in text


async def test_a_scripted_evening_runs_the_guard_and_ends_on_finish():
    g, surface, sink = await guard()
    model = scripted(
        call("assert_screen", label="inquiry"),
        call("act", index=1, verb="set_value", value="{{input.member_number}}"),
        call("act", index=3, verb="invoke"),
        call("assert_screen", label="posted"),
        call("finish", outcome="posted"),
    )
    result = await author(model, g, "place a hold")
    assert result.finished and result.outcome == "posted"
    assert surface.acts == [("set_value", "h-member", "400118"), ("invoke", "h-search", None)]
    tools_used = [t.tool for t in sink.turns]
    assert tools_used == ["assert_screen", "act", "act", "assert_screen", "finish"]
    assert result.model_calls == 6  # five tool calls and the closing word


async def test_a_refusal_reaches_the_model_as_text_and_the_evening_goes_on():
    g, surface, _ = await guard()
    model = scripted(
        call("assert_screen", label="inquiry"),
        call("act", index=9, verb="invoke"),  # not on the menu
        call("act", index=3, verb="invoke"),
        call("assert_screen", label="posted"),
        call("finish", outcome="posted"),
    )
    result = await author(model, g, "place a hold")
    refusals = [m.content for m in result.messages if getattr(m, "type", "") == "tool"]
    assert any(str(c).startswith("refused: 9 is not on the menu") for c in refusals)
    assert result.finished and surface.acts == [("invoke", "h-search", None)]


async def test_an_evening_that_never_finishes_stops_at_the_turn_limit():
    g, _, _ = await guard()
    model = scripted(*[call("assert_screen", label="inquiry") for _ in range(50)])
    result = await author(model, g, "dither", max_turns=3)
    assert not result.finished and result.outcome is None
    assert len(result.trace) <= 4
