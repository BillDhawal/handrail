"""The front desk: it answers the door, points visitors to a shelf, and hands over the paper.

A hotel front desk does not cook or clean. A guest asks a question, the clerk
looks it up in the right book, and reads back the answer, or says plainly
"we have no such room". This module is the clerk. Each GET route asks the
store one question and answers in JSON; a missing thing is a 404, a name that
tries to wander outside the shelves is a 400. Anything not under ``/api`` is
the static page.

``build_app`` builds the routes as a plain list so later jobs (a live run, a
verify, an approval) can add their own doors without rebuilding the desk.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import BaseRoute, Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from .broadcast import Broadcast
from .jobs import Jobs, job_routes
from .live import Busy, LiveRun
from .live import _surface as default_surface
from .settings import Settings
from .store import NotFound, Store

STATIC = Path(__file__).parent / "static"
Handler = Callable[[Request], Awaitable[Response]]


def _failure(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _answer(ask: Callable[[Request], Any]) -> Handler:
    async def handler(request: Request) -> Response:
        try:
            return JSONResponse(ask(request))
        except NotFound as e:
            return _failure(str(e), 404)
        except ValueError as e:
            return _failure(str(e), 400)

    return handler


class NoStore(BaseHTTPMiddleware):
    """Nothing here is worth caching: a fixed page should show on the next reload."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response


def read_routes(store: Store) -> list[BaseRoute]:
    def run_file(request: Request) -> Response:
        p = request.path_params
        return FileResponse(store.run_file(p["run_id"], p["name"]))

    async def file_handler(request: Request) -> Response:
        try:
            return run_file(request)
        except NotFound as e:
            return _failure(str(e), 404)
        except ValueError as e:
            return _failure(str(e), 400)

    def limit(request: Request) -> int:
        try:
            return int(request.query_params.get("limit", "100"))
        except ValueError as e:
            raise ValueError("limit must be a whole number") from e

    return [
        Route("/api/summary", _answer(lambda r: store.summary())),
        Route("/api/capabilities", _answer(lambda r: store.capabilities())),
        Route(
            "/api/capabilities/{file}", _answer(lambda r: store.capability(r.path_params["file"]))
        ),
        Route(
            "/api/capabilities/{file}/checklist",
            _answer(lambda r: store.checklist(r.path_params["file"])),
        ),
        Route("/api/runs", _answer(lambda r: store.runs(limit(r)))),
        Route("/api/runs/{run_id}", _answer(lambda r: store.run(r.path_params["run_id"]))),
        Route("/api/runs/{run_id}/files/{name}", file_handler),
        Route("/api/drift", _answer(lambda r: store.drift())),
    ]


def live_routes(live: LiveRun) -> list[BaseRoute]:
    async def body(request: Request) -> dict[str, Any]:
        try:
            data = await request.json()
        except ValueError as e:
            raise ValueError("body must be JSON") from e
        if not isinstance(data, dict):
            raise ValueError("body must be a JSON object")
        return data

    async def start(request: Request) -> Response:
        try:
            return JSONResponse(live.start(await body(request)))
        except Busy as e:
            return _failure(str(e), 409)
        except (ValueError, SystemExit) as e:
            return _failure(str(e), 400)

    async def act(request: Request) -> Response:
        try:
            data = await body(request)
        except ValueError as e:
            return _failure(str(e), 400)
        action, by = str(data.get("action", "")), str(data.get("by") or "someone")
        said = live.act(action, by, data.get("screen"))
        return JSONResponse({"ok": True}) if said == "ok" else _failure(said, 409)

    async def socket(ws: WebSocket) -> None:
        """Read the queue aloud until the listener hangs up; the hang-up is heard, not guessed."""
        await ws.accept()
        q = live.broadcast.subscribe()
        hangup = asyncio.ensure_future(ws.receive())
        try:
            while not hangup.done():
                item = asyncio.ensure_future(q.get())
                await asyncio.wait({item, hangup}, return_when=asyncio.FIRST_COMPLETED)
                if item.done():
                    await ws.send_json(item.result())
                else:
                    item.cancel()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            hangup.cancel()
            live.broadcast.unsubscribe(q)

    return [
        Route("/api/live", _answer(lambda r: live.state())),
        Route("/api/live/start", start, methods=["POST"]),
        Route("/api/live/act", act, methods=["POST"]),
        WebSocketRoute("/ws", socket),
    ]


async def _no_such_api(request: Request) -> Response:
    return _failure("no such route", 404)


def build_app(settings: Settings, surface_factory: Any = None) -> Starlette:
    if not STATIC.exists():
        STATIC.mkdir(parents=True)
        (STATIC / "index.html").write_text(
            "<!doctype html><title>Handrail</title><h1>Handrail</h1>"
        )
    store = Store(settings)
    routes: list[BaseRoute] = read_routes(store)
    broadcast = Broadcast()
    live = LiveRun(settings, broadcast, surface_factory or default_surface)
    routes += live_routes(live)
    routes += job_routes(Jobs(settings, broadcast.publish))
    routes += [Route("/api/{rest:path}", _no_such_api)]
    routes += [Mount("/", app=StaticFiles(directory=STATIC, html=True), name="static")]
    return Starlette(routes=routes, middleware=[Middleware(NoStore)])


async def ui_command(args: argparse.Namespace) -> int:
    import uvicorn

    episodes = Path(args.episodes) if args.episodes else None
    settings = Settings(Path(args.capabilities), Path(args.evidence), episodes, port=args.port)
    server = uvicorn.Server(
        uvicorn.Config(build_app(settings), host=settings.host, port=settings.port)
    )
    print(f"Handrail UI on http://{settings.host}:{settings.port}")
    await server.serve()
    return 0


def register(sub: Any) -> None:
    u = sub.add_parser("ui", help="serve the web UI on localhost")
    u.add_argument("--port", type=int, default=8090)
    u.add_argument("--capabilities", default="capabilities")
    u.add_argument("--evidence", default="evidence/runs")
    u.add_argument("--episodes", default="evidence/episodes.db")
    u.set_defaults(run=ui_command)
