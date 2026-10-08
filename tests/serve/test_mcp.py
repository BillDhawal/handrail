"""One line on the menu per approved card, no password on it, and a receipt an agent can read."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp")

from handrail.compile.approve import approve  # noqa: E402
from handrail.schema.capability import Capability  # noqa: E402
from handrail.schema.errors import ErrorCode, OutcomeCategory  # noqa: E402
from handrail.schema.results import ErrorDetail, RunResult  # noqa: E402
from handrail.serve.mcp import build_server, load_cards, receipt, tool_name  # noqa: E402

from ..compile.test_approve import verified  # noqa: E402


def with_secret() -> Capability:
    cap = verified().model_dump()
    cap["inputs"].append({"name": "password", "sensitivity": "secret"})
    return approve(Capability.model_validate(cap), "dhawal")


def result(
    category: OutcomeCategory, code: ErrorCode, outcome: str | None = None, **outputs: Any
) -> RunResult:
    error = None
    if category in (OutcomeCategory.RECOVERABLE, OutcomeCategory.HARD_FAILURE):
        error = ErrorDetail(code=code, message="it broke", step_id="post_hold")
    return RunResult(
        run_id="run_x", capability_id="bank.place_hold", capability_version="1.0.0",
        started_at="now", duration_ms=1, category=category, code=code, outcome=outcome,
        outputs=outputs, error=error,
    )  # fmt: skip


class Kitchen:
    """A runner that returns what the test says and remembers every order."""

    def __init__(self, answer: RunResult) -> None:
        self.answer, self.orders = answer, []

    async def __call__(self, capability: Capability, inputs: dict[str, Any]) -> RunResult:
        self.orders.append(inputs)
        return self.answer


def test_only_approved_cards_are_served_and_the_others_are_named(tmp_path: Path):
    (tmp_path / "draft.json").write_text(
        Capability.model_validate(
            __import__("tests.factory", fromlist=["place_hold"]).place_hold()
        ).model_dump_json()
    )
    (tmp_path / "verified.json").write_text(verified().model_dump_json())
    (tmp_path / "approved.json").write_text(approve(verified(), "dhawal").model_dump_json())
    (tmp_path / "junk.json").write_text("{}")
    said: list[str] = []
    cards = load_cards(tmp_path, said.append)
    assert [c.id for c in cards] == ["bank.place_hold"]
    assert any("verified, not approved" in s for s in said) and any("draft" in s for s in said)
    assert any("junk.json: not a capability" in s for s in said)


async def test_the_tool_schema_is_the_cards_public_inputs_and_never_the_password():
    server = build_server(
        [with_secret()], Kitchen(result(OutcomeCategory.SUCCESS, ErrorCode.NONE, "posted")), {}
    )
    (tool,) = await server.list_tools()
    assert tool.name == tool_name(with_secret()) == "bank_place_hold"
    props = tool.inputSchema["properties"]
    assert set(props) == {"member_number", "reason"}
    assert props["reason"]["enum"] == ["LEGAL", "FRAUD_REVIEW"]
    assert "password" not in json.dumps(tool.inputSchema)


async def test_a_missing_secret_is_a_typed_refusal_and_nothing_is_touched():
    kitchen = Kitchen(result(OutcomeCategory.SUCCESS, ErrorCode.NONE, "posted"))
    server = build_server([with_secret()], kitchen, {})
    out = await server.call_tool("bank_place_hold", {"member_number": "400118", "reason": "LEGAL"})
    answer = json.loads(out[0].text)
    assert (answer["category"], answer["code"], answer["retryable"]) == (
        "HARD_FAILURE",
        "INVALID_INPUT",
        False,
    )
    assert "password" in answer["error"] and kitchen.orders == []


async def test_the_secret_comes_from_the_environment_and_the_receipt_is_data():
    kitchen = Kitchen(
        result(OutcomeCategory.SUCCESS, ErrorCode.NONE, "posted", confirmation="HX-1")
    )
    server = build_server([with_secret()], kitchen, {"HANDRAIL_SECRET_PASSWORD": "plumbline-demo"})
    out = await server.call_tool("bank_place_hold", {"member_number": "400118", "reason": "LEGAL"})
    answer = json.loads(out[0].text)
    assert kitchen.orders == [
        {"member_number": "400118", "reason": "LEGAL", "password": "plumbline-demo"}
    ]
    assert answer["outputs"] == {"confirmation": "HX-1"} and answer["category"] == "SUCCESS"
    assert "plumbline-demo" not in json.dumps(answer)


def test_already_held_is_an_answer_and_only_recoverable_is_retryable():
    held = receipt(
        result(OutcomeCategory.BUSINESS_OUTCOME, ErrorCode.ALREADY_PROCESSED, "already_held")
    )
    assert (held["category"], held["retryable"], held["error"]) == ("BUSINESS_OUTCOME", False, None)
    slow = receipt(result(OutcomeCategory.RECOVERABLE, ErrorCode.SLOW_LOAD))
    assert slow["retryable"] is True and slow["error"] == "it broke"
    broken = receipt(result(OutcomeCategory.HARD_FAILURE, ErrorCode.SCREEN_MISMATCH))
    assert broken["retryable"] is False


async def test_an_agent_reads_already_held_and_does_not_order_twice():
    """The example caller's promise, with a scripted model: one order, then a report."""
    pytest.importorskip("langchain")
    from langchain.agents import create_agent
    from langchain_core.messages import AIMessage

    from ..author.test_agent import call, scripted

    kitchen = Kitchen(
        result(OutcomeCategory.BUSINESS_OUTCOME, ErrorCode.ALREADY_PROCESSED, "already_held")
    )
    server = build_server([with_secret()], kitchen, {"HANDRAIL_SECRET_PASSWORD": "x"})

    from langchain_core.tools import StructuredTool

    async def place_hold(member_number: str, reason: str) -> str:
        out = await server.call_tool(
            "bank_place_hold", {"member_number": member_number, "reason": reason}
        )
        return out[0].text

    tool = StructuredTool.from_function(
        coroutine=place_hold, name="bank_place_hold", description="place a hold"
    )
    model = scripted(
        call("bank_place_hold", member_number="400226", reason="LEGAL"),
        AIMessage(content="The share is already under hold; nothing was changed."),
    )
    agent = create_agent(model, tools=[tool])
    out = await agent.ainvoke({"messages": [("user", "hold 400226")]})
    assert len(kitchen.orders) == 1
    assert "already" in out["messages"][-1].content


async def test_the_server_keeps_stdout_for_the_wire(tmp_path: Path, capsys):
    """A greeting on stdout corrupts the MCP handshake; the first live run proved it."""
    import argparse

    from handrail.serve.mcp import serve_command

    args = argparse.Namespace(capabilities=str(tmp_path), evidence=str(tmp_path))
    assert await serve_command(args) == 4  # nothing approved in an empty directory
    out, err = capsys.readouterr()
    assert out == "" and "nothing approved" in err
