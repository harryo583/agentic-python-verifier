"""Refine failing task specifications based on verifier feedback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

from src.llm import LLMClient, LLMError
from src.models.task import TaskSpecification, VerificationResult


@dataclass(slots=True)
class RefinerAgent:
    """Refine failing task/specification pairs based on verifier feedback."""

    llm_client: Optional[LLMClient] = None

    def refine(self, task: TaskSpecification, verification: VerificationResult) -> TaskSpecification:
        """Return a refined copy of the task after a failed verification."""

        if self.llm_client is not None:
            try:
                return self._refine_with_llm(task, verification)
            except (LLMError, ValidationError, ValueError, TypeError):
                pass

        refined = task.model_copy(deep=True)
        issues = " ".join(verification.details)

        if task.task_type == "bounded_counter":
            minimum = int(refined.parameters.get("min_value", 0))
            maximum = int(refined.parameters.get("max_value", 10))
            if minimum > maximum:
                refined.parameters["min_value"] = maximum
                refined.parameters["max_value"] = minimum
            refined.invariants = [f"{refined.parameters['min_value']} <= counter <= {refined.parameters['max_value']}"]

        if task.task_type == "bank_transfer" and "preserve total funds" in issues.lower():
            refined.invariants = ["source >= 0", "target >= 0", "source + target = total_funds"]

        if not refined.invariants:
            refined.invariants = ["state remains well-formed"]

        refined.assumptions.append("Refinement applied after failed verification.")
        return refined

    def _refine_with_llm(self, task: TaskSpecification, verification: VerificationResult) -> TaskSpecification:
        assert self.llm_client is not None
        data = self.llm_client.complete_json(
            system_prompt=(
                "You repair formal-methods artifacts. Given a TaskSpecification and verifier "
                "feedback, return a corrected TaskSpecification JSON. Diagnose whether the "
                "failure is initiation, consecution, property implication, syntax, or bounds. "
                "Prefer repairing invariants/specs over weakening properties."
            ),
            user_prompt=(
                "TaskSpecification JSON:\n"
                f"{task.model_dump_json(indent=2)}\n\n"
                "Verification result JSON:\n"
                f"{verification.model_dump_json(indent=2)}"
            ),
        )
        data.setdefault("description", task.description)
        data.setdefault("task_type", task.task_type)
        data.setdefault("slug", task.slug)
        if data["task_type"] not in {
            "bounded_counter",
            "bank_transfer",
            "state_machine",
            "mutual_exclusion",
            "queue",
            "stack",
            "generic",
            "custom",
        }:
            data["task_type"] = "custom"
        return TaskSpecification.model_validate(data)
