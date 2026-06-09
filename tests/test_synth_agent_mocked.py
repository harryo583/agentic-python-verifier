"""Tests for SynthesisAgent using a mocked Anthropic client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.agents.synth_agent import SynthesisAgent
from src.llm.anthropic_client import AnthropicClient, LLMResponseError, ToolUse
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


def _propose_block(input_data: dict[str, Any], tool_use_id: str = "tu_1") -> FakeBlock:
    return FakeBlock(type="tool_use", id=tool_use_id, name="propose_pluscal_with_invariant", input=input_data)


def _repair_block(input_data: dict[str, Any], tool_use_id: str = "tu_2") -> FakeBlock:
    return FakeBlock(type="tool_use", id=tool_use_id, name="repair_after_counterexample", input=input_data)


def _make_client(scripted: list[FakeMessage]) -> tuple[AnthropicClient, FakeAnthropic]:
    fake = FakeAnthropic(scripted)
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
    return client, fake


def test_propose_returns_validated_proposal_and_history():
    proposal_input = {
        "module_name": "BoundedCounter",
        "slug": "bounded_counter",
        "pluscal": "---- MODULE BoundedCounter ----\n====",
        "constants": {"values": {"MaxValue": [10]}},
    }
    client, fake = _make_client([FakeMessage(content=[_propose_block(proposal_input)])])
    agent = SynthesisAgent(client)

    proposal, history = agent.propose(TaskRequest(prompt="bounded counter"))

    assert isinstance(proposal, SynthesisProposal)
    assert proposal.module_name == "BoundedCounter"
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert any(b.get("type") == "tool_use" for b in history[1]["content"])

    call = fake.calls[0]
    assert call["model"] == "claude-opus-4-7"
    assert call["tool_choice"]["name"] == "propose_pluscal_with_invariant"
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_repair_serialises_failure_and_returns_revision():
    proposal_input = {
        "module_name": "BoundedCounter",
        "slug": "bounded_counter",
        "pluscal": "...",
        "constants": {"values": {"MaxValue": [10]}},
    }
    repair_input = {
        **proposal_input,
        "reasoning": "Strengthened Inv to bound counter from below.",
        "targeted_obligation": "consec",
    }
    client, fake = _make_client(
        [
            FakeMessage(content=[_propose_block(proposal_input, "tu_1")]),
            FakeMessage(content=[_repair_block(repair_input, "tu_2")]),
        ]
    )
    agent = SynthesisAgent(client)
    proposal, history = agent.propose(TaskRequest(prompt="bounded counter"))

    bundle = ProofBundle(
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

    new_proposal, repair_obj, new_history = agent.repair(
        task=TaskRequest(prompt="x"),
        history=history,
        bundle=bundle,
        last_proposal=proposal,
        previous_tool_use_id="tu_1",
    )

    assert repair_obj.targeted_obligation == "consec"
    assert new_proposal.module_name == "BoundedCounter"

    repair_call = fake.calls[1]
    user_tool_result = repair_call["messages"][-1]
    assert user_tool_result["role"] == "user"
    tool_result_block = user_tool_result["content"][0]
    assert tool_result_block["type"] == "tool_result"
    assert tool_result_block["tool_use_id"] == "tu_1"
    assert "consec: FAILED" in tool_result_block["content"]
    assert "counter=11" in tool_result_block["content"]

    assert len(new_history) == 4
    assert new_history[-1]["role"] == "assistant"


def test_extract_tool_use_raises_when_block_absent():
    client, _ = _make_client([FakeMessage(content=[FakeBlock(type="text", text="hi")])])
    agent = SynthesisAgent(client)

    with pytest.raises(LLMResponseError):
        agent.propose(TaskRequest(prompt="x"))
