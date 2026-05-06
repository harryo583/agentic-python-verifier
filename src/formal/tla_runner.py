"""Helpers for running TLC or a deterministic mock verifier."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class TLCExecutionResult:
    """Raw result from a TLC attempt."""

    succeeded: bool
    used_mock: bool
    stdout: str
    stderr: str


def run_tlc(tla_file: Path, tlc_jar_path: Optional[str]) -> TLCExecutionResult:
    """Run TLC if a jar path is configured, otherwise return a mock-verifier marker."""

    if not tlc_jar_path or not Path(tlc_jar_path).exists():
        return TLCExecutionResult(
            succeeded=False,
            used_mock=True,
            stdout="TLC unavailable; using deterministic mock verifier.",
            stderr="",
        )

    java_binary = shutil.which("java")
    if java_binary is None:
        return TLCExecutionResult(
            succeeded=False,
            used_mock=True,
            stdout="Java runtime unavailable; using deterministic mock verifier.",
            stderr="",
        )

    command = [java_binary, "-cp", tlc_jar_path, "tlc2.TLC", str(tla_file)]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return TLCExecutionResult(
        succeeded=completed.returncode == 0,
        used_mock=False,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
