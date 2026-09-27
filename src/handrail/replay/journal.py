"""The step journal: a notebook the engine writes in before it acts, never after.

Think of a cashier with a paper ledger. Before handing cash across the counter
she writes "paying out $500 to account 118" in the ledger. After the customer
has the money she writes "paid". If the lights go out between those two lines,
the ledger still says "paying out" with no "paid" beside it - and the one thing
she must never do when the lights come back is pay out again on the strength
of "I don't remember doing it". She checks the till. If she cannot check, she
calls a supervisor. She does not guess.

That is this file. Before any step that changes the application - a staged
form field, a posted transaction - the engine appends ``dispatched`` here, on
disk, and only then touches the surface. When the effect is confirmed it
appends ``observed``. The rule the rest of the engine is built on:

    A step that is dispatched and not observed is never re-executed.

Not on a retry, not after a restart, not when a supervisor or a model swears
the screen is back where it was. From that state the engine may run the step's
read-only probe to find out what happened, or hand the run to a person. It may
not act again. The prototype learned this by posting a bank hold twice, on two
different code paths; here it is one rule in one place.

The journal also records each screen the engine verified it was on, because
"where may we safely go back to" has the same answer: any screen after which
nothing was dispatched.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Kind = Literal["screen", "dispatched", "observed"]


@dataclass(frozen=True)
class Entry:
    seq: int
    kind: Kind
    name: str  # a screen name, or a step id


class Journal:
    """Append-only. There is deliberately no way to remove or rewrite an entry."""

    def __init__(self, path: Path | None = None) -> None:
        self._entries: list[Entry] = []
        self._path = path

    @classmethod
    def load(cls, path: Path) -> Journal:
        """Rebuild from disk, so a crashed run's doubts survive into the next."""
        journal = cls(path)
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    journal._entries.append(Entry(**json.loads(line)))
        return journal

    # -- writing ----------------------------------------------------------------

    def reached(self, screen: str) -> None:
        self._append("screen", screen)

    def dispatch(self, step_id: str) -> None:
        """Call this before the action. It does not return until the line is on disk."""
        self._append("dispatched", step_id)

    def observe(self, step_id: str) -> None:
        self._append("observed", step_id)

    def _append(self, kind: Kind, name: str) -> None:
        entry = Entry(seq=len(self._entries) + 1, kind=kind, name=name)
        if self._path is not None:
            with self._path.open("a") as fh:
                fh.write(json.dumps(asdict(entry)) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        self._entries.append(entry)

    # -- reading ----------------------------------------------------------------

    @property
    def entries(self) -> tuple[Entry, ...]:
        return tuple(self._entries)

    def in_doubt(self, step_id: str) -> bool:
        """Dispatched, and never since observed. The state nothing may re-run from."""
        state = None
        for e in self._entries:
            if e.name == step_id and e.kind in ("dispatched", "observed"):
                state = e.kind
        return state == "dispatched"

    def already_done(self, step_id: str) -> bool:
        return any(e.kind == "observed" and e.name == step_id for e in self._entries)

    def steps_in_doubt(self) -> list[str]:
        names = {e.name for e in self._entries if e.kind == "dispatched"}
        return sorted(n for n in names if self.in_doubt(n))

    def safe_rewind_targets(self) -> list[str]:
        """Screens after which nothing was dispatched, most recent first.

        Conservative on purpose: a dispatch after a screen makes that screen
        unsafe even if the step was later observed. Going back there would put
        the engine in front of a step it has already run, and "skip it, it is
        done" is a decision for the engine at that moment, not for this list.
        """
        safe: list[str] = []
        clean_since_last_dispatch = True
        for e in reversed(self._entries):
            if e.kind == "dispatched":
                clean_since_last_dispatch = False
            elif e.kind == "screen" and clean_since_last_dispatch and e.name not in safe:
                safe.append(e.name)
        return safe
