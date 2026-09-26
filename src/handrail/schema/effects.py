"""What a step does to the world, declared rather than inferred.

The prototype guessed risk from keywords in a step's intent, and the guess was
wrong in both directions: "submit the sign-on form" counted as dangerous, while
"freeze the account" would not have. Here every step carries an effect class.
A model may *propose* one while authoring; a named person confirms every commit
before the capability may leave draft; replay only ever reads the field.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class EffectClass(StrEnum):
    READ = "read"  # nothing changes
    NAVIGATE = "navigate"  # only the view changes
    STAGE = "stage"  # a reversible draft: a half-filled form, a selected row
    COMMIT = "commit"  # externally visible and not freely reversible


#: Effects the journal must record before the step is attempted.
MUTATING: frozenset[EffectClass] = frozenset({EffectClass.STAGE, EffectClass.COMMIT})


class Effect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EffectClass
    proposed_by: str | None = None  # "model", or a person
    confirmed_by: str | None = None  # a named person; required for a commit to leave draft
    confirmed_at: str | None = None
    #: Name of a read-only check answering "did this already happen?".
    probe: str | None = None

    @property
    def is_mutating(self) -> bool:
        return self.kind in MUTATING

    @property
    def is_retryable(self) -> bool:
        """A commit may be retried only if something can tell whether it landed."""
        return self.kind is not EffectClass.COMMIT or self.probe is not None
