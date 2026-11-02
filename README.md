# Handrail

Banks run old screens with no API. Handrail lets an AI model work through a task on those
screens **once**, with a person watching. That run becomes a small typed file, a **capability**.
After that the task is replayed from the file with no model at all, in about a second, and other
AI agents can call it like a function.

When a replay hits a screen it does not recognise, it climbs a ladder: a cheap classifier, then a
model on a short leash that cannot commit anything, then a person who takes over the same
browser. Each rung only suggests. The engine checks before acting.

```
goal ──▶ author (model, once) ──▶ compile ──▶ capability ──▶ verify ──▶ approve
                                                                 │
inputs ───────────────────────────────────▶ replay (no model) ──▶ result
                                                   │ when a check fails
                                                   ▼
                                       classifier → model on a leash → person
```

The target is **PLUMBLINE**, a fake core-banking app in `targetapp/` built to be awkward the way
real ones are: framesets, no ids, no labels, table layout, form tokens that change every page,
two tenants with different markup, and faults you can switch on.

**Where to look**

- [REPORT.md](REPORT.md): the design write-up, seven sections.
- [docs/HANDRAIL-GUIDE.pdf](docs/HANDRAIL-GUIDE.pdf): user guide with screenshots of every command,
  including how to write a new capability.
- [evidence/examples/](evidence/examples/): the real discovery run and seven replays, with logs.
- [docs/DESIGN.md](docs/DESIGN.md), [docs/PLAN.md](docs/PLAN.md), [docs/HANDOFF.md](docs/HANDOFF.md):
  the reasoning, the build order, and where things stand.
- https://billdhawal.github.io/handrail/: two illustrated walkthroughs.

## Setup

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra browser --extra author --extra classify --extra serve --extra ui
uv run playwright install chromium
cp .env.example .env            # put ANTHROPIC_API_KEY in it
```

The key is only used for **discovery**, the Claude classifier, and the model on a leash.
**Replay needs no key.** `TYPESAFE_API_KEY` is optional. The Laya classifier runs on your
machine with no key; it downloads once on first use.

### Run without any live service

```bash
make test        # lint, types, 380 tests, about 45 seconds (five drive a real headless Chromium)
```

No key, no server. Most tests use a scripted fake surface. Seventeen drive a real headless
Chromium against PLUMBLINE started inside the test. The discovery loop runs against a scripted
fake model.

## Demo path

Start the fake bank:

```bash
make up
export BASE_URL=http://127.0.0.1:8081
```

**1. Discover once.** The model drives the bank through a numbered menu of legal moves. It never
sees a selector. Each button press asks you at the terminal whether it is a commit.

```bash
uv run handrail author \
  --goal "Sign on as the operator, search for the member by member number, open the member record, open the hold form for the given share, choose the hold reason, go to the review screen, post the hold, and finish on the result screen." \
  --id plumbline.place_hold --entry http://127.0.0.1:8081/signon --entry-template '{{env.BASE_URL}}/signon' \
  --allow 127.0.0.1:8081 --out capabilities/plumbline-place-hold.authored.json \
  --input operator_id=dcolewell --input password=plumbline-demo --secret password \
  --input member_number=400118 --input share_id=400118-S0001 --input reason=LEGAL --by "$USER"
```

Add `--confirm commit` to answer every prompt up front. The card comes out as a draft.

**2. Replay with no model.** Inputs in, typed result out. Exit code 0 success, 2 business
outcome, 3 recoverable, 4 hard failure.

```bash
uv run handrail replay capabilities/plumbline-place-hold.authored.json \
  --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400118 --input share_id=400118-S0005 --input reason=LEGAL
```

A share that is already on hold is an answer, not a failure:

```bash
uv run handrail replay capabilities/plumbline-place-hold.json \
  --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400226 --input share_id=400226-S0002 --input reason=LEGAL
# BUSINESS_OUTCOME  code=ALREADY_PROCESSED  outcome=already_held
```

**3. Verify and approve.** Three clean replays for three members, each checked against the
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
is placed by the classifier. A rewritten result page comes to you at the console.

```bash
curl -s -X POST http://127.0.0.1:8081/__test__/reset
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"fault":"drift_reword","on_path":"/","once":false}' http://127.0.0.1:8081/__test__/arm_fault
uv run handrail replay capabilities/plumbline-place-hold.authored.json --classifier claude \
  --episodes episodes.db --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400337 --input share_id=400337-S0001 --input reason=LEGAL
uv run handrail episodes episodes.db        # how well the classifier has done so far

curl -s -X POST http://127.0.0.1:8081/__test__/reset
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"fault":"drift_major","on_path":"/","once":false}' http://127.0.0.1:8081/__test__/arm_fault
uv run handrail replay capabilities/plumbline-place-hold.authored.json --classifier claude \
  --console 8765 --headed --input operator_id=dcolewell --input password=plumbline-demo \
  --input member_number=400445 --input share_id=400445-S0001 --input reason=LEGAL
# open http://127.0.0.1:8765/ : take over, fix things in the browser, hand back
```

Add `--bridge anthropic:claude-sonnet-5` for the model on a leash. Use `--classifier laya` for
the on-device classifier. Other faults: `slow`, `dialog`, `maintenance`, `error`, `drift_minor`.

**5. An agent calls it.** One typed MCP tool per approved card. The agent never sees a screen or
a password.

```bash
HANDRAIL_SECRET_PASSWORD=plumbline-demo uv run python examples/agent_caller.py \
  "Place a LEGAL hold on share 400226-S0002 of member 400226"
```

`uv run handrail serve --capabilities capabilities` is the MCP server itself, over stdio.

## See it in a browser

The look comes from the Handrail design system (https://claude.ai/artifact/9jDNM3XJEW5Q5Bf15GZW2H):
`static/tokens.css` is generated from its tokens (one light theme, green brand, brass only for
"needs a person"), `static/ds.css` is its component stylesheet, and `static/app.css` maps the
page classes onto them. Change colours and type in the design system, then regenerate tokens.css.


A shop window onto the same shop. `handrail ui` shows the cards, the runs and the drift in a
page, and lets you start a replay from it. It is not a second engine.

```bash
uv run handrail ui          # http://127.0.0.1:8090, localhost only
uv run handrail ui --port 8090 --capabilities capabilities --evidence evidence/runs \
  --episodes evidence/episodes.db --index evidence/handrail.db
```

The page reads from a small SQLite index (`--index`, default `evidence/handrail.db`) so it stays quick with
thousands of runs; the cards and evidence folders remain the truth, and the index is rebuilt from them
whenever it is missing or `POST /api/index/sync` is called.

- **Home**: the numbers that matter (approved cards, replays, model calls on replay, open escalations) and the cards.
- **Author**: give the model a goal, watch it work, answer the commit prompts with buttons.
- **Catalog**: every capability and where it stands: draft, verified, approved.
- **Runs**: every replay, newest first, filterable, with its evidence.
- **Live**: start a replay, watch the browser, take over when the ladder pauses and hand back.
- **Drift**: which rung found each control, even on runs that passed.
- **A card**, reached from Catalog or Home: **Card** (inputs, outputs, steps), **Versions** (what changed) and **Approve** (verify, then sign).

A replay started from Live is the same engine and writes the same evidence as `handrail replay`.
Model calls on replay stay at zero. The live screen is a stream of screenshots of the headless
browser, about two a second. Tick "Headed" to get a real window you can drive during a takeover.
Authoring from the page needs the same model key as `handrail author`.

### Deploy

`docker compose up` gives the UI on 8080 and the API on 8090, with `capabilities/` and `evidence/`
mounted from the repo. To host the static files elsewhere, set `HANDRAIL_API` (or the
`handrail-api` meta tag in `index.html`) to the API origin and start the API with
`--cors <the UI origin>`. The API binds to localhost unless you pass `--host 0.0.0.0`. There is
no authentication, so put it behind something that has some.

If port 8081 is taken, run the bank on another port and point `BASE_URL` at it. The cards' allowed
hosts must match, or the guard will refuse the page.

## Layout

```
src/handrail/
  schema/     the capability file and the result          surface/   six verbs; browser/ is Playwright
  replay/     engine, journal, screens, rungs/ (ladder)    kernel/    evidence, signatures, episodes, baton
  author/     the model's tools, the guard, the leash, the recorder
  compile/    trace to card; verify gate; approve          escalate/  questions, ports, three classifiers
  serve/      console, MCP server, web/ (the UI)                cli.py     replay, observe, author, verify, episodes, approve, serve
capabilities/ three cards for PLUMBLINE       targetapp/  PLUMBLINE       tests/  380
```

Rules that do not bend are in [CLAUDE.md](CLAUDE.md). The terminal surface and macOS
accessibility surface are designed and not built; see REPORT.md, section 7.
