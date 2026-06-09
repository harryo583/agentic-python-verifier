"""Tests for Feature #0 — LLM cost/latency instrumentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.llm.anthropic_client import AnthropicClient
from src.llm.usage import (
    PRICE_TABLE,
    LLMCall,
    UsageLedger,
    price_for,
)


def _call(stage: str, **kw: Any) -> LLMCall:
    base = dict(
        model_served="claude-opus-4-7",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
        cache_creation_tokens=0,
        latency_s=1.0,
        degraded=False,
    )
    base.update(kw)
    return LLMCall(stage=stage, **base)  # type: ignore[arg-type]


def test_price_for_exact_and_prefix_match():
    assert price_for("claude-opus-4-7") is PRICE_TABLE["claude-opus-4-7"]
    # Dated suffix should resolve by longest-prefix match.
    assert price_for("claude-opus-4-7-20260101") is PRICE_TABLE["claude-opus-4-7"]


def test_est_usd_matches_price_table():
    price = PRICE_TABLE["claude-opus-4-7"]
    call = _call("synth")
    expected = (
        1000 * price.input
        + 500 * price.output
        + 200 * price.cache_read
        + 0 * price.cache_write
    ) / 1_000_000
    assert call.est_usd() == expected


def test_degraded_call_excluded_from_cost():
    degraded = _call(
        "repair_bundle",
        input_tokens=None,
        output_tokens=None,
        cache_read_tokens=None,
        cache_creation_tokens=None,
        degraded=True,
    )
    assert degraded.est_usd() == 0.0


def test_ledger_aggregation_and_by_stage():
    ledger = UsageLedger()
    ledger.record(_call("synth"))
    ledger.record(_call("synth", input_tokens=2000))
    ledger.record(_call("repair", output_tokens=100))
    ledger.record(
        _call(
            "refine",
            input_tokens=None,
            output_tokens=None,
            cache_read_tokens=None,
            cache_creation_tokens=None,
            degraded=True,
        )
    )

    summary = ledger.summary()
    assert summary.total_calls == 4
    assert summary.degraded_calls == 1
    # 1000 + 2000 + 1000 + 0 (degraded counted as 0 tokens)
    assert summary.input_tokens == 4000
    assert summary.est_usd > 0.0

    by_stage = {s.stage: s for s in summary.by_stage}
    assert by_stage["synth"].calls == 2
    assert by_stage["synth"].input_tokens == 3000
    assert by_stage["refine"].degraded_calls == 1
    assert by_stage["refine"].est_usd == 0.0
    # Stage order is first-seen order.
    assert [s.stage for s in summary.by_stage] == ["synth", "repair", "refine"]


@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _Resp:
    content: list[Any] = field(default_factory=list)
    model: str = "claude-opus-4-7"
    usage: Any = None


class _FakeWithUsage:
    def __init__(self, usage: _Usage, model: str = "claude-opus-4-7"):
        self._usage = usage
        self._model = model
        self.messages = self

    def create(self, **kwargs: Any) -> _Resp:
        return _Resp(model=self._model, usage=self._usage)


def test_client_records_usage_into_ledger():
    ledger = UsageLedger()
    fake = _FakeWithUsage(
        _Usage(
            input_tokens=1200,
            output_tokens=340,
            cache_read_input_tokens=800,
            cache_creation_input_tokens=50,
        )
    )
    client = AnthropicClient(
        api_key="x", model="claude-opus-4-7", client=fake, ledger=ledger
    )

    client.message(system="s", messages=[], stage="synth_bundle")

    assert len(ledger.calls) == 1
    call = ledger.calls[0]
    assert call.stage == "synth_bundle"
    assert call.model_served == "claude-opus-4-7"
    assert call.input_tokens == 1200
    assert call.cache_read_tokens == 800
    assert call.cache_creation_tokens == 50
    assert not call.degraded
    assert call.latency_s >= 0.0


def test_client_records_degraded_when_no_usage():
    """A response object without a usage block is recorded as degraded."""

    ledger = UsageLedger()

    @dataclass
    class _NoUsage:
        content: list[Any] = field(default_factory=list)

    class _Fake:
        def __init__(self) -> None:
            self.messages = self

        def create(self, **kwargs: Any) -> _NoUsage:
            return _NoUsage()

    client = AnthropicClient(
        api_key="x", model="claude-opus-4-7", client=_Fake(), ledger=ledger
    )
    client.message(system="s", messages=[], stage="planner")

    assert len(ledger.calls) == 1
    assert ledger.calls[0].degraded
    assert ledger.calls[0].est_usd() == 0.0


def test_no_ledger_is_a_noop():
    fake = _FakeWithUsage(_Usage(input_tokens=10))
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
    # Should not raise even though no ledger is attached.
    client.message(system="s", messages=[], stage="synth")
