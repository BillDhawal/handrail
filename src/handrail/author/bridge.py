"""The scout with a model behind it: the same card, commit struck off, a short leash.

Everything here is borrowed from authoring. The ``Session`` is seeded with the
card's declared screens so ``finish`` can only name one of them. The guard
is the same maître d', but the owner on the phone says no to every commit:
when a button is pressed, the referee is asked whether it looks like a
commit, and only a confident "not a commit" turns it into a navigation.
There is no ``assert_screen`` on the scout's card: the scout does not get to
invent landmarks, only to recognise the ones on the map.

The leash is ``max_turns``, four by default. A scout that does not report
in time has reported nothing, and the cook climbs to rung three. The leash
is short because a scout that wanders is worse than one that gives up: in
the first live run an eight-turn scout, forbidden to commit, walked the
application back to the hold form, and the run could not go forward from
there without a person. The scout's first duty is to recognise, not to roam.
"""

from __future__ import annotations

from typing import Any

from ..escalate.bridge import Crossing
from ..escalate.classifier import Classifier, ClassifierUnavailable
from ..escalate.questions import is_this_a_commit
from ..schema.capability import Capability
from ..schema.effects import EffectClass
from ..surface.base import Surface
from .agent import build_tools
from .middleware import Decision, Guard, Proposal
from .tools import Session

PROMPT = """The replay of a recorded task has lost its place. You are on a screen it does not
recognise. Using only the act tool, with read, set_value, select and invoke on links or
harmless buttons, bring the application to one of the expected screens below, then call
finish with that screen's exact name. If the screen showing now is already one of them, call
finish at once. You may not post, submit, confirm or delete anything; such presses are refused.
Never type a real value; use the input blanks given. Say nothing else; use the tools."""


def bridge_prompt(expected: dict[str, str], goal: str, input_names: list[str]) -> str:
    landmarks = "\n".join(f"- {label}: {hint}" for label, hint in expected.items())
    blanks = ", ".join(f"{{{{input.{n}}}}}" for n in input_names) or "none"
    return (
        f"{PROMPT}\n\nThe task being replayed: {goal}\n"
        f"Expected screens:\n{landmarks}\nInput blanks you may use: {blanks}"
    )


class LangChainBridge:
    name = "langchain"

    def __init__(
        self, model: Any, authoring: Any, classifier: Classifier | None = None, max_turns: int = 4
    ) -> None:
        self.model = model
        self.authoring = authoring  # BrowserAuthoring(page), or a factory for one
        self.classifier = classifier
        self.max_turns = max_turns

    def _refuse_commits(self, state: Any) -> Any:
        async def confirm(proposal: Proposal) -> Decision:
            if self.classifier is not None:
                question = is_this_a_commit()
                control = proposal.control
                text = f"Control: {control.role} {control.name!r}\n\nScreen:\n{state.text}"
                try:
                    verdict = await self.classifier.ask(text, question)
                except ClassifierUnavailable:
                    return Decision(None, "bridge")
                if verdict.chosen == "not_commit" and verdict.accepted_by(question):
                    return Decision(EffectClass.NAVIGATE, f"bridge:{self.classifier.name}")
            return Decision(None, "bridge")  # a commit is never the scout's to make

        return confirm

    async def cross(
        self,
        surface: Surface,
        capability: Capability,
        candidates: list[str],
        inputs: dict[str, Any],
        env: dict[str, str],
        step_id: str | None,
    ) -> Crossing:
        from langchain.agents import create_agent
        from langgraph.errors import GraphRecursionError

        session = Session(surface, inputs=dict(inputs), env=dict(env), lenient_finish=True)
        screens = capability.screens
        session.screens = {c: screens[c].signature for c in candidates if c in screens}
        session.paths = {c: tuple(screens[c].paths) for c in candidates if c in screens}
        menu = await session.look()
        assert session.observation is not None
        authoring = self.authoring() if callable(self.authoring) else self.authoring
        guard = Guard(session, authoring, self._refuse_commits(session.observation))
        tools = [t for t in build_tools(guard) if t.name in ("act", "finish")]
        expected = {c: screens[c].label for c in candidates if c in screens}
        opening = bridge_prompt(expected, capability.title, sorted(inputs))
        opening += f"\n\nScreen now:\n{menu}"
        agent: Any = create_agent(self.model, tools=tools, system_prompt=PROMPT)
        calls = 0
        try:
            out = await agent.ainvoke(
                {"messages": [("user", opening)]},
                config={"recursion_limit": 2 * self.max_turns + 1},
            )
            calls = sum(getattr(m, "type", "") == "ai" for m in out["messages"])
        except GraphRecursionError:
            calls = self.max_turns
        return Crossing(session.outcome, calls, len(session.trace), note=step_id or "")
