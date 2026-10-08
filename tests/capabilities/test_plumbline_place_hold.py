"""The milestone 2 demo, as a test: the hand-written capability replays on the real mock bank."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from handrail.kernel.evidence import Recorder, verify_chain
from handrail.replay.engine import ReplayEngine
from handrail.schema.capability import Capability
from handrail.schema.errors import ErrorCode, OutcomeCategory

pytest.importorskip("playwright")

from handrail.surface.browser.surface import BrowserSurface  # noqa: E402

CAPABILITY = Path(__file__).resolve().parents[2] / "capabilities" / "plumbline-place-hold.json"
SIGN_ON = {"operator_id": "dcolewell", "password": "plumbline-demo", "reason": "LEGAL"}


@pytest.fixture(scope="module")
def bank() -> Iterator[str]:
    from werkzeug.serving import make_server

    from targetapp.app import ARMED, STORE, create_app

    STORE.reset()  # the store is one object per process; an earlier test may have used it
    ARMED.clear()
    server = make_server("127.0.0.1", 0, create_app("quarrybrook"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_port}"
    server.shutdown()


def capability() -> Capability:
    return Capability.model_validate(json.loads(CAPABILITY.read_text()))


async def replay(bank: str, tmp_path: Path, run_id: str, **inputs: str):
    surface = BrowserSurface(allowed_hosts=[bank])
    recorder = Recorder(run_id, root=tmp_path)
    engine = ReplayEngine(surface, recorder, env={"BASE_URL": f"http://{bank}"})
    try:
        return await engine.run(capability(), {**SIGN_ON, **inputs}), recorder
    finally:
        await surface.close()


def test_the_capability_file_is_valid_approved_and_its_commit_was_confirmed_by_a_name():
    cap = capability()
    assert cap.lifecycle.state == "approved" and cap.lifecycle.approved_by == "dhawal"
    assert cap.step("post_hold").effect.kind == "commit"
    assert cap.step("post_hold").effect.confirmed_by == "dhawal"


async def test_a_hold_is_placed_with_zero_model_calls(bank: str, tmp_path: Path):
    result, recorder = await replay(
        bank, tmp_path, "run_posted", member_number="400118", share_id="400118-S0001"
    )
    assert result.category is OutcomeCategory.SUCCESS, result.error
    assert result.outcome == "posted"
    assert result.outputs["confirmation"].startswith("HX-")
    assert (result.classifier_calls, result.llm_calls) == (0, 0)
    assert result.drift.first_choice == result.drift.steps_resolved == 11
    ok, _ = verify_chain(recorder.dir / "log.jsonl")
    assert ok


async def test_a_share_already_under_hold_is_an_answer_not_a_failure(bank: str, tmp_path: Path):
    result, _ = await replay(
        bank, tmp_path, "run_held", member_number="400226", share_id="400226-S0002"
    )
    assert result.category is OutcomeCategory.BUSINESS_OUTCOME
    assert result.code is ErrorCode.ALREADY_PROCESSED
    assert result.outcome == "already_held"
    assert result.outputs == {}


async def test_an_unknown_member_is_record_not_found(bank: str, tmp_path: Path):
    result, _ = await replay(
        bank, tmp_path, "run_nomatch", member_number="999999", share_id="999999-S0001"
    )
    assert result.category is OutcomeCategory.BUSINESS_OUTCOME
    assert result.code is ErrorCode.RECORD_NOT_FOUND


async def test_the_password_never_reaches_the_evidence(bank: str, tmp_path: Path):
    _, recorder = await replay(
        bank, tmp_path, "run_secret", member_number="400337", share_id="400337-S0001"
    )
    for path in recorder.dir.iterdir():
        if path.suffix in (".jsonl", ".json", ".txt"):
            assert "plumbline-demo" not in path.read_text(), path.name
