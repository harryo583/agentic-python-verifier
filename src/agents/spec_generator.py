"""Agent that produces PlusCal/TLA+ specifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.formal.pluscal_templates import render_pluscal
from src.llm import LLMClient, LLMError
from src.models.task import TaskSpecification


@dataclass(slots=True)
class SpecificationGenerator:
    """Generate PlusCal/TLA+ modules with candidate inductive invariants."""

    llm_client: Optional[LLMClient] = None

    def generate(self, task: TaskSpecification) -> str:
        """Render a task into a self-contained TLA+ module."""

        if task.pluscal_spec:
            return task.pluscal_spec
        if self.llm_client is not None:
            try:
                generated = self._generate_with_llm(task)
                if _looks_like_tla_module(generated):
                    task.pluscal_spec = generated
                    return generated
            except LLMError:
                pass
        return render_pluscal(task)

    def _generate_with_llm(self, task: TaskSpecification) -> str:
        assert self.llm_client is not None
        data = self.llm_client.complete_json(
            system_prompt=(
                "You generate formal specifications for an agentic verifier. Return exactly one "
                "strictly valid JSON object and nothing else: no markdown, no code fences, no "
                "comments outside JSON, and no trailing prose. "
                "The spec must be a self-contained TLA+ module containing a PlusCal algorithm "
                "comment block, an Init predicate, a Next predicate or translated next-state "
                "relation when practical, an Invariant predicate, a Property predicate, and "
                "comments identifying the proof obligations Initiation, Consecution, and "
                "Property Implication. Keep finite bounds suitable for TLC."
            ),
            user_prompt=(
                "TaskSpecification JSON:\n"
                f"{task.model_dump_json(indent=2)}\n\n"
                'Return only {"pluscal_spec": "..."} where pluscal_spec is complete TLA+ text. '
                "Escape all newlines and quotes as required by JSON."
            ),
        )
        return str(data.get("pluscal_spec", "")).strip()


def _looks_like_tla_module(text: str) -> bool:
    return "MODULE" in text and "--algorithm" in text and "Invariant" in text
