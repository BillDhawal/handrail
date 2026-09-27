"""A pretend dining room, scripted by the test that uses it.

A real waiter walks into a real restaurant. This one reads from a script: the
test says what each page looks like, which items a locator would find and how
many, what a read returns, and which actions turn the page. That is enough to
drive every branch of the engine - the happy path, a business refusal, every
failure code, every escalation - with no browser and in a few milliseconds.

It is a stage set, not a simulation. It never guesses what an application
would do; it does exactly what the script says, so a test that passes here
proves something about the engine and nothing about any application.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schema.errors import ErrorCode, HandrailError
from ..schema.target import Target, Verb
from .base import ActResult, EvidenceBundle, Observation, Operation, Resolution


@dataclass
class Page:
    """One screen in the script."""

    signature: str
    text: str = ""
    #: (rung kind, control name) -> how many controls that rung would find.
    matches: dict[tuple[str, str], int] = field(default_factory=dict)
    #: control name -> what a `read` returns.
    reads: dict[str, str] = field(default_factory=dict)
    #: acting on any of these control names turns to the next page.
    advance_on: frozenset[str] = frozenset()

    def present(self, name: str) -> bool:
        return any(n == name and count > 0 for (_, n), count in self.matches.items())


class NullSurface:
    kind = "null"

    def __init__(self, pages: list[Page]) -> None:
        if not pages:
            raise ValueError("a script needs at least one page")
        self.pages = pages
        self.index = 0
        self.opened: list[str] = []
        #: Every act, in order: (verb, control name, value). Tests assert on this.
        self.actions: list[tuple[str, str, str | None]] = []

    @property
    def page(self) -> Page:
        return self.pages[self.index]

    def advance(self) -> None:
        """Turn the page by hand, for scripts where no action does it."""
        self.index = min(self.index + 1, len(self.pages) - 1)

    # -- the six verbs ----------------------------------------------------------

    async def open(self, entry: str) -> None:
        self.opened.append(entry)

    async def observe(self) -> Observation:
        ops = [
            Operation(index=i + 1, verb="invoke", role="control", name=n, handle=n)
            for i, ((_, n), count) in enumerate(self.page.matches.items())
            if count > 0
        ]
        return Observation(
            text=self.page.text, operations=tuple(ops), structure=(self.page.signature,)
        )

    async def resolve(self, target: Target, timeout_ms: int) -> Resolution:
        name = target.name.eq if target.name and target.name.eq else target.role
        for rung in target.ladder:  # already sorted cheapest first by the schema
            count = self.page.matches.get((rung.rung, name), 0)
            if count == 0:
                continue
            if count > 1:
                raise HandrailError(
                    f"{rung.rung} finds {count} controls named {name!r}",
                    ErrorCode.AMBIGUOUS_CONTROL,
                )
            return Resolution(handle=name, rung=rung.rung, rung_cost=rung.cost, match_count=1)
        raise HandrailError(f"no rung finds {name!r}", ErrorCode.MISSING_CONTROL)

    async def act(self, resolution: Resolution | None, verb: Verb, value: str | None) -> ActResult:
        name = str(resolution.handle) if resolution else ""
        self.actions.append((verb, name, value))
        result = ActResult(ok=True, value=self.page.reads.get(name) if verb == "read" else None)
        if name in self.page.advance_on:
            self.advance()
        return result

    async def evaluate(self, condition: str) -> bool:
        kind, _, arg = condition.partition(":")
        if kind == "target_present":
            return self.page.present(arg)
        if kind == "screen_is":
            return self.page.signature == arg
        if kind == "keyboard_unlocked":
            return True
        return False

    async def evidence(self) -> EvidenceBundle:
        return EvidenceBundle(text=self.page.text)

    async def close(self) -> None:
        pass
