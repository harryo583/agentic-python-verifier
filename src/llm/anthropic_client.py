"""Thin wrapper around the Anthropic Messages API with prompt caching."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol


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


class AnthropicClient:
    """A small adapter so agents can be tested without the real SDK.

    Supports a fallback model: if the primary model returns an Anthropic
    529 OverloadedError, the call is retried once on ``fallback_model``.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 8192,
        client: Optional[AnthropicProtocol] = None,
        fallback_model: Optional[str] = None,
    ) -> None:
        self.model = model
        self.fallback_model = fallback_model
        self.max_tokens = max_tokens
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
    ) -> Any:
        """Issue one Messages API call with the system prompt cached.

        Falls back to ``self.fallback_model`` on 529 OverloadedError.
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

        try:
            return self._client.messages.create(**kwargs)
        except Exception as exc:
            if not (_is_overloaded(exc) and self.fallback_model):
                raise
            LOGGER.warning(
                "Primary model %s overloaded (529); falling back to %s.",
                self.model,
                self.fallback_model,
            )
            kwargs["model"] = self.fallback_model
            return self._client.messages.create(**kwargs)

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
