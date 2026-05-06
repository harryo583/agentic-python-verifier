"""Parse TLC stdout/stderr into structured ObligationResult."""

from __future__ import annotations

import re

from src.formal.tla_runner import TLCRun
from src.models.proof import (
    Counterexample,
    ObligationResult,
    Obligation,
    TraceState,
)


_INVARIANT_VIOLATION_RE = re.compile(
    r"Error: Invariant\s+(?P<name>\S+)\s+is violated\."
)
_INITIAL_PRED_VIOLATION_RE = re.compile(
    r"Error:\s+(?:The initial predicate|Initial state)\s+(?P<name>\S+)?", re.IGNORECASE
)
_EVAL_ERROR_RE = re.compile(
    r"Error: In evaluation, the identifier (?P<name>\S+) is either undefined.*"
)
_GENERIC_ERROR_RE = re.compile(r"^Error:\s*(?P<msg>.+)$", re.MULTILINE)
_STATE_HEADER_RE = re.compile(r"^State\s+(\d+):\s*(.*?)\s*$")
_ASSIGNMENT_RE = re.compile(r"^/\\\s*(\w+)\s*=\s*(.+?)\s*$")
_NO_ERROR_RE = re.compile(r"Model checking completed\.\s*No error has been found\.?")


def parse_tlc_output(run: TLCRun, obligation: Obligation) -> ObligationResult:
    """Convert a TLCRun into an ObligationResult."""

    stdout = run.stdout or ""
    stderr = run.stderr or ""
    combined = stdout + "\n" + stderr

    if run.timed_out:
        return ObligationResult(
            obligation=obligation,
            status="timeout",
            tlc_returncode=run.returncode,
            duration_s=run.duration_s,
            raw_stdout=stdout,
            raw_stderr=stderr,
            note=f"TLC exceeded the configured timeout while checking {obligation}.",
        )

    if run.returncode == 0 and _NO_ERROR_RE.search(combined):
        return ObligationResult(
            obligation=obligation,
            status="passed",
            tlc_returncode=0,
            duration_s=run.duration_s,
            raw_stdout=stdout,
            raw_stderr=stderr,
        )

    inv_match = _INVARIANT_VIOLATION_RE.search(combined)
    init_match = _INITIAL_PRED_VIOLATION_RE.search(combined) if inv_match is None else None

    if inv_match or init_match:
        violated = (inv_match or init_match).group("name") or "<unknown>"
        trace = _extract_trace(combined)
        excerpt = _excerpt_around(combined, inv_match or init_match, lines_before=2, lines_after=12)
        return ObligationResult(
            obligation=obligation,
            status="failed",
            tlc_returncode=run.returncode,
            duration_s=run.duration_s,
            counterexample=Counterexample(
                obligation=obligation,
                violated_predicate=violated,
                trace=trace,
                raw_excerpt=excerpt,
            ),
            raw_stdout=stdout,
            raw_stderr=stderr,
        )

    eval_match = _EVAL_ERROR_RE.search(combined)
    if eval_match:
        excerpt = _excerpt_around(combined, eval_match, lines_before=1, lines_after=8)
        return ObligationResult(
            obligation=obligation,
            status="error",
            tlc_returncode=run.returncode,
            duration_s=run.duration_s,
            raw_stdout=stdout,
            raw_stderr=stderr,
            note=(
                f"TLC could not enumerate states from the spec/invariant: identifier "
                f"`{eval_match.group('name')}` is undefined or unbounded. This "
                "usually means `Inv` (used as the initial predicate for the "
                "consec/property checks) does not bound a variable via explicit "
                "set membership.\n" + excerpt
            ),
        )

    generic = _GENERIC_ERROR_RE.search(combined)
    note = (
        "TLC exited with a non-zero code but no recognisable invariant or "
        "initial-predicate violation was found in its output. This usually "
        "means a parse/semantic error in the spec or config."
    )
    if generic:
        note += "\nFirst error line: " + generic.group("msg").strip()
    return ObligationResult(
        obligation=obligation,
        status="error",
        tlc_returncode=run.returncode,
        duration_s=run.duration_s,
        raw_stdout=stdout,
        raw_stderr=stderr,
        note=note,
    )


def _extract_trace(text: str) -> list[TraceState]:
    """Extract `State N: <action>` blocks and their `/\\ var = value` body."""

    states: list[TraceState] = []
    current: TraceState | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        header = _STATE_HEADER_RE.match(line)
        if header:
            if current is not None:
                states.append(current)
            idx = int(header.group(1))
            action = header.group(2).strip("<> ").strip() or None
            current = TraceState(index=idx, action=action, assignments={})
            continue
        if current is None:
            continue
        assign = _ASSIGNMENT_RE.match(line)
        if assign:
            current.assignments[assign.group(1)] = assign.group(2)
            continue
        if line == "" and current.assignments:
            states.append(current)
            current = None
    if current is not None and current.assignments:
        states.append(current)
    return states


def _excerpt_around(text: str, match: re.Match | None, lines_before: int, lines_after: int) -> str:
    if match is None:
        return ""
    lines = text.splitlines()
    start_pos = match.start()
    line_index = text[:start_pos].count("\n")
    lo = max(0, line_index - lines_before)
    hi = min(len(lines), line_index + lines_after + 1)
    return "\n".join(lines[lo:hi])
