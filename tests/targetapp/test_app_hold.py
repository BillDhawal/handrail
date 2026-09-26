import pytest

from targetapp.app import STORE, create_app
from targetapp.data import (
    MSG_ALREADY_HELD,
    MSG_HOLD_POSTED,
    MSG_NOT_AUTHORIZED,
    MSG_RESTRICTED_BANNER,
)


def _client(operator: str):
    STORE.reset()
    app = create_app("quarrybrook")
    app.config["TESTING"] = True
    c = app.test_client()
    html = c.get("/signon").get_data(as_text=True)
    marker = 'name="_tk" value="'
    start = html.index(marker) + len(marker)
    tk = html[start : html.index('"', start)]
    c.post("/signon", data={"opid": operator, "pw": "plumbline-demo", "br": "QB-01", "_tk": tk})
    return c


@pytest.fixture
def teller():
    return _client("mrivas")


@pytest.fixture
def supervisor():
    return _client("dcolewell")


def test_hold_form_renders_reason_and_notes(teller):
    html = teller.get("/hold/new?share=400118-S0001").get_data(as_text=True)
    assert 'name="rsn"' in html
    assert 'name="nt"' in html
    assert "F8=Review" in html
    assert "400118-S0001" in html


def test_review_screen_shows_the_restricted_banner_to_a_teller(teller):
    html = teller.post(
        "/hold/review", data={"share": "400118-S0001", "rsn": "LEGAL", "nt": "n/a"}
    ).get_data(as_text=True)
    assert MSG_RESTRICTED_BANNER in html
    assert "F10=Post Hold" in html


def test_review_screen_shows_the_same_banner_to_a_supervisor(supervisor):
    html = supervisor.post(
        "/hold/review", data={"share": "400118-S0001", "rsn": "LEGAL", "nt": "n/a"}
    ).get_data(as_text=True)
    assert MSG_RESTRICTED_BANNER in html


def test_teller_post_is_refused_with_200_and_nothing_changes(teller):
    resp = teller.post("/hold/post", data={"share": "400118-S0001", "rsn": "LEGAL", "nt": ""})
    assert resp.status_code == 200
    assert MSG_NOT_AUTHORIZED in resp.get_data(as_text=True)
    assert STORE.get_share("400118-S0001").status == "ACTIVE"


def test_supervisor_post_succeeds_with_a_confirmation_code(supervisor):
    html = supervisor.post(
        "/hold/post", data={"share": "400118-S0001", "rsn": "LEGAL", "nt": "court order"}
    ).get_data(as_text=True)
    assert MSG_HOLD_POSTED in html
    assert "HX-" in html
    assert STORE.get_share("400118-S0001").status == "HOLD"


def test_supervisor_holding_an_already_held_share_is_a_business_outcome(supervisor):
    html = supervisor.post(
        "/hold/post", data={"share": "400226-S0002", "rsn": "LEGAL", "nt": ""}
    ).get_data(as_text=True)
    assert MSG_ALREADY_HELD in html


def test_denial_and_banner_are_distinguishable_strings():
    # Both mention AUTHORIZATION. A detector keyed on the banner would report a
    # permission failure on every successful supervisor run.
    assert "AUTHORIZATION" in MSG_RESTRICTED_BANNER
    assert "AUTHORIZATION" in MSG_NOT_AUTHORIZED
    assert MSG_RESTRICTED_BANNER not in MSG_NOT_AUTHORIZED
    assert MSG_NOT_AUTHORIZED not in MSG_RESTRICTED_BANNER


def test_hold_routes_require_a_session():
    app = create_app("quarrybrook")
    app.config["TESTING"] = True
    assert app.test_client().get("/hold/new?share=400118-S0001").status_code == 302
