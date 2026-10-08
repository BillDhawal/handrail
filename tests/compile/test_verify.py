"""Three clean plates from a cold kitchen, or the card stays in draft."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from handrail.compile.verify import MINIMUM_TRIALS, verify
from handrail.kernel.evidence import Recorder
from handrail.schema.capability import Capability
from handrail.schema.results import RunResult
from handrail.surface.null_surface import NullSurface

from ..factory import place_hold
from ..replay.test_engine import ENV, pages

TRIALS = [{"member_number": n, "reason": "LEGAL"} for n in ("400118", "400226", "400337")]


def confirmed() -> Capability:
    cap = place_hold()
    for step in cap["steps"]:
        if step["effect"]["kind"] == "commit":
            step["effect"]["confirmed_by"] = "dhawal"
    return Capability.model_validate(cap)


async def yes(inputs: dict[str, Any], result: RunResult) -> bool:
    return True


async def no(inputs: dict[str, Any], result: RunResult) -> bool:
    return False


def kitchen(tmp_path: Path, final: str = "sig:posted"):
    return (lambda: NullSurface(pages(final)), lambda n: Recorder(f"verify_{n}", root=tmp_path))


async def test_three_clean_plates_mark_the_card_verified(tmp_path: Path):
    make_surface, make_recorder = kitchen(tmp_path)
    verdict = await verify(confirmed(), TRIALS, make_surface, make_recorder, yes, ENV)
    assert verdict.verified and verdict.reasons == []
    assert verdict.capability.lifecycle.reliability.replays == 3
    assert verdict.capability.lifecycle.reliability.clean == 3
    assert all(p.clean and p.checked for p in verdict.plates)


async def test_fewer_than_three_trials_is_refused_before_cooking(tmp_path: Path):
    cooked: list[int] = []

    def make_surface() -> NullSurface:
        cooked.append(1)
        return NullSurface(pages())

    verdict = await verify(confirmed(), TRIALS[:2], make_surface, kitchen(tmp_path)[1], yes)
    assert not verdict.verified and cooked == []
    assert verdict.reasons == [f"needs at least {MINIMUM_TRIALS} trials, got 2"]


async def test_a_plate_the_judge_rejects_keeps_the_card_in_draft(tmp_path: Path):
    make_surface, make_recorder = kitchen(tmp_path)
    verdict = await verify(confirmed(), TRIALS, make_surface, make_recorder, no, ENV)
    assert not verdict.verified
    assert verdict.reasons[0] == "trial 1: the independent check says the task did not happen"
    assert verdict.capability.lifecycle.state == "draft"


async def test_a_plate_that_ends_as_a_business_outcome_is_not_clean(tmp_path: Path):
    make_surface, make_recorder = kitchen(tmp_path, final="sig:held")
    verdict = await verify(confirmed(), TRIALS, make_surface, make_recorder, yes, ENV)
    assert not verdict.verified
    assert verdict.reasons[0] == "trial 1: ended BUSINESS_OUTCOME ALREADY_PROCESSED"


async def test_a_commit_nobody_confirmed_cannot_leave_draft_however_clean(tmp_path: Path):
    make_surface, make_recorder = kitchen(tmp_path)
    unconfirmed = Capability.model_validate(place_hold())
    verdict = await verify(unconfirmed, TRIALS, make_surface, make_recorder, yes, ENV)
    assert all(p.clean for p in verdict.plates)  # three clean plates
    assert not verdict.verified
    assert "not confirmed by a person" in verdict.reasons[0]


async def test_every_plate_gets_a_cold_kitchen_and_its_own_record(tmp_path: Path):
    made: list[NullSurface] = []

    def make_surface() -> NullSurface:
        made.append(NullSurface(pages()))
        return made[-1]

    await verify(confirmed(), TRIALS, make_surface, kitchen(tmp_path)[1], yes, ENV)
    assert len(made) == 3 and len({id(s) for s in made}) == 3
    assert sorted(p.name for p in tmp_path.iterdir()) == ["verify_1", "verify_2", "verify_3"]
