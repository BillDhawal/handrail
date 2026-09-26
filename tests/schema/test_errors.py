"""Invariant 9: the four outcome categories stay distinct."""

from handrail.schema.errors import DEFAULT_CATEGORY, ErrorCode, HandrailError, OutcomeCategory


def test_every_code_belongs_to_exactly_one_category():
    assert set(DEFAULT_CATEGORY) == set(ErrorCode)


def test_the_application_saying_no_is_an_answer_not_a_failure():
    for code in (ErrorCode.ALREADY_PROCESSED, ErrorCode.RECORD_NOT_FOUND):
        assert DEFAULT_CATEGORY[code] is OutcomeCategory.BUSINESS_OUTCOME


def test_only_the_absence_of_an_error_is_success():
    successes = [c for c, cat in DEFAULT_CATEGORY.items() if cat is OutcomeCategory.SUCCESS]
    assert successes == [ErrorCode.NONE]


def test_refusing_to_retry_is_a_hard_failure_never_a_retryable_one():
    assert DEFAULT_CATEGORY[ErrorCode.UNSAFE_TO_RETRY] is OutcomeCategory.HARD_FAILURE


def test_an_error_derives_its_category_from_its_code():
    err = HandrailError("no such control", ErrorCode.MISSING_CONTROL, step_id="s3")
    assert err.category is OutcomeCategory.RECOVERABLE
    assert err.step_id == "s3"
