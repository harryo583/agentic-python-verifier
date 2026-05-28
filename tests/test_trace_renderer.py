"""Unit tests for src/formal/trace_renderer.py.

These tests cover the value-rendering type matrix, abs-module introspection
(VARIABLE / action-operator discovery), and the structural shape of the
generated Trace_<Name>.tla template.
"""

from __future__ import annotations

import pytest

from src.formal.trace_renderer import (
    TraceEntry,
    TraceRenderError,
    discover_abs_actions,
    discover_abs_variables,
    entries_from_records,
    is_parametric_action,
    render_trace_cfg,
    render_trace_module,
    render_value,
)
from src.models.synthesis import Constants


# ---------------------------------------------------------------------------
# render_value: leaf types
# ---------------------------------------------------------------------------


def test_render_value_bool_renders_uppercase():
    assert render_value(True) == "TRUE"
    assert render_value(False) == "FALSE"


def test_render_value_int():
    assert render_value(0) == "0"
    assert render_value(-7) == "-7"
    assert render_value(42) == "42"


def test_render_value_none_uses_sentinel():
    assert render_value(None) == '"_NONE_"'


def test_render_value_string_double_quotes_with_escapes():
    assert render_value("hello") == '"hello"'
    # backslash and quote escapes
    assert render_value('a"b') == '"a\\"b"'
    assert render_value("a\\b") == '"a\\\\b"'
    # control chars become literal escape sequences
    assert render_value("a\nb") == '"a\\nb"'


def test_render_value_rejects_float():
    with pytest.raises(TraceRenderError):
        render_value(1.5)


def test_render_value_rejects_custom_object():
    class Foo:
        pass

    with pytest.raises(TraceRenderError):
        render_value(Foo())


# ---------------------------------------------------------------------------
# render_value: containers
# ---------------------------------------------------------------------------


def test_render_value_list_becomes_sequence():
    assert render_value([1, 2, 3]) == "<<1, 2, 3>>"


def test_render_value_empty_list_is_empty_tuple():
    assert render_value([]) == "<<>>"


def test_render_value_nested_list():
    assert render_value([1, [2, 3], 4]) == "<<1, <<2, 3>>, 4>>"


def test_render_value_tuple_renders_same_as_list():
    assert render_value((1, 2, 3)) == "<<1, 2, 3>>"


def test_render_value_set_is_sorted_for_determinism():
    # Sets are unordered in Python; we sort by repr for stable diffs.
    out = render_value({3, 1, 2})
    assert out == "{1, 2, 3}"


def test_render_value_dict_with_safe_keys_renders_as_record():
    out = render_value({"x": 1, "y": 2})
    assert out == "[x |-> 1, y |-> 2]"


def test_render_value_dict_with_unsafe_key_renders_as_function():
    out = render_value({"weird-key": 1})
    # function literal: ("weird-key" :> 1)
    assert out == '("weird-key" :> 1)'


def test_render_value_dict_with_reserved_prefix_renders_as_function():
    # WF_/SF_ are reserved fairness prefixes; record form is unsafe.
    out = render_value({"WF_action": True})
    assert '"WF_action"' in out
    assert ":>" in out


def test_render_value_dict_with_digit_prefix_renders_as_function():
    out = render_value({"1abc": 0})
    assert ":>" in out


def test_render_value_empty_dict_uses_safe_sentinel():
    # TLA+ has no literal empty record; renderer emits a defensive sentinel.
    out = render_value({})
    assert out.startswith("[")
    assert "_NONE_" in out


def test_render_value_dict_rejects_non_string_keys():
    with pytest.raises(TraceRenderError):
        render_value({1: "x"})


# ---------------------------------------------------------------------------
# Abs introspection
# ---------------------------------------------------------------------------


_ABS_SRC = """\
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


def test_discover_abs_variables_single():
    assert discover_abs_variables(_ABS_SRC) == ["queue"]


def test_discover_abs_variables_multi_comma_separated():
    src = "VARIABLES x, y, z\nInv == TRUE\n"
    assert discover_abs_variables(src) == ["x", "y", "z"]


def test_discover_abs_actions_excludes_framework_names():
    actions = discover_abs_actions(_ABS_SRC)
    assert "Enqueue" in actions
    assert "Dequeue" in actions
    assert "Init" not in actions
    assert "Next" not in actions
    assert "Inv" not in actions


def test_is_parametric_action_true_for_arg_form():
    src = "Enqueue(item) == TRUE\n"
    assert is_parametric_action(src, "Enqueue") is True


def test_is_parametric_action_false_for_nullary():
    assert is_parametric_action(_ABS_SRC, "Enqueue") is False


# ---------------------------------------------------------------------------
# Trace module template
# ---------------------------------------------------------------------------


def _two_entry_trace() -> list[TraceEntry]:
    return [
        TraceEntry(action="Enqueue", state={"queue": [1]}),
        TraceEntry(action="Dequeue", state={"queue": []}),
    ]


def test_render_trace_module_has_required_sections():
    module = render_trace_module(
        class_name="Queue",
        abs_module_name="Queue_Abs",
        abs_source=_ABS_SRC,
        entries=_two_entry_trace(),
    )
    assert "---- MODULE Trace_Queue ----" in module
    assert "EXTENDS Queue_Abs, Sequences, Naturals, TLC" in module
    assert "Trace ==" in module
    assert "VARIABLE l" in module
    assert "IsEvent(e) ==" in module
    assert "TraceInit ==" in module
    assert "TraceNext ==" in module
    assert "TraceSpec == TraceInit" in module
    assert module.rstrip().endswith("====")


def test_render_trace_module_emits_one_disjunct_per_action():
    module = render_trace_module(
        class_name="Queue",
        abs_module_name="Queue_Abs",
        abs_source=_ABS_SRC,
        entries=_two_entry_trace(),
    )
    # Two abs actions (Enqueue, Dequeue) -> two disjunct branches in TraceNext.
    next_section = module.split("TraceNext ==")[1].split("TraceSpec ==")[0]
    branches = [
        line for line in next_section.splitlines() if line.strip().startswith("\\/")
    ]
    assert len(branches) == 2


def test_render_trace_module_records_event_and_abs_vars():
    module = render_trace_module(
        class_name="Queue",
        abs_module_name="Queue_Abs",
        abs_source=_ABS_SRC,
        entries=_two_entry_trace(),
    )
    assert 'event |-> "Enqueue"' in module
    assert "queue |-> <<1>>" in module
    assert "queue |-> <<>>" in module


def test_render_trace_module_handles_parametric_action():
    """Parametric abs actions degrade: keep IsEvent (state binding from the
    recorded post-state) but drop the action-relation conjunct so TLC doesn't
    have to invent the parameter value. Inv still gets checked at every
    state."""

    src = """\
---- MODULE Q_Abs ----
VARIABLE queue
Enqueue(item) == queue' = Append(queue, item)
Inv == TRUE
====
"""
    module = render_trace_module(
        class_name="Q",
        abs_module_name="Q_Abs",
        abs_source=src,
        entries=[TraceEntry(action="Enqueue", state={"queue": [0]})],
    )
    # Should only contain IsEvent, not the bare Enqueue(...) relation.
    assert 'IsEvent("Enqueue")' in module
    assert "parametric" in module  # documenting comment
    assert "Enqueue(__arg)" not in module
    assert "\\E __arg" not in module


def test_render_trace_module_fallback_when_no_actions_discovered():
    src = "---- MODULE X_Abs ----\nVARIABLE x\nInv == TRUE\n===="
    module = render_trace_module(
        class_name="X",
        abs_module_name="X_Abs",
        abs_source=src,
        entries=[TraceEntry(action="Step", state={"x": 0})],
    )
    assert "UNCHANGED vars" in module
    assert "No top-level action operators discovered" in module


def test_render_trace_module_rejects_empty_entries():
    with pytest.raises(TraceRenderError, match="zero entries"):
        render_trace_module(
            class_name="Q",
            abs_module_name="Q_Abs",
            abs_source=_ABS_SRC,
            entries=[],
        )


def test_render_trace_module_rejects_missing_abs_var_in_state():
    bad_entry = TraceEntry(action="Enqueue", state={"unrelated": 1})
    with pytest.raises(TraceRenderError, match="missing abs variable"):
        render_trace_module(
            class_name="Queue",
            abs_module_name="Queue_Abs",
            abs_source=_ABS_SRC,
            entries=[bad_entry],
        )


def test_render_trace_module_rejects_abs_with_no_variables():
    src = "---- MODULE X_Abs ----\nInv == TRUE\n===="
    with pytest.raises(TraceRenderError, match="VARIABLE"):
        render_trace_module(
            class_name="X",
            abs_module_name="X_Abs",
            abs_source=src,
            entries=[TraceEntry(action="A", state={})],
        )


# ---------------------------------------------------------------------------
# Cfg
# ---------------------------------------------------------------------------


def test_render_trace_cfg_minimal():
    cfg = render_trace_cfg(Constants())
    assert "SPECIFICATION TraceSpec" in cfg
    assert "INVARIANT Inv" in cfg


def test_render_trace_cfg_includes_constants():
    cfg = render_trace_cfg(Constants(values={"N": [3]}))
    assert "CONSTANT" in cfg
    assert "N" in cfg


# ---------------------------------------------------------------------------
# entries_from_records (gate-side filter)
# ---------------------------------------------------------------------------


def test_entries_from_records_filters_by_class_prefix():
    records = [
        {"action": "Queue.Enqueue", "state": {"queue": [1]}},
        {"action": "Lock.Acquire", "state": {"locked": True}},
        {"action": "Queue.Dequeue", "state": {"queue": []}},
        {"action": "System.Step", "state": {}},
    ]
    out = entries_from_records(records, "Queue")
    assert len(out) == 2
    assert out[0].action == "Enqueue"
    assert out[1].action == "Dequeue"


def test_entries_from_records_drops_dotless_actions():
    records = [
        {"action": "no_dot_here", "state": {"x": 1}},
        {"action": "Queue.Enqueue", "state": {"queue": [1]}},
    ]
    out = entries_from_records(records, "Queue")
    assert len(out) == 1


def test_entries_from_records_drops_non_dict_state():
    records = [
        {"action": "Queue.A", "state": "not a dict"},
        {"action": "Queue.B", "state": {"q": [1]}},
    ]
    out = entries_from_records(records, "Queue")
    assert len(out) == 1
    assert out[0].action == "B"
