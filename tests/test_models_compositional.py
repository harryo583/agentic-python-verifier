"""Unit tests for compositional pipeline data models.

Covers DecompositionPlan / PlanModuleSpec / AbstractInterface (decomposition.py)
and ModuleSource / ModuleBundle / CompositionalProofBundle (bundle.py).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.decomposition import (
    AbstractInterface,
    DecompositionPlan,
    PlanModuleSpec,
)
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    ModuleSource,
)
from src.models.proof import ObligationResult, ProofBundle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obligation(status: str = "passed") -> ObligationResult:
    return ObligationResult(obligation="init", status=status)  # type: ignore[arg-type]


def _passing_proof_bundle() -> ProofBundle:
    return ProofBundle(
        init=ObligationResult(obligation="init", status="passed"),
        consec=ObligationResult(obligation="consec", status="passed"),
        property=ObligationResult(obligation="property", status="passed"),
    )


def _failing_proof_bundle() -> ProofBundle:
    return ProofBundle(
        init=ObligationResult(obligation="init", status="passed"),
        consec=ObligationResult(obligation="consec", status="failed"),
        property=ObligationResult(obligation="property", status="passed"),
    )


def _plan_module(name: str = "Queue") -> PlanModuleSpec:
    return PlanModuleSpec(
        name=name,
        role="manages a FIFO queue",
        abstract_iface=AbstractInterface(),
    )


def _impl_source(name: str = "Queue") -> ModuleSource:
    return ModuleSource(
        name=name,
        role="impl",
        tla_source="---- MODULE Queue_Impl ----\n====",
        pluscal_source="(* --algorithm Queue ... *)",
        abstraction_map={"head": "queue[1]"},
    )


def _abs_source(name: str = "Queue") -> ModuleSource:
    return ModuleSource(
        name=name,
        role="abs",
        tla_source="---- MODULE Queue_Abs ----\n====",
    )


def _parent_source(name: str = "System") -> ModuleSource:
    return ModuleSource(
        name=name,
        role="parent",
        tla_source="---- MODULE System ----\n====",
    )


# ---------------------------------------------------------------------------
# 1. AbstractInterface accepts default-empty lists
# ---------------------------------------------------------------------------

def test_abstract_interface_default_empty():
    iface = AbstractInterface()
    assert iface.state_variables == []
    assert iface.actions == []
    assert iface.invariant_sketch == ""


# ---------------------------------------------------------------------------
# 2. PlanModuleSpec rejects invalid module names
# ---------------------------------------------------------------------------

def test_plan_module_spec_rejects_digit_start():
    with pytest.raises(ValidationError):
        PlanModuleSpec(
            name="1queue",  # must start with a letter, not a digit
            role="manages a queue",
            abstract_iface=AbstractInterface(),
        )


def test_plan_module_spec_rejects_name_with_space():
    with pytest.raises(ValidationError):
        PlanModuleSpec(
            name="My Queue",  # space disallowed
            role="manages a queue",
            abstract_iface=AbstractInterface(),
        )


def test_plan_module_spec_accepts_valid_name():
    spec = _plan_module("Queue2")
    assert spec.name == "Queue2"


# ---------------------------------------------------------------------------
# 3. DecompositionPlan rejects empty modules list and >4 modules
# ---------------------------------------------------------------------------

def test_decomposition_plan_rejects_empty_modules():
    with pytest.raises(ValidationError):
        DecompositionPlan(
            parent_name="System",
            parent_role="composes everything",
            modules=[],
        )


def test_decomposition_plan_rejects_more_than_four_modules():
    with pytest.raises(ValidationError):
        DecompositionPlan(
            parent_name="System",
            parent_role="composes everything",
            modules=[
                _plan_module("QueueA"),
                _plan_module("QueueB"),
                _plan_module("QueueC"),
                _plan_module("QueueD"),
                _plan_module("QueueE"),
            ],
        )


def test_decomposition_plan_accepts_one_to_four_modules():
    plan = DecompositionPlan(
        parent_name="System",
        parent_role="composes everything",
        modules=[_plan_module("Queue")],
    )
    assert len(plan.modules) == 1

    plan4 = DecompositionPlan(
        parent_name="System",
        parent_role="composes everything",
        modules=[
            _plan_module("QueueA"),
            _plan_module("QueueB"),
            _plan_module("QueueC"),
            _plan_module("QueueD"),
        ],
    )
    assert len(plan4.modules) == 4


# ---------------------------------------------------------------------------
# 4. DecompositionPlan rejects duplicate names (modules vs parent)
# ---------------------------------------------------------------------------

def test_decomposition_plan_rejects_duplicate_module_names():
    with pytest.raises(ValidationError):
        DecompositionPlan(
            parent_name="System",
            parent_role="composes everything",
            modules=[_plan_module("Queue"), _plan_module("Queue")],
        )


def test_decomposition_plan_rejects_module_name_colliding_with_parent():
    with pytest.raises(ValidationError):
        DecompositionPlan(
            parent_name="Queue",
            parent_role="composes everything",
            modules=[_plan_module("Queue")],
        )


# ---------------------------------------------------------------------------
# 5. ModuleSource(role="impl") accepts pluscal_source and abstraction_map;
#    filename property returns <name>_Impl.tla
# ---------------------------------------------------------------------------

def test_module_source_impl_accepts_pluscal_and_abstraction_map():
    impl = _impl_source("Queue")
    assert impl.pluscal_source is not None
    assert impl.abstraction_map == {"head": "queue[1]"}


def test_module_source_impl_filename():
    assert _impl_source("Queue").filename == "Queue_Impl.tla"


# ---------------------------------------------------------------------------
# 6. ModuleSource(role="abs") rejects pluscal_source; filename returns <name>_Abs.tla
# ---------------------------------------------------------------------------

def test_module_source_abs_rejects_pluscal_source():
    with pytest.raises(ValidationError):
        ModuleSource(
            name="Queue",
            role="abs",
            tla_source="---- MODULE Queue_Abs ----\n====",
            pluscal_source="(* --algorithm Queue ... *)",
        )


def test_module_source_abs_filename():
    assert _abs_source("Queue").filename == "Queue_Abs.tla"


# ---------------------------------------------------------------------------
# 7. ModuleSource(role="parent") rejects abstraction_map; filename returns <name>.tla
# ---------------------------------------------------------------------------

def test_module_source_parent_rejects_abstraction_map():
    with pytest.raises(ValidationError):
        ModuleSource(
            name="System",
            role="parent",
            tla_source="---- MODULE System ----\n====",
            abstraction_map={"x": "y"},
        )


def test_module_source_parent_filename():
    assert _parent_source("System").filename == "System.tla"


# ---------------------------------------------------------------------------
# 8. ModuleBundle rejects a parent ModuleSource whose role != "parent"
# ---------------------------------------------------------------------------

def test_module_bundle_rejects_non_parent_in_parent_field():
    with pytest.raises(ValidationError):
        ModuleBundle(
            parent=_impl_source("Queue"),  # wrong role
            modules=[_abs_source("Queue")],
            slug="queue_system",
        )


# ---------------------------------------------------------------------------
# 9. ModuleBundle rejects any module in modules[] whose role == "parent"
# ---------------------------------------------------------------------------

def test_module_bundle_rejects_parent_role_in_modules():
    with pytest.raises(ValidationError):
        ModuleBundle(
            parent=_parent_source("System"),
            modules=[_parent_source("AnotherParent")],
            slug="queue_system",
        )


# ---------------------------------------------------------------------------
# 10. ModuleBundle rejects duplicate filenames
# ---------------------------------------------------------------------------

def test_module_bundle_rejects_duplicate_filenames():
    # Two abs modules with the same name produce identical filenames
    with pytest.raises(ValidationError):
        ModuleBundle(
            parent=_parent_source("System"),
            modules=[_abs_source("Queue"), _abs_source("Queue")],
            slug="queue_system",
        )


# ---------------------------------------------------------------------------
# 11. ModuleBundle.impls() and .abstractions() partition modules correctly
# ---------------------------------------------------------------------------

def test_module_bundle_impls_and_abstractions_partition():
    bundle = ModuleBundle(
        parent=_parent_source("System"),
        modules=[
            _abs_source("Queue"),
            _impl_source("Queue"),
            _abs_source("Counter"),
            _impl_source("Counter"),
        ],
        slug="system",
    )

    impls = bundle.impls()
    abstractions = bundle.abstractions()

    assert len(impls) == 2
    assert len(abstractions) == 2
    assert all(m.role == "impl" for m in impls)
    assert all(m.role == "abs" for m in abstractions)
    # Together they cover all modules
    assert set(m.name for m in impls) | set(m.name for m in abstractions) == {
        "Queue",
        "Counter",
    }


# ---------------------------------------------------------------------------
# 12. CompositionalProofBundle.all_passed is True only when refinement passes
#     AND every per_module ProofBundle passes
# ---------------------------------------------------------------------------

def test_compositional_proof_bundle_all_passed_true():
    cpb = CompositionalProofBundle(
        per_module={"Queue": _passing_proof_bundle()},
        refinement=ObligationResult(obligation="init", status="passed"),
    )
    assert cpb.all_passed is True


def test_compositional_proof_bundle_all_passed_false_when_refinement_fails():
    cpb = CompositionalProofBundle(
        per_module={"Queue": _passing_proof_bundle()},
        refinement=ObligationResult(obligation="init", status="failed"),
    )
    assert cpb.all_passed is False


def test_compositional_proof_bundle_all_passed_false_when_module_fails():
    cpb = CompositionalProofBundle(
        per_module={"Queue": _failing_proof_bundle()},
        refinement=ObligationResult(obligation="init", status="passed"),
    )
    assert cpb.all_passed is False


def test_compositional_proof_bundle_all_passed_false_when_both_fail():
    cpb = CompositionalProofBundle(
        per_module={"Queue": _failing_proof_bundle()},
        refinement=ObligationResult(obligation="init", status="failed"),
    )
    assert cpb.all_passed is False


# ---------------------------------------------------------------------------
# 13. CompositionalProofBundle.failing_modules() lists exactly the modules
#     whose ProofBundle has a failing obligation
# ---------------------------------------------------------------------------

def test_failing_modules_empty_when_all_pass():
    cpb = CompositionalProofBundle(
        per_module={
            "Queue": _passing_proof_bundle(),
            "Counter": _passing_proof_bundle(),
        },
        refinement=ObligationResult(obligation="init", status="passed"),
    )
    assert cpb.failing_modules() == []


def test_failing_modules_lists_only_failing_ones():
    cpb = CompositionalProofBundle(
        per_module={
            "Queue": _passing_proof_bundle(),
            "Counter": _failing_proof_bundle(),
            "Lock": _failing_proof_bundle(),
        },
        refinement=ObligationResult(obligation="init", status="passed"),
    )
    failing = cpb.failing_modules()
    assert set(failing) == {"Counter", "Lock"}
    assert "Queue" not in failing
