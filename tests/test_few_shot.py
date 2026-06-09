"""Tests for the few-shot exemplar pool (Feature #6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.llm.few_shot import (
    assert_disjoint,
    exemplar_slugs,
    load_exemplars,
    render_repair_few_shot,
    render_synth_few_shot,
)
from src.models.bundle import ModuleBundle, ModuleSource


def _exemplar_bundle() -> ModuleBundle:
    parent = ModuleSource.model_validate(
        {
            "name": "MutexSystem",
            "role": "parent",
            "tla_source": "---- MODULE MutexSystem ----\nL == INSTANCE Lock_Impl\nInv == TRUE\n====",
        }
    )
    abs_mod = ModuleSource.model_validate(
        {
            "name": "Lock",
            "role": "abs",
            "tla_source": "---- MODULE Lock_Abs ----\nVARIABLE held\n====",
        }
    )
    impl_mod = ModuleSource.model_validate(
        {
            "name": "Lock",
            "role": "impl",
            "tla_source": "---- MODULE Lock_Impl ----\n(* --algorithm L { skip } *)\n====",
            "pluscal_source": "---- MODULE Lock_Impl ----\n(* --algorithm L { skip } *)\n====",
            "abstraction_map": {"held": "owner # NoClient"},
        }
    )
    return ModuleBundle(
        parent=parent, modules=[abs_mod, impl_mod], slug="mutex", notes=""
    )


def _write_pool(root: Path, slug: str = "mutex") -> Path:
    pool = root / "examples_pool"
    d = pool / slug
    d.mkdir(parents=True)
    (d / "prompt.txt").write_text("A mutual-exclusion lock for N clients.\n")
    (d / "bundle.json").write_text(_exemplar_bundle().model_dump_json())
    return pool


def test_load_exemplars_reads_pool(tmp_path: Path):
    pool = _write_pool(tmp_path)
    exemplars = load_exemplars(pool)
    assert len(exemplars) == 1
    ex = exemplars[0]
    assert ex.slug == "mutex"
    assert "mutual-exclusion" in ex.prompt
    assert isinstance(ex.bundle, ModuleBundle)
    assert ex.bundle.slug == "mutex"


def test_load_exemplars_missing_dir_is_empty(tmp_path: Path):
    assert load_exemplars(tmp_path / "nope") == []
    assert load_exemplars(None) == []


def test_load_skips_incomplete_exemplar(tmp_path: Path):
    pool = tmp_path / "examples_pool"
    (pool / "partial").mkdir(parents=True)
    (pool / "partial" / "prompt.txt").write_text("x")  # no bundle.json
    assert load_exemplars(pool) == []


def test_render_synth_block_includes_structure(tmp_path: Path):
    pool = _write_pool(tmp_path)
    block = render_synth_few_shot(load_exemplars(pool))
    assert "Worked examples" in block
    assert "Exemplar: mutex" in block
    assert "MutexSystem" in block  # parent module rendered
    assert "abstraction_map: held <- owner # NoClient" in block
    assert "mutual-exclusion" in block


def test_render_empty_is_blank():
    assert render_synth_few_shot([]) == ""
    assert render_repair_few_shot([]) == ""


def test_assert_disjoint_raises_on_overlap(tmp_path: Path):
    pool = _write_pool(tmp_path, slug="producer_consumer")  # collides w/ benchmark
    assert exemplar_slugs(pool) == {"producer_consumer"}
    with pytest.raises(AssertionError, match="leakage"):
        assert_disjoint(pool, {"producer_consumer", "bank_audit"})


def test_assert_disjoint_passes_when_disjoint(tmp_path: Path):
    pool = _write_pool(tmp_path, slug="mutex")
    # Should not raise.
    assert_disjoint(pool, {"producer_consumer", "bank_audit"})
