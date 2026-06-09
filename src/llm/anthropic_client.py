"""Thin wrapper around the Anthropic Messages API with prompt caching."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from src.llm.usage import LLMCall, UsageLedger


LOGGER = logging.getLogger(__name__)


class AnthropicProtocol(Protocol):
    """Subset of the Anthropic SDK we depend on (for typing/mocks)."""

    messages: Any  # noqa: ANN401  - SDK shape


@dataclass(slots=True)
class ToolUse:
    """Minimal view of an assistant tool_use block."""

    tool_use_id: str
    name: str
    input: dict[str, Any]


def _is_overloaded(exc: BaseException) -> bool:
    """Return True for Anthropic 529 overload errors.

    We avoid a hard import of ``anthropic._exceptions`` so the module stays
    testable without the SDK; we match by class name plus a 529 status hint.
    """

    name = type(exc).__name__
    if name == "OverloadedError":
        return True
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    return status == 529


class TertiaryInvoker(Protocol):
    """A drop-in replacement that returns an Anthropic-shaped response.

    Used as the third-tier fallback when both Anthropic models 529.
    """

    def message(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[dict[str, Any]] = None,
    ) -> Any: ...


class AnthropicClient:
    """A small adapter so agents can be tested without the real SDK.

    Fallback chain:
      1. ``model`` (primary, e.g. ``claude-opus-4-7``)
      2. ``fallback_model`` on the same Anthropic SDK (e.g. ``claude-opus-4-6``)
      3. ``tertiary`` (e.g. an OpenAI adapter for ``gpt-5.4``)

    Each tier only fires on a 529 OverloadedError from the previous tier.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 8192,
        client: Optional[AnthropicProtocol] = None,
        fallback_model: Optional[str] = None,
        tertiary: Optional[TertiaryInvoker] = None,
        ledger: Optional[UsageLedger] = None,
    ) -> None:
        self.model = model
        self.fallback_model = fallback_model
        self.tertiary = tertiary
        self.max_tokens = max_tokens
        self.ledger = ledger
        if client is not None:
            self._client = client
        else:
            from anthropic import Anthropic  # imported lazily for testability

            self._client = Anthropic(api_key=api_key)

    def message(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[dict[str, Any]] = None,
        stage: str = "unknown",
    ) -> Any:
        """Issue one Messages API call with the system prompt cached.

        Falls back to ``self.fallback_model`` on 529 OverloadedError, then
        to ``self.tertiary`` on a second 529. When a :class:`UsageLedger` is
        attached, one :class:`LLMCall` is recorded per round-trip tagged with
        ``stage`` (the served model and token usage are read off the response,
        so the fallback chain is accounted for at its real price).
        """

        system_blocks = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_blocks,
            "messages": messages,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        started = time.monotonic()
        try:
            response = self._client.messages.create(**kwargs)
            self._record(stage, response, started, degraded=False)
            return response
        except Exception as primary_exc:
            if not _is_overloaded(primary_exc):
                raise
            if not self.fallback_model and not self.tertiary:
                raise

            if self.fallback_model:
                LOGGER.warning(
                    "Primary model %s overloaded (529); falling back to %s.",
                    self.model,
                    self.fallback_model,
                )
                fallback_kwargs = dict(kwargs)
                fallback_kwargs["model"] = self.fallback_model
                started_fb = time.monotonic()
                try:
                    response = self._client.messages.create(**fallback_kwargs)
                    self._record(stage, response, started_fb, degraded=False)
                    return response
                except Exception as fallback_exc:
                    if not _is_overloaded(fallback_exc):
                        raise
                    if self.tertiary is None:
                        raise

            LOGGER.warning(
                "Anthropic fallback %s also overloaded (529); falling back to tertiary "
                "client (%s).",
                self.fallback_model or "<none>",
                getattr(self.tertiary, "model", type(self.tertiary).__name__),
            )
            assert self.tertiary is not None
            started_t = time.monotonic()
            response = self.tertiary.message(
                system=system,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
            )
            # The tertiary (OpenAI) adapter returns no usage block; record the
            # call as degraded so est_usd doesn't silently undercount.
            self._record(stage, response, started_t, degraded=True)
            return response

    def _record(
        self, stage: str, response: Any, started: float, degraded: bool
    ) -> None:
        """Append one LLMCall to the ledger (no-op when no ledger is attached)."""

        if self.ledger is None:
            return
        latency = time.monotonic() - started
        usage = _attr(response, "usage")
        model_served = _attr(response, "model") or self.model
        if degraded or usage is None:
            self.ledger.record(
                LLMCall(
                    stage=stage,
                    model_served=model_served,
                    input_tokens=None,
                    output_tokens=None,
                    cache_read_tokens=None,
                    cache_creation_tokens=None,
                    latency_s=latency,
                    degraded=True,
                )
            )
            return
        self.ledger.record(
            LLMCall(
                stage=stage,
                model_served=model_served,
                input_tokens=_attr(usage, "input_tokens"),
                output_tokens=_attr(usage, "output_tokens"),
                cache_read_tokens=_attr(usage, "cache_read_input_tokens"),
                cache_creation_tokens=_attr(usage, "cache_creation_input_tokens"),
                latency_s=latency,
                degraded=False,
            )
        )

    @staticmethod
    def extract_tool_use(message: Any, expected_name: Optional[str] = None) -> ToolUse:
        """Pull the first `tool_use` block from a Messages response."""

        blocks = getattr(message, "content", None) or []
        for block in blocks:
            block_type = _attr(block, "type")
            if block_type != "tool_use":
                continue
            name = _attr(block, "name")
            if expected_name is not None and name != expected_name:
                continue
            return ToolUse(
                tool_use_id=_attr(block, "id"),
                name=name,
                input=_attr(block, "input") or {},
            )
        raise LLMResponseError(
            f"No tool_use block found in assistant response (expected {expected_name!r})."
        )


def _attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


class LLMResponseError(RuntimeError):
    """Raised when the model response cannot be parsed as a tool call."""
