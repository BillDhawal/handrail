"""The emergency stop with a telephone next to it: pull it, do what needs doing, ring to hand back.

On a factory line the stop button halts the belt; it does not fix anything.
A person walks over, sorts the jam by hand, and tells the line it may run
again. This page is that button and that telephone, and nothing more. It
shows whose hands the baton is in, which screens the run was hoping for,
and three things a person can do: take over, hand back naming the screen
they left the application on, or abort.

It is deliberately tiny: a few dozen lines of HTML served by a few dozen
lines of asyncio, no framework, nothing to install. It binds to localhost
only. The live browser the person drives is the same one the run was using,
opened with ``--headed``; this page never drives it.
"""

from __future__ import annotations

import asyncio
from html import escape
from urllib.parse import parse_qs

from ..kernel.control import Baton, IllegalExchange

PAGE = """<!doctype html><meta charset="utf-8"><title>Handrail console</title>
<style>body{{font:16px system-ui;margin:2rem;max-width:40rem}}form{{display:inline}}
button{{font:inherit;padding:.4rem .9rem;margin:.2rem}}
code{{background:#eee;padding:0 .3rem}}</style>
<h1>Handrail console</h1>
<p>Baton: <code>{owner}</code>{waiting}</p>
<p>Expected screens: {expected}</p>
<form method="post" action="/take_over"><input name="by" placeholder="your name" required>
<button>Take over</button></form>
<form method="post" action="/hand_back"><input name="by" placeholder="your name" required>
<select name="screen">{options}</select><button>Hand back</button></form>
<form method="post" action="/abort"><input name="by" placeholder="your name" required>
<button>Abort</button></form>
<ul>{history}</ul>"""


class Console:
    def __init__(self, baton: Baton, host: str = "127.0.0.1", port: int = 0) -> None:
        self.baton = baton
        self.host, self.port = host, port
        self.candidates: list[str] = []
        self.handed_back: str | None = None
        self._server: asyncio.base_events.Server | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    async def start(self) -> str:
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self.url

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    def offer(self, candidates: list[str]) -> None:
        """Tell the page which screens the run was hoping for; hand-back must name one."""
        self.candidates = list(candidates)
        self.handed_back = None

    # -- the three things a person can do ----------------------------------------

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

    # -- the smallest possible HTTP ------------------------------------------------

    def render(self) -> str:
        b = self.baton
        return PAGE.format(
            owner=escape(b.owner.value),
            waiting=" (the run is waiting for you)" if not b.automation_may_act else "",
            expected=", ".join(escape(c) for c in self.candidates) or "none",
            options="".join(
                f'<option value="{escape(c)}">{escape(c)}</option>' for c in self.candidates
            ),
            history="".join(
                f"<li>{escape(e.at[11:19])} {escape(e.action)} by {escape(e.by)} "
                f"{escape(e.why)}</li>"
                for e in b.history
            ),
        )

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = (await reader.readline()).decode().strip()
            method, path, *_ = request.split(" ") if request else ("GET", "/")
            length = 0
            while True:
                line = (await reader.readline()).decode()
                if line in ("\r\n", "\n", ""):
                    break
                if line.lower().startswith("content-length:"):
                    length = int(line.split(":", 1)[1])
            body = parse_qs((await reader.readexactly(length)).decode()) if length else {}
            status, text = "200 OK", ""
            if method == "POST":
                by = body.get("by", ["someone"])[0].strip() or "someone"
                screen = body.get("screen", [None])[0]
                text = self.act(path.lstrip("/"), by, screen)
                if text != "ok":
                    status = "409 Conflict"
            page = self.render() if text in ("", "ok") else f"<p>{escape(text)}</p>" + self.render()
            payload = page.encode()
            writer.write(
                f"HTTP/1.1 {status}\r\nContent-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode()
                + payload
            )
            await writer.drain()
        finally:
            writer.close()
