"""The scout: sent ahead when the map stops matching the ground, told to report a named landmark.

The cook cannot tell which counter this is, and the referee could not say
either. Rung two sends a scout: a model, seated once more at the three-line
card, but with ``commit`` struck off it. The scout may look, may navigate,
may stage a draft, and must end by naming one of the landmarks the cook was
expecting. The cook then checks the furniture itself before believing the
scout. A scout that names a landmark behind the cook is ignored: a bridge
goes forward or not at all.

This file is the port and the report. The scout that uses a model lives in
``author/bridge.py``; nothing in ``replay`` imports it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..schema.capability import Capability
from ..surface.base import Surface


@dataclass(frozen=True)
class Crossing:
    """What the scout reported: the landmark named, or None, and what it cost."""

    named: str | None
    model_calls: int
    turns: int
    note: str = ""


class Bridge(Protocol):
    name: str

    async def cross(
        self,
        surface: Surface,
        capability: Capability,
        candidates: list[str],
        inputs: dict[str, Any],
        env: dict[str, str],
        step_id: str | None,
    ) -> Crossing: ...
