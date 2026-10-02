"""The menu lists only dishes the kitchen can make tonight, numbered from one."""

from handrail.surface.browser.operations import (
    SUPPORTS,
    Control,
    build_table,
    display_name,
    render,
    supports_for,
)


def rows(*controls: Control) -> list[tuple[int, str, str, str]]:
    return [(op.index, op.verb, op.role, op.name) for op in build_table(controls)]


def test_a_disabled_button_is_not_on_the_menu():
    assert rows(Control("button", "F10=Post Hold", disabled=True)) == []


def test_a_hidden_control_is_not_on_the_menu():
    assert rows(Control("textbox", "Notes", visible=False)) == []


def test_a_checkbox_is_never_offered_as_a_place_to_type():
    verbs = [op.verb for op in build_table((Control("checkbox", "Urgent"),))]
    assert "set_value" not in verbs
    assert verbs == ["toggle", "read"]


def test_a_read_only_field_can_be_read_and_nothing_else():
    assert supports_for(Control("textbox", "Balance", readonly=True)) == {"read": []}


def test_a_role_outside_the_vocabulary_gets_no_rows():
    assert rows(Control("img", "logo"), Control("generic", "")) == []


def test_indexes_start_at_one_and_stay_dense_in_page_order():
    table = rows(
        Control("textbox", "Operator ID"),
        Control("button", "Ghost", disabled=True),
        Control("button", "F5=Sign On"),
    )
    assert table == [
        (1, "set_value", "textbox", "Operator ID"),
        (2, "read", "textbox", "Operator ID"),
        (3, "invoke", "button", "F5=Sign On"),
    ]


def test_an_unlabelled_field_is_named_from_its_caption_then_its_name_attribute():
    beside_a_caption = Control("textbox", name="", label="Operator ID", attr_name="opid")
    bare = Control("textbox", name="", label="", attr_name="opid")
    nameless = Control("textbox")
    assert display_name(beside_a_caption) == "Operator ID"
    assert display_name(bare) == "opid"
    assert display_name(nameless) == ""


def test_a_nameless_control_is_still_on_the_menu():
    assert rows(Control("textbox")) == [(1, "set_value", "textbox", ""), (2, "read", "textbox", "")]


def test_the_row_carries_the_controls_handle_untouched():
    handle = object()
    (op,) = build_table((Control("link", "Hold", handle=handle),))
    assert op.handle is handle


def test_supports_is_what_the_compiler_will_write_into_the_target():
    assert supports_for(Control("combobox", "Reason")) == {"select": ["string"], "read": []}


def test_the_vocabulary_only_uses_verbs_that_take_a_target():
    from handrail.schema.target import TARGETED_VERBS

    for role, verbs in SUPPORTS.items():
        assert set(verbs) <= TARGETED_VERBS, role


def test_render_is_one_numbered_line_per_row():
    text = render(build_table((Control("button", "F5=Sign On"),)))
    assert text == "1: invoke button 'F5=Sign On'"
