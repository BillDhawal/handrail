"""The librarian's desk: it fetches what is on the shelves and never writes a word.

Three shelves hold everything the page shows: capability cards, evidence
folders, and the notebook of escalations. The librarian walks to a shelf,
reads what is there, and hands it over as plain dictionaries. It does not
tidy, edit or guess; if a book is not on the shelf it says so. It will also
refuse any request for a book by a name that points outside the shelves.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ...kernel.evidence import verify_chain
from ...schema.capability import Capability
from ...schema.effects import EffectClass
from ...schema.results import RunResult
from . import rollup
from .rollup import lines, when
from .settings import Settings


class NotFound(LookupError):
    pass


def _plain(name: str) -> str:
    if not name or "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"not a plain name: {name!r}")
    return name


def _writes(cap: Capability) -> bool:
    return any(s.effect.kind is EffectClass.COMMIT for s in cap.steps)


class Store:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # ---- cards -------------------------------------------------------------------------

    def cards(self) -> list[tuple[str, Capability]]:
        out = []
        for path in sorted(self.settings.capabilities.glob("*.json")):
            try:
                out.append((path.name, Capability.model_validate_json(path.read_text())))
            except (ValidationError, ValueError):
                continue
        return out

    def _card(self, file: str) -> Capability:
        path = self.settings.capabilities / _plain(file)
        if not path.is_file():
            raise NotFound(f"no capability card named {file}")
        try:
            return Capability.model_validate_json(path.read_text())
        except (ValidationError, ValueError) as e:
            raise NotFound(f"{file} is not a valid capability card") from e

    def capabilities(self) -> list[dict[str, Any]]:
        runs = self.results()
        out = []
        for file, cap in self.cards():
            rel = cap.lifecycle.reliability
            last = next((r for _, r in runs if r.capability_id == cap.id), None)
            out.append(
                {
                    "id": cap.id,
                    "version": cap.version,
                    "title": cap.title,
                    "description": cap.title,
                    "state": cap.lifecycle.state,
                    "approved_by": cap.lifecycle.approved_by,
                    "approved_at": cap.lifecycle.approved_at,
                    "reliability": {"replays": rel.replays, "clean": rel.clean},
                    "read_or_write": "write" if _writes(cap) else "read",
                    "inputs": [i.model_dump(mode="json") for i in cap.inputs],
                    "outputs": [o.model_dump(mode="json") for o in cap.outputs],
                    "file": file,
                    "last_run": last
                    and {
                        "run_id": last.run_id,
                        "category": last.category.value,
                        "started_at": last.started_at,
                    },
                    "success_rate": rel.clean / rel.replays if rel.replays else None,
                }
            )
        return out

    def capability(self, file: str) -> dict[str, Any]:
        cap = self._card(file)
        card = cap.model_dump(mode="json")
        card["versions"] = [
            {"file": f, "version": c.version, "state": c.lifecycle.state}
            for f, c in self.cards()
            if c.id == cap.id
        ]
        return card

    def checklist(self, file: str) -> dict[str, Any]:
        cap = self._card(file)
        state = cap.lifecycle.state
        commits = [s for s in cap.steps if s.effect.kind is EffectClass.COMMIT]
        leaked = _literal_secret_steps(cap)
        verified = state in ("verified", "approved")
        confirmed = all(s.effect.confirmed_by for s in commits)
        reasons = []
        if not verified:
            reasons.append(f"It is {state}; a card must be verified by replays before approval.")
        if not confirmed:
            names = ", ".join(s.id for s in commits if not s.effect.confirmed_by)
            reasons.append(f"These commit steps have not been confirmed by a person: {names}.")
        if leaked:
            reasons.append(f"These steps type a secret input as a literal: {', '.join(leaked)}.")
        ok = not leaked
        return {
            "verified": verified,
            "commits_confirmed": confirmed,
            "no_secret_literals": ok,
            "allowed_hosts": list(cap.safety.allowed_hosts),
            "plates": cap.lifecycle.reliability.clean,
            "reasons": reasons,
            "approvable": state == "verified" and confirmed and ok,
        }

    # ---- runs --------------------------------------------------------------------------

    def results(self) -> list[tuple[Path, RunResult]]:
        out = []
        if self.settings.evidence.is_dir():
            for d in self.settings.evidence.iterdir():
                f = d / "result.json"
                if d.is_dir() and f.is_file():
                    try:
                        out.append((d, RunResult.model_validate_json(f.read_text())))
                    except (ValidationError, ValueError):
                        continue
        out.sort(key=lambda p: when(p[1].started_at), reverse=True)
        return out

    def _dir(self, run_id: str) -> Path:
        """A run is found by the id inside its result, or failing that by its folder name."""
        _plain(run_id)
        for d, r in self.results():
            if r.run_id == run_id:
                return d
        d = self.settings.evidence / run_id
        if (d / "result.json").is_file():
            return d
        raise NotFound(f"no run named {run_id}")

    def runs(self, limit: int = 100) -> list[dict[str, Any]]:
        out = []
        for _, r in self.results()[: max(limit, 0)]:
            out.append(
                {
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
            )
        return out

    def run(self, run_id: str) -> dict[str, Any]:
        d = self._dir(run_id)
        log, journal = d / "log.jsonl", d / "journal.jsonl"
        ok, bad = verify_chain(log) if log.is_file() else (True, 0)
        total = len(log.read_text().splitlines()) if log.is_file() else 0
        shots = [
            {
                "label": p.stem,
                "png": p.name,
                "txt": p.with_suffix(".txt").name if p.with_suffix(".txt").is_file() else None,
            }
            for p in sorted(d.glob("*.png"))
        ]
        return {
            "result": json.loads((d / "result.json").read_text()),
            "events": lines(log) if log.is_file() else [],
            "journal": lines(journal) if journal.is_file() else None,
            "chain": {"ok": ok, "lines": total, "bad_line": bad},
            "files": sorted(p.name for p in d.iterdir() if p.is_file()),
            "screenshots": shots,
        }

    def run_file(self, run_id: str, name: str) -> Path:
        path = self._dir(run_id) / _plain(name)
        if not path.is_file():
            raise NotFound(f"run {run_id} has no file named {name}")
        return path

    # ---- roll-ups: see rollup.py -------------------------------------------------------

    def drift(self) -> dict[str, Any]:
        return rollup.drift(self)

    def summary(self) -> dict[str, Any]:
        return rollup.summary(self)


def _literal_secret_steps(cap: Capability) -> list[str]:
    """Steps that type a secret input by hand-written text instead of a template."""
    names = {i.name for i in cap.inputs if i.sensitivity == "secret"}
    hits = []
    for s in cap.steps:
        v = (s.op.value or "").strip()
        if not v or "{{" in v:
            continue
        label = f"{s.intent} {s.target or ''}".lower().replace("_", " ")
        if any(n.lower().replace("_", " ") in label for n in names):
            hits.append(s.id)
    return hits
