"""Entry point and orchestration for the agentic verifier."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.agents.code_generator import CodeGeneratorAgent
from src.agents.planner import PlannerAgent
from src.agents.refiner import RefinerAgent
from src.agents.spec_generator import SpecificationGenerator
from src.agents.verifier import VerifierAgent
from src.config import Settings, get_settings
from src.models.task import TaskSpecification, VerificationResult
from src.utils.file_utils import ensure_directory, write_text
from src.utils.logger import configure_logging


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineResult:
    """Bundle of outputs produced by the pipeline."""

    task: TaskSpecification
    verification: VerificationResult
    tla_path: Path
    python_path: Path


def run_pipeline(prompt: str, settings: Settings, verify: bool = True) -> PipelineResult:
    """Run the full natural-language to verified-Python pipeline."""

    ensure_directory(settings.tla_dir)
    ensure_directory(settings.python_dir)

    planner = PlannerAgent()
    spec_generator = SpecificationGenerator()
    verifier = VerifierAgent(settings)
    refiner = RefinerAgent()
    code_generator = CodeGeneratorAgent()

    task = planner.plan(prompt)
    tla_content = spec_generator.generate(task)
    tla_path = settings.tla_dir / f"{task.slug}.tla"
    write_text(tla_path, tla_content)
    LOGGER.info("Generated TLA+ specification at %s", tla_path)

    verification = verifier.verify(task, tla_path, tla_content) if verify else VerificationResult(
        status="skipped",
        used_mock=True,
        message="Verification skipped by user option.",
        details=["Verification disabled."],
    )

    if verification.status != "success" and verify:
        LOGGER.warning("Initial verification failed; refining specification.")
        task = refiner.refine(task, verification)
        tla_content = spec_generator.generate(task)
        write_text(tla_path, tla_content)
        verification = verifier.verify(task, tla_path, tla_content)

    python_content = code_generator.generate(task, verification)
    python_path = settings.python_dir / f"{task.slug}.py"
    write_text(python_path, python_content)
    LOGGER.info("Generated Python code at %s", python_path)

    return PipelineResult(
        task=task,
        verification=verification,
        tla_path=tla_path,
        python_path=python_path,
    )


def main() -> None:
    """Support `python -m src.main ...` by delegating to the Typer app."""

    import sys

    if len(sys.argv) > 1:
        prompt = sys.argv[1]
        verify = "--no-verify" not in sys.argv
        verbose = "--verbose" in sys.argv
        output = None
        if "--output" in sys.argv:
            output_index = sys.argv.index("--output")
            if output_index + 1 < len(sys.argv):
                output = sys.argv[output_index + 1]
        settings = get_settings(output, verbose)
        configure_logging(settings.log_level)
        result = run_pipeline(prompt, settings, verify=verify)
        LOGGER.info("Python artifact written to %s", result.python_path)
    else:
        from src.cli import app

        app()


if __name__ == "__main__":
    main()
