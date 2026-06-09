"""Trace-conformance shim for the emitted package.

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
            json.dumps({"action": name, "state": snapshot}, default=str) + "\n"
        )
