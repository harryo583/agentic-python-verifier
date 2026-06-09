"""Wrapper around `pcal.trans` (bundled in tla2tools.jar)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PCalError(RuntimeError):
    """Raised when pcal.trans fails to translate a PlusCal block."""


def translate_pluscal(tla_path: Path, jar: str, timeout_s: int = 60) -> None:
    """Run pcal.trans on the file. Rewrites it in place to insert
    the `\\* BEGIN TRANSLATION` ... `\\* END TRANSLATION` block.
    """

    java = shutil.which("java")
    if java is None:
        raise PCalError("`java` executable not found on PATH")
    if not Path(jar).exists():
        raise PCalError(f"tla2tools.jar not found at {jar}")
    if not tla_path.exists():
        raise PCalError(f"TLA+ file not found: {tla_path}")

    cmd = [java, "-cp", jar, "pcal.trans", str(tla_path)]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise PCalError(f"pcal.trans timed out after {timeout_s}s") from exc

    if completed.returncode != 0:
        raise PCalError(
            f"pcal.trans failed (exit {completed.returncode})\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    text = tla_path.read_text(encoding="utf-8")
    if "BEGIN TRANSLATION" not in text:
        raise PCalError(
            "pcal.trans returned 0 but produced no translation block. "
            "The PlusCal algorithm may be missing or malformed.\n"
            f"stdout:\n{completed.stdout}"
        )
