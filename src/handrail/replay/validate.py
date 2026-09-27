"""The bouncer at the door: inputs are checked before anything touches a screen.

A capability declares the inputs it accepts, the way a form declares its
fields. This module compares what the caller supplied against that
declaration and refuses anything that does not fit - a member number with five
digits, a reason code that is not on the list, a field the capability never
heard of. It runs before the surface is opened, so a bad call changes nothing
in the application and costs nothing.

The strictness is the point. A replay that quietly typed "40011" into a bank
would report the resulting "no such member" screen as the answer, and the
caller would never learn that its own input was wrong.
"""

from __future__ import annotations

import re
from typing import Any

from ..schema.capability import Capability, InputSpec
from ..schema.errors import ErrorCode, HandrailError

TRUE_WORDS = frozenset({"1", "true", "yes", "y", "on"})
FALSE_WORDS = frozenset({"0", "false", "no", "n", "off"})


def validate_inputs(capability: Capability, supplied: dict[str, Any]) -> dict[str, Any]:
    """Return the checked, typed inputs, or raise INVALID_INPUT naming the problem."""
    declared = {spec.name: spec for spec in capability.inputs}

    unknown = sorted(set(supplied) - set(declared))
    if unknown:
        raise HandrailError(
            f"inputs not declared by this capability: {unknown}", ErrorCode.INVALID_INPUT
        )

    checked: dict[str, Any] = {}
    for name, spec in declared.items():
        if name not in supplied or supplied[name] is None:
            if spec.required:
                raise HandrailError(f"required input missing: {name}", ErrorCode.INVALID_INPUT)
            continue
        checked[name] = _coerce(spec, supplied[name])
    return checked


def _coerce(spec: InputSpec, raw: Any) -> Any:
    if spec.type == "number":
        # bool is a subclass of int, so float(True) == 1.0 would let a JSON `true`
        # slip into a numeric field. Refuse it before float() ever sees it.
        if isinstance(raw, bool):
            raise HandrailError(f"{spec.name} is a boolean, not a number", ErrorCode.INVALID_INPUT)
        try:
            return float(raw)
        except (TypeError, ValueError) as exc:
            raise HandrailError(
                f"{spec.name} is not a number: {raw!r}", ErrorCode.INVALID_INPUT
            ) from exc

    if spec.type == "boolean":
        if isinstance(raw, bool):
            return raw
        word = str(raw).strip().lower()
        if word in TRUE_WORDS:
            return True
        if word in FALSE_WORDS:
            return False
        # A typo that quietly became False would steer a branch with no error surfaced.
        raise HandrailError(f"{spec.name} is not a boolean: {raw!r}", ErrorCode.INVALID_INPUT)

    text = str(raw)
    if spec.type == "enum":
        if spec.enum is None or text not in spec.enum:
            raise HandrailError(
                f"{spec.name} must be one of {spec.enum}, not {text!r}", ErrorCode.INVALID_INPUT
            )
        return text

    if spec.pattern is not None and re.fullmatch(spec.pattern, text) is None:
        raise HandrailError(
            f"{spec.name} does not match {spec.pattern!r}: {text!r}", ErrorCode.INVALID_INPUT
        )
    return text
