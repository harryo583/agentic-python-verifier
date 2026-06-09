"""Tests for src/formal/refinement.py — all 7 scenarios."""

from __future__ import annotations

import pytest

from src.formal.refinement import (
    RefinementError,
    RefinementModule,
    generate_refinement_module,
    write_refinement_module,
)
from src.models.bundle import ModuleBundle, ModuleSource


# ---------------------------------------------------------------------------
# Helpers to build minimal test bundles
# ---------------------------------------------------------------------------

_TRIVIAL_TLA = "---- MODULE {name} ----\n===="


def _parent(name: str) -> ModuleSource:
    return ModuleSource(
        name=name,
        role="parent",
        tla_source=_TRIVIAL_TLA.format(name=name),
    )


def _impl(name: str, abstraction_map: dict[str, str] | None = None) -> ModuleSource:
    return ModuleSource(
        name=name,
        role="impl",
        tla_source=_TRIVIAL_TLA.format(name=f"{name}_Impl"),
        abstraction_map=abstraction_map or {},
    )


def _abs(name: str) -> ModuleSource:
    return ModuleSource(
        name=name,
        role="abs",
        tla_source=_TRIVIAL_TLA.format(name=f"{name}_Abs"),
    )


def _bundle(parent_name: str, modules: list[ModuleSource], slug: str) -> ModuleBundle:
    return ModuleBundle(
        parent=_parent(parent_name),
        modules=modules,
        slug=slug,
    )


# ---------------------------------------------------------------------------
# Scenario 1: single impl with abstraction_map
# ---------------------------------------------------------------------------

def test_single_impl_produces_correct_module():
    bundle = _bundle(
        "System",
        [
            _impl("Queue", {"q": "impl_q"}),
            _abs("Queue"),
        ],
        slug="system",
    )
    result = generate_refinement_module(bundle)

    assert isinstance(result, RefinementModule)
    assert result.module_name == "Refinement_System"

    src = result.source
    assert "---- MODULE Refinement_System ----" in src
    assert "EXTENDS System" in src
    assert "Abs_Queue == INSTANCE Queue_Abs WITH q <- impl_q" in src
    assert "RefinementSpec == Abs_Queue!Spec" in src
    assert "====" in src


# ---------------------------------------------------------------------------
# Scenario 2: multiple impls, all with abstraction_maps
# ---------------------------------------------------------------------------

def test_multiple_impls_produce_one_instance_each():
    bundle = _bundle(
        "Composed",
        [
            _impl("Counter", {"cnt": "impl_cnt"}),
            _abs("Counter"),
            _impl("Stack", {"elems": "impl_stack"}),
            _abs("Stack"),
        ],
        slug="composed",
    )
    result = generate_refinement_module(bundle)

    src = result.source
    assert "Abs_Counter == INSTANCE Counter_Abs WITH cnt <- impl_cnt" in src
    assert "Abs_Stack == INSTANCE Stack_Abs WITH elems <- impl_stack" in src
    # RefinementSpec must conjoin both
    assert "/\\ Abs_Counter!Spec" in src
    assert "/\\ Abs_Stack!Spec" in src
    # Both appear under RefinementSpec
    assert "RefinementSpec ==" in src


# ---------------------------------------------------------------------------
# Scenario 3: multi-key abstraction_map renders as multi-line WITH
# ---------------------------------------------------------------------------

def test_multikey_abstraction_map_multiline_with():
    bundle = _bundle(
        "Parent",
        [
            _impl("Bag", {"items": "impl_items", "size": "Cardinality(impl_items)"}),
            _abs("Bag"),
        ],
        slug="parent",
    )
    result = generate_refinement_module(bundle)

    src = result.source
    # The head line should have INSTANCE ... WITH (no inline clause)
    assert "Abs_Bag == INSTANCE Bag_Abs WITH" in src
    # Each key-value pair appears as an indented clause
    assert "items <- impl_items," in src
    assert "size <- Cardinality(impl_items)" in src
    # The last clause must NOT have a trailing comma
    lines = src.splitlines()
    last_clause_line = next(
        l for l in reversed(lines) if "size <- Cardinality" in l
    )
    assert not last_clause_line.rstrip().endswith(",")


# ---------------------------------------------------------------------------
# Scenario 4: zero refinable impls raises RefinementError with slug
# ---------------------------------------------------------------------------

def test_zero_refinable_impls_raises_error():
    bundle = _bundle(
        "Empty",
        [
            _impl("NoAbs"),  # empty abstraction_map
        ],
        slug="empty_bundle",
    )
    with pytest.raises(RefinementError, match="empty_bundle"):
        generate_refinement_module(bundle)


# ---------------------------------------------------------------------------
# Scenario 5: impl with abstraction_map but no matching abs raises error
# ---------------------------------------------------------------------------

def test_missing_abs_module_raises_error():
    bundle = _bundle(
        "Broken",
        [
            _impl("Orphan", {"x": "impl_x"}),
            # No _abs("Orphan") added — missing abs module
        ],
        slug="broken",
    )
    with pytest.raises(RefinementError, match="Orphan"):
        generate_refinement_module(bundle)


# ---------------------------------------------------------------------------
# Scenario 6: write_refinement_module writes file and returns path
# ---------------------------------------------------------------------------

def test_write_refinement_module_creates_file(tmp_path):
    bundle = _bundle(
        "FileTest",
        [
            _impl("Widget", {"w": "impl_w"}),
            _abs("Widget"),
        ],
        slug="file_test",
    )
    result_module = generate_refinement_module(bundle)
    returned_path = write_refinement_module(tmp_path, bundle)

    expected_path = tmp_path / "Refinement_FileTest.tla"
    assert returned_path == expected_path
    assert expected_path.exists()
    assert expected_path.read_text(encoding="utf-8") == result_module.source


# ---------------------------------------------------------------------------
# Scenario 7: impl with empty abstraction_map is skipped silently
# ---------------------------------------------------------------------------

def test_empty_abstraction_map_impl_is_skipped():
    bundle = _bundle(
        "Mixed",
        [
            _impl("NoMap"),          # empty map — should be skipped
            _impl("HasMap", {"v": "impl_v"}),
            _abs("HasMap"),
        ],
        slug="mixed",
    )
    result = generate_refinement_module(bundle)

    src = result.source
    # The skipped impl must not appear anywhere in the source
    assert "NoMap" not in src
    # The refinable impl must appear
    assert "Abs_HasMap == INSTANCE HasMap_Abs WITH v <- impl_v" in src
    assert "RefinementSpec == Abs_HasMap!Spec" in src


# ---------------------------------------------------------------------------
# Scenario 8: abs declares CONSTANTS — they must appear as identity bindings
# in the INSTANCE WITH, ahead of the variable bindings. Without these, SANY
# rejects the refinement module with "Unknown operator" cascades.
# ---------------------------------------------------------------------------

_ABS_WITH_CONSTANTS = """\
---- MODULE BackingStore_Abs ----
EXTENDS Naturals
CONSTANTS Keys, Vals
VARIABLES storePresent, storeVal
====
"""


def test_abs_constants_are_substituted_in_instance_with():
    abs_mod = ModuleSource(
        name="BackingStore",
        role="abs",
        tla_source=_ABS_WITH_CONSTANTS,
    )
    impl_mod = _impl(
        "BackingStore",
        {"storePresent": "S!storePresent", "storeVal": "S!storeVal"},
    )
    bundle = _bundle(
        "WriteThroughCacheSystem",
        [impl_mod, abs_mod],
        slug="write_through_cache",
    )

    src = generate_refinement_module(bundle).source

    # Multi-clause: head line carries the INSTANCE preamble, clauses follow.
    assert "Abs_BackingStore == INSTANCE BackingStore_Abs WITH" in src

    # Constants come BEFORE variables in the WITH clause list.
    lines = src.splitlines()
    clause_order = [
        l.strip().rstrip(",") for l in lines
        if l.strip().startswith(("Keys <-", "Vals <-", "storePresent <-", "storeVal <-"))
    ]
    assert clause_order == [
        "Keys <- Keys",
        "Vals <- Vals",
        "storePresent <- S!storePresent",
        "storeVal <- S!storeVal",
    ]

    # All non-final clauses get a trailing comma; the final one does not.
    body_lines = [l for l in lines if l.startswith("    ") and " <- " in l]
    for l in body_lines[:-1]:
        assert l.rstrip().endswith(","), f"missing trailing comma: {l!r}"
    assert not body_lines[-1].rstrip().endswith(",")


def test_abs_without_constants_is_unchanged():
    """Regression: an abs with no CONSTANTS line still produces a
    variables-only WITH clause (no spurious identity bindings)."""

    abs_mod = ModuleSource(
        name="Queue",
        role="abs",
        # _TRIVIAL_TLA has no CONSTANTS line.
        tla_source=_TRIVIAL_TLA.format(name="Queue_Abs"),
    )
    impl_mod = _impl("Queue", {"q": "impl_q"})
    bundle = _bundle("System", [impl_mod, abs_mod], slug="system")

    src = generate_refinement_module(bundle).source
    assert "Abs_Queue == INSTANCE Queue_Abs WITH q <- impl_q" in src


# ---------------------------------------------------------------------------
# Scenario 10: abs and parent disagree on CONSTANT names. The parent's
# `INSTANCE Consumer_Impl WITH ... MaxLen <- MaxItem` is the source of truth;
# the refinement module must mirror that binding (NOT identity `MaxLen <-
# MaxLen`), or SANY rejects with "Unknown operator: MaxLen".
# ---------------------------------------------------------------------------

_ABS_WITH_MAXLEN = """\
---- MODULE Consumer_Abs ----
EXTENDS Naturals
CONSTANTS MaxVal, MaxLen
VARIABLES received, sum
====
"""

_PARENT_REBINDS_MAXLEN = """\
---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxVal, MaxItem

VARIABLES received, sum, pcC

C == INSTANCE Consumer_Impl WITH received <- received, sum <- sum, pc <- pcC, MaxVal <- MaxVal, MaxLen <- MaxItem

vars == <<received, sum, pcC>>
====
"""


def test_parent_rebinds_abs_constant():
    """Bug B regression: when the parent's INSTANCE of <Name>_Impl rebinds
    the abs's CONSTANT (e.g. MaxLen <- MaxItem), the refinement module must
    use the parent's RHS, not identity."""

    abs_mod = ModuleSource(
        name="Consumer", role="abs", tla_source=_ABS_WITH_MAXLEN
    )
    impl_mod = _impl(
        "Consumer",
        {"received": "received", "sum": "sum"},
    )
    parent_mod = ModuleSource(
        name="ProducerConsumerSystem",
        role="parent",
        tla_source=_PARENT_REBINDS_MAXLEN,
    )
    bundle = ModuleBundle(
        parent=parent_mod,
        modules=[abs_mod, impl_mod],
        slug="producer_consumer_system",
    )

    src = generate_refinement_module(bundle).source

    # MaxVal binds to itself (parent uses same name).
    assert "MaxVal <- MaxVal" in src
    # MaxLen MUST bind to MaxItem (parent's choice), NOT MaxLen <- MaxLen.
    assert "MaxLen <- MaxItem" in src
    assert "MaxLen <- MaxLen" not in src
