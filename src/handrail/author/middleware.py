"""The maître d': between the guest and the waiter, asking the owner before anything irreversible.

The guest (the model) says "number 7". Before the waiter moves, the maître d'
does four things the guest never sees. He looks at what number 7 actually is,
and writes down every way of finding that dish again, tested on tonight's
menu (``locators.surviving``). He takes its fingerprint. He decides how
serious the order is: looking, moving tables, a reversible draft, or
something that cannot be taken back. And if it cannot be taken back, he goes
and asks the owner, who may say yes, may say "that one is only a navigation,
carry on", or may say no. Only then is the waiter sent.

Afterwards he writes the whole turn into the book, and the book is written
before the guest is allowed to say anything else. That is the sink; in
milestone 3 step 4 the sink is the recorder on disk.

Two rules worth knowing. First, the default classification is cautious: a
button press is a commit until a person says otherwise, because the
prototype's keyword guesser got this wrong in both directions. Second, a
control that no rung can find again is still acted on. Authoring must be
able to continue; it is the compiler, later, that refuses to store a step it
could never replay.

No model is imported here either. The classifier rung (milestone 5) can be
plugged in as ``classify``; until then the rule above is the classifier.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

from ..schema.effects import EffectClass
from ..schema.target import Fingerprint, Rung, Verb
from ..schema.trace import Turn
from ..surface.browser.fingerprint import fingerprint
from ..surface.browser.locators import Probe, surviving
from ..surface.browser.operations import Control
from . import tools
from .tools import Session, ToolRefused


class Authorable(Protocol):
    """What a surface must add, beyond the six verbs, for authoring to probe a menu row."""

    async def describe(self, handle: Any) -> Control: ...

    def probe(self, handle: Any, control: Control) -> Probe: ...


@dataclass(frozen=True)
class Proposal:
    """What is about to be done, with everything the owner needs to decide."""

    index: int
    verb: Verb
    value: str | None
    control: Control
    effect: EffectClass
    rungs: tuple[Rung, ...]
    fingerprint: Fingerprint


@dataclass(frozen=True)
class Decision:
    """The owner's answer. `effect=None` means no."""

    effect: EffectClass | None
    by: str


Confirm = Callable[[Proposal], Awaitable[Decision]]
Classify = Callable[[Control, Verb], EffectClass]


class Sink(Protocol):
    def write(self, turn: Turn) -> None: ...


@dataclass
class MemorySink:
    turns: list[Turn] = field(default_factory=list)

    def write(self, turn: Turn) -> None:
        self.turns.append(turn)


def cautious(control: Control, verb: Verb) -> EffectClass:
    """The default classifier: a button press is a commit until a person says otherwise."""
    if verb == "read":
        return EffectClass.READ
    if verb in ("set_value", "select", "toggle"):
        return EffectClass.STAGE
    if control.role == "link":
        return EffectClass.NAVIGATE
    return EffectClass.COMMIT


class Guard:
    def __init__(
        self,
        session: Session,
        surface: Authorable,
        confirm: Confirm,
        sink: Sink | None = None,
        classify: Classify = cautious,
    ) -> None:
        self.session = session
        self.surface = surface
        self.confirm = confirm
        self.sink: Sink = sink or MemorySink()
        self.classify = classify
        # A model may send several tool calls in one breath and the loop runs them
        # concurrently. "Fill, fill, click" fired at once clicks an empty form. One guest
        # speaks at a time, in the order the words came out.
        self._one_at_a_time = asyncio.Lock()

    async def propose(self, index: int, verb: Verb, value: str | None) -> Proposal:
        row = self.session.row(index)
        control = await self.surface.describe(row.handle)
        return Proposal(
            index=index,
            verb=verb,
            value=value,
            control=control,
            effect=self.classify(control, verb),
            rungs=tuple(await surviving(control, self.surface.probe(row.handle, control))),
            fingerprint=fingerprint(control),
        )

    async def act(self, index: int, verb: Verb, value: str | None = None) -> str:
        async with self._one_at_a_time:
            return await self._act(index, verb, value)

    async def _act(self, index: int, verb: Verb, value: str | None) -> str:
        if self.session.finished:
            raise ToolRefused("the session is finished")
        proposal = await self.propose(index, verb, value)
        effect, by = proposal.effect, None
        if effect is EffectClass.COMMIT:
            decision = await self.confirm(proposal)
            if decision.effect is None:
                who, what = decision.by, proposal.control.name
                raise ToolRefused(f"{who} did not allow row {index} ({what!r})")
            effect, by = decision.effect, decision.by
        shown = await tools.act(self.session, index, verb, value)
        turn = replace(
            self.session.trace[-1],
            effect=effect.value,
            confirmed_by=by,
            rungs=proposal.rungs,
            fingerprint=proposal.fingerprint,
            row=proposal.control.row or None,
            ancestors=proposal.control.ancestors,
        )
        self.session.trace[-1] = turn
        self.sink.write(turn)
        return shown

    async def assert_screen(self, label: str) -> str:
        async with self._one_at_a_time:
            shown = await tools.assert_screen(self.session, label)
            self.sink.write(self.session.trace[-1])
            return shown

    async def finish(self, outcome: str) -> str:
        async with self._one_at_a_time:
            shown = await tools.finish(self.session, outcome)
            self.sink.write(self.session.trace[-1])
            return shown
