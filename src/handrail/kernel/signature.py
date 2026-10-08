"""Recognising a room by its furniture, never by what is written on the whiteboard.

You walk into a meeting room you have used before. You do not read the
agenda on the board to know where you are; you see the long table, the
screen on the far wall, the two doors. If someone added a chair, it is still
the same room. If the table is gone and there are rows of desks, it is not.

A screen signature works the same way. It is the set of attribute paths of
the elements that make the screen what it is: tag, classes and ``name`` on
the way down, never text and never a typed value. The hash of that set is
what the artifact stores. Matching is tiered, and every tier is plain data:

1. exact: the hashes are equal.
2. similar: the sets overlap by Jaccard at or above ``THRESHOLD``. One extra
   banner on a page is a chair, not a new room.
3. none: the engine's own tiers are exhausted. From here the ladder is
   climbed: a classifier choosing among declared screens, then a bridge,
   then a person. None of that lives in this file.

A surface that has already taken the signature may report it as the single
path (the scripted stage set does): then that value is the signature.

This is the Stoat idea, "keep the chrome, ignore the rows", in forty lines.
A terminal surface will report protected-field positions as its paths and
need nothing else from here.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

#: Below this overlap two screens are not the same room, whatever the classifier says later.
THRESHOLD = 0.85

Tier = Literal["exact", "similar", "none"]


@dataclass(frozen=True)
class Signature:
    value: str
    paths: frozenset[str]


def take(paths: Iterable[str]) -> Signature:
    """The signature of a set of paths. Order-free; duplicates are one path."""
    unique = frozenset(p for p in paths if p)
    if len(unique) == 1:
        only = next(iter(unique))
        if only.startswith(("sha256:", "sig:")):
            return Signature(value=only, paths=unique)  # already taken by the surface
    digest = hashlib.sha256("\n".join(sorted(unique)).encode("utf-8")).hexdigest()
    return Signature(value="sha256:" + digest[:16], paths=unique)


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


@dataclass(frozen=True)
class Match:
    label: str | None
    tier: Tier
    score: float


def match(observed: Sequence[str], screens: Mapping[str, tuple[str, Sequence[str]]]) -> Match:
    """Which declared screen is this? `screens` maps a label to (stored value, stored paths)."""
    seen = take(observed)
    for label, (value, _) in screens.items():
        if value == seen.value:
            return Match(label, "exact", 1.0)
    best, best_score = None, 0.0
    for label, (_, paths) in screens.items():
        if not paths:
            continue  # a screen without paths can only be matched exactly
        score = jaccard(seen.paths, paths)
        if score > best_score:
            best, best_score = label, score
    if best is not None and best_score >= THRESHOLD:
        return Match(best, "similar", best_score)
    return Match(None, "none", best_score)
