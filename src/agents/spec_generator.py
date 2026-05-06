"""Agent that produces PlusCal/TLA+ specifications."""

from __future__ import annotations

from dataclasses import dataclass

from src.formal.pluscal_templates import render_pluscal
from src.models.task import TaskSpecification


@dataclass(slots=True)
class SpecificationGenerator:
    """Generate PlusCal and TLA+ modules from structured tasks."""

    def generate(self, task: TaskSpecification) -> str:
        """Render a task into a self-contained TLA+ module."""

        return render_pluscal(task)
