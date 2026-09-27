"""The cook follows the recipe, checks every step, and never repeats a step in doubt."""

from __future__ import annotations

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
