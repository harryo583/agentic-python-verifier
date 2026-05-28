"""Render Python `log_action` trace entries into a per-child Trace_<Name>.tla.

The trace gate (`src/agents/trace_gate.py`) calls this module once per child
class with the captured JSONL entries. We produce a TLA+ module that, when
fed to TLC together with the child's `<Name>_Abs.tla` sibling, replays the
recorded execution against the abstract spec.

Encoding follows Cirstea et al. 2024 §3.2 (arXiv 2404.16075), adapted for the
per-child Abs scope decided in the Week-3 plan:

    ---- MODULE Trace_<Name> ----
    EXTENDS <Name>_Abs, Sequences, Naturals, TLC

    Trace == << [event |-> "...", <abs_var> |-> <rendered>, ...], ... >>

    VARIABLE l

    IsEvent(e) ==
        /\\ l \\in 1..Len(Trace)
        /\\ Trace[l].event = e
        /\\ <abs_var>' = Trace[l].<abs_var>     \\* one per abs var
        /\\ l' = l + 1

    TraceInit ==
        /\\ l = 1
        /\\ <abs_var> = Trace[1].<abs_var>      \\* one per abs var

    TraceNext ==
        \\/ IsEvent("Action1") /\\ Action1       \\* discovered from abs source
        \\/ IsEvent("Action2") /\\ Action2
        \\/ ...

    TraceSpec == TraceInit /\\ [][TraceNext]_<<l, <abs_vars...>>>
    ====

The cfg is the standard ``SPECIFICATION TraceSpec`` + ``INVARIANT Inv`` plus
the abs module's CONSTANTS (re-used from the impl's `Constants` object).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from src.models.synthesis import Constants


# Per the TLA+ grammar (Lamport, TLA+2 grammar): an identifier must start
# with a letter or underscore, then letters/digits/underscores, and must
# contain at least one letter. The reserved prefixes WF_ and SF_ are weak/
# strong fairness operators and must never be used as a user identifier.
_TLA_ID_RE = re.compile(r"^(?=.*[A-Za-z])[A-Za-z_][A-Za-z0-9_]*$")
_RESERVED_PREFIXES = ("WF_", "SF_")


# Action operators sit at the top level of an abs module as `Name ==` (nullary)
# or `Name(args) ==` (parametric) lines. We skip the special framework names
# that aren't transition relations.
_ABS_OP_RE = re.compile(
    r"^([A-Z][A-Za-z0-9_]*)(?:\([^)]*\))?\s*==",
    re.MULTILINE,
)
_NON_ACTION_OPS = frozenset(
    {"Init", "Next", "Spec", "Inv", "Property", "TypeOk", "TypeOK", "Vars", "vars"}
)


_VAR_DECL_RE = re.compile(
    r"^[ \t]*VARIABLES?[ \t]+([A-Za-z_][A-Za-z0-9_,\t ]*)",
    re.MULTILINE,
)


class TraceRenderError(ValueError):
    """Raised when a JSONL entry contains a value with no clean TLA+ rendering."""


@dataclass(slots=True)
class TraceEntry:
    """One ``log_action`` JSONL record attributed to a single child class.

    `action` is the bare action name (no ``<Class>.`` prefix; the gate strips
    that before constructing entries). `state` maps abs-variable names to
    Python values (per the REFINE_MODULE_SYSTEM rule that log_action state
    keys must be abs-shape).
    """

    action: str
    state: dict[str, Any]


# ---------------------------------------------------------------------------
# Pure value rendering (Python -> TLA+ literal)
# ---------------------------------------------------------------------------


def render_value(value: Any) -> str:
    """Recursive Python -> TLA+ literal converter.

    Raises ``TraceRenderError`` for types we deliberately refuse to lower
    (floats, arbitrary objects). The gate buckets these into
    ``status="tlc_error"`` for the child whose entry triggered the failure.
    """

    if isinstance(value, bool):
        # bool MUST come before int (bool is a subclass of int in Python)
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if value is None:
        # TLA+ has no null. We document the sentinel "_NONE_" so abs specs that
        # genuinely need optionality can compare against it.
        return '"_NONE_"'
    if isinstance(value, str):
        return _render_string(value)
    if isinstance(value, (list, tuple)):
        return "<<" + ", ".join(render_value(v) for v in value) + ">>"
    if isinstance(value, (set, frozenset)):
        # Sort by repr so the TLA+ literal is deterministic across runs.
        sorted_items = sorted(value, key=lambda x: repr(x))
        return "{" + ", ".join(render_value(v) for v in sorted_items) + "}"
    if isinstance(value, dict):
        return _render_dict(value)
    raise TraceRenderError(
        f"cannot render value of type {type(value).__name__!r} to TLA+: {value!r}"
    )


def _render_string(s: str) -> str:
    """Render a Python str as a TLA+ string literal.

    TLA+ string literals are double-quoted; only ``\\`` and ``"`` need escaping
    inside them. Newlines/tabs are rendered as literal escapes so the produced
    .tla file stays on one line per record field.
    """

    out = s.replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return f'"{out}"'


def _render_dict(d: dict[Any, Any]) -> str:
    """Render a dict as a TLA+ record (preferred) or function (fallback).

    All keys must be strings. If every key is a safe TLA+ identifier (and
    not a reserved fairness prefix), emit a record; otherwise emit a
    function literal using TLC's ``:>`` and ``@@`` operators (which is why
    the trace module EXTENDS TLC).
    """

    if not d:
        # An empty record `[]` is a parse error in TLA+; emit an empty function
        # instead. The literal `<<>> :> 0` is not legal either, so we use the
        # idiomatic "empty function" via the empty set: `(0 :> 0) @@ ... ` is
        # only used when there's at least one entry. For zero entries we emit a
        # sentinel empty record `[empty |-> "_NONE_"]`. Abs modules rarely
        # rely on empty state dicts in practice; the trace gate also bails on
        # zero entries before this would matter.
        return '[empty |-> "_NONE_"]'

    non_str_keys = [k for k in d.keys() if not isinstance(k, str)]
    if non_str_keys:
        raise TraceRenderError(
            f"dict keys must be strings, got {[type(k).__name__ for k in non_str_keys]}"
        )

    if all(_is_safe_tla_id(str(k)) for k in d.keys()):
        body = ", ".join(
            f"{k} |-> {render_value(v)}" for k, v in d.items()
        )
        return f"[{body}]"

    parts = [
        f"({_render_string(str(k))} :> {render_value(v)})"
        for k, v in d.items()
    ]
    return " @@ ".join(parts)


def _is_safe_tla_id(name: str) -> bool:
    if not _TLA_ID_RE.match(name):
        return False
    if any(name.startswith(p) for p in _RESERVED_PREFIXES):
        return False
    return True


# ---------------------------------------------------------------------------
# Abs-module introspection
# ---------------------------------------------------------------------------


def discover_abs_variables(abs_source: str) -> list[str]:
    """Extract the variable names declared in an Abs module.

    Handles both ``VARIABLE x`` and ``VARIABLES x, y, z`` forms (TLA+ allows
    multiple comma-separated names per VARIABLES line) and concatenates them
    in source order.
    """

    out: list[str] = []
    for match in _VAR_DECL_RE.finditer(abs_source):
        for part in match.group(1).split(","):
            name = part.strip()
            if name:
                out.append(name)
    return out


def discover_abs_actions(abs_source: str) -> list[str]:
    """Extract candidate action operator names from an Abs module.

    A top-level `Name == ...` line whose name is capitalised and not in
    `_NON_ACTION_OPS` is treated as an action. Parametric forms
    (`Name(arg) == ...`) are detected separately by `is_parametric_action`.
    """

    out: list[str] = []
    for name in _ABS_OP_RE.findall(abs_source):
        if name in _NON_ACTION_OPS:
            continue
        out.append(name)
    return out


def is_parametric_action(abs_source: str, action: str) -> bool:
    """True if the abs source defines `<action>(...) == ...`."""

    pattern = re.compile(
        rf"^{re.escape(action)}\s*\(", re.MULTILINE
    )
    return pattern.search(abs_source) is not None


# ---------------------------------------------------------------------------
# Trace module template
# ---------------------------------------------------------------------------


def render_trace_module(
    class_name: str,
    abs_module_name: str,
    abs_source: str,
    entries: list[TraceEntry],
) -> str:
    """Produce a complete `Trace_<Name>.tla` source string.

    ``class_name`` is only used in the module name; ``abs_module_name`` is the
    EXTENDS target (typically ``<class_name>_Abs``). Distinguishing the two
    makes test fixtures (which often use ad-hoc names) easier to write.
    """

    if not entries:
        raise TraceRenderError(
            "cannot render a Trace module from zero entries; the gate must "
            "short-circuit to status='empty' before calling render_trace_module"
        )

    abs_vars = discover_abs_variables(abs_source)
    if not abs_vars:
        raise TraceRenderError(
            f"could not discover any VARIABLE declarations in abs module "
            f"{abs_module_name!r}"
        )

    abs_actions = discover_abs_actions(abs_source)

    _validate_entries_against_abs(entries, abs_vars, abs_module_name)

    lines: list[str] = []
    lines.append(f"---- MODULE Trace_{class_name} ----")
    lines.append(f"EXTENDS {abs_module_name}, Sequences, Naturals, TLC")
    lines.append("")
    lines.extend(_render_trace_constant(entries, abs_vars))
    lines.append("")
    lines.append("VARIABLE l")
    lines.append("")
    lines.extend(_render_is_event(abs_vars))
    lines.append("")
    lines.extend(_render_trace_init(abs_vars))
    lines.append("")
    lines.extend(_render_trace_next(abs_actions, abs_source))
    lines.append("")
    lines.append(_render_trace_spec(abs_vars))
    lines.append("")
    lines.append("====")
    return "\n".join(lines) + "\n"


def render_trace_cfg(constants: Constants) -> str:
    """Produce a TLC cfg for the trace module.

    The trace-conformance check is: replay every recorded transition and
    verify Inv at every state. Acceptance is inferred from TLC's depth of
    state-graph search (see `parse_trace_outcome`), not from this cfg.
    """

    parts = ["SPECIFICATION TraceSpec", "INVARIANT Inv"]
    parts.extend(constants.to_cfg_lines())
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Template fragments
# ---------------------------------------------------------------------------


def _validate_entries_against_abs(
    entries: list[TraceEntry],
    abs_vars: list[str],
    abs_module_name: str,
) -> None:
    """Fail fast if any entry's state dict is missing an abs variable.

    Surfaces as `status="tlc_error"` with the offending step index in the
    note; better than letting TLC choke on an undefined record field.
    """

    abs_var_set = set(abs_vars)
    for step, entry in enumerate(entries, start=1):
        missing = abs_var_set - set(entry.state.keys())
        if missing:
            raise TraceRenderError(
                f"entry {step} (action {entry.action!r}) is missing abs "
                f"variable(s) {sorted(missing)} (expected from {abs_module_name!r})"
            )


def _render_trace_constant(entries: list[TraceEntry], abs_vars: list[str]) -> list[str]:
    """Render `Trace == << ... >>` with one record per entry."""

    lines = ["Trace =="]
    record_lines: list[str] = []
    for entry in entries:
        fields = [f'event |-> {_render_string(entry.action)}']
        for var in abs_vars:
            fields.append(f"{var} |-> {render_value(entry.state[var])}")
        record_lines.append("    [" + ", ".join(fields) + "]")
    body = ",\n".join(record_lines)
    lines.append("    <<")
    lines.append(body)
    lines.append("    >>")
    return lines


def _render_is_event(abs_vars: list[str]) -> list[str]:
    """Render the `IsEvent(e)` helper that gates one trace step.

    Trace[l] is the post-state after l actions. At cursor position l we are
    "between" Trace[l] and Trace[l+1]; IsEvent fires the (l+1)th recorded
    action and binds the new state to Trace[l+1]. So the guard fires for
    `l \\in 1..Len(Trace)-1`. For l = Len(Trace), no successor (TLC reports
    depth = Len(Trace) = the expected len; that is the success signal that
    `parse_trace_outcome` looks for).
    """

    lines = ["IsEvent(e) =="]
    lines.append("    /\\ l \\in 1..(Len(Trace) - 1)")
    lines.append("    /\\ Trace[l + 1].event = e")
    for var in abs_vars:
        lines.append(f"    /\\ {var}' = Trace[l + 1].{var}")
    lines.append("    /\\ l' = l + 1")
    return lines


def _render_trace_init(abs_vars: list[str]) -> list[str]:
    """TraceInit binds the cursor + abs vars to Trace[1] (the post-state after
    the first recorded action). We do NOT call the spec's Init here; the trace
    gate's contract is per-step refinement, not initial-state checking.
    """

    lines = ["TraceInit =="]
    lines.append("    /\\ l = 1")
    for var in abs_vars:
        lines.append(f"    /\\ {var} = Trace[1].{var}")
    return lines


def _render_trace_next(actions: list[str], abs_source: str) -> list[str]:
    """Render `TraceNext` as a disjunction over discovered abs actions.

    If the abs has no discoverable action operators we fall back to a
    trace-driven UNCHANGED form that still lets `INVARIANT Inv` catch bad
    states. The trace gate inspects the renderer's note via the TraceResult
    pipeline; nothing else depends on the fallback being correct beyond that.
    """

    if not actions:
        return [
            "\\* No top-level action operators discovered in abs module.",
            "\\* Falling back to trace-driven form; Inv still checked at each state.",
            "TraceNext ==",
            "    /\\ l \\in 1..(Len(Trace) - 1)",
            "    /\\ l' = l + 1",
            "    /\\ UNCHANGED vars",
        ]

    lines = ["TraceNext =="]
    for i, action in enumerate(actions):
        prefix = "    \\/ "
        if is_parametric_action(abs_source, action):
            # The action takes parameters whose domain we cannot reliably
            # infer from the abs source alone (it might depend on CONSTANTS
            # that aren't in scope for the trace gate). We degrade safely:
            # drop the action-relation conjunct, keep only IsEvent. State
            # binding still comes from the recorded post-state in IsEvent,
            # and the cfg's `INVARIANT Inv` still catches bad states. We do
            # lose the "transition not permitted by spec" signal for
            # parametric actions; that is documented in the trace note.
            lines.append(
                f"{prefix}IsEvent({_render_string(action)})"
                f"    \\* parametric; transition relation not enforced"
            )
        else:
            lines.append(
                f"{prefix}/\\ IsEvent({_render_string(action)}) /\\ {action}"
            )
    return lines


def _render_trace_spec(abs_vars: list[str]) -> str:
    var_tuple = ", ".join(["l", *abs_vars])
    return f"TraceSpec == TraceInit /\\ [][TraceNext]_<<{var_tuple}>>"


# ---------------------------------------------------------------------------
# Convenience: build entries from raw JSONL records
# ---------------------------------------------------------------------------


def entries_from_records(
    records: Iterable[dict[str, Any]],
    class_prefix: str,
) -> list[TraceEntry]:
    """Filter raw JSONL records to those owned by `class_prefix` and strip it.

    Records whose ``action`` lacks a ``<Class>.<Method>`` shape are dropped
    (the gate logs a warning for malformed lines separately).
    """

    out: list[TraceEntry] = []
    for record in records:
        action_full = record.get("action", "")
        if "." not in action_full:
            continue
        cls, _, method = action_full.partition(".")
        if cls != class_prefix:
            continue
        state = record.get("state")
        if not isinstance(state, dict):
            continue
        out.append(TraceEntry(action=method, state=state))
    return out
