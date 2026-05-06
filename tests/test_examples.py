"""Unit tests for individual agents and example tasks."""

from __future__ import annotations

from pathlib import Path

from src.agents.code_generator import CodeGeneratorAgent
from src.agents.planner import PlannerAgent
from src.agents.refiner import RefinerAgent
from src.agents.spec_generator import SpecificationGenerator
from src.agents.verifier import VerifierAgent
from src.config import get_settings
from src.models.task import VerificationResult


def test_planner_extracts_bounded_counter_bounds() -> None:
    task = PlannerAgent().plan("Implement a bounded counter from 0 to 10")

    assert task.task_type == "bounded_counter"
    assert task.parameters["min_value"] == 0
    assert task.parameters["max_value"] == 10


def test_spec_generator_contains_invariant() -> None:
    task = PlannerAgent().plan("Implement a bounded counter from 0 to 10")
    specification = SpecificationGenerator().generate(task)

    assert "Invariant ==" in specification
    assert "counter <= 10" in specification


def test_mock_verifier_succeeds_for_bank_transfer(tmp_path: Path) -> None:
    settings = get_settings(str(tmp_path), verbose=False)
    task = PlannerAgent().plan("Implement a bank transfer")
    specification = SpecificationGenerator().generate(task)
    verifier = VerifierAgent(settings)

    result = verifier.verify(task, tmp_path / "bank_transfer.tla", specification)

    assert result.status == "success"
    assert result.used_mock is True


def test_refiner_swaps_invalid_counter_bounds() -> None:
    task = PlannerAgent().plan("Implement a bounded counter from 10 to 0")
    verification = VerificationResult(
        status="failure",
        used_mock=True,
        message="Bounds invalid.",
        details=["Counter lower bound exceeds upper bound."],
    )

    refined = RefinerAgent().refine(task, verification)

    assert refined.parameters["min_value"] == 0
    assert refined.parameters["max_value"] == 10


def test_code_generator_emits_queue_operations() -> None:
    task = PlannerAgent().plan("Implement a queue with enqueue and dequeue")
    code = CodeGeneratorAgent().generate(
        task,
        VerificationResult(
            status="success",
            used_mock=True,
            message="ok",
            details=["ok"],
        ),
    )

    assert "def enqueue" in code
    assert "def dequeue" in code
