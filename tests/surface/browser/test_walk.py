"""The walk's notebook is plain data, and the signature cares about structure only."""

from handrail.surface.browser.walk import Handle, control_from, signature_of


def raw(**over):
    base = {
        "role": "textbox", "name": "", "label": "Operator ID", "attr_name": "opid",
        "test_id": "", "ancestors": ["form", "table", "row", "cell"], "disabled": False,
        "readonly": False, "visible": True, "selector": "body > form > input:nth-child(1)",
    }  # fmt: skip
    return {**base, **over}


def test_a_record_becomes_a_control_with_its_frame_as_scope():
    c = control_from("work", raw())
    assert (c.role, c.label, c.attr_name, c.scope) == ("textbox", "Operator ID", "opid", ("work",))
    assert c.ancestors == ("form", "table", "row", "cell")
    assert c.handle == Handle("work", "body > form > input:nth-child(1)")


def test_the_top_frame_has_no_scope():
    assert control_from("", raw()).scope == ()


def test_the_signature_does_not_care_about_order():
    a = signature_of([("work", ["div.hdr", "form/table.box"]), ("menu", ["table.grid/tr/td/a"])])
    b = signature_of([("menu", ["table.grid/tr/td/a"]), ("work", ["form/table.box", "div.hdr"])])
    assert a == b and a.startswith("sha256:")


def test_one_different_class_is_a_different_screen():
    posted = signature_of([("work", ["div.hdr"])])
    already_held = signature_of([("work", ["div.hdr", "div.msg"])])
    assert posted != already_held


def test_the_same_path_in_five_rows_is_one_path():
    # "keep the chrome, ignore the rows": the walk already de-duplicates, and so does this.
    one = signature_of([("work", ["table.grid/tr/td/a"])])
    five = signature_of([("work", ["table.grid/tr/td/a"] * 5)])
    assert one == five
