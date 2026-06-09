"""Pure unit tests for the TLC counterexample parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.formal.counterexample_parser import parse_tlc_output
from src.formal.tla_runner import TLCRun


FIXTURES = Path(__file__).parent / "fixtures" / "tlc_traces"


def _run(name: str, returncode: int, *, timed_out: bool = False) -> TLCRun:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return TLCRun(
        returncode=returncode,
        stdout=text,
        stderr="",
        duration_s=0.5,
        timed_out=timed_out,
        cfg_path=Path("/tmp/x.cfg"),
        tla_path=Path("/tmp/x.tla"),
    )


def test_passed_run_returns_passed_status():
    run = _run("passed.txt", returncode=0)

    result = parse_tlc_output(run, "init")

    assert result.status == "passed"
    assert result.passed
    assert result.counterexample is None
    assert result.duration_s == 0.5


def test_invariant_violation_yields_counterexample_with_two_states():
    run = _run("invariant_violation.txt", returncode=12)

    result = parse_tlc_output(run, "init")

    assert result.status == "failed"
    assert not result.passed
    assert result.counterexample is not None
    ce = result.counterexample
    assert ce.violated_predicate == "Inv"
    assert ce.obligation == "init"
    assert len(ce.trace) == 2
    assert ce.trace[0].index == 1
    assert ce.trace[0].assignments == {"counter": "0", "pc": '"Increment"'}
    assert ce.trace[0].action == "Initial predicate"
    assert ce.trace[1].index == 2
    assert ce.trace[1].assignments == {"counter": "11", "pc": '"Done"'}
    assert "Increment" in (ce.trace[1].action or "")


def test_obligation_label_is_propagated_from_caller():
    run = _run("invariant_violation.txt", returncode=12)

    result = parse_tlc_output(run, "consec")

    assert result.obligation == "consec"
    assert result.counterexample is not None
    assert result.counterexample.obligation == "consec"


def test_initial_state_violation_has_single_state():
    run = _run("initial_violation.txt", returncode=12)

    result = parse_tlc_output(run, "init")

    assert result.status == "failed"
    assert result.counterexample is not None
    assert len(result.counterexample.trace) == 1
    assert result.counterexample.trace[0].assignments["counter"] == "-1"


def test_parse_error_returns_error_status_not_failed():
    run = _run("parse_error.txt", returncode=255)

    result = parse_tlc_output(run, "property")

    assert result.status == "error"
    assert result.counterexample is None
    assert "non-zero" in result.note.lower()


def test_timeout_returns_timeout_status_regardless_of_output():
    run = _run("passed.txt", returncode=-1, timed_out=True)

    result = parse_tlc_output(run, "consec")

    assert result.status == "timeout"
    assert result.counterexample is None
    assert "timeout" in result.note.lower()


def test_zero_returncode_without_no_error_line_is_error():
    run = TLCRun(
        returncode=0,
        stdout="TLC2 Version 2.18\nParsing file Foo.tla\n",
        stderr="",
        duration_s=0.1,
        timed_out=False,
        cfg_path=Path("/tmp/x.cfg"),
        tla_path=Path("/tmp/x.tla"),
    )

    result = parse_tlc_output(run, "init")

    assert result.status == "error"
