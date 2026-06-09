"""Map a TLC run on a Trace_<Name>.tla module to a TraceResult outcome.

`tla2tools.jar` v2.19 has no POSTCONDITION, so trace acceptance is inferred
from stdout: TLC always reports ``The depth of the complete state graph
search is N.`` on a clean finish. For our `IsEvent`-gated trace spec the
depth equals the number of trace entries consumed; comparing against the
expected length distinguishes ``conforms`` from ``diverged``.

Invariant violations are caught with the same regex `counterexample_parser`
already uses, with the trace step number lifted from the failing `State N`
block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from src.formal.counterexample_parser import (
    _INVARIANT_VIOLATION_RE,
    _NO_ERROR_RE,
    _STATE_HEADER_RE,
)
from src.formal.tla_runner import TLCRun
from src.models.bundle import TraceResult, TraceStatus


_DEPTH_RE = re.compile(r"The depth of the complete state graph search is (\d+)\.")


@dataclass(slots=True)
class TraceOutcome:
    """Internal carrier; the gate wraps this in a TraceResult per child."""

    status: TraceStatus
    tla_depth: Optional[int]
    divergence_step: Optional[int]
    note: str


def parse_trace_outcome(run: TLCRun, expected_len: int) -> TraceOutcome:
    """Classify one TLC run against an expected trace length.

    Decision order (matches the failure-mode matrix in the plan):
      1. Timeout -> tlc_timeout
      2. Invariant violation -> invariant_violated (extract failing State N)
      3. depth == expected_len AND no error -> conforms
      4. depth <  expected_len AND no error -> diverged at depth+1
      5. anything else -> tlc_error
    """

    stdout = run.stdout or ""
    stderr = run.stderr or ""
    combined = stdout + "\n" + stderr

    if run.timed_out:
        return TraceOutcome(
            status="tlc_timeout",
            tla_depth=None,
            divergence_step=None,
            note=f"TLC exceeded timeout after {run.duration_s:.1f}s",
        )

    inv_match = _INVARIANT_VIOLATION_RE.search(combined)
    if inv_match is not None:
        failing_step = _last_state_index(combined)
        violated = inv_match.group("name")
        excerpt = _excerpt_around(combined, inv_match)
        return TraceOutcome(
            status="invariant_violated",
            tla_depth=None,
            divergence_step=failing_step,
            note=f"abs invariant {violated!r} violated\n{excerpt}",
        )

    depth_match = _DEPTH_RE.search(combined)
    if depth_match is None:
        return TraceOutcome(
            status="tlc_error",
            tla_depth=None,
            divergence_step=None,
            note=(
                "TLC produced no depth line and no recognised invariant "
                f"violation (returncode={run.returncode}). First 800 chars "
                f"of stdout:\n{stdout[:800]}"
            ),
        )

    depth = int(depth_match.group(1))
    has_no_error = bool(_NO_ERROR_RE.search(combined))

    if has_no_error and depth == expected_len:
        return TraceOutcome(
            status="conforms",
            tla_depth=depth,
            divergence_step=None,
            note=f"replayed {expected_len} entries against abs spec",
        )

    if depth < expected_len:
        return TraceOutcome(
            status="diverged",
            tla_depth=depth,
            divergence_step=depth + 1,
            note=(
                f"TLC reached depth {depth}/{expected_len}; abs spec does not "
                f"permit the transition recorded at step {depth + 1}"
            ),
        )

    # depth > expected_len shouldn't happen with our IsEvent guard, but be
    # explicit rather than silently passing.
    return TraceOutcome(
        status="tlc_error",
        tla_depth=depth,
        divergence_step=None,
        note=(
            f"TLC depth {depth} exceeds expected trace length {expected_len}; "
            "Trace constant or IsEvent guard is malformed"
        ),
    )


def to_trace_result(
    outcome: TraceOutcome,
    *,
    child_name: str,
    trace_length: int,
) -> TraceResult:
    """Lift a TraceOutcome into a TraceResult tagged with the child's name."""

    return TraceResult(
        child_name=child_name,
        status=outcome.status,
        tla_depth=outcome.tla_depth,
        trace_length=trace_length,
        divergence_step=outcome.divergence_step,
        note=outcome.note,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _last_state_index(combined: str) -> Optional[int]:
    """Return the LAST `State N:` index found in TLC's counterexample dump.

    TLC dumps every state on the offending path, ending with the state that
    violates the invariant. For our trace spec where `l` starts at 1 and
    advances by 1 per IsEvent step, TLC's State K corresponds to trace
    post-step K (i.e. the state immediately after the K-th recorded action),
    so the LAST State block is the trace step that broke things.
    """

    last: Optional[int] = None
    for raw_line in combined.splitlines():
        header = _STATE_HEADER_RE.match(raw_line.rstrip())
        if header:
            try:
                last = int(header.group(1))
            except (TypeError, ValueError):
                continue
    return last


def _excerpt_around(text: str, match: re.Match, lines_around: int = 6) -> str:
    lines = text.splitlines()
    line_index = text[: match.start()].count("\n")
    lo = max(0, line_index - 1)
    hi = min(len(lines), line_index + lines_around + 1)
    return "\n".join(lines[lo:hi])
