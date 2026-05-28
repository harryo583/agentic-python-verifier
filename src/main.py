"""Orchestrator for the proof-driven PlusCal+invariant co-synthesis pipeline.

Two pipeline entry points:

* ``run_pipeline`` - legacy single-module flow (synth -> 3 obligations ->
  refine -> Python with bare asserts). Unchanged from Week 1.
* ``run_compositional_pipeline`` - multi-module flow (plan -> synth bundle ->
  4 obligations -> refine to PythonPackage with icontract decorators). New
  in Week 2.

The CLI picks one based on the ``--compositional`` / ``--legacy`` flag.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from src.agents.planner_agent import DecompositionError, PlannerAgent
from src.agents.refine_agent import (
    RefineAgent,
    RefinedModule,
    package_init_source,
    trace_shim_source,
)
from src.agents.synth_agent import SynthesisAgent
from src.agents.verifier import Verifier
from src.config import Settings, get_settings, require_runtime_settings
from src.llm.anthropic_client import AnthropicClient
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    PythonPackage,
)
from src.models.proof import ProofBundle
from src.models.synthesis import SynthesisProposal
from src.models.task import (
    CompositionalPipelineResult,
    PipelineResult,
    TaskRequest,
)
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

    if client is None:
        tertiary = None
        if settings.openai_api_key:
            from src.llm.openai_adapter import OpenAIAdapter

            tertiary = OpenAIAdapter(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
        client = AnthropicClient(
            api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
            model=settings.model,
            fallback_model=settings.fallback_model,
            tertiary=tertiary,
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


def run_compositional_pipeline(
    task: TaskRequest,
    settings: Settings,
    client: Optional[AnthropicClient] = None,
    verifier: Optional[Verifier] = None,
) -> CompositionalPipelineResult:
    """Run the multi-module compositional pipeline.

    Steps:
        1. PlannerAgent.decompose -> DecompositionPlan
        2. SynthesisAgent.propose_bundle -> ModuleBundle
        3. Verifier.check_bundle (4 obligations per impl + refinement)
        4. SynthesisAgent.repair_bundle loop up to ``task.max_iterations``
        5. RefineAgent.to_python_package -> PythonPackage
        6. Write the package + ``_trace.py`` shim + ``__init__.py`` to
           ``settings.python_dir/<slug>/``, and every TLA+ module the
           verifier accepted to ``settings.tla_dir/<slug>/``.

    `client` and `verifier` may be injected for testing.
    """

    require_runtime_settings(settings)
    ensure_directory(settings.tla_dir)
    ensure_directory(settings.python_dir)
    ensure_directory(settings.work_dir)

    if client is None:
        tertiary = None
        if settings.openai_api_key:
            from src.llm.openai_adapter import OpenAIAdapter

            tertiary = OpenAIAdapter(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
        client = AnthropicClient(
            api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
            model=settings.model,
            fallback_model=settings.fallback_model,
            tertiary=tertiary,
        )
    verifier = verifier or Verifier(settings)
    planner = PlannerAgent(client)
    synth = SynthesisAgent(client)
    refine = RefineAgent(client)

    LOGGER.info("Decomposing task into modules...")
    try:
        plan = planner.decompose(task)
    except DecompositionError as exc:
        LOGGER.error("Planner failed: %s", exc)
        return CompositionalPipelineResult(
            status="planner_failed",
            iterations=0,
            note=str(exc),
        )

    LOGGER.info(
        "Plan: parent=%s, %d module(s).",
        plan.parent_name,
        len(plan.modules),
    )

    LOGGER.info("Synthesising initial bundle...")
    bundle, history, tool_use_id = synth.propose_bundle(task, plan)

    proof: CompositionalProofBundle | None = None
    iterations = 0
    last_work_dir: Path | None = None
    for i in range(task.max_iterations):
        iterations = i + 1
        LOGGER.info(
            "Iteration %d: verifying bundle %s...", iterations, bundle.slug
        )
        work_dir = settings.work_dir / f"{bundle.slug}_iter{i}"
        proof = verifier.check_bundle(bundle, work_dir)
        last_work_dir = work_dir
        if proof.all_passed:
            LOGGER.info(
                "All compositional obligations passed at iteration %d.", iterations
            )
            break

        failing_mods = proof.failing_modules()
        ref_status = proof.refinement.status
        LOGGER.warning(
            "Iteration %d failed: modules=%s, refinement=%s. Requesting repair...",
            iterations,
            failing_mods,
            ref_status,
        )
        if i == task.max_iterations - 1:
            break

        bundle, history, tool_use_id = synth.repair_bundle(
            history=history,
            proof=proof,
            last_bundle=bundle,
            previous_tool_use_id=tool_use_id,
        )

    assert proof is not None
    assert last_work_dir is not None

    if not proof.all_passed:
        LOGGER.error(
            "Compositional pipeline exhausted %d iterations without verification.",
            iterations,
        )
        return CompositionalPipelineResult(
            status="unverified",
            iterations=iterations,
            plan=plan,
            bundle=bundle,
            proof=proof,
        )

    LOGGER.info("Refining verified bundle into Python package...")
    package = refine.to_python_package(bundle)

    tla_out_dir = settings.tla_dir / bundle.slug
    py_out_dir = settings.python_dir / bundle.slug
    ensure_directory(tla_out_dir)
    ensure_directory(py_out_dir)
    _write_bundle_outputs(bundle, last_work_dir, tla_out_dir)
    _write_package_outputs(package, py_out_dir)

    return CompositionalPipelineResult(
        status="verified",
        iterations=iterations,
        plan=plan,
        bundle=bundle,
        proof=proof,
        tla_dir=tla_out_dir,
        python_dir=py_out_dir,
    )


def _write_bundle_outputs(
    bundle: ModuleBundle, work_dir: Path, tla_out_dir: Path
) -> None:
    """Copy each verified module from the verifier's work dir into the final tla_dir.

    Prefer the in-place pcal-translated file from ``work_dir``; fall back to
    the original ``tla_source`` if the work file is missing (covers paths
    where ``check_bundle`` skipped pcal.trans).
    """

    for module in (bundle.parent, *bundle.modules):
        work_file = work_dir / module.filename
        if work_file.exists():
            write_text(tla_out_dir / module.filename, work_file.read_text(encoding="utf-8"))
        else:
            write_text(tla_out_dir / module.filename, module.tla_source)


def _write_package_outputs(package: PythonPackage, py_out_dir: Path) -> None:
    """Write each child module, the parent app, and the trace + init shims."""

    write_text(py_out_dir / "__init__.py", package_init_source())
    write_text(py_out_dir / "_trace.py", trace_shim_source())
    for module in package.modules:
        write_text(py_out_dir / module.filename, module.source)
    if package.parent_app is not None:
        write_text(py_out_dir / "app.py", package.parent_app.source)


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
