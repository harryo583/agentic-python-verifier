"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_FALLBACK_MODEL = "claude-opus-4-6"
DEFAULT_OPENAI_MODEL = "gpt-5.4"


@dataclass(slots=True)
class Settings:
    """Runtime settings for the proof-driven pipeline."""

    project_root: Path
    generated_dir: Path
    tla_dir: Path
    python_dir: Path
    work_dir: Path

    anthropic_api_key: Optional[str]
    openai_api_key: Optional[str]
    tla2tools_jar: Optional[str]
    model: str
    fallback_model: Optional[str]
    openai_model: str
    max_iterations: int
    tlc_timeout_s: int
    log_level: str

    # Week-3 trace-conformance gate
    trace_timeout_s: int = 30
    trace_steps: int = 50
    trace_max_entries: int = 200
    skip_trace_gate: bool = False

    # Efficiency knobs (all default to today's behavior so A/B is clean).
    # #1a — "full" sends the whole growing transcript on each repair (today);
    #       "latest" truncates to [initial task, most-recent attempt] + newest failure.
    repair_history_mode: str = "full"
    # #1b/c — when enabled, abandon a repair chain after `repairs_per_chain`
    #         repairs (or on a repeated failure fingerprint) and reroll from a
    #         fresh propose_bundle. `repairs_per_chain=0` means "never reroll".
    enable_reroll: bool = False
    repairs_per_chain: int = 2
    # #2 — deterministic pre-flight linter; reject known-mechanical errors before
    #      spending a TLC+repair round-trip.
    enable_preflight: bool = False
    # #6 — append frozen few-shot exemplars to the synth/repair system prompts.
    few_shot_enabled: bool = False
    exemplar_pool_dir: Optional[Path] = None


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


def get_settings(
    output_dir: Optional[str] = None,
    verbose: bool = False,
    max_iterations: Optional[int] = None,
    model: Optional[str] = None,
    fallback_model: Optional[str] = None,
) -> Settings:
    """Build application settings from environment and optional CLI overrides."""

    project_root = Path(__file__).resolve().parent.parent
    generated_dir = (
        Path(output_dir).resolve()
        if output_dir
        else project_root / "generated"
    )
    tla_dir = generated_dir / "tla"
    python_dir = generated_dir / "python"
    work_dir = generated_dir / "work"
    log_level = "DEBUG" if verbose else os.getenv("LOG_LEVEL", "INFO")

    return Settings(
        project_root=project_root,
        generated_dir=generated_dir,
        tla_dir=tla_dir,
        python_dir=python_dir,
        work_dir=work_dir,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        tla2tools_jar=os.getenv("TLA2TOOLS_JAR") or os.getenv("TLA_TLC_JAR"),
        model=model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
        fallback_model=fallback_model
        or os.getenv("ANTHROPIC_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        max_iterations=max_iterations
        or int(os.getenv("AGENT_MAX_ITERATIONS", "5")),
        tlc_timeout_s=int(os.getenv("TLC_TIMEOUT_S", "120")),
        log_level=log_level,
        trace_timeout_s=int(os.getenv("TRACE_TIMEOUT_S", "30")),
        trace_steps=int(os.getenv("TRACE_STEPS", "50")),
        trace_max_entries=int(os.getenv("TRACE_MAX_ENTRIES", "200")),
        skip_trace_gate=False,
        repair_history_mode=os.getenv("REPAIR_HISTORY_MODE", "full"),
        enable_reroll=_env_bool("ENABLE_REROLL", False),
        repairs_per_chain=int(os.getenv("REPAIRS_PER_CHAIN", "2")),
        enable_preflight=_env_bool("ENABLE_PREFLIGHT", False),
        few_shot_enabled=_env_bool("FEW_SHOT_ENABLED", False),
        exemplar_pool_dir=project_root / "examples_pool",
    )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def require_runtime_settings(settings: Settings) -> None:
    """Fail fast if mandatory settings are missing."""

    missing: list[str] = []
    if not settings.anthropic_api_key:
        missing.append(
            "ANTHROPIC_API_KEY (set in your environment or a .env file)"
        )
    if not settings.tla2tools_jar:
        missing.append(
            "TLA2TOOLS_JAR (path to tla2tools.jar; supplies pcal.trans and tlc2.TLC)"
        )
    elif not Path(settings.tla2tools_jar).exists():
        missing.append(
            f"TLA2TOOLS_JAR points to a missing file: {settings.tla2tools_jar}"
        )
    if missing:
        joined = "\n  - ".join(missing)
        raise ConfigError(
            "Cannot run the proof-driven pipeline. Missing required settings:\n  - "
            + joined
        )
