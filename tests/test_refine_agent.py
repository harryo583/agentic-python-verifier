"""Tests for the refinement agent (PlusCal -> Python)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agents.refine_agent import RefineAgent, _split_invariant_conjuncts
from src.llm.anthropic_client import AnthropicClient
from src.models.synthesis import SynthesisProposal


_PLUSCAL = """\
---- MODULE BoundedCounter ----
EXTENDS Integers

VARIABLE counter

Init == counter = 0
Next == counter' = counter + 1

Inv == counter >= 0
    /\\ counter <= 10
    /\\ counter \\in 0..10

Property == counter <= 10

====
"""


def test_split_invariant_conjuncts_extracts_three_clauses():
    parts = _split_invariant_conjuncts(_PLUSCAL, "Inv")

    assert parts[0].startswith("counter >= 0")
    assert any("counter <= 10" in p for p in parts)
    assert any("\\in 0..10" in p for p in parts)


def test_split_invariant_conjuncts_respects_nested_conjunctions():
    pluscal = """\
---- MODULE NestedInv ----
VARIABLE x, y

Inv ==
    /\\ x \\in {0, 1}
    /\\ (x = 0 /\\ y = 1)
    /\\ y >= 0 \\* comment with /\\ text

Property == y >= 0
====
"""

    parts = _split_invariant_conjuncts(pluscal, "Inv")

    assert parts == [
        "x \\in {0, 1}",
        "(x = 0 /\\ y = 1)",
        "y >= 0 \\* comment with /\\ text",
    ]


def test_split_invariant_conjuncts_returns_empty_when_missing():
    assert _split_invariant_conjuncts(_PLUSCAL, "Nonexistent") == []


def test_split_invariant_conjuncts_honors_requested_invariant_name():
    pluscal = """\
---- MODULE TwoInvariants ----
VARIABLE x

Init == x = 0
Next == x' = x + 1

WeakInv == x >= 0

StrongInv == x >= 0
    /\\ x <= 5
    /\\ x \\in 0..5

Property == x <= 5
====
"""

    parts = _split_invariant_conjuncts(pluscal, "StrongInv")

    assert parts == ["x >= 0", "x <= 5", "x \\in 0..5"]


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


def test_refine_agent_returns_module_and_passes_conjuncts_to_llm():
    fake = FakeAnthropic(
        [
            FakeMessage(
                content=[
                    FakeBlock(
                        type="tool_use",
                        id="tu_1",
                        name="emit_python_module",
                        input={
                            "python_module": "def increment(c):\n    return c\n",
                            "entry_function": "increment",
                            "assertion_map": [],
                        },
                    )
                ]
            )
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-1-20250805", client=fake)
    agent = RefineAgent(client)

    proposal = SynthesisProposal(
        module_name="BoundedCounter",
        slug="bounded_counter",
        pluscal=_PLUSCAL,
    )

    refined = agent.to_python(proposal)

    assert refined.entry_function == "increment"
    assert "def increment" in refined.python_module

    user_text = fake.calls[0]["messages"][0]["content"][0]["text"]
    assert "counter >= 0" in user_text
    assert "counter <= 10" in user_text


def test_refine_agent_uses_custom_invariant_name_in_prompt():
    fake = FakeAnthropic(
        [
            FakeMessage(
                content=[
                    FakeBlock(
                        type="tool_use",
                        id="tu_1",
                        name="emit_python_module",
                        input={
                            "python_module": "def run(x):\n    assert x <= 5\n    return x\n",
                            "entry_function": "run",
                            "assertion_map": [
                                {"tla_clause": "x <= 5", "python_check": "x <= 5"}
                            ],
                        },
                    )
                ]
            )
        ]
    )
    client = AnthropicClient(api_key="x", model="claude-opus-4-1-20250805", client=fake)
    agent = RefineAgent(client)
    proposal = SynthesisProposal(
        module_name="TwoInvariants",
        slug="two_invariants",
        pluscal="""\
---- MODULE TwoInvariants ----
VARIABLE x
WeakInv == x >= 0
StrongInv == x >= 0
    /\\ x <= 5
Property == x <= 5
====
""",
        invariant_name="StrongInv",
    )

    refined = agent.to_python(proposal)

    assert refined.assertion_map == [{"tla_clause": "x <= 5", "python_check": "x <= 5"}]
    user_text = fake.calls[0]["messages"][0]["content"][0]["text"]
    assert "Inductive invariant (StrongInv) conjuncts" in user_text
    assert "- x <= 5" in user_text
