"""Unit tests for src/formal/trace_postcondition.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.formal.tla_runner import TLCRun
from src.formal.trace_postcondition import parse_trace_outcome, to_trace_result


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "tlc_traces"


def _run_from_fixture(name: str, *, timed_out: bool = False, returncode: int = 0) -> TLCRun:
    stdout = (_FIXTURE_DIR / name).read_text(encoding="utf-8")
    return TLCRun(
        returncode=returncode,
        stdout=stdout,
        stderr="",
        duration_s=0.1,
        timed_out=timed_out,
        cfg_path=Path("/dev/null/cfg"),
        tla_path=Path("/dev/null/tla"),
    )


def test_parse_trace_outcome_conforms_when_depth_matches():
    run = _run_from_fixture("trace_passed.txt")
    out = parse_trace_outcome(run, expected_len=3)
    assert out.status == "conforms"
    assert out.tla_depth == 3
    assert out.divergence_step is None


def test_parse_trace_outcome_conforms_one_step_trace():
    """Depth=1 with expected_len=1 still conforms."""

    stdout = (
        "Model checking completed. No error has been found.\n"
        "The depth of the complete state graph search is 1.\n"
    )
    run = TLCRun(
        returncode=0,
        stdout=stdout,
        stderr="",
        duration_s=0.05,
        timed_out=False,
        cfg_path=Path("/x"),
        tla_path=Path("/x"),
    )
    out = parse_trace_outcome(run, expected_len=1)
    assert out.status == "conforms"


def test_parse_trace_outcome_diverged_when_depth_shorter():
    run = _run_from_fixture("trace_diverged.txt")
    out = parse_trace_outcome(run, expected_len=3)
    assert out.status == "diverged"
    assert out.tla_depth == 1
    assert out.divergence_step == 2
    assert "2" in out.note or "transition" in out.note.lower()


def test_parse_trace_outcome_invariant_violation():
    run = _run_from_fixture("trace_inv_violation.txt")
    out = parse_trace_outcome(run, expected_len=2)
    assert out.status == "invariant_violated"
    # Last State header in the counterexample is the violating state (State 2
    # in this fixture: queue=<<1,1,1,1>>, which exceeds Inv's bound).
    assert out.divergence_step == 2
    assert "Inv" in out.note


def test_parse_trace_outcome_timeout():
    run = TLCRun(
        returncode=-1,
        stdout="",
        stderr="",
        duration_s=120.0,
        timed_out=True,
        cfg_path=Path("/x"),
        tla_path=Path("/x"),
    )
    out = parse_trace_outcome(run, expected_len=10)
    assert out.status == "tlc_timeout"
    assert out.divergence_step is None


def test_parse_trace_outcome_no_depth_line_is_error():
    run = TLCRun(
        returncode=1,
        stdout="completely unexpected garbage",
        stderr="",
        duration_s=0.01,
        timed_out=False,
        cfg_path=Path("/x"),
        tla_path=Path("/x"),
    )
    out = parse_trace_outcome(run, expected_len=3)
    assert out.status == "tlc_error"


def test_parse_trace_outcome_depth_exceeds_expected_is_error():
    """Should never happen with our IsEvent guard, but we surface it loudly."""

    stdout = (
        "Model checking completed. No error has been found.\n"
        "The depth of the complete state graph search is 9.\n"
    )
    run = TLCRun(
        returncode=0,
        stdout=stdout,
        stderr="",
        duration_s=0.1,
        timed_out=False,
        cfg_path=Path("/x"),
        tla_path=Path("/x"),
    )
    out = parse_trace_outcome(run, expected_len=3)
    assert out.status == "tlc_error"


def test_to_trace_result_lifts_outcome():
    run = _run_from_fixture("trace_passed.txt")
    out = parse_trace_outcome(run, expected_len=3)
    result = to_trace_result(out, child_name="Queue", trace_length=3)
    assert result.child_name == "Queue"
    assert result.status == "conforms"
    assert result.conforms is True
    assert result.tla_depth == 3
    assert result.trace_length == 3
