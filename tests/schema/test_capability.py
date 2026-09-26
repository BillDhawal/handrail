"""Each test breaks one thing in a valid capability and expects a refusal that names it."""

import pytest
from pydantic import ValidationError

from handrail.schema.capability import Capability

from ..factory import place_hold, step


def load(cap):
    return Capability.model_validate(cap)


def refused(cap, match):
    with pytest.raises(ValidationError, match=match):
        load(cap)


def test_the_factory_capability_is_valid_and_starts_as_a_draft():
    cap = load(place_hold())
    assert cap.ref == "bank.place_hold@1.0.0"
    assert cap.lifecycle.state == "draft"
    assert cap.step("post_hold").effect.probe == "hold_exists"


def test_it_round_trips_through_json_unchanged():
    cap = load(place_hold())
    assert Capability.model_validate_json(cap.model_dump_json()) == cap


def test_a_step_without_an_effect_class_does_not_validate():
    cap = place_hold()
    del step(cap, "post_hold")["effect"]
    refused(cap, "effect")


def test_a_step_without_a_screen_does_not_validate():
    cap = place_hold()
    del step(cap, "post_hold")["screen"]
    refused(cap, "screen")


def test_a_step_must_run_on_a_declared_screen():
    cap = place_hold()
    step(cap, "post_hold")["screen"] = "somewhere_else"
    refused(cap, "unknown screen 'somewhere_else'")


def test_a_step_must_name_a_declared_target_that_supports_its_verb():
    cap = place_hold()
    step(cap, "post_hold")["target"] = "nope"
    refused(cap, "unknown target 'nope'")
    cap = place_hold()
    step(cap, "post_hold")["target"] = "member_field"
    refused(cap, "does not support invoke")


def test_a_targeted_verb_needs_a_target():
    cap = place_hold()
    step(cap, "post_hold")["target"] = None
    refused(cap, "invoke needs a target")


def test_expected_screens_are_a_closed_list_of_declared_screens():
    cap = place_hold()
    step(cap, "post_hold")["expect"]["screen_in"].append("surprise")
    refused(cap, "expects unknown screen 'surprise'")


def test_an_outcome_must_be_a_screen_and_one_must_be_success():
    cap = place_hold()
    cap["outcomes"]["ghost"] = {"category": "SUCCESS"}
    refused(cap, "'ghost' is not a declared screen")
    cap = place_hold()
    del cap["outcomes"]["posted"]
    cap["outputs"] = []
    refused(cap, "no outcome is a SUCCESS")


def test_an_outcome_cannot_call_a_business_answer_a_failure():
    cap = place_hold()
    cap["outcomes"]["already_held"]["category"] = "HARD_FAILURE"
    refused(cap, "ALREADY_PROCESSED is not a HARD_FAILURE")


def test_outputs_live_only_in_outputs_and_come_from_read_steps():
    cap = place_hold()
    cap["outputs"][0]["source"]["step"] = "post_hold"
    refused(cap, "source must be a read step")
    cap = place_hold()
    cap["outputs"][0]["produced_on"] = ["nowhere"]
    refused(cap, "'nowhere' is not an outcome")


def test_binding_residue_is_refused_when_the_artifact_is_built():
    cap = place_hold()
    step(cap, "enter_member")["op"]["value"] = "{{member_number}}"
    refused(cap, "binding residue")


def test_a_binding_must_name_a_declared_input():
    cap = place_hold()
    step(cap, "enter_member")["op"]["value"] = "{{input.account}}"
    refused(cap, "input.account")


def test_a_verb_outside_the_safety_block_is_refused():
    cap = place_hold()
    cap["safety"]["allowed_verbs"] = ["read", "set_value", "select"]
    refused(cap, "verb invoke is outside safety.allowed_verbs")


def test_a_capability_cannot_leave_draft_with_an_unconfirmed_commit():
    cap = place_hold()
    cap["lifecycle"] = {"state": "verified"}
    refused(cap, "commit steps not confirmed by a person: \\['post_hold'\\]")
    step(cap, "post_hold")["effect"]["confirmed_by"] = "dgajwe"
    assert load(cap).lifecycle.state == "verified"


def test_approval_needs_a_name():
    cap = place_hold()
    step(cap, "post_hold")["effect"]["confirmed_by"] = "dgajwe"
    cap["lifecycle"] = {"state": "approved"}
    refused(cap, "approved: needs approved_by")


def test_unknown_fields_are_refused_so_a_typo_cannot_hide():
    cap = place_hold()
    cap["safe_restart"] = True
    refused(cap, "safe_restart")
