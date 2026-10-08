"""The menu: what a diner may order, written from what is in the kitchen tonight.

A restaurant does not hand you the kitchen. It hands you a menu, and the menu
only lists dishes that can actually be made right now. Out of sea bass? Not on
the menu. Soup is never listed under "grilled". You order by number, and the
worst a confused diner can do is pick a real dish they did not mean.

This module writes that menu for a browser page. The waiter (``surface.py``)
walks the page and hands over one ``Control`` per element it found: its role,
its accessible name, and a few facts such as whether it is disabled. From that
list this module builds the numbered operations table: one row per legal verb
on each present, enabled control. A disabled button is not on it. A checkbox is
never offered as a place to type. A read-only field can be read and nothing
else.

Two things the prototype learned live here. First, the closed table of which
verbs a role supports is the browser's whole vocabulary; the compiler copies a
row's ``supports`` straight into the target it writes, so authoring and replay
agree on what a control can do. Second, legacy pages rarely label their fields
(PLUMBLINE never does), so a control with no accessible name is named from the
caption beside it, then from its HTML ``name`` attribute, and only then left
blank. It is still on the menu: a blank name hides nothing from the diner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...schema.target import Verb
from ..base import Operation


@dataclass(frozen=True)
class Control:
    """One element as the waiter saw it. Surface-specific facts stop here."""

    role: str
    #: The accessible name, computed the way a screen reader would.
    name: str = ""
    #: The caption beside a field that has no accessible name (the cell to its left).
    label: str = ""
    #: The HTML ``name`` attribute: the last resort for naming, the first for finding.
    attr_name: str = ""
    #: A test id the page's authors put there on purpose. Rare on legacy pages; gold when present.
    test_id: str = ""
    #: Frame names on the way down, outermost first.
    scope: tuple[str, ...] = ()
    #: Roles from the frame root to the parent, for the fingerprint later.
    ancestors: tuple[str, ...] = ()
    #: The first cell of the table row this control sits in, if any: "the Hold link in row X".
    row: str = ""
    disabled: bool = False
    readonly: bool = False
    visible: bool = True
    handle: Any = None


#: role -> verb -> the argument types that verb takes. The browser's whole vocabulary.
#: Order within a role is the order rows appear in the table.
SUPPORTS: dict[str, dict[Verb, list[str]]] = {
    "button": {"invoke": []},
    "link": {"invoke": []},
    "menuitem": {"invoke": []},
    "tab": {"invoke": []},
    "textbox": {"set_value": ["string"], "read": []},
    "searchbox": {"set_value": ["string"], "read": []},
    "spinbutton": {"set_value": ["string"], "read": []},
    "combobox": {"select": ["string"], "read": []},
    "listbox": {"select": ["string"], "read": []},
    "checkbox": {"toggle": [], "read": []},
    "radio": {"toggle": [], "read": []},
    "switch": {"toggle": [], "read": []},
    "status": {"read": []},
    "alert": {"read": []},
    "heading": {"read": []},
    "cell": {"read": []},
}


def display_name(control: Control) -> str:
    """What the menu calls this control: name, then caption, then attribute, then nothing."""
    return control.name or control.label or control.attr_name


def supports_for(control: Control) -> dict[Verb, list[str]]:
    """The verbs this control takes right now. Empty means it is not on the menu."""
    if control.disabled or not control.visible:
        return {}
    verbs = SUPPORTS.get(control.role)
    if verbs is None:
        return {}
    if control.readonly:
        return {v: a for v, a in verbs.items() if v == "read"}
    return dict(verbs)


def build_table(controls: list[Control] | tuple[Control, ...]) -> tuple[Operation, ...]:
    """Number the legal operations, in page order, starting at one."""
    rows: list[Operation] = []
    for control in controls:
        for verb in supports_for(control):
            rows.append(
                Operation(
                    index=len(rows) + 1,
                    verb=verb,
                    role=control.role,
                    name=display_name(control),
                    handle=control.handle,
                )
            )
    return tuple(rows)


def render(operations: tuple[Operation, ...]) -> str:
    """The menu as a model will read it: one numbered line per row."""
    return "\n".join(f"{op.index}: {op.verb} {op.role} {op.name!r}" for op in operations)
