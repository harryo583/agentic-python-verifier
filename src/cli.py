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
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """Run the full co-synthesis pipeline on PROMPT."""

    settings = get_settings(
        output_dir=output,
        verbose=verbose,
        max_iterations=max_iterations,
        model=model,
    )
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

    if result.status == "verified":
        body = (
            f"[bold green]Verified[/bold green] in {result.iterations} iteration(s)\n\n"
            f"{obligations}\n\n"
            f"TLA+:   {result.tla_dir}\n"
            f"Python: {result.python_dir}"
        )
    else:
        body = (
            f"[bold yellow]Unverified[/bold yellow] after {result.iterations} iteration(s)\n\n"
            f"{obligations}"
        )

    console.print(Panel.fit(body, title="Proof-Driven Verifier (compositional)"))
    if result.status != "verified":
        sys.exit(1)


if __name__ == "__main__":
    app()
