"""The back office: signing the menu, holding the tasting, and the chef's evening.

The page can show a card, but somebody has to sign it, taste it, or cook it
fresh. This is the office that does those things and pins a running note on
the board ("plate 1: clean") for anyone watching. Signing and retiring are
quick, done at the desk. Tasting and authoring take a while, so each is handed
to a cook in the back with a ticket number, and the board is how you follow it.
Nothing here forges a signature: the real rules live in ``compile/approve.py``.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Route

from ...author.run import CHECKS, check_for, load_dotenv
from ...compile.approve import NotApprovable, approve, deprecate
from ...compile.verify import Check, verify
from ...kernel.evidence import Recorder, new_run_id
from ...schema.capability import Capability
from ...surface.base import Surface
from .authoring import Authoring, Busy, Kit, NoModel, browser_kit
from .index import Index
from .settings import Settings
from .store import NotFound, _plain

SurfaceFor = Callable[[Capability], Surface]
Checks = dict[str, Callable[[str], Check]]


def _browser(capability: Capability) -> Surface:
    from ...surface.browser.surface import BrowserSurface

    return BrowserSurface(capability.safety.allowed_hosts, headless=True)


class Jobs:
    def __init__(
        self,
        settings: Settings,
        publish: Callable[[dict[str, Any]], None],
        *,
        surface_for: SurfaceFor = _browser,
        checks: Checks = CHECKS,
        kit: Kit = browser_kit,
        model: Any = None,
        dotenv: Path = Path(".env"),
        index: Index | None = None,
    ) -> None:
        self.settings, self.publish, self.index = settings, publish, index
        self.surface_for, self.checks = surface_for, checks
        self.authoring = Authoring(settings, self._publish_author, kit, model, dotenv)
        self.states: dict[str, dict[str, Any]] = {}
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self._n = 0

    def _say(self, job_id: str, state: str, line: str) -> None:
        job = self.states.setdefault(job_id, {"job_id": job_id, "state": state, "lines": []})
        job["state"] = state
        job["lines"].append(line)
        self.publish({"type": "job", "job_id": job_id, "state": state, "line": line})

    def _publish_author(self, message: dict[str, Any]) -> None:
        job_id = str(message["job_id"])
        job = self.states.setdefault(job_id, {"job_id": job_id, "lines": []})
        job["state"] = message["state"]
        job["lines"].append(message["line"])
        done = self.authoring.compiled
        if self.index is not None and message["state"] == "done" and done:
            self.index.upsert_capability(self.settings.capabilities / done)
        self.publish(message)

    # ---- the desk ----------------------------------------------------------------------

    def _path(self, file: str) -> Path:
        path = self.settings.capabilities / _plain(file)
        if not path.is_file():
            raise NotFound(f"no capability card named {file}")
        return path

    def _load(self, file: str) -> Capability:
        return Capability.model_validate_json(self._path(file).read_text())

    def _save(self, file: str, card: Capability) -> dict[str, Any]:
        text = card.model_dump_json(indent=2, exclude_none=True) + "\n"
        self._path(file).write_text(text)
        if self.index is not None:
            self.index.upsert_capability(self._path(file))
        return card.model_dump(mode="json", exclude_none=True)

    def approve(self, file: str, by: str) -> dict[str, Any]:
        return self._save(file, approve(self._load(file), by))

    def deprecate(self, file: str, by: str, why: str) -> dict[str, Any]:
        return self._save(file, deprecate(self._load(file), by, why))

    # ---- the tasting -------------------------------------------------------------------

    def verify(
        self, file: str, trials: list[dict[str, Any]], check: str | None, env: dict[str, str]
    ) -> str:
        card = self._load(file)
        load_dotenv()
        env = {**os.environ, **env}
        try:
            name = check_for(card, check)
        except SystemExit as e:
            raise ValueError(str(e)) from e
        if name not in self.checks:
            raise ValueError(f"unknown check {name!r}; known: {sorted(self.checks)}")
        if "BASE_URL" not in env:
            raise ValueError("env needs BASE_URL, for the independent check")
        self._n += 1
        job_id = f"verify{self._n}"
        self._say(job_id, "running", f"independent check: {name}")
        coro = self._verify(job_id, file, card, trials, self.checks[name](env["BASE_URL"]), env)
        self.tasks[job_id] = asyncio.create_task(coro)
        return job_id

    async def _verify(
        self,
        job_id: str,
        file: str,
        card: Capability,
        trials: list[dict[str, Any]],
        check: Check,
        env: dict[str, str],
    ) -> None:
        try:
            verdict = await verify(
                card,
                trials,
                lambda: self.surface_for(card),
                lambda n: Recorder(new_run_id(f"verify{n}"), root=self.settings.evidence),
                check,
                env,
            )
            for number, plate in enumerate(verdict.plates, start=1):
                seen = "clean" if plate.clean else plate.reason
                self._say(job_id, "running", f"plate {number}: {seen}")
            if not verdict.verified:
                self._say(job_id, "failed", "stays in draft: " + "; ".join(verdict.reasons))
                return
            self._save(file, verdict.capability)
            ref = verdict.capability.ref
            self._say(job_id, "done", f"verified {ref} after {len(trials)} clean plates")
        except Exception as e:
            self._say(job_id, "failed", str(e) or type(e).__name__)


# ---- the doors -------------------------------------------------------------------------


def _failure(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def _body(request: Request) -> dict[str, Any]:
    if not await request.body():
        return {}
    try:
        data = await request.json()
    except ValueError as e:
        raise ValueError("body must be JSON") from e
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    return data


def _door(work: Callable[[Request, dict[str, Any]], Any], needs_body: bool = True) -> Any:
    async def handler(request: Request) -> Response:
        try:
            data = await _body(request) if needs_body else {}
            return JSONResponse(work(request, data))
        except NotFound as e:
            return _failure(str(e), 404)
        except (NotApprovable, Busy, NoModel) as e:
            return _failure(str(e), 409)
        except ValueError as e:
            return _failure(str(e), 400)

    return handler


def job_routes(jobs: Jobs) -> list[BaseRoute]:
    def who(data: dict[str, Any]) -> str:
        return str(data.get("by") or "").strip()

    def job(request: Request, data: dict[str, Any]) -> Any:
        found = jobs.states.get(request.path_params["job_id"])
        if found is None:
            raise NotFound("no such job")
        return found

    def start_verify(request: Request, data: dict[str, Any]) -> Any:
        trials = data.get("trials")
        if not isinstance(trials, list) or not all(isinstance(t, dict) for t in trials):
            raise ValueError("trials must be a list of input objects")
        env = {str(k): str(v) for k, v in (data.get("env") or {}).items()}
        check = data.get("check") or None
        return {"job_id": jobs.verify(request.path_params["file"], trials, check, env)}

    def confirm(request: Request, data: dict[str, Any]) -> Any:
        jobs.authoring.confirm(str(data.get("decision", "")), who(data))
        return {"ok": True}

    def stop(request: Request, data: dict[str, Any]) -> Any:
        jobs.authoring.stop()
        return {"ok": True}

    def post(path: str, work: Callable[[Request, dict[str, Any]], Any]) -> BaseRoute:
        return Route(path, _door(work), methods=["POST"])

    return [
        post(
            "/api/capabilities/{file}/approve",
            lambda r, d: jobs.approve(r.path_params["file"], who(d)),
        ),
        post(
            "/api/capabilities/{file}/deprecate",
            lambda r, d: jobs.deprecate(r.path_params["file"], who(d), str(d.get("why") or "")),
        ),
        post("/api/capabilities/{file}/verify", start_verify),
        post("/api/author/start", lambda r, d: {"job_id": jobs.authoring.start(d)}),
        Route("/api/author", _door(lambda r, d: jobs.authoring.state(), False)),
        post("/api/author/confirm", confirm),
        post("/api/author/stop", stop),
        Route("/api/jobs/{job_id}", _door(job, False)),
    ]
