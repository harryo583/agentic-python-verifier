"""Synthesiser-output models: a verifiable multi-module bundle and its proof results."""

from __future__ import annotations
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.proof import ObligationResult, ProofBundle
from src.models.synthesis import Constants

_MODULE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

ModuleRole = Literal["abs", "impl", "parent"]


class ModuleSource(BaseModel):
    """One TLA+ module emitted by the synthesiser.

    For impls, `pluscal_source` carries the un-translated PlusCal text that
    will be fed to pcal.trans; `tla_source` may be the same string if it
    contains a `(* --algorithm ... *)` block (the verifier re-uses the existing
    single-module flow).

    For abs and parent modules, `pluscal_source` is None and `tla_source` is
    pure TLA+ (no PlusCal block).

    `abstraction_map` is only meaningful when role == "impl": it maps each
    variable of the corresponding `<name>_Abs` module to a TLA+ expression
    over this impl's variables. Consumed by `src/formal/refinement.py`.
    """

    name: str = Field(
        ...,
        description=(
            "Conceptual module name (e.g. 'Queue'); the actual file name is "
            "derived as <name>_Abs.tla, <name>_Impl.tla, or <name>.tla for "
            "the parent."
        ),
    )
    role: ModuleRole
    tla_source: str
    pluscal_source: Optional[str] = None
    constants: Constants = Field(default_factory=Constants)
    abstraction_map: dict[str, str] = Field(default_factory=dict)
    invariant_name: str = "Inv"
    property_name: str = "Property"

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not _MODULE_NAME_RE.fullmatch(v):
            raise ValueError("name must match ^[A-Za-z][A-Za-z0-9_]*$")
        return v

    @model_validator(mode="after")
    def _role_constraints(self):
        if self.role == "impl":
            # impls may carry abstraction_map (may be empty for now)
            pass
        else:
            # abs/parent must not carry pluscal or abstraction_map
            if self.pluscal_source is not None:
                raise ValueError(
                    f"role={self.role!r} must not have pluscal_source"
                )
            if self.abstraction_map:
                raise ValueError(
                    f"role={self.role!r} must not have abstraction_map"
                )
        return self

    @property
    def filename(self) -> str:
        """Return the on-disk file name for this module's role."""
        if self.role == "parent":
            return f"{self.name}.tla"
        suffix = "_Abs" if self.role == "abs" else "_Impl"
        return f"{self.name}{suffix}.tla"


class ModuleBundle(BaseModel):
    """A parent composition module plus its constituent abs+impl modules."""

    parent: ModuleSource = Field(..., description="role must be 'parent'.")
    modules: list[ModuleSource] = Field(
        ...,
        min_length=1,
        description="abs and impl module sources; never includes the parent.",
    )
    slug: str = Field(
        ..., description="Lower-snake-case slug for output directories."
    )
    notes: str = ""

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", v):
            raise ValueError("slug must match ^[a-z][a-z0-9_]*$")
        return v

    @model_validator(mode="after")
    def _bundle_constraints(self):
        if self.parent.role != "parent":
            raise ValueError("parent.role must be 'parent'")
        for m in self.modules:
            if m.role == "parent":
                raise ValueError(
                    "modules[] must contain only abs/impl sources, not parent"
                )
        # filename uniqueness
        filenames = [m.filename for m in self.modules] + [self.parent.filename]
        if len(filenames) != len(set(filenames)):
            raise ValueError(f"module filenames must be unique, got {filenames}")
        return self

    def impls(self) -> list[ModuleSource]:
        return [m for m in self.modules if m.role == "impl"]

    def abstractions(self) -> list[ModuleSource]:
        return [m for m in self.modules if m.role == "abs"]


class CompositionalProofBundle(BaseModel):
    """Per-impl 3-obligation results plus a 4th refinement obligation."""

    per_module: dict[str, ProofBundle] = Field(
        default_factory=dict,
        description="Keyed by impl ModuleSource.name.",
    )
    refinement: ObligationResult

    @property
    def all_passed(self) -> bool:
        return self.refinement.passed and all(
            b.all_passed for b in self.per_module.values()
        )

    def failing_modules(self) -> list[str]:
        return [name for name, b in self.per_module.items() if not b.all_passed]


class PythonModuleSource(BaseModel):
    """One Python module emitted by the refinement agent (Week 2 placeholder)."""

    name: str
    source: str
    entry_function: str = ""


class PythonPackage(BaseModel):
    """A package of Python modules + a parent app file (Week 2 placeholder)."""

    modules: list[PythonModuleSource] = Field(default_factory=list)
    parent_app: Optional[PythonModuleSource] = None


class TraceResult(BaseModel):
    """Outcome of the trace-conformance gate (Week 3 placeholder)."""

    conforms: bool
    divergence_step: Optional[int] = None
    note: str = ""
