"""Tests for the librarian's desk, run against the real cards and the real example evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from handrail.serve.web.settings import Settings
from handrail.serve.web.store import NotFound, Store

ROOT = Path(__file__).parents[3]


@pytest.fixture
def store() -> Store:
    return Store(
        Settings(
            ROOT / "capabilities",
            ROOT / "evidence/examples",
            ROOT / "evidence/examples/episodes.db",
        )
    )


def test_runs_come_newest_first_and_hide_nothing_the_recorder_did_not_write(store: Store) -> None:
    runs = store.runs(100)
    on_disk = [p for p in (ROOT / "evidence/examples").iterdir() if (p / "result.json").is_file()]
    assert len(runs) == len(on_disk)
    stamps = [r["started_at"] for r in runs]
    assert stamps == sorted(stamps, reverse=True)


def test_a_run_id_with_a_slash_is_refused(store: Store) -> None:
    with pytest.raises(ValueError):
        store.run("../capabilities")
    with pytest.raises(ValueError):
        store.run_file("a/b", "x.png")
    with pytest.raises(ValueError):
        store.capability("../pyproject.toml")


def test_an_unknown_run_is_not_found(store: Store) -> None:
    with pytest.raises(NotFound):
        store.run("no-such-run")


def test_the_chain_of_the_success_example_verifies(store: Store) -> None:
    run_id = store.runs(100)[0]["run_id"]
    for r in store.runs(100):
        got = store.run(r["run_id"])
        assert got["chain"]["ok"] and got["chain"]["lines"] > 0, run_id
        assert got["chain"]["bad_line"] == 0
        assert got["events"] and got["result"]["run_id"] == r["run_id"]


def test_the_takeover_example_carries_its_screenshots(store: Store) -> None:
    got = next(store.run(r["run_id"]) for r in store.runs(100) if r["escalated_to_human"])
    assert got["screenshots"]
    assert all(s["png"].endswith(".png") and s["txt"] for s in got["screenshots"])
    assert store.run_file(got["result"]["run_id"], got["screenshots"][0]["png"]).is_file()


def test_the_approved_read_card_is_a_read_capability(store: Store) -> None:
    cards = {c["file"]: c for c in store.capabilities()}
    read = cards["plumbline-read-balance.json"]
    assert read["read_or_write"] == "read" and read["state"] == "approved"
    assert cards["plumbline-place-hold.json"]["read_or_write"] == "write"


def test_success_rate_is_clean_over_replays(store: Store) -> None:
    for c in store.capabilities():
        rel = c["reliability"]
        want = rel["clean"] / rel["replays"] if rel["replays"] else None
        assert c["success_rate"] == want


def test_a_card_lists_its_sibling_versions(store: Store) -> None:
    card = store.capability("plumbline-place-hold.json")
    files = {v["file"] for v in card["versions"]}
    assert files == {"plumbline-place-hold.json", "plumbline-place-hold.authored.json"}


def test_an_approved_card_is_not_approvable_again(store: Store) -> None:
    done = store.checklist("plumbline-place-hold.json")
    assert done["verified"] and done["commits_confirmed"] and done["no_secret_literals"]
    assert done["approvable"] is False


def test_a_verified_card_with_confirmed_commits_is_approvable(store: Store) -> None:
    got = store.checklist("plumbline-place-hold.authored.json")
    assert got["reasons"] == [] and got["approvable"] is True


def test_summary_counts_the_takeover_example_as_handed_back_not_open(store: Store) -> None:
    s = store.summary()
    assert s["escalations_open"] == 0 and s["needs_a_person"] == []
    assert s["model_calls_on_replay"] == 0
    assert s["capabilities"] == 3 and s["approved"] == 2


def test_summary_lists_a_pause_that_was_never_handed_back(tmp_path: Path, store: Store) -> None:
    import json
    import shutil

    src = ROOT / "evidence/examples/7-replay-human-takeover"
    dst = tmp_path / "stuck"
    shutil.copytree(src, dst)
    lines = (dst / "log.jsonl").read_text().splitlines()
    kept = [x for x in lines if json.loads(x)["event"] != "rung3.handed_back"]
    (dst / "log.jsonl").write_text("\n".join(kept) + "\n")
    s = Store(Settings(store.settings.capabilities, tmp_path, None)).summary()
    assert s["escalations_open"] == 1
    assert s["needs_a_person"][0]["expected"]


def test_drift_counts_rungs_and_reads_the_notebook(store: Store) -> None:
    d = store.drift()
    assert d["rungs"] and {"capability_id", "step_id", "rung", "count", "last_run"} <= set(
        d["rungs"][0]
    )
    assert all({"run_id", "step_id", "rung", "accepted"} <= set(h) for h in d["healing"])
    assert len(d["calibration"]) == 5


def test_drift_without_a_notebook_has_no_calibration(store: Store) -> None:
    bare = Store(Settings(store.settings.capabilities, store.settings.evidence, None))
    assert bare.drift()["calibration"] == []
