"""Tests for the deterministic pre-flight linter (Feature #2)."""

from __future__ import annotations

from typing import Any

from src.formal.preflight import lint_bundle, preflight_proof
from src.models.bundle import ModuleBundle, ModuleSource


def _module(role: str, name: str, pluscal: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": name,
        "role": role,
        "tla_source": f"---- MODULE {name}_{role.title()} ----\n====",
    }
    if pluscal is not None:
        data["pluscal_source"] = pluscal
    return data


def _bundle(impl_pluscal: str | None) -> ModuleBundle:
    parent = ModuleSource.model_validate(
        {"name": "System", "role": "parent", "tla_source": "---- MODULE System ----\n===="}
    )
    modules = [
        ModuleSource.model_validate(_module("abs", "Producer")),
        ModuleSource.model_validate(_module("impl", "Producer", impl_pluscal)),
    ]
    return ModuleBundle(parent=parent, modules=modules, slug="prod_sys", notes="")


_RESERVED_PLUSCAL = """---- MODULE Producer_Impl ----
(* --algorithm Producer
variables x = 0;
begin
  Loop:
    x := 1;
  Done:
    skip;
end algorithm; *)
===="""

_CLEAN_PLUSCAL = """---- MODULE Producer_Impl ----
(* --algorithm Producer
variables x = 0, pc = "Loop";
Inv == pc \\in {"Loop", "Finish", "Done"}
begin
  Loop:
    x := 1;
  Finish:
    skip;
end algorithm; *)
===="""


def test_lint_flags_reserved_done_label():
    findings = lint_bundle(_bundle(_RESERVED_PLUSCAL))
    assert len(findings) == 1
    f = findings[0]
    assert f.module == "Producer"
    assert f.label == "Done"
    assert f.line == 7
    assert "reserved PlusCal label 'Done:'" in f.message


def test_lint_ignores_done_in_strings_and_assignments():
    # `pc \in {"Done"}` (string in an invariant) and a `Finish:` label only.
    findings = lint_bundle(_bundle(_CLEAN_PLUSCAL))
    assert findings == []


def test_lint_flags_lbl_n_and_error():
    pluscal = (
        "---- MODULE Producer_Impl ----\n"
        "(* --algorithm Producer\nbegin\n"
        "  Lbl_3:\n    skip;\n"
        "  Error:\n    skip;\n"
        "end algorithm; *)\n===="
    )
    labels = {f.label for f in lint_bundle(_bundle(pluscal))}
    assert labels == {"Lbl_3", "Error"}


def test_lint_uses_tla_source_when_no_pluscal():
    # Impl with the reserved label only in tla_source (pluscal_source absent).
    parent = ModuleSource.model_validate(
        {"name": "System", "role": "parent", "tla_source": "---- MODULE System ----\n===="}
    )
    impl = ModuleSource.model_validate(
        {
            "name": "Producer",
            "role": "impl",
            "tla_source": "---- MODULE Producer_Impl ----\n  Done:\n    skip\n====",
        }
    )
    bundle = ModuleBundle(parent=parent, modules=[impl], slug="s", notes="")
    findings = lint_bundle(bundle)
    assert len(findings) == 1 and findings[0].label == "Done"


def test_preflight_proof_marks_only_offending_module():
    bundle = _bundle(_RESERVED_PLUSCAL)
    findings = lint_bundle(bundle)
    proof = preflight_proof(bundle, findings)

    assert not proof.all_passed
    assert "Producer" in proof.failing_modules()
    # The note mentions pcal so the repair serialiser promotes it to a header.
    assert "pcal.trans" in proof.per_module["Producer"].init.note
    assert proof.refinement.passed


def test_preflight_proof_all_pass_when_no_findings():
    bundle = _bundle(_CLEAN_PLUSCAL)
    proof = preflight_proof(bundle, [])
    assert proof.all_passed
