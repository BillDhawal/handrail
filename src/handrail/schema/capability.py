"""The capability: a reviewable description of how to do one task in one application.

It is data, not code. A person can read it, diff it, and sign it. Everything the
replay engine is allowed to do is written down here, and the validators below
refuse an artifact that is internally inconsistent, so the engine never has to
wonder whether a step's screen exists or a commit was ever confirmed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .bindings import find_bindings, residue, target_texts
from .effects import Effect, EffectClass
from .errors import DEFAULT_CATEGORY, ErrorCode, OutcomeCategory
from .target import TARGETED_VERBS, Target, Verb

SCHEMA_VERSION: Literal["capability/2"] = "capability/2"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InputSpec(_Model):
    name: str
    type: Literal["string", "number", "boolean", "enum"] = "string"
    required: bool = True
    pattern: str | None = None
    enum: list[str] | None = None
    sensitivity: Literal["low", "secret"] = "low"
    description: str = ""


class OutputSource(_Model):
    step: str  # must be a `read` step
    extract: str | None = None  # a regex with one group; None means the whole text


class OutputSpec(_Model):
    name: str
    type: Literal["string", "number", "boolean"] = "string"
    source: OutputSource
    #: Outcome screens on which this output exists. Empty means every success.
    produced_on: list[str] = Field(default_factory=list)


class Screen(_Model):
    signature: str  # structural, never a text literal
    label: str  # one sentence a person, or a closed-set classifier, can read
    #: The attribute paths the signature was taken over. With them, a screen that gained a
    #: banner still matches (kernel/signature.py tier 2); without them, only an exact match.
    paths: list[str] = Field(default_factory=list)


class Op(_Model):
    verb: Verb
    value: str | None = None  # may contain bindings
    key: str | None = None


class Settle(_Model):
    """How the engine knows the step's effect has landed. Never a fixed sleep."""

    kind: Literal["target_present", "screen_is", "keyboard_unlocked"]
    step: str | None = None
    screen: str | None = None


class Expect(_Model):
    screen_in: list[str] = Field(min_length=1)  # a closed list


class Step(_Model):
    id: str
    intent: str
    screen: str  # the screen this step may run on: a precondition, always
    op: Op
    target: str | None = None  # a key into Capability.targets
    effect: Effect  # required: an unclassified step does not validate
    settle: Settle
    expect: Expect | None = None


class Outcome(_Model):
    category: OutcomeCategory
    code: ErrorCode = ErrorCode.NONE
    description: str = ""

    @model_validator(mode="after")
    def _category_agrees_with_code(self) -> Outcome:
        if DEFAULT_CATEGORY[self.code] is not self.category:
            raise ValueError(f"{self.code.value} is not a {self.category.value}")
        return self


class Reliability(_Model):
    replays: int = 0
    clean: int = 0


class Lifecycle(_Model):
    state: Literal["draft", "verified", "approved", "deprecated"] = "draft"
    approved_by: str | None = None
    approved_at: str | None = None
    deprecated_by: str | None = None
    note: str = ""  # why it was deprecated, or anything else a person wants to say
    reliability: Reliability = Field(default_factory=Reliability)


class SurfaceSpec(_Model):
    kind: Literal["browser", "terminal", "macos_ax"]
    entry: str  # a URL, host:port, or bundle id; may contain {{env.X}}
    requires: list[str] = Field(default_factory=list)


class Safety(_Model):
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_apps: list[str] = Field(default_factory=list)
    allowed_verbs: list[Verb] = Field(default_factory=list)


class Capability(_Model):
    schema_version: Literal["capability/2"] = SCHEMA_VERSION
    id: str
    version: str
    title: str
    lifecycle: Lifecycle = Field(default_factory=Lifecycle)
    surface: SurfaceSpec
    inputs: list[InputSpec] = Field(default_factory=list)
    outputs: list[OutputSpec] = Field(default_factory=list)
    screens: dict[str, Screen] = Field(min_length=1)
    targets: dict[str, Target] = Field(default_factory=dict)
    steps: list[Step] = Field(min_length=1)
    #: Which screens end the run, and what ending there means. Keys are screen names.
    outcomes: dict[str, Outcome] = Field(min_length=1)
    safety: Safety = Field(default_factory=Safety)

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"

    def step(self, step_id: str) -> Step:
        for candidate in self.steps:
            if candidate.id == step_id:
                return candidate
        raise KeyError(step_id)

    # -- validators: each one is a sentence the engine gets to rely on ------------

    @model_validator(mode="after")
    def _references_resolve(self) -> Capability:
        ids = [s.id for s in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate step ids")
        for s in self.steps:
            if s.screen not in self.screens:
                raise ValueError(f"step {s.id}: unknown screen {s.screen!r}")
            if s.op.verb in TARGETED_VERBS and s.target is None:
                raise ValueError(f"step {s.id}: {s.op.verb} needs a target")
            if s.target is not None:
                if s.target not in self.targets:
                    raise ValueError(f"step {s.id}: unknown target {s.target!r}")
                if s.op.verb not in self.targets[s.target].supports:
                    raise ValueError(
                        f"step {s.id}: target {s.target!r} does not support {s.op.verb}"
                    )
            for name in s.expect.screen_in if s.expect else []:
                if name not in self.screens:
                    raise ValueError(f"step {s.id}: expects unknown screen {name!r}")
            if s.settle.step is not None and s.settle.step not in ids:
                raise ValueError(f"step {s.id}: settles on unknown step {s.settle.step!r}")
        return self

    @model_validator(mode="after")
    def _outcomes_are_screens_and_one_is_success(self) -> Capability:
        for name in self.outcomes:
            if name not in self.screens:
                raise ValueError(f"outcome {name!r} is not a declared screen")
        if not any(o.category is OutcomeCategory.SUCCESS for o in self.outcomes.values()):
            raise ValueError("no outcome is a SUCCESS")
        return self

    @model_validator(mode="after")
    def _outputs_come_from_reads(self) -> Capability:
        by_id = {s.id: s for s in self.steps}
        for out in self.outputs:
            source = by_id.get(out.source.step)
            if source is None or source.op.verb != "read":
                raise ValueError(f"output {out.name}: source must be a read step")
            for name in out.produced_on:
                if name not in self.outcomes:
                    raise ValueError(f"output {out.name}: {name!r} is not an outcome")
        return self

    @model_validator(mode="after")
    def _bindings_are_closed(self) -> Capability:
        declared = {i.name for i in self.inputs}
        texts = [self.surface.entry] + [s.op.value for s in self.steps if s.op.value]
        for target in self.targets.values():
            texts += target_texts(target)
        for text in texts:
            if residue(text):
                raise ValueError(f"binding residue {residue(text)} in {text!r}")
            for source, name in find_bindings(text):
                if source == "input" and name not in declared:
                    raise ValueError(f"{{{{input.{name}}}}} is not a declared input")
        return self

    @model_validator(mode="after")
    def _verbs_are_allowed(self) -> Capability:
        allowed = set(self.safety.allowed_verbs)
        for s in self.steps:
            if allowed and s.op.verb not in allowed:
                raise ValueError(f"step {s.id}: verb {s.op.verb} is outside safety.allowed_verbs")
        return self

    @model_validator(mode="after")
    def _lifecycle_gates(self) -> Capability:
        state = self.lifecycle.state
        if state != "draft":
            unconfirmed = [
                s.id
                for s in self.steps
                if s.effect.kind is EffectClass.COMMIT and not s.effect.confirmed_by
            ]
            if unconfirmed:
                raise ValueError(f"{state}: commit steps not confirmed by a person: {unconfirmed}")
        if state == "approved" and not self.lifecycle.approved_by:
            raise ValueError("approved: needs approved_by")
        return self
