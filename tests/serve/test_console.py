"""The stop button and the telephone: take over, hand back naming a screen, or abort."""

from __future__ import annotations

import asyncio
import urllib.parse
import urllib.request

from handrail.kernel.control import Baton, Owner
from handrail.serve.console import Console


def post(url: str, **fields: str) -> tuple[int, str]:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()


async def test_the_page_shows_the_baton_and_the_expected_screens():
    baton = Baton()
    console = Console(baton)
    url = await console.start()
    try:
        console.offer(["posted", "already_held"])
        html = await asyncio.to_thread(lambda: urllib.request.urlopen(url).read().decode())
        assert "AUTOMATION_RUNNING" in html and "posted, already_held" in html
    finally:
        await console.stop()


async def test_take_over_then_hand_back_names_a_screen_and_moves_the_baton():
    baton = Baton()
    baton.exchange("pause", "engine")
    console = Console(baton)
    url = await console.start()
    try:
        console.offer(["posted"])
        status, _ = await asyncio.to_thread(post, url + "take_over", by="dhawal")
        assert status == 200 and baton.owner is Owner.HUMAN_CONTROL
        back = url + "hand_back"
        status, body = await asyncio.to_thread(post, back, by="dhawal", screen="inquiry")
        assert status == 409 and "must name one of" in body  # not an expected screen
        status, _ = await asyncio.to_thread(post, back, by="dhawal", screen="posted")
        assert status == 200 and baton.owner is Owner.AUTOMATION_RUNNING
        assert console.handed_back == "posted" and baton.history[-1].by == "dhawal"
    finally:
        await console.stop()


async def test_an_illegal_exchange_is_a_conflict_not_a_crash():
    baton = Baton()
    console = Console(baton)
    url = await console.start()
    try:
        status, body = await asyncio.to_thread(post, url + "take_over", by="dhawal")
        assert status == 409 and "cannot take_over while AUTOMATION_RUNNING" in body
        status, _ = await asyncio.to_thread(post, url + "abort", by="dhawal")
        assert status == 200 and baton.aborted
    finally:
        await console.stop()
