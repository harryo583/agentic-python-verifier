"""Synthesis agent: propose and repair PlusCal+invariant pairs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from src.llm.anthropic_client import AnthropicClient
from src.llm.prompts import (
    REPAIR_BUNDLE_SYSTEM,
    REPAIR_SYSTEM,
    SYNTH_BUNDLE_SYSTEM,
    SYNTH_SYSTEM,
)
from src.llm.tools import (
    PROPOSE_BUNDLE_TOOL,
    PROPOSE_TOOL,
    REPAIR_BUNDLE_TOOL,
    REPAIR_TOOL,
)
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    ModuleSource,
)
from src.models.decomposition import DecompositionPlan
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

    def propose_bundle(
        self, task: TaskRequest, plan: DecompositionPlan
    ) -> tuple[ModuleBundle, list[dict[str, Any]], str]:
        """Expand a DecompositionPlan into a verifiable ModuleBundle.

        Returns (bundle, conversation_history, tool_use_id). The tool_use_id
        is needed so a subsequent repair_bundle can attach its tool_result.
        """

        user_msg = _initial_bundle_user_message(task, plan)
        request_messages: list[dict[str, Any]] = [user_msg]
        response = self.client.message(
            system=SYNTH_BUNDLE_SYSTEM,
            messages=request_messages,
            tools=[PROPOSE_BUNDLE_TOOL],
            tool_choice={"type": "tool", "name": PROPOSE_BUNDLE_TOOL["name"]},
        )
        tool_use = self.client.extract_tool_use(
            response, expected_name=PROPOSE_BUNDLE_TOOL["name"]
        )
        bundle = _bundle_from_tool_input(tool_use.input)
        new_history = request_messages + [
            {"role": "assistant", "content": _content_blocks(response)}
        ]
        return bundle, new_history, tool_use.tool_use_id

    def repair_bundle(
        self,
        history: list[dict[str, Any]],
        proof: CompositionalProofBundle,
        last_bundle: ModuleBundle,
        previous_tool_use_id: str,
    ) -> tuple[ModuleBundle, list[dict[str, Any]], str]:
        """Send a per-module + refinement failure summary back to the LLM."""

        feedback = _serialise_bundle_failure(proof, last_bundle)
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
            system=REPAIR_BUNDLE_SYSTEM,
            messages=request_messages,
            tools=[REPAIR_BUNDLE_TOOL],
            tool_choice={"type": "tool", "name": REPAIR_BUNDLE_TOOL["name"]},
        )
        tool_use = self.client.extract_tool_use(
            response, expected_name=REPAIR_BUNDLE_TOOL["name"]
        )
        new_bundle = _bundle_from_tool_input(tool_use.input)
        new_history = request_messages + [
            {"role": "assistant", "content": _content_blocks(response)}
        ]
        return new_bundle, new_history, tool_use.tool_use_id


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


def _initial_bundle_user_message(
    task: TaskRequest, plan: DecompositionPlan
) -> dict[str, Any]:
    """User message that hands the synthesiser a plan + the original NL task."""

    plan_lines = [
        f"Parent: {plan.parent_name}",
        f"Parent role: {plan.parent_role}",
        "",
        "Child modules:",
    ]
    for m in plan.modules:
        plan_lines.append(f"  - {m.name}: {m.role}")
        iface = m.abstract_iface
        plan_lines.append(
            f"      state_variables: {', '.join(iface.state_variables) or '<none>'}"
        )
        plan_lines.append(
            f"      actions: {', '.join(iface.actions) or '<none>'}"
        )
        plan_lines.append(f"      invariant_sketch: {iface.invariant_sketch}")
    if plan.notes:
        plan_lines.append("")
        plan_lines.append(f"Planner notes: {plan.notes}")

    body = (
        "Requirement (natural language):\n"
        f"{task.prompt.strip()}\n\n"
        "Approved decomposition plan:\n"
        + "\n".join(plan_lines)
        + "\n\n"
        "Expand this plan into a ModuleBundle. For each child, emit both "
        "<Name>_Abs (pure TLA+) and <Name>_Impl (PlusCal-bearing TLA+). "
        "Emit a parent module that INSTANCEs each impl and defines its "
        "own composed Inv and Property. Pin small finite CONSTANTS so TLC "
        "can model-check exhaustively. Emit one call to propose_module_bundle."
    )
    return {"role": "user", "content": [{"type": "text", "text": body}]}


def _bundle_from_tool_input(data: dict[str, Any]) -> ModuleBundle:
    """Convert tool input shape into a validated ModuleBundle.

    The tool emits `parent` without a `role` field (parent is implicit); we
    inject ``role="parent"`` before delegating to Pydantic so the validators
    on ModuleSource and ModuleBundle do the real checking.
    """

    parent_data = dict(data["parent"])
    parent_data["role"] = "parent"
    parent = ModuleSource.model_validate(parent_data)

    modules = [ModuleSource.model_validate(m) for m in data.get("modules", [])]

    return ModuleBundle(
        parent=parent,
        modules=modules,
        slug=data["slug"],
        notes=data.get("notes", ""),
    )


def _serialise_bundle_failure(
    proof: CompositionalProofBundle,
    bundle: ModuleBundle,
) -> str:
    """Render a failing CompositionalProofBundle as a tool_result string."""

    lines = ["The bundle failed model checking. Details:\n"]

    any_failure = False
    for mod_name, pb in proof.per_module.items():
        for result in (pb.init, pb.consec, pb.property):
            if result.passed:
                continue
            any_failure = True
            lines.append(
                f"- module {mod_name} :: {result.obligation}: {result.status.upper()}"
            )
            if result.note:
                lines.append(f"    note: {result.note}")
            if result.counterexample is not None:
                ce = result.counterexample
                lines.append(f"    violated_predicate: {ce.violated_predicate}")
                for state in ce.trace:
                    act = state.action or "<initial>"
                    assigns = ", ".join(
                        f"{k}={v}" for k, v in state.assignments.items()
                    )
                    lines.append(f"    State {state.index} <{act}>: {assigns}")
                if ce.raw_excerpt:
                    lines.append("    raw TLC excerpt:")
                    for raw_line in ce.raw_excerpt.splitlines():
                        lines.append(f"      {raw_line}")

    if not proof.refinement.passed:
        any_failure = True
        lines.append(
            f"- refinement obligation: {proof.refinement.status.upper()}"
        )
        if proof.refinement.note:
            lines.append(f"    note: {proof.refinement.note}")
        if proof.refinement.counterexample is not None:
            ce = proof.refinement.counterexample
            lines.append(f"    violated_predicate: {ce.violated_predicate}")
            for state in ce.trace:
                act = state.action or "<initial>"
                assigns = ", ".join(
                    f"{k}={v}" for k, v in state.assignments.items()
                )
                lines.append(f"    State {state.index} <{act}>: {assigns}")
            if ce.raw_excerpt:
                lines.append("    raw TLC excerpt:")
                for raw_line in ce.raw_excerpt.splitlines():
                    lines.append(f"      {raw_line}")

    if not any_failure:
        # Defensive: caller should have detected all_passed before invoking
        # repair, but if not we still want a non-empty feedback string.
        lines.append("- (no failing obligations were reported)")

    lines.append("")
    lines.append(f"Last bundle slug: {bundle.slug}")
    lines.append(f"Parent module: {bundle.parent.name}")
    lines.append(
        "Modules: "
        + ", ".join(f"{m.name}({m.role})" for m in bundle.modules)
    )
    lines.append(
        "Revise the failing module(s) and/or abstraction map(s). "
        "Return one call to repair_module_bundle with the FULL revised bundle."
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
