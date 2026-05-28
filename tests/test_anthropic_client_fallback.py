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
    client = AnthropicClient(api_key="x", model="claude-opus-4-1-20250805", client=fake)

    with pytest.raises(OverloadedError):
        client.message(system="s", messages=[])

    assert len(fake.calls) == 1


def test_fallback_retries_on_overload_with_secondary_model():
    fake = FakeAnthropic(overload_first=1)
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-1-20250805",
        client=fake,
        fallback_model="claude-opus-4-20250514",
    )

    response = client.message(system="s", messages=[])

    assert len(fake.calls) == 2
    assert fake.calls[0]["model"] == "claude-opus-4-1-20250805"
    assert fake.calls[1]["model"] == "claude-opus-4-20250514"
    assert response.model_used == "claude-opus-4-20250514"


def test_fallback_does_not_retry_a_second_overload():
    fake = FakeAnthropic(overload_first=2)
    client = AnthropicClient(
        api_key="x",
        model="claude-opus-4-1-20250805",
        client=fake,
        fallback_model="claude-opus-4-20250514",
    )

    with pytest.raises(OverloadedError):
        client.message(system="s", messages=[])

    assert len(fake.calls) == 2  # primary + one fallback attempt, no further retries


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
        model="claude-opus-4-1-20250805",
        client=fake,
        fallback_model="claude-opus-4-20250514",
    )

    with pytest.raises(TransientNetworkError):
        client.message(system="s", messages=[])

    assert len(fake.calls) == 1
