"""Same furniture, same room. One extra chair is still the room. Rows of desks is not."""

from handrail.kernel.signature import THRESHOLD, Match, jaccard, match, take

ROOM = ["work:div.hdr", "work:form", "work:form/table.box", "work:form/table.box/tr/td/input[opid]"]


def test_the_signature_is_order_free_and_duplicates_are_one_path():
    assert take(ROOM) == take(reversed(ROOM)) == take(ROOM + ROOM)
    assert take(ROOM).value.startswith("sha256:")


def test_a_surface_that_already_took_the_signature_passes_it_through():
    assert take(["sig:inquiry"]).value == "sig:inquiry"
    assert take(["sha256:abcdef0123456789"]).value == "sha256:abcdef0123456789"
    assert take(["sig:a", "sig:b"]).value.startswith("sha256:")  # two paths are a set, not a value


def test_jaccard_is_overlap_over_union():
    assert jaccard(["a", "b"], ["b", "c"]) == 1 / 3
    assert jaccard([], []) == 1.0


def screens(**paths: list[str]):
    return {label: (take(p).value, p) for label, p in paths.items()}


def test_exact_wins_and_scores_one():
    assert match(ROOM, screens(signon=ROOM)) == Match("signon", "exact", 1.0)


def test_one_extra_chair_is_still_the_room():
    seven = [f"p{i}" for i in range(7)]
    assert match(seven + ["banner"], screens(desk=seven)) == Match("desk", "similar", 7 / 8)
    assert 7 / 8 >= THRESHOLD


def test_rows_of_desks_is_not_the_room():
    seven = [f"p{i}" for i in range(7)]
    m = match(["p0", "p1", "x", "y", "z", "w"], screens(desk=seven))
    assert m.label is None and m.tier == "none" and m.score < THRESHOLD


def test_a_screen_without_stored_paths_matches_exactly_or_not_at_all():
    stored = {"legacy": ("sha256:0000000000000000", [])}
    assert match(ROOM, stored).tier == "none"
    assert match(["sha256:0000000000000000"], stored).tier == "exact"


def test_the_closest_room_is_named_when_several_are_similar():
    base = [f"p{i}" for i in range(10)]
    m = match(base, screens(a=base + ["one_chair"], b=base[:8] + ["q", "r"]))  # 10/11 vs 8/12
    assert (m.label, m.tier) == ("a", "similar")
