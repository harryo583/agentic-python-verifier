"""Refinement agent: verified PlusCal -> Python (single module or whole package).

Single-module path (`to_python`) emits a flat .py file with bare asserts
(legacy baseline). Compositional path (`to_python_package`) emits one
icontract-decorated class per impl module plus a parent app file that
composes them; both flavors end with a generated `_trace.py` shim so the
emitted package is self-contained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.llm.anthropic_client import AnthropicClient
from src.llm.prompts import (
    REFINE_APP_SYSTEM,
    REFINE_MODULE_SYSTEM,
    REFINE_SYSTEM,
)
from src.llm.tools import (
    EMIT_PYTHON_APP_FOR_BUNDLE_TOOL,
    EMIT_PYTHON_MODULE_FOR_BUNDLE_TOOL,
    REFINE_TOOL,
)
from src.models.bundle import (
    ModuleBundle,
    ModuleSource,
    PythonModuleSource,
    PythonPackage,
    to_snake_case,
)
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

    def to_python_package(self, verified: ModuleBundle) -> PythonPackage:
        """Lower a verified ModuleBundle into a Python package.

        Calls the LLM once per impl (in the bundle's declared order) and once
        more for the parent app. The parent call receives the already-emitted
        children's (module_name, class_name) tuples so it can wire imports
        deterministically — that is why the calls cannot run in parallel.
        """

        impls = verified.impls()
        if not impls:
            raise ValueError(
                f"bundle {verified.slug!r} has no impl modules to lower"
            )

        children: list[PythonModuleSource] = []
        for impl in impls:
            abs_module = self._abs_for(verified, impl)
            children.append(self._emit_child_module(impl, abs_module))

        parent_app = self._emit_parent_app(verified, children)

        return PythonPackage(
            slug=verified.slug,
            modules=children,
            parent_app=parent_app,
        )

    def _abs_for(
        self, bundle: ModuleBundle, impl: ModuleSource
    ) -> ModuleSource | None:
        """Return the abs sibling for an impl, or None if the bundle has none."""

        for m in bundle.abstractions():
            if m.name == impl.name:
                return m
        return None

    def _emit_child_module(
        self, impl: ModuleSource, abs_module: ModuleSource | None
    ) -> PythonModuleSource:
        """One LLM call: lower a single impl to a Python class module."""

        conjuncts = _split_invariant_conjuncts(impl.tla_source, impl.invariant_name)
        abs_block = (
            "\n\nSibling Abs module (defines the abstract contract):\n\n"
            f"{abs_module.tla_source}"
            if abs_module is not None
            else ""
        )
        user_msg = (
            f"Verified TLA+ impl module ({impl.name}_Impl):\n\n"
            f"{impl.tla_source}"
            f"{abs_block}\n\n"
            f"Inductive invariant ({impl.invariant_name}) conjuncts "
            "(top-level /\\):\n"
            + "\n".join(f"  - {c}" for c in conjuncts)
            + (
                "\n\nAbstraction map (this impl's variables -> abstract vars):\n"
                + "\n".join(
                    f"  {av} <- {expr}" for av, expr in impl.abstraction_map.items()
                )
                if impl.abstraction_map
                else ""
            )
            + "\n\nTranslate this impl into a Python 3.11+ class module per the "
            "system prompt. Snake-case file name will be "
            f"`{to_snake_case(impl.name)}.py`."
        )
        response = self.client.message(
            system=REFINE_MODULE_SYSTEM,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_msg}]}],
            tools=[EMIT_PYTHON_MODULE_FOR_BUNDLE_TOOL],
            tool_choice={
                "type": "tool",
                "name": EMIT_PYTHON_MODULE_FOR_BUNDLE_TOOL["name"],
            },
        )
        tool_use = self.client.extract_tool_use(
            response, expected_name=EMIT_PYTHON_MODULE_FOR_BUNDLE_TOOL["name"]
        )
        data = tool_use.input
        return PythonModuleSource(
            name=impl.name,
            source=data.get("python_module", ""),
            class_name=data.get("class_name", ""),
            entry_function=data.get("entry_function", ""),
        )

    def _emit_parent_app(
        self, bundle: ModuleBundle, children: list[PythonModuleSource]
    ) -> PythonModuleSource:
        """One LLM call: emit the parent app that imports and composes children."""

        child_lines = []
        for c in children:
            child_lines.append(
                f"  - {c.name}: file `{c.filename}`, class `{c.class_name}`, "
                f"entry method `{c.entry_function}`"
            )

        user_msg = (
            f"Parent module ({bundle.parent.name}) TLA+ source:\n\n"
            f"{bundle.parent.tla_source}\n\n"
            "Children already emitted (import them via relative imports):\n"
            + "\n".join(child_lines)
            + "\n\nEmit the parent app module per the system prompt. Use "
            f"`from ._trace import log_action`. The composed class should be "
            f"named `{bundle.parent.name}` (matching the parent's TLA+ module)."
        )
        response = self.client.message(
            system=REFINE_APP_SYSTEM,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_msg}]}],
            tools=[EMIT_PYTHON_APP_FOR_BUNDLE_TOOL],
            tool_choice={
                "type": "tool",
                "name": EMIT_PYTHON_APP_FOR_BUNDLE_TOOL["name"],
            },
        )
        tool_use = self.client.extract_tool_use(
            response, expected_name=EMIT_PYTHON_APP_FOR_BUNDLE_TOOL["name"]
        )
        data = tool_use.input
        return PythonModuleSource(
            name=bundle.parent.name,
            source=data.get("python_module", ""),
            class_name=data.get("class_name", ""),
            entry_function=data.get("entry_function", "run"),
        )

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


_TRACE_SHIM_SOURCE = '''"""Trace-conformance shim for the emitted package.

Each impl class and the parent app call ``log_action(name, state)`` at the
end of every state-mutating method. By default the action log accumulates
in-memory. When the Week-3 trace gate subprocesses the package it sets
``TRACE_JSONL_PATH``; in that mode each call also appends a JSON line to
the file so the gate can read it back after the run completes.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, TextIO


ACTIONS: list[tuple[str, dict[str, Any]]] = []

_JSONL_PATH: Optional[str] = os.environ.get("TRACE_JSONL_PATH")
_JSONL_FH: Optional[TextIO] = (
    open(_JSONL_PATH, "a", buffering=1, encoding="utf-8")
    if _JSONL_PATH
    else None
)


def log_action(name: str, state: dict[str, Any]) -> None:
    """Record one ``(name, state)`` pair.

    Always appends to the in-memory ``ACTIONS`` list. When the
    ``TRACE_JSONL_PATH`` env var is set at module import time, also writes
    a ``{"action": ..., "state": ...}`` line to that file. ``default=str``
    keeps non-JSON-native values from crashing the run; the trace renderer
    will reject anything it cannot map back to TLA+.
    """

    snapshot = dict(state)
    ACTIONS.append((name, snapshot))
    if _JSONL_FH is not None:
        _JSONL_FH.write(
            json.dumps({"action": name, "state": snapshot}, default=str) + "\\n"
        )
'''


_PKG_INIT_SOURCE = '"""Generated by agentic-python-verifier."""\n'


def trace_shim_source() -> str:
    """Public accessor so main.py can write the shim alongside the package."""

    return _TRACE_SHIM_SOURCE


def package_init_source() -> str:
    """Public accessor so main.py can write the ``__init__.py``."""

    return _PKG_INIT_SOURCE


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
