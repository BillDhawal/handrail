# Working in this repo

Handrail is a computer-use system built on one bet: doing a task once tells you nothing about
doing it a hundred times. A model works out a task once; the run compiles to a typed, reviewable
capability; replay is deterministic with no model in the loop; when a check fails, a ladder of
classifier, bounded model, then human is climbed, and every rung only proposes.

Read first: `docs/HANDOFF.md` (where we are), `docs/PLAN.md` (what is next, file by file),
`docs/DESIGN.md` (why). Do not re-derive the design; it was researched by six agents and approved.

## How we build together

The owner (Dhawal) is learning the system by pasting each file himself. So:

- **One file at a time.** Give the file, its test, a two-to-four-line explanation, and the
  command to run. Then stop and wait for "done". Never bulk-write feature files into the repo.
- **Verify before handing over.** Build the file in a scratch clone, run `make lint && make test`
  there, and only then present it. Never present code you have not seen pass.
- **Short responses. Analogies.** Every module docstring opens with a plain-language analogy
  (the waiter, the bouncer, the cashier's ledger, the flight recorder, the cook). Keep that up.
  Explain with pictures from ordinary life before naming the mechanism.
- **Tests first, and the test's name is the sentence it protects.** A file arrives with its
  tests. Point at the one or two tests worth reading slowly.
- After a paste, the owner runs `make lint && make test`. `make lint` fixes trailing newlines
  and wrapping an editor may change; it never alters behaviour.

## Rules that do not bend

1. No model client is importable from `schema`, `replay`, `surface`, `kernel` or `compile`.
   `tests/invariants/test_no_model_in_the_core.py` enforces it. Model-backed code lives only in
   `author/` and `escalate/backends/`.
2. A commit step journalled `dispatched` and not `observed` is never re-executed, on any path.
   `replay/journal.py` is the one place that rule lives.
3. Every escalation rung proposes; the engine verifies deterministically before acting.
4. `RunResult.classifier_calls` and `llm_calls` are separate and both zero on the ordinary path.
5. Secrets are masked at the boundary (surface, recorder, serialiser), never at call sites.
6. A run never ends in a bare exception; every path yields a typed `RunResult`.
7. Files stay under about 250 lines. One over that is doing two jobs.

## Commands

```bash
make test        # ruff check, ruff format --check, mypy strict, pytest
make lint        # autofix formatting
make up          # PLUMBLINE, the mock bank, on :8081 and :8082
make down
```

Commit messages: conventional commits, body says why, and end with
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` unless the session says otherwise.
Never commit `.env` or anything under `evidence/runs/`.
