"""Tests for SynthesisAgent.propose_bundle / repair_bundle using a mocked client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.agents.synth_agent import SynthesisAgent
from src.llm.anthropic_client import AnthropicClient
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
)
from src.models.decomposition import (
    AbstractInterface,
    DecompositionPlan,
    PlanModuleSpec,
)
from src.models.proof import (
    Counterexample,
    ObligationResult,
    ProofBundle,
    TraceState,
)
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


def _propose_bundle_block(
    input_data: dict[str, Any], tool_use_id: str = "tu_b1"
) -> FakeBlock:
    return FakeBlock(
        type="tool_use",
        id=tool_use_id,
        name="propose_module_bundle",
        input=input_data,
    )


def _repair_bundle_block(
    input_data: dict[str, Any], tool_use_id: str = "tu_b2"
) -> FakeBlock:
    return FakeBlock(
        type="tool_use",
        id=tool_use_id,
        name="repair_module_bundle",
        input=input_data,
    )


def _make_client(scripted: list[FakeMessage]) -> tuple[AnthropicClient, FakeAnthropic]:
    fake = FakeAnthropic(scripted)
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
    return client, fake


def _sample_plan() -> DecompositionPlan:
    return DecompositionPlan(
        parent_name="System",
        parent_role="composes a queue and its consumer",
        modules=[
            PlanModuleSpec(
                name="Queue",
                role="bounded FIFO queue",
                abstract_iface=AbstractInterface(
                    state_variables=["queue"],
                    actions=["Enqueue", "Dequeue"],
                    invariant_sketch="queue length stays within bounds",
                ),
            ),
        ],
    )


def _sample_bundle_input() -> dict[str, Any]:
    """A minimal tool-input payload for propose_module_bundle."""

    return {
        "slug": "queue_system",
        "parent": {
            "name": "System",
            "tla_source": "---- MODULE System ----\n====",
        },
        "modules": [
            {
                "name": "Queue",
                "role": "abs",
                "tla_source": "---- MODULE Queue_Abs ----\n====",
            },
            {
                "name": "Queue",
                "role": "impl",
                "tla_source": "---- MODULE Queue_Impl ----\n(* --algorithm Queue ... *)\n====",
                "pluscal_source": "---- MODULE Queue_Impl ----\n(* --algorithm Queue ... *)\n====",
                "abstraction_map": {"queue": "buffer"},
            },
        ],
    }


# ---------------------------------------------------------------------------
# propose_bundle
# ---------------------------------------------------------------------------


def test_propose_bundle_returns_validated_bundle_and_history():
    bundle_input = _sample_bundle_input()
    client, fake = _make_client(
        [FakeMessage(content=[_propose_bundle_block(bundle_input)])]
    )
    agent = SynthesisAgent(client)

    bundle, history, tool_use_id = agent.propose_bundle(
        TaskRequest(prompt="bounded queue and consumer"),
        _sample_plan(),
    )

    assert isinstance(bundle, ModuleBundle)
    assert bundle.slug == "queue_system"
    assert bundle.parent.name == "System"
    assert bundle.parent.role == "parent"
    assert {m.role for m in bundle.modules} == {"abs", "impl"}
    impl = next(m for m in bundle.modules if m.role == "impl")
    assert impl.abstraction_map == {"queue": "buffer"}
    assert impl.pluscal_source is not None
    assert tool_use_id == "tu_b1"

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert any(b.get("type") == "tool_use" for b in history[1]["content"])

    call = fake.calls[0]
    assert call["tool_choice"]["name"] == "propose_module_bundle"
    # System prompt is the BUNDLE variant (cached).
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "ModuleBundle" in call["system"][0]["text"]
    # User message embeds the plan.
    user_text = call["messages"][0]["content"][0]["text"]
    assert "Parent: System" in user_text
    assert "Queue" in user_text
    assert "queue length stays within bounds" in user_text


def test_propose_bundle_rejects_invalid_role_via_pydantic():
    bad_input = _sample_bundle_input()
    bad_input["modules"][0]["role"] = "bogus"
    client, _ = _make_client(
        [FakeMessage(content=[_propose_bundle_block(bad_input)])]
    )
    agent = SynthesisAgent(client)

    with pytest.raises(Exception):  # pydantic ValidationError
        agent.propose_bundle(TaskRequest(prompt="x"), _sample_plan())


# ---------------------------------------------------------------------------
# repair_bundle
# ---------------------------------------------------------------------------


def _failing_compositional_proof() -> CompositionalProofBundle:
    """A CompositionalProofBundle where the Queue impl's consec fails."""

    queue_proof = ProofBundle(
        init=ObligationResult(obligation="init", status="passed"),
        consec=ObligationResult(
            obligation="consec",
            status="failed",
            counterexample=Counterexample(
                obligation="consec",
                violated_predicate="Inv",
                trace=[
                    TraceState(
                        index=1,
                        action="Enqueue",
                        assignments={"buffer": "<<1,2,3>>"},
                    )
                ],
            ),
        ),
        property=ObligationResult(obligation="property", status="passed"),
    )
    return CompositionalProofBundle(
        per_module={"Queue": queue_proof},
        refinement=ObligationResult(obligation="init", status="passed"),
    )


def test_repair_bundle_serialises_failure_and_returns_revision():
    propose_input = _sample_bundle_input()
    repair_input = {
        **propose_input,
        "reasoning": "Strengthened Queue_Impl's Inv to bound buffer length.",
        "targeted_failure": "Queue/consec",
    }
    client, fake = _make_client(
        [
            FakeMessage(content=[_propose_bundle_block(propose_input, "tu_b1")]),
            FakeMessage(content=[_repair_bundle_block(repair_input, "tu_b2")]),
        ]
    )
    agent = SynthesisAgent(client)
    bundle, history, tool_use_id = agent.propose_bundle(
        TaskRequest(prompt="bounded queue"),
        _sample_plan(),
    )

    new_bundle, new_history, new_tool_use_id = agent.repair_bundle(
        history=history,
        proof=_failing_compositional_proof(),
        last_bundle=bundle,
        previous_tool_use_id=tool_use_id,
    )

    assert isinstance(new_bundle, ModuleBundle)
    assert new_tool_use_id == "tu_b2"

    repair_call = fake.calls[1]
    user_tool_result = repair_call["messages"][-1]
    assert user_tool_result["role"] == "user"
    block = user_tool_result["content"][0]
    assert block["type"] == "tool_result"
    assert block["tool_use_id"] == "tu_b1"
    content = block["content"]
    assert "module Queue :: consec: FAILED" in content
    assert "buffer=<<1,2,3>>" in content
    assert "Parent module: System" in content
    assert "repair_module_bundle" in content  # instruction to caller

    assert repair_call["tool_choice"]["name"] == "repair_module_bundle"
    assert len(new_history) == 4
    assert new_history[-1]["role"] == "assistant"


def test_repair_bundle_includes_refinement_failure():
    propose_input = _sample_bundle_input()
    repair_input = {
        **propose_input,
        "reasoning": "Fixed abstraction map.",
        "targeted_failure": "refinement",
    }
    client, fake = _make_client(
        [
            FakeMessage(content=[_propose_bundle_block(propose_input, "tu_b1")]),
            FakeMessage(content=[_repair_bundle_block(repair_input, "tu_b2")]),
        ]
    )
    agent = SynthesisAgent(client)
    bundle, history, tool_use_id = agent.propose_bundle(
        TaskRequest(prompt="bounded queue"),
        _sample_plan(),
    )

    proof = CompositionalProofBundle(
        per_module={
            "Queue": ProofBundle(
                init=ObligationResult(obligation="init", status="passed"),
                consec=ObligationResult(obligation="consec", status="passed"),
                property=ObligationResult(obligation="property", status="passed"),
            )
        },
        refinement=ObligationResult(
            obligation="init",
            status="failed",
            counterexample=Counterexample(
                obligation="init",
                violated_predicate="Abs_Queue!Spec",
                trace=[
                    TraceState(
                        index=0,
                        action="<initial>",
                        assignments={"buffer": "<<>>"},
                    )
                ],
            ),
        ),
    )

    agent.repair_bundle(
        history=history,
        proof=proof,
        last_bundle=bundle,
        previous_tool_use_id=tool_use_id,
    )

    repair_call = fake.calls[1]
    content = repair_call["messages"][-1]["content"][0]["content"]
    assert "refinement obligation: FAILED" in content
    assert "Abs_Queue!Spec" in content
