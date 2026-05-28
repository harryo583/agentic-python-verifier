"""Task request and pipeline result models."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    TraceResult,
)
from src.models.decomposition import DecompositionPlan
from src.models.proof import ProofBundle
from src.models.synthesis import SynthesisProposal


class TaskRequest(BaseModel):
    """A natural-language requirement for the agent to verify and implement."""

    prompt: str = Field(..., min_length=1)
    name: Optional[str] = None
    slug: Optional[str] = None
    extra_constants: dict[str, list[str | int]] = Field(default_factory=dict)
    max_iterations: int = Field(default=5, ge=1, le=20)

    @field_validator("slug")
    @classmethod
    def _slug_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.fullmatch(r"[a-z][a-z0-9_]*", v):
            raise ValueError("slug must match ^[a-z][a-z0-9_]*$")
        return v


class PipelineResult(BaseModel):
    """Final outcome of a single-module (legacy) pipeline run."""

    status: Literal["verified", "unverified"]
    iterations: int
    proposal: SynthesisProposal
    bundle: ProofBundle
    tla_path: Optional[Path] = None
    python_path: Optional[Path] = None

    model_config = {"arbitrary_types_allowed": True}


class CompositionalPipelineResult(BaseModel):
    """Final outcome of a compositional (multi-module) pipeline run.

    `status` reflects ONLY the static proof obligations (per-impl + refinement).
    Trace-conformance results land in `traces` (keyed by child class name) and
    are advisory: a non-conforming trace does NOT flip `status` to unverified
    (per the Week-3 locked decision). `trace_skipped_reason` is populated when
    the gate was deliberately bypassed (e.g. `--skip-trace-gate`) or could not
    run (e.g. the package itself was unverified).
    """

    status: Literal["verified", "unverified", "planner_failed", "refinement_failed"]
    iterations: int
    plan: Optional[DecompositionPlan] = None
    bundle: Optional[ModuleBundle] = None
    proof: Optional[CompositionalProofBundle] = None
    tla_dir: Optional[Path] = None
    python_dir: Optional[Path] = None
    traces: dict[str, TraceResult] = Field(default_factory=dict)
    trace_skipped_reason: Optional[str] = None
    note: str = ""

    model_config = {"arbitrary_types_allowed": True}
