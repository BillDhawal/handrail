"""The guest's evening, watched from the pass window, with the owner's nod done by a button.

At the terminal the maître d' turns to the owner and asks "may I press this?".
On the web the owner is not standing there, so the question goes up on a
board ("row 7 is waiting for a person") and the evening pauses until
somebody presses a button on the page. Everything else is the same evening
as ``handrail author``: same guard, same book, same recipe writer. This file
only swaps the voice that asks, and keeps a board anyone can read.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...author.middleware import Decision
from ...author.run import load_dotenv
from ...compile.compiler import CompileError, Source, compile_trace
from ...schema.effects import EffectClass
from .settings import Settings

#: (allowed hosts) -> (surface, authorable view of it); the default opens a real browser.
Kit = Callable[[list[str]], tuple[Any, Any]]
DECISIONS = {"commit", "navigate", "stage", "deny"}


class Busy(RuntimeError):
    pass


class NoModel(RuntimeError):
    pass


def browser_kit(hosts: list[str]) -> tuple[Any, Any]:
    from ...surface.browser.queries import BrowserAuthoring
    from ...surface.browser.surface import BrowserSurface

    surface = BrowserSurface(hosts, headless=True)
    return surface, _Lazy(surface, BrowserAuthoring)


class _Lazy:
    """BrowserAuthoring needs the page, which exists only after `open`."""

    def __init__(self, surface: Any, make: Callable[[Any], Any]) -> None:
        self._surface, self._make, self._real = surface, make, None

    def _get(self) -> Any:
        if self._real is None:
            self._real = self._make(self._surface.page)
        return self._real

    async def describe(self, handle: Any) -> Any:
        return await self._get().describe(handle)

    def probe(self, handle: Any, control: Any) -> Any:
        return self._get().probe(handle, control)


def _key_needed(model: str) -> str | None:
    if model.startswith("anthropic:") or model.startswith("claude"):
        return "ANTHROPIC_API_KEY"
    if model.startswith("openai:"):
        return "OPENAI_API_KEY"
    return None


class Authoring:
    def __init__(
        self,
        settings: Settings,
        publish: Callable[[dict[str, Any]], None],
        kit: Kit = browser_kit,
        model: Any = None,
        dotenv: Path = Path(".env"),
    ) -> None:
        self.settings, self.publish, self.kit = settings, publish, kit
        self.model, self.dotenv = model, dotenv
        self.task: asyncio.Task[None] | None = None
        self.job_id: str | None = None
        self._n = 0
        self._reset()

    def _reset(self) -> None:
        self.session: Any = None
        self.surface: Any = None
        self.pending: dict[str, Any] | None = None
        self._future: asyncio.Future[Decision] | None = None
        self.model_calls = 0
        self.finished = False
        self.outcome: str | None = None
        self.compiled: str | None = None
        self.error: str | None = None

    def _say(self, state: str, line: str) -> None:
        self.publish({"type": "job", "job_id": self.job_id, "state": state, "line": line})

    @property
    def active(self) -> bool:
        return self.task is not None and not self.task.done()

    def state(self) -> dict[str, Any]:
        turns = [
            {
                "index": t.index,
                "intent": t.label or t.tool,
                "screen": t.signature_after,
                "verb": t.verb,
                "target": f"{t.role} {t.name!r}" if t.role else None,
                "effect": t.effect,
            }
            for t in (self.session.trace if self.session else [])
        ]
        return {
            "active": self.active,
            "turns": turns,
            "pending_confirm": self.pending,
            "model_calls": self.model_calls,
            "finished": self.finished,
            "outcome": self.outcome,
            "compiled": self.compiled,
            "error": self.error,
        }

    def confirm(self, decision: str, by: str) -> None:
        if self._future is None or self._future.done():
            raise Busy("nothing is waiting for a person")
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {sorted(DECISIONS)}")
        effect = None if decision == "deny" else EffectClass(decision)
        self._future.set_result(Decision(effect, by.strip() or "someone"))

    def start(self, spec: dict[str, Any]) -> str:
        goal, entry, cid = (str(spec.get(k) or "").strip() for k in ("goal", "entry", "id"))
        out = str(spec.get("out") or f"{cid.replace('.', '-')}.authored.json")
        if not (goal and entry and cid):
            raise ValueError("goal, entry and id are required")
        if "/" in out or "\\" in out or ".." in out:
            raise ValueError(f"not a plain file name: {out!r}")
        if self.active:
            raise Busy("an authoring session is already running")
        model = self.model or str(spec.get("model") or "anthropic:claude-sonnet-5")
        if isinstance(model, str):
            load_dotenv(self.dotenv)
            need = _key_needed(model)
            if need and not os.environ.get(need):
                raise NoModel(f"{need} is not set; authoring needs a model key")
        self._reset()
        self._n += 1
        self.job_id = f"author{self._n}"
        self.task = asyncio.create_task(self._run(spec, model, goal, entry, cid, out))
        return self.job_id

    def stop(self) -> None:
        if not self.active or self.task is None:
            raise Busy("nothing is running")
        self.error = "stopped by operator"
        self.task.cancel()

    async def _ask(self, proposal: Any) -> Decision:
        what = f"{proposal.verb} {proposal.control.role} {proposal.control.name!r}"
        self._future = asyncio.get_running_loop().create_future()
        shown = {"index": proposal.index, "what": what, "screen": self._screen()}
        self.pending = shown
        self._say("running", f"waiting for a person to mark row {proposal.index}: {what}")
        try:
            return await self._future
        finally:
            self.pending = None

    def _screen(self) -> str:
        trace = self.session.trace if self.session else []
        return next((t.signature_after for t in reversed(trace) if t.signature_after), "")

    async def _run(
        self, spec: dict[str, Any], model: Any, goal: str, entry: str, cid: str, out: str
    ) -> None:
        from ...author.agent import author
        from ...author.middleware import Guard
        from ...author.recorder import TraceRecorder
        from ...author.tools import Session
        from ...kernel.evidence import Recorder, new_run_id

        hosts = [str(h) for h in spec.get("allow") or []]
        values = {str(k): v for k, v in (spec.get("inputs") or {}).items()}
        secrets = {str(s) for s in spec.get("secrets") or []}
        self._say("running", f"authoring {cid}")
        try:
            recorder = Recorder(new_run_id("author"), root=self.settings.evidence)
            for name in secrets & values.keys():
                recorder.add_secret(values[name])
            self.surface, authorable = self.kit(hosts)
            self.session = Session(self.surface, inputs=values, env=dict(os.environ))
            await self.surface.open(entry)
            guard = Guard(self.session, authorable, self._ask, TraceRecorder(recorder))
            if isinstance(model, str):
                from langchain.chat_models import init_chat_model

                model = init_chat_model(model)
            result = await author(model, guard, goal, int(spec.get("max_turns") or 40))
            self.model_calls, self.finished, self.outcome = (
                result.model_calls,
                result.finished,
                result.outcome,
            )
            self._say("running", f"turns={len(result.trace)} finished={result.finished}")
            source = Source(
                id=cid,
                title=goal,
                entry=entry,
                inputs=[
                    {"name": n, **({"sensitivity": "secret"} if n in secrets else {})}
                    for n in values
                ],
                values=values,
                screens=result.screens,
                paths=result.paths,
                trace=result.trace,
                allowed_hosts=hosts,
            )
            self._compile(source, out)
        except asyncio.CancelledError:
            self._fail(self.error or "stopped by operator")
        except Exception as e:
            self._fail(str(e) or type(e).__name__)
        finally:
            if self.surface is not None:
                await self.surface.close()

    def _compile(self, source: Source, out: str) -> None:
        try:
            capability = compile_trace(source)
        except CompileError as e:
            self._fail("not compiled: " + "; ".join(e.reasons))
            return
        path = self.settings.capabilities / out
        path.write_text(capability.model_dump_json(indent=2, exclude_none=True) + "\n")
        self.compiled = out
        self._say("done", f"compiled {capability.ref} -> {out}")

    def _fail(self, message: str) -> None:
        self.error = message
        self._say("failed", message)
