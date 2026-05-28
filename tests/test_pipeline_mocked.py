"""End-to-end pipeline tests with both LLM and verifier mocked."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.verifier import Verifier
from src.config import Settings
from src.llm.anthropic_client import AnthropicClient
from src.main import run_pipeline
from src.models.proof import (
    Counterexample,
    ObligationResult,
    ProofBundle,
    TraceState,
)
from src.models.synthesis import SynthesisProposal
from src.models.task import TaskRequest


@dataclass
class FakeBlock:
    type: str
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    text: str = ""


@dataclass
class FakeMessage:
    content: list[FakeBlock]


class FakeAnthropic:
    def __init__(self, scripted: list[FakeMessage]):
        self.scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        return self.scripted.pop(0)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        generated_dir=tmp_path / "gen",
        tla_dir=tmp_path / "gen" / "tla",
        python_dir=tmp_path / "gen" / "python",
        work_dir=tmp_path / "gen" / "work",
        anthropic_api_key="fake-key",
        tla2tools_jar=str(tmp_path / "fake.jar"),
        model="claude-opus-4-1-20250805",
        fallback_model="claude-opus-4-20250514",
        max_iterations=3,
        tlc_timeout_s=30,
        log_level="INFO",
    )


def _passing_bundle() -> ProofBundle:
    return ProofBundle(
        init=ObligationResult(obligation="init", status="passed"),
        consec=ObligationResult(obligation="consec", status="passed"),
        property=ObligationResult(obligation="property", status="passed"),
    )


def _failing_bundle() -> ProofBundle:
    return ProofBundle(
        init=ObligationResult(obligation="init", status="passed"),
        consec=ObligationResult(
            obligation="consec",
            status="failed",
            counterexample=Counterexample(
                obligation="consec",
                violated_predicate="Inv",
                trace=[TraceState(index=1, action="Initial predicate", assignments={"counter": "11"})],
            ),
        ),
        property=ObligationResult(obligation="property", status="passed"),
    )


class ScriptedVerifier(Verifier):
    """Verifier that returns scripted ProofBundles instead of running TLC."""

    def __init__(self, settings: Settings, scripted: list[ProofBundle]):
        super().__init__(settings)
        self._scripted = list(scripted)
        self.calls: list[SynthesisProposal] = []

    def check(self, proposal: SynthesisProposal, work_dir: Path) -> ProofBundle:  # type: ignore[override]
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / f"{proposal.module_name}.tla").write_text(proposal.pluscal, encoding="utf-8")
        self.calls.append(proposal)
        return self._scripted.pop(0)


_PROPOSAL_INPUT = {
    "module_name": "BoundedCounter",
    "slug": "bounded_counter",
    "pluscal": "---- MODULE BoundedCounter ----\nVARIABLE counter\nInit == counter = 0\nNext == counter' = counter + 1\nInv == counter >= 0\nProperty == counter >= 0\n====",
    "constants": {"values": {"MaxValue": [10]}},
}

_REPAIR_INPUT = {
    **_PROPOSAL_INPUT,
    "reasoning": "Strengthened Inv to bound counter above.",
    "targeted_obligation": "consec",
}

_REFINE_INPUT = {
    "python_module": (
        "def increment(c):\n"
        "    assert c >= 0\n"
        "    nxt = c + 1\n"
        "    assert nxt <= 10\n"
        "    return nxt\n"
    ),
    "entry_function": "increment",
    "assertion_map": [
        {"tla_clause": "counter >= 0", "python_check": "c >= 0"},
        {"tla_clause": "counter <= 10", "python_check": "nxt <= 10"},
    ],
}


def _load_generated_module(path: Path):
    spec = importlib.util.spec_from_file_location("generated_under_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pipeline_succeeds_on_first_iteration(tmp_path: Path):
    fake = FakeAnthropic(
        [
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_1", name="propose_pluscal_with_invariant", input=_PROPOSAL_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_3", name="emit_python_module", input=_REFINE_INPUT)]),
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-1-20250805", client=fake)
    settings = _settings(tmp_path)
    verifier = ScriptedVerifier(settings, [_passing_bundle()])

    result = run_pipeline(
        TaskRequest(prompt="bounded counter from 0 to 10", max_iterations=3),
        settings,
        client=client,
        verifier=verifier,
    )

    assert result.status == "verified"
    assert result.iterations == 1
    assert result.tla_path is not None and result.tla_path.exists()
    assert result.python_path is not None and result.python_path.exists()
    assert "def increment" in result.python_path.read_text()
    artifact_names = {p.name for p in result.artifact_paths}
    assert artifact_names == {
        "proposal.json",
        "proof_bundle.json",
        "iteration_summary.md",
    }

    generated = _load_generated_module(result.python_path)
    assert generated.increment(2) == 3
    try:
        generated.increment(10)
    except AssertionError:
        pass
    else:
        raise AssertionError("generated module did not enforce the upper-bound invariant")


def test_pipeline_repairs_then_succeeds(tmp_path: Path):
    fake = FakeAnthropic(
        [
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_1", name="propose_pluscal_with_invariant", input=_PROPOSAL_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_2", name="repair_after_counterexample", input=_REPAIR_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_3", name="emit_python_module", input=_REFINE_INPUT)]),
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-1-20250805", client=fake)
    settings = _settings(tmp_path)
    Path(settings.tla2tools_jar).write_text("")
    verifier = ScriptedVerifier(settings, [_failing_bundle(), _passing_bundle()])

    result = run_pipeline(
        TaskRequest(prompt="bounded counter", max_iterations=3),
        settings,
        client=client,
        verifier=verifier,
    )

    assert result.status == "verified"
    assert result.iterations == 2
    assert len(verifier.calls) == 2
    assert len(fake.calls) == 3
    assert all(path.exists() for path in result.artifact_paths)

    first_iter = settings.work_dir / "bounded_counter_iter0" / "BoundedCounter.tla"
    second_iter = settings.work_dir / "bounded_counter_iter1" / "BoundedCounter.tla"
    assert first_iter.exists()
    assert second_iter.exists()
    assert first_iter.read_text(encoding="utf-8") == _PROPOSAL_INPUT["pluscal"]
    assert second_iter.read_text(encoding="utf-8") == _REPAIR_INPUT["pluscal"]
    first_iter_dir = settings.work_dir / "bounded_counter_iter0"
    assert (first_iter_dir / "proof_bundle.json").exists()
    assert (first_iter_dir / "repair.json").exists()
    assert "consec" in (first_iter_dir / "repair_summary.md").read_text(encoding="utf-8")

    artifact_names_by_iter = {
        path.parent.name: set()
        for path in result.artifact_paths
    }
    for path in result.artifact_paths:
        artifact_names_by_iter[path.parent.name].add(path.name)
        assert path.exists()
    assert artifact_names_by_iter["bounded_counter_iter0"] == {
        "proposal.json",
        "proof_bundle.json",
        "iteration_summary.md",
        "repair.json",
        "repair_summary.md",
    }
    assert artifact_names_by_iter["bounded_counter_iter1"] == {
        "proposal.json",
        "proof_bundle.json",
        "iteration_summary.md",
    }
    assert "consec: failed" in (
        settings.work_dir / "bounded_counter_iter0" / "iteration_summary.md"
    ).read_text(encoding="utf-8")
    assert "Targeted obligation: consec" in (
        settings.work_dir / "bounded_counter_iter0" / "repair_summary.md"
    ).read_text(encoding="utf-8")


def test_pipeline_exhausts_iterations_and_returns_unverified(tmp_path: Path):
    fake = FakeAnthropic(
        [
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_1", name="propose_pluscal_with_invariant", input=_PROPOSAL_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_2", name="repair_after_counterexample", input=_REPAIR_INPUT)]),
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-1-20250805", client=fake)
    settings = _settings(tmp_path)
    Path(settings.tla2tools_jar).write_text("")
    verifier = ScriptedVerifier(settings, [_failing_bundle(), _failing_bundle()])

    result = run_pipeline(
        TaskRequest(prompt="x", max_iterations=2),
        settings,
        client=client,
        verifier=verifier,
    )

    assert result.status == "unverified"
    assert result.iterations == 2
    assert result.tla_path is None
    assert result.python_path is None
    assert (settings.work_dir / "bounded_counter_iter1" / "iteration_summary.md").exists()
    assert len(result.artifact_paths) == 8
