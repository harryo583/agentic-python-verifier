"""Orchestrator for the proof-driven PlusCal+invariant co-synthesis pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from src.agents.refine_agent import RefineAgent, RefinedModule
from src.agents.synth_agent import SynthesisAgent
from src.agents.verifier import Verifier
from src.config import ConfigError, Settings
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

    _require_pipeline_settings(
        settings,
        need_client=client is None,
        need_verifier=verifier is None,
    )
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
    artifact_paths: list[Path] = []

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
        artifact_paths.extend(
            _write_iteration_artifacts(
                work_dir=work_dir,
                iteration=iterations,
                proposal=proposal,
                bundle=bundle,
            )
        )
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
        artifact_paths.extend(
            _write_repair_artifacts(
                work_dir=work_dir,
                iteration=iterations,
                repair=_repair,
            )
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
            artifact_paths=artifact_paths,
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
        artifact_paths=artifact_paths,
    )


def _last_tool_use_id(history: list[dict[str, Any]]) -> str:
    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue
        for block in msg.get("content", []) or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                return block["id"]
    raise RuntimeError("No tool_use block found in conversation history.")


def _require_pipeline_settings(
    settings: Settings,
    *,
    need_client: bool,
    need_verifier: bool,
) -> None:
    """Fail fast only for production components this run will construct."""

    missing: list[str] = []
    if need_client and not settings.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY (set in your environment or a .env file)")
    if need_verifier:
        if not settings.tla2tools_jar:
            missing.append(
                "TLA2TOOLS_JAR (path to tla2tools.jar; supplies pcal.trans and tlc2.TLC)"
            )
        elif not Path(settings.tla2tools_jar).exists():
            missing.append(
                f"TLA2TOOLS_JAR points to a missing file: {settings.tla2tools_jar}"
            )
    if missing:
        joined = "\n  - ".join(missing)
        raise ConfigError(
            "Cannot run the proof-driven pipeline. Missing required settings:\n  - "
            + joined
        )


def _write_iteration_artifacts(
    *,
    work_dir: Path,
    iteration: int,
    proposal: SynthesisProposal,
    bundle: ProofBundle,
) -> list[Path]:
    """Persist small, stable reporting files for one verification attempt."""

    paths = [
        write_text(work_dir / "proposal.json", proposal.model_dump_json(indent=2)),
        write_text(work_dir / "proof_bundle.json", bundle.model_dump_json(indent=2)),
        write_text(
            work_dir / "iteration_summary.md",
            _format_iteration_summary(iteration, proposal, bundle),
        ),
    ]
    return paths


def _write_repair_artifacts(
    *,
    work_dir: Path,
    iteration: int,
    repair: Any,
) -> list[Path]:
    """Persist the LLM repair diagnosis alongside the failed iteration."""

    content = (
        repair.model_dump_json(indent=2)
        if hasattr(repair, "model_dump_json")
        else str(repair)
    )
    summary = (
        f"# Repair requested after iteration {iteration}\n\n"
        f"- Targeted obligation: {getattr(repair, 'targeted_obligation', '<unknown>')}\n"
        f"- Reasoning: {getattr(repair, 'reasoning', '<none>')}\n"
    )
    return [
        write_text(work_dir / "repair.json", content),
        write_text(work_dir / "repair_summary.md", summary),
    ]


def _format_iteration_summary(
    iteration: int,
    proposal: SynthesisProposal,
    bundle: ProofBundle,
) -> str:
    lines = [
        f"# Verification iteration {iteration}",
        "",
        f"- Module: {proposal.module_name}",
        f"- Slug: {proposal.slug}",
        f"- Overall: {'passed' if bundle.all_passed else 'failed'}",
        "",
        "## Obligations",
    ]
    for result in (bundle.init, bundle.consec, bundle.property):
        lines.append(f"- {result.obligation}: {result.status}")
        if result.note:
            lines.append(f"  - note: {result.note}")
        if result.counterexample is not None:
            ce = result.counterexample
            lines.append(f"  - violated_predicate: {ce.violated_predicate}")
            lines.append(f"  - trace_states: {len(ce.trace)}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Entrypoint for `python -m src.main`."""

    from src.cli import app

    app()


if __name__ == "__main__":
    main()
