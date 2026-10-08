"""The two counter windows for authoring: book an evening, and hold the tasting.

``handrail replay`` is for the daily customer. These two are for the person
who puts a dish on the menu. ``author`` seats a model at a real browser with
the three-line card, writes the book as it goes, and hands the book to the
recipe writer; the card comes back in draft, or a list of holes. ``verify``
takes a draft card and three orders, cooks each from a cold kitchen, asks
the record store whether the hold really exists, and marks the card
verified when all three plates are clean.

The owner's "yes" on a commit is a terminal prompt here. A non-interactive
run may pass ``--confirm commit --by NAME`` to answer in advance, and the
name is written into the card as the person who confirmed; do not lie to it.

This is where the model is constructed, once, from a provider string, and
handed to ``agent.author``. Nothing below ``author/`` ever constructs one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

from ..compile.compiler import CompileError, Source, compile_trace
from ..compile.verify import Check, verify
from ..kernel.evidence import Recorder, new_run_id
from ..schema.capability import Capability
from ..schema.effects import EffectClass
from ..schema.results import RunResult
from .middleware import Confirm, Decision, Guard, Proposal
from .recorder import TraceRecorder
from .tools import Session


def load_dotenv(path: Path = Path(".env")) -> None:
    """KEY=VALUE lines into the environment, never overriding what is already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key, value.strip().strip("'\""))


def pairs(values: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in values or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise SystemExit(f"expected k=v, got {item!r}")
        out[key] = value
    return out


def terminal_confirm(by: str, preset: str | None) -> Confirm:
    """Ask the owner at the terminal, or answer with the preset given up front."""

    async def confirm(proposal: Proposal) -> Decision:
        answer = preset
        if answer is None:
            what = f"{proposal.verb} {proposal.control.role} {proposal.control.name!r}"
            print(f"\ncommit? row {proposal.index}: {what}", end="")
            print("  [c]ommit / [n]avigate / [s]tage / [d]eny: ", end="")
            sys.stdout.flush()
            answer = {"c": "commit", "n": "navigate", "s": "stage"}.get(
                sys.stdin.readline().strip().lower()[:1], "deny"
            )
        effect = None if answer == "deny" else EffectClass(answer)
        return Decision(effect, by)

    return confirm


async def author_command(args: argparse.Namespace, model: Any = None) -> int:
    from langchain.chat_models import init_chat_model

    from ..surface.browser.queries import BrowserAuthoring
    from ..surface.browser.surface import BrowserSurface

    load_dotenv()
    values = pairs(args.input)
    secrets = set(args.secret or [])
    recorder = Recorder(new_run_id("author"), root=Path(args.evidence))
    for name in secrets & values.keys():
        recorder.add_secret(values[name])
    surface = BrowserSurface(args.allow, headless=not args.headed)
    env = {**os.environ, **pairs(args.env)}
    session = Session(surface, inputs=values, env=env)
    book, confirm = TraceRecorder(recorder), terminal_confirm(args.by, args.confirm)
    from .agent import author

    try:
        await surface.open(args.entry)
        guard = Guard(session, BrowserAuthoring(surface.page), confirm, book)
        chat = model or init_chat_model(args.model)
        result = await author(chat, guard, args.goal, args.max_turns)
    finally:
        await surface.close()
    print(
        f"turns={len(result.trace)}  model_calls={result.model_calls}  "
        f"finished={result.finished}  outcome={result.outcome}  evidence={recorder.dir}"
    )
    source = Source(
        id=args.id,
        title=args.goal,
        entry=args.entry_template or args.entry,
        inputs=[{"name": n, **({"sensitivity": "secret"} if n in secrets else {})} for n in values],
        values=values,
        screens=result.screens,
        trace=result.trace,
        allowed_hosts=list(args.allow),
    )
    try:
        capability = compile_trace(source)
    except CompileError as exc:
        print("not compiled:")
        for reason in exc.reasons:
            print(f"  - {reason}")
        return 4
    Path(args.out).write_text(capability.model_dump_json(indent=2, exclude_none=True) + "\n")
    print(
        f"compiled {capability.ref}: {len(capability.steps)} steps, "
        f"{len(capability.screens)} screens, draft -> {args.out}"
    )
    return 0


def plumbline_check(base_url: str) -> Check:
    """Ask PLUMBLINE's record store whether the share is on hold. Never the screen."""

    async def check(inputs: dict[str, Any], result: RunResult) -> bool:
        with urllib.request.urlopen(f"{base_url}/__test__/share/{inputs['share_id']}") as resp:
            return bool(json.load(resp).get("status") == "HOLD")

    return check


async def verify_command(args: argparse.Namespace) -> int:
    from ..surface.browser.surface import BrowserSurface

    load_dotenv()
    capability = Capability.model_validate_json(Path(args.capability).read_text())
    env = {**os.environ, **pairs(args.env)}
    trials = [pairs(t.split(",")) for t in args.trial]
    root = Path(args.evidence)
    verdict = await verify(
        capability,
        trials,
        lambda: BrowserSurface(capability.safety.allowed_hosts, headless=not args.headed),
        lambda n: Recorder(new_run_id(f"verify{n}"), root=root),
        plumbline_check(env["BASE_URL"]),
        env,
    )
    for number, plate in enumerate(verdict.plates, start=1):
        print(f"plate {number}: {'clean' if plate.clean else plate.reason}")
    if not verdict.verified:
        print("stays in draft: " + "; ".join(verdict.reasons))
        return 4
    Path(args.capability).write_text(
        verdict.capability.model_dump_json(indent=2, exclude_none=True) + "\n"
    )
    ref = verdict.capability.ref
    print(f"verified {ref} after {len(trials)} clean plates -> {args.capability}")
    return 0


def register(sub: Any) -> None:
    a = sub.add_parser("author", help="let a model work the task out once, then compile it")
    a.add_argument("--goal", required=True)
    a.add_argument("--entry", required=True, help="the URL to open")
    a.add_argument("--entry-template", help="what the card says, e.g. {{env.BASE_URL}}/signon")
    a.add_argument("--id", required=True, help="capability id, e.g. plumbline.place_hold")
    a.add_argument("--allow", action="append", default=[], metavar="HOST:PORT")
    a.add_argument("--input", action="append", metavar="NAME=VALUE")
    a.add_argument("--secret", action="append", metavar="NAME", help="an input that is a secret")
    a.add_argument("--env", action="append", metavar="NAME=VALUE")
    a.add_argument("--model", default="anthropic:claude-sonnet-5")
    a.add_argument("--confirm", choices=["commit", "navigate", "stage", "deny"])
    a.add_argument("--by", default=os.environ.get("USER", "owner"), help="who confirms commits")
    a.add_argument("--max-turns", type=int, default=40)
    a.add_argument("--out", required=True)
    a.add_argument("--evidence", default="evidence/runs")
    a.add_argument("--headed", action="store_true")
    a.set_defaults(run=author_command)

    v = sub.add_parser("verify", help="three clean replays with an independent check")
    v.add_argument("capability")
    v.add_argument("--trial", action="append", required=True, metavar="k=v,k=v")
    v.add_argument("--env", action="append", metavar="NAME=VALUE")
    v.add_argument("--evidence", default="evidence/runs")
    v.add_argument("--headed", action="store_true")
    v.set_defaults(run=verify_command)
