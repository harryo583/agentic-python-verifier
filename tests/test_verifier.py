"""Unit tests for verifier failure handling."""

from __future__ import annotations

from pathlib import Path

from src.agents.verifier import Verifier
from src.config import Settings
from src.formal.tla_runner import TLCError
from src.models.synthesis import SynthesisProposal


def _settings(tmp_path: Path) -> Settings:
    jar = tmp_path / "tla2tools.jar"
    jar.write_text("", encoding="utf-8")
    return Settings(
        project_root=tmp_path,
        generated_dir=tmp_path / "g",
        tla_dir=tmp_path / "g" / "tla",
        python_dir=tmp_path / "g" / "python",
        work_dir=tmp_path / "g" / "work",
        anthropic_api_key="not-used",
        tla2tools_jar=str(jar),
        model="claude-opus-4-1-20250805",
        fallback_model="claude-opus-4-20250514",
        max_iterations=1,
        tlc_timeout_s=120,
        log_level="INFO",
    )


def test_tlc_invocation_error_returns_error_bundle(tmp_path: Path, monkeypatch):
    def fake_translate(_tla_path: Path, _jar: str) -> None:
        return None

    def fake_run_tlc(*_args, **_kwargs):
        raise TLCError("java executable not found")

    monkeypatch.setattr("src.agents.verifier.translate_pluscal", fake_translate)
    monkeypatch.setattr("src.agents.verifier.run_tlc", fake_run_tlc)

    proposal = SynthesisProposal(
        module_name="BoundedCounter",
        slug="bounded_counter",
        pluscal="---- MODULE BoundedCounter ----\n====\n",
    )

    bundle = Verifier(_settings(tmp_path)).check(proposal, tmp_path / "work")

    assert not bundle.all_passed
    assert bundle.init.status == "error"
    assert bundle.consec.status == "error"
    assert bundle.property.status == "error"
    assert "tlc stage failed" in bundle.init.note
    assert "java executable not found" in bundle.init.note
