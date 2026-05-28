"""Integration test: drive the renderer + postcondition parser against real TLC.

Gated on ``TLA2TOOLS_JAR``: skipped in CI/dev environments without the jar.
Exercises the full Trace_<Name>.tla -> TLC -> outcome pipeline on three
hand-crafted scenarios that cover the conforming, transition-divergence,
and invariant-violation buckets.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from src.formal.tla_runner import run_tlc
from src.formal.trace_postcondition import parse_trace_outcome
from src.formal.trace_renderer import (
    TraceEntry,
    render_trace_cfg,
    render_trace_module,
)
from src.models.synthesis import Constants


_JAR = os.environ.get("TLA2TOOLS_JAR")
_HAS_JAR = bool(_JAR and Path(_JAR).exists())
_HAS_JAVA = shutil.which("java") is not None

pytestmark = pytest.mark.skipif(
    not (_HAS_JAR and _HAS_JAVA),
    reason="TLA2TOOLS_JAR or java unavailable; integration test skipped",
)


_NULLARY_ABS = """\
---- MODULE Queue_Abs ----
EXTENDS Naturals, Sequences
VARIABLE queue
Init == queue = <<>>
Enqueue == queue \\in Seq(0..2) /\\ queue' = Append(queue, 1) /\\ Len(queue) < 3
Dequeue == queue /= <<>> /\\ queue' = Tail(queue)
Next == Enqueue \\/ Dequeue
Inv == Len(queue) \\in 0..3
====
"""


_PARAMETRIC_ABS = """\
---- MODULE Q_Abs ----
EXTENDS Naturals, Sequences
VARIABLE queue
Init == queue = <<>>
Enqueue(item) == queue' = Append(queue, item) /\\ Len(queue) < 3
Dequeue == queue /= <<>> /\\ queue' = Tail(queue)
Next == (\\E i \\in 1..9 : Enqueue(i)) \\/ Dequeue
Inv == Len(queue) \\in 0..3
====
"""


def _run(tmp_path: Path, abs_module: str, abs_source: str, entries: list[TraceEntry]):
    """Render trace module + cfg, drop both into tmp_path, run TLC."""

    (tmp_path / f"{abs_module}.tla").write_text(abs_source, encoding="utf-8")
    src = render_trace_module(
        class_name=abs_module.split("_")[0],
        abs_module_name=abs_module,
        abs_source=abs_source,
        entries=entries,
    )
    tla_path = tmp_path / f"Trace_{abs_module.split('_')[0]}.tla"
    cfg_path = tmp_path / f"Trace_{abs_module.split('_')[0]}.cfg"
    tla_path.write_text(src, encoding="utf-8")
    cfg_path.write_text(render_trace_cfg(Constants()), encoding="utf-8")
    return run_tlc(tla_path, cfg_path, _JAR, tmp_path, 30)


def test_real_tlc_accepts_conforming_nullary_trace(tmp_path):
    run = _run(
        tmp_path,
        "Queue_Abs",
        _NULLARY_ABS,
        [
            TraceEntry("Enqueue", {"queue": [1]}),
            TraceEntry("Enqueue", {"queue": [1, 1]}),
            TraceEntry("Dequeue", {"queue": [1]}),
        ],
    )
    out = parse_trace_outcome(run, expected_len=3)
    assert out.status == "conforms"
    assert out.tla_depth == 3


def test_real_tlc_rejects_transition_not_in_spec(tmp_path):
    """Step 2 records queue=<<1,1,1,1>>, but Enqueue produces Append(queue, 1)
    = <<1,1>>. No spec transition can produce <<1,1,1,1>> in one step."""

    run = _run(
        tmp_path,
        "Queue_Abs",
        _NULLARY_ABS,
        [
            TraceEntry("Enqueue", {"queue": [1]}),
            TraceEntry("Enqueue", {"queue": [1, 1, 1, 1]}),
        ],
    )
    out = parse_trace_outcome(run, expected_len=2)
    assert out.status == "diverged"
    assert out.divergence_step == 2


def test_real_tlc_reports_invariant_violation(tmp_path):
    """Use a tighter Inv that the trace violates at step 3."""

    abs_src = _NULLARY_ABS.replace(
        "Enqueue == queue \\in Seq(0..2) /\\ queue' = Append(queue, 1) /\\ Len(queue) < 3",
        "Enqueue == queue \\in Seq(0..2) /\\ queue' = Append(queue, 1)",
    ).replace(
        "Inv == Len(queue) \\in 0..3",
        "Inv == Len(queue) \\in 0..2",
    )
    run = _run(
        tmp_path,
        "Queue_Abs",
        abs_src,
        [
            TraceEntry("Enqueue", {"queue": [1]}),
            TraceEntry("Enqueue", {"queue": [1, 1]}),
            TraceEntry("Enqueue", {"queue": [1, 1, 1]}),
        ],
    )
    out = parse_trace_outcome(run, expected_len=3)
    assert out.status == "invariant_violated"
    assert out.divergence_step == 3


def test_real_tlc_accepts_conforming_parametric_trace(tmp_path):
    """Parametric abs: relation not enforced, but Inv at every state still
    catches bad transitions whose post-state breaks Inv."""

    run = _run(
        tmp_path,
        "Q_Abs",
        _PARAMETRIC_ABS,
        [
            TraceEntry("Enqueue", {"queue": [5]}),
            TraceEntry("Enqueue", {"queue": [5, 7]}),
            TraceEntry("Dequeue", {"queue": [7]}),
        ],
    )
    out = parse_trace_outcome(run, expected_len=3)
    assert out.status == "conforms"
    assert out.tla_depth == 3
