"""Only a named person puts a verified card on the menu, and a draft never gets there."""

import pytest

from handrail.compile.approve import NotApprovable, approve, deprecate
from handrail.schema.capability import Capability

from ..factory import place_hold


def verified() -> Capability:
    cap = place_hold()
    for step in cap["steps"]:
        if step["effect"]["kind"] == "commit":
            step["effect"]["confirmed_by"] = "dhawal"
    cap["lifecycle"] = {"state": "verified", "reliability": {"replays": 3, "clean": 3}}
    return Capability.model_validate(cap)


def test_a_verified_card_signed_by_a_name_is_approved():
    card = approve(verified(), "dhawal", when="2026-10-08T12:00:00+00:00")
    assert (card.lifecycle.state, card.lifecycle.approved_by) == ("approved", "dhawal")
    assert card.lifecycle.approved_at == "2026-10-08T12:00:00+00:00"
    assert card.lifecycle.reliability.clean == 3  # the tasting's record travels with it


def test_a_draft_cannot_be_approved_however_good_it_looks():
    with pytest.raises(NotApprovable, match="a draft card cannot be approved; verify it first"):
        approve(Capability.model_validate(place_hold()), "dhawal")


def test_approval_needs_a_name_and_happens_once():
    with pytest.raises(NotApprovable, match="needs a name"):
        approve(verified(), "  ")
    with pytest.raises(NotApprovable, match="already approved by dhawal"):
        approve(approve(verified(), "dhawal"), "someone else")


def test_deprecation_is_the_only_way_off_the_menu_and_keeps_the_reason():
    card = deprecate(approve(verified(), "dhawal"), "dhawal", "the bank retired the screen")
    assert card.lifecycle.state == "deprecated"
    assert (card.lifecycle.deprecated_by, card.lifecycle.note) == (
        "dhawal",
        "the bank retired the screen",
    )
