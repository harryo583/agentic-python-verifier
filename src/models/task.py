"""Domain models for task planning and verification."""

from __future__ import annotations

from typing import Literal, Union

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
    ]
    description: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    state_variables: dict[str, Union[int, str, list[str]]] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    parameters: dict[str, Union[int, str]] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Outcome of a verification run."""

    status: Literal["success", "failure", "skipped"]
    used_mock: bool
    message: str
    details: list[str] = Field(default_factory=list)
