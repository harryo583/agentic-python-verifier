"""Tests for .cfg generation and auxiliary module emission."""

from __future__ import annotations

from pathlib import Path

from src.formal.tlc_config import (
    write_consec_cfg,
    write_consec_module,
    write_init_cfg,
    write_property_cfg,
    write_property_module,
)
from src.models.synthesis import Constants


def test_init_cfg_uses_spec_and_invariant(tmp_path: Path):
    cfg = tmp_path / "init.cfg"
    write_init_cfg(cfg, "Inv", Constants(values={"MaxValue": [10]}))

    content = cfg.read_text()
    assert "SPECIFICATION Spec" in content
    assert "INVARIANT Inv" in content
    assert "CONSTANT MaxValue = 10" in content


def test_consec_cfg_uses_ispec(tmp_path: Path):
    cfg = tmp_path / "consec.cfg"
    write_consec_cfg(cfg, "Inv", Constants(values={"N": [3, 5, 10]}))

    content = cfg.read_text()
    assert "SPECIFICATION ISpec" in content
    assert "INVARIANT Inv" in content
    assert "CONSTANT N = {3, 5, 10}" in content


def test_property_cfg_uses_pspec_and_property(tmp_path: Path):
    cfg = tmp_path / "property.cfg"
    write_property_cfg(cfg, "Property", Constants(values={"MaxValue": [10]}))

    content = cfg.read_text()
    assert "SPECIFICATION PSpec" in content
    assert "INVARIANT Property" in content


def test_string_constants_quoted(tmp_path: Path):
    cfg = tmp_path / "init.cfg"
    write_init_cfg(cfg, "Inv", Constants(values={"States": ["IDLE", "RUNNING"]}))

    assert 'CONSTANT States = {"IDLE", "RUNNING"}' in cfg.read_text()


def test_consec_module_extends_main(tmp_path: Path):
    path = write_consec_module(tmp_path, "BoundedCounter", "Inv")

    content = path.read_text()
    assert "MODULE Consec_BoundedCounter" in content
    assert "EXTENDS BoundedCounter" in content
    assert "IInit == Inv" in content
    assert "ISpec == IInit /\\ [][Next]_vars" in content


def test_property_module_uses_unchanged_step(tmp_path: Path):
    path = write_property_module(tmp_path, "BoundedCounter", "Inv")

    content = path.read_text()
    assert "MODULE Prop_BoundedCounter" in content
    assert "PInit == Inv" in content
    assert "[][UNCHANGED vars]_vars" in content
