# Handrail

A computer-use system for one specific bet: **being able to do a task once tells you nothing
about doing it a hundred times.**

A model works out how to do a task in some application, once. That run becomes a typed,
versioned, reviewable **capability**. From then on it replays deterministically with no model in
the loop. When a replay check fails, the system climbs a ladder — a cheap closed-set classifier,
then a bounded model excursion, then a person on the same live session — and every rung only
proposes; the engine verifies before it acts.

```
goal ──▶ author (model, once) ──▶ trace ──▶ compile ──▶ capability ──▶ verify ──▶ approve
                                                                          │
inputs ───────────────────────────────────────────────────▶ replay (no model) ──▶ result
                                                              │ on a failed check
                                                              ▼
                                                   classifier → bridge → human
```

- [docs/DESIGN.md](docs/DESIGN.md) — the architecture and the reasoning behind each part.
- [docs/PLAN.md](docs/PLAN.md) — the build order, file by file, with what each file teaches.

## Setup

```bash
uv sync                      # the core: pydantic only
uv run pytest -q             # 50 passed
```

Surfaces and model backends are opt-in extras, so a replay installs none of them:

```bash
uv sync --extra browser      # playwright
uv sync --extra terminal     # py3270
uv sync --extra author       # langchain, langchain-typesafe
uv sync --extra classify     # typesafe-sdk
```

`.env` holds `ANTHROPIC_API_KEY` (authoring) and `TYPESAFE_API_KEY` (the classifier rung).
Replay needs neither.

## Status

Milestone 0 of 8: the schema and the first invariants. See the plan for what comes next.
