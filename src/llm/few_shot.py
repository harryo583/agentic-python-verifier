"""Few-shot exemplar pool (Feature #6).

Loads a *frozen, leakage-safe* pool of verified ``ModuleBundle`` exemplars and
renders them into static blocks appended to the synthesis / repair system
prompts. The exemplars are drawn from canonical published TLA+ specs in domains
**disjoint** from the benchmark suite (mutex, ticket lock, …) — public *method*
artifacts, not held-out test data — so they teach the mechanical pattern class
(named-INSTANCE composition, real abstraction maps, valid PlusCal labels)
without leaking benchmark answers. See ``examples_pool/README.md``.

Because the blocks are constant for a run, appending them to the cached system
prompt keeps the prompt-cache hit (their marginal token cost is ~one cache read).

The eval-time disjointness guarantee (``exemplar_slugs ∩ benchmark_slugs == ∅``)
is enforced by ``scripts/run_benchmarks.py`` and ``assert_disjoint``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.models.bundle import ModuleBundle


@dataclass(slots=True)
class Exemplar:
    """One verified exemplar: a reverse-engineered prompt + its verified bundle."""

    slug: str
    prompt: str
    bundle: ModuleBundle


def load_exemplars(pool_dir: Optional[Path]) -> list[Exemplar]:
    """Load every ``<slug>/{prompt.txt,bundle.json}`` exemplar under ``pool_dir``.

    Missing/empty pool dir → empty list (few-shot is then a no-op).
    """

    if pool_dir is None or not pool_dir.exists():
        return []
    out: list[Exemplar] = []
    for slug_dir in sorted(p for p in pool_dir.iterdir() if p.is_dir()):
        prompt_path = slug_dir / "prompt.txt"
        bundle_path = slug_dir / "bundle.json"
        if not (prompt_path.exists() and bundle_path.exists()):
            continue
        bundle = ModuleBundle.model_validate_json(
            bundle_path.read_text(encoding="utf-8")
        )
        out.append(
            Exemplar(
                slug=slug_dir.name,
                prompt=prompt_path.read_text(encoding="utf-8").strip(),
                bundle=bundle,
            )
        )
    return out


def exemplar_slugs(pool_dir: Optional[Path]) -> set[str]:
    """The set of exemplar slugs (used for the disjointness assertion)."""

    return {ex.slug for ex in load_exemplars(pool_dir)}


def assert_disjoint(pool_dir: Optional[Path], benchmark_slugs: set[str]) -> None:
    """Fail loudly if any exemplar slug overlaps the benchmark suite.

    This is the load-bearing eval-integrity guarantee: an exemplar drawn from
    the evaluation set would leak the answer and invalidate the few-shot lift.
    """

    overlap = exemplar_slugs(pool_dir) & benchmark_slugs
    if overlap:
        raise AssertionError(
            "Few-shot exemplar pool overlaps the benchmark suite "
            f"(leakage risk): {sorted(overlap)}. Exemplars must be drawn from "
            "domains disjoint from examples/."
        )


def _render_exemplar(ex: Exemplar) -> str:
    lines = [
        f"## Exemplar: {ex.slug}",
        "Natural-language requirement:",
        f"  {ex.prompt}",
        "",
        f"Verified ModuleBundle (slug `{ex.bundle.slug}`):",
        "",
        f"### Parent module `{ex.bundle.parent.name}` (composes the children):",
        "```tla",
        ex.bundle.parent.tla_source.strip(),
        "```",
    ]
    for module in ex.bundle.modules:
        lines.append(f"### `{module.name}` ({module.role}):")
        if module.role == "impl" and module.abstraction_map:
            amap = ", ".join(
                f"{av} <- {expr}" for av, expr in module.abstraction_map.items()
            )
            lines.append(f"abstraction_map: {amap}")
        lines.append("```tla")
        lines.append(module.tla_source.strip())
        lines.append("```")
    return "\n".join(lines)


_SYNTH_HEADER = (
    "\n\n"
    "# Worked examples (verified bundles from a disjoint exemplar pool)\n"
    "The following are complete, TLC-verified ModuleBundles from domains "
    "UNRELATED to your current task. They are NOT the task — do not copy their "
    "content. Study and mimic their STRUCTURE: a named-INSTANCE parent that "
    "composes each `<Name>_Impl`, a strictly-weaker `<Name>_Abs` per child with "
    "a real (non-identity) abstraction map, and PlusCal that uses only valid "
    "(non-reserved) labels.\n"
)

_REPAIR_HEADER = (
    "\n\n"
    "# Reference: shape of a correct, verified bundle\n"
    "When repairing, converge toward the structure shown in these verified "
    "exemplars (disjoint from your task): named-INSTANCE parent composition, "
    "strictly-weaker abstractions with real maps, valid PlusCal labels.\n"
)


def render_synth_few_shot(exemplars: list[Exemplar]) -> str:
    """Static block appended to ``SYNTH_BUNDLE_SYSTEM`` when few-shot is on."""

    if not exemplars:
        return ""
    return _SYNTH_HEADER + "\n\n".join(_render_exemplar(ex) for ex in exemplars)


def render_repair_few_shot(exemplars: list[Exemplar]) -> str:
    """Static block appended to ``REPAIR_BUNDLE_SYSTEM`` when few-shot is on."""

    if not exemplars:
        return ""
    return _REPAIR_HEADER + "\n\n".join(_render_exemplar(ex) for ex in exemplars)
