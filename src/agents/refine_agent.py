"""Refinement agent: verified PlusCal -> Python (single module or whole package).

Single-module path (`to_python`) emits a flat .py file with bare asserts
(legacy baseline). Compositional path (`to_python_package`) emits one
icontract-decorated class per impl module plus a parent app file that
composes them; both flavors end with a generated `_trace.py` shim so the
emitted package is self-contained.
"""

from __future__ import annotations

import ast
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
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


class RefineSyntaxError(Exception):
    """Raised when an LLM-emitted module is not valid Python.

    Carries enough context for the pipeline to surface a useful message
    (which module, which file, which line). Never raised for the generated
    `_trace.py` / `__init__.py` shims — only for LLM output.
    """

    def __init__(
        self,
        *,
        module_name: str,
        filename: str,
        lineno: int | None,
        offset: int | None,
        message: str,
        source_excerpt: str = "",
    ) -> None:
        self.module_name = module_name
        self.filename = filename
        self.lineno = lineno
        self.offset = offset
        self.message = message
        self.source_excerpt = source_excerpt
        loc = f"{filename}:{lineno}" if lineno is not None else filename
        excerpt = f" — {source_excerpt!r}" if source_excerpt else ""
        super().__init__(
            f"SyntaxError in emitted module {module_name!r} at {loc}: "
            f"{message}{excerpt}"
        )


def _validate_python_source(
    *, module_name: str, filename: str, source: str
) -> None:
    """Parse `source` with `ast.parse` and raise RefineSyntaxError on failure.

    `filename` is passed to `ast.parse` so SyntaxError carries the real
    on-disk file name in its message — the same name we'll write later.
    """

    try:
        ast.parse(source, filename=filename)
    except SyntaxError as exc:
        excerpt = ""
        if exc.lineno is not None:
            lines = source.splitlines()
            if 1 <= exc.lineno <= len(lines):
                excerpt = lines[exc.lineno - 1].strip()
        raise RefineSyntaxError(
            module_name=module_name,
            filename=filename,
            lineno=exc.lineno,
            offset=exc.offset,
            message=exc.msg,
            source_excerpt=excerpt,
        ) from exc


class RefineRuntimeError(Exception):
    """Raised when the emitted package imports cleanly but crashes at runtime.

    Catches the class of bugs the static syntax check misses:
    AttributeError from mismatched attribute names, TypeError from
    method-signature drift, invariant violations on construction, etc.
    """

    def __init__(self, *, stderr: str, returncode: int | None) -> None:
        self.stderr = stderr
        self.returncode = returncode
        rc = f"exit code {returncode}" if returncode is not None else "timeout"
        super().__init__(
            f"smoke test failed ({rc}); stderr:\n{stderr}"
        )


def smoke_test_package(
    *,
    slug: str,
    package_parent_dir: Path,
    steps: int = 1,
    timeout_s: float = 30.0,
) -> None:
    """Subprocess-import the package and run `run(steps=...)`.

    Assumes the package has already been written to disk under
    ``package_parent_dir / slug``. Uses subprocess isolation so any
    icontract side-effects don't pollute the verifier process. Sets
    ``PYTHONHASHSEED=0`` to match the trace gate's environment so a
    smoke-test pass implies the trace gate will at least get past
    construction.
    """

    script = (
        "import sys, os; "
        f"sys.path.insert(0, {str(package_parent_dir)!r}); "
        f"from {slug}.app import run; "
        f"run(steps={steps})"
    )
    cmd = [sys.executable, "-X", "faulthandler", "-c", script]
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        completed = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stderr.decode("utf-8", errors="replace") if isinstance(
            exc.stderr, (bytes, bytearray)
        ) else (exc.stderr or "")
        raise RefineRuntimeError(stderr=partial, returncode=None) from exc

    if completed.returncode != 0:
        raise RefineRuntimeError(
            stderr=completed.stderr,
            returncode=completed.returncode,
        )


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
        module = PythonModuleSource(
            name=impl.name,
            source=data.get("python_module", ""),
            class_name=data.get("class_name", ""),
            entry_function=data.get("entry_function", ""),
        )
        _validate_python_source(
            module_name=module.name,
            filename=module.filename,
            source=module.source,
        )
        return module

    def _emit_parent_app(
        self, bundle: ModuleBundle, children: list[PythonModuleSource]
    ) -> PythonModuleSource:
        """One LLM call: emit the parent app that imports and composes children.

        The parent must reference the children by their *exact* emitted Python
        names (snake_case attributes, method signatures). To pin those down,
        we include each child's full source in the user message — the LLM
        otherwise tends to default to TLA-style PascalCase attribute names
        and crash at first construction. See REFINE_APP_SYSTEM for the rule.
        """

        # Map child name -> impl ModuleSource so we can surface the TLA cfg
        # constants the LLM must mirror when constructing each child.
        impls_by_name = {impl.name: impl for impl in bundle.impls()}

        child_blocks: list[str] = []
        for c in children:
            impl = impls_by_name.get(c.name)
            const_lines = ""
            if impl is not None and impl.constants.values:
                const_lines = (
                    "\n  TLA+ CONSTANT pins for this impl (the python "
                    "constructor MUST use these exact values so trace "
                    "conformance replays under matching bounds):\n"
                    + "\n".join(
                        f"    - {k} = {v}"
                        for k, v in impl.constants.values.items()
                    )
                )
            child_blocks.append(
                f"--- child `{c.name}` (file: `{c.filename}`, "
                f"class: `{c.class_name}`, entry: `{c.entry_function}`)"
                f"{const_lines} ---\n"
                f"```python\n{c.source}```"
            )

        user_msg = (
            f"Parent module ({bundle.parent.name}) TLA+ source:\n\n"
            f"{bundle.parent.tla_source}\n\n"
            "Children already emitted (their full Python source follows; the "
            "parent must call each class's actual constructor/method names "
            "and reference its actual instance attributes — do NOT invent "
            "PascalCase names from the TLA+ spec). The TLA+ CONSTANT pins "
            "are listed alongside each child; the parent's constructor for "
            "that child MUST pass values consistent with those pins (e.g. "
            "if the impl's `MaxLen = [3]`, instantiate the child with "
            "`max_len=3` — using a larger value will cause the trace gate "
            "to report `invariant_violated` because the spec rejects the "
            "out-of-range state):\n\n"
            + "\n\n".join(child_blocks)
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
        parent_module = PythonModuleSource(
            name=bundle.parent.name,
            source=data.get("python_module", ""),
            class_name=data.get("class_name", ""),
            entry_function=data.get("entry_function", "run"),
        )
        # Parent app is written to `app.py` on disk (see _write_package_outputs);
        # don't use `.filename` (which would snake-case the parent name).
        _validate_python_source(
            module_name=parent_module.name,
            filename="app.py",
            source=parent_module.source,
        )
        return parent_module

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
        python_module = data.get("python_module", "")
        _validate_python_source(
            module_name=verified.module_name,
            filename=f"{verified.module_name}.py",
            source=python_module,
        )
        return RefinedModule(
            python_module=python_module,
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
