"""The cook follows the recipe, checks every step, and never repeats a step in doubt."""

from __future__ import annotations

import asyncio

from handrail.kernel.evidence import Recorder, verify_chain
from handrail.replay.engine import ReplayEngine
from handrail.replay.journal import Journal
from handrail.schema.capability import Capability
from handrail.schema.errors import ErrorCode, OutcomeCategory
from handrail.surface.null_surface import NullSurface, Page

from ..factory import place_hold

ENV = {"BASE_URL": "http://bank"}
INPUTS = {"member_number": "400118", "reason": "LEGAL"}
CONFIRMATION = "HOLD POSTED CONFIRMATION HX-829120"


def capability() -> Capability:
    return Capability.model_validate(place_hold())


def pages(final: str = "sig:posted") -> list[Page]:
    """The stage set for the factory capability: three screens, in the order it visits them."""
    return [
        Page(
            "sig:inquiry",
            text="MEMBER INQUIRY",
            matches={("role_name", "Member number"): 1, ("role_name", "Hold"): 1},
            advance_on=frozenset({"Hold"}),
        ),
        Page(
            "sig:hold_form",
            text="NEW HOLD",
            matches={("role_name", "Reason"): 1, ("role_name", "F10=Post Hold"): 1},
            advance_on=frozenset({"F10=Post Hold"}),
        ),
        Page(
            final,
            text=CONFIRMATION,
            matches={("role_name", "Result"): 1},
            reads={"Result": CONFIRMATION},
        ),
    ]


def engine(surface, tmp_path) -> ReplayEngine:
    return ReplayEngine(
        surface,
        Recorder("run_t", root=tmp_path),
        env=ENV,
        poll_interval_s=0.001,
        settle_timeout_ms=50,
    )


async def test_the_happy_path_returns_typed_outputs_with_no_model_help(tmp_path):
    surface = NullSurface(pages())
    result = await engine(surface, tmp_path).run(capability(), INPUTS)
    assert result.ok and result.outcome == "posted"
    assert result.outputs == {"confirmation": "HX-829120"}
    assert (result.classifier_calls, result.llm_calls) == (0, 0)
    assert [s.status for s in result.steps] == ["ok"] * 5
    assert result.drift.score == 1.0
    assert surface.opened == ["http://bank/inquiry"]


async def test_the_run_leaves_a_sealed_record_behind(tmp_path):
    eng = engine(NullSurface(pages()), tmp_path)
    await eng.run(capability(), INPUTS)
    assert (eng.recorder.dir / "result.json").exists()
    assert verify_chain(eng.recorder.dir / "log.jsonl") == (True, 0)


async def test_every_mutating_step_is_journalled_before_and_after(tmp_path):
    journal = Journal()
    await engine(NullSurface(pages()), tmp_path).run(capability(), INPUTS, journal=journal)
    kinds = [(e.kind, e.name) for e in journal.entries if e.kind != "screen"]
    assert kinds == [
        ("dispatched", "enter_member"),
        ("observed", "enter_member"),
        ("dispatched", "choose_reason"),
        ("observed", "choose_reason"),
        ("dispatched", "post_hold"),
        ("observed", "post_hold"),
    ]


async def test_the_application_saying_no_is_an_answer_not_a_failure(tmp_path):
    result = await engine(NullSurface(pages(final="sig:held")), tmp_path).run(capability(), INPUTS)
    assert result.category is OutcomeCategory.BUSINESS_OUTCOME
    assert result.code is ErrorCode.ALREADY_PROCESSED
    assert result.outcome == "already_held"
    assert result.error is None and result.outputs == {}


async def test_a_bad_input_is_refused_before_anything_is_touched(tmp_path):
    surface = NullSurface(pages())
    result = await engine(surface, tmp_path).run(capability(), {**INPUTS, "member_number": "12"})
    assert result.code is ErrorCode.INVALID_INPUT
    assert surface.opened == [] and surface.actions == []


async def test_a_missing_control_names_the_step_and_photographs_the_screen(tmp_path):
    script = pages()
    script[1].matches.pop(("role_name", "Reason"))
    eng = engine(NullSurface(script), tmp_path)
    result = await eng.run(capability(), INPUTS)
    assert result.category is OutcomeCategory.RECOVERABLE
    assert result.code is ErrorCode.MISSING_CONTROL
    assert result.error is not None and result.error.step_id == "choose_reason"
    assert (eng.recorder.dir / "fail_choose_reason.txt").exists()


async def test_an_unexpected_screen_after_a_step_says_what_was_expected_and_seen(tmp_path):
    script = pages(final="sig:somewhere_else")  # the post lands on a screen nobody declared
    result = await engine(NullSurface(script), tmp_path).run(capability(), INPUTS)
    assert result.code is ErrorCode.SCREEN_MISMATCH
    assert result.error is not None and result.error.step_id == "post_hold"
    assert "['posted', 'already_held']" in result.error.message
    assert "sig:somewhere_else" in result.error.message


async def test_a_step_in_doubt_is_never_repeated_across_runs(tmp_path):
    """Invariant 2 at the engine: the post lands, the confirmation never shows, the run
    dies. A second run on the same journal must refuse, not click again."""
    script = pages()
    script[1].advance_on = frozenset()  # the click happens, the page never turns
    surface = NullSurface(script)
    journal = Journal(tmp_path / "journal.jsonl")

    first = await engine(surface, tmp_path / "r1").run(capability(), INPUTS, journal=journal)
    assert first.code is ErrorCode.SLOW_LOAD
    assert journal.in_doubt("post_hold")
    assert surface.actions.count(("invoke", "F10=Post Hold", None)) == 1

    surface.index = 0  # a fresh session starts from the top; the doubt remains on disk
    second = await engine(surface, tmp_path / "r2").run(
        capability(), INPUTS, journal=Journal.load(tmp_path / "journal.jsonl")
    )
    assert second.code is ErrorCode.UNSAFE_TO_RETRY
    assert second.error is not None and second.error.step_id == "post_hold"
    assert surface.actions.count(("invoke", "F10=Post Hold", None)) == 1, "posted exactly once"
    # the stage steps were harmlessly done again on the way there
    assert surface.actions.count(("set_value", "Member number", "400118")) == 2


async def test_a_commit_already_done_is_skipped_not_repeated(tmp_path):
    journal = Journal()
    journal.dispatch("post_hold")
    journal.observe("post_hold")
    surface = NullSurface(pages())
    result = await engine(surface, tmp_path).run(capability(), INPUTS, journal=journal)
    assert ("invoke", "F10=Post Hold", None) not in surface.actions
    assert [s.status for s in result.steps][:4] == ["ok", "ok", "ok", "already_done"]
    # With the post skipped the page never turned, so the run cannot honestly claim success.
    assert result.category is not OutcomeCategory.SUCCESS


async def test_a_crashing_surface_still_yields_a_typed_result(tmp_path):
    class Exploding(NullSurface):
        async def act(self, resolution, verb, value):
            raise RuntimeError("browser vanished")

    result = await engine(Exploding(pages()), tmp_path).run(capability(), INPUTS)
    assert result.category is OutcomeCategory.HARD_FAILURE
    assert result.code is ErrorCode.APPLICATION_ERROR
    assert result.error is not None and "browser vanished" in result.error.message


async def test_the_wrong_kind_of_surface_is_refused_up_front(tmp_path):
    class Terminal(NullSurface):
        kind = "terminal"

    surface = Terminal(pages())
    result = await engine(surface, tmp_path).run(capability(), INPUTS)
    assert result.code is ErrorCode.SURFACE_INCOMPATIBLE and surface.opened == []


async def test_a_secret_input_never_reaches_the_evidence(tmp_path):
    cap = place_hold()
    cap["inputs"].append({"name": "pin", "sensitivity": "secret"})
    eng = engine(NullSurface(pages()), tmp_path)
    await eng.run(Capability.model_validate(cap), {**INPUTS, "pin": "7731"})
    assert "7731" not in (eng.recorder.dir / "log.jsonl").read_text()


async def test_a_reused_engine_does_not_mix_two_runs(tmp_path):
    eng = engine(NullSurface(pages()), tmp_path)
    await eng.run(capability(), INPUTS)
    eng.surface = NullSurface(pages())
    second = await eng.run(capability(), INPUTS)
    assert len(second.steps) == 5


async def test_a_target_named_by_an_input_is_resolved_under_its_bound_name(tmp_path):
    cap = place_hold()
    cap["inputs"].append({"name": "share_id", "pattern": "^[0-9]{6}-S[0-9]{4}$"})
    cap["targets"]["open_hold"]["name"] = {"eq": "{{input.share_id}}"}
    stage = pages()
    stage[0].matches = {("role_name", "Member number"): 1, ("role_name", "400118-S0001"): 1}
    stage[0].advance_on = frozenset({"400118-S0001"})
    surface = NullSurface(stage)
    result = await engine(surface, tmp_path).run(
        Capability.model_validate(cap), {**INPUTS, "share_id": "400118-S0001"}
    )
    assert result.category is OutcomeCategory.SUCCESS
    assert ("invoke", "400118-S0001", None) in surface.actions


async def test_a_screen_that_gained_one_element_is_still_recognised_and_logged(tmp_path):
    # Tier 2 of kernel/signature.py: same furniture plus one chair.
    furniture = [f"work:path{i}" for i in range(8)]
    cap = place_hold()
    cap["screens"]["inquiry"] = {
        "signature": "sha256:0000000000000000",  # will not match exactly
        "label": "the member inquiry screen",
        "paths": furniture,
    }
    stage = pages()
    stage[0].paths = tuple(furniture + ["work:div.banner"])  # 8 of 9 shared: 0.89
    surface = NullSurface(stage)
    recorder = Recorder("run_t", root=tmp_path)
    result = await ReplayEngine(surface, recorder, env=ENV, poll_interval_s=0.001).run(
        Capability.model_validate(cap), INPUTS
    )
    assert result.category is OutcomeCategory.SUCCESS
    log = (recorder.dir / "log.jsonl").read_text()
    assert '"event": "screen.similar"' in log and '"screen": "inquiry"' in log


class Referee:
    """A scripted classifier: always this answer, this sure."""

    name = "fake"

    def __init__(self, answer: str, confidence: float = 0.95) -> None:
        self.answer, self.confidence, self.asked = answer, confidence, []

    async def ask(self, state, question):
        from handrail.escalate.questions import Verdict

        self.asked.append(question.name)
        rest = [o for o in question.options if o != self.answer]
        probs = {self.answer: self.confidence}
        probs.update({o: (1 - self.confidence) / len(rest) for o in rest})
        return Verdict(question.name, probs)


FURNITURE = [f"work:path{i}" for i in range(10)]


def reworded(shared: int) -> tuple[dict, list]:
    """A capability whose 'posted' screen stores furniture, and a stage set whose final page
    shares only `shared` of those ten paths: too few for tier 2, enough for the re-check."""
    cap = place_hold()
    cap["screens"]["posted"] = {
        "signature": "sha256:0000000000000000",
        "label": "the hold was posted",
        "paths": FURNITURE,
    }
    stage = pages()
    stage[2].paths = tuple(FURNITURE[:shared] + [f"work:new{i}" for i in range(10 - shared)])
    return cap, stage


def with_referee(stage, tmp_path, referee, book=None) -> tuple[ReplayEngine, Recorder]:
    recorder = Recorder("run_t", root=tmp_path)
    eng = ReplayEngine(
        NullSurface(stage),
        recorder,
        env=ENV,
        poll_interval_s=0.001,
        settle_timeout_ms=50,
        classifier=referee,
        episodes=book,
    )
    return eng, recorder


async def test_a_reworded_screen_is_named_by_the_referee_and_checked_against_the_furniture(
    tmp_path,
):
    from handrail.kernel.episodes import Episodes

    cap, stage = reworded(shared=7)  # 7 of 13: 0.54, below similar, above the re-check
    book = Episodes()
    eng, recorder = with_referee(stage, tmp_path, Referee("posted"), book)
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is OutcomeCategory.SUCCESS and result.outcome == "posted"
    assert result.classifier_calls >= 1 and result.llm_calls == 0
    rows = book.rows(recorder.run_id)
    assert rows and all(r["accepted"] for r in rows) and rows[0]["held"] == 1


async def test_a_confident_referee_is_still_refused_when_the_furniture_disagrees(tmp_path):
    cap, stage = reworded(shared=3)  # 3 of 17: the referee may be sure, the room is not the room
    eng, recorder = with_referee(stage, tmp_path, Referee("posted", confidence=0.99))
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is not OutcomeCategory.SUCCESS
    assert result.classifier_calls >= 1
    assert '"accepted": false' in (recorder.dir / "log.jsonl").read_text()


async def test_none_of_these_leaves_the_run_where_it_was(tmp_path):
    cap, stage = reworded(shared=7)
    eng, _ = with_referee(stage, tmp_path, Referee("none_of_these"))
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is not OutcomeCategory.SUCCESS and result.classifier_calls >= 1


async def test_without_a_referee_the_counter_stays_zero_and_the_run_fails_as_before(tmp_path):
    cap, stage = reworded(shared=7)
    result = await engine(NullSurface(stage), tmp_path).run(Capability.model_validate(cap), INPUTS)
    assert result.category is not OutcomeCategory.SUCCESS and result.classifier_calls == 0


async def test_the_referee_is_asked_once_per_screen_per_run(tmp_path):
    cap, stage = reworded(shared=7)
    referee = Referee("posted")
    eng, _ = with_referee(stage, tmp_path, referee)
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is OutcomeCategory.SUCCESS
    # settle, expect and the final outcome check all look at the same reworded page
    assert result.classifier_calls == 1 and len(referee.asked) == 1


class Scout:
    """A scripted bridge: turns the page by hand, then names what the test says."""

    name = "fake"

    def __init__(self, names: str | None, advance: bool = True, calls: int = 2) -> None:
        self.names, self.advance, self.calls, self.sent = names, advance, calls, []

    async def cross(self, surface, capability, candidates, inputs, env, step_id):
        from handrail.escalate.bridge import Crossing

        self.sent.append(list(candidates))
        if self.advance:
            surface.advance()
        return Crossing(self.names, self.calls, 3)


async def test_when_the_referee_abstains_the_scout_crosses_and_the_furniture_is_checked(tmp_path):
    # The result page has moved one page further than the stage set says; the scout turns it.
    cap, stage = reworded(shared=7)
    waiting = Page(
        "sig:interstitial",
        text="PLEASE WAIT",
        matches={("role_name", "Result"): 1},  # the settle is satisfied; the screen is not
        paths=("work:div.wait",),
    )
    stage.insert(2, waiting)
    stage[1].advance_on = frozenset({"F10=Post Hold"})
    scout = Scout("posted")
    recorder = Recorder("run_t", root=tmp_path)
    eng = ReplayEngine(
        NullSurface(stage), recorder, env=ENV, poll_interval_s=0.001, settle_timeout_ms=50,
        classifier=Referee("none_of_these"), bridge=scout,
    )  # fmt: skip
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is OutcomeCategory.SUCCESS, result.error
    assert result.classifier_calls >= 1 and result.llm_calls == 2
    assert '"event": "rung2.screen"' in (recorder.dir / "log.jsonl").read_text()


async def test_a_scout_naming_a_landmark_behind_the_cook_is_ignored(tmp_path):
    # Invariant 3: a forward bridge never moves the run backwards. "inquiry" is not a candidate
    # after post_hold, so naming it is not a crossing, however sure the scout is.
    cap, stage = reworded(shared=7)
    scout = Scout("inquiry", advance=False)
    eng, _ = with_referee(stage, tmp_path, Referee("none_of_these"))
    eng.bridge = scout
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is not OutcomeCategory.SUCCESS
    assert all("inquiry" not in sent for sent in scout.sent)


async def test_a_scout_that_names_the_right_screen_on_the_wrong_furniture_is_refused(tmp_path):
    cap, stage = reworded(shared=3)  # 3 of 17 shared: the scout's word is not enough
    eng, recorder = with_referee(stage, tmp_path, Referee("none_of_these"))
    eng.bridge = Scout("posted", advance=False)
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is not OutcomeCategory.SUCCESS
    assert '"accepted": false' in (recorder.dir / "log.jsonl").read_text()


async def test_when_every_rung_fails_a_person_takes_over_and_hands_back(tmp_path):
    from handrail.kernel.control import Baton
    from handrail.serve.console import Console

    cap, stage = reworded(shared=3)  # nothing deterministic can place this page
    console = Console(Baton())
    eng, recorder = with_referee(stage, tmp_path, Referee("none_of_these"))
    eng.console, eng.human_wait_s = console, 2.0

    async def person():
        await asyncio.sleep(0.05)
        console.act("take_over", "dhawal")
        console.act("hand_back", "dhawal", "posted")

    asyncio.get_running_loop().create_task(person())
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is OutcomeCategory.SUCCESS and result.outcome == "posted"
    assert result.escalated_to_human is True
    log = (recorder.dir / "log.jsonl").read_text()
    assert '"event": "rung3.paused"' in log and '"by": "dhawal"' in log


async def test_an_abort_at_the_console_ends_the_run_as_aborted_by_operator(tmp_path):
    from handrail.kernel.control import Baton
    from handrail.serve.console import Console

    cap, stage = reworded(shared=3)
    console = Console(Baton())
    eng, _ = with_referee(stage, tmp_path, Referee("none_of_these"))
    eng.console, eng.human_wait_s = console, 2.0

    async def person():
        await asyncio.sleep(0.05)
        console.act("abort", "dhawal")

    asyncio.get_running_loop().create_task(person())
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.code is ErrorCode.ABORTED_BY_OPERATOR


async def test_nobody_at_the_console_is_a_timeout_not_a_guess(tmp_path):
    from handrail.kernel.control import Baton
    from handrail.serve.console import Console

    cap, stage = reworded(shared=3)
    eng, _ = with_referee(stage, tmp_path, Referee("none_of_these"))
    eng.console, eng.human_wait_s = Console(Baton()), 0.05
    result = await eng.run(Capability.model_validate(cap), INPUTS)
    assert result.category is not OutcomeCategory.SUCCESS and result.escalated_to_human
