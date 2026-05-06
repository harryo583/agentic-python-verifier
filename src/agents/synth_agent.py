"""Synthesis agent: propose and repair PlusCal+invariant pairs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from src.llm.anthropic_client import AnthropicClient
from src.llm.prompts import REPAIR_SYSTEM, SYNTH_SYSTEM
from src.llm.tools import PROPOSE_TOOL, REPAIR_TOOL
from src.models.proof import ObligationResult, ProofBundle
from src.models.synthesis import RepairProposal, SynthesisProposal
from src.models.task import TaskRequest


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SynthesisAgent:
    """Orchestrates the LLM calls that propose and repair specs."""

    client: AnthropicClient

    def propose(self, task: TaskRequest) -> tuple[SynthesisProposal, list[dict[str, Any]]]:
        """Initial proposal. Returns the proposal and the conversation history."""

        user_msg = _initial_user_message(task)
        request_messages: list[dict[str, Any]] = [user_msg]
        response = self.client.message(
            system=SYNTH_SYSTEM,
            messages=request_messages,
            tools=[PROPOSE_TOOL],
            tool_choice={"type": "tool", "name": PROPOSE_TOOL["name"]},
        )
        tool_use = self.client.extract_tool_use(response, expected_name=PROPOSE_TOOL["name"])
        proposal = SynthesisProposal.model_validate(tool_use.input)
        new_history = request_messages + [
            {"role": "assistant", "content": _content_blocks(response)}
        ]
        return proposal, new_history

    def repair(
        self,
        task: TaskRequest,
        history: list[dict[str, Any]],
        bundle: ProofBundle,
        last_proposal: SynthesisProposal,
        previous_tool_use_id: str,
    ) -> tuple[SynthesisProposal, RepairProposal, list[dict[str, Any]]]:
        """Send TLC failure back to the LLM and parse the revised proposal."""

        feedback = _serialise_failure(bundle, last_proposal)
        request_messages = list(history) + [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": previous_tool_use_id,
                        "content": feedback,
                    }
                ],
            }
        ]
        response = self.client.message(
            system=REPAIR_SYSTEM,
            messages=request_messages,
            tools=[REPAIR_TOOL],
            tool_choice={"type": "tool", "name": REPAIR_TOOL["name"]},
        )
        tool_use = self.client.extract_tool_use(response, expected_name=REPAIR_TOOL["name"])
        repair = RepairProposal.model_validate(tool_use.input)
        new_history = request_messages + [
            {"role": "assistant", "content": _content_blocks(response)}
        ]
        return repair.to_proposal(), repair, new_history


def _initial_user_message(task: TaskRequest) -> dict[str, Any]:
    body = (
        "Requirement (natural language):\n"
        f"{task.prompt.strip()}\n\n"
        "Produce a PlusCal+invariant proposal for this requirement. "
        "Pin small finite CONSTANTS so TLC can model-check exhaustively."
    )
    if task.extra_constants:
        body += "\n\nThe user also requests these CONSTANTS domains:\n"
        body += json.dumps(task.extra_constants, indent=2)
    return {"role": "user", "content": [{"type": "text", "text": body}]}


def _serialise_failure(
    bundle: ProofBundle,
    proposal: SynthesisProposal,
) -> str:
    """Render a failing ProofBundle as a structured tool_result string."""

    lines = ["The proposal failed model checking. Details:\n"]
    for result in (bundle.init, bundle.consec, bundle.property):
        lines.append(f"- {result.obligation}: {result.status.upper()}")
        if result.note:
            lines.append(f"    note: {result.note}")
        if result.counterexample is not None:
            ce = result.counterexample
            lines.append(f"    violated_predicate: {ce.violated_predicate}")
            for state in ce.trace:
                act = state.action or "<initial>"
                assigns = ", ".join(f"{k}={v}" for k, v in state.assignments.items())
                lines.append(f"    State {state.index} <{act}>: {assigns}")
            if ce.raw_excerpt:
                lines.append("    raw TLC excerpt:")
                for raw_line in ce.raw_excerpt.splitlines():
                    lines.append(f"      {raw_line}")
    lines.append("")
    lines.append("Last proposal module name: " + proposal.module_name)
    lines.append("Last proposal slug: " + proposal.slug)
    lines.append(
        "Revise the module to make all three obligations pass. "
        "Return one call to repair_after_counterexample."
    )
    return "\n".join(lines)


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
