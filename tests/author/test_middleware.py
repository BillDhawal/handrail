"""The maître d' asks before anything irreversible, and writes every turn in the book."""

from __future__ import annotations

import pytest

from handrail.author.middleware import Decision, Guard, MemorySink, Proposal, cautious
from handrail.author.tools import Session, ToolRefused
from handrail.schema.effects import EffectClass
from handrail.surface.browser.locators import Query
from handrail.surface.browser.operations import Control

from .test_tools import Counter

CONTROLS = {
    "h-member": Control("textbox", label="Member", attr_name="mbr", ancestors=("form",)),
    "h-search": Control("button", "F5=Search", ancestors=("form",)),
    "h-result": Control("status", "Result", ancestors=("main",)),
}


class Street:
    """Every rung finds exactly the right control, except `text` for the button."""

    async def count(self, query: Query) -> int:
        return 0 if query.how == "text" else 1

    async def is_same(self, query: Query, handle: object) -> bool:
        return True


class AuthorableCounter(Counter):
    async def describe(self, handle: str) -> Control:
        c = CONTROLS[handle]
        return Control(c.role, c.name, c.label, c.attr_name, ancestors=c.ancestors, handle=handle)

    def probe(self, handle: str, control: Control) -> Street:
        return Street()


class Owner:
    def __init__(self, answer: Decision) -> None:
        self.answer = answer
        self.asked: list[Proposal] = []

    async def __call__(self, proposal: Proposal) -> Decision:
        self.asked.append(proposal)
        return self.answer


YES = Decision(EffectClass.COMMIT, "dhawal")
NO = Decision(None, "dhawal")
ONLY_NAVIGATION = Decision(EffectClass.NAVIGATE, "dhawal")


async def guard(owner: Owner) -> tuple[Guard, AuthorableCounter, MemorySink]:
    surface = AuthorableCounter()
    session = Session(surface, inputs={"member_number": "400118"})
    await session.look()
    sink = MemorySink()
    return Guard(session, surface, owner, sink), surface, sink


def test_the_default_classifier_is_cautious_about_buttons():
    assert cautious(CONTROLS["h-search"], "invoke") is EffectClass.COMMIT
    assert cautious(Control("link", "Member Inquiry"), "invoke") is EffectClass.NAVIGATE
    assert cautious(CONTROLS["h-member"], "set_value") is EffectClass.STAGE
    assert cautious(CONTROLS["h-result"], "read") is EffectClass.READ


async def test_a_button_press_asks_the_owner_and_no_means_nothing_happens():
    owner = Owner(NO)
    g, surface, sink = await guard(owner)
    with pytest.raises(ToolRefused, match="did not allow row 3"):
        await g.act(3, "invoke")
    assert len(owner.asked) == 1 and owner.asked[0].control.name == "F5=Search"
    assert surface.acts == [] and sink.turns == []


async def test_the_owner_may_downgrade_a_commit_to_a_navigation():
    g, surface, sink = await guard(Owner(ONLY_NAVIGATION))
    await g.act(3, "invoke")
    assert surface.acts == [("invoke", "h-search", None)]
    assert (sink.turns[-1].effect, sink.turns[-1].confirmed_by) == ("navigate", "dhawal")


async def test_a_confirmed_commit_carries_the_name_of_the_person():
    g, _, sink = await guard(Owner(YES))
    await g.act(3, "invoke")
    assert (sink.turns[-1].effect, sink.turns[-1].confirmed_by) == ("commit", "dhawal")


async def test_a_stage_step_asks_nobody():
    owner = Owner(NO)
    g, surface, sink = await guard(owner)
    await g.act(1, "set_value", "{{input.member_number}}")
    assert owner.asked == []
    assert surface.acts == [("set_value", "h-member", "400118")]
    assert sink.turns[-1].effect == "stage" and sink.turns[-1].confirmed_by is None


async def test_every_surviving_rung_and_the_fingerprint_are_on_the_turn():
    g, _, sink = await guard(Owner(YES))
    await g.act(3, "invoke")
    turn = sink.turns[-1]
    assert [r.rung for r in turn.rungs] == ["role_name"]  # `text` found nothing on this street
    assert turn.fingerprint is not None and turn.fingerprint.value.startswith("sha256:")


async def test_a_control_no_rung_can_find_is_still_acted_on():
    class Fog(AuthorableCounter):
        def probe(self, handle: str, control: Control):
            class Nothing:
                async def count(self, query: Query) -> int:
                    return 0

                async def is_same(self, query: Query, handle: object) -> bool:
                    return False

            return Nothing()

    surface = Fog()
    session = Session(surface, inputs={"member_number": "400118"})
    await session.look()
    sink = MemorySink()
    await Guard(session, surface, Owner(YES), sink).act(1, "set_value", "{{input.member_number}}")
    assert surface.acts and sink.turns[-1].rungs == ()  # the compiler refuses this later


async def test_the_book_is_written_in_order_including_labels_and_the_finish():
    g, _, sink = await guard(Owner(YES))
    await g.assert_screen("inquiry")
    await g.act(3, "invoke")
    await g.assert_screen("posted")
    await g.finish("posted")
    assert [t.tool for t in sink.turns] == ["assert_screen", "act", "assert_screen", "finish"]
    assert [t.seq for t in sink.turns] == [1, 2, 3, 4]


async def test_a_custom_classifier_replaces_the_cautious_rule():
    def trusting(control: Control, verb: str) -> EffectClass:
        return EffectClass.NAVIGATE

    owner = Owner(NO)
    surface = AuthorableCounter()
    session = Session(surface)
    await session.look()
    await Guard(session, surface, owner, classify=trusting).act(3, "invoke")
    assert owner.asked == [] and surface.acts


async def test_tool_calls_sent_in_one_breath_run_one_at_a_time_in_order():
    """Claude may batch "fill, fill, click" into one message; the loop runs them concurrently."""
    import asyncio

    class Slow(AuthorableCounter):
        active = 0
        overlap = False

        async def act(self, resolution, verb, value):
            Slow.active += 1
            Slow.overlap = Slow.overlap or Slow.active > 1
            await asyncio.sleep(0.01)
            Slow.active -= 1
            return await super().act(resolution, verb, value)

    surface = Slow()
    session = Session(surface, inputs={"member_number": "400118"})
    await session.look()
    g = Guard(session, surface, Owner(YES))
    await asyncio.gather(
        g.act(1, "set_value", "{{input.member_number}}"),
        g.act(2, "read"),
        g.act(3, "invoke"),
    )
    assert not Slow.overlap
    assert [a[0] for a in surface.acts] == ["set_value", "read", "invoke"]
