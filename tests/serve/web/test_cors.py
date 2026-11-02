from __future__ import annotations

import argparse

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from handrail.serve.web.cors import cors_middleware, cors_origins

ALLOWED = "http://localhost:8080"


def _client() -> TestClient:
    async def ping(request: object) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/ping", ping)], middleware=[cors_middleware([ALLOWED])])
    return TestClient(app)


def _preflight(origin: str):  # noqa: ANN202
    return _client().options(
        "/ping",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_a_listed_origin_is_let_through_the_preflight() -> None:
    r = _preflight(ALLOWED)
    assert r.headers["access-control-allow-origin"] == ALLOWED
    assert "POST" in r.headers["access-control-allow-methods"]
    assert "access-control-allow-credentials" not in r.headers


def test_an_unlisted_origin_gets_no_allow_header() -> None:
    r = _preflight("http://evil.example")
    assert "access-control-allow-origin" not in r.headers


def test_cors_origins_reads_the_repeatable_flag() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cors", action="append", default=[])
    args = p.parse_args(["--cors", "http://a.test/", "--cors", "https://b.test"])
    assert cors_origins(args) == ["http://a.test", "https://b.test"]
    assert cors_origins(p.parse_args([])) == []
