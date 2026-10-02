"""Checking the face, not just the name on the door.

A hotel key card opens room 214. That tells you the card found a door; it does
not tell you the room behind it is still the one you booked. If the hotel
renumbered the floor overnight, the card still opens "214", and you walk into
somebody else's room. A ladder rung is the key card: it answers "did something
match". The fingerprint is the look around the room: it answers "is this the
same thing".

The fingerprint is a hash over what a control *is*: its role, its name, the
verbs it takes, and the roles of the containers it sits in. It deliberately
ignores where the control is on the page, so adding a row above it changes
nothing, and it ignores whatever a user has typed into it.

The prototype got this wrong twice, live, and both corrections are here.

1. A submit button's ``value`` is its label. The first version threw away
   every ``value`` as "content a user typed", and every button in the bank
   hashed identically, so the check could never fail. Here the name of a
   control is part of its identity, and for a button the name *is* that label.
2. A ``read`` step's text is the thing being read. A confirmation line says
   HX-829120 today and HX-829121 tomorrow; fingerprinting that text reports
   drift on the one difference that is not drift. So a control that can only
   be read is fingerprinted without its name.

The stored fingerprint lists the fields it was taken over, and a later check
hashes exactly those fields. The artifact says what was compared; the code
never guesses.
"""

from __future__ import annotations

import hashlib
import json

from ...schema.target import Fingerprint
from .operations import Control, display_name, supports_for

#: Everything a fingerprint may be taken over, in the order they are listed in the artifact.
FIELDS: tuple[str, ...] = ("role", "name", "supports", "ancestor_roles")


def _value_of(field: str, control: Control) -> object:
    if field == "role":
        return control.role
    if field == "name":
        return display_name(control)
    if field == "supports":
        return sorted(supports_for(control))
    if field == "ancestor_roles":
        return list(control.ancestors)
    raise ValueError(f"a fingerprint cannot be taken over {field!r}")


def _hash(over: list[str], control: Control) -> str:
    facts = {field: _value_of(field, control) for field in over}
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def fields_for(control: Control) -> list[str]:
    """Which facts identify this control. A read-only control leaves its own text out."""
    read_only = set(supports_for(control)) == {"read"}
    return [f for f in FIELDS if not (read_only and f == "name")]


def fingerprint(control: Control) -> Fingerprint:
    """Take the fingerprint at authoring time, for the compiler to store."""
    over = fields_for(control)
    return Fingerprint(over=over, value=_hash(over, control))


def same_control(stored: Fingerprint, control: Control) -> bool:
    """At replay time: is the control the ladder found the one that was recorded?"""
    return _hash(stored.over, control) == stored.value
