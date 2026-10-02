"""A direction is kept only if it leads to exactly one house, and the right one."""

from typing import Any

import pytest

from handrail.schema.target import Rung, Target
from handrail.surface.browser.locators import Query, candidates, query_for, surviving
from handrail.surface.browser.operations import Control


class Street:
    """A scripted page: each query finds the handles the test says it finds."""

    def __init__(self, found: dict[Query, list[Any]]) -> None:
        self.found = found
        self.asked: list[Query] = []

    async def count(self, query: Query) -> int:
        self.asked.append(query)
        return len(self.found.get(query, []))

    async def is_same(self, query: Query, handle: Any) -> bool:
        return self.found[query][0] is handle


ME = object()
NEIGHBOUR = object()

ROLE = Query("role", role="button", name="F5=Sign On")
TEXT = Query("text", "F5=Sign On")


def kinds(rungs: list[Rung]) -> list[str]:
    return [r.rung for r in rungs]


def test_candidates_come_cheapest_first_so_the_ladder_is_already_ranked():
    control = Control("button", "Save", attr_name="sv", test_id="save-btn")
    rungs = candidates(control)
    assert kinds(rungs) == ["stable_id", "role_name", "text", "native"]
    Target(role="button", supports={"invoke": []}, ladder=rungs)  # the schema agrees


def test_a_field_with_no_accessible_name_is_found_by_its_caption_not_by_role():
    control = Control("textbox", label="Operator ID", attr_name="opid")
    assert kinds(candidates(control)) == ["label", "native"]


def test_a_position_rung_is_never_proposed():
    everything = Control("link", "Hold", label="x", attr_name="h", test_id="t")
    assert "position" not in kinds(candidates(everything))


async def test_a_rung_that_finds_three_controls_does_not_survive():
    control = Control("button", "F5=Sign On", handle=ME)
    street = Street({ROLE: [ME, NEIGHBOUR, NEIGHBOUR], TEXT: [ME]})
    assert kinds(await surviving(control, street)) == ["text"]


async def test_a_rung_that_finds_nothing_does_not_survive():
    control = Control("button", "F5=Sign On", handle=ME)
    street = Street({ROLE: [ME]})
    assert kinds(await surviving(control, street)) == ["role_name"]


async def test_a_rung_that_finds_exactly_one_control_but_the_wrong_one_does_not_survive():
    control = Control("button", "F5=Sign On", handle=ME)
    street = Street({ROLE: [NEIGHBOUR], TEXT: [ME]})
    assert kinds(await surviving(control, street)) == ["text"]


async def test_a_control_nothing_can_find_has_an_empty_ladder_for_the_compiler_to_refuse():
    control = Control("button", "F5=Sign On", handle=ME)
    assert await surviving(control, Street({})) == []


async def test_authoring_probes_with_the_same_question_replay_will_ask():
    control = Control("textbox", label="Operator ID", attr_name="opid", handle=ME)
    street = Street({})
    await surviving(control, street)
    assert street.asked == [query_for(r, "textbox", "") for r in candidates(control)]


def test_the_label_rung_looks_for_the_first_field_after_the_caption():
    (label, _) = candidates(Control("textbox", label="Operator ID", attr_name="opid"))
    query = query_for(label, "textbox", "")
    assert query == Query(
        "selector",
        "xpath=//*[normalize-space(text())='Operator ID']"
        "/following::*[self::input or self::select or self::textarea][1]",
    )


def test_a_caption_with_both_kinds_of_quote_still_makes_a_valid_question():
    (label,) = candidates(Control("textbox", label="""Member's "DBA" name"""))
    assert "concat('Member', \"'\", 's \"DBA\" name')" in query_for(label, "textbox", "").value


def test_a_name_attribute_with_a_quote_cannot_break_out_of_the_selector():
    (native,) = candidates(Control("textbox", attr_name='a"]b'))
    assert native.value == '[name="a\\"]b"]'
    assert native.surface == "browser"


def test_the_browser_refuses_a_rung_it_cannot_follow():
    foreign = Rung(rung="native", cost=10_000_000, surface="terminal", value="row 3 col 12")
    with pytest.raises(ValueError, match="cannot follow"):
        query_for(foreign, "textbox", "")
