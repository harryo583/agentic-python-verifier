"""Minimal LLM provider abstraction for agent synthesis."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from src.config import Settings


LOGGER = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when an LLM request cannot be completed."""


@dataclass(slots=True)
class LLMClient:
    """Small client for Ollama, OpenAI-compatible APIs, and Anthropic messages."""

    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout_seconds: int = 90
    max_json_parse_attempts: int = 3

    @property
    def enabled(self) -> bool:
        """Return whether this client should make remote/local model calls."""

        return self.provider not in {"", "offline", "mock", "none"}

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return model text for a system/user prompt pair."""

        if not self.enabled:
            raise LLMError("LLM provider is disabled.")
        if self.provider == "ollama":
            return self._complete_ollama(system_prompt, user_prompt)
        if self.provider in {"openai", "openai-compatible"}:
            return self._complete_openai(system_prompt, user_prompt)
        if self.provider == "anthropic":
            return self._complete_anthropic(system_prompt, user_prompt)
        raise LLMError(f"Unsupported LLM_PROVIDER: {self.provider}")

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return a JSON object from the model response."""

        last_error: Optional[Exception] = None
        retry_user_prompt = user_prompt
        for attempt in range(1, self.max_json_parse_attempts + 1):
            text = self.complete(system_prompt, retry_user_prompt)
            LOGGER.debug("Raw LLM response before JSON parse: %s", text)
            try:
                return parse_json_object(text)
            except LLMError as exc:
                last_error = exc
                if attempt >= self.max_json_parse_attempts:
                    break
                retry_user_prompt = (
                    f"{user_prompt}\n\n"
                    "Your previous response was not parseable JSON. Retry now with exactly one "
                    "valid JSON object and no markdown, no code fence, no prose, and no trailing text."
                )
                LOGGER.warning(
                    "Failed to parse LLM JSON response on attempt %s/%s: %s",
                    attempt,
                    self.max_json_parse_attempts,
                    exc,
                )
        raise LLMError(f"Failed to parse LLM JSON response: {last_error}") from last_error

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMError(str(exc)) from exc

    def _complete_ollama(self, system_prompt: str, user_prompt: str) -> str:
        base_url = (self.base_url or "http://localhost:11434").rstrip("/")
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._post_json(f"{base_url}/api/chat", payload, {})
        return str(data.get("message", {}).get("content", ""))

    def _complete_openai(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "openai" and not self.api_key:
            raise LLMError("OpenAI-compatible provider requires LLM_API_KEY or OPENAI_API_KEY.")
        base_url = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = self._post_json(f"{base_url}/chat/completions", payload, headers)
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("LLM response contained no choices.")
        return str(choices[0].get("message", {}).get("content", ""))

    def _complete_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise LLMError("Anthropic provider requires LLM_API_KEY or ANTHROPIC_API_KEY.")
        base_url = (self.base_url or "https://api.anthropic.com").rstrip("/")
        payload = {
            "model": self.model,
            "system": system_prompt,
            "max_tokens": 4096,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        data = self._post_json(
            f"{base_url}/v1/messages",
            payload,
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        parts = data.get("content") or []
        return "\n".join(str(part.get("text", "")) for part in parts if part.get("type") == "text")


def build_llm_client(settings: Settings) -> Optional[LLMClient]:
    """Create an LLM client from settings, or None when disabled."""

    provider = settings.llm_provider
    if provider in {"", "offline", "mock", "none"}:
        return None
    default_model = {
        "ollama": "llama3.1",
        "openai": "gpt-4o",
        "openai-compatible": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-latest",
    }.get(provider)
    if default_model is None:
        LOGGER.warning("Unsupported LLM_PROVIDER=%s; using offline fallback.", provider)
        return None
    return LLMClient(
        provider=provider,
        model=settings.llm_model or default_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


def parse_json_object(text: str) -> dict[str, Any]:
    """Extract and parse a JSON object from plain text or fenced output."""

    stripped = text.strip()
    fenced_blocks = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*(.*?)\s*```", stripped, re.DOTALL)
    candidates = [*fenced_blocks, stripped]
    decoder = json.JSONDecoder()

    for candidate in candidates:
        candidate = candidate.strip()
        for start in _json_object_starts(candidate):
            try:
                parsed, _ = decoder.raw_decode(candidate[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
            raise LLMError("Expected a JSON object.")
    raise LLMError("Could not parse a JSON object from LLM response.")


def _json_object_starts(text: str) -> list[int]:
    starts = [index for index, char in enumerate(text) if char == "{"]
    return [0, *[index for index in starts if index != 0]] if text.startswith("{") else starts
