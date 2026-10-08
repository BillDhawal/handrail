"""One command in, one receipt out, and the exit code says which kind of ending it was."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from handrail.cli import main, pairs, parser

pytest.importorskip("playwright")

CAPABILITY = Path(__file__).resolve().parents[1] / "capabilities" / "plumbline-place-hold.json"


@pytest.fixture(scope="module")
def bank() -> Iterator[str]:
    from werkzeug.serving import make_server

    from targetapp.app import ARMED, STORE, create_app

    STORE.reset()
    ARMED.clear()
    server = make_server("127.0.0.1", 0, create_app("quarrybrook"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def capability_for(bank: str, tmp_path: Path) -> Path:
    """The real file, with the allowlist pointed at this test's port."""
    spec = json.loads(CAPABILITY.read_text())
    spec["safety"]["allowed_hosts"] = [bank]
    path = tmp_path / "cap.json"
    path.write_text(json.dumps(spec))
    return path


def test_inputs_are_name_equals_value_and_a_value_may_contain_equals():
    assert pairs(["a=1", "b=x=y"]) == {"a": "1", "b": "x=y"}
    with pytest.raises(SystemExit):
        pairs(["novalue"])


def test_the_parser_knows_both_commands():
    args = parser().parse_args(["replay", "cap.json", "--input", "a=1", "--env", "BASE_URL=u"])
    assert (args.command, args.input, args.env) == ("replay", ["a=1"], ["BASE_URL=u"])
    assert parser().parse_args(["observe", "http://x", "--allow", "x"]).command == "observe"


def test_replay_prints_a_receipt_with_zero_model_calls_and_exits_zero(
    bank: str, capability_for: Path, tmp_path: Path, capsys
):
    code = main(
        [
            "replay", str(capability_for),
            "--env", f"BASE_URL=http://{bank}",
            "--evidence", str(tmp_path / "evidence"),
            "--input", "operator_id=dcolewell", "--input", "password=plumbline-demo",
            "--input", "member_number=400445", "--input", "share_id=400445-S0001",
            "--input", "reason=LEGAL",
        ]
    )  # fmt: skip
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("SUCCESS")
    assert "llm_calls=0  classifier_calls=0" in out
    assert '"confirmation": "HX-' in out


def test_a_business_outcome_exits_two(bank: str, capability_for: Path, tmp_path: Path, capsys):
    code = main(
        [
            "replay", str(capability_for),
            "--env", f"BASE_URL=http://{bank}",
            "--evidence", str(tmp_path / "evidence"),
            "--input", "operator_id=dcolewell", "--input", "password=plumbline-demo",
            "--input", "member_number=400226", "--input", "share_id=400226-S0002",
            "--input", "reason=LEGAL",
        ]
    )  # fmt: skip
    assert code == 2
    assert capsys.readouterr().out.startswith("BUSINESS_OUTCOME  code=ALREADY_PROCESSED")


def test_observe_prints_the_signature_and_the_menu(bank: str, capsys):
    code = main(["observe", f"http://{bank}/signon", "--allow", bank])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("signature=sha256:")
    assert "invoke button 'F5=Sign On'" in out


def test_the_parser_knows_author_and_verify():
    a = parser().parse_args(
        ["author", "--goal", "g", "--entry", "http://x", "--id", "i", "--out", "o.json"]
    )
    assert (a.command, a.model, a.confirm) == ("author", "anthropic:claude-sonnet-5", None)
    v = parser().parse_args(["verify", "cap.json", "--trial", "a=1,b=2"])
    assert (v.command, v.trial) == ("verify", ["a=1,b=2"])


def test_the_parser_knows_the_referee_and_the_notebook():
    a = parser().parse_args(["replay", "c.json", "--classifier", "claude", "--episodes", "e.db"])
    assert (a.classifier, a.episodes) == ("claude", "e.db")
    e = parser().parse_args(["episodes", "e.db", "--question", "which_screen"])
    assert (e.command, e.question) == ("episodes", "which_screen")


def test_episodes_prints_a_calibration_table(tmp_path: Path, capsys):
    from handrail.kernel.episodes import Episodes

    book = Episodes(tmp_path / "e.db")
    book.record("r1", "c", "screen", 1, question="which_screen", confidence=0.9, accepted=True)
    book.settle("r1", "SUCCESS", True)
    assert main(["episodes", str(tmp_path / "e.db")]) == 0
    out = capsys.readouterr().out
    assert "1 episodes" in out and "0.8 to 1.0          1      1   1.00" in out
