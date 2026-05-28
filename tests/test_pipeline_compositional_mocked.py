"""End-to-end compositional pipeline tests with both LLM and verifier mocked."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from src.agents.trace_gate import TraceGate
from src.agents.verifier import Verifier
from src.config import Settings
from src.llm.anthropic_client import AnthropicClient
from src.main import run_compositional_pipeline
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    PythonPackage,
    TraceResult,
)
from src.models.proof import (
    Counterexample,
    ObligationResult,
    ProofBundle,
    TraceState,
)
from src.models.task import TaskRequest


# ---------------------------------------------------------------------------
# Anthropic SDK harness
# ---------------------------------------------------------------------------

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
        if not self.scripted:
            raise AssertionError("FakeAnthropic ran out of scripted responses")
        return self.scripted.pop(0)


def _settings(tmp_path: Path) -> Settings:
    jar = tmp_path / "fake.jar"
    jar.write_text("")
    return Settings(
        project_root=tmp_path,
        generated_dir=tmp_path / "gen",
        tla_dir=tmp_path / "gen" / "tla",
        python_dir=tmp_path / "gen" / "python",
        work_dir=tmp_path / "gen" / "work",
        anthropic_api_key="fake-key",
        openai_api_key=None,
        tla2tools_jar=str(jar),
        model="claude-opus-4-7",
        fallback_model="claude-opus-4-6",
        openai_model="gpt-5.4",
        max_iterations=3,
        tlc_timeout_s=30,
        log_level="INFO",
    )


# ---------------------------------------------------------------------------
# Tool-input fixtures
# ---------------------------------------------------------------------------

_PLAN_INPUT = {
    "parent_name": "System",
    "parent_role": "Composes a queue and a lock.",
    "modules": [
        {
            "name": "Queue",
            "role": "Bounded buffer.",
            "abstract_iface": {
                "state_variables": ["queue"],
                "actions": ["Enqueue"],
                "invariant_sketch": "Length within bounds.",
            },
        },
        {
            "name": "Lock",
            "role": "Mutex.",
            "abstract_iface": {
                "state_variables": ["locked"],
                "actions": ["Acquire"],
                "invariant_sketch": "Mutual exclusion.",
            },
        },
    ],
}


_BUNDLE_INPUT = {
    "slug": "system_qlock",
    "parent": {
        "name": "System",
        "tla_source": "---- MODULE System ----\nVARIABLES q\nInv == TRUE\nProperty == TRUE\n====",
    },
    "modules": [
        {
            "name": "Queue",
            "role": "abs",
            "tla_source": "---- MODULE Queue_Abs ----\nVARIABLE queue\n====",
        },
        {
            "name": "Queue",
            "role": "impl",
            "tla_source": "---- MODULE Queue_Impl ----\n(* --algorithm Q { skip } *)\n====",
            "pluscal_source": "---- MODULE Queue_Impl ----\n(* --algorithm Q { skip } *)\n====",
            "abstraction_map": {"queue": "buffer"},
        },
        {
            "name": "Lock",
            "role": "abs",
            "tla_source": "---- MODULE Lock_Abs ----\nVARIABLE locked\n====",
        },
        {
            "name": "Lock",
            "role": "impl",
            "tla_source": "---- MODULE Lock_Impl ----\n(* --algorithm L { skip } *)\n====",
            "pluscal_source": "---- MODULE Lock_Impl ----\n(* --algorithm L { skip } *)\n====",
            "abstraction_map": {"locked": "held"},
        },
    ],
}


_REPAIRED_BUNDLE_INPUT = {
    **_BUNDLE_INPUT,
    "reasoning": "Strengthened Queue's Inv.",
    "targeted_failure": "Queue/consec",
}


def _emit_child_input(class_name: str) -> dict[str, Any]:
    return {
        "python_module": (
            "from __future__ import annotations\n"
            "import icontract\n"
            "from ._trace import log_action\n"
            f"@icontract.invariant(lambda self: True)\n"
            f"class {class_name}:\n"
            "    def __init__(self) -> None: self.x = 0\n"
            "    def step(self) -> None:\n"
            f"        log_action('{class_name}.Step', {{'x': self.x}})\n"
        ),
        "class_name": class_name,
        "entry_function": "step",
    }


_APP_INPUT = {
    "python_module": (
        "from __future__ import annotations\n"
        "import icontract\n"
        "from ._trace import log_action\n"
        "from .queue import Queue\n"
        "from .lock import Lock\n"
        "@icontract.invariant(lambda self: True)\n"
        "class System:\n"
        "    def __init__(self) -> None:\n"
        "        self.q = Queue()\n"
        "        self.l = Lock()\n"
        "    def step(self) -> None:\n"
        "        self.q.step(); self.l.step()\n"
        "        log_action('System.Step', {})\n"
        "def run(steps: int = 50) -> System:\n"
        "    app = System()\n"
        "    for _ in range(steps): app.step()\n"
        "    return app\n"
    ),
    "class_name": "System",
    "entry_function": "run",
}


def _block(name: str, tool_use_id: str, payload: dict[str, Any]) -> FakeBlock:
    return FakeBlock(type="tool_use", id=tool_use_id, name=name, input=payload)


# ---------------------------------------------------------------------------
# Verifier helpers
# ---------------------------------------------------------------------------


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
                trace=[TraceState(index=1, action="Enqueue", assignments={"buffer": "<<1,2,3,4>>"})],
            ),
        ),
        property=ObligationResult(obligation="property", status="passed"),
    )


class ScriptedVerifier(Verifier):
    """Returns scripted CompositionalProofBundles instead of running TLC."""

    def __init__(self, settings: Settings, scripted: list[CompositionalProofBundle]):
        super().__init__(settings)
        self._scripted = list(scripted)
        self.calls: list[ModuleBundle] = []

    def check_bundle(  # type: ignore[override]
        self, bundle: ModuleBundle, work_dir: Path
    ) -> CompositionalProofBundle:
        work_dir.mkdir(parents=True, exist_ok=True)
        # Materialise every module so _write_bundle_outputs has something to copy.
        for module in (bundle.parent, *bundle.modules):
            (work_dir / module.filename).write_text(module.tla_source, encoding="utf-8")
        self.calls.append(bundle)
        return self._scripted.pop(0)


class StubTraceGate:
    """Bypasses subprocessing + TLC; returns whatever the test scripted."""

    def __init__(self, scripted: dict[str, TraceResult] | None = None):
        self._scripted = scripted if scripted is not None else {}
        self.calls: list[tuple[PythonPackage, ModuleBundle, Path]] = []

    def check(
        self,
        package: PythonPackage,
        bundle: ModuleBundle,
        work_dir: Path,
    ) -> dict[str, TraceResult]:
        work_dir.mkdir(parents=True, exist_ok=True)
        self.calls.append((package, bundle, work_dir))
        return dict(self._scripted)


def _all_passing_proof() -> CompositionalProofBundle:
    return CompositionalProofBundle(
        per_module={
            "Queue": _passing_bundle(),
            "Lock": _passing_bundle(),
        },
        refinement=ObligationResult(obligation="refinement", status="passed"),
    )


def _consec_failure_proof() -> CompositionalProofBundle:
    return CompositionalProofBundle(
        per_module={
            "Queue": _failing_bundle(),
            "Lock": _passing_bundle(),
        },
        refinement=ObligationResult(obligation="refinement", status="passed"),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _make_client(scripted: list[FakeMessage]):
    fake = FakeAnthropic(scripted)
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
    return client, fake


def test_compositional_pipeline_succeeds_on_first_iteration(tmp_path: Path):
    client, fake = _make_client(
        [
            FakeMessage(content=[_block("propose_decomposition", "tu_plan", _PLAN_INPUT)]),
            FakeMessage(content=[_block("propose_module_bundle", "tu_bundle", _BUNDLE_INPUT)]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_q", _emit_child_input("Queue"))]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_l", _emit_child_input("Lock"))]),
            FakeMessage(content=[_block("emit_python_app_for_bundle", "tu_app", _APP_INPUT)]),
        ]
    )
    settings = _settings(tmp_path)
    verifier = ScriptedVerifier(settings, [_all_passing_proof()])

    result = run_compositional_pipeline(
        TaskRequest(prompt="bounded queue + lock", max_iterations=3),
        settings,
        client=client,
        verifier=verifier,
        trace_gate=StubTraceGate(),
    )

    assert result.status == "verified"
    assert result.iterations == 1
    assert result.plan is not None
    assert result.plan.parent_name == "System"
    assert result.bundle is not None
    assert result.bundle.slug == "system_qlock"

    # Output layout: tla_dir/<slug>/ and python_dir/<slug>/
    assert result.tla_dir == settings.tla_dir / "system_qlock"
    assert result.python_dir == settings.python_dir / "system_qlock"
    assert (result.tla_dir / "System.tla").exists()
    assert (result.tla_dir / "Queue_Impl.tla").exists()
    assert (result.python_dir / "queue.py").exists()
    assert (result.python_dir / "lock.py").exists()
    assert (result.python_dir / "app.py").exists()
    assert (result.python_dir / "_trace.py").exists()
    assert (result.python_dir / "__init__.py").exists()

    # _trace.py must be the canonical shim, not whatever the LLM emitted.
    assert "def log_action" in (result.python_dir / "_trace.py").read_text()


def test_compositional_pipeline_repairs_then_succeeds(tmp_path: Path):
    client, fake = _make_client(
        [
            FakeMessage(content=[_block("propose_decomposition", "tu_plan", _PLAN_INPUT)]),
            FakeMessage(content=[_block("propose_module_bundle", "tu_bundle", _BUNDLE_INPUT)]),
            FakeMessage(content=[_block("repair_module_bundle", "tu_repair", _REPAIRED_BUNDLE_INPUT)]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_q", _emit_child_input("Queue"))]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_l", _emit_child_input("Lock"))]),
            FakeMessage(content=[_block("emit_python_app_for_bundle", "tu_app", _APP_INPUT)]),
        ]
    )
    settings = _settings(tmp_path)
    verifier = ScriptedVerifier(
        settings, [_consec_failure_proof(), _all_passing_proof()]
    )

    result = run_compositional_pipeline(
        TaskRequest(prompt="bounded queue + lock", max_iterations=3),
        settings,
        client=client,
        verifier=verifier,
        trace_gate=StubTraceGate(),
    )

    assert result.status == "verified"
    assert result.iterations == 2
    assert len(verifier.calls) == 2
    # 6 LLM calls total: plan, propose, repair, 2 children, app.
    assert len(fake.calls) == 6


def test_compositional_pipeline_exhausts_iterations_and_returns_unverified(tmp_path: Path):
    client, _ = _make_client(
        [
            FakeMessage(content=[_block("propose_decomposition", "tu_plan", _PLAN_INPUT)]),
            FakeMessage(content=[_block("propose_module_bundle", "tu_bundle", _BUNDLE_INPUT)]),
            FakeMessage(content=[_block("repair_module_bundle", "tu_repair", _REPAIRED_BUNDLE_INPUT)]),
        ]
    )
    settings = _settings(tmp_path)
    verifier = ScriptedVerifier(
        settings, [_consec_failure_proof(), _consec_failure_proof()]
    )

    result = run_compositional_pipeline(
        TaskRequest(prompt="x", max_iterations=2),
        settings,
        client=client,
        verifier=verifier,
        trace_gate=StubTraceGate(),
    )

    assert result.status == "unverified"
    assert result.iterations == 2
    assert result.python_dir is None
    assert result.tla_dir is None
    # Verified proof must still surface so the caller can inspect it.
    assert result.proof is not None
    assert "Queue" in result.proof.failing_modules()
    assert result.traces == {}
    assert result.trace_skipped_reason == "package_unverified"


def test_compositional_pipeline_handles_planner_failure(tmp_path: Path):
    """Planner with no scripted responses raises DecompositionError, which the
    pipeline must catch and surface as a clean planner_failed result."""

    # 3 invalid plan attempts (MAX_DECOMPOSITION_RETRIES + 1)
    bad_plan_input = {
        "parent_name": "Sys",
        "parent_role": "many modules",
        "modules": [
            {
                "name": f"M{i}",
                "role": "x",
                "abstract_iface": {
                    "state_variables": ["v"],
                    "actions": ["a"],
                    "invariant_sketch": "x",
                },
            }
            for i in range(5)  # > max_length=4
        ],
    }
    client, _ = _make_client(
        [
            FakeMessage(content=[_block("propose_decomposition", "tu_p", bad_plan_input)])
            for _ in range(3)
        ]
    )
    settings = _settings(tmp_path)
    verifier = ScriptedVerifier(settings, [])

    result = run_compositional_pipeline(
        TaskRequest(prompt="too many", max_iterations=3),
        settings,
        client=client,
        verifier=verifier,
        trace_gate=StubTraceGate(),
    )

    assert result.status == "planner_failed"
    assert result.iterations == 0
    assert result.proof is None
    assert "exhausted" in result.note.lower()
    assert result.trace_skipped_reason == "planner_failed"


def test_compositional_pipeline_threads_trace_result(tmp_path: Path):
    """Successful pipeline runs the trace gate and surfaces results."""

    client, _ = _make_client(
        [
            FakeMessage(content=[_block("propose_decomposition", "tu_plan", _PLAN_INPUT)]),
            FakeMessage(content=[_block("propose_module_bundle", "tu_bundle", _BUNDLE_INPUT)]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_q", _emit_child_input("Queue"))]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_l", _emit_child_input("Lock"))]),
            FakeMessage(content=[_block("emit_python_app_for_bundle", "tu_app", _APP_INPUT)]),
        ]
    )
    settings = _settings(tmp_path)
    verifier = ScriptedVerifier(settings, [_all_passing_proof()])
    gate = StubTraceGate(
        {
            "Queue": TraceResult(
                child_name="Queue",
                status="conforms",
                tla_depth=10,
                trace_length=10,
            ),
            "Lock": TraceResult(
                child_name="Lock",
                status="diverged",
                tla_depth=2,
                trace_length=5,
                divergence_step=3,
                note="example divergence",
            ),
        }
    )

    result = run_compositional_pipeline(
        TaskRequest(prompt="bounded queue + lock", max_iterations=3),
        settings,
        client=client,
        verifier=verifier,
        trace_gate=gate,
    )

    # Pipeline status is unchanged by trace results (advisory only).
    assert result.status == "verified"
    assert result.trace_skipped_reason is None
    assert set(result.traces.keys()) == {"Queue", "Lock"}
    assert result.traces["Queue"].conforms is True
    assert result.traces["Lock"].conforms is False
    assert result.traces["Lock"].divergence_step == 3
    # Gate was invoked exactly once with the expected package + bundle.
    assert len(gate.calls) == 1
    pkg, bundle, work_dir = gate.calls[0]
    assert pkg.slug == "system_qlock"
    assert bundle.slug == "system_qlock"
    assert work_dir.name == "trace"


def test_compositional_pipeline_skip_trace_gate_flag(tmp_path: Path):
    """--skip-trace-gate skips the gate and records the reason."""

    client, _ = _make_client(
        [
            FakeMessage(content=[_block("propose_decomposition", "tu_plan", _PLAN_INPUT)]),
            FakeMessage(content=[_block("propose_module_bundle", "tu_bundle", _BUNDLE_INPUT)]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_q", _emit_child_input("Queue"))]),
            FakeMessage(content=[_block("emit_python_module_for_bundle", "tu_l", _emit_child_input("Lock"))]),
            FakeMessage(content=[_block("emit_python_app_for_bundle", "tu_app", _APP_INPUT)]),
        ]
    )
    settings = _settings(tmp_path)
    settings.skip_trace_gate = True
    verifier = ScriptedVerifier(settings, [_all_passing_proof()])
    gate = StubTraceGate({"should_not_be_called": TraceResult(child_name="x", status="conforms")})

    result = run_compositional_pipeline(
        TaskRequest(prompt="bounded queue + lock", max_iterations=3),
        settings,
        client=client,
        verifier=verifier,
        trace_gate=gate,
    )

    assert result.status == "verified"
    assert result.traces == {}
    assert result.trace_skipped_reason == "skip_trace_gate flag set"
    assert gate.calls == []
