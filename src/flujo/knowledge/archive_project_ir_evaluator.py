"""Independent falsification gate for the Stage 2D Project IR bundle.

The evaluator consumes an already materialized Stage 2A projection, the full
Stage 2B relation payload, accepted Stage 2C units and a Stage 2D bundle.  It
does not rescan a root, open a database, infer relations, consult labels or
mutate any input.  Archive-memory physical references remain authoritative;
Project IR is only an additive, provisional view.

Canonical call shape::

    evaluate_project_ir_payload(projection, relations, units, bundle)

``assert_project_ir_payload`` has the same arguments.  A three-argument
compatibility form (projection, units, bundle) is accepted only to produce a
fail-closed report, because the independent relation hash cannot be recomputed
without the complete Stage 2B payload.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import PurePosixPath
from typing import Any, Mapping

from ._contract_helpers import stable_json as _canonical


PROJECTION_SCHEMA = "mak-archive-reconstruction-input-v1"
OBSERVER_SCHEMA = "mak-archive-observation-batch-v1"
UNIT_SCHEMA = "mak-archive-unit-reconstruction-v1"
RELATION_SCHEMA = "mak-archive-relation-candidates-v1"
PROJECT_IR_SCHEMA = "mak-project-ir-v1"
SCHEMA = "mak-archive-project-ir-bundle-v1"
REPORT_SCHEMA = "mak-archive-project-ir-evaluation-v1"

ALGORITHM_VERSION = "archive-units-to-project-ir-1"
PROJECT_ID_ALGORITHM = "archive-unit-full-digest-v1"
RELATION_HASH_ALGORITHM = "sha256-canonical-complete-relation-payload-v1"
REPORT_HASH_ALGORITHM = "sha256-canonical-report-without-report-hash-v1"

UNIT_STATUSES = frozenset({"provisional_unit", "unresolved_unit"})
ASSIGNMENT_STATUSES = frozenset({"assigned", "ambiguous", "unassigned"})
PROJECT_STATES = frozenset({"candidate", "unknown"})
RELATION_STATUSES = frozenset({"provisional", "pending_relation", "unresolved_candidate"})
UNIT_ROLES = frozenset({
    "project_unit", "subproject", "library_dependency", "shared_resource",
    "exported_product", "undecided",
})

BUNDLE_FIELDS = frozenset({
    "schema", "source_unit_schema", "target_project_ir_schema", "algorithm_version",
    "archive_id", "snapshot_id", "input_hash", "relation_hash", "records",
    "unit_project_map", "ambiguous_refs", "unassigned_refs", "reconciliation",
})
UNIT_FIELDS = frozenset({
    "unit_id", "role", "status", "root_path", "anchor_refs", "member_refs",
    "dependency_refs", "candidate_ids", "evidence_for", "evidence_against",
    "alternatives", "missing_evidence",
})
ASSIGNMENT_FIELDS = frozenset({
    "artifact_ref", "status", "unit_id", "reason_codes", "candidate_ids",
    "alternatives",
})
RECORD_REQUIRED_FIELDS = frozenset({
    "schema", "project_id", "title", "state", "source", "purpose", "domains",
    "artifacts", "relations", "evidence", "unknowns", "next_action", "provenance",
    "archive_unit", "archive_id", "snapshot_id", "input_hash", "relation_hash",
})
PROVENANCE_FIELDS = frozenset({
    "producer", "method", "archive_id", "snapshot_id", "input_hash", "relation_hash",
    "unit_id", "source_unit_schema", "source_relation_schema",
})
UNIT_MAP_FIELDS = frozenset({"unit_id", "project_id", "role", "status"})
RELATION_FIELDS = frozenset({
    "relation_id", "subject", "predicate", "object", "status", "score",
    "evidence_refs", "evidence_for", "evidence_against", "alternatives",
    "missing_evidence", "next_probe", "archive_unit_id",
})
RECONCILIATION_FIELDS = frozenset({
    "units_input", "records_output", "unit_mappings", "unit_ids_unique",
    "units_mapped_exactly_once", "project_ids_unique", "member_refs_total",
    "member_refs_preserved", "dependency_refs_total", "dependency_refs_preserved",
    "ambiguous_refs_count", "unassigned_refs_count", "duplicates", "loss",
    "balanced", "truth_promotions", "deterministic_order",
    "ambiguous_and_unassigned_explicit",
})


class ArchiveProjectIREvaluationError(ValueError):
    """Raised when a Project IR bundle fails the independent gate."""

    def __init__(self, message: str, report: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.report = dict(report) if report is not None else None


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def relation_hash_for(relations: Mapping[str, Any]) -> str:
    """Independently recompute the Stage 2B hash used by Stage 2C/2D."""

    if not isinstance(relations, Mapping):
        raise ArchiveProjectIREvaluationError("relations_not_object")
    return "sha256:" + _digest(dict(relations))


def _is_json(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _is_json(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_is_json(item) for item in value)
    return False


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _relative(value: Any, *, allow_empty: bool = False) -> bool:
    if allow_empty and value == "":
        return True
    if not _nonempty(value) or "\\" in value or value.startswith("/"):
        return False
    try:
        path = PurePosixPath(value)
    except (TypeError, ValueError):
        return False
    return path.as_posix() == value and value not in {".", ".."} and all(
        part not in {"", ".", ".."} for part in path.parts
    )


def _sorted_unique(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty(item) for item in value) and value == sorted(set(value))


def _json_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_json(item) for item in value)


def _error(errors: list[dict[str, Any]], code: str, detail: str, **metadata: Any) -> None:
    item: dict[str, Any] = {"code": code, "detail": detail}
    item.update(metadata)
    errors.append(item)


def _sorted_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(errors, key=lambda item: (
        str(item.get("code", "")), str(item.get("detail", "")),
        int(item.get("record_index", -1)), int(item.get("unit_index", -1)),
        int(item.get("assignment_index", -1)),
    ))


def project_id_for(unit_id: str) -> str:
    """Recompute the core's deterministic full-digest Project IR ID."""

    if not _nonempty(unit_id) or not unit_id.startswith("unit:"):
        raise ArchiveProjectIREvaluationError("unit_id_invalid_for_project_id")
    return "archive-unit-" + unit_id.removeprefix("unit:")


def _projection_context(projection: Any, errors: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": None, "source_schema": None, "archive_id": None,
        "snapshot_id": None, "input_hash": None, "artifact_refs": {},
        "content_ids": set(), "paths": {""}, "observation_ids": set(),
    }
    if not isinstance(projection, Mapping):
        _error(errors, "projection_not_object", "projection must be an object")
        return result
    for field in ("schema", "source_schema", "archive_id", "snapshot_id", "input_hash"):
        result[field] = projection.get(field)
    if result["schema"] != PROJECTION_SCHEMA:
        _error(errors, "projection_schema_mismatch", "projection schema is not Stage 2A")
    if result["source_schema"] != OBSERVER_SCHEMA:
        _error(errors, "projection_source_schema_mismatch", "projection source schema is not observer v1")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if not _nonempty(result[field]):
            _error(errors, f"projection_{field}_invalid", f"projection.{field} is invalid")
    artifacts = projection.get("artifacts")
    if not isinstance(artifacts, list):
        _error(errors, "projection_artifacts_invalid", "projection.artifacts must be a list")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            _error(errors, "artifact_invalid", f"artifact[{index}] is not an object", artifact_index=index)
            continue
        ref = artifact.get("artifact_ref")
        if not _nonempty(ref):
            _error(errors, "artifact_ref_invalid", f"artifact[{index}] has no artifact_ref", artifact_index=index)
            continue
        if ref in result["artifact_refs"]:
            _error(errors, "duplicate_artifact_ref", f"duplicate artifact_ref:{ref}", artifact_index=index)
            continue
        if "archive_id" in artifact and artifact.get("archive_id") != result["archive_id"]:
            _error(errors, "cross_archive_artifact", f"artifact_ref:{ref} belongs to another archive", artifact_index=index)
        relative = artifact.get("relative_path")
        if not _relative(relative, allow_empty=True):
            _error(errors, "artifact_path_invalid", f"artifact_ref:{ref} path is not relative", artifact_index=index)
        else:
            result["paths"].add(relative)
            parts = relative.split("/") if relative else []
            for end in range(1, len(parts)):
                result["paths"].add("/".join(parts[:end]))
        content_id = artifact.get("content_id")
        if _nonempty(content_id):
            result["content_ids"].add(content_id)
        result["artifact_refs"][ref] = artifact
    observations = projection.get("candidate_observations", [])
    if not isinstance(observations, list):
        _error(errors, "projection_observations_invalid", "candidate_observations must be a list")
        observations = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, Mapping) or not _nonempty(observation.get("observation_id")):
            _error(errors, "observation_invalid", f"candidate_observations[{index}] invalid", observation_index=index)
            continue
        observation_id = observation["observation_id"]
        if observation_id in result["observation_ids"]:
            _error(errors, "duplicate_observation_id", f"duplicate observation_id:{observation_id}", observation_index=index)
        result["observation_ids"].add(observation_id)
    return result


def _unit_context(
    projection: Mapping[str, Any],
    relations: Any,
    units: Any,
    projection_context: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": None, "archive_id": None, "snapshot_id": None,
        "input_hash": None, "relation_hash": None, "units": [],
        "unit_by_id": {}, "assignments": {}, "assigned": {},
        "ambiguous": set(), "unassigned": set(), "candidate_ids": set(),
        "relation_payload": relations,
    }
    if not isinstance(units, Mapping):
        _error(errors, "units_not_object", "units must be an object")
        return result
    for field in ("schema", "archive_id", "snapshot_id", "input_hash", "relation_hash"):
        result[field] = units.get(field)
    if result["schema"] != UNIT_SCHEMA:
        _error(errors, "unit_schema_mismatch", "units schema is not Stage 2C")
    if units.get("source_projection_schema") != PROJECTION_SCHEMA:
        _error(errors, "unit_source_projection_schema_mismatch", "units source projection schema is invalid")
    if units.get("source_relation_schema") != RELATION_SCHEMA:
        _error(errors, "unit_source_relation_schema_mismatch", "units source relation schema is invalid")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if units.get(field) != projection_context.get(field):
            _error(errors, f"unit_{field}_mismatch", f"units.{field} differs from Stage 2A")
    if isinstance(relations, Mapping):
        if relations.get("schema") != RELATION_SCHEMA:
            _error(errors, "relation_schema_mismatch", "relations schema is not Stage 2B")
        if relations.get("source_schema") != PROJECTION_SCHEMA:
            _error(errors, "relation_source_schema_mismatch", "relations source schema is not Stage 2A")
        for field in ("archive_id", "snapshot_id", "input_hash"):
            if relations.get(field) != projection_context.get(field):
                _error(errors, f"relation_{field}_mismatch", f"relations.{field} differs from Stage 2A")
        expected_relation_hash = relation_hash_for(relations)
        if units.get("relation_hash") != expected_relation_hash:
            _error(errors, "unit_relation_hash_mismatch", "units relation_hash is not the full Stage 2B hash")
        candidates = relations.get("candidates", [])
        if isinstance(candidates, list):
            result["candidate_ids"] = {
                str(candidate.get("candidate_id")) for candidate in candidates
                if isinstance(candidate, Mapping) and _nonempty(candidate.get("candidate_id"))
            }
    else:
        _error(errors, "relations_missing_for_hash", "complete Stage 2B payload is required for independent hash recomputation")
    if not _nonempty(units.get("relation_hash")):
        _error(errors, "unit_relation_hash_invalid", "units relation_hash is missing")

    artifact_refs = set(projection_context.get("artifact_refs", {}))
    content_ids = set(projection_context.get("content_ids", set()))
    paths = set(projection_context.get("paths", {""}))
    raw_units = units.get("units")
    if not isinstance(raw_units, list):
        _error(errors, "units_list_invalid", "units.units must be a list")
        raw_units = []
    result["units"] = raw_units
    unit_ids: list[str] = []
    for index, raw in enumerate(raw_units):
        if not isinstance(raw, Mapping) or set(raw) != UNIT_FIELDS:
            _error(errors, "unit_fields_invalid", f"unit[{index}] fields are not canonical", unit_index=index)
            continue
        unit = dict(raw)
        unit_id = unit.get("unit_id")
        if not _nonempty(unit_id):
            _error(errors, "unit_id_invalid", f"unit[{index}] unit_id invalid", unit_index=index)
        else:
            unit_ids.append(unit_id)
        if unit.get("status") not in UNIT_STATUSES:
            _error(errors, "unit_promoted_status", f"unit[{index}] status is invalid/promoted", unit_index=index)
        if unit.get("role") not in UNIT_ROLES:
            _error(errors, "unit_role_invalid", f"unit[{index}] role is invalid", unit_index=index)
        if not _relative(unit.get("root_path"), allow_empty=True) or unit.get("root_path") not in paths:
            _error(errors, "unit_root_path_invalid", f"unit[{index}] root_path is not observed", unit_index=index)
        for field in ("anchor_refs", "member_refs", "dependency_refs", "candidate_ids"):
            if not _sorted_unique(unit.get(field)):
                _error(errors, "unit_list_invalid", f"unit[{index}].{field} is not sorted unique", unit_index=index)
        for candidate_id in unit.get("candidate_ids", []) if isinstance(unit.get("candidate_ids"), list) else []:
            if result["candidate_ids"] and candidate_id not in result["candidate_ids"]:
                _error(errors, "unit_candidate_id_dangling", f"unit[{index}] candidate_id unresolved:{candidate_id}", unit_index=index)
        for field in ("evidence_for", "evidence_against", "alternatives", "missing_evidence"):
            if not _json_list(unit.get(field)):
                _error(errors, "unit_evidence_invalid", f"unit[{index}].{field} is not a JSON list", unit_index=index)
        refs = set(unit.get("anchor_refs", [])) | set(unit.get("member_refs", [])) | set(unit.get("dependency_refs", []))
        if not set(unit.get("anchor_refs", [])).issubset(set(unit.get("member_refs", []))):
            _error(errors, "unit_anchor_membership_invalid", f"unit[{index}] anchor is not member", unit_index=index)
        if set(unit.get("member_refs", [])) & set(unit.get("dependency_refs", [])):
            _error(errors, "unit_member_dependency_overlap", f"unit[{index}] member/dependency overlap", unit_index=index)
        for ref in refs:
            if ref in content_ids:
                _error(errors, "unit_content_id_endpoint", f"unit[{index}] uses content_id:{ref}", unit_index=index)
            elif ref not in artifact_refs:
                _error(errors, "unit_ref_dangling", f"unit[{index}] uses unknown artifact_ref:{ref}", unit_index=index)
        expected_id = None
        if _nonempty(units.get("archive_id")) and _nonempty(units.get("snapshot_id")):
            semantic = {
                "archive_id": units["archive_id"], "snapshot_id": units["snapshot_id"],
                "role": unit.get("role"), "root_path": unit.get("root_path"),
                "anchor_refs": sorted(set(unit.get("anchor_refs", []))),
            }
            if _is_json(semantic):
                expected_id = "unit:" + _digest(semantic)
        if expected_id != unit_id:
            _error(errors, "unit_id_mismatch", f"unit[{index}] unit_id is not canonical", unit_index=index)
        if unit_id in result["unit_by_id"]:
            _error(errors, "duplicate_unit_id", f"duplicate unit_id:{unit_id}", unit_index=index)
        else:
            result["unit_by_id"][unit_id] = unit
        result["candidate_ids"].update(unit.get("candidate_ids", []))
    if unit_ids != sorted(unit_ids) or len(unit_ids) != len(set(unit_ids)):
        _error(errors, "unit_order_or_duplicate", "units must be sorted and unique by unit_id")

    raw_assignments = units.get("assignments")
    if not isinstance(raw_assignments, list):
        _error(errors, "assignments_invalid", "units.assignments must be a list")
        raw_assignments = []
    assignment_refs: list[str] = []
    for index, raw in enumerate(raw_assignments):
        if not isinstance(raw, Mapping) or set(raw) != ASSIGNMENT_FIELDS:
            _error(errors, "assignment_fields_invalid", f"assignment[{index}] fields are not canonical", assignment_index=index)
            continue
        assignment = dict(raw)
        ref = assignment.get("artifact_ref")
        assignment_refs.append(ref)
        if ref not in artifact_refs:
            _error(errors, "assignment_ref_dangling", f"assignment[{index}] ref is not physical", assignment_index=index)
        if ref in content_ids:
            _error(errors, "assignment_content_id_endpoint", f"assignment[{index}] uses content_id", assignment_index=index)
        if assignment.get("status") not in ASSIGNMENT_STATUSES:
            _error(errors, "assignment_status_invalid", f"assignment[{index}] status invalid", assignment_index=index)
        for field in ("reason_codes", "candidate_ids"):
            if not _sorted_unique(assignment.get(field)):
                _error(errors, "assignment_list_invalid", f"assignment[{index}].{field} is not sorted unique", assignment_index=index)
        if not _json_list(assignment.get("alternatives")):
            _error(errors, "assignment_alternatives_invalid", f"assignment[{index}].alternatives invalid", assignment_index=index)
        for candidate_id in assignment.get("candidate_ids", []) if isinstance(assignment.get("candidate_ids"), list) else []:
            if result["candidate_ids"] and candidate_id not in result["candidate_ids"]:
                _error(errors, "assignment_candidate_id_dangling", f"assignment[{index}] candidate_id unresolved:{candidate_id}", assignment_index=index)
        status = assignment.get("status")
        unit_id = assignment.get("unit_id")
        if status == "assigned":
            if unit_id not in result["unit_by_id"]:
                _error(errors, "assigned_unit_missing", f"assignment[{index}] unit missing", assignment_index=index)
            elif ref not in set(result["unit_by_id"][unit_id].get("member_refs", [])):
                _error(errors, "assigned_membership_mismatch", f"assignment[{index}] ref is not unit member", assignment_index=index)
            result["assigned"][ref] = unit_id
        elif status == "ambiguous":
            if unit_id is not None or not isinstance(assignment.get("alternatives"), list) or len(assignment["alternatives"]) < 2:
                _error(errors, "ambiguous_assignment_invalid", f"assignment[{index}] ambiguous form invalid", assignment_index=index)
            result["ambiguous"].add(ref)
        elif status == "unassigned":
            if unit_id is not None:
                _error(errors, "unassigned_unit_present", f"assignment[{index}] has unit_id", assignment_index=index)
            result["unassigned"].add(ref)
        if ref in result["assignments"]:
            _error(errors, "duplicate_assignment", f"duplicate assignment:{ref}", assignment_index=index)
        else:
            result["assignments"][ref] = assignment
    if assignment_refs != sorted(assignment_refs):
        _error(errors, "assignment_order_invalid", "assignments must be sorted by artifact_ref")
    if set(assignment_refs) != artifact_refs or len(assignment_refs) != len(set(assignment_refs)):
        _error(errors, "assignment_partition_unbalanced", "assignments do not cover artifacts exactly once")
    for field, expected in (("unassigned_refs", result["unassigned"]), ("ambiguous_refs", result["ambiguous"])):
        values = units.get(field)
        if not _sorted_unique(values):
            _error(errors, f"{field}_invalid", f"units.{field} must be sorted unique")
        elif set(values) != expected:
            _error(errors, f"{field}_mismatch", f"units.{field} disagrees with assignments")

    reconciliation = units.get("reconciliation")
    if not isinstance(reconciliation, Mapping):
        _error(errors, "unit_reconciliation_invalid", "Stage 2C reconciliation is missing")
    else:
        role_counts: dict[str, int] = {}
        for unit in result["unit_by_id"].values():
            role = str(unit.get("role"))
            role_counts[role] = role_counts.get(role, 0) + 1
        relation_candidate_count = len(relations.get("candidates", [])) if isinstance(relations, Mapping) and isinstance(relations.get("candidates"), list) else 0
        expected = {
            "total_artifacts": len(artifact_refs), "assigned": len(result["assigned"]),
            "ambiguous": len(result["ambiguous"]), "unassigned": len(result["unassigned"]),
            "unit_count": len(result["unit_by_id"]), "assignment_count": len(raw_assignments),
            "units_by_role": dict(sorted(role_counts.items())),
            "duplicates": len(assignment_refs) - len(set(assignment_refs)),
            "loss": len(artifact_refs - set(assignment_refs)),
            "balanced": set(assignment_refs) == artifact_refs and len(assignment_refs) == len(set(assignment_refs)),
            "truth_promotions": 0, "relation_candidate_count": relation_candidate_count,
            "unit_status_values": ["provisional_unit", "unresolved_unit"],
        }
        required_reconciliation = {
            "total_artifacts", "assigned", "ambiguous", "unassigned", "unit_count",
            "units_by_role", "assignment_count", "duplicates", "loss", "balanced",
            "truth_promotions", "relation_candidate_count", "unit_status_values",
        }
        if set(reconciliation) != required_reconciliation:
            _error(errors, "unit_reconciliation_field_set_invalid", "Stage 2C reconciliation keys are not canonical")
        for field, expected_value in expected.items():
            if reconciliation.get(field) != expected_value:
                _error(errors, "unit_reconciliation_mismatch", f"units.reconciliation.{field} differs", field=field)
    return result


def _record_evidence_refs(record: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for evidence in record.get("evidence", []) if isinstance(record.get("evidence"), list) else []:
        if not isinstance(evidence, Mapping):
            continue
        for key in ("artifact_ref", "observation_id", "candidate_id"):
            value = evidence.get(key)
            if isinstance(value, str):
                refs.add(value)
        for key in ("artifact_refs", "observation_ids", "candidate_ids", "evidence_refs"):
            value = evidence.get(key)
            if isinstance(value, list):
                refs.update(item for item in value if isinstance(item, str))
    return refs


def _validate_record(
    record: Any,
    index: int,
    projection_context: Mapping[str, Any],
    unit_context: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(record, Mapping):
        _error(errors, "project_record_invalid", f"record[{index}] is not object", record_index=index)
        return None
    missing = sorted(RECORD_REQUIRED_FIELDS - set(record))
    if missing:
        _error(errors, "project_record_fields_missing", f"record[{index}] missing:{','.join(missing)}", record_index=index)
    if record.get("schema") != PROJECT_IR_SCHEMA:
        _error(errors, "project_record_schema_invalid", f"record[{index}] schema invalid", record_index=index)
    project_id = record.get("project_id")
    if not _nonempty(project_id):
        _error(errors, "project_id_invalid", f"record[{index}] project_id invalid", record_index=index)
    if not _nonempty(record.get("title")):
        _error(errors, "project_title_invalid", f"record[{index}] title invalid", record_index=index)
    if not isinstance(record.get("purpose"), str):
        _error(errors, "project_purpose_invalid", f"record[{index}] purpose invalid", record_index=index)
    state = record.get("state")
    if state not in PROJECT_STATES:
        _error(errors, "project_truth_promoted", f"record[{index}] state:{state}", record_index=index)
    if record.get("next_action") != "preserve_provisional_status":
        _error(errors, "mandatory_review_semantics_missing", f"record[{index}] next_action is not preserve_provisional_status", record_index=index)
    for field in ("domains", "artifacts", "relations", "evidence", "unknowns"):
        if not isinstance(record.get(field), list):
            _error(errors, "project_record_list_invalid", f"record[{index}].{field} must be list", record_index=index)
    source = record.get("source")
    if not isinstance(source, Mapping) or not _nonempty(source.get("kind")) or not _nonempty(source.get("root_ref")):
        _error(errors, "project_source_invalid", f"record[{index}] source.root_ref missing", record_index=index)
    elif str(source.get("root_ref")).startswith("/"):
        _error(errors, "project_source_absolute", f"record[{index}] source root is absolute", record_index=index)
    if not isinstance(record.get("evidence"), list) or not record.get("evidence"):
        _error(errors, "project_evidence_missing", f"record[{index}] evidence is empty", record_index=index)
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping) or set(provenance) != PROVENANCE_FIELDS:
        _error(errors, "project_provenance_shape_invalid", f"record[{index}] provenance is not canonical", record_index=index)
        provenance = {}
    for field in ("archive_id", "snapshot_id", "input_hash", "relation_hash"):
        if provenance.get(field) != projection_context.get(field) and field != "relation_hash":
            _error(errors, f"project_{field}_mismatch", f"record[{index}] provenance.{field} differs", record_index=index)
    if provenance.get("relation_hash") != unit_context.get("relation_hash"):
        _error(errors, "project_relation_hash_mismatch", f"record[{index}] provenance relation_hash differs", record_index=index)
    if provenance.get("source_unit_schema") != UNIT_SCHEMA or provenance.get("source_relation_schema") != RELATION_SCHEMA:
        _error(errors, "project_provenance_source_schema_invalid", f"record[{index}] provenance source schema differs", record_index=index)
    if not _nonempty(provenance.get("producer")) or not _nonempty(provenance.get("method")):
        _error(errors, "project_provenance_identity_invalid", f"record[{index}] provenance producer/method missing", record_index=index)
    unit_id = provenance.get("unit_id")
    unit = unit_context.get("unit_by_id", {}).get(unit_id)
    if unit is None:
        _error(errors, "project_unit_mapping_invalid", f"record[{index}] unit_id is not Stage 2C", record_index=index)
    else:
        if record.get("archive_unit") != unit:
            _error(errors, "project_archive_unit_loss", f"record[{index}] archive_unit differs from Stage 2C", record_index=index)
        expected_state = "candidate" if unit.get("status") == "provisional_unit" else "unknown"
        if state != expected_state:
            _error(errors, "project_state_provenance_mismatch", f"record[{index}] state does not preserve unit status", record_index=index)
    if record.get("archive_id") != projection_context.get("archive_id") or record.get("snapshot_id") != projection_context.get("snapshot_id"):
        _error(errors, "project_record_provenance_mismatch", f"record[{index}] archive/snapshot differs", record_index=index)
    if record.get("input_hash") != projection_context.get("input_hash") or record.get("relation_hash") != unit_context.get("relation_hash"):
        _error(errors, "project_record_hash_mismatch", f"record[{index}] hash differs", record_index=index)
    if provenance.get("unit_id") != (record.get("source", {}).get("unit_id") if isinstance(record.get("source"), Mapping) else None):
        _error(errors, "project_source_unit_mismatch", f"record[{index}] source unit differs", record_index=index)
    if isinstance(source, Mapping) and (
        source.get("archive_id") != projection_context.get("archive_id")
        or source.get("snapshot_id") != projection_context.get("snapshot_id")
        or source.get("unit_id") != unit_id
    ):
        _error(errors, "project_source_provenance_mismatch", f"record[{index}] source provenance differs", record_index=index)
    if _nonempty(unit_id):
        try:
            expected_id = project_id_for(unit_id)
        except ArchiveProjectIREvaluationError:
            expected_id = None
        if project_id != expected_id:
            _error(errors, "project_id_mismatch", f"record[{index}] project_id is not canonical", record_index=index)

    physical = set(projection_context.get("artifact_refs", {}))
    content_ids = set(projection_context.get("content_ids", set()))
    member_refs: set[str] = set()
    for artifact_index, artifact in enumerate(record.get("artifacts", []) if isinstance(record.get("artifacts"), list) else []):
        if not isinstance(artifact, Mapping):
            _error(errors, "project_artifact_invalid", f"record[{index}] artifact[{artifact_index}] is not object", record_index=index)
            continue
        ref = artifact.get("artifact_ref")
        if not _nonempty(ref):
            _error(errors, "project_artifact_ref_invalid", f"record[{index}] artifact has no ref", record_index=index)
            continue
        member_refs.add(ref)
        if ref in content_ids:
            _error(errors, "project_content_id_endpoint", f"record[{index}] artifact uses content_id:{ref}", record_index=index)
        if ref not in physical:
            _error(errors, "project_nonphysical_ref", f"record[{index}] artifact ref is not physical:{ref}", record_index=index)
        source_artifact = projection_context["artifact_refs"].get(ref)
        if source_artifact is not None and artifact.get("relative_path") != source_artifact.get("relative_path"):
            _error(errors, "project_artifact_path_mismatch", f"record[{index}] artifact path differs:{ref}", record_index=index)
        if source_artifact is not None and "physical_id" in artifact and artifact.get("physical_id") != source_artifact.get("physical_id"):
            _error(errors, "project_physical_id_mismatch", f"record[{index}] physical_id differs:{ref}", record_index=index)
    if len(member_refs) != len(record.get("artifacts", [])):
        _error(errors, "project_duplicate_artifact_ref", f"record[{index}] repeats a physical artifact ref", record_index=index)
    if isinstance(unit, Mapping) and member_refs != set(unit.get("member_refs", [])):
        _error(errors, "project_member_refs_mismatch", f"record[{index}] member refs are not lossless", record_index=index)
    archive_evidence = [
        evidence for evidence in record.get("evidence", [])
        if isinstance(evidence, Mapping) and evidence.get("kind") == "archive_unit_provenance"
    ]
    if not archive_evidence:
        _error(errors, "project_archive_evidence_missing", f"record[{index}] archive provenance evidence missing", record_index=index)
    else:
        witness = archive_evidence[0]
        for field, expected in (
            ("archive_id", projection_context.get("archive_id")),
            ("snapshot_id", projection_context.get("snapshot_id")),
            ("input_hash", projection_context.get("input_hash")),
            ("relation_hash", unit_context.get("relation_hash")),
            ("unit_id", unit_id),
        ):
            if witness.get(field) != expected:
                _error(errors, "project_archive_evidence_mismatch", f"record[{index}] evidence.{field} differs", record_index=index)
    return {"record": record, "unit_id": unit_id, "unit": unit, "project_id": project_id, "member_refs": member_refs}


def _validate_relations(
    record: Mapping[str, Any],
    item: Mapping[str, Any],
    projection_context: Mapping[str, Any],
    unit_context: Mapping[str, Any],
    errors: list[dict[str, Any]],
    record_index: int,
) -> tuple[set[str], set[str]]:
    physical = set(projection_context.get("artifact_refs", {}))
    content_ids = set(projection_context.get("content_ids", set()))
    blocked = set(unit_context.get("ambiguous", set())) | set(unit_context.get("unassigned", set()))
    member_refs: set[str] = set()
    dependency_refs: set[str] = set()
    relations = record.get("relations", [])
    relation_ids: list[str] = []
    for relation_index, relation in enumerate(relations if isinstance(relations, list) else []):
        if not isinstance(relation, Mapping) or set(relation) != RELATION_FIELDS:
            _error(errors, "project_relation_shape_invalid", f"record[{record_index}] relation[{relation_index}] shape invalid", record_index=record_index)
            continue
        relation_id = relation.get("relation_id")
        relation_ids.append(str(relation_id))
        if relation.get("archive_unit_id") != item.get("unit_id"):
            _error(errors, "project_relation_unit_mismatch", f"record[{record_index}] relation unit differs", record_index=record_index)
        if relation.get("status") not in RELATION_STATUSES:
            _error(errors, "project_relation_truth_promoted", f"record[{record_index}] relation status invalid", record_index=record_index)
        if relation.get("score") is not None and (not isinstance(relation.get("score"), (int, float)) or not math.isfinite(float(relation["score"]))):
            _error(errors, "project_relation_score_invalid", f"record[{record_index}] relation score invalid", record_index=record_index)
        subject = relation.get("subject")
        object_ref = relation.get("object")
        predicate = relation.get("predicate")
        if predicate in {"provisional_member", "provisional_dependency"}:
            if subject != record.get("project_id"):
                _error(errors, "project_relation_subject_invalid", f"record[{record_index}] relation subject invalid", record_index=record_index)
            if object_ref not in physical:
                _error(errors, "project_relation_endpoint_invalid", f"record[{record_index}] physical relation object invalid", record_index=record_index)
        elif subject not in physical or object_ref not in physical:
            _error(errors, "project_relation_endpoint_invalid", f"record[{record_index}] candidate relation endpoint invalid", record_index=record_index)
        elif relation_id not in set(unit_context.get("candidate_ids", set())):
            _error(errors, "project_relation_candidate_dangling", f"record[{record_index}] candidate relation is not in Stage 2B", record_index=record_index)
        if object_ref in content_ids:
            _error(errors, "project_content_id_endpoint", f"record[{record_index}] relation uses content_id:{object_ref}", record_index=record_index)
        if object_ref in blocked:
            _error(errors, "project_ambiguous_unassigned_fabrication", f"record[{record_index}] relation uses unresolved ref:{object_ref}", record_index=record_index)
        if subject in blocked:
            _error(errors, "project_ambiguous_unassigned_fabrication", f"record[{record_index}] relation uses unresolved subject:{subject}", record_index=record_index)
        for field in ("evidence_refs",):
            values = relation.get(field)
            if not _sorted_unique(values):
                _error(errors, "project_relation_evidence_invalid", f"record[{record_index}] relation evidence is not sorted unique", record_index=record_index)
            else:
                valid_evidence = physical | set(unit_context.get("candidate_ids", set())) | set(projection_context.get("observation_ids", set()))
                for ref in values:
                    if ref not in valid_evidence:
                        _error(errors, "project_relation_evidence_dangling", f"record[{record_index}] relation evidence unresolved:{ref}", record_index=record_index)
        for field in ("evidence_for", "evidence_against", "alternatives", "missing_evidence"):
            if not _json_list(relation.get(field)):
                _error(errors, "project_relation_annotation_invalid", f"record[{record_index}] relation {field} invalid", record_index=record_index)
        if predicate == "provisional_member":
            member_refs.add(object_ref)
        elif predicate == "provisional_dependency":
            dependency_refs.add(object_ref)
    if relation_ids != sorted(relation_ids) or len(relation_ids) != len(set(relation_ids)):
        _error(errors, "project_relation_order_invalid", f"record[{record_index}] relations must be sorted unique", record_index=record_index)
    return member_refs, dependency_refs


def _normalize_arguments(
    projection: Mapping[str, Any],
    relations_or_units: Mapping[str, Any],
    units_or_payload: Mapping[str, Any],
    payload: Mapping[str, Any] | None,
) -> tuple[Any, Any, Any, bool]:
    if payload is None:
        return None, relations_or_units, units_or_payload, False
    return relations_or_units, units_or_payload, payload, True


def evaluate_project_ir_payload(
    projection: Mapping[str, Any],
    relations_or_units: Mapping[str, Any],
    units_or_payload: Mapping[str, Any],
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic independent report for a Stage 2D bundle."""

    relations, units, bundle, has_relations = _normalize_arguments(projection, relations_or_units, units_or_payload, payload)
    projection_errors: list[dict[str, Any]] = []
    projection_context = _projection_context(projection, projection_errors)
    unit_errors: list[dict[str, Any]] = []
    unit_context = _unit_context(projection, relations, units, projection_context, unit_errors)
    bundle_errors: list[dict[str, Any]] = []
    if not isinstance(bundle, Mapping):
        _error(bundle_errors, "bundle_not_object", "bundle must be an object")
        bundle = {}
    if set(bundle) != BUNDLE_FIELDS:
        _error(bundle_errors, "bundle_field_set_invalid", "bundle field set is not canonical")
    for field, expected in (
        ("schema", SCHEMA), ("source_unit_schema", UNIT_SCHEMA),
        ("target_project_ir_schema", PROJECT_IR_SCHEMA), ("algorithm_version", ALGORITHM_VERSION),
    ):
        if bundle.get(field) != expected:
            _error(bundle_errors, "bundle_schema_or_algorithm_invalid", f"bundle.{field} differs")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if bundle.get(field) != projection_context.get(field):
            _error(bundle_errors, f"bundle_{field}_mismatch", f"bundle.{field} differs from Stage 2A")
    if bundle.get("relation_hash") != unit_context.get("relation_hash"):
        _error(bundle_errors, "bundle_relation_hash_mismatch", "bundle relation_hash differs from Stage 2C")
    if has_relations is False:
        _error(bundle_errors, "relations_missing_for_hash", "full Stage 2B payload was not supplied")
    records = bundle.get("records")
    mappings = bundle.get("unit_project_map")
    if not isinstance(records, list):
        _error(bundle_errors, "bundle_records_invalid", "bundle.records must be a list")
        records = []
    if not isinstance(mappings, list):
        _error(bundle_errors, "bundle_map_invalid", "bundle.unit_project_map must be a list")
        mappings = []
    project_items: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        item = _validate_record(record, index, {**projection_context, "relation_hash": unit_context.get("relation_hash")}, unit_context, bundle_errors)
        if item is not None:
            project_items.append(item)
    project_ids = [str(item.get("project_id", "")) for item in project_items]
    if project_ids != sorted(project_ids):
        _error(bundle_errors, "project_record_order_invalid", "records must be sorted by project_id")
    if len(project_ids) != len(set(project_ids)):
        _error(bundle_errors, "duplicate_project_id", "project IDs must be unique")
    records_by_unit: dict[str, dict[str, Any]] = {}
    for item in project_items:
        unit_id = item.get("unit_id")
        if unit_id in records_by_unit:
            _error(bundle_errors, "duplicate_unit_projection", f"unit projected twice:{unit_id}")
        else:
            records_by_unit[unit_id] = item
        member_relation_refs, dependency_relation_refs = _validate_relations(
            item["record"], item, projection_context, unit_context, bundle_errors, project_items.index(item)
        )
        item["relation_member_refs"] = member_relation_refs
        item["relation_dependency_refs"] = dependency_relation_refs
        if member_relation_refs != item["member_refs"]:
            _error(bundle_errors, "project_member_refs_mismatch", f"unit:{unit_id} member refs are not lossless")
        expected_dependencies = set(item["unit"].get("dependency_refs", [])) if isinstance(item.get("unit"), Mapping) else set()
        if dependency_relation_refs != expected_dependencies:
            _error(bundle_errors, "project_dependency_refs_mismatch", f"unit:{unit_id} dependency refs are not lossless")

    unit_ids = set(unit_context.get("unit_by_id", {}))
    projected_unit_ids = set(records_by_unit)
    for unit_id in sorted(unit_ids - projected_unit_ids):
        _error(bundle_errors, "missing_unit_projection", f"Stage 2C unit missing from Project IR:{unit_id}")
    for unit_id in sorted(projected_unit_ids - unit_ids):
        _error(bundle_errors, "fabricated_unit_projection", f"Project IR unit is not in Stage 2C:{unit_id}")

    mapping_ids: list[str] = []
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, Mapping) or set(mapping) != UNIT_MAP_FIELDS:
            _error(bundle_errors, "unit_project_map_shape_invalid", f"map[{index}] shape invalid")
            continue
        mapping_ids.append(str(mapping.get("unit_id")))
        unit_id = mapping.get("unit_id")
        if unit_id not in unit_context.get("unit_by_id", {}) or unit_id not in records_by_unit:
            _error(bundle_errors, "unit_project_map_unit_invalid", f"map[{index}] unit invalid")
            continue
        item = records_by_unit[unit_id]
        unit = unit_context["unit_by_id"][unit_id]
        if mapping.get("project_id") != item.get("project_id"):
            _error(bundle_errors, "unit_project_map_project_invalid", f"map[{index}] project ID differs")
        if mapping.get("role") != unit.get("role") or mapping.get("status") != unit.get("status"):
            _error(bundle_errors, "unit_project_map_semantics_invalid", f"map[{index}] role/status differs")
    if mapping_ids != sorted(mapping_ids) or mapping_ids != sorted(unit_ids) or len(mapping_ids) != len(set(mapping_ids)):
        _error(bundle_errors, "unit_project_map_not_bijective", "unit_project_map is not sorted and bijective")

    for field in ("ambiguous_refs", "unassigned_refs"):
        values = bundle.get(field)
        expected = set(unit_context.get("ambiguous" if field.startswith("ambiguous") else "unassigned", set()))
        if not _sorted_unique(values):
            _error(bundle_errors, "bundle_assignment_refs_invalid", f"bundle.{field} invalid")
        elif values != sorted(expected):
            _error(bundle_errors, "bundle_assignment_projection_mismatch", f"bundle.{field} differs from Stage 2C")
    unresolved = set(unit_context.get("ambiguous", set())) | set(unit_context.get("unassigned", set()))
    for item in project_items:
        if item["member_refs"] & unresolved:
            _error(bundle_errors, "project_ambiguous_unassigned_fabrication", f"unit:{item.get('unit_id')} fabricates unresolved members")

    expected_reconciliation = {
        "units_input": len(unit_context.get("unit_by_id", {})),
        "records_output": len(records),
        "unit_mappings": len(mappings),
        "unit_ids_unique": len(unit_ids) == len(unit_context.get("unit_by_id", {})),
        "units_mapped_exactly_once": len(records) == len(unit_ids) == len(mappings) and not (unit_ids - projected_unit_ids),
        "project_ids_unique": len(project_ids) == len(set(project_ids)),
        "member_refs_total": sum(len(unit.get("member_refs", [])) for unit in unit_context.get("unit_by_id", {}).values()),
        "member_refs_preserved": all(
            set(item.get("member_refs", set())) == set(item.get("unit", {}).get("member_refs", []))
            for item in project_items if isinstance(item.get("unit"), Mapping)
        ) and not any(error["code"] == "project_member_refs_mismatch" for error in bundle_errors),
        "dependency_refs_total": sum(len(unit.get("dependency_refs", [])) for unit in unit_context.get("unit_by_id", {}).values()),
        "dependency_refs_preserved": all(
            set(item.get("relation_dependency_refs", set())) == set(item.get("unit", {}).get("dependency_refs", []))
            for item in project_items if isinstance(item.get("unit"), Mapping)
        ) and not any(error["code"] == "project_dependency_refs_mismatch" for error in bundle_errors),
        "ambiguous_refs_count": len(unit_context.get("ambiguous", set())),
        "unassigned_refs_count": len(unit_context.get("unassigned", set())),
        "duplicates": len(unit_ids) - len(set(unit_ids)),
        "loss": len(unit_ids - projected_unit_ids),
        "balanced": len(records) == len(unit_context.get("unit_by_id", {})) and len(mappings) == len(records) and not (unit_ids - projected_unit_ids),
        "truth_promotions": sum(1 for item in project_items if item["record"].get("state") not in PROJECT_STATES),
        "deterministic_order": records == sorted(records, key=lambda item: item.get("project_id", "")) and mappings == sorted(mappings, key=lambda item: item.get("unit_id", "")),
        "ambiguous_and_unassigned_explicit": True,
    }
    reconciliation = bundle.get("reconciliation")
    if not isinstance(reconciliation, Mapping) or set(reconciliation) != RECONCILIATION_FIELDS:
        _error(bundle_errors, "bundle_reconciliation_field_set_invalid", "bundle reconciliation keys are not canonical")
    else:
        for field, expected in expected_reconciliation.items():
            if reconciliation.get(field) != expected:
                _error(bundle_errors, "bundle_reconciliation_mismatch", f"bundle reconciliation.{field} differs", field=field)

    errors = _sorted_errors(projection_errors + unit_errors + bundle_errors)
    checks = {
        "upstream_schema_hash_archive_match": {"passed": not any(error["code"] in {"projection_schema_mismatch", "projection_source_schema_mismatch", "unit_schema_mismatch", "unit_source_projection_schema_mismatch", "unit_source_relation_schema_mismatch", "unit_archive_id_mismatch", "unit_snapshot_id_mismatch", "unit_input_hash_mismatch", "unit_relation_hash_mismatch", "relation_schema_mismatch", "relation_source_schema_mismatch", "relation_archive_id_mismatch", "relation_snapshot_id_mismatch", "relation_input_hash_mismatch", "bundle_archive_id_mismatch", "bundle_snapshot_id_mismatch", "bundle_input_hash_mismatch", "bundle_relation_hash_mismatch", "relations_missing_for_hash"} for error in errors)},
        "unit_projections": {"passed": not any(error["code"] in {"missing_unit_projection", "fabricated_unit_projection", "duplicate_unit_projection", "unit_project_map_not_bijective"} for error in errors)},
        "project_ir_records": {"passed": not any(error["code"].startswith("project_record") or error["code"] in {"project_id_invalid", "project_id_mismatch", "project_truth_promoted"} for error in errors)},
        "physical_refs": {"passed": not any(error["code"] in {"unit_ref_dangling", "unit_content_id_endpoint", "assignment_ref_dangling", "assignment_content_id_endpoint", "project_nonphysical_ref", "project_content_id_endpoint", "project_relation_endpoint_invalid", "project_ambiguous_unassigned_fabrication"} for error in errors)},
        "member_dependency_preservation": {"passed": not any(error["code"] in {"project_member_refs_mismatch", "project_dependency_refs_mismatch", "project_archive_unit_loss"} for error in errors)},
        "evidence_provenance": {"passed": not any(error["code"] in {"project_provenance_shape_invalid", "project_evidence_missing", "project_relation_evidence_dangling", "project_relation_evidence_invalid"} for error in errors)},
        "mandatory_review_no_truth_promotion": {"passed": not any(error["code"] in {"project_truth_promoted", "mandatory_review_semantics_missing", "project_relation_truth_promoted"} for error in errors)},
        "deterministic_ids_order": {"passed": not any(error["code"] in {"project_id_mismatch", "project_record_order_invalid", "project_relation_order_invalid", "unit_order_or_duplicate", "unit_project_map_not_bijective"} for error in errors)},
        "reconciliation": {"passed": not any(error["code"].startswith("bundle_reconciliation") for error in errors)},
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "algorithm_version": "archive-project-ir-evaluator-v2",
        "project_id_algorithm": PROJECT_ID_ALGORITHM,
        "relation_hash_algorithm": RELATION_HASH_ALGORITHM,
        "report_hash_algorithm": REPORT_HASH_ALGORITHM,
        "source": {
            "projection_schema": projection_context.get("schema"),
            "relation_schema": relations.get("schema") if isinstance(relations, Mapping) else None,
            "unit_schema": unit_context.get("schema"),
            "bundle_schema": bundle.get("schema"),
            "project_ir_schema": PROJECT_IR_SCHEMA,
            "archive_id": projection_context.get("archive_id"),
            "snapshot_id": projection_context.get("snapshot_id"),
            "input_hash": projection_context.get("input_hash"),
            "relation_hash": unit_context.get("relation_hash"),
        },
        "checks": checks,
        "metrics": {
            "artifact_count": len(projection_context.get("artifact_refs", {})),
            "unit_count": len(unit_context.get("unit_by_id", {})),
            "record_count": len(records),
            "mapping_count": len(mappings),
            "ambiguous_count": len(unit_context.get("ambiguous", set())),
            "unassigned_count": len(unit_context.get("unassigned", set())),
        },
        "errors": errors,
    }
    report["passed"] = not errors and all(check["passed"] for check in checks.values())
    report["valid"] = bool(report["passed"])
    report["status"] = "pass" if report["valid"] else "fail"
    report["report_hash"] = "report:" + _digest(report)
    return report


def assert_project_ir_payload(
    projection: Mapping[str, Any],
    relations_or_units: Mapping[str, Any],
    units_or_payload: Mapping[str, Any],
    payload: Mapping[str, Any] | None = None,
) -> bool:
    """Return ``True`` or raise with the complete deterministic report."""

    report = evaluate_project_ir_payload(projection, relations_or_units, units_or_payload, payload)
    if not report["valid"]:
        codes = ",".join(error["code"] for error in report["errors"])
        raise ArchiveProjectIREvaluationError(f"archive_project_ir_rejected:{codes}", report)
    return True


evaluate_archive_project_ir = evaluate_project_ir_payload
assert_archive_project_ir = assert_project_ir_payload


__all__ = [
    "ALGORITHM_VERSION", "ArchiveProjectIREvaluationError", "BUNDLE_FIELDS",
    "PROJECT_ID_ALGORITHM", "PROJECT_IR_SCHEMA", "RELATION_HASH_ALGORITHM",
    "REPORT_SCHEMA", "SCHEMA", "assert_archive_project_ir", "assert_project_ir_payload",
    "evaluate_archive_project_ir", "evaluate_project_ir_payload", "project_id_for",
    "relation_hash_for",
]
