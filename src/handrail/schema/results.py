"""What a caller gets back. Never a bare exception, never a raw string.

A result says which of the four ways the run ended, what it produced, and exactly
how much model help it needed. The two counters are separate on purpose: a cheap
closed-set classifier and a generative model are different kinds of risk, and an
auditor will want to know that the ordinary path used neither.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import DEFAULT_CATEGORY, ErrorCode, OutcomeCategory


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(_Model):
    code: ErrorCode
    message: str
    step_id: str | None = None
    expected: str | None = None
    observed: str | None = None


class StepReport(_Model):
    step_id: str
    status: Literal["ok", "already_done", "recovered", "bridged", "skipped", "failed"]
    #: Which rung of the ladder found the control, and what it cost. Drift shows here first.
    rung: str | None = None
    rung_cost: int | None = None
    note: str | None = None


class Drift(_Model):
    steps_resolved: int = 0
    first_choice: int = 0

    @property
    def score(self) -> float:
        return 1.0 if self.steps_resolved == 0 else self.first_choice / self.steps_resolved


class RunResult(_Model):
    run_id: str
    capability_id: str
    capability_version: str
    started_at: str
    duration_ms: int
    category: OutcomeCategory
    code: ErrorCode = ErrorCode.NONE
    outcome: str | None = None  # the outcome screen the run ended on, if any
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail | None = None
    steps: list[StepReport] = Field(default_factory=list)
    drift: Drift = Field(default_factory=Drift)
    #: Both are zero on the ordinary path. Anything else means the ladder was climbed.
    classifier_calls: int = 0
    llm_calls: int = 0
    escalated_to_human: bool = False

    @property
    def ok(self) -> bool:
        return self.category is OutcomeCategory.SUCCESS

    @property
    def retryable(self) -> bool:
        """What a calling agent needs most: may I try this again?"""
        return self.category is OutcomeCategory.RECOVERABLE

    @model_validator(mode="after")
    def _coherent(self) -> RunResult:
        if DEFAULT_CATEGORY[self.code] is not self.category:
            raise ValueError(f"{self.code.value} is not a {self.category.value}")
        answered = self.category in (OutcomeCategory.SUCCESS, OutcomeCategory.BUSINESS_OUTCOME)
        if answered and self.error is not None:
            raise ValueError("an answer is not an error: `error` must be empty")
        if not answered and self.error is None:
            raise ValueError("a failure must say what failed: `error` is required")
        return self
