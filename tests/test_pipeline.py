"""Integration tests for the full pipeline."""

from __future__ import annotations

from pathlib import Path

from src.config import get_settings
from src.main import run_pipeline
from src.utils.file_utils import read_text


def test_pipeline_generates_bounded_counter_artifacts(tmp_path: Path) -> None:
    settings = get_settings(str(tmp_path), verbose=False)
    result = run_pipeline("Implement a bounded counter from 0 to 10", settings, verify=True)

    assert result.verification.status == "success"
    assert result.verification.used_mock is True
    assert result.tla_path.exists()
    assert result.python_path.exists()
    assert "--algorithm BoundedCounter" in read_text(result.tla_path)
    assert "def increment" in read_text(result.python_path)


def test_pipeline_generates_bank_transfer_code(tmp_path: Path) -> None:
    settings = get_settings(str(tmp_path), verbose=False)
    result = run_pipeline(
        "Implement a bank transfer that preserves total balance",
        settings,
        verify=True,
    )

    python_code = read_text(result.python_path)
    assert result.verification.status == "success"
    assert "def transfer" in python_code
    assert "assert new_source + new_target == total_funds" in python_code
