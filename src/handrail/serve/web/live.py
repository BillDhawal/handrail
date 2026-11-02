"""The stage manager with a window onto the stage: one show at a time, and the audience can watch.

A theatre runs one performance at a time. The stage manager starts it, a
camera in the wings sends a picture to the lobby screen twice a second, and
the prompt book (the recorder) is read aloud to anyone listening as each
line is written. If the lead freezes, the manager can call a person from
the audience on stage, and the person must say which scene they left the
set on before the show goes on. ``LiveRun`` is that manager; ``Broadcast``
is the lobby speaker; ``WebConsole`` is the stage door with the same rules
as the little HTTP console, minus the HTTP.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ...kernel.control import Baton, Exchange, IllegalExchange
from ...kernel.episodes import Episodes
from ...kernel.evidence import new_run_id
from ...replay.engine import ReplayEngine
from ...replay.journal import Journal
from ...schema.capability import Capability
from .broadcast import Broadcast, WebRecorder
from .settings import Settings

FRAME_EVERY_S = 0.5


class Busy(RuntimeError):
    """A run is already on stage."""


def _exchange(e: Exchange) -> dict[str, Any]:
    return {k: str(v) if k in ("frm", "to") else v for k, v in dataclasses.asdict(e).items()}


class WebConsole:
    """The console contract (baton, offer, act, handed_back, url) with the page as its door."""

    def __init__(self, broadcast: Broadcast, host: str = "127.0.0.1", port: int = 8090) -> None:
        self.baton = Baton()
        self.broadcast = broadcast
        self.host, self.port = host, port
        self.candidates: list[str] = []
        self.handed_back: str | None = None
        self.baton.watch(lambda e: broadcast.publish({"type": "baton", **self.snapshot()}))

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/#/live"

    def snapshot(self) -> dict[str, Any]:
        return {
            "owner": self.baton.owner.value,
            "history": [_exchange(e) for e in self.baton.history],
        }

    def offer(self, candidates: list[str]) -> None:
        self.candidates = list(candidates)
        self.handed_back = None

    def act(self, action: str, by: str, screen: str | None = None) -> str:
        try:
            if action == "hand_back":
                if screen not in self.candidates:
                    return f"hand back must name one of {self.candidates}"
                self.handed_back = screen
                self.baton.exchange("hand_back", by, f"on screen {screen!r}")
            elif action in ("take_over", "abort"):
                self.baton.exchange(action, by)
            else:
                return f"no such action {action!r}"
        except IllegalExchange as exc:
            return str(exc)
        return "ok"


def _surface(allowed_hosts: list[str], headless: bool) -> Any:
    from ...surface.browser.surface import BrowserSurface

    return BrowserSurface(allowed_hosts, headless)


class LiveRun:
    def __init__(
        self,
        settings: Settings,
        broadcast: Broadcast,
        surface_factory: Callable[[list[str], bool], Any] = _surface,
        poll_interval_s: float = 0.25,
    ) -> None:
        self.settings, self.broadcast = settings, broadcast
        self.surface_factory = surface_factory
        self.poll_interval_s = poll_interval_s
        self.console: WebConsole | None = None
        self.task: asyncio.Task[None] | None = None
        self._frames: asyncio.Task[None] | None = None
        self._last: dict[str, Any] = {}
        self.pause: dict[str, Any] | None = None

    def _note(self, message: dict[str, Any]) -> None:
        """Keep the engine's own words about the pause, so a page opened late can show them."""
        if message["event"] == "rung3.paused":
            self.pause = {
                "step": message.get("step"),
                "at": message["at"],
                "expected": list(message.get("expected") or []),
            }
        elif message["event"] == "rung3.handed_back":
            self.pause = None

    @property
    def active(self) -> bool:
        return self.task is not None and not self.task.done()

    def _card(self, name: str) -> Capability:
        if not name or "/" in name or ".." in name or "\\" in name:
            raise ValueError(f"not a capability file name: {name!r}")
        path = self.settings.capabilities / name
        if not path.is_file():
            raise ValueError(f"no such capability file: {name!r}")
        return Capability.model_validate_json(path.read_text())

    def start(self, spec: dict[str, Any]) -> dict[str, str]:
        if self.active:
            raise Busy("a run is already active")
        from ...cli import referee

        card = self._card(str(spec.get("file", "")))
        inputs = dict(spec.get("inputs") or {})
        headed = bool(spec.get("headed", False))
        self.pause = None
        recorder = WebRecorder(
            new_run_id("replay"),
            root=self.settings.evidence,
            broadcast=self.broadcast,
            on_event=self._note,
        )
        for item in card.inputs:  # before anything is logged; prepare() will not double-add
            if item.sensitivity == "secret" and item.name in inputs:
                recorder.add_secret(str(inputs[item.name]))
        journal = Journal.load(recorder.dir / "journal.jsonl")
        surface = self.surface_factory(card.safety.allowed_hosts, not headed)
        classifier = referee(spec.get("classifier"))
        self.console = (
            WebConsole(self.broadcast, self.settings.host, self.settings.port)
            if spec.get("console", True)
            else None
        )
        episodes = Episodes(self.settings.episodes) if self.settings.episodes else None
        engine = ReplayEngine(
            surface,
            recorder,
            env=dict(spec.get("env") or {}),
            poll_interval_s=self.poll_interval_s,
            classifier=classifier,
            episodes=episodes,
            console=self.console,
        )
        self._last = {"run_id": recorder.run_id, "capability_id": card.ref, "headed": headed}
        self._last |= {"result": None, "error": None}
        self.task = asyncio.create_task(self._run(engine, card, inputs, journal, surface))
        self._frames = asyncio.create_task(self._screencast(surface))
        self.broadcast.publish({"type": "live", **self.state()})
        return {"run_id": recorder.run_id}

    async def _run(
        self, engine: ReplayEngine, card: Capability, inputs: dict[str, Any], j: Journal, s: Any
    ) -> None:
        try:
            result = await engine.run(card, inputs, j)
            self._last["result"] = engine.recorder._mask_value(result.model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001 - a run never ends in a bare exception
            self._last["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                await s.close()
            except Exception as exc:  # noqa: BLE001
                self._last["error"] = self._last["error"] or f"close failed: {exc}"
            self._last["finished"] = True
            self.broadcast.publish({"type": "live", **self.state()})

    async def _screencast(self, surface: Any) -> None:
        while self.task is not None and not self.task.done():
            await asyncio.sleep(FRAME_EVERY_S)
            try:
                shot = await surface.page.screenshot(type="jpeg", quality=55)
            except Exception:  # noqa: BLE001 - no page, page closed: skip this frame
                continue
            self.broadcast.publish(
                {
                    "type": "frame",
                    "jpeg": base64.b64encode(shot).decode(),
                    "at": datetime.now(UTC).isoformat(),
                }
            )

    async def wait(self) -> None:
        if self.task is not None:
            await self.task
        if self._frames is not None:
            await self._frames

    def act(self, action: str, by: str, screen: str | None = None) -> str:
        if self.console is None or not self.active:
            return "no live run with a console"
        return self.console.act(action, by, screen)

    def state(self) -> dict[str, Any]:
        if not self._last:
            return {
                "active": False,
                "run_id": None,
                "capability_id": None,
                "state": "idle",
                "baton": None,
                "expected": [],
                "headed": False,
                "result": None,
                "pause": None,
            }
        c = self.console
        paused = c is not None and not c.baton.automation_may_act
        state = "finished" if self._last.get("finished") else "paused" if paused else "running"
        out = {
            "active": self.active,
            "run_id": self._last["run_id"],
            "capability_id": self._last["capability_id"],
            "state": state,
            "baton": c.snapshot() if c else None,
            "expected": list(c.candidates) if c else [],
            "headed": self._last["headed"],
            "result": self._last["result"],
            "pause": self.pause if paused else None,
        }
        if self._last["error"]:
            out["error"] = self._last["error"]
        return out
