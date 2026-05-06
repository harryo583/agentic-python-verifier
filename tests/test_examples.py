"""Unit tests for individual agents and example tasks."""

from __future__ import annotations

from pathlib import Path

from src.agents.code_generator import CodeGeneratorAgent
from src.agents.planner import PlannerAgent
from src.agents.refiner import RefinerAgent
from src.agents.spec_generator import SpecificationGenerator
from src.agents.verifier import VerifierAgent
from src.config import get_settings
from src.llm import LLMClient, parse_json_object
from src.models.task import VerificationResult


class FakeLLM:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = responses

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, object]:
        return self.responses.pop(0)


class FakeRawLLM(LLMClient):
    def __init__(self, responses: list[str]) -> None:
        super().__init__(provider="mock-raw", model="fake")
        self.responses = responses

    @property
    def enabled(self) -> bool:
        return True

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.responses.pop(0)


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


def test_parse_json_object_extracts_markdown_fenced_json() -> None:
    parsed = parse_json_object(
        """Here is the JSON:
```json
{"outer": {"inner": 1}, "items": [1, 2]}
```
"""
    )

    assert parsed == {"outer": {"inner": 1}, "items": [1, 2]}


def test_complete_json_retries_after_parse_failure() -> None:
    llm = FakeRawLLM(["not json", '{"ok": true}'])

    assert llm.complete_json("system", "user") == {"ok": True}


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


def test_agents_can_use_llm_for_custom_prompt() -> None:
    llm = FakeLLM(
        [
            {
                "name": "ToggleFlag",
                "slug": "toggle_flag",
                "task_type": "custom",
                "description": "toggle a boolean flag",
                "inputs": ["flag"],
                "outputs": ["flag"],
                "state_variables": {"flag": False},
                "preconditions": ["flag is boolean"],
                "postconditions": ["result is boolean"],
                "invariants": ["flag \\in BOOLEAN"],
                "operations": ["toggle"],
                "parameters": {},
                "assumptions": ["toggle flips the flag"],
            },
            {
                "pluscal_spec": """------------------------------ MODULE ToggleFlag ------------------------------
EXTENDS TLC

(* --algorithm ToggleFlag
variables flag = FALSE;
begin
  Toggle:
    flag := ~flag;
end algorithm; *)

Invariant == flag \\in BOOLEAN
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
""",
            },
            {
                "python_code": '''"""Generated implementation."""

def toggle(flag: bool) -> bool:
    assert isinstance(flag, bool)
    result = not flag
    assert isinstance(result, bool)
    return result
''',
            },
        ]
    )

    task = PlannerAgent(llm_client=llm).plan("toggle a boolean flag")
    specification = SpecificationGenerator(llm_client=llm).generate(task)
    code = CodeGeneratorAgent(llm_client=llm).generate(
        task,
        VerificationResult(status="success", used_mock=True, message="ok", details=[]),
    )

    assert task.task_type == "custom"
    assert "--algorithm ToggleFlag" in specification
    assert "def toggle" in code
