"""CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from src.cli import app


def test_cli_fails_fast_when_anthropic_api_key_is_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TLA2TOOLS_JAR", raising=False)
    monkeypatch.delenv("TLA_TLC_JAR", raising=False)

    runner = CliRunner()
    result = runner.invoke(app, ["bounded counter", "--output", str(tmp_path)])

    assert result.exit_code == 2
    assert "Configuration error" in result.stdout
    assert "ANTHROPIC_API_KEY" in result.stdout


def test_cli_help_lists_options():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--max-iterations" in result.stdout
    assert "--model" in result.stdout
