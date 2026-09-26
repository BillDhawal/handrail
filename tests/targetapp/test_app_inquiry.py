import pytest

from targetapp.app import create_app
from targetapp.data import MSG_NO_MATCH


@pytest.fixture
def client():
    app = create_app("quarrybrook")
    app.config["TESTING"] = True
    c = app.test_client()
    html = c.get("/signon").get_data(as_text=True)
    marker = 'name="_tk" value="'
    start = html.index(marker) + len(marker)
    tk = html[start : html.index('"', start)]
    c.post("/signon", data={"opid": "mrivas", "pw": "plumbline-demo", "br": "QB-01", "_tk": tk})
    return c


def test_inquiry_form_uses_tenant_field_names(client):
    html = client.get("/inquiry").get_data(as_text=True)
    assert 'name="sby"' in html
    assert 'name="sval"' in html
    assert "F5=Search" in html


def test_search_by_member_number_lists_a_linked_result(client):
    resp = client.post("/inquiry", data={"sby": "MBRNO", "sval": "400118"})
    html = resp.get_data(as_text=True)
    assert '<a href="/member/400118">400118</a>' in html


def test_search_with_no_match_renders_the_business_message(client):
    html = client.post("/inquiry", data={"sby": "MBRNO", "sval": "400999"}).get_data(as_text=True)
    assert MSG_NO_MATCH in html


def test_member_record_shows_header_name_and_shares(client):
    html = client.get("/member/400118").get_data(as_text=True)
    assert "MEMBER RECORD" in html
    assert "Alvarez, Marisol" in html
    assert "SHARES / BALANCES" in html
    assert "400118-S0001" in html
    assert "$42,100.50" in html
    assert "REGULAR" in html
    assert "ACTIVE" in html


def test_share_rows_link_to_the_hold_form(client):
    html = client.get("/member/400118").get_data(as_text=True)
    assert 'href="/hold/new?share=400118-S0001"' in html


def test_member_record_has_no_stable_identifiers(client):
    html = client.get("/member/400118").get_data(as_text=True)
    assert "data-testid" not in html
    assert 'id="' not in html


def test_unknown_member_record_renders_the_business_message(client):
    html = client.get("/member/400999").get_data(as_text=True)
    assert MSG_NO_MATCH in html


def test_inquiry_requires_a_session():
    app = create_app("quarrybrook")
    app.config["TESTING"] = True
    resp = app.test_client().get("/inquiry")
    assert resp.status_code == 302
