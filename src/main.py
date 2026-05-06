"""Orchestrator for the proof-driven PlusCal+invariant co-synthesis pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from src.agents.refine_agent import RefineAgent, RefinedModule
from src.agents.synth_agent import SynthesisAgent
from src.agents.verifier import Verifier
from src.config import Settings, get_settings, require_runtime_settings
from src.llm.anthropic_client import AnthropicClient
from src.models.proof import ProofBundle
from src.models.synthesis import SynthesisProposal
from src.models.task import PipelineResult, TaskRequest
from src.utils.file_utils import ensure_directory, write_text
from src.utils.logger import configure_logging


LOGGER = logging.getLogger(__name__)


def run_pipeline(
    task: TaskRequest,
    settings: Settings,
    client: Optional[AnthropicClient] = None,
    verifier: Optional[Verifier] = None,
) -> PipelineResult:
    """Run the full proof-driven pipeline.

    `client` and `verifier` may be injected for testing. In production they
    are constructed from `settings`.
    """

    require_runtime_settings(settings)
    ensure_directory(settings.tla_dir)
    ensure_directory(settings.python_dir)
    ensure_directory(settings.work_dir)

    client = client or AnthropicClient(
        api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
        model=settings.model,
        fallback_model=settings.fallback_model,
    )
    verifier = verifier or Verifier(settings)
    synth = SynthesisAgent(client)
    refine = RefineAgent(client)

    LOGGER.info("Synthesising initial proposal...")
    proposal, history = synth.propose(task)
    last_tool_use_id = _last_tool_use_id(history)

    bundle: ProofBundle | None = None
    iterations = 0
    for i in range(task.max_iterations):
        iterations = i + 1
        LOGGER.info(
            "Iteration %d: verifying proposal %s...", iterations, proposal.module_name
        )
        work_dir = settings.work_dir / f"{proposal.slug}_iter{i}"
        bundle = verifier.check(proposal, work_dir)
        if bundle.all_passed:
            LOGGER.info("All three obligations passed at iteration %d.", iterations)
            break

        failing = [r.obligation for r in bundle.failing()]
        LOGGER.warning(
            "Iteration %d failed obligations: %s. Requesting repair...",
            iterations,
            failing,
        )
        if i == task.max_iterations - 1:
            break

        proposal, _repair, history = synth.repair(
            task=task,
            history=history,
            bundle=bundle,
            last_proposal=proposal,
            previous_tool_use_id=last_tool_use_id,
        )
        last_tool_use_id = _last_tool_use_id(history)

    assert bundle is not None

    if not bundle.all_passed:
        LOGGER.error("Pipeline exhausted %d iterations without verification.", iterations)
        return PipelineResult(
            status="unverified",
            iterations=iterations,
            proposal=proposal,
            bundle=bundle,
        )

    LOGGER.info("Refining verified PlusCal into Python...")
    refined: RefinedModule = refine.to_python(proposal)

    tla_path = settings.tla_dir / f"{proposal.slug}.tla"
    python_path = settings.python_dir / f"{proposal.slug}.py"
    work_main = settings.work_dir / f"{proposal.slug}_iter{iterations - 1}" / f"{proposal.module_name}.tla"
    if work_main.exists():
        write_text(tla_path, work_main.read_text(encoding="utf-8"))
    else:
        write_text(tla_path, proposal.pluscal)
    write_text(python_path, refined.python_module)

    return PipelineResult(
        status="verified",
        iterations=iterations,
        proposal=proposal,
        bundle=bundle,
        tla_path=tla_path,
        python_path=python_path,
    )


def _last_tool_use_id(history: list[dict[str, Any]]) -> str:
    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue
        for block in msg.get("content", []) or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                return block["id"]
    raise RuntimeError("No tool_use block found in conversation history.")


def main() -> None:
    """Entrypoint for `python -m src.main`."""

    from src.cli import app

    app()


if __name__ == "__main__":
    main()
