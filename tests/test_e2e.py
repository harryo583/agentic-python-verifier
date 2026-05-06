"""Live end-to-end test. Gated by ANTHROPIC_API_KEY and TLA2TOOLS_JAR."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.config import get_settings
from src.main import run_pipeline
from src.models.task import TaskRequest


pytestmark = pytest.mark.integration


needs_keys = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY")
    or not (os.getenv("TLA2TOOLS_JAR") or os.getenv("TLA_TLC_JAR")),
    reason=(
        "Set ANTHROPIC_API_KEY and TLA2TOOLS_JAR to run live e2e tests. "
        "These will incur API costs."
    ),
)


@needs_keys
def test_e2e_bounded_counter(tmp_path: Path):
    settings = get_settings(output_dir=str(tmp_path), max_iterations=5)
    task = TaskRequest(
        prompt="Implement a bounded counter from 0 to 5 that increments and never exceeds the bound.",
        max_iterations=5,
    )

    result = run_pipeline(task, settings)

    assert result.status == "verified", (
        f"Pipeline failed to verify after {result.iterations} iteration(s).\n"
        f"Init: {result.bundle.init.note}\n"
        f"Consec: {result.bundle.consec.note}\n"
        f"Property: {result.bundle.property.note}"
    )
    assert result.tla_path is not None and result.tla_path.exists()
    assert result.python_path is not None and result.python_path.exists()
    assert "BEGIN TRANSLATION" in result.tla_path.read_text()
    assert "assert" in result.python_path.read_text()
