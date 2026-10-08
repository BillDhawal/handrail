"""The tasting before the dish goes on the menu: three plates, three tables, one honest judge.

A recipe card the chef wrote last night is not on the menu yet. The line
cook makes it three times, for three different orders, from a cold kitchen
each time. And after each plate somebody who was not in the kitchen walks to
the table and checks the diner actually got what was ordered. Only then is
the card marked ``verified``. Marking it ``approved`` is still a named
person's signature, never this file's.

Why so strict: PreAct measured that replay without a store-time gate decays
to zero success as bad cards pile up. One good evening proves one evening.

What counts as a clean plate: the run ended in ``SUCCESS``, both model
counters are zero, and the independent check says yes. The check is
injected, because only the caller knows how to ask the application's record
store whether a hold really exists; the gate never trusts the screen alone.

A card with a commit nobody confirmed cannot leave draft, however many clean
plates it produced. The schema enforces that; this file just reports it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ..kernel.evidence import Recorder
from ..replay.engine import ReplayEngine
from ..replay.journal import Journal
from ..schema.capability import Capability
from ..schema.errors import OutcomeCategory
from ..schema.results import RunResult
from ..surface.base import Surface

#: Did the task really happen? Asked of the record store, never of the screen.
Check = Callable[[dict[str, Any], RunResult], Awaitable[bool]]
#: A cold kitchen for each plate.
MakeSurface = Callable[[], Surface]
MakeRecorder = Callable[[int], Recorder]

MINIMUM_TRIALS = 3


@dataclass
class Plate:
    inputs: dict[str, Any]
    result: RunResult | None = None
    checked: bool | None = None
    reason: str | None = None

    @property
    def clean(self) -> bool:
        return self.reason is None


@dataclass
class Verdict:
    capability: Capability
    plates: list[Plate] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return self.capability.lifecycle.state == "verified"


async def _plate(
    capability: Capability,
    inputs: dict[str, Any],
    surface: Surface,
    recorder: Recorder,
    check: Check,
    env: dict[str, str],
) -> Plate:
    plate = Plate(inputs=inputs)
    engine = ReplayEngine(surface, recorder, env=env)
    try:
        plate.result = await engine.run(capability, inputs, Journal())
    finally:
        await surface.close()
    result = plate.result
    if result.category is not OutcomeCategory.SUCCESS:
        plate.reason = f"ended {result.category.value} {result.code.value}"
        return plate
    if result.classifier_calls or result.llm_calls:
        plate.reason = "a model was consulted on the replay path"
        return plate
    plate.checked = await check(inputs, result)
    if not plate.checked:
        plate.reason = "the independent check says the task did not happen"
    return plate


async def verify(
    capability: Capability,
    trials: list[dict[str, Any]],
    make_surface: MakeSurface,
    make_recorder: MakeRecorder,
    check: Check,
    env: dict[str, str] | None = None,
) -> Verdict:
    """Three plates from a cold kitchen, each judged. The card leaves draft only if all are clean.

    The verdict carries the promoted card, or the original one plus every reason it stayed.
    """
    verdict = Verdict(capability=capability)
    if len(trials) < MINIMUM_TRIALS:
        verdict.reasons.append(f"needs at least {MINIMUM_TRIALS} trials, got {len(trials)}")
        return verdict
    for number, inputs in enumerate(trials, start=1):
        surface, recorder = make_surface(), make_recorder(number)
        plate = await _plate(capability, inputs, surface, recorder, check, env or {})
        verdict.plates.append(plate)
        if not plate.clean:
            verdict.reasons.append(f"trial {number}: {plate.reason}")
    if verdict.reasons:
        return verdict
    promoted = capability.model_dump()
    promoted["lifecycle"] = {
        **promoted["lifecycle"],
        "state": "verified",
        "reliability": {"replays": len(trials), "clean": len(trials)},
    }
    try:
        verdict.capability = Capability.model_validate(promoted)
    except ValidationError as exc:
        verdict.reasons.append(str(exc.errors()[0].get("msg", exc)))
    return verdict
