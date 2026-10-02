"""The real waiter, in a real Chromium, against PLUMBLINE started inside this test."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import pytest

from handrail.schema.errors import ErrorCode, HandrailError
from handrail.schema.target import RUNG_COST, Target

pytest.importorskip("playwright")

from handrail.surface.browser.locators import surviving  # noqa: E402
from handrail.surface.browser.operations import Control  # noqa: E402
from handrail.surface.browser.queries import FrameProbe  # noqa: E402
from handrail.surface.browser.surface import BrowserSurface  # noqa: E402


@pytest.fixture(scope="module")
def bank() -> Iterator[str]:
    from werkzeug.serving import make_server

    from targetapp.app import create_app

    server = make_server("127.0.0.1", 0, create_app("quarrybrook"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
async def waiter(bank: str) -> BrowserSurface:
    s = BrowserSurface(allowed_hosts=[bank])
    try:
        await s.open(f"http://{bank}/signon")
        yield s
    finally:
        await s.close()


def target(role: str, name: str, ladder: list[dict], scope: list[dict] | None = None) -> Target:
    return Target.model_validate(
        {
            "role": role,
            "name": {"eq": name},
            "supports": {"invoke": [], "set_value": ["string"], "read": []},
            "scope": scope or [],
            "ladder": ladder,
        }
    )


ROLE = {"rung": "role_name", "cost": RUNG_COST["role_name"]}


def label(caption: str) -> dict:
    return {"rung": "label", "cost": RUNG_COST["label"], "value": caption}


async def sign_on(s: BrowserSurface) -> None:
    opid = target("textbox", "Operator ID", [label("Operator ID")])
    pw = target("textbox", "Password", [label("Password")])
    go = target("button", "F5=Sign On", [ROLE])
    await s.act(await s.resolve(opid, 2000), "set_value", "dcolewell")
    await s.act(await s.resolve(pw, 2000), "set_value", "plumbline-demo")
    await s.act(await s.resolve(go, 2000), "invoke", None)
    await s.page.wait_for_load_state("load")


async def test_open_refuses_a_host_outside_the_allowlist(bank: str):
    s = BrowserSurface(allowed_hosts=[bank])
    with pytest.raises(HandrailError) as err:
        await s.open("http://example.com/")
    assert err.value.code is ErrorCode.POLICY_VIOLATION


async def test_the_sign_on_page_becomes_a_numbered_menu(waiter: BrowserSurface):
    ops = (await waiter.observe()).operations
    rows = [(op.index, op.verb, op.role, op.name) for op in ops]
    assert rows[0] == (1, "set_value", "textbox", "Operator ID")  # caption-named, no label tag
    assert (7, "invoke", "button", "F5=Sign On") in rows
    assert all(op.name != "_tk" for op in ops)  # the hidden token is not a control


async def test_resolve_reports_the_rung_that_found_the_control(waiter: BrowserSurface):
    found = await waiter.resolve(target("button", "F5=Sign On", [ROLE]), 2000)
    assert (found.rung, found.rung_cost) == ("role_name", 100)


async def test_a_caption_named_field_is_found_by_its_label_rung_and_can_be_read_back(
    waiter: BrowserSurface,
):
    field = target("textbox", "Operator ID", [label("Operator ID")])
    await waiter.act(await waiter.resolve(field, 2000), "set_value", "mrivas")
    value = await waiter.page.locator('[name="opid"]').input_value()
    assert value == "mrivas"


async def test_a_control_nothing_finds_is_missing_after_the_timeout(waiter: BrowserSurface):
    started = time.monotonic()
    with pytest.raises(HandrailError) as err:
        await waiter.resolve(target("button", "F99=Nope", [ROLE]), 600)
    assert err.value.code is ErrorCode.MISSING_CONTROL
    assert 0.5 < time.monotonic() - started < 5


async def test_signing_on_changes_the_signature_and_opens_two_frames(waiter: BrowserSurface):
    before = (await waiter.observe()).structure
    await sign_on(waiter)
    after = await waiter.observe()
    assert after.structure != before
    assert {f.name for f in waiter.page.frames} >= {"menu", "work"}
    search = target("button", "F5=Search", [ROLE], scope=[{"role": "frame", "name": "work"}])
    assert (await waiter.resolve(search, 2000)).rung == "role_name"


async def test_evaluate_answers_at_once_without_waiting(waiter: BrowserSurface):
    started = time.monotonic()
    assert await waiter.evaluate("target_present:F5=Sign On")
    assert not await waiter.evaluate("target_present:F99=Nope")
    assert await waiter.evaluate("screen_is:" + (await waiter.observe()).structure[0])
    assert time.monotonic() - started < 2


async def test_a_wrong_fingerprint_is_a_target_mismatch(waiter: BrowserSurface):
    spec = target("button", "F5=Sign On", [ROLE]).model_dump()
    spec["fingerprint"] = {"over": ["role"], "value": "sha256:not-this"}
    t = Target.model_validate(spec)
    with pytest.raises(HandrailError) as err:
        await waiter.resolve(t, 2000)
    assert err.value.code is ErrorCode.TARGET_MISMATCH


async def test_rungs_are_probed_for_uniqueness_on_the_real_page(waiter: BrowserSurface):
    ops = (await waiter.observe()).operations
    button = next(op for op in ops if op.name == "F5=Sign On")
    control = Control("button", "F5=Sign On", attr_name="", handle=button.handle)
    kept = await surviving(control, FrameProbe(waiter.page.main_frame))
    # Both find exactly this button. Playwright's text engine reads a submit's value as its text.
    assert [r.rung for r in kept] == ["role_name", "text"]


async def test_evidence_has_the_screen_text_and_a_screenshot(waiter: BrowserSurface):
    bundle = await waiter.evidence()
    assert "OPERATOR SIGN ON" in bundle.text
    assert bundle.screenshot_png and bundle.screenshot_png[:4] == b"\x89PNG"
