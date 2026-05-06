"""Proof-obligation and counterexample models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Obligation = Literal["init", "consec", "property"]


class TraceState(BaseModel):
    """One state in a TLC counterexample trace."""

    index: int
    action: Optional[str] = None
    assignments: dict[str, str] = Field(default_factory=dict)


class Counterexample(BaseModel):
    """Structured TLC counterexample."""

    obligation: Obligation
    violated_predicate: str
    trace: list[TraceState] = Field(default_factory=list)
    raw_excerpt: str = ""


ObligationStatus = Literal["passed", "failed", "timeout", "error"]


class ObligationResult(BaseModel):
    """Outcome of one of the three TLC obligation checks."""

    obligation: Obligation
    status: ObligationStatus
    tlc_returncode: Optional[int] = None
    duration_s: float = 0.0
    counterexample: Optional[Counterexample] = None
    raw_stdout: str = ""
    raw_stderr: str = ""
    note: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "passed"


class ProofBundle(BaseModel):
    """Results of all three proof obligations for one synthesis attempt."""

    init: ObligationResult
    consec: ObligationResult
    property: ObligationResult

    @property
    def all_passed(self) -> bool:
        return self.init.passed and self.consec.passed and self.property.passed

    def failing(self) -> list[ObligationResult]:
        return [r for r in (self.init, self.consec, self.property) if not r.passed]
