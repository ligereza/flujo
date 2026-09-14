"""Deterministic semantic diff for versioned opportunity constraints.

This module closes the boundary between a captured opportunity version and its
downstream consumers.  It does not fetch sources, mutate a corpus or rerun a
consumer.  It only identifies which documentary items changed and whether a
downstream recomputation is justified by that change.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import sha256_ref as _hash, stable_json

from .opportunity_constraints import (
    SCHEMA as CONSTRAINTS_SCHEMA,
    OpportunityConstraintsError,
    validate_opportunity_constraints,
)


SCHEMA = "mak-opportunity-delta-v1"
ALGORITHM_VERSION = "opportunity-constraints-semantic-diff-1"

_TOP_LEVEL_FIELDS = {
    "schema",
    "algorithm_version",
    "opportunity_id",
    "previous_input_hash",
    "current_input_hash",
    "source",
    "changes",
    "affected_requirement_ids",
    "impact",
    "reconciliation",
    "provenance",
}
_CHANGE_FIELDS = {
    "change_id",
    "domain",
    "item_id",
    "change_type",
    "changed_fields",
    "previous_hash",
    "current_hash",
    "previous",
    "current",
    "evidence_refs",
}
_CHANGE_TYPES = {"added", "removed", "changed"}
_DOMAINS = {"source", "constraint", "criterion", "unknowns"}
_DOWNSTREAM_CONSUMERS = [
    "opportunity_fit",
    "artistic_program_hypotheses",
    "possibility_field",
    "research_frontier_bridge",
    "product_plan",
    "portfolio_dossier",
    "application_research_package",
    "product_episode",
    "autonomy_plan",
]


class OpportunityDeltaError(ValueError):
    """Raised when a constraints diff cannot be computed fail-closed."""


def _require_payload(payload: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise OpportunityDeltaError(f"{name}_must_be_object")
    try:
        validate_opportunity_constraints(payload)
    except OpportunityConstraintsError as exc:
        raise OpportunityDeltaError(f"{name}_invalid:{exc}") from exc
    return payload


def _rows(payload: Mapping[str, Any], field: str, id_field: str) -> dict[str, Mapping[str, Any]]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        raise OpportunityDeltaError(f"{field}_must_be_list")
    result: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise OpportunityDeltaError(f"{field}[{index}]_must_be_object")
        item_id = row.get(id_field)
        if not isinstance(item_id, str) or not item_id:
            raise OpportunityDeltaError(f"{field}[{index}]_id_invalid")
        if item_id in result:
            raise OpportunityDeltaError(f"{field}_duplicate_id")
        result[item_id] = row
    return result


def _source_view(source: Any) -> Mapping[str, Any]:
    if not isinstance(source, Mapping):
        raise OpportunityDeltaError("source_invalid")
    return source


def _evidence_refs(row: Mapping[str, Any] | None) -> list[str]:
    if isinstance(row, list):
        refs: set[str] = set()
        for item in row:
            refs.update(_evidence_refs(item))
        return sorted(refs)
    if not isinstance(row, Mapping):
        return []
    refs: set[str] = set()
    values = row.get("evidence_refs")
    if isinstance(values, list):
        refs.update(value for value in values if isinstance(value, str) and value)
    return sorted(refs)


def _change(
    *,
    domain: str,
    item_id: str,
    change_type: str,
    previous: Any,
    current: Any,
) -> dict[str, Any]:
    if change_type not in _CHANGE_TYPES:
        raise OpportunityDeltaError("change_type_invalid")
    previous_hash = _hash(previous) if previous is not None else None
    current_hash = _hash(current) if current is not None else None
    if change_type == "changed" and isinstance(previous, Mapping) and isinstance(current, Mapping):
        changed_fields = sorted({str(key) for key in set(previous) | set(current) if previous.get(key) != current.get(key)})
    elif change_type == "added":
        changed_fields = sorted(str(key) for key in current) if isinstance(current, Mapping) else []
    else:
        changed_fields = sorted(str(key) for key in previous) if isinstance(previous, Mapping) else []
    if not changed_fields:
        changed_fields = ["value"]
    evidence_refs = sorted(set(_evidence_refs(previous)) | set(_evidence_refs(current)))
    semantics = {
        "domain": domain,
        "item_id": item_id,
        "change_type": change_type,
        "changed_fields": changed_fields,
        "previous_hash": previous_hash,
        "current_hash": current_hash,
    }
    return {
        "change_id": "delta:" + hashlib.sha256(stable_json(semantics).encode("utf-8")).hexdigest(),
        "domain": domain,
        "item_id": item_id,
        "change_type": change_type,
        "changed_fields": changed_fields,
        "previous_hash": previous_hash,
        "current_hash": current_hash,
        "previous": previous,
        "current": current,
        "evidence_refs": evidence_refs,
    }


def _mapping_changes(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    domain: str,
    id_field: str,
) -> list[dict[str, Any]]:
    previous_rows = _rows(previous, "constraints" if domain == "constraint" else "criteria", id_field)
    current_rows = _rows(current, "constraints" if domain == "constraint" else "criteria", id_field)
    changes: list[dict[str, Any]] = []
    for item_id in sorted(set(previous_rows) | set(current_rows)):
        before = previous_rows.get(item_id)
        after = current_rows.get(item_id)
        if before is None:
            changes.append(_change(domain=domain, item_id=item_id, change_type="added", previous=None, current=after))
        elif after is None:
            changes.append(_change(domain=domain, item_id=item_id, change_type="removed", previous=before, current=None))
        elif before != after:
            changes.append(_change(domain=domain, item_id=item_id, change_type="changed", previous=before, current=after))
    return changes


def _unknowns_change(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[dict[str, Any]]:
    before = previous.get("unknowns", [])
    after = current.get("unknowns", [])
    if before == after:
        return []
    return [_change(domain="unknowns", item_id="unknowns", change_type="changed", previous=before, current=after)]


def _source_change(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[dict[str, Any]]:
    before = _source_view(previous.get("source"))
    after = _source_view(current.get("source"))
    if before == after:
        return []
    return [_change(domain="source", item_id="source", change_type="changed", previous=before, current=after)]


def _impact(changes: list[dict[str, Any]]) -> dict[str, Any]:
    if not changes:
        return {
            "recompute_required": False,
            "selective": True,
            "reason_codes": ["no_semantic_change"],
            "affected_consumers": [],
        }
    reason_codes: set[str] = set()
    affected_requirement_ids: set[str] = set()
    semantic = False
    for row in changes:
        domain = row["domain"]
        if domain == "constraint":
            reason_codes.add("constraint_changed")
            semantic = True
            affected_requirement_ids.add(row["item_id"])
        elif domain == "criterion":
            reason_codes.add("criterion_changed")
            semantic = True
            affected_requirement_ids.add(row["item_id"])
        elif domain == "unknowns":
            reason_codes.add("unknowns_changed")
            semantic = True
        elif domain == "source":
            changed_fields = set(row["changed_fields"])
            if "validity" in changed_fields:
                reason_codes.add("source_validity_changed")
                semantic = True
            else:
                reason_codes.add("source_provenance_changed_only")
    return {
        "recompute_required": semantic,
        "selective": True,
        "reason_codes": sorted(reason_codes),
        "affected_consumers": list(_DOWNSTREAM_CONSUMERS) if semantic else [],
    }


def compare_opportunity_constraints(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    _validate: bool = True,
) -> dict[str, Any]:
    """Compare two validated versions without fetching or recomputing them."""
    previous = _require_payload(previous, "previous")
    current = _require_payload(current, "current")
    if previous.get("schema") != CONSTRAINTS_SCHEMA or current.get("schema") != CONSTRAINTS_SCHEMA:
        raise OpportunityDeltaError("constraints_schema_invalid")
    opportunity_id = previous.get("opportunity_id")
    if opportunity_id != current.get("opportunity_id"):
        raise OpportunityDeltaError("opportunity_id_mismatch")
    changes = []
    changes.extend(_source_change(previous, current))
    changes.extend(_mapping_changes(previous, current, domain="constraint", id_field="constraint_id"))
    changes.extend(_mapping_changes(previous, current, domain="criterion", id_field="criterion_id"))
    changes.extend(_unknowns_change(previous, current))
    changes.sort(key=lambda row: row["change_id"])
    impact = _impact(changes)
    affected_requirement_ids = sorted({
        row["item_id"] for row in changes if row["domain"] in {"constraint", "criterion"}
    })
    previous_source = _source_view(previous.get("source"))
    current_source = _source_view(current.get("source"))
    output = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "opportunity_id": opportunity_id,
        "previous_input_hash": previous.get("input_hash"),
        "current_input_hash": current.get("input_hash"),
        "source": {
            "previous": previous_source,
            "current": current_source,
            "changed": previous_source != current_source,
        },
        "changes": changes,
        "affected_requirement_ids": affected_requirement_ids,
        "impact": {
            **impact,
            "affected_requirement_ids": affected_requirement_ids,
        },
        "reconciliation": {
            "previous_constraint_count": len(previous.get("constraints", [])),
            "current_constraint_count": len(current.get("constraints", [])),
            "previous_criterion_count": len(previous.get("criteria", [])),
            "current_criterion_count": len(current.get("criteria", [])),
            "change_count": len(changes),
            "changed_domains": sorted({row["domain"] for row in changes}),
            "evidence_refs_preserved": True,
            "truth_promotions": 0,
            "deterministic_order": True,
        },
        "provenance": {
            "previous_schema": CONSTRAINTS_SCHEMA,
            "current_schema": CONSTRAINTS_SCHEMA,
            "promotion": "none",
            "training_permitted": False,
            "source_rescan": False,
            "deterministic": True,
        },
    }
    if _validate and not validate_opportunity_delta(previous, current, output):
        raise OpportunityDeltaError("generated_delta_failed_validation")
    return output


def validate_opportunity_delta(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Strictly validate a delta by recomputing its canonical projection."""
    try:
        previous = _require_payload(previous, "previous")
        current = _require_payload(current, "current")
        if not isinstance(payload, Mapping) or set(payload) != _TOP_LEVEL_FIELDS:
            return False
        expected = compare_opportunity_constraints(previous, current, _validate=False)
        return payload == expected
    except (OpportunityDeltaError, OpportunityConstraintsError, TypeError, ValueError):
        return False


def _validate_shape_only(previous: Mapping[str, Any], current: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    """Validate generated fields without recursively rebuilding the payload."""
    if payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION:
        return False
    if previous.get("opportunity_id") != current.get("opportunity_id") != payload.get("opportunity_id"):
        return False
    if payload.get("previous_input_hash") != previous.get("input_hash") or payload.get("current_input_hash") != current.get("input_hash"):
        return False
    changes = payload.get("changes")
    if not isinstance(changes, list) or changes != sorted(changes, key=lambda row: row.get("change_id", "")):
        return False
    ids: set[str] = set()
    for row in changes:
        if not isinstance(row, Mapping) or set(row) != _CHANGE_FIELDS:
            return False
        if row.get("domain") not in _DOMAINS or row.get("change_type") not in _CHANGE_TYPES:
            return False
        change_id = row.get("change_id")
        if not isinstance(change_id, str) or not change_id or change_id in ids:
            return False
        ids.add(change_id)
        if not isinstance(row.get("changed_fields"), list) or row["changed_fields"] != sorted(set(row["changed_fields"])):
            return False
        if not isinstance(row.get("evidence_refs"), list) or row["evidence_refs"] != sorted(set(row["evidence_refs"])):
            return False
    if payload.get("affected_requirement_ids") != sorted(set(payload.get("affected_requirement_ids", []))):
        return False
    impact = payload.get("impact")
    recon = payload.get("reconciliation")
    provenance = payload.get("provenance")
    if not isinstance(impact, Mapping) or not isinstance(recon, Mapping) or not isinstance(provenance, Mapping):
        return False
    if provenance.get("promotion") != "none" or provenance.get("training_permitted") is not False or provenance.get("source_rescan") is not False:
        return False
    if recon.get("change_count") != len(changes) or recon.get("truth_promotions") != 0 or recon.get("deterministic_order") is not True:
        return False
    if impact.get("affected_requirement_ids") != payload.get("affected_requirement_ids"):
        return False
    expected_impact = _impact(changes)
    if dict(impact) != {**expected_impact, "affected_requirement_ids": payload.get("affected_requirement_ids")}:
        return False
    return True


def validate_delta(previous: Mapping[str, Any], current: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    """Compatibility alias for downstream callers."""
    return validate_opportunity_delta(previous, current, payload)
