"""The counter window: one command in, one typed answer out.

A customer at a counter does not get to see the kitchen. They say what they
want, hand over the form, and get back a receipt that says what happened. This
is that window for Handrail: ``handrail replay`` takes a capability file and
its inputs, runs it with no model in the loop, and prints a receipt that names
the outcome, the outputs, and the two model counters, which are zero.

``handrail observe`` is the window for the person writing a capability by
hand: it opens a page and prints what the waiter sees, the screen signature
and the numbered menu, so the signatures in a capability file come from a live
walk and never from guesswork.

The exit code is the outcome category, so a shell script can tell "the bank
said no" from "something broke" without parsing anything:
0 success, 2 business outcome, 3 recoverable, 4 hard failure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from .kernel.evidence import Recorder, new_run_id
from .kernel.signature import take
from .replay.engine import ReplayEngine
from .replay.journal import Journal
from .schema.capability import Capability
from .schema.errors import OutcomeCategory
from .schema.results import RunResult

EXIT_CODES = {
    OutcomeCategory.SUCCESS: 0,
    OutcomeCategory.BUSINESS_OUTCOME: 2,
    OutcomeCategory.RECOVERABLE: 3,
    OutcomeCategory.HARD_FAILURE: 4,
}


def pairs(values: list[str] | None) -> dict[str, str]:
    """``k=v`` arguments into a dict; a value may itself contain ``=``."""
    out: dict[str, str] = {}
    for item in values or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise SystemExit(f"expected k=v, got {item!r}")
        out[key] = value
    return out


def referee(name: str | None) -> Any:
    """The classifier rung's backend, by name. None means the rung is never climbed."""
    if not name:
        return None
    if name == "claude":
        from .escalate.backends.claude import ClaudeClassifier

        return ClaudeClassifier()
    if name == "jev":
        from .escalate.backends.jev import JevClassifier

        return JevClassifier()
    if name == "laya":
        from .escalate.backends.laya import LayaClassifier

        return LayaClassifier()
    raise SystemExit(f"unknown classifier {name!r}; use claude, jev or laya")


def notebook(path: str | None) -> Any:
    if not path:
        return None
    from .kernel.episodes import Episodes

    return Episodes(Path(path))


def receipt(result: RunResult, evidence_dir: Path) -> str:
    lines = [
        f"{result.category.value}  code={result.code.value}  outcome={result.outcome}",
        f"outputs={json.dumps(result.outputs)}",
        f"llm_calls={result.llm_calls}  classifier_calls={result.classifier_calls}"
        f"  drift={result.drift.first_choice}/{result.drift.steps_resolved} first-choice",
        f"steps={len(result.steps)}  duration_ms={result.duration_ms}  evidence={evidence_dir}",
    ]
    if result.error:
        lines.append(f"error: {result.error.message}")
    return "\n".join(lines)


async def replay(args: argparse.Namespace) -> int:
    from .author.run import load_dotenv
    from .surface.browser.surface import BrowserSurface

    load_dotenv()  # the referee's key, if a referee was asked for; replay itself needs none
    capability = Capability.model_validate_json(Path(args.capability).read_text())
    env = {**os.environ, **pairs(args.env)}
    recorder = Recorder(new_run_id("replay"), root=Path(args.evidence))
    journal_path = Path(args.journal) if args.journal else recorder.dir / "journal.jsonl"
    journal = Journal.load(journal_path)
    surface = BrowserSurface(capability.safety.allowed_hosts, headless=not args.headed)
    engine = ReplayEngine(
        surface,
        recorder,
        env=env,
        settle_timeout_ms=args.timeout_ms,
        classifier=referee(args.classifier),
        episodes=notebook(args.episodes),
    )
    try:
        result = await engine.run(capability, pairs(args.input), journal)
    finally:
        await surface.close()
    print(receipt(result, recorder.dir))
    return EXIT_CODES[result.category]


async def observe(args: argparse.Namespace) -> int:
    from .surface.browser.operations import render
    from .surface.browser.surface import BrowserSurface

    surface = BrowserSurface(args.allow, headless=not args.headed)
    try:
        await surface.open(args.url)
        seen = await surface.observe()
    finally:
        await surface.close()
    print(f"signature={take(seen.structure).value}  paths={len(seen.structure)}")
    print(render(seen.operations))
    return 0


async def episodes(args: argparse.Namespace) -> int:
    from .kernel.episodes import Episodes

    book = Episodes(Path(args.path))
    rows = book.rows()
    print(f"{len(rows)} episodes in {args.path}")
    for row in rows[-10:]:
        print(
            f"  {row['run_id']}  {row['step_id'] or '-':24} {row['question'] or '-':14} "
            f"{row['chosen'] or '-':14} conf={row['confidence'] or 0:.2f} "
            f"accepted={bool(row['accepted'])} held={row['held']}"
        )
    print("calibration (accepted verdicts with a settled outcome):")
    print("  confidence   verdicts   held   rate")
    for b in book.calibration(args.question):
        rate = f"{b.rate:.2f}" if b.count else "   -"
        print(f"  {b.low:.1f} to {b.high:.1f}   {b.count:8d}   {b.held:4d}   {rate}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="handrail", description=__doc__.split("\n\n")[1])
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("replay", help="replay a capability with no model in the loop")
    r.add_argument("capability", help="path to a capability JSON file")
    r.add_argument("--input", action="append", metavar="NAME=VALUE", help="one input; repeatable")
    r.add_argument("--env", action="append", metavar="NAME=VALUE", help="override an env binding")
    r.add_argument("--journal", help="journal shared across runs: a step in doubt stays in doubt")
    r.add_argument("--evidence", default="evidence/runs", help="where run records go")
    r.add_argument("--timeout-ms", type=int, default=8000, help="settle timeout per step")
    r.add_argument("--headed", action="store_true", help="show the browser")
    r.add_argument("--classifier", choices=["claude", "jev", "laya"], help="rung one's referee")
    r.add_argument("--episodes", help="SQLite notebook for every escalation, e.g. episodes.db")
    r.set_defaults(run=replay)

    e = sub.add_parser("episodes", help="the referee's record: calibration by confidence")
    e.add_argument("path", nargs="?", default="episodes.db")
    e.add_argument("--question", help="one question only, e.g. which_screen")
    e.set_defaults(run=episodes)

    o = sub.add_parser("observe", help="print what the browser surface sees on a page")
    o.add_argument("url")
    o.add_argument("--allow", action="append", default=[], metavar="HOST:PORT", help="allowed host")
    o.add_argument("--headed", action="store_true")
    o.set_defaults(run=observe)

    from .author.run import register

    register(sub)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return int(asyncio.run(args.run(args)))


if __name__ == "__main__":
    sys.exit(main())
