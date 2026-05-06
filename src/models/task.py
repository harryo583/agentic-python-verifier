"""Domain models for task planning and verification."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskSpecification(BaseModel):
    """Structured representation of an input task."""

    name: str
    slug: str
    task_type: Literal[
        "bounded_counter",
        "bank_transfer",
        "state_machine",
        "mutual_exclusion",
        "queue",
        "stack",
        "generic",
        "custom",
    ]
    description: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    state_variables: dict[str, Any] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    pluscal_spec: str | None = None
    python_code: str | None = None


class VerificationResult(BaseModel):
    """Outcome of a verification run."""

    status: Literal["success", "failure", "skipped"]
    used_mock: bool
    message: str
    details: list[str] = Field(default_factory=list)
