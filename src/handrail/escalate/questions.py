"""The multiple-choice card: every question the ladder may ever ask, written in advance.

A referee does not ask the crowd "what should happen now?". The referee asks
"was that a foul, yes or no?", with the options printed before the match.
The ladder's first rung works the same way. It never asks a model an open
question. It asks one of a handful of closed questions whose options are
things the capability already declares: its screens, its menu rows, its
effect classes. The answer is a probability per option, and ``none_of_these``
is always on the card so that "I do not know" is a legal answer.

Thresholds are per question and empirical. The defaults follow the design:
accept at top probability at or above 0.80 with a margin of at least 0.20
over the runner-up. Anything that touches a commit is not a question here at
all; that goes to a person.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

NONE = "none_of_these"


@dataclass(frozen=True)
class Question:
    """One closed question: a name, what is being asked, and the options with a hint each."""

    name: str
    prompt: str
    options: Mapping[str, str]  # option -> one line a person or a classifier can read
    accept_at: float = 0.80
    margin: float = 0.20

    def with_none(self) -> Question:
        if NONE in self.options:
            return self
        return Question(
            self.name,
            self.prompt,
            {**self.options, NONE: "none of the above"},
            self.accept_at,
            self.margin,
        )


@dataclass(frozen=True)
class Verdict:
    """What a classifier said, and whether the card's own threshold accepts it."""

    question: str
    probabilities: Mapping[str, float]
    chosen: str = field(init=False)
    confidence: float = field(init=False)
    margin: float = field(init=False)

    def __post_init__(self) -> None:
        ranked = sorted(self.probabilities.items(), key=lambda kv: kv[1], reverse=True)
        top, second = ranked[0], (ranked[1] if len(ranked) > 1 else (NONE, 0.0))
        object.__setattr__(self, "chosen", top[0])
        object.__setattr__(self, "confidence", top[1])
        object.__setattr__(self, "margin", top[1] - second[1])

    def accepted_by(self, question: Question) -> bool:
        return (
            self.chosen != NONE
            and self.confidence >= question.accept_at
            and self.margin >= question.margin
        )


def which_screen(labels: Mapping[str, str]) -> Question:
    """Which declared screen is showing? Options are the step's expected screens."""
    return Question(
        "which_screen",
        "Which of these screens is the application showing right now?",
        dict(labels),
    ).with_none()


def which_control(rows: Sequence[tuple[int, str, str, str]], wanted: str) -> Question:
    """Which menu row is the control the step wants? Options are the rows, by index."""
    options = {str(i): f"{verb} {role} {name!r}" for i, verb, role, name in rows}
    return Question(
        "which_control",
        f"Which row of the menu is: {wanted}?",
        options,
    ).with_none()


def is_this_a_commit() -> Question:
    """Does this action look like it cannot be freely undone? Never decisive on its own."""
    return Question(
        "is_this_a_commit",
        "Does pressing this control change something outside the form, not freely undoable?",
        {
            "commit": "posts, submits, transfers, deletes, or confirms",
            "not_commit": "navigates, searches, or stages a draft",
        },
    )


def is_it_done(outcome: str) -> Question:
    """Did the task's declared outcome happen, judging by the screen? A tie-breaker, not a probe."""
    return Question(
        "is_it_done",
        f"Does the screen say that this happened: {outcome}?",
        {"yes": "the screen confirms it", "no": "the screen denies it or says nothing"},
    ).with_none()


def is_this_a_dialog() -> Question:
    """Is the application showing a notice that must be acknowledged before anything else?"""
    return Question(
        "is_this_a_dialog",
        "Is this a notice, warning or dialog that must be acknowledged before continuing?",
        {"dialog": "a notice to acknowledge", "not_dialog": "an ordinary screen"},
    )


def session_expired() -> Question:
    """Has the application signed the operator out?"""
    return Question(
        "session_expired",
        "Is the application asking the operator to sign on again?",
        {"expired": "sign-on is required again", "signed_on": "still signed on"},
    )
