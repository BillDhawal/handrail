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

if TYPE_CHECKING:
    from .store import Store


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def when(stamp: str) -> datetime:
    t = datetime.fromisoformat(stamp)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


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


def summary(store: Store) -> dict[str, Any]:
    cards = store.cards()
    results = store.results()
    today = datetime.now(UTC).date()
    waiting = []
    for d, r in results:
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
                    "run_id": r.run_id,
                    "step": open_event.get("step"),
                    "expected": open_event.get("expected"),
                    "since": open_event.get("at"),
                }
            )
    return {
        "capabilities": len(cards),
        "approved": sum(c.lifecycle.state == "approved" for _, c in cards),
        "runs_today": sum(when(r.started_at).astimezone(UTC).date() == today for _, r in results),
        "model_calls_on_replay": sum(r.llm_calls for _, r in results),
        "escalations_open": len(waiting),
        "needs_a_person": waiting,
    }
