"""The book at the maître d's stand: written in ink, before the guest speaks again.

A restaurant that only remembers the evening at closing time remembers it
wrong. So the maître d' writes each order into the book the moment it is
accepted, and the guest is not asked "anything else?" until the ink is dry.
If the lights go out, the book still says what was ordered.

This is the sink the guard writes to. Each accepted turn goes to disk twice,
synchronously, before ``write`` returns: once into ``trace.jsonl``, which the
compiler reads, and once into the run's hash-chained ``log.jsonl``, which an
auditor reads. Both go through the evidence recorder, so any value registered
as a secret is masked in both. The trace is supposed to hold blanks such as
``{{input.password}}`` rather than values; masking is the belt to that pair of
braces.

``load`` rebuilds the turns from ``trace.jsonl``. A handle comes back as plain
data rather than a live locator, because the page it pointed at is gone; the
compiler only needs the rungs that were probed while it was there.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from ..kernel.evidence import Recorder
from ..schema.target import Fingerprint, Rung
from ..schema.trace import Turn

TRACE = "trace.jsonl"


def _plain(value: Any) -> Any:
    """Anything a turn can hold, as JSON-safe data."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in dataclasses.asdict(value).items()}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def turn_to_dict(turn: Turn) -> dict[str, Any]:
    return {f.name: _plain(getattr(turn, f.name)) for f in dataclasses.fields(turn)}


def turn_from_dict(data: dict[str, Any]) -> Turn:
    data = dict(data)
    data["rungs"] = tuple(Rung.model_validate(r) for r in data.get("rungs") or ())
    data["ancestors"] = tuple(data.get("ancestors") or ())
    fp = data.get("fingerprint")
    data["fingerprint"] = Fingerprint.model_validate(fp) if fp else None
    return Turn(**data)


class TraceRecorder:
    """The sink: one turn in, one line on disk, before the model is asked again."""

    def __init__(self, recorder: Recorder) -> None:
        self.recorder = recorder
        self.path = recorder.dir / TRACE

    def write(self, turn: Turn) -> None:
        data = turn_to_dict(turn)
        with self.path.open("a") as fh:
            fh.write(self.recorder.mask(json.dumps(data, default=str)) + "\n")
            fh.flush()
        self.recorder.log("author.turn", **data)

    @staticmethod
    def load(path: Path) -> list[Turn]:
        if not path.exists():
            return []
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        return [turn_from_dict(json.loads(line)) for line in lines]
