import pytest
from pydantic import ValidationError

from handrail.schema.target import RUNG_COST, NameMatch, Rung, Target


def button(**over):
    base = {
        "role": "button",
        "name": {"eq": "F10=Post Hold"},
        "supports": {"invoke": []},
        "ladder": [
            {"rung": "stable_id", "cost": RUNG_COST["stable_id"]},
            {"rung": "role_name", "cost": RUNG_COST["role_name"]},
        ],
    }
    base.update(over)
    return Target.model_validate(base)


def test_a_target_is_described_the_way_a_screen_reader_would():
    target = button()
    assert target.role == "button"
    assert target.name == NameMatch(eq="F10=Post Hold")
    assert list(target.supports) == ["invoke"]


def test_a_name_is_either_exact_or_a_pattern_never_both_or_neither():
    with pytest.raises(ValidationError, match="exactly one"):
        NameMatch()
    with pytest.raises(ValidationError, match="exactly one"):
        NameMatch(eq="a", matches="a.*")


def test_rungs_are_listed_cheapest_first_so_drift_is_measurable():
    with pytest.raises(ValidationError, match="cheapest first"):
        button(ladder=[{"rung": "role_name", "cost": 100}, {"rung": "stable_id", "cost": 1}])


def test_two_rungs_may_not_tie():
    with pytest.raises(ValidationError, match="share a cost"):
        button(ladder=[{"rung": "label", "cost": 140}, {"rung": "text", "cost": 140}])


def test_a_surface_specific_rung_must_say_which_surface():
    with pytest.raises(ValidationError, match="which surface"):
        Rung(rung="native", cost=RUNG_COST["native"], value="input.btn")
    ok = Rung(rung="native", cost=RUNG_COST["native"], surface="browser", value="input.btn")
    assert ok.surface == "browser"


def test_an_unknown_verb_is_refused():
    with pytest.raises(ValidationError):
        button(supports={"click": []})


def test_a_target_needs_at_least_one_rung():
    with pytest.raises(ValidationError):
        button(ladder=[])
