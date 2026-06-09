"""Per-call LLM usage accounting: tokens, latency, cache hits, and a $ estimate.

The Anthropic Messages API already returns a ``usage`` block on every response
(``input_tokens``, ``output_tokens``, ``cache_creation_input_tokens``,
``cache_read_input_tokens``); we used to throw it away. ``AnthropicClient`` now
records one :class:`LLMCall` per round-trip into a :class:`UsageLedger`, tagged
with the pipeline ``stage`` that issued it. The pipeline attaches a serialisable
:class:`UsageSummary` to its result so the benchmark harness can report which
stage dominates tokens / dollars.

Pricing in :data:`PRICE_TABLE` is **approximate** and meant to be edited to match
the live price sheet; ``est_usd`` is a planning estimate, not a billing figure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """Approximate USD-per-million-token rates for one model id.

    ``cache_read`` is the discounted rate applied to ``cache_read_input_tokens``;
    ``cache_write`` is the surcharged rate for ``cache_creation_input_tokens``.
    The Anthropic ``usage.input_tokens`` field already excludes cached tokens, so
    the four buckets do not double-count.
    """

    input: float
    output: float
    cache_read: float
    cache_write: float


# Approximate $/MTok. EDIT to match the live Anthropic price sheet — these are
# placeholders so ``est_usd`` is meaningful for the report, not billing-accurate.
PRICE_TABLE: dict[str, ModelPrice] = {
    "claude-opus-4-8": ModelPrice(input=15.0, output=75.0, cache_read=1.5, cache_write=18.75),
    "claude-opus-4-7": ModelPrice(input=15.0, output=75.0, cache_read=1.5, cache_write=18.75),
    "claude-opus-4-6": ModelPrice(input=15.0, output=75.0, cache_read=1.5, cache_write=18.75),
    "claude-sonnet-4-6": ModelPrice(input=3.0, output=15.0, cache_read=0.3, cache_write=3.75),
    "claude-haiku-4-5": ModelPrice(input=1.0, output=5.0, cache_read=0.1, cache_write=1.25),
}

# Fallback when a served model id isn't in the table (e.g. a dated suffix). We
# default to Opus rates so cost is over- rather than under-estimated.
_DEFAULT_PRICE = ModelPrice(input=15.0, output=75.0, cache_read=1.5, cache_write=18.75)


def price_for(model_served: str) -> ModelPrice:
    """Return the price row for a served model, tolerating dated id suffixes."""

    if model_served in PRICE_TABLE:
        return PRICE_TABLE[model_served]
    # Tolerate ids like "claude-opus-4-7-20260101" by longest-prefix match.
    for key, price in PRICE_TABLE.items():
        if model_served.startswith(key):
            return price
    return _DEFAULT_PRICE


@dataclass(slots=True)
class LLMCall:
    """One LLM round-trip's accounting.

    ``model_served`` is the model that *actually answered* (the 529 fallback /
    tertiary chain can differ from ``settings.model``). ``degraded`` is True when
    usage was unavailable — e.g. the OpenAI tertiary path returns no ``usage`` —
    in which case token fields are ``None`` and the call is excluded from
    ``est_usd`` rather than silently costed at zero.
    """

    stage: str
    model_served: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cache_read_tokens: Optional[int]
    cache_creation_tokens: Optional[int]
    latency_s: float
    degraded: bool = False

    def est_usd(self) -> float:
        if self.degraded:
            return 0.0
        price = price_for(self.model_served)
        return (
            (self.input_tokens or 0) * price.input
            + (self.output_tokens or 0) * price.output
            + (self.cache_read_tokens or 0) * price.cache_read
            + (self.cache_creation_tokens or 0) * price.cache_write
        ) / 1_000_000


class StageUsage(BaseModel):
    """Aggregated usage for a single pipeline stage."""

    stage: str
    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    latency_s: float
    est_usd: float
    degraded_calls: int


class UsageSummary(BaseModel):
    """Whole-run usage, plus a per-stage breakdown. Attached to pipeline results."""

    total_calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    latency_s: float
    est_usd: float
    degraded_calls: int
    by_stage: list[StageUsage] = []


@dataclass(slots=True)
class UsageLedger:
    """Collects :class:`LLMCall`s for one pipeline run."""

    calls: list[LLMCall] = field(default_factory=list)

    def record(self, call: LLMCall) -> None:
        self.calls.append(call)

    def est_usd(self) -> float:
        return sum(c.est_usd() for c in self.calls)

    def by_stage(self) -> list[StageUsage]:
        order: list[str] = []
        buckets: dict[str, list[LLMCall]] = {}
        for call in self.calls:
            if call.stage not in buckets:
                buckets[call.stage] = []
                order.append(call.stage)
            buckets[call.stage].append(call)
        return [_aggregate_stage(stage, buckets[stage]) for stage in order]

    def summary(self) -> UsageSummary:
        degraded = sum(1 for c in self.calls if c.degraded)
        if degraded:
            LOGGER.warning(
                "UsageLedger: %d/%d call(s) had no usage data (degraded); their "
                "tokens and est_usd are excluded from the summary.",
                degraded,
                len(self.calls),
            )
        return UsageSummary(
            total_calls=len(self.calls),
            input_tokens=sum(c.input_tokens or 0 for c in self.calls),
            output_tokens=sum(c.output_tokens or 0 for c in self.calls),
            cache_read_tokens=sum(c.cache_read_tokens or 0 for c in self.calls),
            cache_creation_tokens=sum(c.cache_creation_tokens or 0 for c in self.calls),
            latency_s=round(sum(c.latency_s for c in self.calls), 3),
            est_usd=round(self.est_usd(), 6),
            degraded_calls=degraded,
            by_stage=self.by_stage(),
        )


def _aggregate_stage(stage: str, calls: list[LLMCall]) -> StageUsage:
    return StageUsage(
        stage=stage,
        calls=len(calls),
        input_tokens=sum(c.input_tokens or 0 for c in calls),
        output_tokens=sum(c.output_tokens or 0 for c in calls),
        cache_read_tokens=sum(c.cache_read_tokens or 0 for c in calls),
        cache_creation_tokens=sum(c.cache_creation_tokens or 0 for c in calls),
        latency_s=round(sum(c.latency_s for c in calls), 3),
        est_usd=round(sum(c.est_usd() for c in calls), 6),
        degraded_calls=sum(1 for c in calls if c.degraded),
    )
