"""Sanity-check every examples/<slug>/expected_modules.yaml.

This test loads each benchmark's expected decomposition and validates the
shape we depend on in scripts/run_benchmarks.py: parent_name + a non-empty
modules list, each with the three required keys.

Skips itself if PyYAML is not installed (we don't want to pull it in as a
runtime dep for the pipeline; it's a dev-time benchmark schema check).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")


_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
_ID_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")


def _benchmark_dirs() -> list[Path]:
    return sorted(d for d in _EXAMPLES_DIR.iterdir() if d.is_dir())


@pytest.mark.parametrize("bench_dir", _benchmark_dirs(), ids=lambda p: p.name)
def test_expected_modules_yaml_is_well_formed(bench_dir: Path):
    yaml_path = bench_dir / "expected_modules.yaml"
    prompt_path = bench_dir / "prompt.txt"
    assert prompt_path.exists(), f"missing {prompt_path}"
    assert yaml_path.exists(), f"missing {yaml_path}"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "parent_name" in data
    assert _ID_RE.match(data["parent_name"]), (
        f"parent_name {data['parent_name']!r} not a TLA+ identifier"
    )
    assert "parent_role" in data
    assert isinstance(data["modules"], list) and data["modules"], "modules must be non-empty list"

    for module in data["modules"]:
        assert _ID_RE.match(module["name"]), (
            f"module name {module['name']!r} not a TLA+ identifier"
        )
        assert "role" in module
        assert "state_variables" in module and module["state_variables"]
        assert "actions" in module and module["actions"]
        assert "invariant_sketch" in module
