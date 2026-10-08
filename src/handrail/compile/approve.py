"""The signature on the menu: a named person says this dish may be sold.

Three plates came out clean; the card says ``verified``. That is the
kitchen's word. Putting the dish on the menu is the owner's word, and the
owner signs with a name. Nothing in the repository can forge that name:
this function writes it, and only when the card is already verified and
every commit on it was confirmed by a person at authoring time.

From ``approved`` a card can be served to callers (``serve/mcp.py``). From
anything else it cannot. ``deprecated`` is the only way back off the menu.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..schema.capability import Capability


class NotApprovable(ValueError):
    """The card is not in a state a signature can be put on."""


def approve(capability: Capability, by: str, when: str | None = None) -> Capability:
    """A verified card, signed by a named person. Refuses a draft, however good it looks."""
    by = by.strip()
    if not by:
        raise NotApprovable("approval needs a name")
    state = capability.lifecycle.state
    if state == "approved":
        raise NotApprovable(f"already approved by {capability.lifecycle.approved_by}")
    if state != "verified":
        raise NotApprovable(f"a {state} card cannot be approved; verify it first")
    spec = capability.model_dump()
    spec["lifecycle"] = {
        **spec["lifecycle"],
        "state": "approved",
        "approved_by": by,
        "approved_at": when or datetime.now(UTC).isoformat(timespec="seconds"),
    }
    return Capability.model_validate(spec)


def deprecate(capability: Capability, by: str, why: str) -> Capability:
    """Off the menu. Kept, never served, and the reason travels with it."""
    spec = capability.model_dump()
    spec["lifecycle"] = {
        **spec["lifecycle"],
        "state": "deprecated",
        "deprecated_by": by,
        "note": why,
    }
    return Capability.model_validate(spec)
