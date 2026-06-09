"""Deterministic pre-flight linter (Feature #2).

Catches mechanical errors the repair loop empirically fails to self-correct
from TLC error text alone — chiefly reserved PlusCal label names, which
``pcal.trans`` rejects outright (see ``notes/WEEK3_LIVE_RUN_ISSUES.md``,
Issue 1: the model emitted ``Done:`` on three consecutive iterations despite
receiving the pcal error each time). Running this *before* ``check_bundle``
lets us reject a known-bad bundle without spending a TLC subprocess + repair
round-trip, and hand the model a sharper, dedicated diagnostic instead of a
note buried under each obligation.

The prompt rules in ``SYNTH_BUNDLE_SYSTEM`` already forbid these labels; this
linter is the deterministic backstop for when the model ignores the rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.models.bundle import CompositionalProofBundle, ModuleBundle, ModuleSource
from src.models.proof import ObligationResult, ProofBundle


# pcal.trans reserves these as labels: `Done` (the terminal value of `pc`),
# `Error`, and `Lbl_<N>` (auto-generated for unlabeled steps). Matched at label
# position — start of line, identifier, then `:` but not `:=` (assignment), so
# `x := Done` and `pc \in {"Done"}` (a string in an invariant) don't trip it.
_RESERVED_LABEL_RE = re.compile(r"(?m)^[ \t]*(Done|Error|Lbl_\d+)[ \t]*:(?!=)")


@dataclass(slots=True)
class LintFinding:
    """One mechanical defect found in a module before model checking."""

    module: str
    line: int
    label: str
    message: str


def lint_bundle(bundle: ModuleBundle) -> list[LintFinding]:
    """Return all pre-flight findings across the bundle's impl modules."""

    findings: list[LintFinding] = []
    for impl in bundle.impls():
        source = impl.pluscal_source or impl.tla_source
        findings.extend(_lint_reserved_labels(impl, source))
    return findings


def _lint_reserved_labels(impl: ModuleSource, source: str) -> list[LintFinding]:
    out: list[LintFinding] = []
    for match in _RESERVED_LABEL_RE.finditer(source):
        label = match.group(1)
        line = source.count("\n", 0, match.start()) + 1
        out.append(
            LintFinding(
                module=impl.name,
                line=line,
                label=label,
                message=(
                    f"pcal.trans will reject reserved PlusCal label '{label}:' in "
                    f"{impl.name}_Impl (line {line}). Rename it (e.g. 'Finish:', "
                    f"'Idle:', or 'End_{impl.name}:'); never use 'Done', 'Error', "
                    f"or 'Lbl_<N>' as a label name."
                ),
            )
        )
    return out


def render_preflight_feedback(findings: list[LintFinding]) -> str:
    """A standalone human-readable summary of the findings (for logs/notes)."""

    lines = ["Pre-flight linter rejected the bundle before model checking:"]
    for f in findings:
        lines.append(f"  - {f.message}")
    return "\n".join(lines)


def preflight_proof(
    bundle: ModuleBundle, findings: list[LintFinding]
) -> CompositionalProofBundle:
    """Render lint findings as a failing ``CompositionalProofBundle``.

    This lets a pre-flight rejection flow through the *same* fingerprint /
    stuck-detection / repair machinery as a real TLC failure. Offending impl
    modules get all three obligations marked ``error`` with the lint message as
    the note (the note mentions ``pcal`` so the repair serialiser promotes it to
    its TOOLCHAIN-ERRORS header); clean modules and the refinement pass.
    """

    by_module: dict[str, list[LintFinding]] = {}
    for f in findings:
        by_module.setdefault(f.module, []).append(f)

    per_module: dict[str, ProofBundle] = {}
    for impl in bundle.impls():
        module_findings = by_module.get(impl.name, [])
        if module_findings:
            note = " | ".join(f.message for f in module_findings)
            per_module[impl.name] = ProofBundle(
                init=ObligationResult(obligation="init", status="error", note=note),
                consec=ObligationResult(obligation="consec", status="error", note=note),
                property=ObligationResult(
                    obligation="property", status="error", note=note
                ),
            )
        else:
            per_module[impl.name] = ProofBundle(
                init=ObligationResult(obligation="init", status="passed"),
                consec=ObligationResult(obligation="consec", status="passed"),
                property=ObligationResult(obligation="property", status="passed"),
            )
    return CompositionalProofBundle(
        per_module=per_module,
        refinement=ObligationResult(obligation="refinement", status="passed"),
    )
