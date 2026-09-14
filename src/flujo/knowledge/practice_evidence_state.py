"""Pure projection of accepted Project IR evidence into practice state.

This module is deliberately a link, not another archive index or department
registry.  It consumes an accepted Stage 2D Project IR bundle (or portable
``mak-project-ir-v1`` records), copies only explicit evidence-bearing fields,
and keeps every physical reference distinct.  It never reads a source path,
opens a database, calls a provider, or promotes an artistic interpretation.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from ._contract_helpers import sha256_ref as _hash, stable_json as _stable_json

from .project_ir import SCHEMA as PROJECT_IR_SCHEMA, validate_project_ir


SCHEMA = "mak-practice-evidence-state-v1"
BUNDLE_SCHEMA = "mak-archive-project-ir-bundle-v1"
ALGORITHM_VERSION = "practice-evidence-state-1"
DIMENSIONS = ("media", "capabilities", "temporality", "manifestations", "resources")
CLAIM_STATUSES = ("supported", "candidate", "unknown")
TRUTH_STATUSES = {"active", "verified", "promoted", "published", "truth"}
DEPENDENCY_PREDICATES = {
    "depends_on", "depended_on_by", "dependency", "provisional_dependency",
    "shared_resource", "shared_resource_of",
}
MANIFESTATION_PREDICATES = {
    "manifestation_of", "has_manifestation", "published_as",
}
_MISSING = object()


class PracticeEvidenceStateError(ValueError):
    """Raised when the input or a serialized state is not safe to project."""


def _text(value: Any) -> str:
    return str(value).strip() if isinstance(value, (str, int, float)) else ""


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return []
    return sorted({item.strip() for item in value if isinstance(item, str) and item.strip()})


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        return [value]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _copy_json(value: Any) -> Any:
    """Copy and check JSON-like input without changing the caller's object."""
    copied = copy.deepcopy(value)
    try:
        _stable_json(copied)
    except (TypeError, ValueError) as error:
        raise PracticeEvidenceStateError(f"input_not_json:{error}") from error
    return copied


def _identity_values(records: Sequence[Mapping[str, Any]], field: str) -> list[str]:
    values: list[str] = []
    for record in records:
        direct = _text(record.get(field))
        nested = record.get("source") if isinstance(record.get("source"), Mapping) else {}
        provenance = record.get("provenance") if isinstance(record.get("provenance"), Mapping) else {}
        for value in (direct, _text(nested.get(field)), _text(provenance.get(field))):
            if value and value not in values:
                values.append(value)
    return values


def _records_semantic_copy(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Strip path/time-only provenance before hashing standalone records."""
    result = copy.deepcopy(list(records))
    for record in result:
        if not isinstance(record, dict):
            continue
        source = record.get("source")
        if isinstance(source, dict):
            source.pop("root_ref", None)
        provenance = record.get("provenance")
        if isinstance(provenance, dict):
            provenance.pop("created_at", None)
            provenance.pop("updated_at", None)
    return result


def _normalise_source(source: Any) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    copied = _copy_json(source)
    bundle: dict[str, Any]
    if isinstance(copied, Mapping):
        source_schema = _text(copied.get("schema"))
        if source_schema == BUNDLE_SCHEMA:
            if not isinstance(copied.get("records"), list):
                raise PracticeEvidenceStateError("bundle_records_invalid")
            if copied.get("target_project_ir_schema") not in {None, PROJECT_IR_SCHEMA}:
                raise PracticeEvidenceStateError("bundle_target_schema_invalid")
            bundle = dict(copied)
            raw_records = copied["records"]
        elif source_schema == PROJECT_IR_SCHEMA:
            bundle = {"schema": PROJECT_IR_SCHEMA}
            raw_records = [copied]
        elif "records" in copied:
            raise PracticeEvidenceStateError("source_schema_required")
        else:
            raise PracticeEvidenceStateError("source_schema_invalid")
    elif isinstance(copied, Sequence) and not isinstance(copied, (str, bytes, bytearray)):
        bundle = {"schema": PROJECT_IR_SCHEMA}
        raw_records = list(copied)
    else:
        raise PracticeEvidenceStateError("source_not_object_or_records")

    records: list[dict[str, Any]] = []
    for index, record in enumerate(raw_records):
        if not isinstance(record, Mapping):
            raise PracticeEvidenceStateError(f"record_{index}_not_object")
        record_copy = dict(record)
        errors = validate_project_ir(record_copy)
        if errors:
            raise PracticeEvidenceStateError(
                f"project_ir_invalid:{index}:{','.join(errors)}"
            )
        records.append(record_copy)
    return _text(bundle.get("schema")) or PROJECT_IR_SCHEMA, bundle, records


def _source_identity(
    source_schema: str,
    bundle: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> tuple[str, str, str, str, list[dict[str, str]]]:
    def choose(field: str, fallback: str) -> str:
        values: list[str] = []
        top = _text(bundle.get(field))
        if top:
            values.append(top)
        values.extend(_identity_values(records, field))
        unique = sorted(set(values))
        if len(unique) > 1:
            raise PracticeEvidenceStateError(f"{field}_mismatch")
        return unique[0] if unique else fallback

    archive_id = choose("archive_id", "unknown")
    snapshot_id = choose("snapshot_id", "unknown")
    input_hash = choose("input_hash", "")
    if not input_hash:
        input_hash = _hash(_records_semantic_copy(records))
    tenant_values = []
    for key in ("tenant", "tenant_id"):
        value = _text(bundle.get(key))
        if value:
            tenant_values.append(value)
    for record in records:
        for key in ("tenant", "tenant_id"):
            value = _text(record.get(key))
            if value:
                tenant_values.append(value)
    unique_tenants = sorted(set(tenant_values))
    if len(unique_tenants) > 1:
        raise PracticeEvidenceStateError("tenant_mismatch")
    tenant = unique_tenants[0] if unique_tenants else "mak"
    source_rows = [
        {
            "schema": source_schema,
            "archive_id": archive_id,
            "snapshot_id": snapshot_id,
            "input_hash": input_hash,
        }
    ]
    if archive_id == "unknown" or snapshot_id == "unknown":
        source_rows[0]["identity_status"] = "missing_explicit_archive_identity"
    return tenant, archive_id, snapshot_id, input_hash, source_rows


def _ref_list(value: Any) -> list[str]:
    return _string_list(value)


def _explicit_requirement_ids(row: Mapping[str, Any]) -> list[str]:
    """Copy only declared opportunity links; never derive them from content."""
    values: list[str] = []
    for key in ("requirement_ids", "supports"):
        raw = row.get(key)
        if isinstance(raw, Mapping):
            raw = raw.get("requirement_ids")
        values.extend(_string_list(raw))
    return sorted(set(values))


def _artifact_ref(artifact: Mapping[str, Any]) -> str:
    return _text(artifact.get("artifact_ref")) or _text(artifact.get("artifact_id"))


def _artifact_rows(record: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    missing = 0
    for artifact in record.get("artifacts", []) if isinstance(record.get("artifacts"), list) else []:
        if not isinstance(artifact, Mapping):
            missing += 1
            continue
        ref = _artifact_ref(artifact)
        if not ref:
            missing += 1
            continue
        row = {
            "artifact_ref": ref,
            "artifact_id": _text(artifact.get("artifact_id")) or None,
            "physical_id": _text(artifact.get("physical_id")) or None,
            "content_id": _text(artifact.get("content_id")) or None,
            "relative_path": _text(artifact.get("relative_path")),
            "availability": _text(artifact.get("availability")) or "unknown",
            "kind": _text(artifact.get("kind")) or None,
            "role": _text(artifact.get("role")) or None,
            "evidence_refs": [ref],
        }
        rows.append(row)
    return rows, ["artifact_missing_physical_ref"] * missing


def _record_evidence_refs(record: Mapping[str, Any]) -> list[str]:
    refs = _ref_list(record.get("evidence_refs"))
    for key in ("evidence", "relations"):
        for item in record.get(key, []) if isinstance(record.get(key), list) else []:
            if isinstance(item, Mapping):
                refs.extend(_ref_list(item.get("evidence_refs")))
    return sorted(set(refs))


def _record_gap_rows(record: Mapping[str, Any], unit_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_gaps = record.get("gaps") if isinstance(record.get("gaps"), list) else []
    for raw in raw_gaps:
        if isinstance(raw, Mapping):
            code = _text(raw.get("code") or raw.get("field") or raw.get("reason")) or "source_gap"
            detail = _text(raw.get("detail") or raw.get("reason"))
            refs = _ref_list(raw.get("evidence_refs"))
        else:
            code = "source_gap"
            detail = _text(raw)
            refs = []
        row: dict[str, Any] = {"code": code, "unit_id": unit_id}
        if detail:
            row["detail"] = detail
        if refs:
            row["evidence_refs"] = refs
        rows.append(row)
    return rows


def _unit_status(unit: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    value = _text(unit.get("status"))
    if value in {"provisional_unit", "unresolved_unit"}:
        return value
    if _text(record.get("state")) == "candidate":
        return "provisional_unit"
    return "unresolved_unit"


def _safe_source_state(value: Any) -> str:
    state = _text(value).casefold()
    if state in {"candidate", "unknown", "review_required"}:
        return state
    if state in TRUTH_STATUSES:
        return "blocked_truth_status"
    return state or "unknown"


def _unit_from_record(
    record: Mapping[str, Any],
    source_schema: str,
    archive_id: str,
    snapshot_id: str,
    input_hash: str,
    index: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    archive_unit = record.get("archive_unit") if isinstance(record.get("archive_unit"), Mapping) else {}
    project_id = _text(record.get("project_id"))
    unit_id = _text(archive_unit.get("unit_id")) or f"project:{project_id}"
    artifact_rows, artifact_gaps = _artifact_rows(record)
    artifact_refs = _ref_list(archive_unit.get("member_refs"))
    if not artifact_refs:
        artifact_refs = sorted({row["artifact_ref"] for row in artifact_rows})
    known_rows = {row["artifact_ref"] for row in artifact_rows}
    for ref in artifact_refs:
        if ref not in known_rows:
            artifact_rows.append({
                "artifact_ref": ref,
                "artifact_id": None,
                "physical_id": None,
                "content_id": None,
                "relative_path": "",
                "availability": "unknown",
                "kind": None,
                "role": None,
                "evidence_refs": [],
            })
    relation_rows = [item for item in record.get("relations", []) if isinstance(item, Mapping)]
    dependency_refs = _ref_list(archive_unit.get("dependency_refs"))
    for relation in relation_rows:
        predicate = _text(relation.get("predicate")).casefold()
        if predicate in DEPENDENCY_PREDICATES:
            target = _text(relation.get("object"))
            if target:
                dependency_refs.append(target)
    dependency_refs = sorted(set(dependency_refs))
    unit = {
        "unit_id": unit_id,
        "project_id": project_id,
        "role": _text(archive_unit.get("role")) or "unknown",
        "status": _unit_status(archive_unit, record),
        "source_state": _safe_source_state(record.get("state")),
        "artifact_refs": sorted(set(artifact_refs)),
        "member_refs": sorted(set(artifact_refs)),
        "dependency_refs": dependency_refs,
        "candidate_ids": _ref_list(archive_unit.get("candidate_ids")),
        "evidence_refs": _record_evidence_refs(record),
        "evidence_for": _string_list(archive_unit.get("evidence_for")),
        "evidence_against": _string_list(archive_unit.get("evidence_against")),
        "alternatives": _string_list(archive_unit.get("alternatives")),
        "missing_evidence": _string_list(archive_unit.get("missing_evidence")),
        "provenance_ref": f"unit:{unit_id}",
    }
    provenance = {
        "source_schema": source_schema,
        "project_id": project_id,
        "unit_id": unit_id,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": input_hash,
        "evidence_refs": _record_evidence_refs(record),
        "source_kind": (
            _text(record.get("source", {}).get("kind"))
            if isinstance(record.get("source"), Mapping) else "unknown"
        ) or "unknown",
        "source_rescan": False,
    }
    unit["provenance"] = provenance
    for artifact in artifact_rows:
        artifact["unit_id"] = unit_id
    gaps = [{"code": "artifact_missing_physical_ref", "unit_id": unit_id} for _ in artifact_gaps]
    gaps.extend(_record_gap_rows(record, unit_id))
    if len(artifact_refs) != len(set(artifact_refs)):
        gaps.append({"code": "duplicate_member_ref", "unit_id": unit_id})
    provenance_rows = [provenance]
    return unit, artifact_rows, gaps, provenance_rows


def _claim_status(raw_status: Any, evidence_refs: list[str]) -> tuple[str, str | None]:
    source_status = _text(raw_status).casefold()
    if source_status in TRUTH_STATUSES:
        return "unknown", "truth_promotion_blocked"
    if not evidence_refs:
        return "unknown", "claim_without_evidence_refs"
    if source_status in {"supported", "observed", "corroborated"}:
        return "supported", None
    if source_status in {"candidate", "pending", "provisional"}:
        return "candidate", None
    if source_status in {"unknown", "unresolved", ""}:
        return "unknown", None
    return "unknown", "claim_status_unrecognized"


def _claim_rows(
    record: Mapping[str, Any],
    unit_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    raw_claims = []
    if isinstance(record.get("claims"), list):
        raw_claims.extend(item for item in record["claims"] if isinstance(item, Mapping))
    if isinstance(record.get("evidence"), list):
        raw_claims.extend(
            item for item in record["evidence"]
            if isinstance(item, Mapping) and any(key in item for key in ("claim", "claim_text", "statement"))
        )
    rows: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for index, raw in enumerate(raw_claims):
        evidence_refs = _ref_list(raw.get("evidence_refs"))
        status, gap_code = _claim_status(raw.get("status", raw.get("claim_status")), evidence_refs)
        statement = (
            _text(raw.get("statement")) or _text(raw.get("claim"))
            or _text(raw.get("claim_text")) or _text(raw.get("label"))
            or _text(raw.get("value"))
        )
        claim_id = _text(raw.get("claim_id")) or "claim:" + hashlib.sha256(
            _stable_json({
                "unit_id": unit_id,
                "index": index,
                "statement": statement,
                "status": status,
                "evidence_refs": evidence_refs,
            }).encode("utf-8")
        ).hexdigest()[:32]
        source_status = _text(raw.get("status", raw.get("claim_status"))).casefold()
        safe_source_status = "blocked_truth_status" if source_status in TRUTH_STATUSES else (
            source_status if source_status in {"supported", "observed", "corroborated", "candidate", "pending", "provisional", "unknown", "unresolved", ""}
            else "unrecognized_status"
        )
        row = {
            "claim_id": claim_id,
            "unit_id": unit_id,
            "status": status,
            "statement": statement,
            "evidence_refs": evidence_refs,
            "requirement_ids": _explicit_requirement_ids(raw),
            "source_status": safe_source_status or "unknown",
            "provenance_ref": f"unit:{unit_id}",
        }
        facet = _text(raw.get("facet")).casefold()
        if facet:
            # Preserve the Copilot vocabulary only when the source declared it;
            # this bridge does not invent or classify facets.
            row["facet"] = facet
        rows.append(row)
        if gap_code:
            gaps.append({"code": gap_code, "unit_id": unit_id, "claim_id": claim_id})
    for index, unknown in enumerate(record.get("unknowns", []) if isinstance(record.get("unknowns"), list) else []):
        statement = _text(unknown)
        if not statement:
            continue
        claim_id = "claim:" + hashlib.sha256(
            _stable_json({"unit_id": unit_id, "unknown": statement, "index": index}).encode("utf-8")
        ).hexdigest()[:32]
        rows.append({
            "claim_id": claim_id,
            "unit_id": unit_id,
            "status": "unknown",
            "statement": statement,
            "evidence_refs": [],
            "requirement_ids": [],
            "source_status": "unknown",
            "provenance_ref": f"unit:{unit_id}",
        })
        gaps.append({"code": "unknown_without_evidence", "unit_id": unit_id, "claim_id": claim_id})
    return rows, gaps


def _evidence_items(record: Mapping[str, Any], dimension: str) -> list[Mapping[str, Any]]:
    aliases = {
        "media": ("media", "media_evidence", "practice_media"),
        "capabilities": ("capabilities", "capability_evidence", "practice_capabilities"),
        "temporality": ("temporality", "temporal", "temporal_evidence", "practice_temporality"),
        "manifestations": ("manifestations", "manifestation_evidence", "practice_manifestations"),
        "resources": ("resources", "resource_evidence", "practice_resources"),
    }
    rows: list[Mapping[str, Any]] = []
    for key in aliases[dimension]:
        if key in record:
            rows.extend(_mapping_list(record[key]))
    for item in record.get("evidence", []) if isinstance(record.get("evidence"), list) else []:
        if not isinstance(item, Mapping):
            continue
        declared = _text(item.get("dimension") or item.get("facet")).casefold()
        if declared == dimension:
            rows.append(item)
    relation_dimensions = {
        "manifestations": MANIFESTATION_PREDICATES,
        "resources": {"shared_resource", "shared_resource_of"},
    }
    for relation in record.get("relations", []) if isinstance(record.get("relations"), list) else []:
        if not isinstance(relation, Mapping):
            continue
        predicate = _text(relation.get("predicate")).casefold()
        if predicate in relation_dimensions.get(dimension, set()):
            row = dict(relation)
            row.setdefault("value", _text(relation.get("object")))
            rows.append(row)
    return rows


def _dimension_rows(
    record: Mapping[str, Any],
    unit_id: str,
    dimension: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for index, raw in enumerate(_evidence_items(record, dimension)):
        refs = _ref_list(raw.get("evidence_refs"))
        value = _text(raw.get("value") or raw.get("label") or raw.get("declared_value"))
        if not refs:
            gaps.append({"code": "dimension_without_evidence_refs", "dimension": dimension, "unit_id": unit_id})
            continue
        if not value:
            gaps.append({"code": "dimension_value_missing", "dimension": dimension, "unit_id": unit_id})
            continue
        source_status = _text(raw.get("status")).casefold()
        status = "candidate" if source_status in {"candidate", "pending", "provisional"} else "supported"
        if source_status in TRUTH_STATUSES:
            status = "unknown"
            gaps.append({"code": "truth_promotion_blocked", "dimension": dimension, "unit_id": unit_id})
        rows.append({
            "dimension": dimension,
            "value": value,
            "status": status,
            "evidence_refs": refs,
            "requirement_ids": _explicit_requirement_ids(raw),
            "unit_id": unit_id,
            "provenance_ref": f"unit:{unit_id}",
            "source_index": index,
        })
    return rows, gaps


def _dependencies(
    record: Mapping[str, Any],
    unit: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    relation_rows = [item for item in record.get("relations", []) if isinstance(item, Mapping)]
    rows: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    explicit: dict[tuple[str, str], Mapping[str, Any]] = {}
    for relation in relation_rows:
        predicate = _text(relation.get("predicate")).casefold()
        target = _text(relation.get("object"))
        if predicate in DEPENDENCY_PREDICATES and target:
            explicit[(predicate, target)] = relation
    for target in unit["dependency_refs"]:
        relation = next((row for (predicate, value), row in explicit.items() if value == target), None)
        predicate = _text(relation.get("predicate")) if relation else "provisional_dependency"
        refs = _ref_list(relation.get("evidence_refs")) if relation else []
        row = {
            "unit_id": unit["unit_id"],
            "predicate": predicate,
            "target_ref": target,
            "status": "candidate" if refs else "unknown",
            "evidence_refs": refs,
            "candidate_ids": _ref_list(unit.get("candidate_ids")),
            "provenance_ref": f"unit:{unit['unit_id']}",
        }
        rows.append(row)
        if not refs:
            gaps.append({"code": "dependency_without_evidence_refs", "unit_id": unit["unit_id"], "target_ref": target})
    return rows, gaps


def _partition(bundle: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    ambiguous = _ref_list(bundle.get("ambiguous_refs"))
    unassigned = _ref_list(bundle.get("unassigned_refs"))
    for record in records:
        for key, target in (("ambiguous_refs", ambiguous), ("unassigned_refs", unassigned)):
            target.extend(_ref_list(record.get(key)))
            archive_unit = record.get("archive_unit") if isinstance(record.get("archive_unit"), Mapping) else {}
            target.extend(_ref_list(archive_unit.get(key)))
    return sorted(set(ambiguous)), sorted(set(unassigned))


def _state_without_hash(state: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(state))
    result.pop("state_hash", None)
    return result


def _reconciliation(
    units: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
    ambiguous: Sequence[str],
    unassigned: Sequence[str],
    claims: Mapping[str, Sequence[Mapping[str, Any]]],
    dimensions: Mapping[str, Sequence[Mapping[str, Any]]],
    gaps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    refs = [str(row.get("artifact_ref")) for row in artifacts if row.get("artifact_ref")]
    content_groups: dict[str, list[str]] = {}
    for row in artifacts:
        content_id = _text(row.get("content_id"))
        if content_id:
            content_groups.setdefault(content_id, []).append(str(row["artifact_ref"]))
    duplicate_groups = sum(1 for refs_for_content in content_groups.values() if len(refs_for_content) > 1)
    unit_refs = [ref for unit in units for ref in unit.get("member_refs", [])]
    overlaps = sorted(set(unit_refs) & (set(ambiguous) | set(unassigned)))
    claim_counts = {status: len(claims.get(status, [])) for status in CLAIM_STATUSES}
    return {
        "unit_count": len(units),
        "physical_artifact_count": len(artifacts),
        "artifact_ref_count": len(refs),
        "artifact_refs_unique": len(refs) == len(set(refs)),
        "duplicate_content_groups": duplicate_groups,
        "duplicate_physical_refs_collapsed": False,
        "ambiguous_ref_count": len(ambiguous),
        "unassigned_ref_count": len(unassigned),
        "partition_overlaps": overlaps,
        "claims_by_status": claim_counts,
        "dimension_counts": {dimension: len(dimensions.get(dimension, [])) for dimension in DIMENSIONS},
        "gap_count": len(gaps),
        "truth_promotions": 0,
        "semantic_inferences": 0,
        "source_rescan": False,
        "balanced": not overlaps and len(refs) == len(set(refs)),
    }


def build_practice_evidence_state(source: Any, *, tenant: str | None = None) -> dict[str, Any]:
    """Build a deterministic evidence-only state from Stage 2D or Project IR.

    ``tenant`` is optional and defaults to the explicit source tenant or
    ``mak``.  No field is inferred from a path, filename, extension or title.
    """
    source_schema, bundle, records = _normalise_source(source)
    source_tenant, archive_id, snapshot_id, input_hash, source_rows = _source_identity(
        source_schema, bundle, records
    )
    if tenant is not None and _text(tenant) and _text(tenant) != source_tenant and source_tenant != "mak":
        raise PracticeEvidenceStateError("tenant_argument_mismatch")
    tenant_value = _text(tenant) or source_tenant
    ambiguous, unassigned = _partition(bundle, records)
    units: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    claims_by_status: dict[str, list[dict[str, Any]]] = {status: [] for status in CLAIM_STATUSES}
    dimensions: dict[str, list[dict[str, Any]]] = {dimension: [] for dimension in DIMENSIONS}
    dependencies: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        unit, artifact_rows, unit_gaps, provenance_rows = _unit_from_record(
            record, source_schema, archive_id, snapshot_id, input_hash, index
        )
        units.append(unit)
        artifacts.extend(artifact_rows)
        gaps.extend(unit_gaps)
        provenance.extend(provenance_rows)
        claim_rows, claim_gaps = _claim_rows(record, unit["unit_id"])
        gaps.extend(claim_gaps)
        for row in claim_rows:
            claims_by_status[row["status"]].append(row)
        for dimension in DIMENSIONS:
            dimension_rows, dimension_gaps = _dimension_rows(record, unit["unit_id"], dimension)
            dimensions[dimension].extend(dimension_rows)
            gaps.extend(dimension_gaps)
        dependency_rows, dependency_gaps = _dependencies(record, unit)
        dependencies.extend(dependency_rows)
        gaps.extend(dependency_gaps)

    units.sort(key=lambda row: row["unit_id"])
    if len({unit["unit_id"] for unit in units}) != len(units):
        raise PracticeEvidenceStateError("unit_ids_not_unique")
    artifacts.sort(key=lambda row: (row["artifact_ref"], row.get("relative_path", "")))
    dependencies.sort(key=lambda row: (row["unit_id"], row["target_ref"], row["predicate"]))
    provenance.sort(key=lambda row: (row["unit_id"], row["project_id"]))
    for status in CLAIM_STATUSES:
        claims_by_status[status].sort(key=lambda row: row["claim_id"])
    for dimension in DIMENSIONS:
        dimensions[dimension].sort(key=lambda row: (row["value"], row["unit_id"], row["evidence_refs"]))
        if not dimensions[dimension]:
            gaps.append({"code": "dimension_unobserved", "dimension": dimension})
    gaps.sort(key=lambda row: _stable_json(row))
    abstentions = [
        {"code": row["code"], "dimension": row.get("dimension"), "unit_id": row.get("unit_id")}
        for row in gaps
        if row.get("code") in {
            "dimension_unobserved", "claim_without_evidence_refs", "unknown_without_evidence",
            "truth_promotion_blocked", "dimension_without_evidence_refs", "dependency_without_evidence_refs",
        }
    ]
    abstentions.sort(key=lambda row: _stable_json(row))
    reconciliation = _reconciliation(
        units, artifacts, ambiguous, unassigned, claims_by_status, dimensions, gaps
    )
    state: dict[str, Any] = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "tenant": tenant_value,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": input_hash,
        "source_schema": source_schema,
        "units": units,
        "artifacts": artifacts,
        "media": dimensions["media"],
        "capabilities": dimensions["capabilities"],
        "temporality": dimensions["temporality"],
        "manifestations": dimensions["manifestations"],
        "resources": dimensions["resources"],
        "claims": claims_by_status,
        "dependencies": dependencies,
        "ambiguous_refs": ambiguous,
        "unassigned_refs": unassigned,
        "gaps": gaps,
        "abstentions": abstentions,
        "provenance": {
            "producer": "flujo.knowledge.practice_evidence_state",
            "method": "stage2d_project_ir_evidence_projection",
            "source_rescan": False,
            "source": source_rows,
            "records": provenance,
        },
        "reconciliation": reconciliation,
    }
    state["state_hash"] = _hash(_state_without_hash(state))
    errors = validate_practice_evidence_state(state)
    if errors:
        raise PracticeEvidenceStateError("state_invalid:" + ",".join(errors))
    return state


def validate_practice_evidence_state(state: Any) -> list[str]:
    """Return validation errors; this validator never repairs or mutates input."""
    errors: list[str] = []
    if not isinstance(state, Mapping):
        return ["state_not_object"]
    required = {
        "schema", "algorithm_version", "tenant", "archive_id", "snapshot_id", "input_hash",
        "source_schema", "units", "artifacts", *DIMENSIONS, "claims", "dependencies", "ambiguous_refs",
        "unassigned_refs", "gaps", "abstentions", "provenance", "reconciliation", "state_hash",
    }
    errors.extend("missing_" + key for key in sorted(required - set(state)))
    if state.get("schema") != SCHEMA:
        errors.append("bad_schema")
    if state.get("algorithm_version") != ALGORITHM_VERSION:
        errors.append("bad_algorithm_version")
    for key in ("tenant", "archive_id", "snapshot_id", "input_hash"):
        if not _text(state.get(key)):
            errors.append("missing_" + key)
    if not isinstance(state.get("units"), list):
        errors.append("units_not_list")
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts_not_list")
    else:
        for artifact in artifacts:
            if not isinstance(artifact, Mapping) or not _text(artifact.get("artifact_ref")):
                errors.append("artifact_ref_missing")
    for dimension in DIMENSIONS:
        if not isinstance(state.get(dimension), list):
            errors.append(dimension + "_not_list")
    claims = state.get("claims")
    if not isinstance(claims, Mapping) or set(claims) != set(CLAIM_STATUSES):
        errors.append("claims_shape_invalid")
    else:
        for status in CLAIM_STATUSES:
            if not isinstance(claims[status], list):
                errors.append("claims_" + status + "_not_list")
            for row in claims[status] if isinstance(claims[status], list) else []:
                if not isinstance(row, Mapping) or row.get("status") != status:
                    errors.append("claim_status_mismatch")
                    continue
                if not isinstance(row.get("evidence_refs"), list):
                    errors.append("claim_evidence_refs_invalid")
                requirement_ids = row.get("requirement_ids")
                if not isinstance(requirement_ids, list) or any(
                    not isinstance(value, str) or not value.strip() for value in requirement_ids
                ):
                    errors.append("claim_requirement_ids_invalid")
                elif requirement_ids != sorted(set(requirement_ids)):
                    errors.append("claim_requirement_ids_not_sorted_unique")
                if _text(row.get("status")).casefold() in TRUTH_STATUSES:
                    errors.append("truth_promotion")
    for key in ("dependencies", "ambiguous_refs", "unassigned_refs", "gaps", "abstentions"):
        if not isinstance(state.get(key), list):
            errors.append(key + "_not_list")
    units = state.get("units") if isinstance(state.get("units"), list) else []
    unit_ids = []
    for unit in units:
        if not isinstance(unit, Mapping):
            errors.append("unit_not_object")
            continue
        unit_id = _text(unit.get("unit_id"))
        if not unit_id:
            errors.append("unit_id_missing")
        unit_ids.append(unit_id)
        if unit.get("status") not in {"provisional_unit", "unresolved_unit"}:
            errors.append("unit_status_invalid")
        for key in ("artifact_refs", "member_refs", "dependency_refs"):
            if not isinstance(unit.get(key), list):
                errors.append("unit_" + key + "_invalid")
    if unit_ids != sorted(unit_ids):
        errors.append("units_not_sorted")
    if len(unit_ids) != len(set(unit_ids)):
        errors.append("unit_ids_not_unique")
    for dimension in DIMENSIONS:
        rows = state.get(dimension) if isinstance(state.get(dimension), list) else []
        for row in rows:
            if not isinstance(row, Mapping) or not _text(row.get("value")):
                errors.append(dimension + "_row_invalid")
            elif not isinstance(row.get("evidence_refs"), list) or not row.get("evidence_refs"):
                errors.append(dimension + "_evidence_missing")
            requirement_ids = row.get("requirement_ids") if isinstance(row, Mapping) else None
            if not isinstance(requirement_ids, list) or any(
                not isinstance(value, str) or not value.strip() for value in requirement_ids
            ):
                errors.append(dimension + "_requirement_ids_invalid")
            elif requirement_ids != sorted(set(requirement_ids)):
                errors.append(dimension + "_requirement_ids_not_sorted_unique")
    provenance = state.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("source_rescan") is not False:
        errors.append("provenance_invalid")
    if not isinstance(state.get("reconciliation"), Mapping):
        errors.append("reconciliation_invalid")
    if isinstance(state.get("state_hash"), str):
        try:
            if state["state_hash"] != _hash(_state_without_hash(state)):
                errors.append("state_hash_mismatch")
        except (TypeError, ValueError):
            errors.append("state_hash_unserializable")
    return sorted(set(errors))


def assert_practice_evidence_state(state: Any) -> bool:
    errors = validate_practice_evidence_state(state)
    if errors:
        raise PracticeEvidenceStateError("state_invalid:" + ",".join(errors))
    return True


def serialize_practice_evidence_state(state: Mapping[str, Any]) -> str:
    assert_practice_evidence_state(state)
    return _stable_json(state)


def deserialize_practice_evidence_state(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise PracticeEvidenceStateError(f"json_invalid:{error}") from error
    if not isinstance(value, Mapping):
        raise PracticeEvidenceStateError("state_json_not_object")
    assert_practice_evidence_state(value)
    return copy.deepcopy(dict(value))


# Compact aliases for callers that describe this operation as compilation or
# projection.  They remain one pure function, not separate registries.
compile_practice_evidence_state = build_practice_evidence_state
project_practice_evidence_state = build_practice_evidence_state
validate_state = validate_practice_evidence_state


__all__ = [
    "ALGORITHM_VERSION", "BUNDLE_SCHEMA", "CLAIM_STATUSES", "DIMENSIONS", "PROJECT_IR_SCHEMA",
    "PracticeEvidenceStateError", "SCHEMA", "assert_practice_evidence_state",
    "build_practice_evidence_state", "compile_practice_evidence_state",
    "deserialize_practice_evidence_state", "project_practice_evidence_state",
    "serialize_practice_evidence_state", "validate_practice_evidence_state", "validate_state",
]
