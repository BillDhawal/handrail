"""The book is written before the guest speaks again, and a secret never reaches it."""

from __future__ import annotations

import json
from pathlib import Path

from handrail.author.recorder import TRACE, TraceRecorder, turn_from_dict, turn_to_dict
from handrail.kernel.evidence import Recorder, verify_chain
from handrail.schema.target import Fingerprint, Rung
from handrail.schema.trace import Turn
from handrail.surface.browser.walk import Handle

RUNGS = (Rung(rung="role_name", cost=100), Rung(rung="label", cost=140, value="Password"))
FP = Fingerprint(over=["role", "name"], value="sha256:abc")


def turn(seq: int = 1, value: str | None = "{{input.password}}") -> Turn:
    return Turn(
        seq=seq,
        tool="act",
        index=3,
        verb="set_value",
        value=value,
        role="textbox",
        name="Password",
        handle=Handle("work", "body > input:nth-child(2)"),
        signature_before="sha256:a",
        signature_after="sha256:a",
        effect="stage",
        rungs=RUNGS,
        fingerprint=FP,
    )


def test_a_turn_is_on_disk_before_write_returns(tmp_path: Path):
    book = TraceRecorder(Recorder("author_t", root=tmp_path))
    book.write(turn())
    lines = book.path.read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["name"] == "Password"
    assert book.path.name == TRACE


def test_a_registered_secret_never_reaches_the_trace_or_the_log(tmp_path: Path):
    recorder = Recorder("author_t", root=tmp_path, secrets=("hunter2",))
    book = TraceRecorder(recorder)
    book.write(turn(value="hunter2"))  # a model that ignored the rule about blanks
    assert "hunter2" not in book.path.read_text()
    assert "hunter2" not in (recorder.dir / "log.jsonl").read_text()


def test_the_book_round_trips_rungs_and_fingerprint(tmp_path: Path):
    book = TraceRecorder(Recorder("author_t", root=tmp_path))
    book.write(turn(1))
    book.write(turn(2))
    loaded = TraceRecorder.load(book.path)
    assert [t.seq for t in loaded] == [1, 2]
    assert loaded[0].rungs == RUNGS and loaded[0].fingerprint == FP
    assert loaded[0].value == "{{input.password}}"


def test_a_handle_comes_back_as_plain_data_not_a_live_locator(tmp_path: Path):
    book = TraceRecorder(Recorder("author_t", root=tmp_path))
    book.write(turn())
    assert TraceRecorder.load(book.path)[0].handle == {
        "frame": "work",
        "selector": "body > input:nth-child(2)",
    }


def test_every_turn_is_a_sealed_line_in_the_run_log(tmp_path: Path):
    recorder = Recorder("author_t", root=tmp_path)
    book = TraceRecorder(recorder)
    for seq in range(1, 4):
        book.write(turn(seq))
    ok, _ = verify_chain(recorder.dir / "log.jsonl")
    assert ok
    log_lines = (recorder.dir / "log.jsonl").read_text().splitlines()
    events = [json.loads(line)["event"] for line in log_lines]
    assert events == ["author.turn"] * 3


def test_a_missing_book_loads_as_empty(tmp_path: Path):
    assert TraceRecorder.load(tmp_path / "nope.jsonl") == []


def test_to_dict_and_back_is_the_identity_for_a_turn_with_no_handle():
    plain = turn_to_dict(Turn(seq=1, tool="finish", label="posted"))
    assert turn_from_dict(plain) == Turn(seq=1, tool="finish", label="posted")
