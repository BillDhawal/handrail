"""The guest's evening: seated once, three lines on the card, home when the bill is signed.

Everything the guest can do was decided before the guest arrived. The card
(``tools.py``) has three lines. The maître d' (``middleware.py``) stands
between the guest and the waiter. This file only seats the guest, reads the
card out loud, and keeps count of how many times the guest spoke.

The loop itself is LangChain's ``create_agent``: a model, a list of tools, a
system prompt. We hand it the three tools bound to one ``Guard``, so every
tool call is probed, classified, confirmed and recorded before the model
hears the answer. A refused call comes back to the model as text beginning
``refused:``, so it can pick another row. Nothing here raises at the model.

The first message names the goal and the *names* of the inputs the model may
use as blanks. Never their values: the model types ``{{input.password}}``
and the session fills it in on the way to the surface.

This is the one file in the repository that is given a model, and it is
given one; it never constructs one. ``model`` may be a chat model or a
provider string LangChain knows how to build.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool, tool
from langgraph.errors import GraphRecursionError

from ..schema.trace import Turn
from .middleware import Guard
from .tools import ToolRefused

SYSTEM_PROMPT = """You are operating a legacy application through a waiter who hands you a
numbered menu. Each turn you see the screen text and a menu of legal operations, one per
line: index, verb, role, name.
You have exactly three tools:
- act(index, verb, value): do one row of the menu. The verb must be the row's own verb.
  set_value and select take a value; the others take none.
- assert_screen(label): give the screen you are on a short human label, before acting on it.
- finish(outcome): end on a labelled screen that is the result of the task.
Rules:
- Never type a real value. Type a blank such as {{input.member_number}}, using only the
  input names given.
- Label every new screen with assert_screen before you act on it. Label the final screen,
  then finish.
- If a call is refused, read why and choose another row. Do not repeat a refused call.
- Say nothing else. Use the tools."""


@dataclass
class AuthoringResult:
    finished: bool
    outcome: str | None
    trace: list[Turn]
    screens: dict[str, str]
    model_calls: int
    paths: dict[str, tuple[str, ...]] = field(default_factory=dict)
    messages: list[Any] = field(default_factory=list)


def build_tools(guard: Guard) -> list[BaseTool]:
    """The three lines on the card, bound to one maître d'."""

    @tool
    async def act(index: int, verb: str, value: str | None = None) -> str:
        """Do row `index` of the menu with its own verb; a value only for set_value/select."""
        try:
            return await guard.act(index, verb, value)  # type: ignore[arg-type]
        except ToolRefused as exc:
            return f"refused: {exc}"

    @tool
    async def assert_screen(label: str) -> str:
        """Pin a short human label to the screen showing now."""
        try:
            return await guard.assert_screen(label)
        except ToolRefused as exc:
            return f"refused: {exc}"

    @tool
    async def finish(outcome: str) -> str:
        """End the run on a labelled screen that is the task's result."""
        try:
            return await guard.finish(outcome)
        except ToolRefused as exc:
            return f"refused: {exc}"

    return [act, assert_screen, finish]


def build_agent(
    model: BaseChatModel | str, guard: Guard, system_prompt: str = SYSTEM_PROMPT
) -> Any:
    return create_agent(model, tools=build_tools(guard), system_prompt=system_prompt)


def opening_message(goal: str, input_names: list[str], menu: str) -> str:
    blanks = ", ".join(f"{{{{input.{n}}}}}" for n in input_names) or "none"
    return f"Goal: {goal}\nInputs you may use as blanks: {blanks}\n\nScreen now:\n{menu}"


async def author(
    model: BaseChatModel | str, guard: Guard, goal: str, max_turns: int = 40
) -> AuthoringResult:
    """Seat the guest, read the card, let the evening run; home at `finish` or the turn limit."""
    session = guard.session
    menu = await session.look()
    opening = opening_message(goal, sorted(session.inputs), menu)
    agent = build_agent(model, guard)
    messages: list[Any] = []
    try:
        out = await agent.ainvoke(
            {"messages": [("user", opening)]},
            config={"recursion_limit": 2 * max_turns + 1},
        )
        messages = list(out["messages"])
    except GraphRecursionError:
        pass  # the evening ran long; what was recorded still stands
    return AuthoringResult(
        finished=session.finished,
        outcome=session.outcome,
        trace=list(session.trace),
        screens=dict(session.screens),
        paths=dict(session.paths),
        model_calls=sum(isinstance(m, AIMessage) for m in messages) or max_turns,
        messages=messages,
    )
