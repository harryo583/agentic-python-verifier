"""Tests for RefineAgent.to_python_package (compositional refinement)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.agents.refine_agent import (
    RefineAgent,
    package_init_source,
    trace_shim_source,
)
from src.llm.anthropic_client import AnthropicClient
from src.models.bundle import (
    ModuleBundle,
    ModuleSource,
    PythonPackage,
)


@dataclass
class FakeBlock:
    type: str
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    text: str = ""


@dataclass
class FakeMessage:
    content: list[FakeBlock]


class FakeAnthropic:
    def __init__(self, scripted: list[FakeMessage]):
        self.scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        if not self.scripted:
            raise AssertionError("FakeAnthropic ran out of scripted responses")
        return self.scripted.pop(0)


def _make_client(scripted: list[FakeMessage]):
    fake = FakeAnthropic(scripted)
    client = AnthropicClient(api_key="x", model="claude-opus-4-7", client=fake)
    return client, fake


def _bundle() -> ModuleBundle:
    queue_impl = ModuleSource(
        name="Queue",
        role="impl",
        tla_source=(
            "---- MODULE Queue_Impl ----\n"
            "EXTENDS Integers\n"
            "VARIABLE buffer\n"
            "Inv == buffer \\in Seq(0..10) /\\ Len(buffer) <= 3\n"
            "(* --algorithm Queue { skip } *)\n===="
        ),
        pluscal_source="placeholder",
        abstraction_map={"queue": "buffer"},
    )
    queue_abs = ModuleSource(
        name="Queue",
        role="abs",
        tla_source="---- MODULE Queue_Abs ----\nVARIABLE queue\n====",
    )
    lock_impl = ModuleSource(
        name="Lock",
        role="impl",
        tla_source=(
            "---- MODULE Lock_Impl ----\n"
            "VARIABLE held\n"
            "Inv == held \\in BOOLEAN\n"
            "===="
        ),
        pluscal_source="placeholder",
        abstraction_map={"locked": "held"},
    )
    lock_abs = ModuleSource(
        name="Lock",
        role="abs",
        tla_source="---- MODULE Lock_Abs ----\nVARIABLE locked\n====",
    )
    parent = ModuleSource(
        name="System",
        role="parent",
        tla_source="---- MODULE System ----\nVARIABLES q,l\nInv == TRUE\n====",
    )
    return ModuleBundle(
        parent=parent,
        modules=[queue_abs, queue_impl, lock_abs, lock_impl],
        slug="qlock",
    )


def _emit_child_block(class_name: str, file_snake: str) -> FakeBlock:
    return FakeBlock(
        type="tool_use",
        id=f"tu_{file_snake}",
        name="emit_python_module_for_bundle",
        input={
            "python_module": (
                "from __future__ import annotations\n"
                "import icontract\n"
                "from ._trace import log_action\n"
                f"@icontract.invariant(lambda self: True)\n"
                f"class {class_name}:\n"
                "    def __init__(self) -> None: self.x = 0\n"
                "    def step(self) -> None:\n"
                f"        log_action('{class_name}.Step', {{'x': self.x}})\n"
            ),
            "class_name": class_name,
            "entry_function": "step",
            "assertion_map": [],
        },
    )


def _emit_app_block() -> FakeBlock:
    return FakeBlock(
        type="tool_use",
        id="tu_app",
        name="emit_python_app_for_bundle",
        input={
            "python_module": (
                "from __future__ import annotations\n"
                "import icontract\n"
                "from ._trace import log_action\n"
                "from .queue import Queue\n"
                "from .lock import Lock\n"
                "@icontract.invariant(lambda self: True)\n"
                "class System:\n"
                "    def __init__(self) -> None:\n"
                "        self.q = Queue()\n"
                "        self.l = Lock()\n"
                "    def step(self) -> None:\n"
                "        self.q.step(); self.l.step()\n"
                "        log_action('System.Step', {})\n"
                "def run(steps: int = 50) -> System:\n"
                "    app = System()\n"
                "    for _ in range(steps): app.step()\n"
                "    return app\n"
            ),
            "class_name": "System",
            "entry_function": "run",
        },
    )


def test_to_python_package_emits_n_plus_one_calls_in_order():
    client, fake = _make_client(
        [
            FakeMessage(content=[_emit_child_block("Queue", "queue")]),
            FakeMessage(content=[_emit_child_block("Lock", "lock")]),
            FakeMessage(content=[_emit_app_block()]),
        ]
    )
    agent = RefineAgent(client)

    package = agent.to_python_package(_bundle())

    assert isinstance(package, PythonPackage)
    assert package.slug == "qlock"
    assert len(package.modules) == 2
    assert [m.name for m in package.modules] == ["Queue", "Lock"]
    assert [m.class_name for m in package.modules] == ["Queue", "Lock"]
    assert package.parent_app is not None
    assert package.parent_app.class_name == "System"
    assert package.parent_app.entry_function == "run"

    # 3 LLM calls in order: child Queue, child Lock, parent app.
    assert len(fake.calls) == 3
    tool_names = [c["tool_choice"]["name"] for c in fake.calls]
    assert tool_names == [
        "emit_python_module_for_bundle",
        "emit_python_module_for_bundle",
        "emit_python_app_for_bundle",
    ]


def test_to_python_package_passes_abstraction_map_and_abs_source_to_llm():
    """The user message for each child should include the abstraction map +
    the sibling Abs's TLA+ source so the LLM can mirror Inv conjuncts."""

    client, fake = _make_client(
        [
            FakeMessage(content=[_emit_child_block("Queue", "queue")]),
            FakeMessage(content=[_emit_child_block("Lock", "lock")]),
            FakeMessage(content=[_emit_app_block()]),
        ]
    )
    agent = RefineAgent(client)
    agent.to_python_package(_bundle())

    queue_call_user_text = fake.calls[0]["messages"][0]["content"][0]["text"]
    assert "Queue_Impl" in queue_call_user_text
    assert "Queue_Abs" in queue_call_user_text
    assert "queue <- buffer" in queue_call_user_text  # abstraction map line
    assert "Inv" in queue_call_user_text


def test_to_python_package_parent_call_lists_child_classes():
    """The parent emit call must mention each child's filename + class_name
    so the LLM can wire the relative imports correctly."""

    client, fake = _make_client(
        [
            FakeMessage(content=[_emit_child_block("Queue", "queue")]),
            FakeMessage(content=[_emit_child_block("Lock", "lock")]),
            FakeMessage(content=[_emit_app_block()]),
        ]
    )
    agent = RefineAgent(client)
    agent.to_python_package(_bundle())

    app_call_user_text = fake.calls[2]["messages"][0]["content"][0]["text"]
    assert "queue.py" in app_call_user_text
    assert "lock.py" in app_call_user_text
    assert "Queue" in app_call_user_text
    assert "Lock" in app_call_user_text
    assert "System" in app_call_user_text


def test_to_python_package_filenames_are_snake_case():
    """Multi-word module names should snake-case correctly."""

    parent = ModuleSource(
        name="Parent",
        role="parent",
        tla_source="---- MODULE Parent ----\n====",
    )
    cache_abs = ModuleSource(
        name="CacheStore",
        role="abs",
        tla_source="---- MODULE CacheStore_Abs ----\n====",
    )
    cache_impl = ModuleSource(
        name="CacheStore",
        role="impl",
        tla_source="---- MODULE CacheStore_Impl ----\n(* --algorithm c {} *)====",
        pluscal_source="placeholder",
        abstraction_map={"store": "store"},
    )
    bundle = ModuleBundle(
        parent=parent,
        modules=[cache_abs, cache_impl],
        slug="cache_store",
    )

    client, _ = _make_client(
        [
            FakeMessage(content=[_emit_child_block("CacheStore", "cache_store")]),
            FakeMessage(content=[_emit_app_block()]),
        ]
    )
    agent = RefineAgent(client)
    package = agent.to_python_package(bundle)

    assert package.modules[0].filename == "cache_store.py"


def test_to_python_package_raises_when_no_impls():
    """A bundle with only abs modules has nothing to lower."""

    parent = ModuleSource(name="P", role="parent", tla_source="---- MODULE P ----\n====")
    abs_only = ModuleSource(
        name="Q", role="abs", tla_source="---- MODULE Q_Abs ----\n===="
    )
    bundle = ModuleBundle(parent=parent, modules=[abs_only], slug="abs_only")

    client, _ = _make_client([])
    agent = RefineAgent(client)
    with pytest.raises(ValueError, match="no impl modules"):
        agent.to_python_package(bundle)


def test_trace_shim_and_init_sources_are_well_formed():
    """Sanity: both helper strings parse as Python and expose the right symbols."""

    trace_src = trace_shim_source()
    assert "def log_action" in trace_src
    assert "ACTIONS" in trace_src

    init_src = package_init_source()
    assert init_src.endswith("\n")

    # Both must be exec-able under a fresh namespace.
    ns: dict[str, Any] = {}
    exec(trace_src, ns)
    assert "log_action" in ns
    assert "ACTIONS" in ns
    # No-op call still works.
    ns["log_action"]("step", {"x": 1})
    assert ns["ACTIONS"] == [("step", {"x": 1})]


def test_trace_shim_writes_jsonl_when_env_var_set(tmp_path, monkeypatch):
    """When TRACE_JSONL_PATH is set at import time, log_action appends a JSON
    line per call (in addition to the in-memory ACTIONS list)."""

    import json

    jsonl_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("TRACE_JSONL_PATH", str(jsonl_path))

    trace_src = trace_shim_source()
    ns: dict[str, Any] = {}
    exec(trace_src, ns)

    ns["log_action"]("Queue.Enqueue", {"queue": [1]})
    ns["log_action"]("Queue.Dequeue", {"queue": []})

    # Force the buffered file to flush before we read it back.
    ns["_JSONL_FH"].flush()

    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"action": "Queue.Enqueue", "state": {"queue": [1]}}
    assert json.loads(lines[1]) == {"action": "Queue.Dequeue", "state": {"queue": []}}
