"""Anthropic function-calling tool schemas."""

from __future__ import annotations

from typing import Any


_CONSTANTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Finite domains for TLA+ CONSTANTS. Each key is a CONSTANT name; "
        "each value is a list of allowed values (small finite domains keep TLC tractable)."
    ),
    "properties": {
        "values": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": ["string", "integer"]},
                "minItems": 1,
            },
        }
    },
    "required": ["values"],
}


PROPOSE_TOOL: dict[str, Any] = {
    "name": "propose_pluscal_with_invariant",
    "description": (
        "Emit a complete TLA+ module that contains a PlusCal algorithm, an inductive "
        "invariant `Inv`, and a target safety property `Property`. The module body "
        "must include the `(* --algorithm <Name> ... *)` block, plus `Inv == ...` "
        "and `Property == ...` as top-level operators after the (eventual) translation. "
        "Do NOT include the BEGIN TRANSLATION / END TRANSLATION block — pcal.trans "
        "will insert it. The module must define `vars` after translation runs (this "
        "happens automatically via pcal.trans)."
    ),
    "input_schema": {
        "type": "object",
        "required": ["module_name", "slug", "pluscal", "constants"],
        "properties": {
            "module_name": {
                "type": "string",
                "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
                "description": "TLA+ module identifier; matches the file name.",
            },
            "slug": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_]*$",
                "description": "Lower-snake-case slug used for output file names.",
            },
            "pluscal": {
                "type": "string",
                "description": (
                    "Full TLA+ module source: `---- MODULE Name ----`, EXTENDS, "
                    "CONSTANTS, the `(* --algorithm ... *)` block, then `Inv` and "
                    "`Property` operators, ending with `===`."
                ),
            },
            "invariant_name": {"type": "string", "default": "Inv"},
            "property_name": {"type": "string", "default": "Property"},
            "constants": _CONSTANTS_SCHEMA,
            "notes": {"type": "string", "default": ""},
        },
    },
}


REPAIR_TOOL: dict[str, Any] = {
    "name": "repair_after_counterexample",
    "description": (
        "Emit a revised TLA+ module after one of the three proof obligations failed. "
        "Diagnose whether the invariant `Inv` was too weak/strong, the spec is wrong, "
        "or the property is unprovable, and revise accordingly."
    ),
    "input_schema": {
        "type": "object",
        "required": [
            "reasoning",
            "targeted_obligation",
            "module_name",
            "slug",
            "pluscal",
            "constants",
        ],
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Brief diagnosis of why the obligation failed and what changed.",
            },
            "targeted_obligation": {
                "type": "string",
                "enum": ["init", "consec", "property"],
                "description": "Which obligation drove this revision.",
            },
            "module_name": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*$"},
            "slug": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
            "pluscal": {"type": "string"},
            "invariant_name": {"type": "string", "default": "Inv"},
            "property_name": {"type": "string", "default": "Property"},
            "constants": _CONSTANTS_SCHEMA,
            "notes": {"type": "string", "default": ""},
        },
    },
}


REFINE_TOOL: dict[str, Any] = {
    "name": "emit_python_module",
    "description": (
        "Translate a verified TLA+/PlusCal module and its inductive invariant `Inv` "
        "into an executable Python 3.11+ module. Insert runtime `assert` statements "
        "that enforce the conjuncts of `Inv` at the entry and exit of every "
        "state-mutating function."
    ),
    "input_schema": {
        "type": "object",
        "required": ["python_module", "entry_function"],
        "properties": {
            "python_module": {
                "type": "string",
                "description": "Complete .py source. May import only Python stdlib.",
            },
            "entry_function": {
                "type": "string",
                "description": "Name of the primary callable in the module.",
            },
            "assertion_map": {
                "type": "array",
                "description": (
                    "Per-conjunct mapping from a TLA+ Inv clause to its Python check, "
                    "for traceability."
                ),
                "items": {
                    "type": "object",
                    "required": ["tla_clause", "python_check"],
                    "properties": {
                        "tla_clause": {"type": "string"},
                        "python_check": {"type": "string"},
                    },
                },
                "default": [],
            },
        },
    },
}


_MODULE_SOURCE_PROPS: dict[str, Any] = {
    "name": {
        "type": "string",
        "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
        "description": (
            "Conceptual module name from the plan; final file names are "
            "<name>_Abs.tla / <name>_Impl.tla."
        ),
    },
    "role": {
        "type": "string",
        "enum": ["abs", "impl"],
        "description": (
            "'abs' = abstract contract (pure TLA+ Spec / Inv). "
            "'impl' = concrete implementation containing a PlusCal block."
        ),
    },
    "tla_source": {
        "type": "string",
        "description": (
            "Full TLA+ module source: `---- MODULE <Name>_Abs ----` or "
            "`---- MODULE <Name>_Impl ----`. For impls, this must contain a "
            "`(* --algorithm <Name> ... *)` block; pcal.trans will rewrite "
            "the file in place. Do NOT pre-insert `\\* BEGIN TRANSLATION`."
        ),
    },
    "pluscal_source": {
        "type": "string",
        "description": (
            "For impl modules only: same text as `tla_source`. The verifier "
            "uses presence of this field as a flag to call pcal.trans. Leave "
            "unset for abs modules."
        ),
    },
    "constants": _CONSTANTS_SCHEMA,
    "abstraction_map": {
        "type": "object",
        "description": (
            "For impl modules only: maps each variable of the sibling "
            "<Name>_Abs module to a TLA+ expression over this impl's "
            "variables. Used to build the refinement aux module."
        ),
        "additionalProperties": {"type": "string"},
        "default": {},
    },
    "invariant_name": {"type": "string", "default": "Inv"},
    "property_name": {"type": "string", "default": "Property"},
}


_PARENT_SOURCE_PROPS: dict[str, Any] = {
    "name": {
        "type": "string",
        "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
        "description": "Parent module name (matches plan.parent_name).",
    },
    "tla_source": {
        "type": "string",
        "description": (
            "Full TLA+ module source for the parent: `---- MODULE <Name> ----` "
            "that EXTENDS / INSTANCEs each <Child>_Impl and defines composed "
            "Inv and Property. No PlusCal block here — composition lives "
            "purely at the TLA+ layer."
        ),
    },
    "constants": _CONSTANTS_SCHEMA,
    "invariant_name": {"type": "string", "default": "Inv"},
    "property_name": {"type": "string", "default": "Property"},
}


PROPOSE_BUNDLE_TOOL: dict[str, Any] = {
    "name": "propose_module_bundle",
    "description": (
        "Emit a verifiable multi-module ModuleBundle: a parent composition "
        "module plus, for each plan child, an <Name>_Abs (abstract contract) "
        "and <Name>_Impl (PlusCal implementation). Each impl carries an "
        "abstraction_map relating its concrete variables to its sibling Abs "
        "variables (used to build the refinement obligation per Hillel "
        "Wayne's ADT pattern). PlusCal cannot compose — the parent module "
        "INSTANCEs each impl and defines the composed Inv and Property."
    ),
    "input_schema": {
        "type": "object",
        "required": ["slug", "parent", "modules"],
        "properties": {
            "slug": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_]*$",
                "description": "Lower-snake-case slug used for output directories.",
            },
            "parent": {
                "type": "object",
                "required": ["name", "tla_source"],
                "properties": _PARENT_SOURCE_PROPS,
            },
            "modules": {
                "type": "array",
                "minItems": 2,
                "maxItems": 8,
                "description": (
                    "Abs and impl module sources. Typical shape: one Abs + "
                    "one Impl per plan child, so 4-8 entries for a 2-4 child "
                    "plan."
                ),
                "items": {
                    "type": "object",
                    "required": ["name", "role", "tla_source"],
                    "properties": _MODULE_SOURCE_PROPS,
                },
            },
            "notes": {"type": "string", "default": ""},
        },
    },
}


REPAIR_BUNDLE_TOOL: dict[str, Any] = {
    "name": "repair_module_bundle",
    "description": (
        "Emit a revised ModuleBundle after one or more proof obligations "
        "failed (a per-impl Init/Consec/Property, or the refinement "
        "obligation across all impls). Diagnose whether a specific module's "
        "Inv was too weak/strong, its PlusCal is wrong, its abstraction_map "
        "is wrong, or the parent's composed Inv/Property is wrong, and revise "
        "accordingly."
    ),
    "input_schema": {
        "type": "object",
        "required": [
            "reasoning",
            "targeted_failure",
            "slug",
            "parent",
            "modules",
        ],
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Brief diagnosis of which obligation failed and what changed.",
            },
            "targeted_failure": {
                "type": "string",
                "description": (
                    "Free-form pointer at the failure: a module name + "
                    "obligation ('Queue/consec'), or 'refinement', or "
                    "'parent/property'."
                ),
            },
            "slug": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_]*$",
            },
            "parent": {
                "type": "object",
                "required": ["name", "tla_source"],
                "properties": _PARENT_SOURCE_PROPS,
            },
            "modules": {
                "type": "array",
                "minItems": 2,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "required": ["name", "role", "tla_source"],
                    "properties": _MODULE_SOURCE_PROPS,
                },
            },
            "notes": {"type": "string", "default": ""},
        },
    },
}


PROPOSE_DECOMPOSITION_TOOL: dict[str, Any] = {
    "name": "propose_decomposition",
    "description": (
        "Decompose a natural-language requirement into a parent TLA+ module "
        "and up to 4 child modules, each with an AbstractInterface "
        "(state_variables, actions, invariant_sketch). The synthesiser will "
        "later expand each child into matched <Name>_Abs.tla and "
        "<Name>_Impl.tla modules; the parent will INSTANCE the impls. "
        "Bias toward 2-3 modules. Composition cannot live in PlusCal — "
        "it lives at the TLA+ layer, so every module must have a clean "
        "abstract contract."
    ),
    "input_schema": {
        "type": "object",
        "required": ["parent_name", "parent_role", "modules"],
        "properties": {
            "parent_name": {
                "type": "string",
                "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
                "description": "TLA+ module name for the composing parent.",
            },
            "parent_role": {
                "type": "string",
                "description": "What the parent composes / orchestrates.",
            },
            "modules": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "required": ["name", "role", "abstract_iface"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
                        },
                        "role": {"type": "string"},
                        "abstract_iface": {
                            "type": "object",
                            "required": ["state_variables", "actions", "invariant_sketch"],
                            "properties": {
                                "state_variables": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "actions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "invariant_sketch": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "notes": {"type": "string", "default": ""},
        },
    },
}
