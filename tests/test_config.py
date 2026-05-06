"""Tests for configuration and fail-fast behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import ConfigError, Settings, require_runtime_settings


def _make(tmp_path: Path, *, key: str | None, jar: str | None) -> Settings:
    return Settings(
        project_root=tmp_path,
        generated_dir=tmp_path / "g",
        tla_dir=tmp_path / "g" / "tla",
        python_dir=tmp_path / "g" / "python",
        work_dir=tmp_path / "g" / "work",
        anthropic_api_key=key,
        tla2tools_jar=jar,
        model="claude-opus-4-7",
        fallback_model="claude-opus-4-6",
        max_iterations=5,
        tlc_timeout_s=120,
        log_level="INFO",
    )


def test_missing_api_key_fails(tmp_path: Path):
    jar = tmp_path / "tla2tools.jar"
    jar.write_text("")
    settings = _make(tmp_path, key=None, jar=str(jar))

    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        require_runtime_settings(settings)


def test_missing_jar_fails(tmp_path: Path):
    settings = _make(tmp_path, key="sk-x", jar=None)

    with pytest.raises(ConfigError, match="TLA2TOOLS_JAR"):
        require_runtime_settings(settings)


def test_jar_pointing_to_nonexistent_file_fails(tmp_path: Path):
    settings = _make(tmp_path, key="sk-x", jar=str(tmp_path / "nope.jar"))

    with pytest.raises(ConfigError, match="missing file"):
        require_runtime_settings(settings)


def test_full_config_passes(tmp_path: Path):
    jar = tmp_path / "tla2tools.jar"
    jar.write_text("")
    settings = _make(tmp_path, key="sk-x", jar=str(jar))

    require_runtime_settings(settings)  # no raise
