"""The baton changes hands only by name, and the engine waits while a person holds it."""

import asyncio

import pytest

from handrail.kernel.control import Baton, IllegalExchange, Owner


def test_the_legal_exchanges_in_order():
    b = Baton()
    b.exchange("pause", "engine", "rung one and two could not name the screen")
    b.exchange("take_over", "dhawal")
    assert b.owner is Owner.HUMAN_CONTROL and not b.automation_may_act
    b.exchange("hand_back", "dhawal", "fixed the form by hand")
    assert b.owner is Owner.AUTOMATION_RUNNING and b.automation_may_act
    assert [e.action for e in b.history] == ["pause", "take_over", "hand_back"]
    assert b.history[1].by == "dhawal"


def test_nobody_grabs_the_baton_from_a_running_automation():
    with pytest.raises(IllegalExchange, match="cannot take_over while AUTOMATION_RUNNING"):
        Baton().exchange("take_over", "dhawal")


def test_abort_is_final():
    b = Baton()
    b.exchange("abort", "dhawal", "wrong member")
    assert b.aborted
    with pytest.raises(IllegalExchange, match="on the floor"):
        b.exchange("pause", "engine")


def test_an_unknown_exchange_is_refused():
    with pytest.raises(IllegalExchange, match="no such exchange"):
        Baton().exchange("steal", "x")


def test_every_exchange_is_seen_by_the_watchers():
    seen = []
    b = Baton()
    b.watch(seen.append)
    b.exchange("pause", "engine")
    b.exchange("resume", "engine")
    assert [(e.frm, e.to) for e in seen] == [
        (Owner.AUTOMATION_RUNNING, Owner.PAUSED),
        (Owner.PAUSED, Owner.AUTOMATION_RUNNING),
    ]


async def test_the_engine_waits_while_a_person_drives_and_goes_on_when_handed_back():
    b = Baton()
    b.exchange("pause", "engine")
    b.exchange("take_over", "dhawal")

    async def person():
        await asyncio.sleep(0.02)
        b.exchange("hand_back", "dhawal")

    asyncio.get_running_loop().create_task(person())
    assert await b.wait_until_automation_may_act(timeout_s=2) is True


async def test_waiting_ends_false_on_abort_or_timeout():
    b = Baton()
    b.exchange("pause", "engine")
    assert await b.wait_until_automation_may_act(timeout_s=0.02) is False
    b.exchange("abort", "dhawal")
    assert await b.wait_until_automation_may_act(timeout_s=1) is False
