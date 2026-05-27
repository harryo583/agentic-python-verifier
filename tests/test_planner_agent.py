"""Tests for PlannerAgent using a mocked Anthropic client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.agents.planner_agent import (
    DecompositionError,
    MAX_DECOMPOSITION_RETRIES,
    PlannerAgent,
)
from src.llm.anthropic_client import AnthropicClient
from src.llm.prompts import PLANNER_SYSTEM
from src.llm.tools import PROPOSE_DECOMPOSITION_TOOL
from src.models.decomposition import DecompositionPlan
from src.models.task import TaskRequest


# ---------------------------------------------------------------------------
# Fake Anthropic SDK harness (same pattern as test_synth_agent_mocked.py)
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
    """Mimics the bits of the Anthropic SDK we use."""

    def __init__(self, scripted: list[FakeMessage]):
        self.scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []
        self.messages = self  # let `client.messages.create(...)` work

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        if not self.scripted:
            raise AssertionError("FakeAnthropic ran out of scripted responses")
        return self.scripted.pop(0)


def _decomp_block(input_data: dict[str, Any], tool_use_id: str = "tu_1") -> FakeBlock:
    return FakeBlock(
        type="tool_use",
        id=tool_use_id,
        name="propose_decomposition",
        input=input_data,
    )


def _make_client(scripted: list[FakeMessage]) -> tuple[AnthropicClient, FakeAnthropic]:
    fake = FakeAnthropic(scripted)
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
    return client, fake


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_VALID_PLAN_INPUT: dict[str, Any] = {
    "parent_name": "ProducerConsumer",
    "parent_role": "Composes a queue with one producer and one consumer.",
    "modules": [
        {
            "name": "Queue",
            "role": "Bounded FIFO buffer.",
            "abstract_iface": {
                "state_variables": ["items"],
                "actions": ["Enqueue", "Dequeue"],
                "invariant_sketch": "Length stays within MaxSize.",
            },
        },
        {
            "name": "Producer",
            "role": "Generates items and enqueues them.",
            "abstract_iface": {
                "state_variables": ["produced"],
                "actions": ["Produce"],
                "invariant_sketch": "Produced count is non-negative.",
            },
        },
    ],
}

# 5 modules — violates max_length=4 in DecompositionPlan
_INVALID_PLAN_INPUT_TOO_MANY_MODULES: dict[str, Any] = {
    "parent_name": "System",
    "parent_role": "Composes everything.",
    "modules": [
        {
            "name": f"Module{i}",
            "role": f"Role {i}.",
            "abstract_iface": {
                "state_variables": [f"var{i}"],
                "actions": [f"Act{i}"],
                "invariant_sketch": f"Invariant {i}.",
            },
        }
        for i in range(1, 6)  # 5 modules → invalid
    ],
}


# ---------------------------------------------------------------------------
# Scenario 1: Happy path — valid plan on first attempt
# ---------------------------------------------------------------------------

def test_happy_path_returns_valid_plan():
    client, fake = _make_client(
        [FakeMessage(content=[_decomp_block(_VALID_PLAN_INPUT, "tu_1")])]
    )
    agent = PlannerAgent(client)

    plan = agent.decompose(TaskRequest(prompt="producer-consumer system"))

    assert isinstance(plan, DecompositionPlan)
    assert plan.parent_name == "ProducerConsumer"
    assert len(plan.modules) == 2
    assert plan.modules[0].name == "Queue"
    # Only one LLM call on the happy path
    assert len(fake.calls) == 1


# ---------------------------------------------------------------------------
# Scenario 2: Invalid first attempt, valid second attempt — retry logic
# ---------------------------------------------------------------------------

def test_retry_on_schema_violation_then_succeeds():
    client, fake = _make_client(
        [
            FakeMessage(content=[_decomp_block(_INVALID_PLAN_INPUT_TOO_MANY_MODULES, "tu_bad")]),
            FakeMessage(content=[_decomp_block(_VALID_PLAN_INPUT, "tu_good")]),
        ]
    )
    agent = PlannerAgent(client)

    plan = agent.decompose(TaskRequest(prompt="complex system"))

    assert isinstance(plan, DecompositionPlan)
    assert plan.parent_name == "ProducerConsumer"
    # Two LLM calls — one bad, one good
    assert len(fake.calls) == 2

    # Verify the retry's messages payload includes a tool_result with the previous tool_use_id
    second_call_messages = fake.calls[1]["messages"]
    # messages: [initial user msg, assistant block, tool_result user block]
    assert len(second_call_messages) == 3

    tool_result_msg = second_call_messages[2]
    assert tool_result_msg["role"] == "user"
    tool_result_block = tool_result_msg["content"][0]
    assert tool_result_block["type"] == "tool_result"
    assert tool_result_block["tool_use_id"] == "tu_bad"

    # The feedback content should mention the validation problem
    feedback_content = tool_result_block["content"]
    assert "decomposition failed schema validation" in feedback_content


# ---------------------------------------------------------------------------
# Scenario 3: All attempts fail → DecompositionError raised
# ---------------------------------------------------------------------------

def test_all_attempts_fail_raises_decomposition_error():
    # MAX_DECOMPOSITION_RETRIES + 1 == 3 total attempts, all invalid
    scripted = [
        FakeMessage(content=[_decomp_block(_INVALID_PLAN_INPUT_TOO_MANY_MODULES, f"tu_{i}")])
        for i in range(MAX_DECOMPOSITION_RETRIES + 1)
    ]
    client, fake = _make_client(scripted)
    agent = PlannerAgent(client)

    with pytest.raises(DecompositionError) as exc_info:
        agent.decompose(TaskRequest(prompt="intractable system"))

    assert "exhausted" in str(exc_info.value).lower()
    assert len(fake.calls) == MAX_DECOMPOSITION_RETRIES + 1


# ---------------------------------------------------------------------------
# Scenario 4: LLM call uses correct tool_choice and system prompt
# ---------------------------------------------------------------------------

def test_llm_call_uses_correct_tool_choice_and_system():
    client, fake = _make_client(
        [FakeMessage(content=[_decomp_block(_VALID_PLAN_INPUT, "tu_1")])]
    )
    agent = PlannerAgent(client)
    agent.decompose(TaskRequest(prompt="any requirement"))

    call = fake.calls[0]
    # tool_choice must name "propose_decomposition"
    assert call["tool_choice"]["name"] == PROPOSE_DECOMPOSITION_TOOL["name"]
    assert call["tool_choice"]["name"] == "propose_decomposition"

    # system prompt must be PLANNER_SYSTEM (wrapped in a cache_control block by the client)
    system_blocks = call["system"]
    assert isinstance(system_blocks, list)
    system_text = system_blocks[0]["text"]
    assert system_text == PLANNER_SYSTEM
    # Cache control is set (consistent with existing agent pattern)
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}


# ---------------------------------------------------------------------------
# Scenario 5: Retry feedback contains common-cause hints
# ---------------------------------------------------------------------------

def test_retry_feedback_contains_common_cause_hints():
    """The tool_result content sent to the LLM on retry must name known hints."""
    client, fake = _make_client(
        [
            FakeMessage(content=[_decomp_block(_INVALID_PLAN_INPUT_TOO_MANY_MODULES, "tu_bad")]),
            FakeMessage(content=[_decomp_block(_VALID_PLAN_INPUT, "tu_good")]),
        ]
    )
    agent = PlannerAgent(client)
    agent.decompose(TaskRequest(prompt="multi-module system"))

    second_call_messages = fake.calls[1]["messages"]
    tool_result_block = second_call_messages[2]["content"][0]
    feedback = tool_result_block["content"]

    # Must mention the hard-cap hint
    assert "Hard cap is 4" in feedback
