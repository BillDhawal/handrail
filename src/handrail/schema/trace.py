"""One line of the order book: what the guest said, and what the maître d' added.

A ``Turn`` is pure data. It is written by the authoring tools, enriched by the
guard, stored by the recorder and read by the compiler, and it lives here in
``schema`` so that the compiler, which must never import model-adjacent code,
can read the book without opening the restaurant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .target import Fingerprint, Rung


@dataclass(frozen=True)
class Turn:
    """One accepted call, as the compiler will read it."""

    seq: int
    tool: str
    index: int | None = None
    verb: str | None = None
    value: str | None = None  # as the model wrote it, blanks unfilled
    role: str | None = None
    name: str | None = None
    handle: Any = None
    signature_before: str = ""
    signature_after: str = ""
    label: str | None = None
    read_value: str | None = None
    # Filled in by the guard in middleware.py, never by the model.
    effect: str | None = None
    confirmed_by: str | None = None
    rungs: tuple[Rung, ...] = ()
    fingerprint: Fingerprint | None = None
    row: str | None = None  # the table row the control sat in, by its first cell
    ancestors: tuple[str, ...] = ()  # container roles, so a fingerprint can be retaken
