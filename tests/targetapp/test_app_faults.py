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


def test_the_share_status_endpoint_reads_the_store_not_the_screen(monkeypatch):
    monkeypatch.setenv("HANDRAIL_ALLOW_FAULTS", "1")
    client = create_app("quarrybrook").test_client()
    assert client.get("/__test__/share/400226-S0002").get_json()["status"] == "HOLD"
    assert client.get("/__test__/share/400118-S0001").get_json()["status"] == "ACTIVE"
    assert client.get("/__test__/share/nope").status_code == 404


def test_the_share_status_endpoint_is_off_without_the_flag(monkeypatch):
    monkeypatch.delenv("HANDRAIL_ALLOW_FAULTS", raising=False)
    client = create_app("quarrybrook").test_client()
    assert client.get("/__test__/share/400226-S0002").status_code == 404


def _arm(client, fault: str) -> None:
    client.post("/__test__/arm_fault", json={"fault": fault, "on_path": "/", "once": False})


def test_minor_drift_adds_a_banner_to_every_page_and_stays_armed(monkeypatch):
    monkeypatch.setenv("HANDRAIL_ALLOW_FAULTS", "1")
    client = create_app("quarrybrook").test_client()
    _arm(client, "drift_minor")
    for _ in range(2):
        assert 'class="promo"' in client.get("/signon").get_data(as_text=True)
    client.post("/__test__/reset")
    assert 'class="promo"' not in client.get("/signon").get_data(as_text=True)


def test_reword_drift_changes_the_hold_result_line_and_its_class(monkeypatch):
    monkeypatch.setenv("HANDRAIL_ALLOW_FAULTS", "1")
    client = create_app("quarrybrook").test_client()
    _arm(client, "drift_reword")
    with client.session_transaction() as sess:
        sess["opid"] = "dcolewell"
    html = client.post(
        "/hold/post", data={"share": "400118-S0001", "rsn": "LEGAL", "nt": ""}
    ).get_data(as_text=True)
    assert "HOLD HAS BEEN PLACED" in html and "HOLD POSTED" not in html
    assert 'class="note">HOLD HAS BEEN PLACED' in html
    html = client.post(
        "/hold/post", data={"share": "400226-S0002", "rsn": "LEGAL", "nt": ""}
    ).get_data(as_text=True)
    assert 'class="note">SHARE IS CURRENTLY HELD' in html
    client.post("/__test__/reset")  # ARMED is one dict per process; leave it clean


def test_major_drift_leaves_nothing_of_the_result_page_for_a_machine_to_recognise(monkeypatch):
    monkeypatch.setenv("HANDRAIL_ALLOW_FAULTS", "1")
    client = create_app("quarrybrook").test_client()
    _arm(client, "drift_major")
    with client.session_transaction() as sess:
        sess["opid"] = "dcolewell"
    html = client.post(
        "/hold/post", data={"share": "400118-S0001", "rsn": "LEGAL", "nt": ""}
    ).get_data(as_text=True)
    assert "REQUEST ACCEPTED" in html and "HOLD" not in html
    assert 'class="hdr"' not in html and 'class="banner"' in html and 'class="frame"' in html
    client.post("/__test__/reset")
