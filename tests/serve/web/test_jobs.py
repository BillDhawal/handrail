"""The back office: a signature only on a verified card, a tasting, a chef who waits."""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from handrail.schema.capability import Capability
from handrail.serve.web.jobs import Jobs, job_routes
from handrail.serve.web.settings import Settings
from handrail.surface.null_surface import NullSurface

from ...author.test_agent import call, scripted
from ...author.test_middleware import AuthorableCounter
from ...factory import place_hold
from ...replay.test_engine import ENV, pages

ROOT = Path(__file__).parents[3]
CARD = "plumbline-place-hold.authored.json"
TRIALS = [{"member_number": n, "reason": "LEGAL"} for n in ("400118", "400226", "400337")]


class Rig:
    def __init__(self, tmp: Path, **kw: Any) -> None:
        self.caps = tmp / "caps"
        self.caps.mkdir()
        self.lines: list[dict[str, Any]] = []
        self.jobs = Jobs(
            Settings(self.caps, tmp / "ev", None),
            self.lines.append,
            dotenv=tmp / "missing.env",
            **kw,
        )
        self.client = TestClient(Starlette(routes=job_routes(self.jobs)))

    def card(self, name: str = CARD) -> Path:
        shutil.copy(ROOT / "capabilities" / CARD, self.caps / name)
        return self.caps / name

    def draft(self, name: str = "draft.json") -> Path:
        cap = place_hold()
        for step in cap["steps"]:
            if step["effect"]["kind"] == "commit":
                step["effect"]["confirmed_by"] = "dhawal"
        (self.caps / name).write_text(json.dumps(cap))
        return self.caps / name

    def pending(self) -> bool:
        return self.client.get("/api/author").json()["pending_confirm"] is not None

    def wait(self, until: Callable[[], bool], what: str) -> None:
        for _ in range(400):
            if until():
                return
            time.sleep(0.02)
        raise AssertionError(f"timed out waiting for {what}")


@pytest.fixture
def rig(tmp_path: Path) -> Iterator[Rig]:
    with_client = Rig(tmp_path)
    with with_client.client:
        yield with_client


def stub_check(answer: bool) -> dict[str, Callable[[str], Any]]:
    async def check(inputs: dict[str, Any], result: Any) -> bool:
        return answer

    return {"hold_exists": lambda base: check}


def test_approve_signs_a_verified_card_and_writes_it_back(rig: Rig) -> None:
    path = rig.card()
    r = rig.client.post(f"/api/capabilities/{CARD}/approve", json={"by": "dhawal"})
    assert r.status_code == 200 and r.json()["lifecycle"]["state"] == "approved"
    saved = Capability.model_validate_json(path.read_text())
    assert saved.lifecycle.state == "approved" and saved.lifecycle.approved_by == "dhawal"
    assert path.read_text().endswith("}\n")


def test_approve_refuses_a_draft_and_an_already_approved_card_with_409(rig: Rig) -> None:
    rig.draft()
    r = rig.client.post("/api/capabilities/draft.json/approve", json={"by": "dhawal"})
    assert r.status_code == 409 and "verify it first" in r.json()["error"]
    rig.card()
    rig.client.post(f"/api/capabilities/{CARD}/approve", json={"by": "dhawal"})
    again = rig.client.post(f"/api/capabilities/{CARD}/approve", json={"by": "dhawal"})
    assert again.status_code == 409 and "already approved" in again.json()["error"]
    missing = rig.client.post("/api/capabilities/nope.json/approve", json={"by": "x"})
    assert missing.status_code == 404


def test_deprecate_keeps_the_card_and_the_reason(rig: Rig) -> None:
    path = rig.card()
    body = {"by": "dhawal", "why": "the bank changed its hold form"}
    r = rig.client.post(f"/api/capabilities/{CARD}/deprecate", json=body)
    assert r.status_code == 200
    saved = Capability.model_validate_json(path.read_text())
    assert saved.lifecycle.state == "deprecated" and saved.lifecycle.note == body["why"]


def start_verify(rig: Rig, check: str | None = "hold_exists") -> str:
    body = {"trials": TRIALS, "check": check, "env": ENV}
    r = rig.client.post("/api/capabilities/draft.json/verify", json=body)
    assert r.status_code == 200, r.text
    return str(r.json()["job_id"])


def test_verify_runs_three_plates_with_a_null_surface_and_publishes_a_line_per_plate(
    tmp_path: Path,
) -> None:
    rig = Rig(tmp_path, surface_for=lambda c: NullSurface(pages()), checks=stub_check(True))
    path = rig.draft()
    with rig.client:
        job_id = start_verify(rig)
        rig.wait(lambda: rig.jobs.states[job_id]["state"] != "running", "verify")
        state = rig.client.get(f"/api/jobs/{job_id}").json()
    lines = [m["line"] for m in rig.lines if m["job_id"] == job_id]
    plates = [ln for ln in lines if ln.startswith("plate")]
    assert plates == [f"plate {n}: clean" for n in (1, 2, 3)]
    assert state["state"] == "done"
    assert Capability.model_validate_json(path.read_text()).lifecycle.state == "verified"


def test_verify_that_fails_the_independent_check_stays_in_draft(tmp_path: Path) -> None:
    rig = Rig(tmp_path, surface_for=lambda c: NullSurface(pages()), checks=stub_check(False))
    path = rig.draft()
    with rig.client:
        job_id = start_verify(rig)
        rig.wait(lambda: rig.jobs.states[job_id]["state"] != "running", "verify")
    last = rig.lines[-1]
    assert last["state"] == "failed" and last["line"].startswith("stays in draft: trial 1")
    assert Capability.model_validate_json(path.read_text()).lifecycle.state == "draft"


def test_author_start_without_a_key_is_refused_with_409(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    spec = {"goal": "g", "entry": "http://x/", "id": "a.b", "out": "a.json"}
    r = rig.client.post("/api/author/start", json=spec)
    assert r.status_code == 409 and "ANTHROPIC_API_KEY" in r.json()["error"]


def test_author_with_a_scripted_model_waits_for_the_person_to_mark_the_commit_then_compiles(
    tmp_path: Path,
) -> None:
    surface = AuthorableCounter()
    model = scripted(
        call("assert_screen", label="inquiry"),
        call("act", index=1, verb="set_value", value="{{input.member_number}}"),
        call("act", index=3, verb="invoke"),
        call("assert_screen", label="posted"),
        call("act", index=1, verb="read"),
        call("finish", outcome="posted"),
    )
    rig = Rig(tmp_path, kit=lambda hosts: (surface, surface), model=model)
    with rig.client:
        spec = {
            "goal": "look up a member",
            "entry": "http://bank/inquiry",
            "id": "bank.lookup",
            "out": "lookup.json",
            "allow": ["bank"],
            "inputs": {"member_number": "400118"},
        }
        assert rig.client.post("/api/author/start", json=spec).status_code == 200
        busy = rig.client.post("/api/author/start", json=spec)
        assert busy.status_code == 409
        rig.wait(lambda: rig.pending(), "pending")
        board = rig.client.get("/api/author").json()
        assert board["active"] and board["pending_confirm"]["index"] == 3
        assert [t["intent"] for t in board["turns"]] == ["inquiry", "act"]
        ok = rig.client.post("/api/author/confirm", json={"decision": "commit", "by": "dhawal"})
        assert ok.json() == {"ok": True}
        rig.wait(lambda: not rig.client.get("/api/author").json()["active"], "the evening to end")
        final = rig.client.get("/api/author").json()
    assert final["error"] is None, final
    assert final["compiled"] == "lookup.json" and final["finished"]
    card = json.loads((rig.caps / "lookup.json").read_text())
    commits = [s for s in card["steps"] if s["effect"]["kind"] == "commit"]
    assert commits and commits[0]["effect"]["confirmed_by"] == "dhawal"


def test_author_stop_ends_the_job_with_a_typed_error(tmp_path: Path) -> None:
    surface = AuthorableCounter()
    model = scripted(call("assert_screen", label="inquiry"), call("act", index=3, verb="invoke"))
    rig = Rig(tmp_path, kit=lambda hosts: (surface, surface), model=model)
    with rig.client:
        spec = {"goal": "g", "entry": "http://bank/", "id": "bank.x", "out": "x.json"}
        rig.client.post("/api/author/start", json=spec)
        rig.wait(lambda: rig.pending(), "pending")
        assert rig.client.post("/api/author/stop").json() == {"ok": True}
        rig.wait(lambda: not rig.client.get("/api/author").json()["active"], "stop")
        board = rig.client.get("/api/author").json()
        assert board["error"] == "stopped by operator" and board["compiled"] is None
        nothing = rig.client.post("/api/author/confirm", json={"decision": "commit", "by": "d"})
        assert nothing.status_code == 409
        assert rig.lines[-1]["state"] == "failed"
