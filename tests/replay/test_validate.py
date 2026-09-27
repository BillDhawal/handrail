"""The bouncer refuses at the door, and names why, before any screen is touched."""

import pytest

from handrail.replay.validate import validate_inputs
from handrail.schema.capability import Capability
from handrail.schema.errors import ErrorCode, HandrailError

from ..factory import place_hold


def cap(**extra_inputs) -> Capability:
    d = place_hold()
    d["inputs"] += [dict(name=k, **v) for k, v in extra_inputs.items()]
    return Capability.model_validate(d)


def refused(capability, supplied, match):
    with pytest.raises(HandrailError, match=match) as err:
        validate_inputs(capability, supplied)
    assert err.value.code is ErrorCode.INVALID_INPUT


def test_good_inputs_come_back_typed():
    out = validate_inputs(cap(), {"member_number": "400118", "reason": "LEGAL"})
    assert out == {"member_number": "400118", "reason": "LEGAL"}


def test_an_undeclared_input_is_refused_not_ignored():
    refused(cap(), {"member_number": "400118", "reason": "LEGAL", "notes": "x"}, r"\['notes'\]")


def test_a_missing_required_input_is_named():
    refused(cap(), {"reason": "LEGAL"}, "required input missing: member_number")


def test_a_pattern_is_enforced():
    refused(cap(), {"member_number": "40011", "reason": "LEGAL"}, "does not match")


def test_an_enum_is_closed():
    refused(cap(), {"member_number": "400118", "reason": "BECAUSE"}, "must be one of")


def test_optional_inputs_may_be_absent():
    c = cap(notes={"required": False})
    assert "notes" not in validate_inputs(c, {"member_number": "400118", "reason": "LEGAL"})


def test_numbers_are_numbers_and_a_json_true_is_not_one():
    c = cap(amount={"type": "number"})
    good = {"member_number": "400118", "reason": "LEGAL", "amount": "12.50"}
    assert validate_inputs(c, good)["amount"] == 12.5
    refused(c, {**good, "amount": True}, "is a boolean, not a number")
    refused(c, {**good, "amount": "lots"}, "is not a number")


def test_booleans_accept_the_usual_words_and_nothing_else():
    c = cap(urgent={"type": "boolean"})
    base = {"member_number": "400118", "reason": "LEGAL"}
    assert validate_inputs(c, {**base, "urgent": "yes"})["urgent"] is True
    assert validate_inputs(c, {**base, "urgent": "off"})["urgent"] is False
    refused(c, {**base, "urgent": "maybe"}, "is not a boolean")
