"""The baton: whoever holds it drives, and it changes hands only by name.

A relay runner does not let go of the baton because someone shouted. It is
handed over, hand to hand, and the exchange is seen. The run works the same
way. One token says who is driving the live session: the automation, nobody
(paused), a person, or nobody ever again (aborted). Every change of hands
records who asked and why, and the only legal exchanges are the ones below.

    AUTOMATION_RUNNING --pause-->    PAUSED
    PAUSED             --take_over-> HUMAN_CONTROL
    HUMAN_CONTROL      --hand_back-> AUTOMATION_RUNNING
    PAUSED             --resume-->   AUTOMATION_RUNNING
    any but ABORTED    --abort-->    ABORTED

The engine checks the baton before every step and before every action. When
a person holds it, the engine does nothing, and waits. On a native desktop
the same token is what an input-event tap flips when an untagged keystroke
arrives: a human touched the machine, so the run pauses. That tap is a later
milestone; the baton it flips is this one.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Owner(StrEnum):
    AUTOMATION_RUNNING = "AUTOMATION_RUNNING"
    PAUSED = "PAUSED"
    HUMAN_CONTROL = "HUMAN_CONTROL"
    ABORTED = "ABORTED"


LEGAL: dict[str, tuple[Owner, Owner]] = {
    "pause": (Owner.AUTOMATION_RUNNING, Owner.PAUSED),
    "take_over": (Owner.PAUSED, Owner.HUMAN_CONTROL),
    "hand_back": (Owner.HUMAN_CONTROL, Owner.AUTOMATION_RUNNING),
    "resume": (Owner.PAUSED, Owner.AUTOMATION_RUNNING),
}


class IllegalExchange(RuntimeError):
    """The baton cannot change hands that way from where it is."""


@dataclass(frozen=True)
class Exchange:
    at: str
    action: str
    frm: Owner
    to: Owner
    by: str
    why: str


@dataclass
class Baton:
    owner: Owner = Owner.AUTOMATION_RUNNING
    history: list[Exchange] = field(default_factory=list)
    _changed: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _watchers: list[Callable[[Exchange], None]] = field(default_factory=list, repr=False)

    def watch(self, callback: Callable[[Exchange], None]) -> None:
        """Be told of every exchange, for the recorder and the console."""
        self._watchers.append(callback)

    def _move(self, action: str, to: Owner, by: str, why: str) -> Exchange:
        exchange = Exchange(datetime.now(UTC).isoformat(), action, self.owner, to, by, why)
        self.owner = to
        self.history.append(exchange)
        for watcher in self._watchers:
            watcher(exchange)
        self._changed.set()
        self._changed = asyncio.Event()
        return exchange

    def exchange(self, action: str, by: str, why: str = "") -> Exchange:
        if self.owner is Owner.ABORTED:
            raise IllegalExchange("the run is aborted; the baton is on the floor")
        if action == "abort":
            return self._move(action, Owner.ABORTED, by, why)
        if action not in LEGAL:
            raise IllegalExchange(f"no such exchange: {action!r}")
        frm, to = LEGAL[action]
        if self.owner is not frm:
            raise IllegalExchange(f"cannot {action} while {self.owner.value}")
        return self._move(action, to, by, why)

    # -- what the engine asks ---------------------------------------------------

    @property
    def automation_may_act(self) -> bool:
        return self.owner is Owner.AUTOMATION_RUNNING

    @property
    def aborted(self) -> bool:
        return self.owner is Owner.ABORTED

    async def wait_until_automation_may_act(self, timeout_s: float | None = None) -> bool:
        """Block while a person drives or the run is paused. False if aborted or timed out."""
        loop = asyncio.get_running_loop()
        deadline = None if timeout_s is None else loop.time() + timeout_s
        while not self.automation_may_act:
            if self.aborted:
                return False
            remaining = None if deadline is None else deadline - loop.time()
            if remaining is not None and remaining <= 0:
                return False
            try:
                await asyncio.wait_for(self._changed.wait(), remaining)
            except TimeoutError:
                return False
        return True
