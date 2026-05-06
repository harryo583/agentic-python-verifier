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
