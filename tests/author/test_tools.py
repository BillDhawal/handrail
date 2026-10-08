"""The guest may say three things, and only what is on the card."""

from __future__ import annotations

import pytest

from handrail.author.tools import Session, ToolRefused, act, assert_screen, finish
from handrail.schema.trace import Turn
from handrail.surface.base import ActResult, EvidenceBundle, Observation, Operation, Resolution


class Counter:
    """A two-page stage set: a form, then a result. Records every act."""

    kind = "null"

    def __init__(self) -> None:
        self.page = 0
        self.acts: list[tuple[str, object, str | None]] = []

    async def open(self, entry: str) -> None:
        pass

    async def observe(self) -> Observation:
        if self.page == 0:
            ops = (
                Operation(1, "set_value", "textbox", "Member", handle="h-member"),
                Operation(2, "read", "textbox", "Member", handle="h-member"),
                Operation(3, "invoke", "button", "F5=Search", handle="h-search"),
            )
            return Observation(text="MEMBER INQUIRY", operations=ops, structure=("sig:form",))
        ops = (Operation(1, "read", "status", "Result", handle="h-result"),)
        return Observation(text="HOLD POSTED", operations=ops, structure=("sig:result",))

    async def resolve(self, target, timeout_ms):  # pragma: no cover - authoring never resolves
        raise AssertionError("authoring acts by menu row, never by ladder")

    async def act(self, resolution: Resolution | None, verb, value) -> ActResult:
        self.acts.append((verb, resolution.handle if resolution else None, value))
        if verb == "invoke":
            self.page = 1
        return ActResult(ok=True, value="HOLD POSTED CONFIRMATION HX-1" if verb == "read" else None)

    async def evaluate(self, condition: str) -> bool:
        return True

    async def evidence(self) -> EvidenceBundle:
        return EvidenceBundle()

    async def close(self) -> None:
        pass


def session() -> tuple[Session, Counter]:
    surface = Counter()
    return Session(surface, inputs={"member_number": "400118"}), surface


async def test_the_menu_is_what_the_model_sees():
    s, _ = session()
    shown = await s.look()
    assert shown.startswith("MEMBER INQUIRY")
    assert "3: invoke button 'F5=Search'" in shown


async def test_a_row_off_the_menu_is_refused_and_nothing_happens():
    s, surface = session()
    await s.look()
    with pytest.raises(ToolRefused, match="not on the menu"):
        await act(s, 9, "invoke")
    assert surface.acts == [] and s.trace == []


async def test_the_model_may_only_agree_with_the_rows_verb():
    s, surface = session()
    await s.look()
    with pytest.raises(ToolRefused, match="is read .* not set_value"):
        await act(s, 2, "set_value", "x")
    assert surface.acts == []


async def test_set_value_needs_a_value_and_invoke_takes_none():
    s, _ = session()
    await s.look()
    with pytest.raises(ToolRefused, match="needs a value"):
        await act(s, 1, "set_value")
    with pytest.raises(ToolRefused, match="takes no value"):
        await act(s, 3, "invoke", "why")


async def test_a_blank_is_filled_for_the_surface_but_stored_unfilled():
    s, surface = session()
    await s.look()
    await act(s, 1, "set_value", "{{input.member_number}}")
    assert surface.acts == [("set_value", "h-member", "400118")]
    assert s.trace[-1].value == "{{input.member_number}}"  # the trace never holds the literal


async def test_a_blank_naming_an_unknown_input_is_refused():
    s, _ = session()
    await s.look()
    with pytest.raises(ToolRefused, match="not supplied"):
        await act(s, 1, "set_value", "{{input.nope}}")


async def test_an_accepted_act_records_the_turn_and_returns_the_new_menu():
    s, _ = session()
    await s.look()
    shown = await act(s, 3, "invoke")
    assert shown.startswith("HOLD POSTED")
    turn = s.trace[-1]
    assert isinstance(turn, Turn)
    assert (turn.tool, turn.index, turn.verb) == ("act", 3, "invoke")
    assert (turn.role, turn.name) == ("button", "F5=Search")
    assert (turn.signature_before, turn.signature_after) == ("sig:form", "sig:result")


async def test_a_read_returns_what_was_read_and_keeps_it_in_the_turn():
    s, _ = session()
    await s.look()
    await act(s, 3, "invoke")
    shown = await act(s, 1, "read")
    assert shown.startswith("read: HOLD POSTED CONFIRMATION HX-1")
    assert s.trace[-1].read_value == "HOLD POSTED CONFIRMATION HX-1"


async def test_assert_screen_pins_a_label_to_the_signature():
    s, _ = session()
    await s.look()
    assert await assert_screen(s, "inquiry") == "screen 'inquiry' recorded"
    assert s.screens == {"inquiry": "sig:form"}


async def test_one_label_cannot_name_two_screens_nor_one_screen_two_labels():
    s, _ = session()
    await s.look()
    await assert_screen(s, "inquiry")
    with pytest.raises(ToolRefused, match="already labelled"):
        await assert_screen(s, "another name")
    await act(s, 3, "invoke")
    with pytest.raises(ToolRefused, match="already names a different screen"):
        await assert_screen(s, "inquiry")


async def test_finish_needs_a_labelled_screen_that_is_showing_now():
    s, _ = session()
    await s.look()
    await assert_screen(s, "inquiry")
    with pytest.raises(ToolRefused, match="not a labelled screen"):
        await finish(s, "posted")
    await act(s, 3, "invoke")
    with pytest.raises(ToolRefused, match="not 'inquiry'"):
        await finish(s, "inquiry")
    await assert_screen(s, "posted")
    assert await finish(s, "posted") == "finished on 'posted'"
    assert s.finished and s.outcome == "posted"


async def test_nothing_is_accepted_after_finish():
    s, _ = session()
    await s.look()
    await assert_screen(s, "inquiry")
    await finish(s, "inquiry")
    with pytest.raises(ToolRefused, match="finished"):
        await act(s, 3, "invoke")
