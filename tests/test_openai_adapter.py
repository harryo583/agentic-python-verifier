"""Tests for the OpenAI fallback adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.llm.openai_adapter import (
    OpenAIAdapter,
    _from_openai_response,
    _to_openai_messages,
    _to_openai_tool_choice,
    _to_openai_tools,
)


# ---------- Fakes ----------


@dataclass
class _OAIFunction:
    name: str
    arguments: str


@dataclass
class _OAIToolCall:
    id: str
    function: _OAIFunction
    type: str = "function"


@dataclass
class _OAIMessage:
    content: Any = None
    tool_calls: list[_OAIToolCall] = field(default_factory=list)


@dataclass
class _OAIChoice:
    message: _OAIMessage


@dataclass
class _OAIResponse:
    choices: list[_OAIChoice]


class FakeOpenAI:
    def __init__(self, scripted: list[_OAIResponse]):
        self.scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []
        self.chat = self
        self.completions = self

    def create(self, **kwargs: Any) -> _OAIResponse:
        self.calls.append(kwargs)
        return self.scripted.pop(0)


# ---------- Conversion helpers ----------


def test_to_openai_messages_translates_text_user_message():
    out = _to_openai_messages(
        "system prompt",
        [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    )

    assert out[0] == {"role": "system", "content": "system prompt"}
    assert out[1] == {"role": "user", "content": "hello"}


def test_to_openai_messages_translates_assistant_tool_use():
    out = _to_openai_messages(
        "s",
        [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu_1",
                        "name": "propose_pluscal_with_invariant",
                        "input": {"slug": "x"},
                    }
                ],
            }
        ],
    )

    asst = out[1]
    assert asst["role"] == "assistant"
    assert asst["content"] is None
    assert asst["tool_calls"][0]["id"] == "tu_1"
    assert asst["tool_calls"][0]["type"] == "function"
    assert asst["tool_calls"][0]["function"]["name"] == "propose_pluscal_with_invariant"
    assert json.loads(asst["tool_calls"][0]["function"]["arguments"]) == {"slug": "x"}


def test_to_openai_messages_translates_tool_result_to_tool_role():
    out = _to_openai_messages(
        "s",
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tu_1",
                        "content": "the bundle failed: ...",
                    }
                ],
            }
        ],
    )

    tool_msg = out[1]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "tu_1"
    assert "the bundle failed" in tool_msg["content"]


def test_to_openai_tools_wraps_in_function_envelope():
    tools = [
        {
            "name": "propose_pluscal_with_invariant",
            "description": "...",
            "input_schema": {"type": "object", "properties": {"slug": {"type": "string"}}},
        }
    ]

    out = _to_openai_tools(tools)

    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "propose_pluscal_with_invariant"
    assert out[0]["function"]["parameters"] == tools[0]["input_schema"]


def test_to_openai_tool_choice_translates_anthropic_tool_choice():
    assert _to_openai_tool_choice({"type": "tool", "name": "X"}) == {
        "type": "function",
        "function": {"name": "X"},
    }
    assert _to_openai_tool_choice({"type": "any"}) == "required"
    assert _to_openai_tool_choice({"type": "auto"}) == "auto"


# ---------- Response parsing ----------


def test_from_openai_response_extracts_tool_use_block():
    response = _OAIResponse(
        choices=[
            _OAIChoice(
                message=_OAIMessage(
                    content=None,
                    tool_calls=[
                        _OAIToolCall(
                            id="call_1",
                            function=_OAIFunction(
                                name="propose_pluscal_with_invariant",
                                arguments=json.dumps(
                                    {
                                        "module_name": "X",
                                        "slug": "x",
                                        "pluscal": "...",
                                        "constants": {"values": {"N": [3]}},
                                    }
                                ),
                            ),
                        )
                    ],
                )
            )
        ]
    )

    result = _from_openai_response(response)

    assert len(result.content) == 1
    block = result.content[0]
    assert block.type == "tool_use"
    assert block.id == "call_1"
    assert block.name == "propose_pluscal_with_invariant"
    assert block.input["module_name"] == "X"


def test_from_openai_response_includes_text_when_present():
    response = _OAIResponse(
        choices=[_OAIChoice(message=_OAIMessage(content="some narration", tool_calls=[]))]
    )

    result = _from_openai_response(response)

    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert result.content[0].text == "some narration"


def test_from_openai_response_handles_malformed_json_arguments():
    response = _OAIResponse(
        choices=[
            _OAIChoice(
                message=_OAIMessage(
                    content=None,
                    tool_calls=[
                        _OAIToolCall(
                            id="call_1",
                            function=_OAIFunction(name="x", arguments="not json {"),
                        )
                    ],
                )
            )
        ]
    )

    result = _from_openai_response(response)

    assert result.content[0].type == "tool_use"
    assert result.content[0].input == {}


# ---------- End-to-end adapter call ----------


def test_adapter_message_round_trips_request_and_response():
    response = _OAIResponse(
        choices=[
            _OAIChoice(
                message=_OAIMessage(
                    content=None,
                    tool_calls=[
                        _OAIToolCall(
                            id="call_1",
                            function=_OAIFunction(
                                name="propose_pluscal_with_invariant",
                                arguments='{"module_name":"X","slug":"x","pluscal":"...","constants":{"values":{"N":[3]}}}',
                            ),
                        )
                    ],
                )
            )
        ]
    )
    fake = FakeOpenAI([response])
    adapter = OpenAIAdapter(api_key="x", model="gpt-5.4", client=fake)

    out = adapter.message(
        system="sys",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        tools=[
            {
                "name": "propose_pluscal_with_invariant",
                "description": "...",
                "input_schema": {"type": "object"},
            }
        ],
        tool_choice={"type": "tool", "name": "propose_pluscal_with_invariant"},
    )

    assert out.content[0].type == "tool_use"
    assert out.content[0].name == "propose_pluscal_with_invariant"

    sent = fake.calls[0]
    assert sent["model"] == "gpt-5.4"
    assert sent["messages"][0]["role"] == "system"
    assert sent["tools"][0]["type"] == "function"
    assert sent["tool_choice"]["function"]["name"] == "propose_pluscal_with_invariant"
