# Evidence, by example

All runs were made on 2026-10-08 and 2026-10-10 against PLUMBLINE (`targetapp/`), the mock
core-banking app, on `127.0.0.1:8081`. Every `log.jsonl` is hash-chained; `verify_chain` in
`kernel/evidence.py` walks it. No run holds a secret: the operator's password is registered with
the recorder and masked in everything it writes.

| directory | what it shows | result |
|---|---|---|
| `0-discovery/` | **The real discovery run.** `claude-sonnet-5` drove the bank through the numbered menu with three tools (`act`, `assert_screen`, `finish`): 19 turns, 12 model calls. `trace.jsonl` is the order book, one line per accepted turn with the rungs probed and the fingerprint taken; `log.jsonl` is the same, sealed. `compiled-capability.json` is what the compiler wrote from it and the verify gate then passed (three clean plates) | 11 steps, 7 screens, verified |
| `1-replay-success/` | The model-authored card replayed with no model: 11 of 11 controls on their first-choice rung | `SUCCESS`, `classifier_calls=0`, `llm_calls=0` |
| `2-replay-already-held/` | The hand-written card on a share already under hold. An answer, not a failure | `BUSINESS_OUTCOME` `ALREADY_PROCESSED` |
| `3-replay-no-such-member/` | Member 999999 does not exist | `BUSINESS_OUTCOME` `RECORD_NOT_FOUND` |
| `4-replay-injected-failure/` | A maintenance page armed on the hold form (`/__test__/arm_fault`). The settle never came true; the screen was photographed (`fail_open_hold.png`, `.txt`). `retryable` is true because the fault was transient | `RECOVERABLE` `SLOW_LOAD` at `open_hold` |
| `5-replay-drift-rung-one/` | The result line reworded and reclassed (`drift_reword`). Exact and similar matching failed; the Claude referee named "Hold Result" at 0.95 and the furniture overlap of 0.8 confirmed it. See `rung1.screen` in the log and `../episodes.db` | `SUCCESS`, `classifier_calls=1`, `llm_calls=0` |
| `6-replay-bad-input/` | `member_number=12` against the card's pattern `^[0-9]{6}$`. Refused before the browser opened | `HARD_FAILURE` `INVALID_INPUT` |
| `7-replay-human-takeover/` | The result page rewritten entirely (`drift_major`). The referee said none of these; the baton went to a person at the console (`rung3.paused`), who took over, handed back naming "Hold Result" (`rung3.handed_back`, with name and time), and the run finished. `human_before_*` and `human_after_*` are the screen either side of the handoff | `SUCCESS`, `escalated_to_human=true` |
| `episodes.db` | The referee's notebook for runs 5 and 7: every whistle, settled by the run's outcome. `uv run handrail episodes evidence/examples/episodes.db` prints the calibration table | |

How to read a log line: `event` names the step of the loop (`step.start`, `step.ok`,
`screen.similar`, `rung1.screen`, `rung3.paused`, `replay.error`, `replay.finish`), `prev` and
`hash` are the chain. A `replay.error` line says which step, what was expected and what was seen,
and names the screenshot taken at that moment.
