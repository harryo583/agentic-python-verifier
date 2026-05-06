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


_INV_DEF_RE = re.compile(
    r"^(?P<name>\w+)\s*==\s*(?P<body>.+?)(?=^\w+\s*==|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _split_invariant_conjuncts(pluscal: str, invariant_name: str) -> list[str]:
    """Best-effort split of `Inv == A /\\ B /\\ C` into [A, B, C]."""

    body: str | None = None
    for match in _INV_DEF_RE.finditer(pluscal):
        if match.group("name") == invariant_name:
            body = match.group("body").strip()
            break
    if not body:
        return []

    parts = re.split(r"\s*/\\\s*", body)
    return [p.strip() for p in parts if p.strip()]
