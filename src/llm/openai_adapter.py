"""OpenAI fallback adapter.

Translates the Anthropic-shaped (system, messages, tools, tool_choice) inputs
that agents already produce into OpenAI Chat Completions arguments, calls the
OpenAI client, and converts the response back to a minimal Anthropic-shaped
object so downstream code (`extract_tool_use`, `_content_blocks`) keeps
working unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


class OpenAIProtocol(Protocol):
    """Subset of the OpenAI SDK we depend on (for typing/mocks)."""

    chat: Any  # noqa: ANN401  - SDK shape


@dataclass(slots=True)
class _Block:
    """Anthropic-shaped content block (text or tool_use)."""

    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _Response:
    """Minimal Anthropic-shaped response: a list of content blocks."""

    content: list[_Block]


class OpenAIAdapter:
    """Calls the OpenAI Chat Completions API behind an Anthropic-shaped
    facade so the downstream agents do not need to know about it.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.4",
        max_tokens: int = 8192,
        client: Optional[OpenAIProtocol] = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI  # imported lazily for testability

            self._client = OpenAI(api_key=api_key)

    def message(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[dict[str, Any]] = None,
    ) -> _Response:
        oai_messages = _to_openai_messages(system, messages)
        oai_tools = _to_openai_tools(tools) if tools else None
        oai_tool_choice = _to_openai_tool_choice(tool_choice) if tool_choice else None

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
            "max_tokens": self.max_tokens,
        }
        if oai_tools is not None:
            kwargs["tools"] = oai_tools
        if oai_tool_choice is not None:
            kwargs["tool_choice"] = oai_tool_choice

        response = self._client.chat.completions.create(**kwargs)
        return _from_openai_response(response)


def _to_openai_messages(
    system: str, messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            text_parts: list[str] = []
            tool_results: list[dict[str, Any]] = []
            for block in _iter_blocks(content):
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_result":
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id", ""),
                            "content": _stringify(block.get("content", "")),
                        }
                    )
            if text_parts:
                out.append({"role": "user", "content": "\n\n".join(text_parts)})
            out.extend(tool_results)
        elif role == "assistant":
            text_parts = []
            tool_calls: list[dict[str, Any]] = []
            for block in _iter_blocks(content):
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": block.get("name", ""),
                                "arguments": json.dumps(block.get("input", {})),
                            },
                        }
                    )
            entry: dict[str, Any] = {"role": "assistant"}
            entry["content"] = "\n\n".join(text_parts) if text_parts else None
            if tool_calls:
                entry["tool_calls"] = tool_calls
            out.append(entry)
        else:
            # Pass through any other roles defensively.
            out.append({"role": role or "user", "content": _stringify(content)})
    return out


def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in tools:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object"}),
                },
            }
        )
    return out


def _to_openai_tool_choice(tool_choice: dict[str, Any]) -> Any:
    if tool_choice.get("type") == "tool":
        return {
            "type": "function",
            "function": {"name": tool_choice.get("name", "")},
        }
    if tool_choice.get("type") == "any":
        return "required"
    if tool_choice.get("type") == "auto":
        return "auto"
    return tool_choice


def _from_openai_response(response: Any) -> _Response:
    choices = _attr(response, "choices") or []
    if not choices:
        return _Response(content=[])
    msg = _attr(choices[0], "message")
    blocks: list[_Block] = []

    text = _attr(msg, "content")
    if isinstance(text, str) and text.strip():
        blocks.append(_Block(type="text", text=text))

    tool_calls = _attr(msg, "tool_calls") or []
    for tc in tool_calls:
        fn = _attr(tc, "function")
        name = _attr(fn, "name") or ""
        raw_args = _attr(fn, "arguments") or "{}"
        try:
            parsed = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            parsed = {}
        blocks.append(
            _Block(
                type="tool_use",
                id=_attr(tc, "id") or "",
                name=name,
                input=parsed if isinstance(parsed, dict) else {},
            )
        )

    return _Response(content=blocks)


def _iter_blocks(content: Any) -> list[dict[str, Any]]:
    if content is None:
        return []
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for b in value:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    parts.append(b.get("text", ""))
                else:
                    parts.append(json.dumps(b))
            else:
                parts.append(str(b))
        return "\n".join(parts)
    return json.dumps(value)


def _attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
