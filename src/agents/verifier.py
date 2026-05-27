"""Three-obligation TLC verifier (plus the 4th refinement obligation for bundles).

Pure proof-checking layer: takes a SynthesisProposal (single-module) or a
ModuleBundle (compositional) and returns the corresponding proof results.
No LLM interaction, no mock fallback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.config import Settings
from src.formal.counterexample_parser import parse_tlc_output
from src.formal.pcal_translator import translate_pluscal
from src.formal.refinement import RefinementError, write_refinement_module
from src.formal.tla_runner import run_tlc
from src.formal.tlc_config import (
    write_consec_cfg,
    write_consec_module,
    write_init_cfg,
    write_property_cfg,
    write_property_module,
)
from src.models.bundle import (
    CompositionalProofBundle,
    ModuleBundle,
    ModuleSource,
)
from src.models.proof import ObligationResult, ProofBundle
from src.models.synthesis import SynthesisProposal
from src.utils.file_utils import ensure_directory


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class Verifier:
    """Runs the three TLC obligations against a SynthesisProposal."""

    settings: Settings

    def check(self, proposal: SynthesisProposal, work_dir: Path) -> ProofBundle:
        """Translate PlusCal, write configs, run all three obligations."""

        ensure_directory(work_dir)
        jar = self.settings.tla2tools_jar
        assert jar is not None  # require_runtime_settings was called upstream
        timeout = self.settings.tlc_timeout_s

        module = proposal.module_name
        main_tla = work_dir / f"{module}.tla"
        main_tla.write_text(proposal.pluscal, encoding="utf-8")

        try:
            translate_pluscal(main_tla, jar)
        except Exception as exc:  # pcal failure surfaces as init+consec+property error
            err = str(exc)
            LOGGER.warning("pcal.trans failed: %s", err)
            return _all_error(err, kind="pcal")

        # Auxiliary modules and config files
        write_consec_module(work_dir, module, proposal.invariant_name)
        write_property_module(work_dir, module, proposal.invariant_name)

        init_cfg = work_dir / "init.cfg"
        consec_cfg = work_dir / "consec.cfg"
        prop_cfg = work_dir / "property.cfg"
        write_init_cfg(init_cfg, proposal.invariant_name, proposal.constants)
        write_consec_cfg(consec_cfg, proposal.invariant_name, proposal.constants)
        write_property_cfg(prop_cfg, proposal.property_name, proposal.constants)

        consec_tla = work_dir / f"Consec_{module}.tla"
        prop_tla = work_dir / f"Prop_{module}.tla"

        init_result = self._check_one(main_tla, init_cfg, jar, work_dir, timeout, "init")
        consec_result = self._check_one(consec_tla, consec_cfg, jar, work_dir, timeout, "consec")
        property_result = self._check_one(prop_tla, prop_cfg, jar, work_dir, timeout, "property")

        return ProofBundle(
            init=init_result,
            consec=consec_result,
            property=property_result,
        )

    def check_bundle(
        self, bundle: ModuleBundle, work_dir: Path
    ) -> CompositionalProofBundle:
        """Verify a multi-module ModuleBundle.

        For each impl, runs the same three obligations (Init / Consec /
        Property) as the single-module flow. Then writes a
        ``Refinement_<Parent>.tla`` aux module per Hillel Wayne's ADT pattern
        and runs TLC on it as the 4th obligation, checking that every impl
        refines its corresponding ``<Name>_Abs`` module via the
        ``abstraction_map``.
        """

        ensure_directory(work_dir)
        jar = self.settings.tla2tools_jar
        assert jar is not None  # require_runtime_settings was called upstream
        timeout = self.settings.tlc_timeout_s

        self._write_bundle_files(bundle, work_dir)

        per_module: dict[str, ProofBundle] = {}
        for impl in bundle.impls():
            per_module[impl.name] = self._verify_impl(impl, work_dir, jar, timeout)

        refinement = self._verify_refinement(bundle, work_dir, jar, timeout)

        return CompositionalProofBundle(
            per_module=per_module,
            refinement=refinement,
        )

    @staticmethod
    def _write_bundle_files(bundle: ModuleBundle, work_dir: Path) -> None:
        """Drop parent + every module file to work_dir so EXTENDS/INSTANCE resolves.

        pcal.trans gets called later, only against impl files; abs and parent
        files are written verbatim and stay pure TLA+.
        """

        (work_dir / bundle.parent.filename).write_text(
            bundle.parent.tla_source, encoding="utf-8"
        )
        for m in bundle.modules:
            (work_dir / m.filename).write_text(m.tla_source, encoding="utf-8")

    def _verify_impl(
        self, impl: ModuleSource, work_dir: Path, jar: str, timeout: int
    ) -> ProofBundle:
        """Run the standard 3-obligation flow against one impl module."""

        module_filename = impl.filename  # e.g. "Queue_Impl.tla"
        module = module_filename[:-4]  # strip ".tla"
        main_tla = work_dir / module_filename

        if impl.pluscal_source is not None:
            try:
                translate_pluscal(main_tla, jar)
            except Exception as exc:
                err = str(exc)
                LOGGER.warning("pcal.trans failed for %s: %s", impl.name, err)
                return _all_error(err, kind="pcal")

        write_consec_module(work_dir, module, impl.invariant_name)
        write_property_module(work_dir, module, impl.invariant_name)

        init_cfg = work_dir / f"{module}_init.cfg"
        consec_cfg = work_dir / f"{module}_consec.cfg"
        prop_cfg = work_dir / f"{module}_property.cfg"
        write_init_cfg(init_cfg, impl.invariant_name, impl.constants)
        write_consec_cfg(consec_cfg, impl.invariant_name, impl.constants)
        write_property_cfg(prop_cfg, impl.property_name, impl.constants)

        consec_tla = work_dir / f"Consec_{module}.tla"
        prop_tla = work_dir / f"Prop_{module}.tla"

        init_r = self._check_one(main_tla, init_cfg, jar, work_dir, timeout, "init")
        consec_r = self._check_one(consec_tla, consec_cfg, jar, work_dir, timeout, "consec")
        property_r = self._check_one(prop_tla, prop_cfg, jar, work_dir, timeout, "property")

        return ProofBundle(init=init_r, consec=consec_r, property=property_r)

    def _verify_refinement(
        self, bundle: ModuleBundle, work_dir: Path, jar: str, timeout: int
    ) -> ObligationResult:
        """Generate Refinement_<Parent>.tla and run TLC on it.

        TLC mode: ``SPECIFICATION Spec`` (the parent's composed behavior) +
        ``PROPERTY RefinementSpec`` (the conjunction of Abs!Spec via the
        abstraction maps). A passing run means every parent behavior is a
        valid trace of every abstract spec — i.e. each impl refines its abs.
        """

        try:
            ref_tla_path = write_refinement_module(work_dir, bundle)
        except RefinementError as exc:
            return ObligationResult(
                obligation="refinement",
                status="error",
                note=f"refinement aux module generation failed: {exc}",
            )

        ref_cfg = work_dir / "refinement.cfg"
        _write_refinement_cfg(ref_cfg, bundle)

        run = run_tlc(ref_tla_path, ref_cfg, jar, work_dir, timeout)
        return parse_tlc_output(run, "refinement")

    def _check_one(
        self,
        tla_path: Path,
        cfg_path: Path,
        jar: str,
        work_dir: Path,
        timeout: int,
        obligation: str,
    ) -> ObligationResult:
        run = run_tlc(tla_path, cfg_path, jar, work_dir, timeout)
        return parse_tlc_output(run, obligation)  # type: ignore[arg-type]


def _write_refinement_cfg(cfg_path: Path, bundle: ModuleBundle) -> None:
    """Write the refinement-check TLC cfg.

    SPECIFICATION = ``Spec`` (the parent's behavior, in scope via EXTENDS).
    PROPERTY      = ``RefinementSpec`` (the conjunction of ``Abs_<Name>!Spec``).
    CONSTANTS     = the parent module's declared CONSTANTS.
    """

    parts = ["SPECIFICATION Spec", "PROPERTY RefinementSpec"]
    parts.extend(bundle.parent.constants.to_cfg_lines())
    cfg_path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _all_error(message: str, *, kind: str) -> ProofBundle:
    template = ObligationResult(
        obligation="init",
        status="error",
        note=f"{kind} stage failed: {message}",
    )
    return ProofBundle(
        init=template.model_copy(update={"obligation": "init"}),
        consec=template.model_copy(update={"obligation": "consec"}),
        property=template.model_copy(update={"obligation": "property"}),
    )
