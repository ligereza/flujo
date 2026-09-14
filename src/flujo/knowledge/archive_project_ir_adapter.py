"""Deterministic Stage 2C -> Project IR projection.

The archive-memory and Stage 2C payloads remain the factual/provisional
authority.  This module emits portable ``mak-project-ir-v1`` records as an
additive view.  It never rescans an archive, writes a database, promotes a
candidate relation, or introduces a filesystem root that was not observed.
"""

from __future__ import annotations

from typing import Any, Mapping

from .archive_unit_reconstruction import (
    ArchiveUnitReconstructionError,
    validate_unit_payload,
)
from .project_ir import PROJECT_STATES, SCHEMA as PROJECT_IR_SCHEMA, validate_project_ir


SCHEMA = "mak-archive-project-ir-bundle-v1"
UNIT_SCHEMA = "mak-archive-unit-reconstruction-v1"
RELATION_SCHEMA = "mak-archive-relation-candidates-v1"
PROJECT_SCHEMA = PROJECT_IR_SCHEMA
ALGORITHM_VERSION = "archive-units-to-project-ir-1"

_BUNDLE_FIELDS = {
    "schema", "source_unit_schema", "target_project_ir_schema", "algorithm_version",
    "archive_id", "snapshot_id", "input_hash", "relation_hash", "records",
    "unit_project_map", "ambiguous_refs", "unassigned_refs", "reconciliation",
}
_RECORD_REQUIRED_FIELDS = {
    "schema", "project_id", "title", "state", "source", "purpose", "domains",
    "artifacts", "relations", "evidence", "unknowns", "next_action", "provenance",
    "archive_unit", "archive_id", "snapshot_id", "input_hash", "relation_hash",
}
_UNIT_MAP_FIELDS = {"unit_id", "project_id", "role", "status"}
_RELATION_FIELDS = {
    "relation_id", "subject", "predicate", "object", "status", "score",
    "evidence_refs", "evidence_for", "evidence_against", "alternatives",
    "missing_evidence", "next_probe", "archive_unit_id",
}


class ArchiveProjectIRAdapterError(ValueError):
    """Invalid Stage 2C input or invalid deterministic Project IR bundle."""


def _sorted_unique(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ArchiveProjectIRAdapterError(f"{field}_invalid")
    result = sorted(set(value))
    if value != result:
        raise ArchiveProjectIRAdapterError(f"{field}_not_sorted_unique")
    return result


def _project_id_for(unit_id: str) -> str:
    # Keep the entire unit digest in the portable ID while avoiding the colon
    # that Project IR's historical slug helper normalizes away.
    digest = unit_id.removeprefix("unit:")
    return "archive-unit-" + digest


def _artifact_record(artifact: Mapping[str, Any], unit_id: str) -> dict[str, Any]:
    ref = str(artifact["artifact_ref"])
    sha256 = artifact.get("sha256") if isinstance(artifact.get("sha256"), str) else ""
    availability = str(artifact.get("availability") or "unknown")
    hash_status = "full" if sha256 else ("unavailable" if availability not in {"available", "present"} else "not_computed")
    return {
        "artifact_id": ref,
        "artifact_ref": ref,
        "physical_id": artifact["physical_id"],
        "content_id": artifact.get("content_id"),
        "relative_path": artifact["relative_path"],
        "parent_path": artifact["parent_path"],
        "name": artifact["basename"],
        "suffix": (artifact["suffix_chain"][-1] if artifact["suffix_chain"] else "").casefold(),
        "format_family": artifact["family"],
        "media_type": artifact["media_type"],
        "size_bytes": int(artifact["size"] or 0),
        # Stage 2A intentionally omits mtime from semantic output.  Zero is a
        # schema-compatible absence marker, not a claimed observed timestamp.
        "mtime_ns": 0,
        "mtime_observed": False,
        "sha256": sha256,
        "hash_status": hash_status,
        "availability": availability,
        "kind": artifact["kind"],
        "role": "provisional_member",
        "unit_id": unit_id,
        "references": list(artifact["references"]),
    }


def _membership_relation(
    project_id: str,
    unit_id: str,
    artifact_ref: str,
    assignment: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "relation_id": f"membership:{unit_id}:{artifact_ref}",
        "subject": project_id,
        "predicate": "provisional_member",
        "object": artifact_ref,
        "status": "provisional",
        "score": None,
        "evidence_refs": list(assignment["candidate_ids"]),
        "evidence_for": list(assignment["reason_codes"]),
        "evidence_against": [],
        "alternatives": list(assignment["alternatives"]),
        "missing_evidence": [],
        "next_probe": None,
        "archive_unit_id": unit_id,
    }


def _dependency_relation(project_id: str, unit: Mapping[str, Any], dependency_ref: str) -> dict[str, Any]:
    candidate_ids = list(unit["candidate_ids"])
    return {
        "relation_id": f"dependency:{unit['unit_id']}:{dependency_ref}",
        "subject": project_id,
        "predicate": "provisional_dependency",
        "object": dependency_ref,
        "status": "provisional",
        "score": None,
        "evidence_refs": candidate_ids,
        "evidence_for": ["dependency_ref_preserved"],
        "evidence_against": ["dependency_not_project_member"],
        "alternatives": [],
        "missing_evidence": [],
        "next_probe": None,
        "archive_unit_id": unit["unit_id"],
    }


def _candidate_relation(candidate: Mapping[str, Any], unit_id: str) -> dict[str, Any]:
    return {
        "relation_id": candidate["candidate_id"],
        "subject": candidate["source_ref"],
        "predicate": candidate["relation"],
        "object": candidate["target_ref"],
        "status": candidate["status"],
        "score": candidate["score"],
        "evidence_refs": list(candidate["evidence_refs"]),
        "evidence_for": list(candidate["evidence_for"]),
        "evidence_against": list(candidate["evidence_against"]),
        "alternatives": list(candidate["alternatives"]),
        "missing_evidence": list(candidate["missing_evidence"]),
        "next_probe": candidate["next_probe"],
        "archive_unit_id": unit_id,
    }


def _record_for_unit(
    projection: Mapping[str, Any],
    relation_hash: str,
    unit: Mapping[str, Any],
    artifacts_by_ref: Mapping[str, Mapping[str, Any]],
    assignments_by_ref: Mapping[str, Mapping[str, Any]],
    candidates_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    archive_id = str(projection["archive_id"])
    snapshot_id = str(projection["snapshot_id"])
    unit_id = str(unit["unit_id"])
    project_id = _project_id_for(unit_id)
    member_refs = list(unit["member_refs"])
    dependency_refs = list(unit["dependency_refs"])
    artifacts = [
        _artifact_record(artifacts_by_ref[ref], unit_id)
        for ref in member_refs
    ]
    relations_out = [
        _membership_relation(project_id, unit_id, ref, assignments_by_ref[ref])
        for ref in member_refs
    ]
    relations_out.extend(
        _dependency_relation(project_id, unit, ref)
        for ref in dependency_refs
    )
    relations_out.extend(
        _candidate_relation(candidates_by_id[candidate_id], unit_id)
        for candidate_id in unit["candidate_ids"]
        if candidate_id in candidates_by_id
    )
    relations_out.sort(key=lambda item: (item["relation_id"], item["predicate"], item["object"]))
    evidence = [
        {
            "kind": "archive_unit_provenance",
            "archive_id": archive_id,
            "snapshot_id": snapshot_id,
            "input_hash": projection["input_hash"],
            "relation_hash": relation_hash,
            "unit_id": unit_id,
            "status": unit["status"],
        },
        {"kind": "unit_evidence_for", "values": list(unit["evidence_for"])},
        {"kind": "unit_evidence_against", "values": list(unit["evidence_against"])},
        {"kind": "unit_alternatives", "values": list(unit["alternatives"])},
        {"kind": "unit_missing_evidence", "values": list(unit["missing_evidence"])},
    ]
    unknowns = sorted(set(
        list(unit["missing_evidence"])
        + (["unit_status_unresolved"] if unit["status"] == "unresolved_unit" else [])
    ))
    state = "candidate" if unit["status"] == "provisional_unit" else "unknown"
    record = {
        "schema": PROJECT_IR_SCHEMA,
        "project_id": project_id,
        "title": f"Provisional archive unit {unit_id}",
        "state": state,
        "source": {
            "kind": "archive_unit_reconstruction",
            "root_ref": f"archive:{archive_id}:snapshot:{snapshot_id}:unit:{unit_id}",
            "root_exists": False,
            "archive_id": archive_id,
            "snapshot_id": snapshot_id,
            "unit_id": unit_id,
        },
        "purpose": "Deterministic provisional Project IR view; not a verified artistic claim.",
        "domains": ["archive", "reconstruction"],
        "artifacts": artifacts,
        "relations": relations_out,
        "evidence": evidence,
        "unknowns": unknowns,
        "next_action": "preserve_provisional_status",
        "provenance": {
            "producer": "flujo.knowledge.archive_project_ir_adapter",
            "method": "stage2c_unit_projection",
            "archive_id": archive_id,
            "snapshot_id": snapshot_id,
            "input_hash": projection["input_hash"],
            "relation_hash": relation_hash,
            "unit_id": unit_id,
            "source_unit_schema": UNIT_SCHEMA,
            "source_relation_schema": RELATION_SCHEMA,
        },
        "archive_unit": dict(unit),
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": projection["input_hash"],
        "relation_hash": relation_hash,
    }
    errors = validate_project_ir(record)
    if errors:
        raise ArchiveProjectIRAdapterError(
            f"project_ir_invalid:{project_id}:{','.join(errors)}"
        )
    return record


def adapt_archive_units_to_project_ir(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
    units: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt Stage 2C units while validating the complete upstream chain."""

    try:
        validate_unit_payload(projection, relations, units)
    except (ArchiveUnitReconstructionError, ValueError) as error:
        raise ArchiveProjectIRAdapterError(f"units_invalid:{error}") from error
    artifacts = {
        str(item["artifact_ref"]): dict(item)
        for item in projection["artifacts"]
    }
    candidates = {
        str(item["candidate_id"]): dict(item)
        for item in relations["candidates"]
    }
    assignments = {
        str(item["artifact_ref"]): dict(item)
        for item in units["assignments"]
    }
    records = [
        _record_for_unit(projection, units["relation_hash"], unit, artifacts, assignments, candidates)
        for unit in units["units"]
    ]
    records.sort(key=lambda item: item["project_id"])
    unit_project_map = [
        {
            "unit_id": unit["unit_id"],
            "project_id": _project_id_for(str(unit["unit_id"])),
            "role": unit["role"],
            "status": unit["status"],
        }
        for unit in units["units"]
    ]
    unit_project_map.sort(key=lambda item: item["unit_id"])
    reconciliation = {
        "units_input": len(units["units"]),
        "records_output": len(records),
        "unit_mappings": len(unit_project_map),
        "unit_ids_unique": len({item["unit_id"] for item in unit_project_map}) == len(unit_project_map),
        "units_mapped_exactly_once": len(records) == len(units["units"]) == len(unit_project_map),
        "project_ids_unique": len({item["project_id"] for item in unit_project_map}) == len(unit_project_map),
        "member_refs_total": sum(len(unit["member_refs"]) for unit in units["units"]),
        "member_refs_preserved": all(
            ref in {
                artifact.get("artifact_ref")
                for record in records
                for artifact in record["artifacts"]
            }
            for unit in units["units"]
            for ref in unit["member_refs"]
        ),
        "dependency_refs_total": sum(len(unit["dependency_refs"]) for unit in units["units"]),
        "dependency_refs_preserved": all(
            ref in {
                relation.get("object")
                for record in records
                for relation in record["relations"]
                if relation.get("predicate") == "provisional_dependency"
            }
            for unit in units["units"]
            for ref in unit["dependency_refs"]
        ),
        "ambiguous_refs_count": len(units["ambiguous_refs"]),
        "unassigned_refs_count": len(units["unassigned_refs"]),
        "duplicates": len(unit_project_map) - len({item["unit_id"] for item in unit_project_map}),
        "loss": len(units["units"]) - len(records),
        "balanced": len(records) == len(units["units"]),
        "truth_promotions": 0,
        "deterministic_order": records == sorted(records, key=lambda item: item["project_id"]),
        "ambiguous_and_unassigned_explicit": True,
    }
    bundle = {
        "schema": SCHEMA,
        "source_unit_schema": UNIT_SCHEMA,
        "target_project_ir_schema": PROJECT_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "archive_id": projection["archive_id"],
        "snapshot_id": projection["snapshot_id"],
        "input_hash": projection["input_hash"],
        "relation_hash": units["relation_hash"],
        "records": records,
        "unit_project_map": unit_project_map,
        "ambiguous_refs": list(units["ambiguous_refs"]),
        "unassigned_refs": list(units["unassigned_refs"]),
        "reconciliation": reconciliation,
    }
    validate_project_ir_bundle(projection, relations, units, bundle)
    return bundle


def project_ir_bundle_from_units(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
    units: Mapping[str, Any],
) -> dict[str, Any]:
    """Public descriptive alias for the Stage 2D adapter."""

    return adapt_archive_units_to_project_ir(projection, relations, units)


def validate_project_ir_bundle(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
    units: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> bool:
    """Strictly validate the additive bundle and every Project IR record."""

    try:
        validate_unit_payload(projection, relations, units)
    except (ArchiveUnitReconstructionError, ValueError) as error:
        raise ArchiveProjectIRAdapterError(f"units_invalid:{error}") from error
    if not isinstance(bundle, Mapping) or set(bundle) != _BUNDLE_FIELDS:
        raise ArchiveProjectIRAdapterError("bundle_field_set_invalid")
    if bundle["schema"] != SCHEMA or bundle["source_unit_schema"] != UNIT_SCHEMA or bundle["target_project_ir_schema"] != PROJECT_SCHEMA:
        raise ArchiveProjectIRAdapterError("bundle_schema_invalid")
    if bundle["algorithm_version"] != ALGORITHM_VERSION:
        raise ArchiveProjectIRAdapterError("bundle_algorithm_version_invalid")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if bundle[field] != projection[field]:
            raise ArchiveProjectIRAdapterError(f"bundle_{field}_mismatch")
    if bundle["relation_hash"] != units["relation_hash"]:
        raise ArchiveProjectIRAdapterError("bundle_relation_hash_mismatch")

    records = bundle["records"]
    mappings = bundle["unit_project_map"]
    if not isinstance(records, list) or not isinstance(mappings, list):
        raise ArchiveProjectIRAdapterError("bundle_records_or_map_invalid")
    if records != sorted(records, key=lambda item: item.get("project_id", "")):
        raise ArchiveProjectIRAdapterError("bundle_records_not_sorted")
    if mappings != sorted(mappings, key=lambda item: item.get("unit_id", "")):
        raise ArchiveProjectIRAdapterError("bundle_map_not_sorted")

    units_by_id = {str(unit["unit_id"]): unit for unit in units["units"]}
    records_by_unit: dict[str, Mapping[str, Any]] = {}
    project_ids: list[str] = []
    for record in records:
        if not isinstance(record, Mapping) or not _RECORD_REQUIRED_FIELDS.issubset(set(record)):
            raise ArchiveProjectIRAdapterError("project_ir_record_shape_invalid")
        if set(record["provenance"]) != {
            "producer", "method", "archive_id", "snapshot_id", "input_hash", "relation_hash",
            "unit_id", "source_unit_schema", "source_relation_schema",
        }:
            raise ArchiveProjectIRAdapterError("project_ir_provenance_not_deterministic")
        if validate_project_ir(record):
            raise ArchiveProjectIRAdapterError(
                f"project_ir_record_invalid:{record.get('project_id')}"
            )
        unit_id = record.get("archive_unit", {}).get("unit_id") if isinstance(record.get("archive_unit"), Mapping) else None
        if unit_id not in units_by_id or unit_id in records_by_unit:
            raise ArchiveProjectIRAdapterError("project_ir_unit_mapping_invalid")
        if record["archive_unit"] != units_by_id[unit_id]:
            raise ArchiveProjectIRAdapterError("project_ir_unit_snapshot_mismatch")
        if record["archive_id"] != bundle["archive_id"] or record["snapshot_id"] != bundle["snapshot_id"]:
            raise ArchiveProjectIRAdapterError("project_ir_record_provenance_mismatch")
        if record["input_hash"] != bundle["input_hash"] or record["relation_hash"] != bundle["relation_hash"]:
            raise ArchiveProjectIRAdapterError("project_ir_record_hash_mismatch")
        if record["provenance"]["unit_id"] != unit_id:
            raise ArchiveProjectIRAdapterError("project_ir_provenance_unit_mismatch")
        if record["state"] not in {"candidate", "unknown"}:
            raise ArchiveProjectIRAdapterError("project_ir_truth_promotion")
        record_member_refs = {
            str(artifact.get("artifact_ref")) for artifact in record["artifacts"]
        }
        if record_member_refs != set(units_by_id[unit_id]["member_refs"]):
            raise ArchiveProjectIRAdapterError("project_ir_member_refs_mismatch")
        records_by_unit[unit_id] = record
        project_ids.append(str(record["project_id"]))
    if len(records_by_unit) != len(units["units"]) or len(project_ids) != len(set(project_ids)):
        raise ArchiveProjectIRAdapterError("project_ir_units_not_mapped_exactly_once")

    mapping_ids: list[str] = []
    for mapping in mappings:
        if not isinstance(mapping, Mapping) or set(mapping) != _UNIT_MAP_FIELDS:
            raise ArchiveProjectIRAdapterError("unit_project_map_shape_invalid")
        unit_id = mapping["unit_id"]
        if unit_id not in units_by_id or unit_id not in records_by_unit:
            raise ArchiveProjectIRAdapterError("unit_project_map_unit_invalid")
        if mapping["project_id"] != records_by_unit[unit_id]["project_id"]:
            raise ArchiveProjectIRAdapterError("unit_project_map_project_invalid")
        if mapping["role"] != units_by_id[unit_id]["role"] or mapping["status"] != units_by_id[unit_id]["status"]:
            raise ArchiveProjectIRAdapterError("unit_project_map_semantics_invalid")
        mapping_ids.append(unit_id)
    if mapping_ids != sorted(mapping_ids) or mapping_ids != sorted(records_by_unit):
        raise ArchiveProjectIRAdapterError("unit_project_map_not_bijective")

    ambiguous = _sorted_unique(bundle["ambiguous_refs"], "bundle_ambiguous_refs")
    unassigned = _sorted_unique(bundle["unassigned_refs"], "bundle_unassigned_refs")
    if ambiguous != units["ambiguous_refs"] or unassigned != units["unassigned_refs"]:
        raise ArchiveProjectIRAdapterError("bundle_assignment_projection_mismatch")
    reconciliation = bundle["reconciliation"]
    required_reconciliation = {
        "units_input", "records_output", "unit_mappings", "unit_ids_unique",
        "units_mapped_exactly_once", "project_ids_unique", "member_refs_total",
        "member_refs_preserved", "dependency_refs_total", "dependency_refs_preserved",
        "ambiguous_refs_count", "unassigned_refs_count", "duplicates", "loss",
        "balanced", "truth_promotions", "deterministic_order",
        "ambiguous_and_unassigned_explicit",
    }
    if not isinstance(reconciliation, Mapping) or set(reconciliation) != required_reconciliation:
        raise ArchiveProjectIRAdapterError("bundle_reconciliation_field_set_invalid")
    if reconciliation["units_input"] != len(units["units"]) or reconciliation["records_output"] != len(records) or reconciliation["unit_mappings"] != len(mappings):
        raise ArchiveProjectIRAdapterError("bundle_reconciliation_counts_invalid")
    if reconciliation["duplicates"] != 0 or reconciliation["loss"] != 0 or reconciliation["balanced"] is not True:
        raise ArchiveProjectIRAdapterError("bundle_reconciliation_balance_invalid")
    if reconciliation["truth_promotions"] != 0 or reconciliation["ambiguous_and_unassigned_explicit"] is not True:
        raise ArchiveProjectIRAdapterError("bundle_reconciliation_truth_or_ambiguity_invalid")
    if reconciliation["deterministic_order"] is not True:
        raise ArchiveProjectIRAdapterError("bundle_reconciliation_order_invalid")
    return True


# Explicit aliases keep the adapter discoverable without introducing another
# API or another persistence layer.
archive_units_to_project_ir = adapt_archive_units_to_project_ir
validate_bundle = validate_project_ir_bundle


__all__ = [
    "ALGORITHM_VERSION",
    "ArchiveProjectIRAdapterError",
    "PROJECT_SCHEMA",
    "SCHEMA",
    "adapt_archive_units_to_project_ir",
    "archive_units_to_project_ir",
    "project_ir_bundle_from_units",
    "validate_bundle",
    "validate_project_ir_bundle",
]
