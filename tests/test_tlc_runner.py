"""Integration tests for the TLC runner. Gated by TLA2TOOLS_JAR."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from src.agents.verifier import Verifier
from src.config import Settings
from src.models.synthesis import Constants, SynthesisProposal


pytestmark = pytest.mark.integration


_JAR = os.getenv("TLA2TOOLS_JAR") or os.getenv("TLA_TLC_JAR")

needs_jar = pytest.mark.skipif(
    not _JAR or not Path(_JAR).exists(),
    reason="Set TLA2TOOLS_JAR to a valid tla2tools.jar to run integration tests.",
)


FIXTURES = Path(__file__).parent / "fixtures" / "tla"


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        generated_dir=tmp_path / "g",
        tla_dir=tmp_path / "g" / "tla",
        python_dir=tmp_path / "g" / "python",
        work_dir=tmp_path / "g" / "work",
        anthropic_api_key="not-used-in-this-test",
        openai_api_key=None,
        tla2tools_jar=_JAR,
        model="claude-opus-4-7",
        fallback_model="claude-opus-4-6",
        openai_model="gpt-5.4",
        max_iterations=1,
        tlc_timeout_s=120,
        log_level="INFO",
    )


def _proposal_from_fixture(name: str, module: str, slug: str) -> SynthesisProposal:
    pluscal = (FIXTURES / name).read_text(encoding="utf-8")
    return SynthesisProposal(
        module_name=module,
        slug=slug,
        pluscal=pluscal,
        constants=Constants(values={"MaxValue": [3]}),
    )


@needs_jar
def test_known_good_module_passes_all_three_obligations(tmp_path: Path):
    settings = _settings(tmp_path)
    work_dir = tmp_path / "work"

    proposal = _proposal_from_fixture(
        "BoundedCounterGood.tla", "BoundedCounterGood", "bounded_counter_good"
    )
    bundle = Verifier(settings).check(proposal, work_dir)

    assert bundle.init.passed, bundle.init.note + "\n" + bundle.init.raw_stdout[:500]
    assert bundle.consec.passed, bundle.consec.note + "\n" + bundle.consec.raw_stdout[:500]
    assert bundle.property.passed, bundle.property.note + "\n" + bundle.property.raw_stdout[:500]
    assert bundle.all_passed


@needs_jar
def test_bad_invariant_fails_consec_with_counterexample(tmp_path: Path):
    settings = _settings(tmp_path)
    work_dir = tmp_path / "work"

    proposal = _proposal_from_fixture(
        "BoundedCounterBadInv.tla", "BoundedCounterBadInv", "bounded_counter_bad_inv"
    )
    bundle = Verifier(settings).check(proposal, work_dir)

    failing = bundle.failing()
    assert failing, "Expected at least one failing obligation"
    obligations = {r.obligation for r in failing}
    assert "consec" in obligations or "init" in obligations
    failed = next(r for r in failing if r.obligation in {"init", "consec"})
    assert failed.counterexample is not None
    assert failed.counterexample.violated_predicate
