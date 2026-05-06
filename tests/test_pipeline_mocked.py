"""End-to-end pipeline tests with both LLM and verifier mocked."""

from __future__ import annotations

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
        model="claude-opus-4-7",
        fallback_model="claude-opus-4-6",
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
    "python_module": "def increment(c):\n    assert c >= 0\n    return c + 1\n",
    "entry_function": "increment",
    "assertion_map": [{"tla_clause": "counter >= 0", "python_check": "c >= 0"}],
}


def test_pipeline_succeeds_on_first_iteration(tmp_path: Path):
    fake = FakeAnthropic(
        [
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_1", name="propose_pluscal_with_invariant", input=_PROPOSAL_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_3", name="emit_python_module", input=_REFINE_INPUT)]),
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
    settings = _settings(tmp_path)
    Path(settings.tla2tools_jar).write_text("")  # touch the fake jar so require_runtime_settings passes
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


def test_pipeline_repairs_then_succeeds(tmp_path: Path):
    fake = FakeAnthropic(
        [
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_1", name="propose_pluscal_with_invariant", input=_PROPOSAL_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_2", name="repair_after_counterexample", input=_REPAIR_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_3", name="emit_python_module", input=_REFINE_INPUT)]),
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
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


def test_pipeline_exhausts_iterations_and_returns_unverified(tmp_path: Path):
    fake = FakeAnthropic(
        [
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_1", name="propose_pluscal_with_invariant", input=_PROPOSAL_INPUT)]),
            FakeMessage(content=[FakeBlock(type="tool_use", id="tu_2", name="repair_after_counterexample", input=_REPAIR_INPUT)]),
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
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
