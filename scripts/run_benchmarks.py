"""Sweep every examples/<slug>/ through the compositional pipeline.

Writes a CSV row per benchmark with the headline numbers we report in the
final write-up (per-module verification rate, refinement rate, trace
conformance counts). Also prints a Markdown summary to stdout.

Invoked directly, not through the CLI: keeps the heavy machinery of
constructing the LLM client + verifier inside `run_compositional_pipeline`
and only times the wrapping call.

Usage:

    python scripts/run_benchmarks.py --out report/bench_results.csv
    python scripts/run_benchmarks.py --only producer_consumer
    python scripts/run_benchmarks.py --skip-trace-gate --max-iterations 5
"""

from __future__ import annotations

import csv
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

# Allow `python scripts/run_benchmarks.py` from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config import get_settings  # noqa: E402
from src.main import run_compositional_pipeline  # noqa: E402
from src.models.task import CompositionalPipelineResult, TaskRequest  # noqa: E402
from src.utils.logger import configure_logging  # noqa: E402


LOGGER = logging.getLogger("benchmarks")


CSV_COLUMNS = [
    "slug",
    "status",
    "iterations",
    "n_modules",
    "n_impls",
    "ref_status",
    "per_module_pass",
    "per_module_fail",
    "trace_conform",
    "trace_diverged",
    "trace_inv_violated",
    "trace_other",
    "pipeline_seconds",
    "total_tlc_seconds",
    "error_note",
]


app = typer.Typer(
    add_completion=False,
    help="Run every examples/<slug>/ through the compositional pipeline.",
)


@dataclass(slots=True)
class _Row:
    slug: str
    status: str
    iterations: int
    n_modules: int
    n_impls: int
    ref_status: str
    per_module_pass: int
    per_module_fail: int
    trace_conform: int
    trace_diverged: int
    trace_inv_violated: int
    trace_other: int
    pipeline_seconds: float
    total_tlc_seconds: float
    error_note: str

    def as_dict(self) -> dict[str, object]:
        return {col: getattr(self, col) for col in CSV_COLUMNS}


@app.command()
def main(
    examples_dir: Path = typer.Option(
        Path("examples"), "--examples", help="Where to find <slug>/prompt.txt."
    ),
    output_csv: Path = typer.Option(
        Path("report/bench_results.csv"),
        "--out",
        help="Where to write the per-benchmark CSV.",
    ),
    max_iterations: int = typer.Option(
        3, "--max-iterations", "-n", min=1, max=20
    ),
    skip_trace_gate: bool = typer.Option(
        False, "--skip-trace-gate", help="Disable the Week-3 trace gate."
    ),
    only: Optional[list[str]] = typer.Option(
        None, "--only", help="Restrict to this slug (repeatable)."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the pipeline on every examples/<slug>/ and emit a results CSV."""

    configure_logging("DEBUG" if verbose else "INFO")

    rows: list[_Row] = []
    only_set = set(only) if only else None

    slug_dirs = sorted(
        d for d in examples_dir.iterdir() if d.is_dir()
    )
    if not slug_dirs:
        typer.echo(f"No benchmark dirs found under {examples_dir}", err=True)
        raise typer.Exit(code=1)

    for slug_dir in slug_dirs:
        slug = slug_dir.name
        if only_set is not None and slug not in only_set:
            continue
        prompt_path = slug_dir / "prompt.txt"
        if not prompt_path.exists():
            LOGGER.warning("skipping %s: no prompt.txt", slug)
            continue

        LOGGER.info("=== running benchmark: %s ===", slug)
        rows.append(
            _run_one(
                slug=slug,
                prompt=prompt_path.read_text(encoding="utf-8"),
                max_iterations=max_iterations,
                skip_trace_gate=skip_trace_gate,
            )
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, output_csv)
    _print_markdown(rows)
    typer.echo(f"\nWrote {len(rows)} row(s) to {output_csv}")


def _run_one(
    *,
    slug: str,
    prompt: str,
    max_iterations: int,
    skip_trace_gate: bool,
) -> _Row:
    settings = get_settings(max_iterations=max_iterations)
    settings.skip_trace_gate = skip_trace_gate
    task = TaskRequest(
        prompt=prompt,
        slug=slug,
        max_iterations=max_iterations,
    )
    t0 = time.monotonic()
    try:
        result = run_compositional_pipeline(task, settings)
        elapsed = time.monotonic() - t0
        return _row_from_result(slug, result, elapsed)
    except Exception as exc:  # noqa: BLE001 - we want to capture every crash
        elapsed = time.monotonic() - t0
        LOGGER.exception("benchmark %s crashed", slug)
        return _Row(
            slug=slug,
            status="crashed",
            iterations=0,
            n_modules=0,
            n_impls=0,
            ref_status="",
            per_module_pass=0,
            per_module_fail=0,
            trace_conform=0,
            trace_diverged=0,
            trace_inv_violated=0,
            trace_other=0,
            pipeline_seconds=elapsed,
            total_tlc_seconds=0.0,
            error_note=str(exc)[:400],
        )


def _row_from_result(
    slug: str,
    result: CompositionalPipelineResult,
    elapsed: float,
) -> _Row:
    n_modules = len(result.plan.modules) if result.plan else 0
    impls = result.bundle.impls() if result.bundle else []
    n_impls = len(impls)
    ref_status = result.proof.refinement.status if result.proof else ""

    per_module_pass = 0
    per_module_fail = 0
    if result.proof is not None:
        for pb in result.proof.per_module.values():
            if pb.all_passed:
                per_module_pass += 1
            else:
                per_module_fail += 1

    total_tlc = 0.0
    if result.proof is not None:
        for pb in result.proof.per_module.values():
            for ob in (pb.init, pb.consec, pb.property):
                total_tlc += ob.duration_s or 0.0
        total_tlc += result.proof.refinement.duration_s or 0.0

    trace_conform = sum(1 for t in result.traces.values() if t.status == "conforms")
    trace_diverged = sum(1 for t in result.traces.values() if t.status == "diverged")
    trace_inv = sum(
        1 for t in result.traces.values() if t.status == "invariant_violated"
    )
    trace_other = (
        len(result.traces) - trace_conform - trace_diverged - trace_inv
    )

    error_note = ""
    if result.status == "planner_failed":
        error_note = result.note or "planner_failed"
    elif result.status == "unverified":
        failing = (
            ",".join(result.proof.failing_modules())
            if result.proof
            else ""
        )
        error_note = f"failing_modules={failing}"

    return _Row(
        slug=slug,
        status=result.status,
        iterations=result.iterations,
        n_modules=n_modules,
        n_impls=n_impls,
        ref_status=ref_status,
        per_module_pass=per_module_pass,
        per_module_fail=per_module_fail,
        trace_conform=trace_conform,
        trace_diverged=trace_diverged,
        trace_inv_violated=trace_inv,
        trace_other=trace_other,
        pipeline_seconds=round(elapsed, 2),
        total_tlc_seconds=round(total_tlc, 2),
        error_note=error_note[:400],
    )


def _write_csv(rows: list[_Row], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())


def _print_markdown(rows: list[_Row]) -> None:
    if not rows:
        return
    headers = [
        "slug",
        "status",
        "iters",
        "per-mod",
        "ref",
        "trace",
        "time",
    ]
    typer.echo("")
    typer.echo("| " + " | ".join(headers) + " |")
    typer.echo("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        per_mod = f"{row.per_module_pass}/{row.per_module_pass + row.per_module_fail}"
        trace = f"{row.trace_conform}c/{row.trace_diverged}d/{row.trace_inv_violated}i"
        typer.echo(
            "| "
            + " | ".join(
                [
                    row.slug,
                    row.status,
                    str(row.iterations),
                    per_mod,
                    row.ref_status or "-",
                    trace,
                    f"{row.pipeline_seconds:.1f}s",
                ]
            )
            + " |"
        )


if __name__ == "__main__":
    app()
