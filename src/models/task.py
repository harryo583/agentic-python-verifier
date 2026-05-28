"""Task request and pipeline result models."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

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
    """Final outcome of a pipeline run."""

    status: Literal["verified", "unverified"]
    iterations: int
    proposal: SynthesisProposal
    bundle: ProofBundle
    tla_path: Optional[Path] = None
    python_path: Optional[Path] = None
    artifact_paths: list[Path] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
