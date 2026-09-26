"""The binding grammar: the only way a run-time value reaches a recorded step.

Two forms and nothing else: ``{{input.name}}`` and ``{{env.NAME}}``. There is no
expression language, no nesting, no defaults. Substitution is a single pass, so a
value that itself looks like a binding is typed literally and never expanded.

A brace pair the grammar does not claim is *residue*. Residue in an artifact is
refused when the artifact is built, because the alternative is typing the literal
text ``{{oops}}`` into a live application.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

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
