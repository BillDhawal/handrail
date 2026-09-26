import pytest

from targetapp.data import Store


@pytest.fixture
def store():
    s = Store()
    s.reset()
    return s


def test_authenticate_accepts_seeded_operator(store):
    op = store.authenticate("mrivas", "plumbline-demo")
    assert op is not None
    assert op.role == "TELLER"


def test_authenticate_rejects_wrong_password(store):
    assert store.authenticate("mrivas", "wrong") is None


def test_find_member_by_number(store):
    found = store.find_members("MBRNO", "400118")
    assert [m.member_number for m in found] == ["400118"]
    assert found[0].display_name == "Alvarez, Marisol"


def test_find_member_by_last_name_is_case_insensitive(store):
    found = store.find_members("LASTNM", "okonkwo")
    assert [m.member_number for m in found] == ["400226"]


def test_unknown_member_returns_empty(store):
    assert store.find_members("MBRNO", "400999") == []


def test_balance_display_formats_cents_as_currency(store):
    share = store.get_share("400118-S0001")
    assert share.balance_display == "$42,100.50"


def test_teller_cannot_place_hold(store):
    teller = store.authenticate("mrivas", "plumbline-demo")
    outcome, detail = store.place_hold("400118-S0001", "LEGAL", "", teller)
    assert outcome == "not_authorized"
    assert detail == ""
    assert store.get_share("400118-S0001").status == "ACTIVE"


def test_supervisor_places_hold_and_gets_confirmation(store):
    sup = store.authenticate("dcolewell", "plumbline-demo")
    outcome, code = store.place_hold("400118-S0001", "LEGAL", "court order", sup)
    assert outcome == "posted"
    assert code.startswith("HX-")
    assert len(code) == len("HX-") + 6
    assert store.get_share("400118-S0001").status == "HOLD"


def test_share_already_on_hold_is_a_business_outcome(store):
    sup = store.authenticate("dcolewell", "plumbline-demo")
    outcome, detail = store.place_hold("400226-S0002", "LEGAL", "", sup)
    assert outcome == "already_held"
    assert detail == ""


def test_teller_gets_not_authorized_even_when_share_already_held(store):
    """Pins the check ORDER, not just the outcomes.

    Role is checked before state deliberately: a teller must be refused for
    authorization, not told the share is already held. If those two checks were
    reversed, every other test in this file would still pass.
    """
    teller = store.authenticate("mrivas", "plumbline-demo")
    outcome, detail = store.place_hold("400226-S0002", "LEGAL", "", teller)
    assert outcome == "not_authorized"
    assert detail == ""


def test_reset_restores_seed_state(store):
    sup = store.authenticate("dcolewell", "plumbline-demo")
    store.place_hold("400118-S0001", "LEGAL", "", sup)
    assert store.get_share("400118-S0001").status == "HOLD"
    store.reset()
    assert store.get_share("400118-S0001").status == "ACTIVE"
