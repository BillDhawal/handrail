"""Invariant 7: the binding grammar is closed and single-pass."""

import pytest

from handrail.schema.bindings import BindingError, bind_text, find_bindings, residue


def test_only_input_and_env_are_bindings():
    text = "{{input.member}} at {{env.BASE_URL}} and {{ input.spaced }}"
    assert find_bindings(text) == [("input", "member"), ("env", "BASE_URL"), ("input", "spaced")]


def test_anything_else_in_braces_is_residue():
    assert residue("{{input.ok}} {{oops}} {{input.a + 1}} {{run.key}}") == [
        "{{oops}}",
        "{{input.a + 1}}",
        "{{run.key}}",
    ]
    assert residue("{{input.ok}} and {{env.OK}}") == []


def test_substitution_happens_once_so_a_value_is_never_re_expanded():
    out = bind_text("{{input.note}}", {"note": "{{env.SECRET}}"}, {"SECRET": "hunter2"})
    assert out == "{{env.SECRET}}"


def test_a_missing_value_raises_rather_than_typing_the_braces():
    with pytest.raises(BindingError, match="input.member"):
        bind_text("{{input.member}}", {}, {})


def test_non_string_inputs_are_rendered_as_text():
    assert bind_text("amount={{input.amount}}", {"amount": 125.5}, {}) == "amount=125.5"
