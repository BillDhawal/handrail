"""Every question is closed, none_of_these is always on the card, and the card decides."""

import pytest

from handrail.escalate.classifier import ClassifierUnavailable, normalise
from handrail.escalate.questions import (
    NONE,
    Question,
    Verdict,
    is_this_a_commit,
    which_control,
    which_screen,
)


def test_which_screen_lists_the_declared_screens_plus_none_of_these():
    q = which_screen({"posted": "the hold was posted", "already_held": "already under hold"})
    assert list(q.options) == ["posted", "already_held", NONE]


def test_which_control_offers_menu_rows_by_index():
    rows = [(3, "invoke", "button", "F5=Search"), (7, "set_value", "textbox", "Value")]
    q = which_control(rows, "the search button")
    assert list(q.options) == ["3", "7", NONE]
    assert q.options["3"] == "invoke button 'F5=Search'"


def test_a_verdict_is_accepted_only_above_the_cards_threshold_and_margin():
    q = which_screen({"a": "", "b": ""})
    assert Verdict("which_screen", {"a": 0.9, "b": 0.05, NONE: 0.05}).accepted_by(q)
    assert not Verdict("which_screen", {"a": 0.79, "b": 0.11, NONE: 0.1}).accepted_by(q)  # below
    assert not Verdict("which_screen", {"a": 0.55, "b": 0.45, NONE: 0.0}).accepted_by(q)  # margin
    assert not Verdict("which_screen", {NONE: 0.95, "a": 0.05, "b": 0.0}).accepted_by(q)  # none


def test_normalise_fills_missing_options_with_zero_and_sums_to_one():
    v = normalise(which_screen({"a": "", "b": ""}), {"a": 3.0, "b": 1.0})
    assert v.probabilities == {"a": 0.75, "b": 0.25, NONE: 0.0}
    assert (v.chosen, v.confidence, v.margin) == ("a", 0.75, 0.5)


def test_an_option_not_on_the_card_is_refused_not_dropped():
    with pytest.raises(ClassifierUnavailable, match="not on the card"):
        normalise(which_screen({"a": ""}), {"a": 0.5, "zzz": 0.5})


def test_no_probability_mass_is_no_answer():
    with pytest.raises(ClassifierUnavailable, match="no probability mass"):
        normalise(which_screen({"a": ""}), {"a": 0.0})


def test_a_commit_question_has_no_none_of_these_because_it_is_never_decisive_alone():
    assert NONE not in is_this_a_commit().options
    assert isinstance(Question("x", "y", {"a": ""}), Question)
