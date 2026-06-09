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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.agents.planner_agent import DecompositionError, PlannerAgent
from src.agents.refine_agent import (
    RefineAgent,
    RefinedModule,
    RefineRuntimeError,
    RefineSyntaxError,
    package_init_source,
    smoke_test_package,
    trace_shim_source,
)
from src.agents.synth_agent import SynthesisAgent, _classify_error_note
from src.agents.trace_gate import TraceGate
from src.agents.verifier import Verifier
from src.config import Settings, get_settings, require_runtime_settings
from src.formal.preflight import lint_bundle, preflight_proof
from src.llm.anthropic_client import AnthropicClient
from src.llm.usage import UsageLedger
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    PythonPackage,
    TraceResult,
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

    ledger: Optional[UsageLedger]
    if client is None:
        ledger = UsageLedger()
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
            ledger=ledger,
        )
    else:
        ledger = getattr(client, "ledger", None)

    def _finalize(result: PipelineResult) -> PipelineResult:
        if ledger is not None:
            result.usage = ledger.summary()
        return result

    verifier = verifier or Verifier(settings)
    synth_few_shot, repair_few_shot = _few_shot_blocks(settings)
    synth = SynthesisAgent(
        client,
        repair_history_mode=settings.repair_history_mode,
        synth_few_shot=synth_few_shot,
        repair_few_shot=repair_few_shot,
    )
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
        return _finalize(PipelineResult(
            status="unverified",
            iterations=iterations,
            proposal=proposal,
            bundle=bundle,
        ))

    LOGGER.info("Refining verified PlusCal into Python...")
    try:
        refined: RefinedModule = refine.to_python(proposal)
    except RefineSyntaxError as exc:
        LOGGER.error("Refinement produced invalid Python: %s", exc)
        return _finalize(PipelineResult(
            status="unverified",
            iterations=iterations,
            proposal=proposal,
            bundle=bundle,
        ))

    tla_path = settings.tla_dir / f"{proposal.slug}.tla"
    python_path = settings.python_dir / f"{proposal.slug}.py"
    work_main = settings.work_dir / f"{proposal.slug}_iter{iterations - 1}" / f"{proposal.module_name}.tla"
    if work_main.exists():
        write_text(tla_path, work_main.read_text(encoding="utf-8"))
    else:
        write_text(tla_path, proposal.pluscal)
    write_text(python_path, refined.python_module)

    return _finalize(PipelineResult(
        status="verified",
        iterations=iterations,
        proposal=proposal,
        bundle=bundle,
        tla_path=tla_path,
        python_path=python_path,
    ))


def run_compositional_pipeline(
    task: TaskRequest,
    settings: Settings,
    client: Optional[AnthropicClient] = None,
    verifier: Optional[Verifier] = None,
    trace_gate: Optional[TraceGate] = None,
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

    ledger: Optional[UsageLedger]
    if client is None:
        ledger = UsageLedger()
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
            ledger=ledger,
        )
    else:
        ledger = getattr(client, "ledger", None)

    def _finalize(
        result: CompositionalPipelineResult,
    ) -> CompositionalPipelineResult:
        if ledger is not None:
            result.usage = ledger.summary()
        return result

    verifier = verifier or Verifier(settings)
    planner = PlannerAgent(client)
    synth_few_shot, repair_few_shot = _few_shot_blocks(settings)
    synth = SynthesisAgent(
        client,
        repair_history_mode=settings.repair_history_mode,
        synth_few_shot=synth_few_shot,
        repair_few_shot=repair_few_shot,
    )
    refine = RefineAgent(client)

    LOGGER.info("Decomposing task into modules...")
    try:
        plan = planner.decompose(task)
    except DecompositionError as exc:
        LOGGER.error("Planner failed: %s", exc)
        return _finalize(CompositionalPipelineResult(
            status="planner_failed",
            iterations=0,
            note=str(exc),
            trace_skipped_reason="planner_failed",
        ))

    LOGGER.info(
        "Plan: parent=%s, %d module(s).",
        plan.parent_name,
        len(plan.modules),
    )

    outcome = _synthesize_and_verify(
        task=task,
        plan=plan,
        settings=settings,
        synth=synth,
        verifier=verifier,
    )
    bundle = outcome.bundle
    proof = outcome.proof
    iterations = outcome.iterations
    reroll_count = outcome.reroll_count
    last_work_dir = outcome.last_work_dir

    assert bundle is not None
    assert proof is not None
    assert last_work_dir is not None

    if not proof.all_passed:
        LOGGER.error(
            "Compositional pipeline exhausted %d iterations without verification.",
            iterations,
        )
        return _finalize(CompositionalPipelineResult(
            status="unverified",
            iterations=iterations,
            reroll_count=reroll_count,
            plan=plan,
            bundle=bundle,
            proof=proof,
            trace_skipped_reason="package_unverified",
        ))

    LOGGER.info("Refining verified bundle into Python package...")
    try:
        package = refine.to_python_package(bundle)
    except RefineSyntaxError as exc:
        LOGGER.error("Refinement produced invalid Python: %s", exc)
        return _finalize(CompositionalPipelineResult(
            status="refinement_failed",
            iterations=iterations,
            reroll_count=reroll_count,
            plan=plan,
            bundle=bundle,
            proof=proof,
            note=str(exc),
            trace_skipped_reason="refinement_failed",
        ))

    tla_out_dir = settings.tla_dir / bundle.slug
    py_out_dir = settings.python_dir / bundle.slug
    ensure_directory(tla_out_dir)
    ensure_directory(py_out_dir)
    _write_bundle_outputs(bundle, last_work_dir, tla_out_dir)
    _write_package_outputs(package, py_out_dir)

    LOGGER.info("Running runtime smoke test on emitted package...")
    try:
        smoke_test_package(
            slug=bundle.slug,
            package_parent_dir=settings.python_dir,
            steps=1,
            timeout_s=float(settings.trace_timeout_s),
        )
    except RefineRuntimeError as exc:
        LOGGER.error("Emitted package crashed at runtime: %s", exc)
        return _finalize(CompositionalPipelineResult(
            status="refinement_failed",
            iterations=iterations,
            reroll_count=reroll_count,
            plan=plan,
            bundle=bundle,
            proof=proof,
            tla_dir=tla_out_dir,
            python_dir=py_out_dir,
            note=str(exc),
            trace_skipped_reason="refinement_failed",
        ))

    traces: dict[str, TraceResult] = {}
    trace_skipped_reason: Optional[str] = None
    if settings.skip_trace_gate:
        trace_skipped_reason = "skip_trace_gate flag set"
        LOGGER.info("Trace gate skipped (--skip-trace-gate).")
    else:
        gate = trace_gate or TraceGate(settings=settings)
        trace_work = last_work_dir / "trace"
        ensure_directory(trace_work)
        LOGGER.info("Running trace-conformance gate on emitted package...")
        traces = gate.check(package, bundle, trace_work)
        for name, result in traces.items():
            LOGGER.info(
                "trace[%s]: %s (depth=%s, len=%s)",
                name,
                result.status,
                result.tla_depth,
                result.trace_length,
            )

    return _finalize(CompositionalPipelineResult(
        status="verified",
        iterations=iterations,
        reroll_count=reroll_count,
        plan=plan,
        bundle=bundle,
        proof=proof,
        tla_dir=tla_out_dir,
        python_dir=py_out_dir,
        traces=traces,
        trace_skipped_reason=trace_skipped_reason,
    ))


def _few_shot_blocks(settings: Settings) -> tuple[str, str]:
    """Render the synth/repair few-shot exemplar blocks (empty when disabled)."""

    if not settings.few_shot_enabled:
        return "", ""
    from src.llm.few_shot import (
        load_exemplars,
        render_repair_few_shot,
        render_synth_few_shot,
    )

    exemplars = load_exemplars(settings.exemplar_pool_dir)
    if not exemplars:
        LOGGER.warning(
            "few_shot_enabled but no exemplars found under %s; running zero-shot.",
            settings.exemplar_pool_dir,
        )
    else:
        LOGGER.info(
            "Few-shot enabled: %d exemplar(s) from %s.",
            len(exemplars),
            settings.exemplar_pool_dir,
        )
    return render_synth_few_shot(exemplars), render_repair_few_shot(exemplars)


@dataclass(slots=True)
class _SynthOutcome:
    """Result of the synth + verify (+ reroll) loop, before refinement."""

    bundle: ModuleBundle
    proof: CompositionalProofBundle
    iterations: int
    reroll_count: int
    last_work_dir: Path


def _proof_fingerprint(
    proof: CompositionalProofBundle,
) -> frozenset[tuple[str, str, str, str]]:
    """Identify *what* failed, so a repeated failure can be detected as "stuck".

    Covers error/timeout obligations (``counterexample is None``) — the
    documented stuck cases (reserved PlusCal labels, refinement SANY errors)
    never produce a counterexample, so a CE-only fingerprint would never fire.
    Each failing obligation contributes ``(module, obligation, status,
    descriptor)`` where the descriptor is the violated predicate (for a CE) or
    the classified toolchain error kind + first note line (for an error).
    """

    def descriptor(result: ObligationResult) -> str:
        if result.counterexample is not None:
            return f"ce:{result.counterexample.violated_predicate}"
        note = result.note or ""
        first_line = note.splitlines()[0] if note else ""
        return f"err:{_classify_error_note(note)}:{first_line}"

    items: set[tuple[str, str, str, str]] = set()
    for mod_name, pb in proof.per_module.items():
        for result in (pb.init, pb.consec, pb.property):
            if result.passed:
                continue
            items.add(
                (mod_name, str(result.obligation), str(result.status), descriptor(result))
            )
    if not proof.refinement.passed:
        ref = proof.refinement
        items.add(
            ("refinement", str(ref.obligation), str(ref.status), descriptor(ref))
        )
    return frozenset(items)


def _synthesize_and_verify(
    *,
    task: TaskRequest,
    plan: "DecompositionPlan",
    settings: Settings,
    synth: SynthesisAgent,
    verifier: Verifier,
) -> _SynthOutcome:
    """Propose a bundle and drive the repair loop, optionally rerolling.

    Default (``enable_reroll=False``) reproduces the historical behavior exactly:
    one ``propose_bundle`` followed by up to ``max_iterations`` verify/repair
    turns. With reroll enabled, a chain is abandoned and re-proposed from scratch
    after ``repairs_per_chain`` repairs or as soon as the same failure
    fingerprint repeats (no progress), reallocating the same total iteration
    budget toward fresh attempts rather than a poisoned transcript.
    """

    budget = task.max_iterations
    total_iter = 0
    reroll_count = 0
    bundle: ModuleBundle
    proof: CompositionalProofBundle | None = None
    last_work_dir: Path | None = None
    first_chain = True

    while budget > 0:
        if first_chain:
            LOGGER.info("Synthesising initial bundle...")
            first_chain = False
        else:
            reroll_count += 1
            LOGGER.info(
                "Rerolling from a fresh propose_bundle (reroll #%d)...", reroll_count
            )
        bundle, history, tool_use_id = synth.propose_bundle(task, plan)
        chain_fingerprints: list[frozenset[tuple[str, str, str, str]]] = []
        chain_len = 0

        while budget > 0:
            budget -= 1
            total_iter += 1
            chain_len += 1
            work_dir = settings.work_dir / f"{bundle.slug}_iter{total_iter - 1}"
            findings = lint_bundle(bundle) if settings.enable_preflight else []
            if findings:
                # #2 — reject deterministically without spending a TLC run; the
                # synthetic proof carries the lint diagnostics into the repair.
                ensure_directory(work_dir)
                proof = preflight_proof(bundle, findings)
                LOGGER.warning(
                    "Iteration %d: pre-flight rejected bundle %s (%d finding(s)); "
                    "skipped TLC.",
                    total_iter,
                    bundle.slug,
                    len(findings),
                )
            else:
                LOGGER.info(
                    "Iteration %d: verifying bundle %s...", total_iter, bundle.slug
                )
                proof = verifier.check_bundle(bundle, work_dir)
            last_work_dir = work_dir
            if proof.all_passed:
                LOGGER.info(
                    "All compositional obligations passed at iteration %d.",
                    total_iter,
                )
                return _SynthOutcome(
                    bundle, proof, total_iter, reroll_count, work_dir
                )

            fingerprint = _proof_fingerprint(proof)
            stuck = bool(chain_fingerprints) and chain_fingerprints[-1] == fingerprint
            chain_fingerprints.append(fingerprint)
            LOGGER.warning(
                "Iteration %d failed: modules=%s, refinement=%s%s.",
                total_iter,
                proof.failing_modules(),
                proof.refinement.status,
                " (same failure as last iteration — stuck)" if stuck else "",
            )
            if budget == 0:
                break

            if settings.enable_reroll and (
                stuck
                or (
                    settings.repairs_per_chain > 0
                    and chain_len >= settings.repairs_per_chain
                )
            ):
                LOGGER.info(
                    "Abandoning chain after %d repair(s) (stuck=%s); rerolling.",
                    chain_len,
                    stuck,
                )
                break  # -> outer reroll loop

            LOGGER.info("Requesting repair...")
            bundle, history, tool_use_id = synth.repair_bundle(
                history=history,
                proof=proof,
                last_bundle=bundle,
                previous_tool_use_id=tool_use_id,
            )

        if not settings.enable_reroll:
            break

    assert proof is not None
    assert last_work_dir is not None
    return _SynthOutcome(bundle, proof, total_iter, reroll_count, last_work_dir)


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
