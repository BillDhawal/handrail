"""Tests for the front desk: every question gets a JSON answer, every bad name a polite no."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from handrail.serve.web.app import build_app
from handrail.serve.web.settings import Settings

ROOT = Path(__file__).parents[3]


@pytest.fixture
def client() -> TestClient:
    s = Settings(
        ROOT / "capabilities", ROOT / "evidence/examples", ROOT / "evidence/examples/episodes.db"
    )
    return TestClient(build_app(s))


def test_every_get_route_answers_json(client: TestClient) -> None:
    run = client.get("/api/runs").json()[0]["run_id"]
    for path in [
        "/api/summary",
        "/api/capabilities",
        "/api/capabilities/plumbline-read-balance.json",
        "/api/capabilities/plumbline-read-balance.json/checklist",
        "/api/runs",
        f"/api/runs/{run}",
        "/api/drift",
    ]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith("application/json"), path


def test_a_run_file_is_served(client: TestClient) -> None:
    takeover = next(r for r in client.get("/api/runs").json() if r["escalated_to_human"])
    shot = client.get(f"/api/runs/{takeover['run_id']}").json()["screenshots"][0]
    assert client.get(f"/api/runs/{takeover['run_id']}/files/{shot['png']}").status_code == 200


def test_a_missing_thing_is_a_404_with_an_error_body(client: TestClient) -> None:
    for path in ["/api/runs/nope", "/api/capabilities/nope.json", "/api/nothing"]:
        r = client.get(path)
        assert r.status_code == 404 and "error" in r.json()


def test_a_bad_name_is_a_400_with_an_error_body(client: TestClient) -> None:
    r = client.get("/api/capabilities/..%2Fpyproject.toml")
    assert r.status_code in (400, 404) and "error" in r.json()
    r = client.get("/api/runs/x/files/..%2F..%2Fpyproject.toml")
    assert r.status_code in (400, 404) and "error" in r.json()
    assert client.get("/api/runs/..").status_code in (400, 404)
    assert client.get("/api/runs?limit=abc").status_code == 400


def test_the_root_serves_a_page(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200 and "<title>" in r.text
