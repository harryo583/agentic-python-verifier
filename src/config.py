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
    llm_provider: str
    llm_model: Optional[str]
    llm_api_key: Optional[str]
    llm_base_url: Optional[str]


def get_settings(
    output_dir: Optional[str] = None,
    verbose: bool = False,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> Settings:
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
    provider = (llm_provider or os.getenv("LLM_PROVIDER", "offline")).strip().lower()
    return Settings(
        project_root=project_root,
        generated_dir=generated_dir,
        tla_dir=tla_dir,
        python_dir=python_dir,
        tlc_jar_path=os.getenv("TLA_TLC_JAR"),
        log_level=log_level,
        llm_provider=provider,
        llm_model=llm_model or os.getenv("LLM_MODEL"),
        llm_api_key=llm_api_key
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY"),
        llm_base_url=llm_base_url or os.getenv("LLM_BASE_URL"),
    )
