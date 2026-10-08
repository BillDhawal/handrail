"""Before the first step and after the last: the order checked at the door, the receipt at the end.

Two small jobs the cook does not do at the stove. Before anything is touched,
the inputs are checked against the card, secrets are registered with the
recorder so they are masked from then on, and the entry is bound. After the
run has ended on an outcome, the values read along the way are turned into
the typed outputs the card promised, each with its extraction pattern.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from ..kernel.evidence import Recorder
from ..schema.bindings import BindingError, bind_text
from ..schema.capability import Capability
from ..schema.errors import ErrorCode, HandrailError
from .validate import validate_inputs


def prepare(
    capability: Capability, inputs: dict[str, Any], recorder: Recorder, env: Mapping[str, str]
) -> dict[str, Any]:
    """Typed inputs, or a typed refusal. Secrets are masked from this moment on."""
    params = validate_inputs(capability, inputs)
    for spec in capability.inputs:
        if spec.sensitivity == "secret" and spec.name in params:
            recorder.add_secret(str(params[spec.name]))
    try:
        entry = bind_text(capability.surface.entry, params, env)
    except BindingError as exc:
        raise HandrailError(str(exc), ErrorCode.INVALID_INPUT) from exc
    recorder.log("replay.start", capability=capability.ref, entry=entry, inputs=params)
    return params


def outputs(capability: Capability, outcome: str, read_values: dict[str, str]) -> dict[str, Any]:
    """What the card promised, from what the read steps saw, for this outcome."""
    out: dict[str, Any] = {}
    for spec in capability.outputs:
        if spec.produced_on and outcome not in spec.produced_on:
            continue
        raw = read_values.get(spec.source.step)
        if raw is None:
            continue
        if spec.source.extract:
            found = re.search(spec.source.extract, raw)
            out[spec.name] = found.group(1) if found else None
        else:
            out[spec.name] = raw
    return out
