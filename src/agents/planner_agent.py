"""Planner agent: decompose a NL task into a multi-module DecompositionPlan."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.llm.anthropic_client import AnthropicClient
from src.llm.prompts import PLANNER_SYSTEM
from src.llm.tools import PROPOSE_DECOMPOSITION_TOOL
from src.models.decomposition import DecompositionPlan
from src.models.task import TaskRequest


LOGGER = logging.getLogger(__name__)


MAX_DECOMPOSITION_RETRIES = 2


class DecompositionError(RuntimeError):
    """Raised when the planner cannot produce a valid plan."""


@dataclass(slots=True)
class PlannerAgent:
    """LLM-driven decomposition with a small repair loop."""

    client: AnthropicClient

    def decompose(self, task: TaskRequest) -> DecompositionPlan:
        """Return a DecompositionPlan. Retries up to MAX_DECOMPOSITION_RETRIES."""

        messages: list[dict[str, Any]] = [_initial_user_message(task)]
        last_error: str | None = None
        last_tool_use_id: str | None = None

        for attempt in range(MAX_DECOMPOSITION_RETRIES + 1):
            response = self.client.message(
                system=PLANNER_SYSTEM,
                messages=messages,
                tools=[PROPOSE_DECOMPOSITION_TOOL],
                tool_choice={"type": "tool", "name": PROPOSE_DECOMPOSITION_TOOL["name"]},
            )
            tool_use = self.client.extract_tool_use(
                response, expected_name=PROPOSE_DECOMPOSITION_TOOL["name"]
            )
            try:
                plan = DecompositionPlan.model_validate(tool_use.input)
                return plan
            except ValidationError as exc:
                last_error = _summarise_validation_error(exc)
                last_tool_use_id = tool_use.tool_use_id
                LOGGER.warning(
                    "Planner attempt %d produced invalid plan: %s",
                    attempt + 1,
                    last_error,
                )
                if attempt == MAX_DECOMPOSITION_RETRIES:
                    break
                # Append assistant response + tool_result feedback for the retry.
                messages.append(
                    {"role": "assistant", "content": _content_blocks(response)}
                )
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": last_tool_use_id,
                                "content": _retry_feedback(last_error),
                            }
                        ],
                    }
                )

        raise DecompositionError(
            f"Planner exhausted {MAX_DECOMPOSITION_RETRIES + 1} attempts; "
            f"last error: {last_error}"
        )


def _initial_user_message(task: TaskRequest) -> dict[str, Any]:
    body = (
        "Requirement (natural language):\n"
        f"{task.prompt.strip()}\n\n"
        "Decompose this into a parent TLA+ module plus 2-4 child modules with "
        "AbstractInterfaces. Emit exactly one call to propose_decomposition."
    )
    return {"role": "user", "content": [{"type": "text", "text": body}]}


def _summarise_validation_error(exc: ValidationError) -> str:
    """Render a ValidationError into a compact actionable string."""

    issues: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        msg = err.get("msg", "")
        issues.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(issues) if issues else str(exc)


def _retry_feedback(error: str) -> str:
    return (
        "Your previous decomposition failed schema validation:\n"
        f"  {error}\n\n"
        "Common causes:\n"
        "  - More than 4 modules. Hard cap is 4; bias toward 2-3.\n"
        "  - Module name colliding with parent_name; all names must be unique.\n"
        "  - Module name not a TLA+ identifier (must match ^[A-Za-z][A-Za-z0-9_]*$).\n"
        "  - Missing required field (state_variables, actions, invariant_sketch).\n"
        "\n"
        "Call propose_decomposition again with a corrected plan."
    )


def _content_blocks(response: Any) -> list[dict[str, Any]]:
    """Convert an Anthropic Messages response into JSON-serialisable content blocks."""

    out: list[dict[str, Any]] = []
    for block in getattr(response, "content", None) or []:
        block_type = _attr(block, "type")
        if block_type == "text":
            out.append({"type": "text", "text": _attr(block, "text") or ""})
        elif block_type == "tool_use":
            out.append(
                {
                    "type": "tool_use",
                    "id": _attr(block, "id"),
                    "name": _attr(block, "name"),
                    "input": _attr(block, "input") or {},
                }
            )
    return out


def _attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
