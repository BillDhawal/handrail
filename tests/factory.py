"""A small, valid capability as a plain dict, so a test can break exactly one thing."""

from __future__ import annotations

import copy
from typing import Any

from handrail.schema.target import RUNG_COST


def _target(role: str, name: str, verb: str, args: list[str] | None = None) -> dict[str, Any]:
    return {
        "role": role,
        "name": {"eq": name},
        "supports": {verb: args or []},
        "scope": [{"role": "frame", "name": "work"}],
        "ladder": [{"rung": "role_name", "cost": RUNG_COST["role_name"]}],
    }


_PLACE_HOLD: dict[str, Any] = {
    "id": "bank.place_hold",
    "version": "1.0.0",
    "title": "Place a hold on a member's share",
    "surface": {"kind": "browser", "entry": "{{env.BASE_URL}}/inquiry"},
    "inputs": [
        {"name": "member_number", "pattern": "^[0-9]{6}$"},
        {"name": "reason", "type": "enum", "enum": ["LEGAL", "FRAUD_REVIEW"]},
    ],
    "outputs": [
        {
            "name": "confirmation",
            "source": {"step": "read_result", "extract": r"CONFIRMATION\s+(\S+)"},
            "produced_on": ["posted"],
        }
    ],
    "screens": {
        "inquiry": {"signature": "sig:inquiry", "label": "the member inquiry screen"},
        "hold_form": {"signature": "sig:hold_form", "label": "the new hold form"},
        "posted": {"signature": "sig:posted", "label": "the hold was posted"},
        "already_held": {"signature": "sig:held", "label": "the share is already on hold"},
    },
    "targets": {
        "member_field": _target("textbox", "Member number", "set_value", ["string"]),
        "open_hold": _target("link", "Hold", "invoke"),
        "reason_list": _target("combobox", "Reason", "select", ["string"]),
        "post_button": _target("button", "F10=Post Hold", "invoke"),
        "result_line": _target("status", "Result", "read"),
    },
    "steps": [
        {
            "id": "enter_member",
            "intent": "Type the member number",
            "screen": "inquiry",
            "op": {"verb": "set_value", "value": "{{input.member_number}}"},
            "target": "member_field",
            "effect": {"kind": "stage"},
            "settle": {"kind": "target_present", "step": "open_hold"},
        },
        {
            "id": "open_hold",
            "intent": "Open the hold form for this share",
            "screen": "inquiry",
            "op": {"verb": "invoke"},
            "target": "open_hold",
            "effect": {"kind": "navigate"},
            "settle": {"kind": "screen_is", "screen": "hold_form"},
        },
        {
            "id": "choose_reason",
            "intent": "Choose the reason code",
            "screen": "hold_form",
            "op": {"verb": "select", "value": "{{input.reason}}"},
            "target": "reason_list",
            "effect": {"kind": "stage"},
            "settle": {"kind": "target_present", "step": "post_hold"},
        },
        {
            "id": "post_hold",
            "intent": "Post the hold",
            "screen": "hold_form",
            "op": {"verb": "invoke"},
            "target": "post_button",
            "effect": {"kind": "commit", "proposed_by": "model", "probe": "hold_exists"},
            "settle": {"kind": "target_present", "step": "read_result"},
            "expect": {"screen_in": ["posted", "already_held"]},
        },
        {
            "id": "read_result",
            "intent": "Read the confirmation line",
            "screen": "posted",
            "op": {"verb": "read"},
            "target": "result_line",
            "effect": {"kind": "read"},
            "settle": {"kind": "screen_is", "screen": "posted"},
        },
    ],
    "outcomes": {
        "posted": {"category": "SUCCESS"},
        "already_held": {"category": "BUSINESS_OUTCOME", "code": "ALREADY_PROCESSED"},
    },
    "safety": {"allowed_hosts": ["127.0.0.1:8081"]},
}


def place_hold() -> dict[str, Any]:
    """A fresh deep copy every call, so tests cannot leak edits into each other."""
    return copy.deepcopy(_PLACE_HOLD)


def step(cap: dict[str, Any], step_id: str) -> dict[str, Any]:
    return next(s for s in cap["steps"] if s["id"] == step_id)
