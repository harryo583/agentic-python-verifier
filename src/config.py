"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    """Runtime settings for the pipeline."""

    project_root: Path
    generated_dir: Path
    tla_dir: Path
    python_dir: Path
    tlc_jar_path: Optional[str]
    log_level: str


def get_settings(output_dir: Optional[str] = None, verbose: bool = False) -> Settings:
    """Build application settings from the environment and optional flags."""

    project_root = Path(__file__).resolve().parent.parent
    generated_dir = (
        Path(output_dir).resolve()
        if output_dir
        else project_root / "generated"
    )
    tla_dir = generated_dir / "tla"
    python_dir = generated_dir / "python"
    log_level = "DEBUG" if verbose else os.getenv("LOG_LEVEL", "INFO")
    return Settings(
        project_root=project_root,
        generated_dir=generated_dir,
        tla_dir=tla_dir,
        python_dir=python_dir,
        tlc_jar_path=os.getenv("TLA_TLC_JAR"),
        log_level=log_level,
    )
