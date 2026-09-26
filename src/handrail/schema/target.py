"""How a control is identified, on any surface.

A target is described the way assistive technology describes it: a role, an
accessible name, the operations it supports, and where it sits. That description
means the same thing for a DOM button, a macOS AXButton and a field on a 3270
screen, which is what lets one replay engine drive all three.

The ladder is the ranked list of ways to find it again. Rungs are tried in cost
order and never raced: the rung that resolved is reported in every result, and a
run that starts landing on rung two is the early warning that the application
moved. Costs follow Playwright's published selector scoring; lowest wins.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Verb = Literal["invoke", "set_value", "select", "toggle", "press_key", "read", "scroll", "wait"]

#: Verbs that act on a specific control and therefore need a target.
TARGETED_VERBS: frozenset[str] = frozenset({"invoke", "set_value", "select", "toggle", "read"})

RungKind = Literal["stable_id", "role_name", "label", "text", "position", "native"]

RUNG_COST: dict[str, int] = {
    "stable_id": 1,
    "role_name": 100,
    "label": 140,
    "text": 180,
    "position": 10_000,
    "native": 10_000_000,
}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NameMatch(_Model):
    """Exactly one of: equals this text, or matches this pattern."""

    eq: str | None = None
    matches: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> NameMatch:
        if (self.eq is None) == (self.matches is None):
            raise ValueError("a name needs exactly one of `eq` or `matches`")
        return self


class ScopeStep(_Model):
    """One container on the way down: a frame, a window, a dialog, a pane."""

    role: str
    name: str | None = None


class Rung(_Model):
    rung: RungKind
    cost: int = Field(ge=1)
    #: Set only on a rung that works on one surface, such as a CSS selector.
    surface: str | None = None
    value: str | None = None

    @model_validator(mode="after")
    def _native_names_its_surface(self) -> Rung:
        if self.rung == "native" and not (self.surface and self.value):
            raise ValueError("a native rung must say which surface it is for, and its value")
        return self


class Fingerprint(_Model):
    """Answers "is this the same control", which a ladder alone cannot."""

    over: list[str] = Field(min_length=1)
    value: str


class Target(_Model):
    role: str
    name: NameMatch | None = None
    #: verb -> the argument types that verb takes on this control.
    supports: dict[Verb, list[str]] = Field(min_length=1)
    scope: list[ScopeStep] = Field(default_factory=list)
    ladder: list[Rung] = Field(min_length=1)
    fingerprint: Fingerprint | None = None

    @model_validator(mode="after")
    def _ladder_is_ranked(self) -> Target:
        costs = [r.cost for r in self.ladder]
        if costs != sorted(costs):
            raise ValueError("ladder rungs must be listed cheapest first")
        if len(set(costs)) != len(costs):
            raise ValueError("two rungs share a cost, so their order would be arbitrary")
        return self
