# Handrail

A computer-use system built on one bet: **doing a task once tells you nothing about doing it a
hundred times.**

A model works out how to do a task in a legacy application, once. That run compiles into a
typed, versioned, reviewable **capability**. From then on it replays deterministically with no
model in the loop. When a replay check fails, a ladder is climbed: a closed-set classifier, then
a bounded model excursion with commits denied, then a person on the same live session. Every
rung only proposes; the engine verifies before it acts.

```
goal ──▶ author (model, once) ──▶ trace ──▶ compile ──▶ capability ──▶ verify ──▶ approve
                                                                          │
inputs ───────────────────────────────────────────────────▶ replay (no model) ──▶ result
                                                              │ on a failed check
                                                              ▼
                                                   classifier → bridge → human
```

The target is **PLUMBLINE**, a mock core-banking app in `targetapp/` built to be hostile the way
real ones are: framesets, no ids, no labels, table layout, per-render form tokens, terse
mainframe messages, two tenants with different markup, faults armed on demand.

- [REPORT.md](REPORT.md) — the design write-up (the seven headings the brief asks for).
- [evidence/examples/](evidence/examples/) — the real discovery run and six replays, with logs.
- [docs/DESIGN.md](docs/DESIGN.md), [docs/PLAN.md](docs/PLAN.md), [docs/HANDOFF.md](docs/HANDOFF.md)
  — the architecture, the build order, and where things stand.
- [Handrail in Five Pictures](https://billdhawal.github.io/handrail/five-pictures.html) and
  [Handrail, as built](https://billdhawal.github.io/handrail/as-built.html) — illustrated,
  animated walkthroughs.

## Setup

Python 3.12 and [uv](https://docs.astral.sh/uv/). Everything beyond the core is an opt-in extra.

```bash
uv sync --extra browser --extra author --extra classify --extra serve
uv run playwright install chromium
cp .env.example .env            # then put your key in it
```

`.env` holds `ANTHROPIC_API_KEY`. It is needed by **authoring**, the **Claude referee** and the
**scout**. Replay needs no key at all. `TYPESAFE_API_KEY` is optional (the Jev referee). The
Laya referee runs on-device and needs no key; its checkpoint downloads on first use.

### Running without live services

```bash
make test        # ruff, ruff format --check, mypy strict, pytest: 332 tests, about 15 seconds
```

The suite needs no key and no server: the engine runs on a scripted surface, seventeen tests
drive a real headless Chromium against PLUMBLINE started inside the test, and the authoring
loop runs with a scripted fake model. Replay against the mock bank needs only `make up`.

## Demo path

Start the mock bank (two tenants, ports 8081 and 8082):

```bash
make up
export BASE_URL=http://127.0.0.1:8081
```

**1. Discover once.** The model drives the bank through a numbered menu of legal operations
and never sees a selector. Every button press asks you at the terminal whether it is a commit.

```bash
uv run handrail author \
  --goal "Sign on as the operator, search for the member by member number, open the member record, open the hold form for the given share, choose the hold reason, go to the review screen, post the hold, and finish on the result screen." \
  --id plumbline.place_hold --entry http://127.0.0.1:8081/signon --entry-template '{{env.BASE_URL}}/signon' \
  --allow 127.0.0.1:8081 --out capabilities/plumbline-place-hold.authored.json \
  --input operator_id=dcolewell --input password=plumbline-demo --secret password \
  --input member_number=400118 --input share_id=400118-S0001 --input reason=LEGAL --by "$USER"
```

Add `--confirm commit` to answer every prompt up front. The compiled card is a draft.

**2. Replay, no model.** Inputs in, typed result out. Exit code 0 success, 2 business outcome,
3 recoverable, 4 hard failure.

```bash
uv run handrail replay capabilities/plumbline-place-hold.authored.json \
  --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400118 --input share_id=400118-S0005 --input reason=LEGAL
```

A share that is already on hold is an answer, not a failure (the hand-written card declares it):

```bash
uv run handrail replay capabilities/plumbline-place-hold.json \
  --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400226 --input share_id=400226-S0002 --input reason=LEGAL
# BUSINESS_OUTCOME  code=ALREADY_PROCESSED  outcome=already_held
```

**3. Verify and approve.** Three clean replays for three members, each confirmed against the
record store, then a named person signs.

```bash
W=operator_id=dcolewell,password=plumbline-demo
uv run handrail verify capabilities/plumbline-place-hold.authored.json --env BASE_URL=$BASE_URL \
  --trial "$W,member_number=400118,share_id=400118-S0005,reason=LEGAL" \
  --trial "$W,member_number=400337,share_id=400337-S0001,reason=LEGAL" \
  --trial "$W,member_number=400445,share_id=400445-S0001,reason=FRAUD_REVIEW"
uv run handrail approve capabilities/plumbline-place-hold.authored.json --by "$USER"
```

**4. Escalation.** Change the bank under the card and watch the ladder. A reworded result line
is placed by the referee; a rewritten result page goes to you at the console.

```bash
curl -s -X POST http://127.0.0.1:8081/__test__/reset
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"fault":"drift_reword","on_path":"/","once":false}' http://127.0.0.1:8081/__test__/arm_fault
uv run handrail replay capabilities/plumbline-place-hold.authored.json --classifier claude \
  --episodes episodes.db --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400337 --input share_id=400337-S0001 --input reason=LEGAL
uv run handrail episodes episodes.db        # the referee's calibration table

curl -s -X POST http://127.0.0.1:8081/__test__/reset
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"fault":"drift_major","on_path":"/","once":false}' http://127.0.0.1:8081/__test__/arm_fault
uv run handrail replay capabilities/plumbline-place-hold.authored.json --classifier claude \
  --console 8765 --headed --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400445 --input share_id=400445-S0001 --input reason=LEGAL
# open http://127.0.0.1:8765/ : take over, fix things in the headed browser, hand back
```

Add `--bridge anthropic:claude-sonnet-5` for rung two, the scout. Use `--classifier laya` for
the on-device referee. Other faults: `slow`, `dialog`, `maintenance`, `error`, `drift_minor`.

**5. An agent orders.** One typed MCP tool per approved card; the agent never sees a screen or
a password.

```bash
HANDRAIL_SECRET_PASSWORD=plumbline-demo uv run python examples/agent_caller.py \
  "Place a LEGAL hold on share 400226-S0002 of member 400226"
```

`uv run handrail serve --capabilities capabilities` is the MCP server itself, over stdio.

## Layout

```
src/handrail/
  schema/     the artifact and the result contract            surface/   six verbs; browser/ is Playwright
  replay/     engine, journal, screens, rungs/ (the ladder)    kernel/    evidence, signatures, episodes, the baton
  author/     the model's three-line card, the guard, the scout, the recorder
  compile/    trace to card; the verify gate; approve          escalate/  the questions, the ports, three referees
  serve/      the console and the MCP server                   cli.py     replay, observe, author, verify, episodes, approve, serve
capabilities/ two cards for PLUMBLINE            targetapp/  PLUMBLINE          tests/  332, invariants first
```

Rules that do not bend are in [CLAUDE.md](CLAUDE.md). Milestone 4 (a 3270 terminal surface) and
8 (macOS accessibility) are designed and not built; see REPORT.md, section 7.
