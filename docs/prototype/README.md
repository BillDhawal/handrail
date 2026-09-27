# Handrail

An LLM drives a legacy banking UI **once**. The successful run compiles into a
typed, versioned **capability** — a small readable JSON file. From then on the
flow replays deterministically, with **zero model calls**, returning typed
outputs and a structured outcome.

The model discovers. The artifact is the reusable capability. Deterministic
replay is how an agent invokes it in production.

```
goal (plain English)                         inputs (member #, share #, …)
      │                                                │
      ▼                                                ▼
┌───────────────┐   trace   ┌──────────┐   ┌─────────────────┐   outcome + outputs
│   DISCOVERY   │ ────────▶ │ COMPILER │──▶│     REPLAY      │─▶ + evidence + drift
│  (LLM, once)  │           │ (no LLM) │   │ (no LLM, ever)  │
└───────────────┘           └──────────┘   └─────────────────┘
```

- **[REPORT.md](REPORT.md)** — the design write-up: architecture, artifact
  schema, determinism, multi-tenancy, escalation, safety, and what I cut.
- **[evidence/](evidence/)** — three real discovery runs and eleven replays,
  all machine-produced.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the same system in plain
  language, component by component.
- **[TESTING.md](TESTING.md)** — every way to exercise it by hand.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run playwright install chromium
cp .env.example .env        # then edit
```

`.env` (gitignored) holds two things:

```
ANTHROPIC_API_KEY=sk-ant-...       # only `handrail discover` needs this
PLUMBLINE_PASSWORD=plumbline-demo  # read at replay; never recorded in an artifact
```

**Everything except discovery runs without an API key.** Discovery is the one
step that cannot be faked, so it refuses rather than simulating a trace.

## The target application

There is no real bank to automate, so this repo ships one: **PLUMBLINE**, a mock
core-banking product run by two fictional credit unions. It is deliberately
hostile in the ways the brief describes — framesets, table layouts, no element
ids, no test hooks, no label associations, a per-render form token, and terse
mainframe messages. It also exposes a test endpoint for injecting timeouts,
maintenance pages and dialogs, so recoverable conditions can be demonstrated on
demand rather than waited for.

```bash
make up      # Quarrybrook on :8081, Fernhollow on :8082
make down
```

Sign on as `dcolewell` / `plumbline-demo` (supervisor) or `mrivas` (teller).

## Demo path

```bash
make up && make demo
```

Runs the whole thread: a live discovery run (or an honest refusal without a
key), then the committed capability replayed across all four outcome categories,
then the same capability at a second institution through a tenant overlay, then
a rendered report. Every replay prints `llm_calls=0`.

The exact commands, if you would rather drive them yourself:

```bash
# 1. An LLM drives the real UI and records what worked.
uv run handrail discover --job place-hold --tenant quarrybrook \
  --base-url http://127.0.0.1:8081 \
  --input operator_id=dcolewell --input "password={{env.PLUMBLINE_PASSWORD}}" \
  --input member_number=400118 --input share_id=400118-S0001 --input reason=LEGAL \
  --out trace.json

# 2. Compile that run into a capability. Pure code - no model.
uv run handrail compile trace.json \
  --id plumbline.place_share_hold --version 1.0.0 --job place-hold \
  --out capability.json

# 3. Replay it. No model, different inputs, typed outputs back.
uv run handrail replay capability.json --tenant quarrybrook \
  --input operator_id=dcolewell --input member_number=400118 \
  --input share_id=400118-S0001 --input reason=LEGAL --input notes=None
```

Step 3 prints the `RunResult` as JSON on stdout and a summary on stderr, so
`... | jq .outputs` works. **Exit codes mirror the outcome taxonomy**, so a
scheduler can tell "the bank said no" from "the automation broke" without
parsing anything:

| exit | meaning |
|---|---|
| 0 | `SUCCESS` |
| 2 | `BUSINESS_OUTCOME` — a legitimate answer, not a crash |
| 3 | `RECOVERABLE` — retry or intervene |
| 4 | `HARD_FAILURE` — stop, surface a debuggable error |
| 5 | refused up front (policy, surface, binding, compile) |
| 64 | usage |

Add `--headed --slow-mo 400` to any of these to watch the browser drive.

## Is it working?

```bash
make up && make verify
```

Twenty checks and one verdict: the test suite, live browser tests, all four
outcome categories, all three catalogued flows, both institutions, the
capability compiled from a real discovery run replaying, evidence rendering, and
a scan proving no credential reached the evidence. A skip is never counted as a pass.

## Human takes over

```bash
uv run python scripts/console_demo.py --headed --slow-mo 400
```

Opens an operator console at <http://127.0.0.1:8090> while a replay drives the
bank. You can pause it, take control of **the same live session**, do the manual
steps yourself, and hand control back. The ownership timeline records who was
driving at every moment.

## When the bank drifts

```bash
uv run handrail replay artifacts/capabilities/place-hold-quarrybrook.json \
  --tenant fernhollow --max-llm-calls 12 \
  --input operator_id=dcolewell --input member_number=400118 \
  --input share_id=400118-S0001 --input reason=LEGAL --input notes=None
```

Replay is model-free by default, and stays that way until a deterministic check
fails. With a budget, a **supervisor** may then drive the browser for a few
turns to reach the next checkpoint the capability declares, or name a declared
outcome it recognises. The engine re-evaluates every claim itself before
trusting it, counts every model call, and writes the excursion to the run's
evidence as `bridge_<n>.trace.json`. `llm_calls` in the result says exactly what
was spent; a budget of zero (the default) is today's guarantee, unchanged.

The model goes before the human: an operator is only escalated to for a failure
the supervisor could not fix. A bridge is denied risky actions of its own unless
the run was started with `--confirm-risky`. It never rewinds across a risky step
that has already run.

## Seeing what happened

```bash
make viewer                                   # a browsable page over all runs
uv run handrail report run <evidence-dir>     # one replay, as markdown
uv run handrail report trace <trace.json>     # one discovery run, turn by turn
```

## The three flows

The job catalogue defines three, and all three were discovered live, compiled
and replayed. Each has a committed trace and capability.

| Job | What it does | Outcomes demonstrated |
|---|---|---|
| `place-hold` | sign on → find member → open share → post a hold → read the confirmation | all four categories |
| `member-inquiry` | sign on → look up a member → read back name, branch, balances | SUCCESS with typed outputs, BUSINESS_OUTCOME |
| `signon-smoke` | sign on → confirm the desk is reachable | SUCCESS, HARD_FAILURE |

```bash
uv run handrail replay artifacts/capabilities/member-inquiry.json --tenant quarrybrook \
  --input operator_id=dcolewell --input search_value=400118 --input search_by=MBRNO | jq .outputs
# { "member_name": "Alvarez, Marisol", "branch": "QB-01",
#   "regular_share_balance": "$42,100.50", "draft_balance": "$880.25" }
```

Worth comparing: search for `999999` and the inquiry returns `BUSINESS_OUTCOME`
(exit 2), while the *same screen text* in `place-hold` is a `HARD_FAILURE`
(exit 4). In one flow the member's existence is the question; in the other it is
a precondition the caller supplied. The outcome belongs to the job, not the
screen.

## Other commands

```bash
make test     # ruff, mypy, pytest
make cov      # coverage
make lint     # autofix
```

## Layout

```
src/handrail/
  discovery/   the LLM loop: three tools, locator probing at the moment of success
  compile/     trace -> capability. Pure code; refuses rather than guessing
  replay/      the deterministic engine. Audited to be unable to reach a model
  surface/     the only code that touches a browser, behind a small protocol
  kernel/      policy, redaction, control ownership, evidence
  tenancy/     per-institution overlays
  jobs/        the job catalogue and outcome mappings
  report/      human-readable write-ups
  cli.py
targetapp/     PLUMBLINE, the deliberately hostile mock bank
artifacts/     committed traces, capabilities and overlays for all three flows
evidence/      three real discovery runs and eleven replays
```
