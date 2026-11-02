"""Tests for the stage manager: one show at a time, the audience hears every line, masked."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from handrail.kernel.evidence import verify_chain
from handrail.serve.web.app import build_app
from handrail.serve.web.broadcast import Broadcast
from handrail.serve.web.live import Busy, LiveRun
from handrail.serve.web.settings import Settings
from handrail.surface.null_surface import NullSurface

from ...factory import place_hold
from ...replay.test_engine import ENV, INPUTS, pages

SECRET = "s3cret-value-9137"


def card_with_secret() -> dict[str, Any]:
    card = place_hold()
    for item in card["inputs"]:
        if item["name"] == "reason":
            item["sensitivity"] = "secret"
    return card


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    caps = tmp_path / "caps"
    caps.mkdir()
    (caps / "hold.json").write_text(json.dumps(place_hold()))
    (caps / "hold-secret.json").write_text(json.dumps(card_with_secret()))
    return Settings(caps, tmp_path / "runs", None)


def make(settings: Settings, surface: Any = None) -> tuple[LiveRun, Broadcast]:
    bc = Broadcast()
    surface = surface or NullSurface(pages())
    return LiveRun(settings, bc, lambda hosts, headless: surface, poll_interval_s=0.001), bc


def spec(file: str = "hold.json", **extra: Any) -> dict[str, Any]:
    return {"file": file, "inputs": INPUTS, "env": ENV, "console": True, **extra}


def drain(q: Any) -> list[dict[str, Any]]:
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


async def test_a_run_started_from_the_page_writes_the_same_evidence_as_the_cli(settings):
    live, _ = make(settings)
    run_id = live.start(spec())["run_id"]
    await live.wait()
    folder = settings.evidence / run_id
    for name in ("result.json", "log.jsonl", "journal.jsonl"):
        assert (folder / name).exists(), name
    assert verify_chain(folder / "log.jsonl") == (True, 0)
    state = live.state()
    assert state["state"] == "finished" and state["result"]["category"] == "SUCCESS"


async def test_only_one_run_at_a_time(settings):
    live, _ = make(settings)
    live.start(spec())
    with pytest.raises(Busy):
        live.start(spec())
    await live.wait()
    live.surface_factory = lambda hosts, headless: NullSurface(pages())
    live.start(spec())  # the stage is free again
    await live.wait()


def test_only_one_run_at_a_time_through_http(settings):
    class Slow(NullSurface):
        async def open(self, entry: str) -> None:
            await asyncio.sleep(0.5)
            await super().open(entry)

    app = build_app(settings, lambda hosts, headless: Slow(pages()))
    with TestClient(app) as client:
        assert client.post("/api/live/start", json=spec("../x.json")).status_code == 400
        assert client.post("/api/live/start", json=spec("nope.json")).status_code == 400
        first = client.post("/api/live/start", json=spec())
        assert first.status_code == 200 and "run_id" in first.json()
        second = client.post("/api/live/start", json=spec())
        assert second.status_code == 409 and "error" in second.json()
        assert client.get("/api/live").json()["active"] is True
        assert client.post("/api/live/act", json={"action": "abort", "by": "d"}).status_code == 200


async def test_events_reach_a_subscriber_in_order_and_masked(settings):
    live, bc = make(settings)
    q = bc.subscribe()
    live.start(spec("hold-secret.json"))
    await live.wait()
    messages = drain(q)
    events = [m for m in messages if m["type"] == "event"]
    assert [m["seq"] for m in events] == sorted(m["seq"] for m in events)
    assert events[0]["event"] == "replay.start" and events[-1]["event"] == "replay.finish"
    assert "[secret]" in json.dumps(events)
    assert messages[-1]["type"] == "live" and messages[-1]["state"] == "finished"
    bc.unsubscribe(q)


async def test_a_secret_input_never_appears_in_any_published_message(settings):
    live, bc = make(settings)
    q = bc.subscribe()
    live.start({**spec("hold-secret.json"), "inputs": {**INPUTS, "reason": SECRET}})
    await live.wait()
    wire = json.dumps(drain(q))
    assert SECRET not in wire
    run_dir = next(settings.evidence.iterdir())
    assert SECRET not in (run_dir / "log.jsonl").read_text()


async def test_the_takeover_page_moves_the_baton_and_hand_back_must_name_an_expected_screen(
    settings,
):
    live, bc = make(settings)
    q = bc.subscribe()
    live.start(spec())
    console = live.console
    assert console is not None
    console.baton.exchange("pause", "engine")
    console.offer(["posted", "refused"])
    assert live.state()["state"] == "paused"
    assert live.state()["expected"] == ["posted", "refused"]
    assert live.act("hand_back", "dhawal", "posted") != "ok"  # nobody holds it yet
    assert live.act("take_over", "dhawal") == "ok"
    assert live.act("hand_back", "dhawal", "wrong") != "ok"
    assert live.act("hand_back", "dhawal", "posted") == "ok"
    assert console.handed_back == "posted"
    await live.wait()
    batons = [m for m in drain(q) if m["type"] == "baton"]
    assert batons[0]["owner"] == "PAUSED" and batons[-1]["owner"] == "AUTOMATION_RUNNING"
    assert live.state()["state"] == "finished"


def test_the_websocket_streams_what_the_recorder_wrote(settings):
    app = build_app(settings, lambda hosts, headless: NullSurface(pages()))
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        client.post("/api/live/start", json=spec())
        events = []
        while True:
            m = ws.receive_json()
            if m["type"] == "event":
                events.append(m["event"])
                if m["event"] == "replay.finish":
                    break
        assert events[0] == "replay.start"
        assert ws.receive_json()["type"] == "live"


async def test_a_surface_that_explodes_still_yields_a_typed_result_and_a_live_message(settings):
    class Boom(NullSurface):
        async def open(self, entry: str) -> None:
            raise RuntimeError("the lights went out")

    live, bc = make(settings, Boom(pages()))
    q = bc.subscribe()
    live.start(spec())
    await live.wait()
    state = live.state()
    assert state["state"] == "finished"
    assert state["result"] is not None or "lights" in state["error"]
    assert drain(q)[-1]["type"] == "live"


async def test_the_state_carries_the_pause_so_a_page_opened_late_can_show_it(settings):
    from ...replay.test_engine import reworded

    card, stage = reworded(shared=3)  # no rung can place the last page, so a person is called
    (settings.capabilities / "reworded.json").write_text(json.dumps(card))
    live, _ = make(settings, NullSurface(stage))
    live.start(spec("reworded.json"))
    for _ in range(500):
        if live.state()["state"] == "paused":
            break
        await asyncio.sleep(0.01)
    pause = live.state()["pause"]
    assert pause is not None and pause["step"] == "post_hold"
    assert pause["at"] and pause["expected"]
    assert live.act("take_over", "dhawal") == "ok"
    assert live.act("hand_back", "dhawal", "posted") == "ok"
    await live.wait()
    assert live.state()["pause"] is None
