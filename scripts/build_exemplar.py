"""Generate a frozen few-shot exemplar by running the compositional pipeline.

A canonical TLA+ spec found online is not in our bundle shape, so we let the
pipeline synthesise + verify a bundle from a reverse-engineered NL prompt and
freeze the verified result as ``examples_pool/<slug>/bundle.json``. The disjoint
exemplar pool is the *method*, not the test set (see ``examples_pool/README.md``).

Usage:

    python scripts/build_exemplar.py --slug mutex --prompt examples_pool/mutex/prompt.txt
    python scripts/build_exemplar.py --slug ticket_lock --prompt-text "A ticket lock ..."
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config import get_settings  # noqa: E402
from src.main import run_compositional_pipeline  # noqa: E402
from src.models.task import TaskRequest  # noqa: E402
from src.utils.logger import configure_logging  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
    slug: str = typer.Option(..., "--slug", help="Exemplar slug (must NOT collide with a benchmark)."),
    prompt: Optional[Path] = typer.Option(None, "--prompt", help="Path to a prompt.txt."),
    prompt_text: Optional[str] = typer.Option(None, "--prompt-text", help="Inline NL prompt."),
    pool: Path = typer.Option(Path("examples_pool"), "--pool", help="Exemplar pool dir."),
    max_iterations: int = typer.Option(6, "--max-iterations", "-n", min=1, max=20),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    configure_logging("DEBUG" if verbose else "INFO")

    if prompt is None and prompt_text is None:
        typer.echo("Provide --prompt PATH or --prompt-text TEXT.", err=True)
        raise typer.Exit(code=1)
    text = prompt_text if prompt_text is not None else prompt.read_text(encoding="utf-8")

    # Guard: exemplar slug must be disjoint from the benchmark suite.
    bench = {d.name for d in Path("examples").iterdir() if d.is_dir()}
    if slug in bench:
        typer.echo(f"Refusing: slug '{slug}' collides with a benchmark (leakage).", err=True)
        raise typer.Exit(code=1)

    settings = get_settings(max_iterations=max_iterations)
    # Exemplar generation must itself be zero-shot (don't seed from the pool).
    settings.few_shot_enabled = False

    task = TaskRequest(prompt=text, slug=slug, max_iterations=max_iterations)
    result = run_compositional_pipeline(task, settings)

    typer.echo(f"status={result.status} iterations={result.iterations} reroll={result.reroll_count}")
    if result.usage is not None:
        typer.echo(f"tokens in/out={result.usage.input_tokens}/{result.usage.output_tokens} est_usd=${result.usage.est_usd:.3f}")

    if result.status != "verified" or result.bundle is None:
        typer.echo("Did NOT verify — adjust the prompt or re-run (synthesis is nondeterministic).", err=True)
        raise typer.Exit(code=2)

    out_dir = pool / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt.txt").write_text(text.strip() + "\n", encoding="utf-8")
    (out_dir / "bundle.json").write_text(result.bundle.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Wrote verified exemplar to {out_dir}/ (prompt.txt + bundle.json)")


if __name__ == "__main__":
    app()
