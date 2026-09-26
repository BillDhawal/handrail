"""Invariant 1: the deterministic core cannot reach a model.

Asserted by reading the source, not by convention. The packages listed here are
the ones that run in production on the ordinary path, plus the compiler. If any
of them imports a model client, or imports the packages that are allowed to, this
fails - today, while there is almost nothing to check, and every day after.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "handrail"

CORE = ["schema", "replay", "surface", "kernel", "compile"]

FORBIDDEN_ROOTS = {
    "anthropic",
    "openai",
    "httpx",
    "requests",
    "typesafe",
    "laya",
    "langchain",
    "deepagents",
}
FORBIDDEN_INTERNAL = ("author", "escalate.backends")


def imports_of(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    return found


def test_the_schema_package_exists_so_this_guard_is_not_vacuous():
    assert list((SRC / "schema").glob("*.py"))


@pytest.mark.parametrize("package", CORE)
def test_the_core_never_imports_a_model_client(package: str):
    offenders: list[str] = []
    for path in (SRC / package).rglob("*.py"):
        for name in imports_of(path):
            bare = name.lstrip(".")
            if bare.split(".")[0] in FORBIDDEN_ROOTS:
                offenders.append(f"{path.relative_to(SRC)} imports {name}")
            if any(bare == inner or bare.startswith(inner + ".") for inner in FORBIDDEN_INTERNAL):
                offenders.append(f"{path.relative_to(SRC)} imports {name}")
    assert offenders == []
