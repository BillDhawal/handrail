"""Evidence: the flight recorder, with a seal on every page.

An aircraft's black box does two things. It records everything, in order, as
it happens - not a summary written afterwards. And it is built so that a page
cannot be quietly altered: investigators must be able to trust what they read.

The recorder here does both. Every event is appended to ``log.jsonl`` the
moment it happens, and each line carries the hash of the line before it, so
the file is a chain. Change one character in the middle and every line after
it stops verifying. ``verify_chain`` is the investigator's tool.

The recorder is also one of the four boundaries where secrets are masked
(surface, logger, evidence writer, serialiser). A password registered here is
replaced with ``[secret]`` in anything the recorder writes, whoever wrote it.
Masking lives at the boundary, never at the call site, so a forgotten call
site cannot leak. This is a first, deliberately small version of that rule;
the fuller redactor arrives with the browser surface.
"""

from __future__ import annotations

import hashlib
import json
import secrets as _secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..surface.base import Surface

MASK = "[secret]"


def new_run_id(kind: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{kind}_{stamp}_{_secrets.token_hex(3)}"


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


class Recorder:
    def __init__(
        self, run_id: str, root: Path = Path("evidence/runs"), secrets: tuple[str, ...] = ()
    ) -> None:
        self.run_id = run_id
        self.dir = root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._secrets: list[str] = [s for s in secrets if s]
        self._prev = "genesis"
        self._seq = 0

    # -- masking ----------------------------------------------------------------

    def add_secret(self, value: str | None) -> None:
        """Register a value that must never appear in evidence, however it got there."""
        if value and value not in self._secrets:
            self._secrets.append(value)

    def mask(self, text: str) -> str:
        for s in sorted(self._secrets, key=len, reverse=True):
            text = text.replace(s, MASK)
        return text

    def _mask_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.mask(value)
        if isinstance(value, dict):
            return {k: self._mask_value(v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [self._mask_value(v) for v in value]
        return value

    # -- writing ----------------------------------------------------------------

    def log(self, event: str, **fields: Any) -> None:
        """Append one sealed line. The seal covers this line and points at the last."""
        self._seq += 1
        body: dict[str, Any] = {
            "seq": self._seq,
            "at": datetime.now(UTC).isoformat(),
            "event": event,
            **self._mask_value(fields),
        }
        digest = hashlib.sha256((self._prev + _canonical(body)).encode()).hexdigest()
        line = {**body, "prev": self._prev, "hash": digest}
        with (self.dir / "log.jsonl").open("a") as fh:
            fh.write(json.dumps(line, default=str) + "\n")
        self._prev = digest

    def write_json(self, name: str, payload: BaseModel | dict[str, Any]) -> Path:
        data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        path = self.dir / name
        path.write_text(json.dumps(self._mask_value(data), indent=2, default=str))
        return path

    async def capture(self, surface: Surface, label: str) -> dict[str, str | None]:
        """Photograph the current screen. Never raises: this runs inside error handlers."""
        try:
            bundle = await surface.evidence()
        except Exception as exc:  # noqa: BLE001 - failing to document a failure must not replace it
            self.log("evidence.capture_failed", label=label, error=str(exc))
            return {"text": None, "screenshot": None}
        refs: dict[str, str | None] = {"text": None, "screenshot": None}
        if bundle.text:
            rel = f"{label}.txt"
            (self.dir / rel).write_text(self.mask(bundle.text))
            refs["text"] = rel
        if bundle.screenshot_png:
            rel = f"{label}.png"
            (self.dir / rel).write_bytes(bundle.screenshot_png)
            refs["screenshot"] = rel
        return refs


def verify_chain(log_path: Path) -> tuple[bool, int]:
    """Walk the chain. Returns (intact, first bad line number or 0)."""
    prev = "genesis"
    for number, raw in enumerate(log_path.read_text().splitlines(), start=1):
        line = json.loads(raw)
        claimed = line.pop("hash")
        if line.pop("prev") != prev:
            return False, number
        if hashlib.sha256((prev + _canonical(line)).encode()).hexdigest() != claimed:
            return False, number
        prev = claimed
    return True, 0
