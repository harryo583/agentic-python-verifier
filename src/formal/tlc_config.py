"""TLC `.cfg` and auxiliary `.tla` generators for the three proof obligations.

Encoding:
- Initiation (Init => Inv): run TLC over the LLM module's `Spec` with `INVARIANT Inv`.
  A length-1 violation is the canonical Init failure.
- Consecution (Inv /\\ Next => Inv'): write `Consec_<Module>.tla` whose IInit == Inv,
  so TLC initialises from any Inv-state. Length-1 violation = inductive step failed.
- Property (Inv => Property): write `Prop_<Module>.tla` with PInit == Inv and
  Next == UNCHANGED vars, enumerating Inv-states and checking Property.

The auxiliary modules EXTEND the LLM module so they pick up `Inv`, `Property`,
`Next`, and `vars` via re-export.
"""

from __future__ import annotations

from pathlib import Path

from src.models.synthesis import Constants


def _cfg(spec: str, invariant: str, constants: Constants) -> str:
    parts = [f"SPECIFICATION {spec}", f"INVARIANT {invariant}"]
    parts.extend(constants.to_cfg_lines())
    return "\n".join(parts) + "\n"


def write_init_cfg(
    cfg_path: Path,
    invariant_name: str,
    constants: Constants,
) -> None:
    cfg_path.write_text(_cfg("Spec", invariant_name, constants), encoding="utf-8")


def write_consec_cfg(
    cfg_path: Path,
    invariant_name: str,
    constants: Constants,
) -> None:
    cfg_path.write_text(_cfg("ISpec", invariant_name, constants), encoding="utf-8")


def write_property_cfg(
    cfg_path: Path,
    property_name: str,
    constants: Constants,
) -> None:
    cfg_path.write_text(_cfg("PSpec", property_name, constants), encoding="utf-8")


CONSEC_TEMPLATE = """\
---- MODULE Consec_{module} ----
EXTENDS {module}

\\* Treat every Inv-satisfying state as initial; one step must preserve Inv.
IInit == {inv}
ISpec == IInit /\\ [][Next]_vars

====
"""


PROP_TEMPLATE = """\
---- MODULE Prop_{module} ----
EXTENDS {module}

\\* Enumerate Inv-states (no transitions); check Property on each.
PInit == {inv}
PSpec == PInit /\\ [][UNCHANGED vars]_vars

====
"""


def write_consec_module(work_dir: Path, module: str, invariant_name: str) -> Path:
    path = work_dir / f"Consec_{module}.tla"
    path.write_text(
        CONSEC_TEMPLATE.format(module=module, inv=invariant_name),
        encoding="utf-8",
    )
    return path


def write_property_module(work_dir: Path, module: str, invariant_name: str) -> Path:
    path = work_dir / f"Prop_{module}.tla"
    path.write_text(
        PROP_TEMPLATE.format(module=module, inv=invariant_name),
        encoding="utf-8",
    )
    return path
