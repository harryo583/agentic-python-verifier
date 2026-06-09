"""Trace-conformance gate.

Subprocesses the emitted Python package with a seeded fixed step budget,
captures every ``log_action`` call as JSONL, then for each child class runs
TLC against a per-child ``Trace_<Name>.tla`` (rendered by
``src/formal/trace_renderer.py``) extending the child's ``<Name>_Abs`` spec.

Per the Week-3 plan: per-child only (no parent-level replay), advisory-only
(does not flip the pipeline's ``status``). One subprocess for the whole
package; one TLC invocation per child impl module.
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.config import Settings
from src.formal.tla_runner import TLCError, run_tlc
from src.formal.trace_postcondition import parse_trace_outcome, to_trace_result
from src.formal.trace_renderer import (
    TraceEntry,
    TraceRenderError,
    entries_from_records,
    render_trace_cfg,
    render_trace_module,
)
from src.models.bundle import (
    ModuleBundle,
    ModuleSource,
    PythonModuleSource,
    PythonPackage,
    TraceResult,
)
from src.utils.file_utils import ensure_directory


LOGGER = logging.getLogger(__name__)


_DRIVER_NAME = "_trace_driver.py"
_TRACE_JSONL_NAME = "trace.jsonl"


@dataclass(slots=True)
class TraceGate:
    """Runs the trace-conformance gate against an emitted package."""

    settings: Settings

    def check(
        self,
        package: PythonPackage,
        bundle: ModuleBundle,
        work_dir: Path,
    ) -> dict[str, TraceResult]:
        """Return one TraceResult per impl module in `bundle.impls()`.

        Never raises; every failure mode is bucketed into a TraceResult.
        The dict is keyed by `ModuleSource.name` (matching the keys used by
        `CompositionalProofBundle.per_module`).
        """

        ensure_directory(work_dir)
        impls = bundle.impls()
        impl_classes = self._class_name_per_impl(impls, package)
        parent_class = (
            package.parent_app.class_name if package.parent_app else ""
        )

        if not package.parent_app:
            return self._all_skipped(
                impls, "package has no parent_app to drive"
            )

        # --- Phase 1: subprocess the package, capture trace.jsonl
        jsonl_path = work_dir / _TRACE_JSONL_NAME
        run_outcome = self._run_python(package, work_dir, jsonl_path)
        if run_outcome.status != "ok":
            return self._all_with_status(
                impls,
                status="python_crashed",
                note=run_outcome.note,
            )

        # --- Phase 2: parse JSONL, partition by class prefix
        records = self._read_jsonl(jsonl_path)
        if records is None:
            return self._all_with_status(
                impls,
                status="empty",
                note="trace.jsonl missing or empty after subprocess run",
            )

        # --- Phase 3: per-child TLC run
        results: dict[str, TraceResult] = {}
        for impl in impls:
            class_name = impl_classes.get(impl.name, "")
            if not class_name:
                results[impl.name] = TraceResult(
                    child_name=impl.name,
                    status="skipped",
                    note=(
                        "no matching PythonModuleSource for this impl; "
                        "package was not emitted with a child class"
                    ),
                )
                continue
            if class_name == parent_class:
                results[impl.name] = TraceResult(
                    child_name=impl.name,
                    status="skipped",
                    note="impl shares parent class name; cannot attribute",
                )
                continue

            entries = entries_from_records(records, class_name)
            results[impl.name] = self._check_child(
                impl=impl,
                class_name=class_name,
                entries=entries,
                work_dir=work_dir,
            )

        return results

    # ------------------------------------------------------------------
    # Subprocess
    # ------------------------------------------------------------------

    def _run_python(
        self,
        package: PythonPackage,
        work_dir: Path,
        jsonl_path: Path,
    ) -> "_PythonRunOutcome":
        """Materialise the driver and run it in an isolated subprocess."""

        if not package.slug:
            return _PythonRunOutcome(
                status="error", note="PythonPackage has empty slug"
            )

        driver_path = work_dir / _DRIVER_NAME
        driver_path.write_text(
            _DRIVER_SOURCE.format(slug=package.slug),
            encoding="utf-8",
        )

        # `jsonl_path` must NOT exist before the run; the shim opens with mode
        # "a" so a stale file would silently extend.
        if jsonl_path.exists():
            jsonl_path.unlink()

        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "TRACE_JSONL_PATH": str(jsonl_path),
            "TRACE_SEED": "0",
            "TRACE_STEPS": str(self.settings.trace_steps),
            "TRACE_PKG_PARENT": str(self.settings.python_dir),
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        cmd = [sys.executable, "-X", "faulthandler", str(driver_path)]
        LOGGER.debug(
            "trace-gate subprocess: %s (env=%s)",
            shlex.join(cmd),
            sorted(env.keys()),
        )

        started = time.monotonic()
        try:
            completed = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.settings.trace_timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - started
            return _PythonRunOutcome(
                status="timeout",
                note=(
                    f"subprocess timed out after {elapsed:.1f}s "
                    f"(limit {self.settings.trace_timeout_s}s); "
                    f"partial stderr: {_excerpt(exc.stderr)}"
                ),
            )

        if completed.returncode != 0:
            return _PythonRunOutcome(
                status="error",
                note=(
                    f"subprocess exited with code {completed.returncode}; "
                    f"stderr: {_excerpt(completed.stderr)}"
                ),
            )
        return _PythonRunOutcome(status="ok", note="")

    def _read_jsonl(self, jsonl_path: Path) -> Optional[list[dict[str, Any]]]:
        """Return parsed JSONL records, or None if the file is missing/empty.

        Lines that fail to parse are skipped with a warning rather than
        aborting the whole gate; the renderer enforces per-entry schema.
        """

        if not jsonl_path.exists():
            return None
        records: list[dict[str, Any]] = []
        for line_num, raw in enumerate(
            jsonl_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                LOGGER.warning(
                    "trace JSONL line %d malformed: %s", line_num, exc
                )
                continue
            if isinstance(obj, dict):
                records.append(obj)
        if not records:
            return None
        return records

    # ------------------------------------------------------------------
    # Per-child TLC
    # ------------------------------------------------------------------

    def _check_child(
        self,
        *,
        impl: ModuleSource,
        class_name: str,
        entries: list[TraceEntry],
        work_dir: Path,
    ) -> TraceResult:
        """Render Trace_<Name>.tla + cfg and run TLC; classify the outcome."""

        if not entries:
            return TraceResult(
                child_name=impl.name,
                status="empty",
                trace_length=0,
                note=f"no log_action entries attributed to class {class_name!r}",
            )

        cap = self.settings.trace_max_entries
        truncated = False
        if len(entries) > cap:
            entries = entries[:cap]
            truncated = True

        abs_module_name = f"{impl.name}_Abs"
        abs_source = self._abs_source_for(impl, work_dir)
        if abs_source is None:
            return TraceResult(
                child_name=impl.name,
                status="skipped",
                trace_length=len(entries),
                note=(
                    f"could not locate {abs_module_name}.tla in work_dir "
                    f"parents; trace gate needs it for the EXTENDS"
                ),
            )

        try:
            tla_source = render_trace_module(
                class_name=class_name,
                abs_module_name=abs_module_name,
                abs_source=abs_source,
                entries=entries,
            )
        except TraceRenderError as exc:
            return TraceResult(
                child_name=impl.name,
                status="tlc_error",
                trace_length=len(entries),
                note=f"render failed: {exc}",
            )

        # Per-child work subdir keeps each TLC run's cwd uncluttered.
        child_dir = work_dir / class_name
        ensure_directory(child_dir)
        # The trace module EXTENDS <Name>_Abs, so the abs file must sit
        # next to it for SANY to resolve.
        (child_dir / f"{abs_module_name}.tla").write_text(
            abs_source, encoding="utf-8"
        )
        tla_path = child_dir / f"Trace_{class_name}.tla"
        cfg_path = child_dir / f"Trace_{class_name}.cfg"
        tla_path.write_text(tla_source, encoding="utf-8")
        cfg_path.write_text(render_trace_cfg(impl.constants), encoding="utf-8")

        jar = self.settings.tla2tools_jar
        if jar is None:
            return TraceResult(
                child_name=impl.name,
                status="skipped",
                trace_length=len(entries),
                note="TLA2TOOLS_JAR not configured; cannot run TLC",
            )
        try:
            run = run_tlc(
                tla_path,
                cfg_path,
                jar,
                child_dir,
                self.settings.trace_timeout_s,
            )
        except TLCError as exc:
            return TraceResult(
                child_name=impl.name,
                status="tlc_error",
                trace_length=len(entries),
                note=f"TLC could not be invoked: {exc}",
            )

        outcome = parse_trace_outcome(run, expected_len=len(entries))
        result = to_trace_result(
            outcome,
            child_name=impl.name,
            trace_length=len(entries),
        )
        if truncated:
            suffix = (
                f" (trace truncated at trace_max_entries="
                f"{self.settings.trace_max_entries})"
            )
            result = result.model_copy(update={"note": result.note + suffix})
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _class_name_per_impl(
        impls: list[ModuleSource], package: PythonPackage
    ) -> dict[str, str]:
        """Map impl.name -> PythonModuleSource.class_name by `name` equality.

        Both sides use the same `name` field (the conceptual module name);
        the package may have fewer Python modules than impls if refinement
        was partial — those impls map to empty string.
        """

        out: dict[str, str] = {}
        by_name: dict[str, PythonModuleSource] = {
            m.name: m for m in package.modules
        }
        for impl in impls:
            mod = by_name.get(impl.name)
            out[impl.name] = mod.class_name if mod else ""
        return out

    def _abs_source_for(
        self, impl: ModuleSource, work_dir: Path
    ) -> Optional[str]:
        """Find ``<impl.name>_Abs.tla`` in the verifier's work tree.

        Searches `work_dir`, then `settings.work_dir/<slug>_iter*`, then
        `settings.tla_dir`. The compositional pipeline writes the abs file
        to all three at various points.
        """

        candidates: list[Path] = []
        filename = f"{impl.name}_Abs.tla"

        # 1. work_dir itself (rare; trace work dir is usually nested under iter)
        candidates.append(work_dir / filename)
        # 2. work_dir.parent (which IS the iter dir if the pipeline wired it)
        candidates.append(work_dir.parent / filename)
        # 3. Settings work dir, scanning every iter sibling.
        for sibling in self.settings.work_dir.glob("*/" + filename):
            candidates.append(sibling)
        # 4. Final tla_dir (post-pipeline write).
        for tla_sibling in self.settings.tla_dir.glob("*/" + filename):
            candidates.append(tla_sibling)

        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def _all_with_status(
        impls: list[ModuleSource], *, status: str, note: str
    ) -> dict[str, TraceResult]:
        return {
            impl.name: TraceResult(
                child_name=impl.name,
                status=status,  # type: ignore[arg-type]
                note=note,
            )
            for impl in impls
        }

    @staticmethod
    def _all_skipped(
        impls: list[ModuleSource], note: str
    ) -> dict[str, TraceResult]:
        return TraceGate._all_with_status(impls, status="skipped", note=note)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _PythonRunOutcome:
    status: str  # "ok" | "timeout" | "error"
    note: str


def _excerpt(text: Any, *, limit: int = 4096) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = str(text)
    if len(text) > limit:
        return text[:limit] + f"... [{len(text) - limit} more chars]"
    return text


# The driver runs in a stripped-down subprocess. Its only job: seed random,
# put the package's parent directory on sys.path, and call `app.run`. The
# shim picks up TRACE_JSONL_PATH from the env we set above.
_DRIVER_SOURCE = """\
import os
import random
import sys

random.seed(int(os.environ.get("TRACE_SEED", "0")))
sys.path.insert(0, os.environ["TRACE_PKG_PARENT"])

from {slug}.app import run

run(steps=int(os.environ.get("TRACE_STEPS", "50")))
"""
