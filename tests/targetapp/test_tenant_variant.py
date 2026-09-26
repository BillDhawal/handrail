import pytest

from targetapp.app import STORE, create_app


def _client(tenant: str, branch: str):
    STORE.reset()
    app = create_app(tenant)
    app.config["TESTING"] = True
    c = app.test_client()
    html = c.get("/signon").get_data(as_text=True)
    marker = 'name="_tk" value="'
    start = html.index(marker) + len(marker)
    tk = html[start : html.index('"', start)]
    c.post("/signon", data={"opid": "mrivas", "pw": "plumbline-demo", "br": branch, "_tk": tk})
    return c


@pytest.fixture
def fern():
    return _client("fernhollow", "FH-01")


def test_variant_uses_its_own_frame_names(fern):
    html = fern.get("/desk").get_data(as_text=True)
    assert 'name="sidebar"' in html
    assert 'name="main"' in html
    assert 'name="work"' not in html


def test_variant_uses_its_own_search_field_and_label(fern):
    html = fern.get("/inquiry").get_data(as_text=True)
    assert 'name="srchval"' in html
    assert "PF5 Find" in html
    assert 'name="sval"' not in html


def test_variant_uses_its_own_member_header_and_table_class(fern):
    html = fern.get("/member/400118").get_data(as_text=True)
    assert "MEMBER MASTER" in html
    assert "MEMBER RECORD" not in html
    assert 'class="lst"' in html


def test_variant_nests_the_shares_table_one_level_deeper(fern):
    html = fern.get("/member/400118").get_data(as_text=True)
    assert '<div class="panel"><table class="lst">' in html


def test_variant_serves_the_same_data(fern):
    html = fern.get("/member/400118").get_data(as_text=True)
    assert "Alvarez, Marisol" in html
    assert "400118-S0001" in html
    assert "$42,100.50" in html


def test_variant_offers_its_own_branch_codes(fern):
    html = fern.get("/signon").get_data(as_text=True)
    assert "FH-01" in html
    assert "QB-01" not in html


def test_variant_has_no_stable_identifiers(fern):
    html = fern.get("/member/400118").get_data(as_text=True)
    assert "data-testid" not in html
    assert 'id="' not in html
