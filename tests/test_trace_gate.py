"""Unit tests for src/agents/trace_gate.py.

The gate's two side effects (subprocess + TLC) are both monkeypatched so the
tests run hermetically without `tla2tools.jar` or a real Python interpreter
invocation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from src.agents import trace_gate as trace_gate_mod
from src.agents.trace_gate import TraceGate
from src.config import Settings
from src.formal.tla_runner import TLCRun
from src.models.bundle import (
    ModuleBundle,
    ModuleSource,
    PythonModuleSource,
    PythonPackage,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _settings(tmp_path: Path) -> Settings:
    jar = tmp_path / "fake.jar"
    jar.write_text("")
    return Settings(
        project_root=tmp_path,
        generated_dir=tmp_path / "gen",
        tla_dir=tmp_path / "gen" / "tla",
        python_dir=tmp_path / "gen" / "python",
        work_dir=tmp_path / "gen" / "work",
        anthropic_api_key="fake-key",
        openai_api_key=None,
        tla2tools_jar=str(jar),
        model="claude-opus-4-7",
        fallback_model="claude-opus-4-6",
        openai_model="gpt-5.4",
        max_iterations=3,
        tlc_timeout_s=30,
        log_level="INFO",
    )


_ABS_SOURCE = """\
---- MODULE Queue_Abs ----
EXTENDS Naturals, Sequences
VARIABLE queue
Init == queue = <<>>
Enqueue == queue' = Append(queue, 1)
Dequeue == queue /= <<>> /\\ queue' = Tail(queue)
Next == Enqueue \\/ Dequeue
Inv == Len(queue) <= 3
====
"""


def _bundle(slug: str = "qlock") -> ModuleBundle:
    queue_abs = ModuleSource(
        name="Queue", role="abs", tla_source=_ABS_SOURCE
    )
    queue_impl = ModuleSource(
        name="Queue",
        role="impl",
        tla_source="---- MODULE Queue_Impl ----\nVARIABLE buffer\n====",
        pluscal_source="placeholder",
        abstraction_map={"queue": "buffer"},
    )
    lock_abs = ModuleSource(
        name="Lock",
        role="abs",
        tla_source=(
            "---- MODULE Lock_Abs ----\nVARIABLE held\n"
            "Acquire == held' = TRUE\n"
            "Inv == TRUE\n===="
        ),
    )
    lock_impl = ModuleSource(
        name="Lock",
        role="impl",
        tla_source="---- MODULE Lock_Impl ----\nVARIABLE locked\n====",
        pluscal_source="placeholder",
        abstraction_map={"held": "locked"},
    )
    parent = ModuleSource(
        name="System",
        role="parent",
        tla_source="---- MODULE System ----\nVARIABLES q, l\n====",
    )
    return ModuleBundle(
        parent=parent,
        modules=[queue_abs, queue_impl, lock_abs, lock_impl],
        slug=slug,
    )


def _package(slug: str = "qlock") -> PythonPackage:
    return PythonPackage(
        slug=slug,
        modules=[
            PythonModuleSource(name="Queue", source="...", class_name="Queue"),
            PythonModuleSource(name="Lock", source="...", class_name="Lock"),
        ],
        parent_app=PythonModuleSource(
            name="System", source="...", class_name="System"
        ),
    )


# ---------------------------------------------------------------------------
# Subprocess + JSONL handling
# ---------------------------------------------------------------------------


def test_gate_short_circuits_when_no_parent_app(tmp_path):
    settings = _settings(tmp_path)
    gate = TraceGate(settings=settings)
    bundle = _bundle()
    pkg = PythonPackage(
        slug=bundle.slug,
        modules=[PythonModuleSource(name="Queue", source="", class_name="Queue")],
        parent_app=None,
    )
    work_dir = tmp_path / "work"
    result = gate.check(pkg, bundle, work_dir)
    assert set(result.keys()) == {"Queue", "Lock"}
    assert all(r.status == "skipped" for r in result.values())
    assert "no parent_app" in result["Queue"].note


def test_gate_handles_subprocess_nonzero_returncode(tmp_path, monkeypatch):
    """A subprocess failure yields python_crashed for every child."""

    settings = _settings(tmp_path)
    bundle = _bundle()
    pkg = _package()
    work_dir = tmp_path / "work"

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="exploded"
        )

    monkeypatch.setattr(trace_gate_mod.subprocess, "run", fake_run)

    gate = TraceGate(settings=settings)
    result = gate.check(pkg, bundle, work_dir)
    assert all(r.status == "python_crashed" for r in result.values())
    assert "exploded" in result["Queue"].note


def test_gate_handles_subprocess_timeout(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    bundle = _bundle()
    pkg = _package()
    work_dir = tmp_path / "work"

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1, stderr="partial")

    monkeypatch.setattr(trace_gate_mod.subprocess, "run", fake_run)
    gate = TraceGate(settings=settings)
    result = gate.check(pkg, bundle, work_dir)
    assert all(r.status == "python_crashed" for r in result.values())
    assert "timed out" in result["Queue"].note


def test_gate_returns_empty_when_jsonl_missing(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    bundle = _bundle()
    pkg = _package()
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True)

    def fake_run(*args, **kwargs):
        # Pretend subprocess ran cleanly but never wrote trace.jsonl
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(trace_gate_mod.subprocess, "run", fake_run)
    gate = TraceGate(settings=settings)
    result = gate.check(pkg, bundle, work_dir)
    assert all(r.status == "empty" for r in result.values())


def test_gate_subprocess_invocation_uses_env_isolation(tmp_path, monkeypatch):
    """The gate must run python with a controlled env (PYTHONHASHSEED=0,
    TRACE_*) and capture stdout/stderr. We verify the env shape, not the
    actual binary."""

    settings = _settings(tmp_path)
    bundle = _bundle()
    pkg = _package()
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True)

    captured: dict[str, Any] = {}

    def fake_run(cmd, *, env=None, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = env
        # Write a tiny valid JSONL so the gate can proceed.
        Path(env["TRACE_JSONL_PATH"]).write_text(
            json.dumps({"action": "Queue.Enqueue", "state": {"queue": [1]}}) + "\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(trace_gate_mod.subprocess, "run", fake_run)
    # Also short-circuit run_tlc; we only care about the env here.
    monkeypatch.setattr(
        trace_gate_mod,
        "run_tlc",
        lambda *a, **k: TLCRun(
            returncode=0,
            stdout="Model checking completed. No error has been found.\nThe depth of the complete state graph search is 1.\n",
            stderr="",
            duration_s=0.01,
            timed_out=False,
            cfg_path=a[1],
            tla_path=a[0],
        ),
    )

    gate = TraceGate(settings=settings)
    # Make sure the abs file is reachable: put it where _abs_source_for looks.
    abs_drop = work_dir.parent / "Queue_Abs.tla"
    abs_drop.write_text(_ABS_SOURCE, encoding="utf-8")
    gate.check(pkg, bundle, work_dir)

    env = captured["env"]
    assert env["PYTHONHASHSEED"] == "0"
    assert env["TRACE_SEED"] == "0"
    assert env["TRACE_STEPS"] == "50"
    assert "TRACE_JSONL_PATH" in env
    assert env["TRACE_PKG_PARENT"] == str(settings.python_dir)
    # No inherited env vars (e.g. HOME) -- we built env from scratch.
    assert set(env.keys()) <= {
        "PATH",
        "TRACE_JSONL_PATH",
        "TRACE_SEED",
        "TRACE_STEPS",
        "TRACE_PKG_PARENT",
        "PYTHONHASHSEED",
        "PYTHONDONTWRITEBYTECODE",
    }


# ---------------------------------------------------------------------------
# Per-child fan-out
# ---------------------------------------------------------------------------


def _setup_clean_run(
    tmp_path: Path, monkeypatch, jsonl_lines: list[dict[str, Any]], tlc_stdout: str
) -> tuple[TraceGate, ModuleBundle, PythonPackage, Path]:
    settings = _settings(tmp_path)
    bundle = _bundle()
    pkg = _package()
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True)
    # Drop abs files where _abs_source_for can find them.
    (work_dir.parent / "Queue_Abs.tla").write_text(_ABS_SOURCE, encoding="utf-8")
    (work_dir.parent / "Lock_Abs.tla").write_text(
        (
            "---- MODULE Lock_Abs ----\nVARIABLE held\n"
            "Acquire == held' = TRUE\nInv == TRUE\n===="
        ),
        encoding="utf-8",
    )

    def fake_run(cmd, *, env=None, **kwargs):
        Path(env["TRACE_JSONL_PATH"]).write_text(
            "\n".join(json.dumps(line) for line in jsonl_lines) + "\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(trace_gate_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(
        trace_gate_mod,
        "run_tlc",
        lambda *a, **k: TLCRun(
            returncode=0,
            stdout=tlc_stdout,
            stderr="",
            duration_s=0.01,
            timed_out=False,
            cfg_path=a[1],
            tla_path=a[0],
        ),
    )

    return TraceGate(settings=settings), bundle, pkg, work_dir


def test_gate_partitions_actions_by_class_prefix(tmp_path, monkeypatch):
    gate, bundle, pkg, work_dir = _setup_clean_run(
        tmp_path,
        monkeypatch,
        jsonl_lines=[
            {"action": "Queue.Enqueue", "state": {"queue": [1]}},
            {"action": "Queue.Dequeue", "state": {"queue": []}},
            {"action": "Lock.Acquire", "state": {"held": True}},
            {"action": "System.Step", "state": {}},
        ],
        tlc_stdout=(
            "Model checking completed. No error has been found.\n"
            "The depth of the complete state graph search is 2.\n"
        ),
    )
    result = gate.check(pkg, bundle, work_dir)
    assert set(result.keys()) == {"Queue", "Lock"}
    # System.Step (parent) is filtered out; not its own key.


def test_gate_marks_class_with_no_entries_as_empty(tmp_path, monkeypatch):
    gate, bundle, pkg, work_dir = _setup_clean_run(
        tmp_path,
        monkeypatch,
        jsonl_lines=[{"action": "Queue.Enqueue", "state": {"queue": [1]}}],
        tlc_stdout=(
            "Model checking completed. No error has been found.\n"
            "The depth of the complete state graph search is 1.\n"
        ),
    )
    result = gate.check(pkg, bundle, work_dir)
    # Queue should have one entry. Lock has zero -> empty.
    assert result["Lock"].status == "empty"
    assert result["Lock"].trace_length == 0


def test_gate_threads_tlc_depth_into_conforms(tmp_path, monkeypatch):
    gate, bundle, pkg, work_dir = _setup_clean_run(
        tmp_path,
        monkeypatch,
        jsonl_lines=[
            {"action": "Queue.Enqueue", "state": {"queue": [1]}},
            {"action": "Queue.Dequeue", "state": {"queue": []}},
        ],
        tlc_stdout=(
            "Model checking completed. No error has been found.\n"
            "The depth of the complete state graph search is 2.\n"
        ),
    )
    result = gate.check(pkg, bundle, work_dir)
    assert result["Queue"].status == "conforms"
    assert result["Queue"].tla_depth == 2
    assert result["Queue"].trace_length == 2


def test_gate_reports_diverged_from_short_depth(tmp_path, monkeypatch):
    gate, bundle, pkg, work_dir = _setup_clean_run(
        tmp_path,
        monkeypatch,
        jsonl_lines=[
            {"action": "Queue.Enqueue", "state": {"queue": [1]}},
            {"action": "Queue.Dequeue", "state": {"queue": []}},
            {"action": "Queue.Enqueue", "state": {"queue": [1]}},
        ],
        tlc_stdout=(
            "Model checking completed. No error has been found.\n"
            "The depth of the complete state graph search is 1.\n"
        ),
    )
    result = gate.check(pkg, bundle, work_dir)
    assert result["Queue"].status == "diverged"
    assert result["Queue"].divergence_step == 2


def test_gate_buckets_render_error_as_tlc_error(tmp_path, monkeypatch):
    """Passing a Python float blows up the renderer; surface as tlc_error."""

    gate, bundle, pkg, work_dir = _setup_clean_run(
        tmp_path,
        monkeypatch,
        jsonl_lines=[
            {"action": "Queue.Enqueue", "state": {"queue": [1.5]}},
        ],
        tlc_stdout="",  # never reached
    )
    result = gate.check(pkg, bundle, work_dir)
    assert result["Queue"].status == "tlc_error"
    assert "float" in result["Queue"].note.lower() or "render" in result["Queue"].note.lower()


def test_gate_truncates_at_max_entries(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    settings.trace_max_entries = 2  # force truncation
    bundle = _bundle()
    pkg = _package()
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True)
    (work_dir.parent / "Queue_Abs.tla").write_text(_ABS_SOURCE, encoding="utf-8")
    (work_dir.parent / "Lock_Abs.tla").write_text(
        (
            "---- MODULE Lock_Abs ----\nVARIABLE held\n"
            "Acquire == held' = TRUE\nInv == TRUE\n===="
        ),
        encoding="utf-8",
    )

    def fake_run(cmd, *, env=None, **kwargs):
        lines = [
            {"action": "Queue.Enqueue", "state": {"queue": [1]}},
            {"action": "Queue.Enqueue", "state": {"queue": [1, 1]}},
            {"action": "Queue.Enqueue", "state": {"queue": [1, 1, 1]}},
        ]
        Path(env["TRACE_JSONL_PATH"]).write_text(
            "\n".join(json.dumps(line) for line in lines) + "\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(trace_gate_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(
        trace_gate_mod,
        "run_tlc",
        lambda *a, **k: TLCRun(
            returncode=0,
            stdout=(
                "No error has been found.\n"
                "The depth of the complete state graph search is 2.\n"
            ),
            stderr="",
            duration_s=0.01,
            timed_out=False,
            cfg_path=a[1],
            tla_path=a[0],
        ),
    )

    gate = TraceGate(settings=settings)
    result = gate.check(pkg, bundle, work_dir)
    assert result["Queue"].trace_length == 2  # capped
    assert "truncated" in result["Queue"].note
