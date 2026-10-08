"""An agent orders from the counter. It never sees the screens; it reads the receipt.

Run the mock bank and the server first, then this:

    make up
    HANDRAIL_SECRET_PASSWORD=plumbline-demo BASE_URL=http://127.0.0.1:8081 \\
        uv run python examples/agent_caller.py \\
            "Place a LEGAL hold on share 400226-S0002 of member 400226"

The agent is a `deepagents` agent given exactly the tools the Handrail MCP server lists. Its
instructions say what a receipt means. Share 400226-S0002 is already on hold, so the honest
answer is "already held, nothing changed", reached in one tool call and no retry.
"""

from __future__ import annotations

import asyncio
import os
import sys

INSTRUCTIONS = """You can place holds through the tools you were given. Each tool replays a
reviewed procedure on the bank's own screens and returns a receipt. Read it:
- category SUCCESS: done; report the outputs.
- category BUSINESS_OUTCOME: the bank answered no (for example ALREADY_PROCESSED). That is the
  answer. Report it. Do not call the tool again.
- retryable true: you may try once more. retryable false: do not.
Never invent a confirmation number. Never ask for or type a password; the server holds it."""


async def main(goal: str) -> None:
    from deepagents import create_deep_agent
    from langchain.chat_models import init_chat_model
    from langchain_mcp_adapters.client import MultiServerMCPClient

    from handrail.author.run import load_dotenv

    load_dotenv()  # the agent's model key; the server loads its own
    client = MultiServerMCPClient(
        {
            "handrail": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "handrail.cli", "serve", "--capabilities", "capabilities"],
                "env": dict(os.environ),
            }
        }
    )
    tools = await client.get_tools()
    print("tools on the menu:", [t.name for t in tools])
    agent = create_deep_agent(
        model=init_chat_model(os.environ.get("HANDRAIL_AGENT_MODEL", "anthropic:claude-sonnet-5")),
        tools=tools,
        system_prompt=INSTRUCTIONS,
    )
    out = await agent.ainvoke({"messages": [("user", goal)]})
    calls = [m for m in out["messages"] if getattr(m, "type", "") == "tool"]
    print(f"tool calls: {len(calls)}")
    for m in calls:
        print("  receipt:", str(m.content)[:200])
    print("agent says:", out["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(
        main(" ".join(sys.argv[1:]) or "Place a LEGAL hold on share 400226-S0002 of member 400226")
    )
