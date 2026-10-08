"""The recipe writer: turns one evening's order book into a card a line cook can follow.

The chef cooked the dish once and the maître d' wrote every order in the
book. The book is not a recipe. It says "number 7, then number 3"; a recipe
says "the Search button on the inquiry screen, then the member's link". The
recipe writer reads the book, names every screen and every control, and
writes the card. If the book has a hole in it, the writer refuses to guess
and says exactly which line is the problem.

Refusals, each a sentence the engine relies on:

- A step acted on a screen nobody labelled. The engine needs a screen name
  as the precondition of every step.
- A step landed on a screen nobody labelled. The engine needs to know what
  "done" looks like for every step.
- A control that no rung could find again. The engine could never replay it.
- A value typed as a literal that belongs to an input. It should have been a
  blank, and a card with a customer's number on it is not a card.
- A run that never called ``finish``. There is no outcome to end on.

Two things it does on purpose. Literal input values found in a target's name
or row become blanks, so "the link named 400118" becomes "the link named
{{input.member_number}}": that is how one evening becomes a card for every
member. And the card is written in ``draft``: a commit the owner confirmed
during authoring keeps that person's name, but leaving draft is the verify
gate's decision, not this file's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..schema.capability import Capability
from ..schema.trace import Turn
from ..surface.browser.fingerprint import fields_for, fingerprint_over
from ..surface.browser.operations import SUPPORTS, Control


class CompileError(ValueError):
    """The book has a hole in it. `reasons` names every line."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass
class Source:
    """What the recipe writer is given besides the book."""

    id: str
    title: str
    entry: str  # may hold {{env.X}}
    inputs: list[dict[str, Any]]  # InputSpec dicts, as the capability will declare them
    values: dict[str, Any]  # the values used during authoring, for finding literals
    screens: dict[str, str]  # label -> signature, as asserted
    trace: list[Turn]
    paths: dict[str, tuple[str, ...]] = field(default_factory=dict)  # label -> its paths
    allowed_hosts: list[str] = field(default_factory=list)
    version: str = "0.1.0"
    surface_kind: str = "browser"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "x"


class _Writer:
    def __init__(self, source: Source) -> None:
        self.src = source
        self.reasons: list[str] = []
        self.by_signature = {sig: label for label, sig in source.screens.items()}
        self.secret_values = {
            str(source.values[i["name"]])
            for i in source.inputs
            if i.get("sensitivity") == "secret" and i["name"] in source.values
        }
        self.literal_blanks = {
            str(v): f"{{{{input.{k}}}}}" for k, v in source.values.items() if str(v)
        }
        self.targets: dict[str, dict[str, Any]] = {}
        self.steps: list[dict[str, Any]] = []
        self.outputs: list[dict[str, Any]] = []
        self.outcome: str | None = None

    # -- helpers ------------------------------------------------------------------

    def unliteral(self, text: str) -> str:
        """An input value standing alone in a name becomes its blank."""
        return self.literal_blanks.get(text, text)

    def target_for(self, turn: Turn) -> str | None:
        if not turn.rungs:
            what = f"{turn.role} {turn.name!r}"
            self.reasons.append(f"turn {turn.seq}: no rung can find {what} again")
            return None
        handle = turn.handle  # a Handle in memory, a dict once it has been through the book
        frame = handle.get("frame") if isinstance(handle, dict) else getattr(handle, "frame", None)
        scope: list[dict[str, Any]] = []
        if frame:
            scope.append({"role": "frame", "name": frame})
        if turn.row:
            scope.append({"role": "row", "name": self.unliteral(turn.row)})
        name = self.unliteral(turn.name or "")
        key = _slug(f"{turn.role}_{name}_{'_'.join(s['name'] for s in scope)}")
        if key not in self.targets:
            spec: dict[str, Any] = {
                "role": turn.role,
                "name": {"eq": name} if name else None,
                "supports": dict(SUPPORTS.get(turn.role or "", {})),
                "scope": scope,
                "ladder": sorted(
                    (r.model_dump(exclude_none=True) for r in turn.rungs), key=lambda r: r["cost"]
                ),
                "fingerprint": self.fingerprint_for(turn, blank=name != (turn.name or "")),
            }
            if not spec["supports"]:
                spec["supports"] = {turn.verb: ["string"] if turn.value else []}
            self.targets[key] = {k: v for k, v in spec.items() if v is not None}
        return key

    def fingerprint_for(self, turn: Turn, blank: bool) -> dict[str, Any] | None:
        """The guard's fingerprint, retaken without `name` when the name became a blank.

        A link named 400118 is the same control as a link named 400337; what makes it
        the same is its role, its verbs and the containers it sits in.
        """
        if turn.fingerprint is None:
            return None
        control = Control(turn.role or "", turn.name or "", ancestors=turn.ancestors)
        over = [f for f in fields_for(control) if not (blank and f == "name")]
        return fingerprint_over(control, over).model_dump()

    def check_value(self, turn: Turn) -> None:
        if not turn.value:
            return
        if turn.value in self.literal_blanks:
            self.reasons.append(
                f"turn {turn.seq}: typed the value of an input as a literal; use a blank"
            )
        for secret in self.secret_values:
            if secret in turn.value:
                self.reasons.append(f"turn {turn.seq}: a secret appears in the typed value")

    # -- the walk through the book ------------------------------------------------

    def write(self) -> dict[str, Any]:
        acts = [t for t in self.src.trace if t.tool == "act"]
        if not any(t.tool == "finish" for t in self.src.trace):
            self.reasons.append("the run never called finish, so there is no outcome")
        for position, turn in enumerate(acts):
            screen = self.by_signature.get(turn.signature_before)
            after = self.by_signature.get(turn.signature_after)
            if screen is None:
                self.reasons.append(f"turn {turn.seq}: acted on a screen nobody labelled")
            if after is None:
                self.reasons.append(f"turn {turn.seq}: landed on a screen nobody labelled")
            self.check_value(turn)
            key = self.target_for(turn)
            if screen is None or after is None or key is None:
                continue
            nxt = acts[position + 1] if position + 1 < len(acts) else None
            step_id = f"s{position + 1:02d}_{turn.verb}_{_slug(turn.name or turn.role or '')}"
            settle: dict[str, Any]
            if after != screen:
                settle = {"kind": "screen_is", "screen": after}
            elif nxt is not None:
                settle = {"kind": "target_present", "step": "__next__"}
            else:
                settle = {"kind": "screen_is", "screen": screen}
            step: dict[str, Any] = {
                "id": step_id,
                "intent": f"{turn.verb} {turn.name or turn.role}",
                "screen": screen,
                "op": {"verb": turn.verb, **({"value": turn.value} if turn.value else {})},
                "target": key,
                "effect": {
                    "kind": turn.effect or "stage",
                    **({"confirmed_by": turn.confirmed_by} if turn.confirmed_by else {}),
                    **({"proposed_by": "model"} if turn.effect else {}),
                },
                "settle": settle,
            }
            if after != screen or turn.effect == "commit":
                step["expect"] = {"screen_in": [after]}
            self.steps.append(step)
            if turn.verb == "read" and set(SUPPORTS.get(turn.role or "", {})) == {"read"}:
                # Only a read-only control is an output. Reading back a field you typed into
                # is the model checking its work, and a card never outputs a password.
                self.outputs.append(
                    {"name": _slug(turn.name or step_id), "source": {"step": step_id}}
                )
        for i, step in enumerate(self.steps):
            if step["settle"].get("step") == "__next__":
                step["settle"]["step"] = self.steps[i + 1]["id"]
        finish = next((t for t in self.src.trace if t.tool == "finish"), None)
        self.outcome = finish.label if finish else None
        return self.capability()

    def capability(self) -> dict[str, Any]:
        src = self.src
        return {
            "id": src.id,
            "version": src.version,
            "title": src.title,
            "surface": {"kind": src.surface_kind, "entry": src.entry},
            "inputs": src.inputs,
            "outputs": [
                {**o, "produced_on": [self.outcome]} if self.outcome else o for o in self.outputs
            ],
            "screens": {
                label: {
                    "signature": sig,
                    "label": label.replace("_", " "),
                    "paths": list(src.paths.get(label, ())),
                }
                for label, sig in src.screens.items()
            },
            "targets": self.targets,
            "steps": self.steps,
            "outcomes": {self.outcome: {"category": "SUCCESS"}} if self.outcome else {},
            "safety": {
                "allowed_hosts": src.allowed_hosts,
                "allowed_verbs": sorted({s["op"]["verb"] for s in self.steps}),
            },
        }


def compile_trace(source: Source) -> Capability:
    """The book into a card, or a refusal that names every hole."""
    writer = _Writer(source)
    spec = writer.write()
    if writer.reasons:
        raise CompileError(writer.reasons)
    try:
        return Capability.model_validate(spec)
    except ValueError as exc:
        raise CompileError([str(exc)]) from exc
