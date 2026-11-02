"""Tests for the card catalogue: it must agree with the shelves and be rebuildable from them."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from handrail.serve.web.index import Index
from handrail.serve.web.settings import Settings
from handrail.serve.web.store import Store

ROOT = Path(__file__).parents[3]


def shelves(tmp_path: Path) -> Settings:
    """A private copy of the real cards and example runs, so a test may move things about."""
    caps, runs = tmp_path / "capabilities", tmp_path / "runs"
    shutil.copytree(ROOT / "capabilities", caps)
    shutil.copytree(ROOT / "evidence/examples", runs, ignore=shutil.ignore_patterns("*.db"))
    return Settings(caps, runs, None)


def test_an_empty_index_rebuilds_itself_from_the_shelves() -> None:
    settings = Settings(ROOT / "capabilities", ROOT / "evidence/examples", None)
    by_files = Store(settings)
    index = Index()
    index.sync(settings)
    from_files = {r["run_id"]: r for r in by_files.runs(1000)}
    from_index = {r["run_id"]: r for r in index.runs(1000)}
    assert from_files and from_index == from_files
    assert [c["id"] for c in index.capabilities()] == [c["id"] for c in by_files.capabilities()]
    assert [c["file"] for c in index.capabilities()] == [c["file"] for c in by_files.capabilities()]


def test_a_run_written_after_the_sync_is_found_by_upsert_without_a_full_rescan(
    tmp_path: Path,
) -> None:
    settings = shelves(tmp_path)
    index = Index()
    index.sync(settings)
    before = len(index.runs(1000))
    source = next(settings.evidence.glob("*/result.json")).parent
    new = settings.evidence / "late-arrival"
    shutil.copytree(source, new)
    result = json.loads((new / "result.json").read_text())
    result["run_id"] = "late-arrival"
    (new / "result.json").write_text(json.dumps(result))
    assert len(index.runs(1000)) == before  # not yet filed
    assert index.upsert_run(new)
    assert len(index.runs(1000)) == before + 1
    assert index.dir_of("late-arrival") == new.resolve()


def test_a_deleted_run_dir_leaves_the_index_on_the_next_sync(tmp_path: Path) -> None:
    settings = shelves(tmp_path)
    index = Index()
    index.sync(settings)
    victim = index.runs(1)[0]["run_id"]
    shutil.rmtree(index.dir_of(victim) or tmp_path)
    assert victim in {r["run_id"] for r in index.runs(1000)}
    index.sync(settings)
    assert victim not in {r["run_id"] for r in index.runs(1000)}
    assert index.dir_of(victim) is None


def test_a_card_that_changes_state_on_disk_is_re_read_because_its_mtime_moved(
    tmp_path: Path,
) -> None:
    settings = shelves(tmp_path)
    index = Index()
    index.sync(settings)
    path = settings.capabilities / "plumbline-read-balance.json"
    card = json.loads(path.read_text())
    was = card["lifecycle"]["state"]
    card["lifecycle"]["state"] = "deprecated" if was != "deprecated" else "draft"
    path.write_text(json.dumps(card))
    stamp = path.stat().st_mtime + 5
    os.utime(path, (stamp, stamp))
    index.sync(settings)
    row = next(c for c in index.capabilities() if c["file"] == path.name)
    assert row["state"] == card["lifecycle"]["state"] != was


def test_filters_by_capability_category_and_escalation() -> None:
    settings = Settings(ROOT / "capabilities", ROOT / "evidence/examples", None)
    index = Index()
    index.sync(settings)
    everything = index.runs(1000)
    cap = everything[0]["capability_id"]
    category = everything[0]["category"]
    assert {r["capability_id"] for r in index.runs(1000, capability_id=cap)} == {cap}
    wanted = [r for r in everything if r["category"] == category]
    assert index.runs(1000, category=category) == wanted
    escalated = index.runs(1000, escalated=True)
    assert escalated == [r for r in everything if r["escalated_to_human"]]
    calm = index.runs(1000, escalated=False)
    assert len(escalated) + len(calm) == len(everything)
    assert index.runs(1000, capability_id="no-such-capability") == []


def test_the_index_file_survives_a_restart(tmp_path: Path) -> None:
    settings = Settings(ROOT / "capabilities", ROOT / "evidence/examples", None)
    db = tmp_path / "nested" / "handrail.db"
    first = Index(db)
    first.sync(settings)
    runs, cards = first.runs(1000), first.capabilities()
    first.close()
    second = Index(db)  # no sync
    assert second.runs(1000) == runs and runs
    assert second.capabilities() == cards and cards
    assert second.synced_at is not None


def test_a_file_that_is_not_a_database_is_replaced_not_mourned(tmp_path: Path) -> None:
    db = tmp_path / "handrail.db"
    db.write_text("this is not sqlite, it is a lunch order")
    assert Index(db).runs() == []
