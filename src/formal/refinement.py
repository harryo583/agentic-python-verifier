"""Generate the `Refinement_<Parent>.tla` auxiliary module.

The verifier writes this file to a per-bundle work directory and runs TLC
against it as a 4th proof obligation (in addition to the per-impl Init / Consec
/ Property checks).

Pattern (Hillel Wayne, https://www.hillelwayne.com/post/tla-adt/):

    ---- MODULE Refinement_<Parent> ----
    EXTENDS <Parent>            \\* gives us every INSTANCE the parent composes
    Abs_<ModName> == INSTANCE <ModName>_Abs
                       WITH <abs_var> <- <expr_over_impl_vars>
    \\* (one Abs_<ModName> per impl with a non-empty abstraction_map)
    RefinementSpec == /\\ Abs_<ModName1>!Spec
                      /\\ Abs_<ModName2>!Spec
                      ...
    ====

EXTENDS the parent (rather than `<Parent>_Impl`) because the parent module is
where the impl INSTANCEs already live: the parent composes the impl modules,
so its scope already has all the impl variables we need to write expressions
over in the WITH clause.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.models.bundle import ModuleBundle, ModuleSource


class RefinementError(RuntimeError):
    """Raised when a ModuleBundle cannot produce a refinement aux module."""


@dataclass(slots=True)
class RefinementModule:
    """Generated refinement aux module."""

    module_name: str  # e.g. "Refinement_System"
    source: str       # the .tla text


_TEMPLATE_HEADER = "---- MODULE Refinement_{parent} ----"
_TEMPLATE_EXTENDS = "EXTENDS {parent}"
_TEMPLATE_FOOTER = "===="


def generate_refinement_module(bundle: ModuleBundle) -> RefinementModule:
    """Produce a Refinement_<Parent>.tla module from a verified bundle.

    Walks every impl with a non-empty `abstraction_map`; for each, emits an
    `Abs_<Name> == INSTANCE <Name>_Abs WITH ...` definition. Conjoins their
    behavior specs into a single `RefinementSpec`.

    Raises RefinementError if zero impls have a non-empty abstraction_map
    (there's nothing to refine), or if an impl declares an abstraction_map
    but the bundle contains no matching `<Name>_Abs` module.
    """

    parent_name = bundle.parent.name
    abs_by_name = {m.name: m for m in bundle.abstractions()}
    refinable_impls: list[ModuleSource] = []
    for impl in bundle.impls():
        if not impl.abstraction_map:
            continue
        if impl.name not in abs_by_name:
            raise RefinementError(
                f"impl {impl.name!r} declares abstraction_map but no "
                f"matching abs module {impl.name}_Abs in bundle"
            )
        refinable_impls.append(impl)

    if not refinable_impls:
        raise RefinementError(
            f"bundle {bundle.slug!r}: no impls with non-empty abstraction_map; "
            "nothing to refine"
        )

    lines: list[str] = [
        _TEMPLATE_HEADER.format(parent=parent_name),
        _TEMPLATE_EXTENDS.format(parent=parent_name),
        "",
    ]

    for impl in refinable_impls:
        lines.extend(_render_instance(impl))
        lines.append("")

    lines.append(_render_refinement_spec(refinable_impls))
    lines.append("")
    lines.append(_TEMPLATE_FOOTER)

    return RefinementModule(
        module_name=f"Refinement_{parent_name}",
        source="\n".join(lines) + "\n",
    )


def _render_instance(impl: ModuleSource) -> list[str]:
    """One `Abs_<Name> == INSTANCE <Name>_Abs WITH ...` block."""

    abs_module = f"{impl.name}_Abs"
    inst_name = f"Abs_{impl.name}"
    assert impl.abstraction_map, (
        f"_render_instance called with empty abstraction_map for {impl.name!r}; "
        "caller must filter before calling"
    )

    with_clauses = [
        f"{abs_var} <- {expr}"
        for abs_var, expr in impl.abstraction_map.items()
    ]
    if len(with_clauses) == 1:
        return [f"{inst_name} == INSTANCE {abs_module} WITH {with_clauses[0]}"]

    head = f"{inst_name} == INSTANCE {abs_module} WITH"
    body = [f"    {clause}," for clause in with_clauses[:-1]]
    body.append(f"    {with_clauses[-1]}")
    return [head] + body


def _render_refinement_spec(impls: list[ModuleSource]) -> str:
    """Conjoin per-impl Abs_<Name>!Spec into a single RefinementSpec line(s)."""

    if len(impls) == 1:
        return f"RefinementSpec == Abs_{impls[0].name}!Spec"

    head = "RefinementSpec == /\\ " + f"Abs_{impls[0].name}!Spec"
    tail = [
        "                  /\\ " + f"Abs_{impl.name}!Spec"
        for impl in impls[1:]
    ]
    return "\n".join([head] + tail)


def write_refinement_module(
    work_dir: Path,
    bundle: ModuleBundle,
) -> Path:
    """Convenience: generate the module, write it under work_dir, return path."""

    refinement = generate_refinement_module(bundle)
    path = work_dir / f"{refinement.module_name}.tla"
    path.write_text(refinement.source, encoding="utf-8")
    return path
