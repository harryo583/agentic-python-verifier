"""Planner-output models: a multi-module decomposition plan."""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator

# Module-name validation (reuse pattern from src/models/synthesis.py)
import re
_MODULE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class AbstractInterface(BaseModel):
    """The abstract contract a module exposes to its siblings/parent.

    This is what the planner emits; the synthesiser later turns it into a
    concrete `<Name>_Abs.tla` module.
    """

    state_variables: list[str] = Field(
        default_factory=list,
        description="Abstract state variable names (no types yet).",
    )
    actions: list[str] = Field(
        default_factory=list,
        description="Abstract action names (e.g. 'Enqueue', 'Dequeue').",
    )
    invariant_sketch: str = Field(
        default="",
        description="One-line natural-language invariant the module must preserve.",
    )


class PlanModuleSpec(BaseModel):
    """One conceptual module in a DecompositionPlan.

    Carries no TLA+ yet — that comes when the SynthesisAgent expands the plan
    into a ModuleBundle.
    """

    name: str = Field(..., description="Conceptual module name, e.g. 'Queue'.")
    role: str = Field(
        ..., description="Free-form description of what this module does."
    )
    abstract_iface: AbstractInterface

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not _MODULE_NAME_RE.fullmatch(v):
            raise ValueError("module name must match ^[A-Za-z][A-Za-z0-9_]*$")
        return v


class DecompositionPlan(BaseModel):
    """Top-level planner output: a parent + ≤4 child modules."""

    parent_name: str = Field(
        ..., description="TLA+ module name for the parent (composition) module."
    )
    parent_role: str = Field(
        ..., description="Free-form description of what the parent composes."
    )
    modules: list[PlanModuleSpec] = Field(
        ...,
        min_length=1,
        max_length=4,
        description="At most 4 child modules — hard cap from plan.",
    )
    notes: str = ""

    @field_validator("parent_name")
    @classmethod
    def _validate_parent(cls, v: str) -> str:
        if not _MODULE_NAME_RE.fullmatch(v):
            raise ValueError("parent_name must match ^[A-Za-z][A-Za-z0-9_]*$")
        return v

    @model_validator(mode="after")
    def _names_unique(self):
        names = [m.name for m in self.modules] + [self.parent_name]
        if len(names) != len(set(names)):
            raise ValueError("module names (including parent_name) must be unique")
        return self
