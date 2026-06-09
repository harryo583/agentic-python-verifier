"""Tests for Verifier.check_bundle (compositional 4-obligation flow).

Mocks pcal.trans and TLC at the formal-module level so the tests don't
require a real tla2tools.jar or a JVM.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents import verifier as verifier_module
from src.agents.verifier import Verifier
from src.config import Settings
from src.formal.tla_runner import TLCRun
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    ModuleSource,
)


# ---------------------------------------------------------------------------
# Settings + bundle helpers
# ---------------------------------------------------------------------------


def _settings(tmp_path: Path) -> Settings:
    jar = tmp_path / "fake.jar"
    jar.write_text("")
    return Settings(
        project_root=tmp_path,
        generated_dir=tmp_path / "gen",
        tla_dir=tmp_path / "gen" / "tla",
        python_dir=tmp_path / "gen" / "python",
        work_dir=tmp_path / "gen" / "work",
        anthropic_api_key="fake",
        openai_api_key=None,
        tla2tools_jar=str(jar),
        model="claude-opus-4-7",
        fallback_model="claude-opus-4-6",
        openai_model="gpt-5.4",
        max_iterations=3,
        tlc_timeout_s=30,
        log_level="INFO",
    )


def _impl(name: str, *, with_abstraction: bool = True) -> ModuleSource:
    abstraction = {"queue": "buffer"} if with_abstraction else {}
    return ModuleSource(
        name=name,
        role="impl",
        tla_source=(
            f"---- MODULE {name}_Impl ----\n"
            "EXTENDS Integers\n"
            "(* --algorithm dummy { skip } *)\n"
            "===="
        ),
        pluscal_source="placeholder",  # truthy → triggers pcal.trans in verifier
        abstraction_map=abstraction,
    )


def _abs(name: str) -> ModuleSource:
    return ModuleSource(
        name=name,
        role="abs",
        tla_source=f"---- MODULE {name}_Abs ----\n====",
    )


def _parent(name: str = "System") -> ModuleSource:
    return ModuleSource(
        name=name,
        role="parent",
        tla_source=f"---- MODULE {name} ----\n====",
    )


def _bundle(slug: str = "queue_system") -> ModuleBundle:
    return ModuleBundle(
        parent=_parent("System"),
        modules=[_abs("Queue"), _impl("Queue")],
        slug=slug,
    )


# ---------------------------------------------------------------------------
# Fake TLC + pcal helpers
# ---------------------------------------------------------------------------


_PASSED_STDOUT = "Model checking completed. No error has been found."


def _tlc_passed(tla_path: Path, cfg_path: Path) -> TLCRun:
    return TLCRun(
        returncode=0,
        stdout=_PASSED_STDOUT,
        stderr="",
        duration_s=0.01,
        timed_out=False,
        cfg_path=cfg_path,
        tla_path=tla_path,
    )


def _tlc_invariant_violated(
    tla_path: Path, cfg_path: Path, predicate: str = "Inv"
) -> TLCRun:
    body = (
        f"Error: Invariant {predicate} is violated.\n"
        "State 1: <Initial predicate>\n"
        "/\\ counter = 11\n"
        "\n"
    )
    return TLCRun(
        returncode=12,
        stdout=body,
        stderr="",
        duration_s=0.01,
        timed_out=False,
        cfg_path=cfg_path,
        tla_path=tla_path,
    )


class _RecordingTLC:
    """Callable that records every (tla, cfg) and returns scripted TLCRuns.

    The verifier passes (tla_path, cfg_path, jar, workdir, timeout); we ignore
    everything but the first two.
    """

    def __init__(self, decide):
        self._decide = decide
        self.calls: list[tuple[Path, Path]] = []

    def __call__(
        self,
        tla_path: Path,
        cfg_path: Path,
        jar,
        workdir,
        timeout_s,
    ) -> TLCRun:
        self.calls.append((tla_path, cfg_path))
        return self._decide(tla_path, cfg_path)


def _install_pcal_noop(monkeypatch) -> list[Path]:
    seen: list[Path] = []

    def fake(tla_path: Path, jar, timeout_s: int = 60) -> None:
        seen.append(tla_path)
        # touch the file as pcal.trans would (real pcal rewrites in place)
        text = tla_path.read_text(encoding="utf-8")
        if "BEGIN TRANSLATION" not in text:
            tla_path.write_text(
                text.replace(
                    "(* --algorithm dummy { skip } *)",
                    "(* --algorithm dummy { skip } *)\n"
                    "\\* BEGIN TRANSLATION\n\\* END TRANSLATION",
                ),
                encoding="utf-8",
            )

    monkeypatch.setattr(verifier_module, "translate_pluscal", fake)
    return seen


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_check_bundle_writes_every_module_file(tmp_path: Path, monkeypatch):
    _install_pcal_noop(monkeypatch)
    monkeypatch.setattr(
        verifier_module,
        "run_tlc",
        _RecordingTLC(lambda t, c: _tlc_passed(t, c)),
    )

    bundle = _bundle()
    work_dir = tmp_path / "work"

    Verifier(_settings(tmp_path)).check_bundle(bundle, work_dir)

    assert (work_dir / "System.tla").exists()
    assert (work_dir / "Queue_Abs.tla").exists()
    assert (work_dir / "Queue_Impl.tla").exists()
    assert (work_dir / "Refinement_System.tla").exists()
    # The bundle's parent text must be preserved verbatim
    assert (work_dir / "System.tla").read_text() == bundle.parent.tla_source


def test_check_bundle_runs_pcal_only_on_impls(tmp_path: Path, monkeypatch):
    seen = _install_pcal_noop(monkeypatch)
    monkeypatch.setattr(
        verifier_module,
        "run_tlc",
        _RecordingTLC(lambda t, c: _tlc_passed(t, c)),
    )

    bundle = ModuleBundle(
        parent=_parent("System"),
        modules=[_abs("Queue"), _impl("Queue"), _abs("Lock"), _impl("Lock")],
        slug="multi",
    )
    work_dir = tmp_path / "work"

    Verifier(_settings(tmp_path)).check_bundle(bundle, work_dir)

    # pcal.trans called once per impl, never on abs or parent.
    called_filenames = {p.name for p in seen}
    assert called_filenames == {"Queue_Impl.tla", "Lock_Impl.tla"}


def test_check_bundle_all_passed_when_all_obligations_pass(tmp_path: Path, monkeypatch):
    _install_pcal_noop(monkeypatch)
    monkeypatch.setattr(
        verifier_module,
        "run_tlc",
        _RecordingTLC(lambda t, c: _tlc_passed(t, c)),
    )

    bundle = _bundle()
    proof = Verifier(_settings(tmp_path)).check_bundle(bundle, tmp_path / "work")

    assert isinstance(proof, CompositionalProofBundle)
    assert proof.all_passed
    assert "Queue" in proof.per_module
    assert proof.per_module["Queue"].all_passed
    assert proof.refinement.obligation == "refinement"
    assert proof.refinement.passed


def test_check_bundle_propagates_per_impl_consec_failure(tmp_path: Path, monkeypatch):
    _install_pcal_noop(monkeypatch)

    def decide(tla_path: Path, cfg_path: Path) -> TLCRun:
        # Fail only the consec aux module for Queue_Impl
        if tla_path.name == "Consec_Queue_Impl.tla":
            return _tlc_invariant_violated(tla_path, cfg_path)
        return _tlc_passed(tla_path, cfg_path)

    recorder = _RecordingTLC(decide)
    monkeypatch.setattr(verifier_module, "run_tlc", recorder)

    proof = Verifier(_settings(tmp_path)).check_bundle(_bundle(), tmp_path / "work")

    assert not proof.all_passed
    assert proof.failing_modules() == ["Queue"]
    assert proof.per_module["Queue"].consec.status == "failed"
    assert proof.per_module["Queue"].init.passed
    assert proof.per_module["Queue"].property.passed
    assert proof.refinement.passed


def test_check_bundle_propagates_refinement_failure(tmp_path: Path, monkeypatch):
    _install_pcal_noop(monkeypatch)

    def decide(tla_path: Path, cfg_path: Path) -> TLCRun:
        if tla_path.name.startswith("Refinement_"):
            return _tlc_invariant_violated(tla_path, cfg_path, predicate="Abs_Queue!Spec")
        return _tlc_passed(tla_path, cfg_path)

    monkeypatch.setattr(verifier_module, "run_tlc", _RecordingTLC(decide))

    proof = Verifier(_settings(tmp_path)).check_bundle(_bundle(), tmp_path / "work")

    assert not proof.all_passed
    assert proof.failing_modules() == []
    assert proof.refinement.status == "failed"
    assert proof.refinement.counterexample is not None


def test_check_bundle_returns_error_when_no_abstraction_maps(tmp_path: Path, monkeypatch):
    _install_pcal_noop(monkeypatch)
    monkeypatch.setattr(
        verifier_module,
        "run_tlc",
        _RecordingTLC(lambda t, c: _tlc_passed(t, c)),
    )

    bundle = ModuleBundle(
        parent=_parent("System"),
        modules=[_abs("Queue"), _impl("Queue", with_abstraction=False)],
        slug="no_map",
    )

    proof = Verifier(_settings(tmp_path)).check_bundle(bundle, tmp_path / "work")

    assert proof.refinement.status == "error"
    assert "no impls" in proof.refinement.note or "nothing to refine" in proof.refinement.note


def test_check_bundle_returns_pcal_error_for_impl_when_translation_fails(
    tmp_path: Path, monkeypatch
):
    def fake_pcal(tla_path: Path, jar, timeout_s: int = 60) -> None:
        from src.formal.pcal_translator import PCalError

        raise PCalError("simulated pcal failure")

    monkeypatch.setattr(verifier_module, "translate_pluscal", fake_pcal)
    monkeypatch.setattr(
        verifier_module,
        "run_tlc",
        _RecordingTLC(lambda t, c: _tlc_passed(t, c)),
    )

    proof = Verifier(_settings(tmp_path)).check_bundle(_bundle(), tmp_path / "work")

    queue_proof = proof.per_module["Queue"]
    assert queue_proof.init.status == "error"
    assert "simulated pcal failure" in queue_proof.init.note
    assert queue_proof.consec.status == "error"
    assert queue_proof.property.status == "error"


def test_check_bundle_writes_refinement_cfg_with_parent_constants(
    tmp_path: Path, monkeypatch
):
    _install_pcal_noop(monkeypatch)
    monkeypatch.setattr(
        verifier_module,
        "run_tlc",
        _RecordingTLC(lambda t, c: _tlc_passed(t, c)),
    )

    parent = ModuleSource(
        name="System",
        role="parent",
        tla_source="---- MODULE System ----\nCONSTANT MaxValue\n====",
        constants={"values": {"MaxValue": [10]}},
    )
    bundle = ModuleBundle(
        parent=parent,
        modules=[_abs("Queue"), _impl("Queue")],
        slug="with_const",
    )

    work_dir = tmp_path / "work"
    Verifier(_settings(tmp_path)).check_bundle(bundle, work_dir)

    cfg = (work_dir / "refinement.cfg").read_text()
    assert "SPECIFICATION Spec" in cfg
    assert "PROPERTY RefinementSpec" in cfg
    assert "MaxValue = 10" in cfg


def test_check_bundle_does_not_collide_cfg_files_across_impls(
    tmp_path: Path, monkeypatch
):
    _install_pcal_noop(monkeypatch)
    monkeypatch.setattr(
        verifier_module,
        "run_tlc",
        _RecordingTLC(lambda t, c: _tlc_passed(t, c)),
    )

    bundle = ModuleBundle(
        parent=_parent("System"),
        modules=[
            _abs("Queue"),
            _impl("Queue"),
            _abs("Lock"),
            _impl("Lock"),
        ],
        slug="multi",
    )

    work_dir = tmp_path / "work"
    Verifier(_settings(tmp_path)).check_bundle(bundle, work_dir)

    # Per-impl cfgs must be namespaced by module name; both impls' cfgs persist.
    for module in ("Queue_Impl", "Lock_Impl"):
        for kind in ("init", "consec", "property"):
            assert (work_dir / f"{module}_{kind}.cfg").exists(), f"missing {module}_{kind}.cfg"
