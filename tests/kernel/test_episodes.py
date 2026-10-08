"""The notebook: one row per whistle, settled when the run ends, binned for calibration."""

from handrail.kernel.episodes import Episodes


def test_a_row_per_escalation_settled_by_the_runs_outcome():
    book = Episodes()
    book.record("run1", "bank.place_hold", "screen", rung=1, step_id="post_hold",
                question="which_screen", backend="fake", chosen="posted", confidence=0.9,
                margin=0.8, probabilities={"posted": 0.9}, accepted=True)  # fmt: skip
    book.record("run1", "bank.place_hold", "screen", rung=1, chosen="x", confidence=0.4)
    book.settle("run1", "SUCCESS", held=True)
    rows = book.rows("run1")
    assert [r["accepted"] for r in rows] == [1, 0]
    assert (rows[0]["outcome"], rows[0]["held"]) == ("SUCCESS", 1)
    assert rows[1]["held"] is None  # a rejected verdict is never judged


def test_calibration_bins_accepted_and_settled_verdicts_by_confidence():
    book = Episodes()
    for conf, held in ((0.95, True), (0.9, True), (0.85, False), (0.5, True)):
        book.record("r", "c", "screen", 1, question="which_screen", confidence=conf, accepted=True)
        book.settle("r", "SUCCESS" if held else "HARD_FAILURE", held)
        book.db.execute("UPDATE episodes SET run_id = ? WHERE run_id = 'r'", (f"r{conf}",))
    top = book.calibration("which_screen", bins=5)[-1]
    assert (top.low, top.count, top.held) == (0.8, 3, 2)
    assert abs(top.rate - 2 / 3) < 1e-9
