"""A real browser walks the real pages: the mystery shopper of the web UI.

A restaurant can pass every kitchen inspection and still have a door that sticks.
These tests send a mystery shopper (headless Chromium) through the front door of
the running app, on a phone and on a desk, and ask what they saw: the right
heading, no error written on the wall, nothing sticking out past the edge.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from handrail.serve.web.app import build_app
from handrail.serve.web.settings import Settings
from handrail.surface.null_surface import NullSurface

from ...factory import place_hold
from ...replay.test_engine import pages as stage_pages
from ...replay.test_engine import reworded

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "evidence" / "examples"


def run_id(folder: str) -> str:
    return json.loads((EXAMPLES / folder / "result.json").read_text())["run_id"]


@asynccontextmanager
async def serving(tmp_path: Path, pause: bool = False, live: bool = False) -> AsyncIterator[str]:
    """The real app on a free port. `live` gives it a scratch evidence folder for new runs."""
    caps = tmp_path / "caps"
    shutil.copytree(ROOT / "capabilities", caps)
    (caps / "factory-hold.json").write_text(json.dumps(place_hold()))
    card, odd_stage = reworded(shared=3)  # no rung can place the last page: a person is needed
    (caps / "factory-reworded.json").write_text(json.dumps(card))
    script = odd_stage if pause else stage_pages()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    evidence = tmp_path / "runs" if live else EXAMPLES
    settings = Settings(caps, evidence, EXAMPLES / "episodes.db", port=port)
    app = build_app(settings, lambda hosts, headless: NullSurface(script))
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=1
        )
    )
    task = asyncio.create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.05)
    assert server.started, "uvicorn did not start"
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task


@asynccontextmanager
async def browser_page(width: int, height: int) -> AsyncIterator[Any]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        pytest.skip(f"playwright is not installed: {e}")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch()
        except Exception as e:  # noqa: BLE001 - no browser binary: skip, do not fail
            pytest.skip(f"chromium could not launch: {e}")
        page = await browser.new_page(viewport={"width": width, "height": height})
        page.problems = []  # type: ignore[attr-defined]
        page.on("pageerror", lambda e: page.problems.append(f"pageerror: {e}"))  # type: ignore[attr-defined]
        page.on(
            "console",
            lambda m: m.type == "error" and page.problems.append(f"console: {m.text}"),  # type: ignore[attr-defined]
        )
        try:
            yield page
        finally:
            await browser.close()


async def open_route(page: Any, base: str, route: str) -> None:
    await page.goto(f"{base}/#{route}")
    await page.wait_for_selector("h1", timeout=10000)
    await page.wait_for_timeout(300)


async def test_every_page_renders_its_heading_with_no_console_errors(tmp_path):
    ok, bad = run_id("1-replay-success"), run_id("4-replay-injected-failure")
    routes = [
        ("/", "Capabilities"),
        ("/author", "Author"),
        ("/catalog", "Catalog"),
        ("/runs", "Run history"),
        ("/drift", "Drift"),
        ("/live", "Live"),
        ("/cards/plumbline-read-balance.json", "plumbline.read_balance"),
        (f"/runs/{ok}", "Run "),
        (f"/runs/{bad}", "Run "),
    ]
    async with serving(tmp_path) as base:
        for width, height in ((390, 844), (1280, 800)):
            async with browser_page(width, height) as page:
                for route, heading in routes:
                    await open_route(page, base, route)
                    h1 = await page.inner_text("h1")
                    assert heading in h1, (route, h1)
                    over = await page.evaluate(
                        "document.documentElement.scrollWidth - window.innerWidth"
                    )
                    assert over <= 0, f"{route} overflows by {over}px at {width}px"
                assert page.problems == [], page.problems


async def test_the_failed_example_run_names_the_check_that_failed_and_shows_the_screenshot(
    tmp_path,
):
    folder = EXAMPLES / "4-replay-injected-failure"
    result = json.loads((folder / "result.json").read_text())
    async with serving(tmp_path) as base, browser_page(1280, 800) as page:
        await open_route(page, base, f"/runs/{result['run_id']}")
        await page.wait_for_selector("img.shot")
        body = await page.inner_text("body")
        assert result["error"]["message"] in body
        src = await page.get_attribute("img.shot", "src")
        assert src.startswith(f"/api/runs/{result['run_id']}/files/"), src
        assert await page.evaluate("document.querySelector('img.shot').naturalWidth") > 0


async def test_the_catalog_lists_only_approved_cards_with_a_read_or_write_badge(tmp_path):
    async with serving(tmp_path) as base, browser_page(1280, 800) as page:
        await open_route(page, base, "/catalog")
        await page.wait_for_selector("article.card")
        tiles = await page.query_selector_all("article.card")
        assert tiles
        for tile in tiles:
            chips = await tile.eval_on_selector_all(
                ".chip", "els => els.map(e => e.textContent.trim().toUpperCase())"
            )
            assert {"READ", "WRITE"} & set(chips), chips
        assert "plumbline-place-hold.authored" not in await page.content()
        assert "plumbline.place_hold" in (await page.inner_text("body"))


async def fill_and_start(page: Any, base: str, file: str) -> None:
    await open_route(page, base, "/live")
    await page.select_option("select[aria-label=Capability]", file)
    await page.wait_for_selector("input[name=member_number]")
    await page.fill("input[name=member_number]", "400118")
    await page.fill("input[name=reason]", "LEGAL")
    await page.fill("input[aria-label=value]", "http://bank")
    await page.click("text=Start replay")


async def test_a_replay_started_from_the_live_page_finishes_and_links_to_its_run(tmp_path):
    async with serving(tmp_path, live=True) as base, browser_page(1280, 800) as page:
        await fill_and_start(page, base, "factory-hold.json")
        await page.wait_for_selector("h2:has-text('Finished')", timeout=15000)
        assert "SUCCESS" in (await page.inner_text("section.card:has(h2:has-text('Finished'))"))
        await page.click("text=Open the run")
        await page.wait_for_selector("h1:has-text('Run ')")
        await page.wait_for_selector("text=chain verified")
        body = await page.inner_text("body")
        assert "llm_calls = 0" in body and "chain verified" in body
        assert page.problems == [], page.problems


async def test_a_pause_shows_the_brass_banner_and_hand_back_resumes_the_run(tmp_path):
    async with serving(tmp_path, pause=True, live=True) as base, browser_page(1280, 800) as page:
        await fill_and_start(page, base, "factory-reworded.json")
        banner = page.locator(".banner-brass")
        await banner.wait_for(timeout=15000)
        text = await banner.inner_text()
        assert "post_hold" in text and "posted" in text
        await page.fill("input[aria-label='Your name']", "dhawal")
        await page.click("text=Take over")
        await page.wait_for_selector("button:has-text('Hand back')")
        await page.select_option("select[aria-label='Hand back as screen']", "posted")
        await page.click("button:has-text('Hand back')")
        await page.wait_for_selector("h2:has-text('Finished')", timeout=15000)
        assert "SUCCESS" in (await page.inner_text("section.card:has(h2:has-text('Finished'))"))
        assert "rung3.handed_back" in await page.inner_text("section.card:has(h2:text('Ladder'))")
