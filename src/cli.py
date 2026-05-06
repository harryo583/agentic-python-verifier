"""Typer CLI for the agentic verifier."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from src.config import get_settings
from src.main import run_pipeline
from src.utils.file_utils import ensure_directory
from src.utils.logger import configure_logging


app = typer.Typer(add_completion=False, help="Generate verified Python from natural language.")
console = Console()


@app.command()
def generate(
    prompt: str = typer.Argument(..., help="Natural language problem description."),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Run verification."),
    output: Optional[str] = typer.Option(None, "--output", help="Output directory for generated artifacts."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging."),
    llm_provider: Optional[str] = typer.Option(None, "--llm-provider", help="offline, ollama, openai, openai-compatible, or anthropic."),
    llm_model: Optional[str] = typer.Option(None, "--llm-model", help="Model name for the selected provider."),
    llm_base_url: Optional[str] = typer.Option(None, "--llm-base-url", help="Override provider base URL."),
) -> None:
    """Run the full planning, verification, and code-generation pipeline."""

    settings = get_settings(output, verbose, llm_provider, llm_model, llm_base_url)
    ensure_directory(Path(settings.tla_dir))
    ensure_directory(Path(settings.python_dir))
    configure_logging(settings.log_level)
    result = run_pipeline(prompt=prompt, settings=settings, verify=verify)
    console.print(
        Panel.fit(
            (
                f"Task type: {result.task.task_type}\n"
                f"Verification: {result.verification.status}\n"
                f"TLA+: {result.tla_path}\n"
                f"Python: {result.python_path}"
            ),
            title="Agentic Python Verifier",
        )
    )


if __name__ == "__main__":
    app()
