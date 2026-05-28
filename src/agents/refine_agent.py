"""Refinement agent: verified PlusCal -> Python module with invariant assertions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.llm.anthropic_client import AnthropicClient
from src.llm.prompts import REFINE_SYSTEM
from src.llm.tools import REFINE_TOOL
from src.models.synthesis import SynthesisProposal


@dataclass(slots=True)
class RefinedModule:
    """Output of the refinement agent."""

    python_module: str
    entry_function: str
    assertion_map: list[dict[str, str]]


@dataclass(slots=True)
class RefineAgent:
    """LLM-driven PlusCal -> Python translator."""

    client: AnthropicClient

    def to_python(self, verified: SynthesisProposal) -> RefinedModule:
        conjuncts = _split_invariant_conjuncts(verified.pluscal, verified.invariant_name)
        user_msg = (
            "Verified TLA+ module (with PlusCal):\n\n"
            f"{verified.pluscal}\n\n"
            f"Inductive invariant ({verified.invariant_name}) conjuncts (top-level /\\):\n"
            + "\n".join(f"  - {c}" for c in conjuncts)
            + "\n\nTranslate this module into a Python 3.11+ module per the system prompt."
        )
        response = self.client.message(
            system=REFINE_SYSTEM,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_msg}]}],
            tools=[REFINE_TOOL],
            tool_choice={"type": "tool", "name": REFINE_TOOL["name"]},
        )
        tool_use = self.client.extract_tool_use(response, expected_name=REFINE_TOOL["name"])
        data = tool_use.input
        return RefinedModule(
            python_module=data.get("python_module", ""),
            entry_function=data.get("entry_function", ""),
            assertion_map=list(data.get("assertion_map", [])),
        )


_DEF_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*==\s*(?P<body>.*)$",
    re.MULTILINE,
)
_DEF_BOUNDARY_RE = re.compile(
    r"^\s*(?:[A-Za-z_]\w*\s*(?:\([^)]*\))?\s*==|====)",
    re.MULTILINE | re.DOTALL,
)


def _split_invariant_conjuncts(pluscal: str, invariant_name: str) -> list[str]:
    """Best-effort split of `Inv == A /\\ B /\\ C` into top-level conjuncts."""

    body = _extract_operator_body(pluscal, invariant_name)
    if not body:
        return []

    parts = _split_top_level_conjunction(body)
    return [p.strip() for p in parts if p.strip()]


def _extract_operator_body(pluscal: str, name: str) -> str:
    for match in _DEF_RE.finditer(pluscal):
        if match.group("name") != name:
            continue
        body_start = match.start("body")
        boundary = _DEF_BOUNDARY_RE.search(pluscal, match.end())
        body_end = boundary.start() if boundary else len(pluscal)
        return pluscal[body_start:body_end].strip()
    return ""


def _split_top_level_conjunction(body: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body) and body[i + 1] == "*":
            newline = body.find("\n", i)
            if newline == -1:
                break
            i = newline + 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        elif ch == "/" and i + 1 < len(body) and body[i + 1] == "\\" and depth == 0:
            parts.append(body[start:i])
            i += 2
            start = i
            continue
        i += 1
    parts.append(body[start:])
    return parts
