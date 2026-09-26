"""The outcome taxonomy: four categories, and a code for every way a run can end.

The category is what a caller branches on. The code says why. The table at the
bottom is the single place that decides which category a code belongs to, so two
parts of the system can never classify the same ending differently.
"""

from __future__ import annotations

from enum import StrEnum


class OutcomeCategory(StrEnum):
    SUCCESS = "SUCCESS"
    BUSINESS_OUTCOME = "BUSINESS_OUTCOME"  # the application said no: an answer, not a fault
    RECOVERABLE = "RECOVERABLE"
    HARD_FAILURE = "HARD_FAILURE"


class ErrorCode(StrEnum):
    NONE = "NONE"

    # business outcomes
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    ALREADY_PROCESSED = "ALREADY_PROCESSED"

    # hard failures
    INVALID_INPUT = "INVALID_INPUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    APPLICATION_ERROR = "APPLICATION_ERROR"
    SCREEN_MISMATCH = "SCREEN_MISMATCH"
    TARGET_MISMATCH = "TARGET_MISMATCH"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    SURFACE_INCOMPATIBLE = "SURFACE_INCOMPATIBLE"
    UNSAFE_TO_RETRY = "UNSAFE_TO_RETRY"
    ABORTED_BY_OPERATOR = "ABORTED_BY_OPERATOR"

    # recoverable
    MISSING_CONTROL = "MISSING_CONTROL"
    AMBIGUOUS_CONTROL = "AMBIGUOUS_CONTROL"
    UNEXPECTED_DIALOG = "UNEXPECTED_DIALOG"
    SLOW_LOAD = "SLOW_LOAD"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    SESSION_EXPIRED = "SESSION_EXPIRED"


_C = OutcomeCategory
DEFAULT_CATEGORY: dict[ErrorCode, OutcomeCategory] = {
    ErrorCode.NONE: _C.SUCCESS,
    ErrorCode.RECORD_NOT_FOUND: _C.BUSINESS_OUTCOME,
    ErrorCode.ALREADY_PROCESSED: _C.BUSINESS_OUTCOME,
    ErrorCode.INVALID_INPUT: _C.HARD_FAILURE,
    ErrorCode.PERMISSION_DENIED: _C.HARD_FAILURE,
    ErrorCode.APPLICATION_ERROR: _C.HARD_FAILURE,
    ErrorCode.SCREEN_MISMATCH: _C.HARD_FAILURE,
    ErrorCode.TARGET_MISMATCH: _C.HARD_FAILURE,
    ErrorCode.POLICY_VIOLATION: _C.HARD_FAILURE,
    ErrorCode.SURFACE_INCOMPATIBLE: _C.HARD_FAILURE,
    ErrorCode.UNSAFE_TO_RETRY: _C.HARD_FAILURE,
    ErrorCode.ABORTED_BY_OPERATOR: _C.HARD_FAILURE,
    ErrorCode.MISSING_CONTROL: _C.RECOVERABLE,
    ErrorCode.AMBIGUOUS_CONTROL: _C.RECOVERABLE,
    ErrorCode.UNEXPECTED_DIALOG: _C.RECOVERABLE,
    ErrorCode.SLOW_LOAD: _C.RECOVERABLE,
    ErrorCode.TRANSIENT_FAILURE: _C.RECOVERABLE,
    ErrorCode.SESSION_EXPIRED: _C.RECOVERABLE,
}


class HandrailError(Exception):
    """An engine-level failure that always carries a taxonomy code."""

    def __init__(self, message: str, code: ErrorCode, step_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.step_id = step_id

    @property
    def category(self) -> OutcomeCategory:
        return DEFAULT_CATEGORY[self.code]
