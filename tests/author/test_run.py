"""The whole evening, offline: a scripted guest authors the hold flow on the real mock bank,
the recipe writer compiles it, and the tasting verifies it against the record store."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytest.importorskip("langchain")

from langchain_core.messages import AIMessage  # noqa: E402

from handrail.author.run import author_command, verify_command  # noqa: E402
from handrail.cli import parser  # noqa: E402
from handrail.schema.capability import Capability  # noqa: E402

from .test_agent import call, scripted  # noqa: E402


@pytest.fixture(scope="module")
def bank() -> Iterator[str]:
    import os

    from werkzeug.serving import make_server

    from targetapp.app import STORE, create_app

    os.environ["HANDRAIL_ALLOW_FAULTS"] = "1"  # the record-store endpoint is behind this flag
    STORE.reset()  # the store is one object per process; an earlier test may have used it
    server = make_server("127.0.0.1", 0, create_app("quarrybrook"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_port}"
    server.shutdown()


def evening() -> list[AIMessage]:
    """Row numbers as the real sign-on, desk, member and hold pages number them."""
    return [
        call("assert_screen", label="signon"),
        call("act", index=1, verb="set_value", value="{{input.operator_id}}"),
        call("act", index=3, verb="set_value", value="{{input.password}}"),
        call("act", index=7, verb="invoke"),
        call("assert_screen", label="desk"),
        call("act", index=5, verb="set_value", value="{{input.member_number}}"),
        call("act", index=7, verb="invoke"),
        call("assert_screen", label="inquiry_results"),
        call("act", index=8, verb="invoke"),
        call("assert_screen", label="member"),
        call("act", index=3, verb="invoke"),
        call("assert_screen", label="hold_form"),
        call("act", index=3, verb="select", value="{{input.reason}}"),
        call("act", index=7, verb="invoke"),
        call("assert_screen", label="hold_review"),
        call("act", index=3, verb="invoke"),
        call("assert_screen", label="posted"),
        call("finish", outcome="posted"),
    ]


async def test_author_then_verify_end_to_end(bank: str, tmp_path: Path):
    out = tmp_path / "authored.json"
    sign_on = ["--input", "operator_id=dcolewell", "--input", "password=plumbline-demo"]
    order = ["--input", "member_number=400118", "--input", "share_id=400118-S0001"]
    args = parser().parse_args(
        [
            "author", "--goal", "Place a hold on a member's share", "--id", "plumbline.place_hold",
            "--entry", f"http://{bank}/signon", "--entry-template", "{{env.BASE_URL}}/signon",
            "--allow", bank, "--out", str(out), "--evidence", str(tmp_path / "evidence"),
            *sign_on, *order, "--input", "reason=LEGAL", "--secret", "password",
            "--confirm", "commit", "--by", "test",
        ]
    )  # fmt: skip
    assert await author_command(args, model=scripted(*evening())) == 0

    cap = Capability.model_validate_json(out.read_text())
    assert cap.lifecycle.state == "draft" and len(cap.steps) == 10
    hold = cap.targets[cap.step("s07_invoke_hold").target or ""]
    assert hold.scope[1].name == "{{input.share_id}}"  # the row became a blank
    member = cap.targets[cap.step("s06_invoke_400118").target or ""]
    assert member.name and member.name.eq == "{{input.member_number}}"
    books = list((tmp_path / "evidence").glob("author_*/trace.jsonl"))
    assert len(books) == 1 and "plumbline-demo" not in books[0].read_text()

    def trial(member: str, share: str, reason: str) -> str:
        who = "operator_id=dcolewell,password=plumbline-demo"
        return f"{who},member_number={member},share_id={share},reason={reason}"

    args = parser().parse_args(
        [
            "verify", str(out), "--env", f"BASE_URL=http://{bank}",
            "--evidence", str(tmp_path / "evidence"),
            "--trial", trial("400118", "400118-S0005", "LEGAL"),
            "--trial", trial("400337", "400337-S0001", "LEGAL"),
            "--trial", trial("400445", "400445-S0001", "FRAUD_REVIEW"),
        ]
    )  # fmt: skip
    assert await verify_command(args) == 0
    verified = json.loads(out.read_text())
    assert verified["lifecycle"]["state"] == "verified"
    assert verified["lifecycle"]["reliability"] == {"replays": 3, "clean": 3}
