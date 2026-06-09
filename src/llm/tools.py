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
            "<Name>_Abs module to a TLA+ expression. Expressions MUST be in "
            "terms of the parent's own VARIABLES (the bare names declared in "
            "the parent module), NOT the '<Alias>!var' form. TLA+'s M!x "
            "accessor works only for defined operators of M, not for its "
            "variables — SANY/TLC reject '<Alias>!var' references with "
            "'Unknown operator: var'. The parent's "
            "'<Alias> == INSTANCE <Name>_Impl WITH <impl_var> <- <parent_var>' "
            "has already bound impl variables to parent variables, and the "
            "refinement aux module EXTENDS the parent so those parent "
            "variables are in scope. Example: given Queue_Abs.queue and a "
            "parent variable 'buffer', write {'queue': 'buffer'}."
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


EMIT_PYTHON_MODULE_FOR_BUNDLE_TOOL: dict[str, Any] = {
    "name": "emit_python_module_for_bundle",
    "description": (
        "Translate one verified TLA+/PlusCal impl module into an executable "
        "Python 3.11+ module using icontract decorators. The module must "
        "define a class with @icontract.invariant decorators (one per "
        "top-level Inv conjunct), public methods for each PlusCal action "
        "decorated with @icontract.require / @icontract.ensure, and each "
        "state-mutating method must end with a call to log_action(...). "
        "Imports are limited to: stdlib, icontract, ._trace."
    ),
    "input_schema": {
        "type": "object",
        "required": ["python_module", "class_name", "entry_function"],
        "properties": {
            "python_module": {
                "type": "string",
                "description": (
                    "Complete .py source. Must `import icontract` and "
                    "`from ._trace import log_action`. May import only "
                    "Python stdlib in addition."
                ),
            },
            "class_name": {
                "type": "string",
                "pattern": "^[A-Z][A-Za-z0-9_]*$",
                "description": (
                    "Name of the public class the parent app will import. "
                    "Typically matches the TLA+ module's conceptual name."
                ),
            },
            "entry_function": {
                "type": "string",
                "description": (
                    "Method on the class that exercises the algorithm, "
                    "e.g. 'enqueue' or 'step'."
                ),
            },
            "assertion_map": {
                "type": "array",
                "description": (
                    "Per-conjunct mapping from a TLA+ Inv clause to the "
                    "Python lambda body inside the corresponding "
                    "@icontract.invariant."
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
            "notes": {"type": "string", "default": ""},
        },
    },
}


EMIT_PYTHON_APP_FOR_BUNDLE_TOOL: dict[str, Any] = {
    "name": "emit_python_app_for_bundle",
    "description": (
        "Emit the parent app module that composes the already-translated "
        "child classes into an executable Python program. Imports the child "
        "classes by relative import (`.<snake>`) and exposes a "
        "`run(steps: int = 50) -> <ParentClass>` entry function. The parent "
        "class itself carries @icontract.invariant decorators reflecting the "
        "parent's composed Inv. State-mutating methods end with "
        "log_action(...)."
    ),
    "input_schema": {
        "type": "object",
        "required": ["python_module", "class_name", "entry_function"],
        "properties": {
            "python_module": {
                "type": "string",
                "description": (
                    "Complete .py source for the parent app. Must use "
                    "relative imports (`from .<snake> import <Class>`) "
                    "for each child."
                ),
            },
            "class_name": {
                "type": "string",
                "pattern": "^[A-Z][A-Za-z0-9_]*$",
                "description": "Name of the composed parent class.",
            },
            "entry_function": {
                "type": "string",
                "description": (
                    "Function name that drives the composed system, "
                    "typically 'run'."
                ),
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
