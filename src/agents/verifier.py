"""Three-obligation TLC verifier.

Pure proof-checking layer: takes a SynthesisProposal and returns a
ProofBundle. No LLM interaction, no mock fallback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.config import Settings
from src.formal.counterexample_parser import parse_tlc_output
from src.formal.pcal_translator import translate_pluscal
from src.formal.tla_runner import TLCError, run_tlc
from src.formal.tlc_config import (
    write_consec_cfg,
    write_consec_module,
    write_init_cfg,
    write_property_cfg,
    write_property_module,
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

        try:
            init_result = self._check_one(main_tla, init_cfg, jar, work_dir, timeout, "init")
            consec_result = self._check_one(consec_tla, consec_cfg, jar, work_dir, timeout, "consec")
            property_result = self._check_one(prop_tla, prop_cfg, jar, work_dir, timeout, "property")
        except TLCError as exc:
            err = str(exc)
            LOGGER.warning("TLC invocation failed: %s", err)
            return _all_error(err, kind="tlc")

        return ProofBundle(
            init=init_result,
            consec=consec_result,
            property=property_result,
        )

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
