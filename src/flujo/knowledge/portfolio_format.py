"""Declared plant for a portfolio document.

A format is the object that lets MAK act without asking: it declares the goal,
so "done" is checkable; it declares what evidence each slot accepts, so
sufficiency stops being absolute; and it makes feasibility answerable *before
producing* rather than after.

A format is data.  Specs live in ``data/portfolio_formats/*.json`` and are never
expressed in code, because a format that mentions a case name has hard-coded
that case.  This module only loads and falsifies them.

It reads no archive, opens no database, calls no provider and produces no
document.  ``portfolio_render`` consumes what this module accepts.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .product_view import stable_json


SCHEMA = "mak-portfolio-format-v1"
ALGORITHM_VERSION = "portfolio-format-1"

# The five claims a portfolio can make.  Field-independent: a barber, a
# photographer and a researcher make exactly the same five.
CLAIMS = ("puedo", "hice_esta_parte", "ocurrio", "significa", "es_mio")

# A state is the result of a named test, never self-assigned confidence.
# Ordered weakest to strongest; a slot declares the minimum it accepts.
STATES = ("observed", "candidate", "supported_candidate", "externally_attested", "certified")
STATE_RANK = {name: index for index, name in enumerate(STATES)}

# Presentation permission: independent of authorship and of evidence, and the
# only layer where being wrong harms a third party.
PERMISSIONS = ("prohibited", "aggregate_only", "unnamed", "public")
PERMISSION_RANK = {name: index for index, name in enumerate(PERMISSIONS)}

# The eight layers.  A claim belongs to exactly one and is never promoted across.
LAYERS = (
    "physical", "content", "process", "work",
    "context", "role", "presentation", "curatorial",
)

# Verticals declare how value is demonstrated; they are never unified.
VERTICAL_GRAMMARS = (
    "transformacion", "practica_o_corpus", "experiencia",
    "resolucion", "ecosistema", "investigacion",
)

# Ceilings that no format may raise.  The archive cannot prove these alone: only
# a named third-party receipt can.
CLAIM_STATE_CEILING = {
    "es_mio": "candidate",
    "hice_esta_parte": "candidate",
}

_TOP_LEVEL = {
    "schema", "format_id", "family", "vertical_grammar", "title", "purpose",
    "consumer", "language", "limits", "declared_claims", "forbidden_claims",
    "forbidden_inferences", "slots", "invalid_if", "control",
}
_SLOT_FIELDS = {
    "slot_id", "title", "count", "claim", "layer", "min_state",
    "min_permission", "caption_grammar", "allowed_caption_fields", "required",
    "evidence_kinds", "prefer_scope", "require_fields",
}
# Optional per-slot preference: which claim scope reads best in this slot.
# "archive" prefers a whole-archive total over one container's share.
SCOPE_PREFERENCES = ("archive", "container", "screen_setup", "any")
_CONSUMER_FIELDS = {
    "kind", "examples", "decision_it_supports", "does_not_support",
}
_CONTROL_EXPECTED = {
    "publication": False,
    "submission": False,
    "signed_document": False,
    "authorship_claimed": False,
    "training_permitted": False,
}


class PortfolioFormatError(ValueError):
    """The declared plant cannot be trusted to bound a document."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PortfolioFormatError(f"{field}_must_be_nonempty_string")
    return value.strip()


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PortfolioFormatError(f"{field}_must_be_object")
    return value


def _string_list(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise PortfolioFormatError(f"{field}_must_be_array")
    rows = [_text(item, f"{field}.item") for item in value]
    if not rows and not allow_empty:
        raise PortfolioFormatError(f"{field}_must_not_be_empty")
    if len(rows) != len(set(rows)):
        raise PortfolioFormatError(f"{field}_must_be_unique")
    return rows


def _caption_fields(grammar: str, allowed: Sequence[str], slot_id: str) -> list[str]:
    """Extract ``{field}`` placeholders and refuse any outside the allow-list.

    The caption is where uncertainty is paid.  A grammar that can reach an
    undeclared field can silently frame the work, which is the failure the
    title/caption layer exists to prevent.
    """
    used: list[str] = []
    depth = 0
    current = ""
    for char in grammar:
        if char == "{":
            depth += 1
            if depth > 1:
                raise PortfolioFormatError(f"slot_{slot_id}_caption_grammar_nested_brace")
            current = ""
        elif char == "}":
            if depth != 1:
                raise PortfolioFormatError(f"slot_{slot_id}_caption_grammar_unbalanced")
            depth -= 1
            name = current.strip()
            if not name:
                raise PortfolioFormatError(f"slot_{slot_id}_caption_grammar_empty_field")
            used.append(name)
        elif depth == 1:
            current += char
    if depth != 0:
        raise PortfolioFormatError(f"slot_{slot_id}_caption_grammar_unbalanced")
    if not used:
        raise PortfolioFormatError(f"slot_{slot_id}_caption_grammar_has_no_field")
    unknown = sorted(set(used) - set(allowed))
    if unknown:
        raise PortfolioFormatError(
            f"slot_{slot_id}_caption_grammar_uses_undeclared_field:{','.join(unknown)}")
    return sorted(set(used))


def _slot(raw: Any, index: int) -> dict[str, Any]:
    slot = _mapping(raw, f"slots[{index}]")
    unknown = sorted(set(slot) - _SLOT_FIELDS)
    if unknown:
        raise PortfolioFormatError(f"slots[{index}]_unknown_fields:{','.join(unknown)}")
    missing = sorted(_SLOT_FIELDS - set(slot) - {"prefer_scope", "require_fields"})
    if missing:
        raise PortfolioFormatError(f"slots[{index}]_missing_fields:{','.join(missing)}")

    slot_id = _text(slot.get("slot_id"), f"slots[{index}].slot_id")
    claim = _text(slot.get("claim"), f"slot_{slot_id}.claim")
    if claim not in CLAIMS:
        raise PortfolioFormatError(f"slot_{slot_id}_claim_invalid:{claim}")
    layer = _text(slot.get("layer"), f"slot_{slot_id}.layer")
    if layer not in LAYERS:
        raise PortfolioFormatError(f"slot_{slot_id}_layer_invalid:{layer}")
    min_state = _text(slot.get("min_state"), f"slot_{slot_id}.min_state")
    if min_state not in STATE_RANK:
        raise PortfolioFormatError(f"slot_{slot_id}_min_state_invalid:{min_state}")
    ceiling = CLAIM_STATE_CEILING.get(claim)
    if ceiling is not None and STATE_RANK[min_state] > STATE_RANK[ceiling]:
        # A format may not demand from the archive what only a third party can give.
        raise PortfolioFormatError(
            f"slot_{slot_id}_min_state_above_claim_ceiling:{claim}>{ceiling}")
    min_permission = _text(slot.get("min_permission"), f"slot_{slot_id}.min_permission")
    if min_permission not in PERMISSION_RANK:
        raise PortfolioFormatError(f"slot_{slot_id}_min_permission_invalid:{min_permission}")
    if min_permission == "prohibited":
        raise PortfolioFormatError(f"slot_{slot_id}_min_permission_cannot_be_prohibited")

    count = _mapping(slot.get("count"), f"slot_{slot_id}.count")
    if set(count) != {"min", "max"}:
        raise PortfolioFormatError(f"slot_{slot_id}_count_fields_invalid")
    minimum, maximum = count.get("min"), count.get("max")
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        raise PortfolioFormatError(f"slot_{slot_id}_count_not_integer")
    if minimum < 0 or maximum < 1 or minimum > maximum:
        raise PortfolioFormatError(f"slot_{slot_id}_count_bounds_invalid")
    required = slot.get("required")
    if not isinstance(required, bool):
        raise PortfolioFormatError(f"slot_{slot_id}_required_not_boolean")
    if required and minimum < 1:
        raise PortfolioFormatError(f"slot_{slot_id}_required_with_zero_minimum")

    allowed = _string_list(slot.get("allowed_caption_fields"),
                           f"slot_{slot_id}.allowed_caption_fields")
    grammar = _text(slot.get("caption_grammar"), f"slot_{slot_id}.caption_grammar")
    used = _caption_fields(grammar, allowed, slot_id)
    evidence_kinds = _string_list(slot.get("evidence_kinds"),
                                  f"slot_{slot_id}.evidence_kinds")
    prefer_scope = str(slot.get("prefer_scope") or "any")
    if prefer_scope not in SCOPE_PREFERENCES:
        raise PortfolioFormatError(f"slot_{slot_id}_prefer_scope_invalid:{prefer_scope}")
    # Optional value filter on caption fields.  Verb, layer and state are not
    # always enough to tell two slots apart: two slots may both take the same
    # verb and differ only by what the claim asserts.
    raw_require = slot.get("require_fields") or {}
    if not isinstance(raw_require, Mapping):
        raise PortfolioFormatError(f"slot_{slot_id}_require_fields_must_be_object")
    require_fields: dict[str, list[str]] = {}
    for key, values in raw_require.items():
        name = _text(key, f"slot_{slot_id}.require_fields.key")
        if name not in allowed:
            raise PortfolioFormatError(
                f"slot_{slot_id}_require_fields_undeclared:{name}")
        require_fields[name] = _string_list(
            values, f"slot_{slot_id}.require_fields.{name}")
    return {
        "slot_id": slot_id,
        "title": _text(slot.get("title"), f"slot_{slot_id}.title"),
        "count": {"min": minimum, "max": maximum},
        "claim": claim,
        "layer": layer,
        "min_state": min_state,
        "min_permission": min_permission,
        "caption_grammar": grammar,
        "allowed_caption_fields": sorted(allowed),
        "caption_fields_used": used,
        "required": required,
        "evidence_kinds": sorted(evidence_kinds),
        "prefer_scope": prefer_scope,
        "require_fields": {key: sorted(value) for key, value in sorted(require_fields.items())},
    }


def validate_portfolio_format(payload: Any) -> dict[str, Any]:
    """Falsify a declared plant and return its normalized, hashed form."""
    spec = _mapping(payload, "format")
    if spec.get("schema") != SCHEMA:
        raise PortfolioFormatError("schema_invalid")
    unknown = sorted(set(spec) - _TOP_LEVEL)
    if unknown:
        raise PortfolioFormatError(f"unknown_fields:{','.join(unknown)}")
    missing = sorted(_TOP_LEVEL - set(spec))
    if missing:
        raise PortfolioFormatError(f"missing_fields:{','.join(missing)}")

    format_id = _text(spec.get("format_id"), "format_id")
    vertical = _text(spec.get("vertical_grammar"), "vertical_grammar")
    if vertical not in VERTICAL_GRAMMARS:
        raise PortfolioFormatError(f"vertical_grammar_invalid:{vertical}")

    consumer = _mapping(spec.get("consumer"), "consumer")
    if set(consumer) != _CONSUMER_FIELDS:
        raise PortfolioFormatError("consumer_fields_invalid")
    _text(consumer.get("kind"), "consumer.kind")
    _text(consumer.get("decision_it_supports"), "consumer.decision_it_supports")
    _string_list(consumer.get("examples"), "consumer.examples")
    # A format must say what it cannot carry, or it will be reused for that.
    _string_list(consumer.get("does_not_support"), "consumer.does_not_support")

    limits = _mapping(spec.get("limits"), "limits")
    if set(limits) != {"max_items_total", "max_bytes", "max_slots_rendered"}:
        raise PortfolioFormatError("limits_fields_invalid")
    for key, value in limits.items():
        if not isinstance(value, int) or value < 1:
            raise PortfolioFormatError(f"limits.{key}_invalid")

    declared = _string_list(spec.get("declared_claims"), "declared_claims")
    forbidden = _string_list(spec.get("forbidden_claims"), "forbidden_claims",
                             allow_empty=True)
    for name in declared + forbidden:
        if name not in CLAIMS:
            raise PortfolioFormatError(f"claim_invalid:{name}")
    overlap = sorted(set(declared) & set(forbidden))
    if overlap:
        raise PortfolioFormatError(f"claim_declared_and_forbidden:{','.join(overlap)}")

    inferences = _string_list(spec.get("forbidden_inferences"), "forbidden_inferences")
    invalid_if = _string_list(spec.get("invalid_if"), "invalid_if")

    raw_slots = spec.get("slots")
    if not isinstance(raw_slots, Sequence) or isinstance(raw_slots, (str, bytes)):
        raise PortfolioFormatError("slots_must_be_array")
    if not raw_slots:
        raise PortfolioFormatError("slots_must_not_be_empty")
    slots = [_slot(row, index) for index, row in enumerate(raw_slots)]
    slot_ids = [row["slot_id"] for row in slots]
    if len(slot_ids) != len(set(slot_ids)):
        raise PortfolioFormatError("slot_ids_not_unique")
    if len(slots) > limits["max_slots_rendered"]:
        raise PortfolioFormatError("slots_exceed_max_slots_rendered")
    if sum(row["count"]["min"] for row in slots) > limits["max_items_total"]:
        raise PortfolioFormatError("slot_minimums_exceed_max_items_total")

    used_claims = {row["claim"] for row in slots}
    undeclared = sorted(used_claims - set(declared))
    if undeclared:
        raise PortfolioFormatError(f"slot_claim_not_declared:{','.join(undeclared)}")
    used_forbidden = sorted(used_claims & set(forbidden))
    if used_forbidden:
        raise PortfolioFormatError(f"slot_claim_forbidden:{','.join(used_forbidden)}")
    if not any(row["required"] for row in slots):
        raise PortfolioFormatError("format_has_no_required_slot")

    control = _mapping(spec.get("control"), "control")
    if dict(control) != _CONTROL_EXPECTED:
        raise PortfolioFormatError("control_invalid")

    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "format_id": format_id,
        "family": _text(spec.get("family"), "family"),
        "vertical_grammar": vertical,
        "title": _text(spec.get("title"), "title"),
        "purpose": _text(spec.get("purpose"), "purpose"),
        "language": _text(spec.get("language"), "language"),
        "consumer": {
            "kind": consumer["kind"],
            "examples": sorted(_string_list(consumer.get("examples"), "consumer.examples")),
            "decision_it_supports": consumer["decision_it_supports"],
            "does_not_support": sorted(
                _string_list(consumer.get("does_not_support"), "consumer.does_not_support")),
        },
        "limits": dict(sorted(limits.items())),
        "declared_claims": sorted(declared),
        "forbidden_claims": sorted(forbidden),
        "forbidden_inferences": sorted(inferences),
        "slots": slots,
        "invalid_if": sorted(invalid_if),
        "control": dict(_CONTROL_EXPECTED),
    }
    result["format_hash"] = "sha256:" + hashlib.sha256(
        stable_json(result).encode("utf-8")).hexdigest()
    return result


def load_portfolio_format(path: str | Path) -> dict[str, Any]:
    """Load one declared plant from disk, read-only."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise PortfolioFormatError(f"format_source_missing:{source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioFormatError(f"format_source_invalid:{source}") from exc
    spec = validate_portfolio_format(payload)
    spec["source_ref"] = str(source)
    spec["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    return spec


def load_format_library(directory: str | Path) -> dict[str, Any]:
    """Load every declared plant in a directory, deterministically ordered."""
    root = Path(directory).expanduser()
    if not root.is_dir():
        raise PortfolioFormatError(f"format_library_missing:{root}")
    formats = [load_portfolio_format(path) for path in sorted(root.glob("*.json"))]
    if not formats:
        raise PortfolioFormatError(f"format_library_empty:{root}")
    ids = [row["format_id"] for row in formats]
    if len(ids) != len(set(ids)):
        raise PortfolioFormatError("format_library_ids_not_unique")
    return {
        "schema": "mak-portfolio-format-library-v1",
        "algorithm_version": ALGORITHM_VERSION,
        "source_ref": str(root),
        "format_count": len(formats),
        "format_ids": sorted(ids),
        "verticals": sorted({row["vertical_grammar"] for row in formats}),
        "families": sorted({row["family"] for row in formats}),
        "formats": sorted(formats, key=lambda row: row["format_id"]),
    }


def accepts(slot: Mapping[str, Any], *, state: str, permission: str) -> bool:
    """Whether one slot admits a claim at this state and permission."""
    if state not in STATE_RANK or permission not in PERMISSION_RANK:
        return False
    return (
        STATE_RANK[state] >= STATE_RANK[str(slot["min_state"])]
        and PERMISSION_RANK[permission] >= PERMISSION_RANK[str(slot["min_permission"])]
    )


__all__ = [
    "ALGORITHM_VERSION", "CLAIMS", "CLAIM_STATE_CEILING", "LAYERS",
    "PERMISSIONS", "PERMISSION_RANK", "PortfolioFormatError", "SCHEMA",
    "SCOPE_PREFERENCES", "STATES", "STATE_RANK", "VERTICAL_GRAMMARS", "accepts",
    "load_format_library", "load_portfolio_format", "validate_portfolio_format",
]
