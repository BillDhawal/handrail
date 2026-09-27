"""Invariant 13: evidence is hash-chained.

Invariant 6, first half: secrets are masked at the writer, never at the call site.
"""

import json

from handrail.kernel.evidence import MASK, Recorder, new_run_id, verify_chain
from handrail.surface.null_surface import NullSurface, Page


def recorder(tmp_path, **kw) -> Recorder:
    return Recorder("run_t", root=tmp_path, **kw)


def test_run_ids_are_unique_and_say_what_kind_of_run():
    a, b = new_run_id("replay"), new_run_id("replay")
    assert a != b and a.startswith("replay_")


def test_an_untouched_log_verifies(tmp_path):
    r = recorder(tmp_path)
    for i in range(3):
        r.log("step.ok", step=f"s{i}")
    assert verify_chain(r.dir / "log.jsonl") == (True, 0)


def test_editing_one_line_breaks_that_line_and_everything_after(tmp_path):
    r = recorder(tmp_path)
    for i in range(4):
        r.log("step.ok", step=f"s{i}", value=100)
    path = r.dir / "log.jsonl"
    lines = path.read_text().splitlines()
    tampered = json.loads(lines[1])
    tampered["value"] = 999  # someone "corrects" the record
    lines[1] = json.dumps(tampered)
    path.write_text("\n".join(lines) + "\n")
    intact, first_bad = verify_chain(path)
    assert (intact, first_bad) == (False, 2)


def test_deleting_a_line_is_detected_too(tmp_path):
    r = recorder(tmp_path)
    for i in range(3):
        r.log("step.ok", step=f"s{i}")
    path = r.dir / "log.jsonl"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert verify_chain(path) == (False, 2)


def test_a_registered_secret_never_reaches_the_log_however_nested(tmp_path):
    r = recorder(tmp_path, secrets=("plumbline-demo",))
    r.log("typed", value="plumbline-demo", nested={"again": ["plumbline-demo"]})
    text = (r.dir / "log.jsonl").read_text()
    assert "plumbline-demo" not in text
    assert text.count(MASK) == 2


def test_a_secret_learned_mid_run_is_masked_from_then_on(tmp_path):
    r = recorder(tmp_path)
    r.add_secret("HX-829120")
    r.write_json("result.json", {"confirmation": "HX-829120"})
    assert MASK in (r.dir / "result.json").read_text()


async def test_capture_writes_the_screen_text_masked(tmp_path):
    r = recorder(tmp_path, secrets=("s3cret",))
    surface = NullSurface([Page("x", text="password: s3cret")])
    refs = await r.capture(surface, "fail_s2")
    assert refs["text"] == "fail_s2.txt"
    assert (r.dir / "fail_s2.txt").read_text() == f"password: {MASK}"


async def test_capture_never_raises_even_when_the_surface_is_broken(tmp_path):
    class Broken(NullSurface):
        async def evidence(self):
            raise RuntimeError("browser gone")

    r = recorder(tmp_path)
    refs = await r.capture(Broken([Page("x")]), "fail")
    assert refs == {"text": None, "screenshot": None}
    assert "evidence.capture_failed" in (r.dir / "log.jsonl").read_text()
