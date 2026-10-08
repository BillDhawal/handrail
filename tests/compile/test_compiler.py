"""The recipe writer refuses to guess, and turns one evening into a card for every member."""

from __future__ import annotations

from typing import Any

import pytest

from handrail.compile.compiler import CompileError, Source, compile_trace
from handrail.schema.target import RUNG_COST, Fingerprint, Rung
from handrail.schema.trace import Turn

ROLE = Rung(rung="role_name", cost=RUNG_COST["role_name"])
FP = Fingerprint(over=["role", "name"], value="sha256:x")
SCREENS = {"inquiry": "sig:inquiry", "member": "sig:member", "posted": "sig:posted"}
INPUTS = [
    {"name": "member_number", "pattern": "^[0-9]{6}$"},
    {"name": "password", "sensitivity": "secret"},
]
VALUES = {"member_number": "400118", "password": "hunter2"}
INQ, MEM, POST = "sig:inquiry", "sig:member", "sig:posted"


def act(seq: int, verb: str, role: str, name: str, before: str, after: str, **over: Any) -> Turn:
    base: dict[str, Any] = dict(
        seq=seq,
        tool="act",
        index=1,
        verb=verb,
        role=role,
        name=name,
        handle={"frame": "work", "selector": "x"},
        signature_before=before,
        signature_after=after,
        effect="stage",
        rungs=(ROLE,),
        fingerprint=FP,
    )
    return Turn(**{**base, **over})


def label(seq: int, name: str, sig: str) -> Turn:
    return Turn(seq, "assert_screen", label=name, signature_before=sig, signature_after=sig)


def open_member(**over: Any) -> Turn:
    return act(3, "invoke", "link", "400118", INQ, MEM, effect="navigate", **over)


def hold() -> Turn:
    confirmed = dict(effect="commit", confirmed_by="dhawal", row="400118-S0005")
    return act(5, "invoke", "link", "Hold", MEM, POST, **confirmed)


def trace() -> list[Turn]:
    return [
        label(1, "inquiry", INQ),
        act(2, "set_value", "textbox", "Value", INQ, INQ, value="{{input.member_number}}"),
        open_member(),
        label(4, "member", MEM),
        hold(),
        label(6, "posted", POST),
        act(7, "read", "status", "Result", POST, POST, effect="read"),
        Turn(seq=8, tool="finish", label="posted", signature_before=POST, signature_after=POST),
    ]


def source(turns: list[Turn] | None = None, **over: Any) -> Source:
    base: dict[str, Any] = dict(
        id="bank.place_hold",
        title="Place a hold",
        entry="{{env.BASE_URL}}/inquiry",
        inputs=INPUTS,
        values=VALUES,
        screens=SCREENS,
        trace=turns if turns is not None else trace(),
        allowed_hosts=["127.0.0.1:8081"],
    )
    return Source(**{**base, **over})


def refused(turns: list[Turn], match: str | None, **over: Any) -> CompileError:
    with pytest.raises(CompileError, match=match) as err:
        compile_trace(source(turns, **over))
    return err.value


def test_a_good_book_becomes_a_valid_draft_card():
    cap = compile_trace(source())
    assert cap.lifecycle.state == "draft"
    assert [s.op.verb for s in cap.steps] == ["set_value", "invoke", "invoke", "read"]
    assert cap.outcomes["posted"].category == "SUCCESS"
    assert cap.safety.allowed_verbs == ["invoke", "read", "set_value"]


def test_a_literal_input_value_in_a_name_becomes_a_blank():
    cap = compile_trace(source())
    link = cap.targets[cap.steps[1].target or ""]
    assert link.name and link.name.eq == "{{input.member_number}}"


def test_a_live_handle_and_a_stored_one_both_give_the_frame_scope():
    from handrail.surface.browser.walk import Handle

    turns = trace()
    turns[2] = open_member(handle=Handle("work", "x"))
    cap = compile_trace(source(turns))
    assert [s.role for s in cap.targets[cap.steps[1].target or ""].scope] == ["frame"]


def test_a_blanked_name_is_dropped_from_the_fingerprint_and_a_literal_one_is_kept():
    from handrail.surface.browser.fingerprint import fingerprint, same_control
    from handrail.surface.browser.operations import Control

    turns = trace()
    turns[2] = open_member(ancestors=("table", "row", "cell"))
    turns[4] = hold()
    cap = compile_trace(source(turns))
    link = cap.targets[cap.steps[1].target or ""]
    assert link.fingerprint and "name" not in link.fingerprint.over
    another_member = Control("link", "400337", ancestors=("table", "row", "cell"))
    assert same_control(link.fingerprint, another_member)
    hold_fp = cap.targets[cap.steps[2].target or ""].fingerprint
    assert hold_fp and "name" in hold_fp.over
    assert hold_fp == fingerprint(Control("link", "Hold"))  # identical to what the guard took


def test_a_row_stays_literal_unless_it_equals_an_input():
    cap = compile_trace(source())
    hold = cap.targets[cap.steps[2].target or ""]
    assert [s.role for s in hold.scope] == ["frame", "row"]
    assert hold.scope[1].name == "400118-S0005"
    with_share = source(
        values={**VALUES, "share_id": "400118-S0005"}, inputs=[*INPUTS, {"name": "share_id"}]
    )
    bound = compile_trace(with_share)
    assert bound.targets[bound.steps[2].target or ""].scope[1].name == "{{input.share_id}}"


def test_settles_are_screen_is_after_a_change_and_target_present_otherwise():
    cap = compile_trace(source())
    first, second = cap.steps[0].settle, cap.steps[1].settle
    assert (first.kind, first.step) == ("target_present", cap.steps[1].id)
    assert (second.kind, second.screen) == ("screen_is", "member")
    assert cap.steps[1].expect and cap.steps[1].expect.screen_in == ["member"]


def test_the_confirmed_commit_keeps_the_persons_name():
    effect = compile_trace(source()).steps[2].effect
    assert (effect.kind, effect.confirmed_by) == ("commit", "dhawal")


def test_a_read_becomes_an_output_produced_on_the_outcome():
    cap = compile_trace(source())
    assert [o.name for o in cap.outputs] == ["result"]
    assert cap.outputs[0].source.step == cap.steps[3].id
    assert cap.outputs[0].produced_on == ["posted"]


def test_reading_back_a_field_is_not_an_output():
    turns = trace()
    turns.insert(2, act(9, "read", "textbox", "Password", INQ, INQ, effect="read"))
    cap = compile_trace(source(turns))
    assert [o.name for o in cap.outputs] == ["result"]  # the status line, not the field


def test_acting_on_an_unlabelled_screen_is_refused_by_line():
    without_inquiry = {k: v for k, v in SCREENS.items() if k != "inquiry"}
    err = refused(trace(), "nobody labelled", screens=without_inquiry)
    assert "turn 2: acted on a screen nobody labelled" in err.reasons


def test_landing_on_an_unlabelled_screen_is_refused():
    turns = trace()
    turns[2] = act(3, "invoke", "link", "400118", INQ, "sig:nowhere", effect="navigate")
    refused(turns, "turn 3: landed on a screen nobody labelled")


def test_a_control_no_rung_can_find_is_refused():
    turns = trace()
    turns[2] = open_member(rungs=())
    refused(turns, "no rung can find link '400118' again")


def test_a_typed_literal_that_belongs_to_an_input_is_refused():
    turns = trace()
    turns[1] = act(2, "set_value", "textbox", "Value", INQ, INQ, value="400118")
    refused(turns, "typed the value of an input as a literal")


def test_a_secret_inside_any_typed_value_is_refused():
    turns = trace()
    turns[1] = act(2, "set_value", "textbox", "Value", INQ, INQ, value="xhunter2x")
    refused(turns, "a secret appears in the typed value")


def test_a_run_without_finish_has_no_outcome_and_is_refused():
    refused(trace()[:-1], "never called finish")


def test_every_hole_is_reported_not_just_the_first():
    turns = trace()[:-1]
    turns[2] = open_member(rungs=())
    assert len(refused(turns, None).reasons) == 2
