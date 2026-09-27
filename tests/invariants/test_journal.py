"""Invariant 2: a step that is dispatched and not observed is never re-executed.

These tests pin the journal's answers. The engine tests that follow pin that the
engine actually asks.
"""

import json

from handrail.replay.journal import Journal


def test_a_dispatched_step_is_in_doubt_until_it_is_observed():
    j = Journal()
    j.dispatch("post_hold")
    assert j.in_doubt("post_hold")
    assert j.steps_in_doubt() == ["post_hold"]
    j.observe("post_hold")
    assert not j.in_doubt("post_hold")
    assert j.already_done("post_hold")


def test_a_step_never_dispatched_is_neither_in_doubt_nor_done():
    j = Journal()
    assert not j.in_doubt("post_hold")
    assert not j.already_done("post_hold")


def test_the_line_is_on_disk_before_dispatch_returns(tmp_path):
    path = tmp_path / "journal.jsonl"
    j = Journal(path)
    j.dispatch("post_hold")
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert lines == [{"seq": 1, "kind": "dispatched", "name": "post_hold"}]


def test_a_crashed_run_reloads_with_its_doubts_intact(tmp_path):
    path = tmp_path / "journal.jsonl"
    first = Journal(path)
    first.reached("hold_form")
    first.dispatch("post_hold")
    # the lights go out here: no observe() ever happens
    second = Journal.load(path)
    assert second.in_doubt("post_hold")
    assert second.safe_rewind_targets() == []


def test_there_is_no_way_to_erase_an_entry():
    j = Journal()
    for name in ("remove", "delete", "pop", "clear", "rewrite", "truncate"):
        assert not hasattr(j, name)
    j.dispatch("x")
    assert len(j.entries) == 1


def test_rewind_targets_are_only_screens_with_nothing_dispatched_after_them():
    j = Journal()
    j.reached("inquiry")
    j.reached("hold_form")
    assert j.safe_rewind_targets() == ["hold_form", "inquiry"]
    j.dispatch("post_hold")
    assert j.safe_rewind_targets() == []
    j.observe("post_hold")
    assert j.safe_rewind_targets() == [], "observed does not make the past safe again"
    j.reached("posted")
    assert j.safe_rewind_targets() == ["posted"]


def test_a_stage_step_blocks_rewind_exactly_like_a_commit():
    j = Journal()
    j.reached("inquiry")
    j.dispatch("enter_member")  # a stage step: still a dispatch
    assert j.safe_rewind_targets() == []
