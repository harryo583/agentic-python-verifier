"""LLM-emitted synthesis artefacts."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Constants(BaseModel):
    """Finite domains for TLA+ CONSTANTS declarations."""

    values: dict[str, list[str | int]] = Field(default_factory=dict)

    def to_cfg_lines(self) -> list[str]:
        """Render as TLC `.cfg` CONSTANT assignments.

        Single-element domains are pinned via `CONSTANT name = value`.
        Multi-element domains are pinned via `CONSTANT name = {v1, v2, ...}`.
        """

        lines: list[str] = []
        for name, domain in self.values.items():
            if len(domain) == 1:
                lines.append(f"CONSTANT {name} = {_render_tla_value(domain[0])}")
            else:
                rendered = ", ".join(_render_tla_value(v) for v in domain)
                lines.append(f"CONSTANT {name} = {{{rendered}}}")
        return lines


def _render_tla_value(v: str | int) -> str:
    if isinstance(v, int):
        return str(v)
    return f'"{v}"'


_MODULE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class SynthesisProposal(BaseModel):
    """A candidate (PlusCal, inductive invariant, target property) bundle."""

    module_name: str
    slug: str
    pluscal: str
    invariant_name: str = "Inv"
    property_name: str = "Property"
    constants: Constants = Field(default_factory=Constants)
    notes: str = ""

    @field_validator("module_name")
    @classmethod
    def _validate_module(cls, v: str) -> str:
        if not _MODULE_NAME_RE.fullmatch(v):
            raise ValueError("module_name must match ^[A-Za-z][A-Za-z0-9_]*$")
        return v

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, v: str) -> str:
        if not _SLUG_RE.fullmatch(v):
            raise ValueError("slug must match ^[a-z][a-z0-9_]*$")
        return v


class RepairProposal(SynthesisProposal):
    """A repaired proposal carrying the agent's diagnosis."""

    reasoning: str
    targeted_obligation: Literal["init", "consec", "property"]

    def to_proposal(self) -> SynthesisProposal:
        return SynthesisProposal(
            module_name=self.module_name,
            slug=self.slug,
            pluscal=self.pluscal,
            invariant_name=self.invariant_name,
            property_name=self.property_name,
            constants=self.constants,
            notes=self.notes,
        )
