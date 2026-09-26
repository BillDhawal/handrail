import pytest

from targetapp.app import create_app
from targetapp.data import MSG_SIGNON_REJECTED


@pytest.fixture
def client():
    app = create_app("quarrybrook")
    app.config["TESTING"] = True
    return app.test_client()


def _token(client) -> str:
    """Pull the current form token out of the rendered sign-on page."""
    html = client.get("/signon").get_data(as_text=True)
    marker = 'name="_tk" value="'
    start = html.index(marker) + len(marker)
    return html[start : html.index('"', start)]


def test_signon_page_renders_nameless_controls(client):
    html = client.get("/signon").get_data(as_text=True)
    assert 'name="opid"' in html
    assert 'name="pw"' in html
    assert 'name="br"' in html
    # The hostile-surface guarantee: no ids, no test ids, no label association.
    assert "data-testid" not in html
    assert "<label" not in html
    assert 'id="' not in html


def test_successful_signon_redirects_to_desk(client):
    resp = client.post(
        "/signon",
        data={"opid": "mrivas", "pw": "plumbline-demo", "br": "QB-01", "_tk": _token(client)},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/desk")


def test_bad_password_renders_rejection_text_with_200(client):
    resp = client.post(
        "/signon",
        data={"opid": "mrivas", "pw": "nope", "br": "QB-01", "_tk": _token(client)},
    )
    assert resp.status_code == 200
    assert MSG_SIGNON_REJECTED in resp.get_data(as_text=True)


def test_form_token_rotates_after_use(client):
    first = _token(client)
    client.post(
        "/signon",
        data={"opid": "mrivas", "pw": "plumbline-demo", "br": "QB-01", "_tk": first},
    )
    assert _token(client) != first


def test_stale_form_token_is_rejected(client):
    stale = _token(client)
    client.post(
        "/signon",
        data={"opid": "mrivas", "pw": "plumbline-demo", "br": "QB-01", "_tk": stale},
    )
    resp = client.post(
        "/signon",
        data={"opid": "mrivas", "pw": "plumbline-demo", "br": "QB-01", "_tk": stale},
    )
    assert resp.status_code == 400


def test_desk_renders_a_frameset_with_tenant_frame_names(client):
    client.post(
        "/signon",
        data={"opid": "mrivas", "pw": "plumbline-demo", "br": "QB-01", "_tk": _token(client)},
    )
    html = client.get("/desk").get_data(as_text=True)
    assert "<frameset" in html
    assert 'name="menu"' in html
    assert 'name="work"' in html


def test_desk_requires_a_session(client):
    resp = client.get("/desk")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/signon")
