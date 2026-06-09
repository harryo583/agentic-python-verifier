"""TLC subprocess wrapper."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TLCRun:
    """Raw outcome of one TLC invocation."""

    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool
    cfg_path: Path
    tla_path: Path


class TLCError(RuntimeError):
    """Raised when TLC cannot be invoked at all (missing java/jar)."""


def run_tlc(
    tla_path: Path,
    cfg_path: Path,
    jar: str,
    workdir: Path,
    timeout_s: int = 120,
) -> TLCRun:
    """Invoke `java -cp <jar> tlc2.TLC -config <cfg> -workers auto -deadlock <tla>`.

    Runs with `workdir` as the cwd so TLC resolves EXTENDS-ed sibling modules.
    """

    java = shutil.which("java")
    if java is None:
        raise TLCError("`java` executable not found on PATH")
    if not Path(jar).exists():
        raise TLCError(f"tla2tools.jar not found at {jar}")
    if not tla_path.exists():
        raise TLCError(f"TLA+ file not found: {tla_path}")
    if not cfg_path.exists():
        raise TLCError(f"TLC config file not found: {cfg_path}")

    cmd = [
        java,
        "-cp",
        jar,
        "tlc2.TLC",
        "-config",
        str(cfg_path.resolve()),
        "-workers",
        "auto",
        "-deadlock",
        str(tla_path.resolve()),
    ]

    started = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(workdir),
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        return TLCRun(
            returncode=-1,
            stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            duration_s=elapsed,
            timed_out=True,
            cfg_path=cfg_path,
            tla_path=tla_path,
        )

    return TLCRun(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_s=time.monotonic() - started,
        timed_out=False,
        cfg_path=cfg_path,
        tla_path=tla_path,
    )
