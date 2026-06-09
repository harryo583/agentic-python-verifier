"""Typer CLI for the proof-driven verifier."""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from src.config import ConfigError, get_settings
from src.main import run_compositional_pipeline, run_pipeline
from src.models.task import TaskRequest
from src.utils.logger import configure_logging


app = typer.Typer(
    add_completion=False,
    help="Proof-driven Python code generation via agentic PlusCal+invariant co-synthesis.",
)
console = Console()


@app.command()
def generate(
    prompt: str = typer.Argument(..., help="Natural language requirement."),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output directory for generated artifacts."
    ),
    max_iterations: int = typer.Option(
        5, "--max-iterations", "-n", min=1, max=20, help="Maximum repair iterations."
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Override the Claude model id."
    ),
    compositional: bool = typer.Option(
        True,
        "--compositional/--legacy",
        help=(
            "Use the multi-module compositional pipeline (default). "
            "--legacy regenerates the single-module baseline."
        ),
    ),
    skip_trace_gate: bool = typer.Option(
        False,
        "--skip-trace-gate/--no-skip-trace-gate",
        help=(
            "Skip the Week-3 trace-conformance gate. Has no effect with --legacy."
        ),
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """Run the full co-synthesis pipeline on PROMPT."""

    settings = get_settings(
        output_dir=output,
        verbose=verbose,
        max_iterations=max_iterations,
        model=model,
    )
    settings.skip_trace_gate = skip_trace_gate
    configure_logging(settings.log_level)
    task = TaskRequest(prompt=prompt, max_iterations=max_iterations)

    try:
        if compositional:
            _render_compositional(run_compositional_pipeline(task, settings))
        else:
            _render_legacy(run_pipeline(task, settings))
    except ConfigError as exc:
        console.print(f"[bold red]Configuration error[/bold red]\n{exc}")
        raise typer.Exit(code=2)


def _render_legacy(result) -> None:
    """Print a panel describing a single-module run."""

    obligations = (
        f"Init:     {result.bundle.init.status}\n"
        f"Consec:   {result.bundle.consec.status}\n"
        f"Property: {result.bundle.property.status}"
    )
    if result.status == "verified":
        body = (
            f"[bold green]Verified[/bold green] in {result.iterations} iteration(s)\n\n"
            f"{obligations}\n\n"
            f"TLA+:   {result.tla_path}\n"
            f"Python: {result.python_path}"
        )
    else:
        body = (
            f"[bold yellow]Unverified[/bold yellow] after {result.iterations} iteration(s)\n\n"
            f"{obligations}"
        )
    console.print(Panel.fit(body, title="Proof-Driven Verifier (legacy)"))
    if result.status != "verified":
        sys.exit(1)


def _render_compositional(result) -> None:
    """Print a panel describing a compositional run."""

    if result.status == "planner_failed":
        console.print(
            Panel.fit(
                f"[bold red]Planner failed[/bold red]\n\n{result.note}",
                title="Proof-Driven Verifier (compositional)",
            )
        )
        sys.exit(1)

    if result.status == "refinement_failed":
        # Two flavours: pre-write syntax failure (python_dir None) and
        # post-write runtime smoke-test failure (python_dir set, files left
        # on disk for the user to debug).
        if result.python_dir is None:
            footer = "Emitted Python did not parse; nothing was written to disk."
        else:
            footer = (
                f"Emitted package was written to {result.python_dir} but its "
                "runtime smoke test failed (parent/child names disagree, an "
                "invariant trips on construction, or `step()` raises)."
            )
        console.print(
            Panel.fit(
                f"[bold red]Refinement failed[/bold red] "
                f"after {result.iterations} verified iteration(s)\n\n"
                f"{result.note}\n\n"
                f"{footer}",
                title="Proof-Driven Verifier (compositional)",
            )
        )
        sys.exit(1)

    proof = result.proof
    assert proof is not None
    per_mod = "\n".join(
        f"  {name:<16} {'PASS' if pb.all_passed else 'FAIL'}"
        for name, pb in proof.per_module.items()
    ) or "  (none)"
    obligations = (
        f"Per-module obligations:\n{per_mod}\n"
        f"Refinement: {proof.refinement.status}"
    )

    trace_block = _format_trace_block(result)

    if result.status == "verified":
        body = (
            f"[bold green]Verified[/bold green] in {result.iterations} iteration(s)\n\n"
            f"{obligations}\n\n"
            f"{trace_block}\n\n"
            f"TLA+:   {result.tla_dir}\n"
            f"Python: {result.python_dir}"
        )
    else:
        body = (
            f"[bold yellow]Unverified[/bold yellow] after {result.iterations} iteration(s)\n\n"
            f"{obligations}\n\n"
            f"{trace_block}"
        )

    console.print(Panel.fit(body, title="Proof-Driven Verifier (compositional)"))
    if result.status != "verified":
        sys.exit(1)


def _format_trace_block(result) -> str:
    """Format the trace-conformance section. Advisory only; never changes exit."""

    if result.trace_skipped_reason:
        return f"Trace conformance: [dim]skipped ({result.trace_skipped_reason})[/dim]"
    if not result.traces:
        return "Trace conformance: [dim]not run[/dim]"
    lines = ["Trace conformance:"]
    for name, tr in result.traces.items():
        colour = {
            "conforms": "green",
            "diverged": "yellow",
            "invariant_violated": "red",
            "empty": "dim",
            "python_crashed": "red",
            "tlc_timeout": "yellow",
            "tlc_error": "red",
            "skipped": "dim",
        }.get(tr.status, "white")
        detail = ""
        if tr.tla_depth is not None and tr.trace_length is not None:
            detail = f" ({tr.tla_depth}/{tr.trace_length} steps)"
        elif tr.divergence_step is not None:
            detail = f" (diverged at step {tr.divergence_step})"
        lines.append(f"  {name:<16} [{colour}]{tr.status}[/{colour}]{detail}")
    return "\n".join(lines)


if __name__ == "__main__":
    app()
