"""The stage set does exactly what its script says, and nothing else."""

import pytest

from handrail.schema.errors import ErrorCode, HandrailError
from handrail.schema.target import RUNG_COST, Target
from handrail.surface.null_surface import NullSurface, Page


def target(name: str) -> Target:
    return Target.model_validate(
        {
            "role": "button",
            "name": {"eq": name},
            "supports": {"invoke": []},
            "ladder": [
                {"rung": "stable_id", "cost": RUNG_COST["stable_id"]},
                {"rung": "role_name", "cost": RUNG_COST["role_name"]},
            ],
        }
    )


def surface() -> NullSurface:
    return NullSurface(
        [
            Page(
                "inquiry",
                text="MEMBER INQUIRY",
                matches={("role_name", "Search"): 1, ("role_name", "Hold"): 2},
                advance_on=frozenset({"Search"}),
            ),
            Page(
                "record",
                text="MEMBER RECORD",
                reads={"Balance": "$42.10"},
                matches={("stable_id", "Balance"): 1},
            ),
        ]
    )


async def test_resolve_walks_the_ladder_cheapest_first_and_reports_the_rung():
    s = surface()
    found = await s.resolve(target("Search"), timeout_ms=0)
    assert (found.rung, found.rung_cost, found.handle) == ("role_name", 100, "Search")


async def test_two_matches_is_ambiguous_not_first_wins():
    with pytest.raises(HandrailError) as err:
        await surface().resolve(target("Hold"), timeout_ms=0)
    assert err.value.code is ErrorCode.AMBIGUOUS_CONTROL


async def test_no_rung_matching_is_a_missing_control():
    with pytest.raises(HandrailError) as err:
        await surface().resolve(target("Nope"), timeout_ms=0)
    assert err.value.code is ErrorCode.MISSING_CONTROL


async def test_an_action_on_a_listed_control_turns_the_page():
    s = surface()
    found = await s.resolve(target("Search"), timeout_ms=0)
    await s.act(found, "invoke", None)
    assert s.actions == [("invoke", "Search", None)]
    assert (await s.observe()).structure == ("record",)


async def test_read_returns_what_the_script_says():
    s = surface()
    s.advance()
    found = await s.resolve(target("Balance"), timeout_ms=0)
    assert (await s.act(found, "read", None)).value == "$42.10"


async def test_evaluate_answers_from_the_current_page_only():
    s = surface()
    assert await s.evaluate("target_present:Search")
    assert not await s.evaluate("target_present:Balance")
    assert await s.evaluate("screen_is:inquiry")
    assert not await s.evaluate("something_else:x")


async def test_the_operations_table_lists_only_present_controls():
    s = surface()
    s.page.matches[("role_name", "Ghost")] = 0
    names = [op.name for op in (await s.observe()).operations]
    assert names == ["Search", "Hold"]
