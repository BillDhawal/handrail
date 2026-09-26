"""Invariant 12: model help is counted, in two separate counters, and defaults to none."""

import pytest
from pydantic import ValidationError

from handrail.schema.errors import ErrorCode, OutcomeCategory
from handrail.schema.results import Drift, ErrorDetail, RunResult


def result(**over):
    base = {
        "run_id": "run_1",
        "capability_id": "bank.place_hold",
        "capability_version": "1.0.0",
        "started_at": "2026-09-19T10:00:00+00:00",
        "duration_ms": 850,
        "category": OutcomeCategory.SUCCESS,
    }
    base.update(over)
    return RunResult.model_validate(base)


def test_the_ordinary_path_reports_no_model_help_of_either_kind():
    r = result()
    assert (r.classifier_calls, r.llm_calls, r.escalated_to_human) == (0, 0, False)
    assert r.ok and not r.retryable


def test_the_two_counters_are_separate_fields():
    r = result(classifier_calls=2, llm_calls=5)
    assert r.classifier_calls == 2 and r.llm_calls == 5


def test_a_business_outcome_is_an_answer_so_it_carries_no_error():
    r = result(
        category=OutcomeCategory.BUSINESS_OUTCOME,
        code=ErrorCode.ALREADY_PROCESSED,
        outcome="already_held",
    )
    assert not r.ok and not r.retryable and r.error is None
    with pytest.raises(ValidationError, match="an answer is not an error"):
        result(
            category=OutcomeCategory.BUSINESS_OUTCOME,
            code=ErrorCode.ALREADY_PROCESSED,
            error=ErrorDetail(code=ErrorCode.ALREADY_PROCESSED, message="x"),
        )


def test_a_failure_must_say_what_failed():
    with pytest.raises(ValidationError, match="must say what failed"):
        result(category=OutcomeCategory.HARD_FAILURE, code=ErrorCode.SCREEN_MISMATCH)


def test_only_a_recoverable_result_invites_a_retry():
    r = result(
        category=OutcomeCategory.RECOVERABLE,
        code=ErrorCode.SLOW_LOAD,
        error=ErrorDetail(code=ErrorCode.SLOW_LOAD, message="timed out", step_id="s2"),
    )
    assert r.retryable
    unsafe = result(
        category=OutcomeCategory.HARD_FAILURE,
        code=ErrorCode.UNSAFE_TO_RETRY,
        error=ErrorDetail(code=ErrorCode.UNSAFE_TO_RETRY, message="post_hold is in doubt"),
    )
    assert not unsafe.retryable


def test_category_and_code_cannot_disagree():
    with pytest.raises(ValidationError, match="ALREADY_PROCESSED is not a SUCCESS"):
        result(code=ErrorCode.ALREADY_PROCESSED)


def test_drift_is_the_share_of_steps_found_by_their_first_choice():
    assert Drift().score == 1.0
    assert Drift(steps_resolved=10, first_choice=9).score == 0.9
