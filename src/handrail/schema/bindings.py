"""The binding grammar: the only way a run-time value reaches a recorded step.

Two forms and nothing else: ``{{input.name}}`` and ``{{env.NAME}}``. There is no
expression language, no nesting, no defaults. Substitution is a single pass, so a
value that itself looks like a binding is typed literally and never expanded.

A brace pair the grammar does not claim is *residue*. Residue in an artifact is
refused when the artifact is built, because the alternative is typing the literal
text ``{{oops}}`` into a live application.

Bindings may appear in three places: the entry, a step's value, and the text
of a target (its name, the names of its scope, a rung's value). The third is
what lets one capability say "the Hold link in the row for *this* share". A
bound target is still data a person reviewed; only the blank is filled in.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from .target import Target

BINDING_RE = re.compile(r"\{\{\s*(input|env)\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_ANY_BRACES_RE = re.compile(r"\{\{.*?\}\}")


class BindingError(ValueError):
    """A binding names something that was not supplied."""


def find_bindings(text: str) -> list[tuple[str, str]]:
    """Every ``(source, name)`` pair the text refers to, in order."""
    return [(m.group(1), m.group(2)) for m in BINDING_RE.finditer(text)]


def residue(text: str) -> list[str]:
    """Brace pairs that look like bindings but are not in the grammar."""
    return [
        m.group(0) for m in _ANY_BRACES_RE.finditer(text) if not BINDING_RE.fullmatch(m.group(0))
    ]


def bind_text(text: str, inputs: Mapping[str, object], env: Mapping[str, str]) -> str:
    """Substitute every binding once. Missing values raise; nothing is guessed."""

    def replace(match: re.Match[str]) -> str:
        source, name = match.group(1), match.group(2)
        table: Mapping[str, object] = inputs if source == "input" else env
        if name not in table:
            raise BindingError(f"{source}.{name} was not supplied")
        return str(table[name])

    return BINDING_RE.sub(replace, text)


def target_texts(target: Target) -> list[str]:
    """Every string in a target that may carry a binding."""
    texts = [s.name for s in target.scope if s.name] + [r.value for r in target.ladder if r.value]
    if target.name:
        texts += [t for t in (target.name.eq, target.name.matches) if t]
    return texts


def bind_target(target: Target, inputs: Mapping[str, object], env: Mapping[str, str]) -> Target:
    """A copy of the target with every blank filled in. The original is never changed."""

    def fill(text: str | None) -> str | None:
        return bind_text(text, inputs, env) if text else text

    spec = target.model_dump()
    for scope in spec["scope"]:
        scope["name"] = fill(scope["name"])
    for rung in spec["ladder"]:
        rung["value"] = fill(rung["value"])
    if spec["name"]:
        spec["name"] = {k: fill(v) for k, v in spec["name"].items()}
    return Target.model_validate(spec)
