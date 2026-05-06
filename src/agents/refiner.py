"""Refine failing task specifications based on verifier feedback."""

from __future__ import annotations

from dataclasses import dataclass

from src.models.task import TaskSpecification, VerificationResult


@dataclass(slots=True)
class RefinerAgent:
    """Simple rule-based refiner for missing invariants and malformed bounds."""

    def refine(self, task: TaskSpecification, verification: VerificationResult) -> TaskSpecification:
        """Return a refined copy of the task after a failed verification."""

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
