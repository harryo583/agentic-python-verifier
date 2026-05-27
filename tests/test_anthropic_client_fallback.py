"""Tests for the Anthropic 529 fallback path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.llm.anthropic_client import AnthropicClient


class OverloadedError(Exception):
    """Mimics anthropic._exceptions.OverloadedError by name."""


@dataclass
class FakeMessage:
    content: list[Any] = field(default_factory=list)
    model_used: str = ""


class FakeAnthropic:
    """Fakes the Anthropic SDK and can be configured to overload N times."""

    def __init__(self, overload_first: int = 0):
        self.overload_first = overload_first
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        if len(self.calls) <= self.overload_first:
            raise OverloadedError("Overloaded")
        return FakeMessage(model_used=kwargs["model"])


def test_no_fallback_when_disabled_propagates_error():
    fake = FakeAnthropic(overload_first=1)
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)

    with pytest.raises(OverloadedError):
        client.message(system="s", messages=[])

    assert len(fake.calls) == 1


def test_fallback_retries_on_overload_with_secondary_model():
    fake = FakeAnthropic(overload_first=1)
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-7",
        client=fake,
        fallback_model="claude-opus-4-6",
    )

    response = client.message(system="s", messages=[])

    assert len(fake.calls) == 2
    assert fake.calls[0]["model"] == "claude-opus-4-7"
    assert fake.calls[1]["model"] == "claude-opus-4-6"
    assert response.model_used == "claude-opus-4-6"


def test_fallback_does_not_retry_a_second_overload():
    fake = FakeAnthropic(overload_first=2)
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-7",
        client=fake,
        fallback_model="claude-opus-4-6",
    )

    with pytest.raises(OverloadedError):
        client.message(system="s", messages=[])

    assert len(fake.calls) == 2  # primary + one fallback attempt, no further retries


class FakeTertiary:
    """Stand-in for an OpenAIAdapter; returns an Anthropic-shaped response."""

    def __init__(self):
        self.model = "gpt-5.4"
        self.calls: list[dict[str, Any]] = []

    def message(self, system, messages, tools=None, tool_choice=None):
        self.calls.append(
            {"system": system, "messages": messages, "tools": tools, "tool_choice": tool_choice}
        )

        @dataclass
        class _Block:
            type: str
            id: str = ""
            name: str = ""
            input: dict[str, Any] = field(default_factory=dict)
            text: str = ""

        @dataclass
        class _Resp:
            content: list[_Block]

        return _Resp(
            content=[
                _Block(
                    type="tool_use",
                    id="tertiary_1",
                    name="propose_pluscal_with_invariant",
                    input={"slug": "x"},
                )
            ]
        )


def test_tertiary_fires_when_both_anthropic_models_overload():
    fake = FakeAnthropic(overload_first=2)  # primary AND fallback both 529
    tertiary = FakeTertiary()
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-7",
        client=fake,
        fallback_model="claude-opus-4-6",
        tertiary=tertiary,
    )

    response = client.message(system="s", messages=[])

    assert len(fake.calls) == 2  # primary + fallback
    assert len(tertiary.calls) == 1
    # Response is the tertiary's, with Anthropic shape preserved
    assert response.content[0].type == "tool_use"
    assert response.content[0].id == "tertiary_1"


def test_tertiary_not_fired_if_fallback_succeeds():
    fake = FakeAnthropic(overload_first=1)  # only primary 529s
    tertiary = FakeTertiary()
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-7",
        client=fake,
        fallback_model="claude-opus-4-6",
        tertiary=tertiary,
    )

    client.message(system="s", messages=[])

    assert len(fake.calls) == 2
    assert len(tertiary.calls) == 0  # fallback rescued the request


def test_tertiary_fires_when_no_fallback_model_configured():
    fake = FakeAnthropic(overload_first=1)
    tertiary = FakeTertiary()
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-7",
        client=fake,
        fallback_model=None,
        tertiary=tertiary,
    )

    client.message(system="s", messages=[])

    assert len(fake.calls) == 1  # primary only, no fallback model to try
    assert len(tertiary.calls) == 1  # straight to tertiary


def test_non_overload_errors_are_not_caught():
    class TransientNetworkError(Exception):
        pass

    class FailingFake:
        def __init__(self):
            self.calls = []
            self.messages = self

        def create(self, **kwargs):
            self.calls.append(kwargs)
            raise TransientNetworkError("connection reset")

    fake = FailingFake()
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-7",
        client=fake,
        fallback_model="claude-opus-4-6",
    )

    with pytest.raises(TransientNetworkError):
        client.message(system="s", messages=[])

    assert len(fake.calls) == 1
