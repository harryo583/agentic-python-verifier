"""Verification agent using TLC or deterministic local checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config import Settings
from src.formal.tla_runner import run_tlc
from src.models.task import TaskSpecification, VerificationResult


@dataclass(slots=True)
class VerifierAgent:
    """Verify generated TLA+ modules with TLC when available."""

    settings: Settings

    def verify(self, task: TaskSpecification, tla_path: Path, tla_content: str) -> VerificationResult:
        """Verify a TLA+ module and return a structured verification result."""

        execution = run_tlc(tla_path, self.settings.tlc_jar_path)
        if not execution.used_mock:
            return VerificationResult(
                status="success" if execution.succeeded else "failure",
                used_mock=False,
                message="TLC verification finished.",
                details=[line for line in execution.stdout.splitlines() if line][:5]
                or [line for line in execution.stderr.splitlines() if line][:5],
            )
        return self._mock_verify(task, tla_content)

    def _mock_verify(self, task: TaskSpecification, tla_content: str) -> VerificationResult:
        """Perform deterministic structural checks when TLC is unavailable."""

        details: list[str] = []
        if "--algorithm" not in tla_content:
            details.append("Missing PlusCal algorithm block.")
        if "Invariant ==" not in tla_content:
            details.append("Missing invariant definition.")
        if "Property ==" not in tla_content:
            details.append("Missing property definition.")
        if not task.invariants:
            details.append("Task has no invariants.")

        proof_text = tla_content.lower()
        for obligation in ("initiation", "consecution", "property implication"):
            if obligation not in proof_text:
                details.append(f"Missing {obligation} proof-obligation marker.")

        if task.task_type == "bank_transfer":
            invariant_text = " ".join(task.invariants)
            if "source + target" not in invariant_text:
                details.append("Bank transfer must preserve total funds.")

        if task.task_type == "bounded_counter":
            lower = int(task.parameters.get("min_value", 0))
            upper = int(task.parameters.get("max_value", 10))
            if lower > upper:
                details.append("Counter lower bound exceeds upper bound.")

        status = "failure" if details else "success"
        message = (
            "Deterministic mock verification succeeded."
            if status == "success"
            else "Deterministic mock verification found issues."
        )
        return VerificationResult(
            status=status,
            used_mock=True,
            message=message,
            details=details or ["Specification structure and invariants are consistent."],
        )
