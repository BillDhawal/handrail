"""The house rules pinned to the kitchen door: which shelves this server may open.

A restaurant manager hands a new waiter a card: the pantry is here, the
receipts are there, the old order book is over there, and nothing else is
yours to touch. This is that card. The server reads only the three places
named on it, and it listens only on the address written at the bottom.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    capabilities: Path
    evidence: Path
    episodes: Path | None
    host: str = "127.0.0.1"
    port: int = 8090
