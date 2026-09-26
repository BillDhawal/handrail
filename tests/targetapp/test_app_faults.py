import pytest

from targetapp.app import STORE, create_app
from targetapp.data import MSG_APP_ERROR, MSG_DIALOG, MSG_MAINTENANCE, MSG_SESSION_EXPIRED


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HANDRAIL_ALLOW_FAULTS", "1")
    STORE.reset()
    app = create_app("quarrybrook")
    app.config["TESTING"] = True
    c = app.test_client()
    html = c.get("/signon").get_data(as_text=True)
    marker = 'name="_tk" value="'
    start = html.index(marker) + len(marker)
    tk = html[start : html.index('"', start)]
    c.post("/signon", data={"opid": "mrivas", "pw": "plumbline-demo", "br": "QB-01", "_tk": tk})
    return c


def test_armed_timeout_fault_fires_once_then_disarms(client):
    client.post("/__test__/arm_fault", json={"fault": "timeout", "on_path": "/member"})
    assert MSG_SESSION_EXPIRED in client.get("/member/400118").get_data(as_text=True)
    assert MSG_SESSION_EXPIRED not in client.get("/member/400118").get_data(as_text=True)


def test_armed_fault_only_fires_on_the_matching_path(client):
    client.post("/__test__/arm_fault", json={"fault": "maintenance", "on_path": "/member"})
    assert MSG_MAINTENANCE not in client.get("/inquiry").get_data(as_text=True)
    assert MSG_MAINTENANCE in client.get("/member/400118").get_data(as_text=True)


def test_dialog_fault_renders_an_interstitial_with_a_continue_control(client):
    client.post("/__test__/arm_fault", json={"fault": "dialog", "on_path": "/member"})
    html = client.get("/member/400118").get_data(as_text=True)
    assert MSG_DIALOG in html
    assert "Continue" in html


def test_error_fault_renders_the_application_error_text(client):
    client.post("/__test__/arm_fault", json={"fault": "error", "on_path": "/member"})
    assert MSG_APP_ERROR in client.get("/member/400118").get_data(as_text=True)


def test_reset_restores_seed_state(client):
    STORE.get_share("400118-S0001").status = "HOLD"
    client.post("/__test__/reset")
    assert STORE.get_share("400118-S0001").status == "ACTIVE"


def test_test_endpoints_are_gated_off_by_default(monkeypatch):
    monkeypatch.delenv("HANDRAIL_ALLOW_FAULTS", raising=False)
    app = create_app("quarrybrook")
    app.config["TESTING"] = True
    c = app.test_client()
    assert c.post("/__test__/reset").status_code == 404
    assert (
        c.post("/__test__/arm_fault", json={"fault": "timeout", "on_path": "/"}).status_code == 404
    )


def test_the_control_surface_is_never_faultable(client):
    """A broad fault must not lock out the endpoint that clears it.

    Arming on "/" with once=false previously made /__test__/reset serve the fault
    page instead of resetting, leaving no way to recover short of a restart.
    """
    client.post("/__test__/arm_fault", json={"fault": "error", "on_path": "/", "once": False})
    assert MSG_APP_ERROR in client.get("/member/400118").get_data(as_text=True)
    assert client.post("/__test__/reset").status_code == 200
    assert MSG_APP_ERROR not in client.get("/member/400118").get_data(as_text=True)
