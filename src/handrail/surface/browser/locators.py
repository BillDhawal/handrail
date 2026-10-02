"""Directions to a house, tested on the street before they are written down.

"The house with the blue door" is a fine direction on a street with one blue
door and a useless one on a street with three. You cannot tell which street you
are on from the house alone; you have to walk the street and count. And a
direction that leads to exactly one house is still wrong if it is the
neighbour's.

This module writes directions to a control and then walks the street. From one
``Control`` it proposes every way the browser could find that control again: by
a test id, by role and accessible name, by the caption beside it, by its
visible text, by its HTML ``name`` attribute. Each proposal is a rung of the
target's ladder. Then it tries each rung on the live page and keeps only the
ones that find exactly one element, and that element is this one. What
survives is what the compiler stores; a control with no surviving rung is one
the compiler must refuse.

Two decisions worth knowing. A rung is turned into a ``Query`` here, in one
place, so the probe at authoring time and the resolve at replay time ask the
page the identical question. And no ``position`` rung is ever proposed: "the
third link" is the direction that breaks the day a row is added, which on a
banking screen is every day.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from ...schema.target import RUNG_COST, Rung
from .operations import Control

#: Tags a caption can sit beside. The label rung finds the first of these after the caption.
_FIELD = "self::input or self::select or self::textarea"


@dataclass(frozen=True)
class Query:
    """One question for the page. The surface turns it into a Playwright locator."""

    how: Literal["test_id", "role", "text", "selector"]
    value: str = ""
    role: str = ""
    name: str = ""
    #: True when `name` is a pattern to match rather than text to equal.
    regex: bool = False


class Probe(Protocol):
    """The street, as far as this module needs it: one frame of the live page."""

    async def count(self, query: Query) -> int: ...

    async def is_same(self, query: Query, handle: Any) -> bool:
        """Does the single element this query finds turn out to be `handle`?"""
        ...


def _xpath_literal(text: str) -> str:
    """Quote text for XPath, which has no escape character."""
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ', "\'", '.join(f"'{p}'" for p in parts) + ")"


def _css_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _rung(kind: str, value: str | None = None, surface: str | None = None) -> Rung:
    return Rung.model_validate(
        {"rung": kind, "cost": RUNG_COST[kind], "value": value, "surface": surface}
    )


def candidates(control: Control) -> list[Rung]:
    """Every direction worth trying, cheapest first. None is trusted yet."""
    rungs: list[Rung] = []
    if control.test_id:
        rungs.append(_rung("stable_id", control.test_id))
    if control.name:
        rungs.append(_rung("role_name"))
    if control.label and not control.name:
        rungs.append(_rung("label", control.label))
    if control.name:
        rungs.append(_rung("text", control.name))
    if control.attr_name:
        rungs.append(_rung("native", f"[name={_css_string(control.attr_name)}]", "browser"))
    return rungs


def query_for(rung: Rung, role: str, name: str, regex: bool = False) -> Query:
    """The one translation from a rung to a question. Authoring and replay both use it."""
    value = rung.value or ""
    if rung.rung == "stable_id":
        return Query("test_id", value)
    if rung.rung == "role_name":
        return Query("role", role=role, name=name, regex=regex)
    if rung.rung == "label":
        caption = _xpath_literal(value)
        return Query(
            "selector",
            f"xpath=//*[normalize-space(text())={caption}]/following::*[{_FIELD}][1]",
        )
    if rung.rung == "text":
        return Query("text", value)
    if rung.rung == "native" and rung.surface == "browser":
        return Query("selector", value)
    raise ValueError(f"the browser cannot follow a {rung.rung!r} rung")


async def surviving(control: Control, probe: Probe) -> list[Rung]:
    """Walk the street: keep a rung only if it finds one element, and it is this one."""
    kept: list[Rung] = []
    for rung in candidates(control):
        query = query_for(rung, control.role, control.name)
        if await probe.count(query) != 1:
            continue
        if not await probe.is_same(query, control.handle):
            continue
        kept.append(rung)
    return kept
