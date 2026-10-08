"""The counter where other agents order: one line on the menu per approved dish, nothing else.

An agent that wants a hold placed does not get into the kitchen, does not
see the screens, does not hold the operator's password. It sees a menu with
one typed line per approved capability, orders by filling in the card's
inputs, and gets back a receipt that says what happened and, most of all,
whether it may try again. "Already held" is an answer, not a failure, and
the receipt says so; an agent that retries it is an agent that did not read
the receipt.

Rules this file keeps:

- Only ``approved`` cards are served. A verified card is not on the menu; a
  draft never is. The directory is read at start, and each card not served
  is logged with the reason.
- Secret inputs are never on the tool's schema. They are filled from the
  environment (``HANDRAIL_SECRET_<NAME>``) at call time; if one is missing,
  the receipt says INVALID_INPUT and nothing is touched.
- The receipt is data: category, code, outcome, outputs, retryable, run id,
  evidence directory. No screen text, no screenshot, no model output.

The server is MCP over stdio by default, so any MCP-speaking agent can be
pointed at ``handrail serve --capabilities DIR``. Stdout is the wire: anything
meant for a person goes to stderr, or the first greeting corrupts the
handshake and the client sees "Connection closed". It did, once.
"""

from __future__ import annotations

import argparse
import inspect
import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from ..kernel.evidence import Recorder, new_run_id
from ..replay.engine import ReplayEngine
from ..schema.capability import Capability, InputSpec
from ..schema.results import RunResult

Runner = Callable[[Capability, dict[str, Any]], Awaitable[RunResult]]

PYTHON_TYPES = {"string": str, "number": float, "boolean": bool}


def tool_name(capability: Capability) -> str:
    return capability.id.replace(".", "_").replace("-", "_")


def say(text: str) -> None:
    """Stdout is the MCP transport. Everything a person should read goes to stderr."""
    print(text, file=sys.stderr)


def load_cards(directory: Path, log: Callable[[str], None] = say) -> list[Capability]:
    """Every approved card in the directory. Each one left off the menu is said out loud."""
    served: list[Capability] = []
    for path in sorted(directory.glob("*.json")):
        try:
            card = Capability.model_validate_json(path.read_text())
        except ValueError as exc:
            log(f"{path.name}: not a capability: {str(exc)[:80]}")
            continue
        if card.lifecycle.state != "approved":
            log(f"{path.name}: {card.lifecycle.state}, not approved; not served")
            continue
        served.append(card)
    return served


def _parameter(spec: InputSpec) -> inspect.Parameter:
    annotation: Any = (
        Literal[tuple(spec.enum or ())] if spec.type == "enum" else PYTHON_TYPES[spec.type]
    )
    default = inspect.Parameter.empty if spec.required else None
    return inspect.Parameter(
        spec.name, inspect.Parameter.KEYWORD_ONLY, annotation=annotation, default=default
    )


def public_inputs(capability: Capability) -> list[InputSpec]:
    return [i for i in capability.inputs if i.sensitivity != "secret"]


def secrets_from_env(
    capability: Capability, env: dict[str, str]
) -> tuple[dict[str, str], list[str]]:
    """The secret inputs, from HANDRAIL_SECRET_<NAME>; and the names of any that are missing."""
    found: dict[str, str] = {}
    missing: list[str] = []
    for spec in capability.inputs:
        if spec.sensitivity == "secret":
            value = env.get(f"HANDRAIL_SECRET_{spec.name.upper()}")
            if value:
                found[spec.name] = value
            else:
                missing.append(spec.name)
    return found, missing


def receipt(result: RunResult, evidence: str | None = None) -> dict[str, Any]:
    return {
        "category": result.category.value,
        "code": result.code.value,
        "outcome": result.outcome,
        "outputs": result.outputs,
        "retryable": result.retryable,
        "run_id": result.run_id,
        "evidence": evidence,
        "error": result.error.message if result.error else None,
    }


def make_tool(capability: Capability, runner: Runner, env: dict[str, str]) -> Callable[..., Any]:
    """One tool: the card's public inputs as its signature, the receipt as its answer."""

    async def tool(**kwargs: Any) -> dict[str, Any]:
        secrets, missing = secrets_from_env(capability, env)
        if missing:
            return {
                "category": "HARD_FAILURE",
                "code": "INVALID_INPUT",
                "outcome": None,
                "outputs": {},
                "retryable": False,
                "run_id": None,
                "evidence": None,
                "error": f"secret inputs not configured on the server: {missing}",
            }
        inputs = {k: v for k, v in kwargs.items() if v is not None} | secrets
        result = await runner(capability, inputs)
        return receipt(result)

    params = [_parameter(spec) for spec in public_inputs(capability)]
    tool.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    tool.__annotations__ = {p.name: p.annotation for p in params} | {"return": dict[str, Any]}
    tool.__name__ = tool_name(capability)
    tool.__doc__ = capability.title
    return tool


def build_server(
    capabilities: list[Capability], runner: Runner, env: dict[str, str] | None = None
) -> Any:
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "handrail",
        instructions=(
            "Each tool replays one approved capability on a live application with no model in "
            "the loop. Read the receipt: a BUSINESS_OUTCOME is an answer, not a failure; retry "
            "only when retryable is true."
        ),
    )
    for card in capabilities:
        outcomes = ", ".join(f"{k} ({v.category.value})" for k, v in card.outcomes.items())
        server.add_tool(
            make_tool(card, runner, env or dict(os.environ)),
            name=tool_name(card),
            description=f"{card.title} Outcomes: {outcomes}.",
        )
    return server


def browser_runner(evidence_root: Path, env: dict[str, str]) -> Runner:
    """The default kitchen: a headless browser per call, the engine with no referee."""

    async def run(capability: Capability, inputs: dict[str, Any]) -> RunResult:
        from ..surface.browser.surface import BrowserSurface

        surface = BrowserSurface(capability.safety.allowed_hosts)
        recorder = Recorder(new_run_id("mcp"), root=evidence_root)
        try:
            return await ReplayEngine(surface, recorder, env=env).run(capability, inputs)
        finally:
            await surface.close()

    return run


# -- the two commands -------------------------------------------------------------


async def approve_command(args: argparse.Namespace) -> int:
    from ..compile.approve import NotApprovable, approve

    path = Path(args.capability)
    try:
        card = approve(Capability.model_validate_json(path.read_text()), args.by)
    except NotApprovable as exc:
        print(f"not approved: {exc}")
        return 4
    path.write_text(card.model_dump_json(indent=2, exclude_none=True) + "\n")
    print(f"approved {card.ref} by {card.lifecycle.approved_by} at {card.lifecycle.approved_at}")
    return 0


async def serve_command(args: argparse.Namespace) -> int:
    from ..author.run import load_dotenv

    load_dotenv()
    env = dict(os.environ)
    cards = load_cards(Path(args.capabilities))
    if not cards:
        say("nothing approved to serve")
        return 4
    server = build_server(cards, browser_runner(Path(args.evidence), env), env)
    say(f"serving {len(cards)} tool(s): {', '.join(tool_name(c) for c in cards)}")
    await server.run_stdio_async()
    return 0


def register(sub: Any) -> None:
    a = sub.add_parser("approve", help="a named person puts a verified card on the menu")
    a.add_argument("capability")
    a.add_argument("--by", required=True, help="the person's name")
    a.set_defaults(run=approve_command)

    s = sub.add_parser("serve", help="MCP server: one tool per approved capability, over stdio")
    s.add_argument("--capabilities", default="capabilities", help="directory of capability files")
    s.add_argument("--evidence", default="evidence/runs")
    s.set_defaults(run=serve_command)
