"""The referee's notebook: every time the whistle blew, what was said, and what it turned out to be.

A referee who never writes anything down cannot be told how often the calls
were right. This is the notebook: one SQLite row per escalation, with what
failed, which question was asked, what the classifier answered, whether the
engine accepted it, and, once the run has ended, whether that was right.

Reliability, drift rate and bridge rate are queries over this table. So is
the calibration curve: group the rows by confidence, count how often the
accepted answer held, and the thresholds on the card can be re-tuned when a
pinned model version changes.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  run_id TEXT NOT NULL,
  capability TEXT NOT NULL,
  step_id TEXT,
  failed TEXT NOT NULL,
  rung INTEGER NOT NULL,
  question TEXT,
  backend TEXT,
  chosen TEXT,
  confidence REAL,
  margin REAL,
  probabilities TEXT,
  accepted INTEGER NOT NULL DEFAULT 0,
  outcome TEXT,
  held INTEGER
);
"""


@dataclass(frozen=True)
class Bin:
    low: float
    high: float
    count: int
    held: int

    @property
    def rate(self) -> float:
        return self.held / self.count if self.count else 0.0


class Episodes:
    def __init__(self, path: Path | str = ":memory:") -> None:
        self.db = sqlite3.connect(str(path))
        self.db.executescript(SCHEMA)

    def record(
        self,
        run_id: str,
        capability: str,
        failed: str,
        rung: int,
        step_id: str | None = None,
        question: str | None = None,
        backend: str | None = None,
        chosen: str | None = None,
        confidence: float | None = None,
        margin: float | None = None,
        probabilities: dict[str, float] | None = None,
        accepted: bool = False,
    ) -> int:
        cur = self.db.execute(
            "INSERT INTO episodes (run_id, capability, step_id, failed, rung, question, backend, "
            "chosen, confidence, margin, probabilities, accepted) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                capability,
                step_id,
                failed,
                rung,
                question,
                backend,
                chosen,
                confidence,
                margin,
                json.dumps(probabilities) if probabilities else None,
                int(accepted),
            ),  # fmt: skip
        )
        self.db.commit()
        return int(cur.lastrowid or 0)

    def settle(self, run_id: str, outcome: str, held: bool) -> None:
        """Once the run has ended: every accepted verdict in it either held or did not."""
        self.db.execute(
            "UPDATE episodes SET outcome = ?, held = ? WHERE run_id = ? AND accepted = 1",
            (outcome, int(held), run_id),
        )
        self.db.commit()

    def rows(self, run_id: str | None = None) -> list[dict[str, Any]]:
        q = "SELECT * FROM episodes" + (" WHERE run_id = ?" if run_id else "") + " ORDER BY id"
        cur = self.db.execute(q, (run_id,) if run_id else ())
        names = [c[0] for c in cur.description]
        return [dict(zip(names, r, strict=True)) for r in cur.fetchall()]

    def calibration(self, question: str | None = None, bins: int = 5) -> list[Bin]:
        """Accepted verdicts with a settled outcome, grouped by confidence."""
        q = "SELECT confidence, held FROM episodes WHERE accepted = 1 AND held IS NOT NULL"
        args: tuple[Any, ...] = ()
        if question:
            q, args = q + " AND question = ?", (question,)
        out = []
        rows = self.db.execute(q, args).fetchall()
        for i in range(bins):
            low, high = i / bins, (i + 1) / bins
            inside = [h for c, h in rows if low <= c < high or (i == bins - 1 and c == 1.0)]
            out.append(Bin(low, high, len(inside), sum(inside)))
        return out
