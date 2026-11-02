"""The weekly tally on the back-office whiteboard: what happened, counted from the receipts.

A shop manager does not re-read every till slip. At the end of the day they
total the slips into a few numbers: how many sales, how many refunds, which
customers are still waiting at the counter. These are those totals, built
only from the cards and the evidence folders, never from a model.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...kernel.episodes import Episodes
from ...schema.results import RunResult

if TYPE_CHECKING:
    from .store import Store

RECENT = 50  # how many newest runs have their logs opened for pauses


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def when(stamp: str) -> datetime:
    t = datetime.fromisoformat(stamp)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def run_row(r: RunResult) -> dict[str, Any]:
    """One line of the runs table, the same shape whether it came from a file or the index."""
    return {
        "run_id": r.run_id,
        "capability_id": r.capability_id,
        "capability_version": r.capability_version,
        "started_at": r.started_at,
        "duration_ms": r.duration_ms,
        "category": r.category.value,
        "code": r.code.value,
        "outcome": r.outcome,
        "classifier_calls": r.classifier_calls,
        "llm_calls": r.llm_calls,
        "escalated_to_human": r.escalated_to_human,
        "steps_ok": sum(s.status in ("ok", "already_done") for s in r.steps),
        "steps_total": len(r.steps),
        "drift": r.drift.model_dump(mode="json"),
    }


def drift(store: Store) -> dict[str, Any]:
    firsts = {}
    for _, cap in store.cards():
        for s in cap.steps:
            t = cap.targets.get(s.target or "")
            if t:
                firsts[(cap.id, s.id)] = t.ladder[0].rung
    counts: dict[tuple[str, str, str], dict[str, Any]] = {}
    healing = []
    for _, r in store.results():  # newest first, so the first sighting is the last run
        for st in r.steps:
            if st.rung:
                c = counts.setdefault(
                    (r.capability_id, st.step_id, st.rung),
                    {"count": 0, "last_run": r.run_id},
                )
                c["count"] += 1
            first = firsts.get((r.capability_id, st.step_id))
            off_first = bool(st.rung and first and st.rung != first)
            if off_first or st.status in ("recovered", "bridged"):
                healing.append(
                    {
                        "run_id": r.run_id,
                        "step_id": st.step_id,
                        "rung": st.rung,
                        "accepted": st.status in ("ok", "recovered"),
                    }
                )
    rungs = [{"capability_id": c, "step_id": s, "rung": g, **v} for (c, s, g), v in counts.items()]
    return {"rungs": rungs, "healing": healing, "calibration": _calibration(store)}


def _calibration(store: Store) -> list[dict[str, Any]]:
    path = store.settings.episodes
    if path is None or not path.is_file():
        return []
    bins = Episodes(path).calibration()
    return [
        {
            "question": "all",
            "lo": b.low,
            "hi": b.high,
            "n": b.count,
            "accepted": b.held,
            "rate": b.rate,
        }
        for b in bins
    ]


def _open_pauses(logs: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    waiting = []
    for run_id, d in logs:
        log = d / "log.jsonl"
        if not log.is_file():
            continue
        open_event = None
        for e in lines(log):
            if e.get("event") == "rung3.paused":
                open_event = e
            elif e.get("event") == "rung3.handed_back":
                open_event = None
        if open_event:
            waiting.append(
                {
                    "run_id": run_id,
                    "step": open_event.get("step"),
                    "expected": open_event.get("expected"),
                    "since": open_event.get("at"),
                }
            )
    return waiting


def summary(store: Store) -> dict[str, Any]:
    if store.index is not None:  # the drawer counts; only the newest 50 logs are opened
        cards = store.index.capabilities()
        waiting = _open_pauses(store.index.run_dirs(RECENT))
        counts = store.index.summary_counts()
        approved = sum(c["state"] == "approved" for c in cards)
        return {"capabilities": len(cards), "approved": approved, **counts} | _open(waiting)
    results = store.results()
    today = datetime.now(UTC).date()
    waiting = _open_pauses([(r.run_id, d) for d, r in results])
    caps = [c for _, c in store.cards()]
    return {
        "capabilities": len(caps),
        "approved": sum(c.lifecycle.state == "approved" for c in caps),
        "runs_today": sum(when(r.started_at).astimezone(UTC).date() == today for _, r in results),
        "model_calls_on_replay": sum(r.llm_calls for _, r in results),
    } | _open(waiting)


def _open(waiting: list[dict[str, Any]]) -> dict[str, Any]:
    return {"escalations_open": len(waiting), "needs_a_person": waiting}
