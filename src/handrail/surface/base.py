"""The Surface: the waiter between the kitchen and the dining room.

The kitchen - Handrail's engine, compiler and escalation ladder - never walks
into the dining room. It never sees a browser, an accessibility tree or a
terminal screen. It only talks to a waiter, and a waiter accepts exactly six
kinds of request: walk to a table (``open``), report what is on it
(``observe``), find one specific item on it (``resolve``), do something to that
item (``act``), answer a yes/no question about it without waiting
(``evaluate``), and take a photo (``evidence``).

A browser, a green-screen terminal and a Mac app are three dining rooms. Each
gets its own waiter. The kitchen's recipe works in all three because the
kitchen never left the kitchen - and every kitchen test runs in milliseconds
against a pretend dining room.

The idea that matters most is the operations table. ``observe`` does not hand
back a photo and say "point at anything". It hands back a numbered menu of what
is legal right now, on controls that are actually present: "1: press Search.
2: type into Member. 3: press Hold." A disabled button is not on it. A checkbox
is never offered as a place to type. Every model in the system can only say a
number from this menu, so the worst a confused or tricked model can do is pick
a wrong item from a list of real, legal actions. No model output ever becomes a
selector, a coordinate or code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..schema.target import Target, Verb


@dataclass(frozen=True)
class Operation:
    """One row of the operations table: this verb, on this control, is legal now."""

    index: int
    verb: Verb
    role: str
    name: str
    #: What the surface will hand back if this row is chosen. Opaque above this line.
    handle: Any = None


@dataclass(frozen=True)
class Observation:
    """What the surface can see right now."""

    text: str
    operations: tuple[Operation, ...]
    #: Inputs to the screen signature: attribute paths of the actionable elements.
    structure: tuple[str, ...] = ()


@dataclass(frozen=True)
class Resolution:
    """Exactly one control, and the rung of the ladder that found it."""

    handle: Any
    rung: str
    rung_cost: int
    match_count: int = 1


@dataclass(frozen=True)
class ActResult:
    ok: bool
    value: str | None = None  # what a `read` returned


@dataclass
class EvidenceBundle:
    text: str = ""
    screenshot_png: bytes | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Surface(Protocol):
    """Six verbs. A surface implements them; nothing else is asked of it."""

    kind: str

    async def open(self, entry: str) -> None: ...

    async def observe(self) -> Observation: ...

    async def resolve(self, target: Target, timeout_ms: int) -> Resolution:
        """Find exactly one control, or raise a HandrailError naming why not."""
        ...

    async def act(
        self, resolution: Resolution | None, verb: Verb, value: str | None
    ) -> ActResult: ...

    async def evaluate(self, condition: str) -> bool:
        """Is this named condition true right now? Never waits."""
        ...

    async def evidence(self) -> EvidenceBundle: ...

    async def close(self) -> None: ...
