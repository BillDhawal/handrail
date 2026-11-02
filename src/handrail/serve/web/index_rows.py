"""The drawer's printed layout: the columns on each index card and how a row reads back.

A card catalogue has a fixed form: title here, shelf mark there. Changing
the form means reprinting every card, so the form carries a number
(``SCHEMA_VERSION``) and a drawer with the wrong number is emptied and refilled.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, dir TEXT, capability_id TEXT, capability_version TEXT,
  started_at TEXT, duration_ms INTEGER, category TEXT, code TEXT, outcome TEXT,
  classifier_calls INTEGER, llm_calls INTEGER, escalated_to_human INTEGER,
  steps_ok INTEGER, steps_total INTEGER, drift_resolved INTEGER, drift_first_choice INTEGER,
  mtime REAL
);
CREATE INDEX IF NOT EXISTS runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS runs_capability ON runs(capability_id);
CREATE TABLE IF NOT EXISTS capabilities (
  file TEXT PRIMARY KEY, id TEXT, version TEXT, title TEXT, state TEXT, approved_by TEXT,
  approved_at TEXT, replays INTEGER, clean INTEGER, read_or_write TEXT, mtime REAL
);
"""

RUN_FIELDS = tuple(
    "run_id capability_id capability_version started_at duration_ms category code outcome "
    "classifier_calls llm_calls escalated_to_human steps_ok steps_total "
    "drift_resolved drift_first_choice".split()
)
CARD_FIELDS = tuple(
    "file id version title state approved_by approved_at replays clean read_or_write".split()
)
RUN_COLS, CARD_COLS = ", ".join(RUN_FIELDS), ", ".join(CARD_FIELDS)


def run_row(r: tuple[Any, ...]) -> dict[str, Any]:
    row = dict(zip(RUN_FIELDS, r, strict=True))
    row["escalated_to_human"] = bool(row["escalated_to_human"])
    row["drift"] = {
        "steps_resolved": row.pop("drift_resolved"),
        "first_choice": row.pop("drift_first_choice"),
    }
    return row


def card_row(r: tuple[Any, ...]) -> dict[str, Any]:
    row = dict(zip(CARD_FIELDS, r, strict=True))
    row["reliability"] = {"replays": row.pop("replays"), "clean": row.pop("clean")}
    return row
