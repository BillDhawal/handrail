"""The three things a diner may say to the waiter. Nothing else is on the card.

A restaurant that lets guests wander into the kitchen gets a guest with a
knife. So the guest gets a card with three lines on it: "I'll have number 7",
"this is the dessert table, is it not?", and "that's all, thank you". The
guest never names a dish by description, never points at a pan, never asks
for the stove.

The guest is the authoring model. The three lines are its whole vocabulary:

- ``act(index, verb, value)``: do row ``index`` of the current menu. The row
  already says which verb it offers; the model may only agree with it. A
  value is accepted only where the verb takes one, and the model is expected
  to write a blank such as ``{{input.member_number}}`` rather than the real
  thing, so the trace never holds a literal that belongs to a customer.
- ``assert_screen(label)``: name the screen we are on, in words a person can
  read. The label is pinned to the screen's structural signature. This is how
  screens get their names in the compiled capability.
- ``finish(outcome)``: declare the task ended on a screen already labelled.

Every call that is accepted writes one ``Turn`` to the session's trace. The
compiler reads the trace; the model never sees it. A refused call writes
nothing and returns the refusal as text, so the model can try another row.
Refusals are typed ``ToolRefused`` for the tests and for the middleware; the
LangChain wrapper in ``agent.py`` turns them into tool output.

No model is imported here. This file is the fence, not the animal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..schema.bindings import BindingError, bind_text
from ..schema.target import TARGETED_VERBS, Verb
from ..schema.trace import Turn
from ..surface.base import Observation, Operation, Resolution, Surface

#: Verbs that take a value, and refuse to act without one.
VALUE_VERBS: frozenset[str] = frozenset({"set_value", "select"})


class ToolRefused(Exception):
    """The guest asked for something not on the card. Nothing was done."""


@dataclass
class Session:
    """One authoring run: a surface, the inputs it may fill in, and the trace so far."""

    surface: Surface
    inputs: dict[str, Any] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    trace: list[Turn] = field(default_factory=list)
    #: label -> signature, as asserted by the model.
    screens: dict[str, str] = field(default_factory=dict)
    observation: Observation | None = None
    outcome: str | None = None

    @property
    def finished(self) -> bool:
        return self.outcome is not None

    def signature(self) -> str:
        return "|".join(self.observation.structure) if self.observation else ""

    async def look(self) -> str:
        """Refresh the menu and return what the model sees: screen text, then numbered rows."""
        self.observation = await self.surface.observe()
        rows = "\n".join(
            f"{op.index}: {op.verb} {op.role} {op.name!r}" for op in self.observation.operations
        )
        return f"{self.observation.text.strip()}\n\n{rows}".strip()

    def row(self, index: int) -> Operation:
        if self.observation is None:
            raise ToolRefused("look at the screen first; there is no menu yet")
        for op in self.observation.operations:
            if op.index == index:
                return op
        raise ToolRefused(f"{index} is not on the menu (1..{len(self.observation.operations)})")

    def _record(self, turn: Turn) -> None:
        self.trace.append(turn)


async def act(session: Session, index: int, verb: Verb, value: str | None = None) -> str:
    """Do one row of the menu. Returns the menu as it looks afterwards."""
    if session.finished:
        raise ToolRefused("the session is finished")
    row = session.row(index)
    if verb != row.verb:
        raise ToolRefused(f"row {index} is {row.verb} on {row.role} {row.name!r}, not {verb}")
    if verb in VALUE_VERBS and not value:
        raise ToolRefused(f"{verb} needs a value")
    if verb not in VALUE_VERBS and value:
        raise ToolRefused(f"{verb} takes no value")
    bound: str | None = None
    if value:
        try:
            bound = bind_text(value, session.inputs, session.env)
        except BindingError as exc:
            raise ToolRefused(str(exc)) from exc
    before = session.signature()
    resolution = Resolution(handle=row.handle, rung="menu", rung_cost=0)
    result = await session.surface.act(resolution if verb in TARGETED_VERBS else None, verb, bound)
    after = await session.look()
    session._record(
        Turn(
            seq=len(session.trace) + 1,
            tool="act",
            index=index,
            verb=verb,
            value=value,
            role=row.role,
            name=row.name,
            handle=row.handle,
            signature_before=before,
            signature_after=session.signature(),
            read_value=result.value,
        )
    )
    return f"read: {result.value}\n\n{after}" if verb == "read" else after


async def assert_screen(session: Session, label: str) -> str:
    """Pin a human-readable label to the structure of the screen we are on."""
    if session.finished:
        raise ToolRefused("the session is finished")
    label = label.strip()
    if not label:
        raise ToolRefused("a screen needs a label")
    if session.observation is None:
        await session.look()
    signature = session.signature()
    known = session.screens.get(label)
    if known is not None and known != signature:
        raise ToolRefused(f"{label!r} already names a different screen")
    for other, sig in session.screens.items():
        if sig == signature and other != label:
            raise ToolRefused(f"this screen is already labelled {other!r}")
    session.screens[label] = signature
    session._record(
        Turn(
            seq=len(session.trace) + 1,
            tool="assert_screen",
            label=label,
            signature_before=signature,
            signature_after=signature,
        )
    )
    return f"screen {label!r} recorded"


async def finish(session: Session, outcome: str) -> str:
    """End the run on a labelled screen. The label becomes an outcome of the capability."""
    if session.finished:
        raise ToolRefused("the session is finished")
    outcome = outcome.strip()
    if outcome not in session.screens:
        raise ToolRefused(f"{outcome!r} is not a labelled screen; call assert_screen first")
    if session.screens[outcome] != session.signature():
        raise ToolRefused(f"the screen showing now is not {outcome!r}")
    session.outcome = outcome
    session._record(
        Turn(
            seq=len(session.trace) + 1,
            tool="finish",
            label=outcome,
            signature_before=session.signature(),
            signature_after=session.signature(),
        )
    )
    return f"finished on {outcome!r}"
