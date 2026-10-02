"""The fingerprint says "same control" for the right reasons, and only those."""

import dataclasses

import pytest

from handrail.schema.target import Fingerprint
from handrail.surface.browser.fingerprint import _hash, fields_for, fingerprint, same_control
from handrail.surface.browser.operations import Control

FORM = ("table", "row", "cell")

POST = Control("button", "F10=Post Hold", ancestors=FORM)
CONFIRMATION = Control("status", "CONFIRMATION HX-829120", ancestors=("main",))


def test_two_buttons_with_different_labels_do_not_hash_the_same():
    # The prototype's first bug: a submit button's value is its label.
    cancel = dataclasses.replace(POST, name="F3=Cancel")
    assert fingerprint(POST).value != fingerprint(cancel).value


def test_a_read_controls_own_text_is_not_drift():
    # The prototype's second bug: the text of a read step is the value being read.
    tomorrow = dataclasses.replace(CONFIRMATION, name="CONFIRMATION HX-829121")
    assert same_control(fingerprint(CONFIRMATION), tomorrow)
    assert "name" not in fields_for(CONFIRMATION)


def test_a_field_you_can_type_into_keeps_its_name_in_the_fingerprint():
    field = Control("textbox", label="Operator ID", ancestors=FORM)
    other = Control("textbox", label="Password", ancestors=FORM)
    assert "name" in fields_for(field)
    assert not same_control(fingerprint(field), other)


def test_the_same_control_seen_twice_has_the_same_fingerprint():
    again = Control("button", "F10=Post Hold", ancestors=FORM, handle=object())
    assert fingerprint(POST) == fingerprint(again)


def test_where_the_control_was_found_is_not_part_of_what_it_is():
    # attr_name and test_id are ways to find it; a renamed form field is a ladder matter.
    renamed = dataclasses.replace(POST, attr_name="btn2", test_id="x")
    assert same_control(fingerprint(POST), renamed)


def test_a_control_that_moved_to_a_different_container_is_a_different_control():
    in_a_dialog = dataclasses.replace(POST, ancestors=("dialog",))
    assert not same_control(fingerprint(POST), in_a_dialog)


def test_a_button_that_became_a_link_is_a_different_control():
    assert not same_control(fingerprint(POST), dataclasses.replace(POST, role="link"))


def test_a_button_that_went_disabled_no_longer_matches():
    # Its supports became empty: it is there, but it is not the control that was recorded.
    assert not same_control(fingerprint(POST), dataclasses.replace(POST, disabled=True))


def test_the_check_hashes_the_fields_the_artifact_lists_not_todays_defaults():
    stored = Fingerprint(over=["role"], value=_hash(["role"], POST))
    assert same_control(stored, dataclasses.replace(POST, name="anything at all"))
    assert not same_control(stored, dataclasses.replace(POST, role="link"))


def test_an_unknown_field_in_a_stored_fingerprint_is_refused_not_ignored():
    with pytest.raises(ValueError, match="cannot be taken over"):
        same_control(Fingerprint(over=["colour"], value="x"), POST)


def test_the_value_is_short_and_says_how_it_was_made():
    value = fingerprint(POST).value
    assert value.startswith("sha256:") and len(value) == len("sha256:") + 16
