"""The card catalogue at the library door: it says where each book sits, and is never the book.

A library keeps its books on the shelves and a drawer of index cards by the
entrance. The drawer saves you walking every aisle to find "runs from last
Tuesday". But if a card is lost, torn or out of date, nobody mourns: the
librarian walks the shelves once and writes the drawer again. This is that
drawer. The capability cards and the evidence folders stay the truth; this
file only remembers where they are and a few facts about each, and a file
whose modified-time moved since the card was written is simply read again.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ...schema.capability import Capability
from ...schema.effects import EffectClass
from ...schema.results import RunResult
from .index_rows import (
    CARD_COLS,
    RUN_COLS,
    SCHEMA,
    SCHEMA_VERSION,
    card_row,
    run_row,
)
from .settings import Settings


class Index:
    def __init__(self, path: Path | str = ":memory:") -> None:
        self.path = str(path)
        self.synced_at: str | None = None
        self._lock = threading.RLock()
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._open()
        except sqlite3.DatabaseError:  # not a database at all: the drawer is rebuilt, not mended
            self.db.close()
            for suffix in ("", "-wal", "-shm"):
                Path(self.path + suffix).unlink(missing_ok=True)
            self._open()

    def _open(self) -> None:
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        row = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row and row[0] != SCHEMA_VERSION:  # old layout: drop the tables, sync refills them
            self.db.executescript("DROP TABLE IF EXISTS runs; DROP TABLE IF EXISTS capabilities;")
        self.db.executescript(SCHEMA)
        self.db.execute(
            "INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)", (SCHEMA_VERSION,)
        )
        row = self.db.execute("SELECT value FROM meta WHERE key='synced_at'").fetchone()
        self.synced_at = row[0] if row else None
        self.db.commit()

    # ---- walking the shelves -----------------------------------------------------------

    def sync(self, settings: Settings) -> None:
        """Re-read what moved, forget what vanished. Untouched files cost one stat each."""
        with self._lock:
            self._sync_runs(settings.evidence)
            self._sync_cards(settings.capabilities)
            self.synced_at = datetime.now(UTC).isoformat()
            self.db.execute(
                "INSERT OR REPLACE INTO meta VALUES ('synced_at', ?)", (self.synced_at,)
            )
            self.db.commit()

    def _sync_runs(self, evidence: Path) -> None:
        known = dict(self.db.execute("SELECT dir, mtime FROM runs"))
        seen: set[str] = set()
        base = evidence.resolve()
        for d in base.iterdir() if base.is_dir() else []:
            try:
                mtime = (d / "result.json").stat().st_mtime
            except OSError:
                continue
            seen.add(str(d))
            if known.get(str(d)) != mtime:
                self._put_run(d, mtime)
        self._forget("runs", "dir", known.keys() - seen)

    def _sync_cards(self, capabilities: Path) -> None:
        known = dict(self.db.execute("SELECT file, mtime FROM capabilities"))
        seen: set[str] = set()
        base = capabilities.resolve()
        for f in base.glob("*.json") if base.is_dir() else []:
            try:
                mtime = f.stat().st_mtime
            except OSError:
                continue
            seen.add(f.name)
            if known.get(f.name) != mtime:
                self._put_card(f, mtime)
        self._forget("capabilities", "file", known.keys() - seen)

    def _forget(self, table: str, column: str, gone: set[str]) -> None:
        self.db.executemany(f"DELETE FROM {table} WHERE {column}=?", [(g,) for g in gone])

    # ---- one file at a time ------------------------------------------------------------

    def upsert_run(self, directory: Path | str) -> bool:
        d = Path(directory).resolve()
        with self._lock:
            try:
                mtime = (d / "result.json").stat().st_mtime
            except OSError:
                return False
            ok = self._put_run(d, mtime)
            self.db.commit()
            return ok

    def _put_run(self, d: Path, mtime: float) -> bool:
        try:
            r = RunResult.model_validate_json((d / "result.json").read_text())
        except (OSError, ValidationError, ValueError):
            self.db.execute("DELETE FROM runs WHERE dir=?", (str(d),))
            return False
        ok = sum(s.status in ("ok", "already_done") for s in r.steps)
        values: tuple[Any, ...] = (
            r.run_id,
            r.capability_id,
            r.capability_version,
            r.started_at,
            r.duration_ms,
        )
        values += (r.category.value, r.code.value, r.outcome, r.classifier_calls, r.llm_calls)
        values += (int(r.escalated_to_human), ok, len(r.steps))
        values += (r.drift.steps_resolved, r.drift.first_choice, str(d), mtime)
        marks = ",".join("?" * len(values))
        self.db.execute(
            f"INSERT OR REPLACE INTO runs ({RUN_COLS}, dir, mtime) VALUES ({marks})", values
        )
        return True

    def upsert_capability(self, file: Path | str) -> bool:
        f = Path(file)
        with self._lock:
            try:
                mtime = f.stat().st_mtime
            except OSError:
                self.db.execute("DELETE FROM capabilities WHERE file=?", (f.name,))
                self.db.commit()
                return False
            ok = self._put_card(f, mtime)
            self.db.commit()
            return ok

    def _put_card(self, f: Path, mtime: float) -> bool:
        try:
            cap = Capability.model_validate_json(f.read_text())
        except (OSError, ValidationError, ValueError):
            self.db.execute("DELETE FROM capabilities WHERE file=?", (f.name,))
            return False
        life = cap.lifecycle
        writes = any(s.effect.kind is EffectClass.COMMIT for s in cap.steps)
        rel = life.reliability
        values: tuple[Any, ...] = (
            f.name,
            cap.id,
            cap.version,
            cap.title,
            life.state,
            life.approved_by,
        )
        values += (life.approved_at, rel.replays, rel.clean, "write" if writes else "read", mtime)
        marks = ",".join("?" * len(values))
        self.db.execute(
            f"INSERT OR REPLACE INTO capabilities ({CARD_COLS}, mtime) VALUES ({marks})", values
        )
        return True

    # ---- asking the drawer -------------------------------------------------------------

    def runs(
        self,
        limit: int = 100,
        capability_id: str | None = None,
        category: str | None = None,
        escalated: bool | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        args: list[Any] = []
        if capability_id is not None:
            where.append("capability_id=?")
            args.append(capability_id)
        if category is not None:
            where.append("category=?")
            args.append(category)
        if escalated is not None:
            where.append("escalated_to_human=?")
            args.append(int(escalated))
        clause = "WHERE " + " AND ".join(where) if where else ""
        sql = f"SELECT {RUN_COLS} FROM runs {clause} ORDER BY started_at DESC, run_id LIMIT ?"
        with self._lock:
            return [run_row(r) for r in self.db.execute(sql, (*args, max(limit, 0)))]

    def run_dirs(self, limit: int) -> list[tuple[str, Path]]:
        sql = "SELECT run_id, dir FROM runs ORDER BY started_at DESC, run_id LIMIT ?"
        with self._lock:
            return [(i, Path(d)) for i, d in self.db.execute(sql, (max(limit, 0),))]

    def dir_of(self, run_id: str) -> Path | None:
        with self._lock:
            row = self.db.execute("SELECT dir FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return Path(row[0]) if row else None

    def capabilities(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute(f"SELECT {CARD_COLS} FROM capabilities ORDER BY file")
            return [card_row(r) for r in rows]

    def last_run(self, capability_id: str) -> dict[str, Any] | None:
        sql = (
            "SELECT run_id, category, started_at FROM runs WHERE capability_id=? "
            "ORDER BY started_at DESC, run_id LIMIT 1"
        )
        with self._lock:
            row = self.db.execute(sql, (capability_id,)).fetchone()
        return {"run_id": row[0], "category": row[1], "started_at": row[2]} if row else None

    def summary_counts(self) -> dict[str, int]:
        """Runs started today (UTC; sqlite's date() folds offsets to UTC) and model calls summed."""
        sql = (
            "SELECT COALESCE(SUM(date(started_at)=date('now')), 0), COALESCE(SUM(llm_calls), 0) "
            "FROM runs"
        )
        with self._lock:
            today, calls = self.db.execute(sql).fetchone()
        return {"runs_today": today, "model_calls_on_replay": calls}

    def counts(self) -> dict[str, int]:
        with self._lock:
            runs = self.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            caps = self.db.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]
        return {"runs": runs, "capabilities": caps}

    def close(self) -> None:
        with self._lock:
            self.db.commit()
            self.db.close()
