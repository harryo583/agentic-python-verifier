"""Pydantic model tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.proof import (
    Counterexample,
    ObligationResult,
    ProofBundle,
    TraceState,
)
from src.models.synthesis import Constants, RepairProposal, SynthesisProposal
from src.models.task import TaskRequest


def test_constants_render_single_and_multi_value():
    c = Constants(values={"N": [10], "States": ["A", "B"]})
    lines = c.to_cfg_lines()

    assert "CONSTANT N = 10" in lines
    assert 'CONSTANT States = {"A", "B"}' in lines


def test_synthesis_proposal_validates_module_and_slug():
    SynthesisProposal(
        module_name="BoundedCounter",
        slug="bounded_counter",
        pluscal="---- MODULE BoundedCounter ----\n====",
    )

    with pytest.raises(ValidationError):
        SynthesisProposal(
            module_name="bounded counter",  # space disallowed
            slug="bounded_counter",
            pluscal="...",
        )

    with pytest.raises(ValidationError):
        SynthesisProposal(
            module_name="BoundedCounter",
            slug="BoundedCounter",  # uppercase disallowed
            pluscal="...",
        )


def test_repair_proposal_to_proposal_strips_diagnosis():
    repair = RepairProposal(
        module_name="X",
        slug="x",
        pluscal="...",
        reasoning="strengthened Inv",
        targeted_obligation="consec",
    )

    bare = repair.to_proposal()

    assert isinstance(bare, SynthesisProposal)
    assert not isinstance(bare, RepairProposal)
    assert bare.module_name == "X"


def test_proof_bundle_all_passed_and_failing():
    passed = ObligationResult(obligation="init", status="passed")
    failed = ObligationResult(
        obligation="consec",
        status="failed",
        counterexample=Counterexample(
            obligation="consec",
            violated_predicate="Inv",
            trace=[TraceState(index=1, action="Init", assignments={"x": "0"})],
        ),
    )
    bundle = ProofBundle(
        init=passed,
        consec=failed,
        property=ObligationResult(obligation="property", status="passed"),
    )

    assert not bundle.all_passed
    failing = bundle.failing()
    assert len(failing) == 1
    assert failing[0].obligation == "consec"


def test_task_request_rejects_empty_prompt():
    with pytest.raises(ValidationError):
        TaskRequest(prompt="")


def test_task_request_max_iterations_bounded():
    TaskRequest(prompt="x", max_iterations=1)
    TaskRequest(prompt="x", max_iterations=20)

    with pytest.raises(ValidationError):
        TaskRequest(prompt="x", max_iterations=0)
    with pytest.raises(ValidationError):
        TaskRequest(prompt="x", max_iterations=21)
