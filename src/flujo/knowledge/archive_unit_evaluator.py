"""Independent falsification gate for provisional archive reconstruction units.

The evaluator consumes already materialized Stage 2A and Stage 2B payloads.
It never rescans an archive, infers a unit, opens a database, consults labels,
or mutates any input.  Its job is to reject an inconsistent Stage 2C payload
before a downstream consumer can treat a provisional grouping as reliable.

Unit IDs are ``unit:<sha256>`` over canonical JSON of exactly::

    archive_id, snapshot_id, role, root_path, anchor_refs

Relation hashes are ``sha256:<hex>`` over the complete Stage 2B relation
payload.  Stage 2B has no embedded ``relation_hash`` field.  Both algorithms use
UTF-8 JSON with sorted keys, compact separators and ``allow_nan=False``.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

from ._contract_helpers import stable_json as _canonical


PROJECTION_SCHEMA = "mak-archive-reconstruction-input-v1"
RELATION_SCHEMA = "mak-archive-relation-candidates-v1"
UNIT_SCHEMA = "mak-archive-unit-reconstruction-v1"
REPORT_SCHEMA = "mak-archive-unit-evaluation-v1"
OBSERVER_SCHEMA = "mak-archive-observation-batch-v1"

UNIT_ID_ALGORITHM = "sha256-canonical-unit-identity-v1"
RELATION_HASH_ALGORITHM = "sha256-canonical-relation-payload-v1"
REPORT_HASH_ALGORITHM = "sha256-canonical-report-without-report-hash-v1"

UNIT_STATUSES = frozenset({"provisional_unit", "unresolved_unit"})
ASSIGNMENT_STATUSES = frozenset({"assigned", "ambiguous", "unassigned"})
ROLES = frozenset({
    "project_unit",
    "subproject",
    "library_dependency",
    "shared_resource",
    "exported_product",
    "undecided",
})
RELATION_STATUSES = frozenset({"pending_relation", "unresolved_candidate"})
DIAGNOSTIC_OBSERVATION_TYPES = frozenset({"failure", "failure_candidate", "limit_reached"})

UNIT_FIELDS = frozenset({
    "unit_id", "role", "status", "root_path", "anchor_refs", "member_refs",
    "dependency_refs", "candidate_ids", "evidence_for", "evidence_against",
    "alternatives", "missing_evidence",
})
ASSIGNMENT_FIELDS = frozenset({
    "artifact_ref", "status", "unit_id", "reason_codes", "candidate_ids",
    "alternatives",
})
UNIT_TOP_FIELDS = frozenset({
    "schema", "source_projection_schema", "source_relation_schema",
    "algorithm_version", "archive_id", "snapshot_id", "input_hash",
    "relation_hash", "units", "assignments", "unassigned_refs",
    "ambiguous_refs", "reconciliation",
})
RELATION_CANDIDATE_FIELDS = frozenset({
    "candidate_id", "source_ref", "relation", "target_ref", "inverse_relation",
    "status", "score", "reason_codes", "evidence_refs", "evidence_for",
    "evidence_against", "alternatives", "missing_evidence", "next_probe",
})
RELATION_REQUIRED_FIELDS = frozenset({
    "schema", "source_schema", "archive_id", "snapshot_id", "input_hash",
    "candidates",
})
RELATION_OPTIONAL_FIELDS = frozenset({
    "algorithm_version", "skipped_observation_summary", "coverage",
    "reconciliation",
})
RECONCILIATION_REQUIRED_FIELDS = frozenset({
    "total_artifacts", "assigned", "ambiguous", "unassigned", "unit_count",
    "units_by_role", "assignment_count", "duplicates", "loss", "balanced",
    "truth_promotions", "relation_candidate_count", "unit_status_values",
})


class ArchiveUnitEvaluationError(ValueError):
    """Raised by ``assert_unit_payload`` when a falsification gate fails."""

    def __init__(self, message: str, report: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.report = dict(report) if report is not None else None


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_is_json_value(item) for item in value)
    return False


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _error(
    errors: list[dict[str, Any]],
    code: str,
    detail: str,
    *,
    unit_index: int | None = None,
    assignment_index: int | None = None,
) -> None:
    item: dict[str, Any] = {"code": code, "detail": detail}
    if unit_index is not None:
        item["unit_index"] = unit_index
    if assignment_index is not None:
        item["assignment_index"] = assignment_index
    errors.append(item)


def _sort_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        errors,
        key=lambda item: (
            str(item.get("code", "")),
            int(item.get("unit_index", -1)),
            int(item.get("assignment_index", -1)),
            str(item.get("detail", "")),
        ),
    )


def _sorted_unique_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(_nonempty_string(item) for item in value)
        and value == sorted(set(value))
    )


def _json_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_json_value(item) for item in value)


def _unique_json_items(value: list[Any]) -> bool:
    encoded = [_canonical(item) for item in value]
    return len(encoded) == len(set(encoded))


def _relative_path(value: Any) -> bool:
    if value == "":
        return True
    if not _nonempty_string(value) or "\\" in value or value.startswith("/"):
        return False
    try:
        path = PurePosixPath(value)
    except (TypeError, ValueError):
        return False
    if path.as_posix() != value or value in {".", ".."}:
        return False
    return all(part not in {"", ".", ".."} for part in path.parts)


def _unit_semantic_fields(unit: Mapping[str, Any], archive_id: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "role": unit["role"],
        "root_path": unit["root_path"],
        "anchor_refs": sorted(set(unit["anchor_refs"])),
    }


def unit_id_for(unit: Mapping[str, Any], archive_id: str, snapshot_id: str) -> str:
    """Compute the canonical unit ID used by the Stage 2C contract."""

    semantic = _unit_semantic_fields(unit, archive_id, snapshot_id)
    if not _is_json_value(semantic):
        raise ArchiveUnitEvaluationError("unit_identity_not_json")
    return "unit:" + _digest(semantic)


def relation_hash_for(relations: Mapping[str, Any]) -> str:
    """Compute the canonical hash of a Stage 2B payload."""

    if not isinstance(relations, Mapping):
        raise ArchiveUnitEvaluationError("relations_must_be_mapping")
    material = dict(relations)
    if not _is_json_value(material):
        raise ArchiveUnitEvaluationError("relations_not_json")
    return "sha256:" + _digest(material)


def _candidate_semantic_fields(candidate: Mapping[str, Any], archive_id: str) -> dict[str, Any]:
    return {
        "archive_id": archive_id,
        "source_ref": candidate["source_ref"],
        "relation": candidate["relation"],
        "target_ref": candidate["target_ref"],
        "inverse_relation": candidate["inverse_relation"],
        "status": candidate["status"],
        "score": candidate["score"],
        "reason_codes": candidate["reason_codes"],
        "evidence_refs": candidate["evidence_refs"],
        "evidence_for": candidate["evidence_for"],
        "evidence_against": candidate["evidence_against"],
        "alternatives": candidate["alternatives"],
        "missing_evidence": candidate["missing_evidence"],
        "next_probe": candidate["next_probe"],
    }


def candidate_id_for(candidate: Mapping[str, Any], archive_id: str) -> str:
    """Compute the Stage 2B full semantic-field candidate ID independently."""

    semantic = _candidate_semantic_fields(candidate, archive_id)
    if not _is_json_value(semantic):
        raise ArchiveUnitEvaluationError("candidate_identity_not_json")
    return "candidate:" + _digest(semantic)


def _inverse_for(relation: str) -> str | None:
    inverses = {
        "contains": "contained_by",
        "contained_by": "contains",
        "depends_on": "depended_on_by",
        "depended_on_by": "depends_on",
        "shared_resource": "shared_resource_of",
        "shared_resource_of": "shared_resource",
        "shares_library_with": "shares_library_with",
        "unrelated": "unrelated",
        "identity_undecided": "identity_undecided",
        "describes": "described_by",
        "described_by": "describes",
        "manifestation_of": "has_manifestation",
        "has_manifestation": "manifestation_of",
        "component_of": "has_component",
        "has_component": "component_of",
        "version_of": "has_version",
        "has_version": "version_of",
        "same_series_candidate": "same_series_candidate",
    }
    return inverses.get(relation)


def _projection_context(projection: Any, errors: list[dict[str, Any]]) -> dict[str, Any]:
    context: dict[str, Any] = {
        "schema": None,
        "source_schema": None,
        "archive_id": None,
        "snapshot_id": None,
        "input_hash": None,
        "artifact_refs": {},
        "content_ids": {},
        "observation_ids": set(),
        "candidate_observations": [],
        "paths": set(),
        "native_anchor_refs": set(),
        "output_refs": set(),
    }
    context["paths"].add("")
    if not isinstance(projection, Mapping):
        _error(errors, "projection_not_object", "projection must be an object")
        return context
    context["schema"] = projection.get("schema")
    context["source_schema"] = projection.get("source_schema")
    context["archive_id"] = projection.get("archive_id")
    context["snapshot_id"] = projection.get("snapshot_id")
    context["input_hash"] = projection.get("input_hash")
    if context["schema"] != PROJECTION_SCHEMA:
        _error(errors, "projection_schema_mismatch", "projection schema is not Stage 2A")
    if context["source_schema"] != OBSERVER_SCHEMA:
        _error(errors, "projection_source_schema_mismatch", "projection source_schema is not the observer schema")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if not _nonempty_string(context[field]):
            _error(errors, f"projection_{field}_invalid", f"projection.{field} must be a non-empty string")

    artifacts = projection.get("artifacts")
    if not isinstance(artifacts, list):
        _error(errors, "projection_artifacts_invalid", "projection.artifacts must be a list")
        artifacts = []
    for index, raw in enumerate(artifacts):
        if not isinstance(raw, Mapping):
            _error(errors, "projection_artifact_invalid", f"artifact[{index}] is not an object")
            continue
        ref = raw.get("artifact_ref")
        if not _nonempty_string(ref):
            _error(errors, "artifact_ref_invalid", f"artifact[{index}].artifact_ref is invalid")
            continue
        if ref in context["artifact_refs"]:
            _error(errors, "duplicate_artifact_ref", f"duplicate artifact_ref:{ref}")
            continue
        if "archive_id" in raw and raw.get("archive_id") != context["archive_id"]:
            _error(errors, "cross_archive_artifact", f"artifact_ref:{ref} belongs to another archive")
        relative_path = raw.get("relative_path")
        if not _relative_path(relative_path):
            _error(errors, "artifact_path_invalid", f"artifact_ref:{ref} has an invalid relative_path")
        else:
            context["paths"].add(relative_path)
            parts = relative_path.split("/")
            for end in range(1, len(parts)):
                context["paths"].add("/".join(parts[:end]))
        context["artifact_refs"][ref] = raw
        content_id = raw.get("content_id")
        if _nonempty_string(content_id):
            context["content_ids"].setdefault(content_id, []).append(ref)
        flags = raw.get("derived_flags")
        if isinstance(flags, Mapping):
            if flags.get("native_authoring_anchor") is True:
                context["native_anchor_refs"].add(ref)
            if flags.get("probable_output_media") is True:
                context["output_refs"].add(ref)

    for field, target in (("native_anchor_refs", "native_anchor_refs"), ("probable_output_refs", "output_refs")):
        refs = projection.get(field)
        if refs is None:
            continue
        if not _sorted_unique_strings(refs):
            _error(errors, f"projection_{field}_invalid", f"projection.{field} must be sorted unique refs")
            continue
        for ref in refs:
            if ref not in context["artifact_refs"]:
                _error(errors, f"projection_{field}_dangling", f"{field}:{ref} is not an artifact_ref")
        context[target].update(refs)

    observations = projection.get("candidate_observations", [])
    if not isinstance(observations, list):
        _error(errors, "projection_observations_invalid", "candidate_observations must be a list")
        observations = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, Mapping) or not _nonempty_string(observation.get("observation_id")):
            _error(errors, "projection_observation_invalid", f"candidate_observations[{index}] is invalid")
            continue
        observation_id = observation["observation_id"]
        if observation_id in context["observation_ids"]:
            _error(errors, "duplicate_observation_id", f"duplicate observation_id:{observation_id}")
        context["observation_ids"].add(observation_id)
        context["candidate_observations"].append(observation)

    return context


def _relation_context(
    relations: Any,
    projection_context: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "schema": None,
        "source_schema": None,
        "archive_id": None,
        "snapshot_id": None,
        "input_hash": None,
        "relation_hash": None,
        "candidate_by_id": {},
    }
    if not isinstance(relations, Mapping):
        _error(errors, "relations_not_object", "relations must be an object")
        return context
    context["schema"] = relations.get("schema")
    context["source_schema"] = relations.get("source_schema")
    context["archive_id"] = relations.get("archive_id")
    context["snapshot_id"] = relations.get("snapshot_id")
    context["input_hash"] = relations.get("input_hash")
    allowed = RELATION_REQUIRED_FIELDS | RELATION_OPTIONAL_FIELDS
    unknown = sorted(str(key) for key in set(relations) - allowed)
    if unknown:
        _error(errors, "relations_unknown_fields", ",".join(unknown))
    if context["schema"] != RELATION_SCHEMA:
        _error(errors, "relations_schema_mismatch", "relations schema is not Stage 2B")
    if context["source_schema"] != PROJECTION_SCHEMA:
        _error(errors, "relations_source_schema_mismatch", "relations source_schema is not Stage 2A")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if relations.get(field) != projection_context.get(field):
            _error(errors, f"relations_{field}_mismatch", f"relations.{field} does not match projection")
    try:
        expected_relation_hash = relation_hash_for(relations)
    except ArchiveUnitEvaluationError as error:
        expected_relation_hash = None
        _error(errors, "relation_hash_uncomputable", str(error))
    context["relation_hash"] = expected_relation_hash

    candidates = relations.get("candidates")
    if not isinstance(candidates, list):
        _error(errors, "relations_candidates_invalid", "relations.candidates must be a list")
        candidates = []
    artifact_refs = set(projection_context["artifact_refs"])
    content_ids = set(projection_context["content_ids"])
    observation_ids = set(projection_context["observation_ids"])
    candidate_ids: list[str] = []
    for index, raw in enumerate(candidates):
        if not isinstance(raw, Mapping) or set(raw) != RELATION_CANDIDATE_FIELDS:
            _error(errors, "relation_candidate_fields_invalid", f"candidate[{index}] fields are not canonical")
            continue
        candidate = dict(raw)
        candidate_id = candidate.get("candidate_id")
        if not _nonempty_string(candidate_id):
            _error(errors, "relation_candidate_id_invalid", f"candidate[{index}] ID is invalid")
        else:
            candidate_ids.append(candidate_id)
        if candidate.get("source_ref") not in artifact_refs or candidate.get("target_ref") not in artifact_refs:
            _error(errors, "relation_endpoint_dangling", f"candidate[{index}] endpoint is unresolved")
        if candidate.get("source_ref") in content_ids or candidate.get("target_ref") in content_ids:
            _error(errors, "relation_content_id_endpoint", f"candidate[{index}] uses content_id as endpoint")
        relation = candidate.get("relation")
        if _inverse_for(relation) != candidate.get("inverse_relation"):
            _error(errors, "relation_inverse_invalid", f"candidate[{index}] inverse is incorrect")
        if candidate.get("status") not in RELATION_STATUSES:
            _error(errors, "relation_promoted_status", f"candidate[{index}] status is promoted or invalid")
        score = candidate.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
            _error(errors, "relation_score_invalid", f"candidate[{index}] score is invalid")
        for field in ("reason_codes", "evidence_refs", "missing_evidence"):
            if not _sorted_unique_strings(candidate.get(field)):
                _error(errors, "relation_candidate_list_invalid", f"candidate[{index}].{field} is not canonical")
        for field in ("evidence_for", "evidence_against", "alternatives"):
            if not _json_list(candidate.get(field)):
                _error(errors, "relation_candidate_evidence_invalid", f"candidate[{index}].{field} is not a JSON list")
        if candidate.get("next_probe") is not None and not _nonempty_string(candidate.get("next_probe")):
            _error(errors, "relation_next_probe_invalid", f"candidate[{index}].next_probe is invalid")
        for ref in candidate.get("evidence_refs", []):
            if ref not in artifact_refs and ref not in observation_ids:
                _error(errors, "relation_evidence_dangling", f"candidate[{index}] evidence ref is unresolved:{ref}")
            if ref in content_ids:
                _error(errors, "relation_content_id_evidence", f"candidate[{index}] evidence ref is content_id:{ref}")
            observation = next((item for item in projection_context["candidate_observations"] if item.get("observation_id") == ref), None)
            if ref in observation_ids and isinstance(observation, Mapping) and observation.get("observation_type") in DIAGNOSTIC_OBSERVATION_TYPES:
                _error(errors, "relation_diagnostic_evidence", f"candidate[{index}] evidence ref is diagnostic:{ref}")
        try:
            expected_id = candidate_id_for(candidate, str(projection_context.get("archive_id")))
        except ArchiveUnitEvaluationError:
            expected_id = None
        if expected_id != candidate_id:
            _error(errors, "relation_candidate_id_mismatch", f"candidate[{index}] ID is not semantic")
        if candidate_id in context["candidate_by_id"]:
            _error(errors, "duplicate_relation_candidate_id", f"duplicate candidate_id:{candidate_id}")
        else:
            context["candidate_by_id"][candidate_id] = candidate
    if candidate_ids != sorted(candidate_ids):
        _error(errors, "relation_candidate_order_invalid", "relations candidates are not sorted by candidate_id")
    return context


def _validate_reconciliation(
    reconciliation: Any,
    expected: Mapping[str, Any],
    errors: list[dict[str, Any]],
) -> bool:
    if not isinstance(reconciliation, Mapping):
        _error(errors, "reconciliation_invalid", "reconciliation must be an object")
        return False
    if set(reconciliation) != RECONCILIATION_REQUIRED_FIELDS:
        _error(errors, "reconciliation_fields_invalid", "reconciliation fields are not canonical")
        return False
    missing = sorted(RECONCILIATION_REQUIRED_FIELDS - set(reconciliation))
    if missing:
        _error(errors, "reconciliation_missing_fields", ",".join(missing))
    ok = not missing
    for field, value in expected.items():
        if field in RECONCILIATION_REQUIRED_FIELDS and reconciliation.get(field) != value:
            ok = False
            _error(errors, "reconciliation_mismatch", f"reconciliation.{field} does not match computed value")
    if reconciliation.get("balanced") is not True:
        ok = False
        _error(errors, "reconciliation_not_balanced", "reconciliation.balanced must be true")
    if reconciliation.get("truth_promotions") != 0:
        ok = False
        _error(errors, "reconciliation_truth_promotion", "reconciliation.truth_promotions must be zero")
    return ok


def evaluate_unit_payload(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
    units: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a deterministic falsification report without mutating inputs."""

    projection_errors: list[dict[str, Any]] = []
    relation_errors: list[dict[str, Any]] = []
    unit_errors: list[dict[str, Any]] = []
    projection_context = _projection_context(projection, projection_errors)
    relation_context = _relation_context(relations, projection_context, relation_errors)
    errors = projection_errors + relation_errors + unit_errors

    unit_context: dict[str, Any] = {
        "schema": None,
        "source_projection_schema": None,
        "source_relation_schema": None,
        "algorithm_version": None,
        "archive_id": None,
        "snapshot_id": None,
        "input_hash": None,
        "relation_hash": None,
        "units": [],
        "assignments": [],
        "unassigned_refs": [],
        "ambiguous_refs": [],
        "reconciliation": None,
    }
    if not isinstance(units, Mapping):
        _error(unit_errors, "units_not_object", "units must be an object")
    else:
        unknown = sorted(str(key) for key in set(units) - UNIT_TOP_FIELDS)
        missing = sorted(UNIT_TOP_FIELDS - set(units))
        if unknown:
            _error(unit_errors, "unit_payload_unknown_fields", ",".join(unknown))
        if missing:
            _error(unit_errors, "unit_payload_missing_fields", ",".join(missing))
        for key in unit_context:
            unit_context[key] = units.get(key)

    if unit_context["schema"] != UNIT_SCHEMA:
        _error(unit_errors, "unit_schema_mismatch", "units schema is not Stage 2C")
    if unit_context["source_projection_schema"] != PROJECTION_SCHEMA:
        _error(unit_errors, "unit_source_projection_schema_mismatch", "units source projection schema is invalid")
    if unit_context["source_relation_schema"] != RELATION_SCHEMA:
        _error(unit_errors, "unit_source_relation_schema_mismatch", "units source relation schema is invalid")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if unit_context[field] != projection_context.get(field):
            _error(unit_errors, f"unit_{field}_mismatch", f"units.{field} does not match projection")
    expected_relation_hash = relation_context.get("relation_hash")
    if unit_context["relation_hash"] != expected_relation_hash:
        _error(unit_errors, "unit_relation_hash_mismatch", "units.relation_hash is not the canonical Stage 2B hash")

    raw_units = unit_context["units"]
    if not isinstance(raw_units, list):
        _error(unit_errors, "units_list_invalid", "units.units must be a list")
        raw_units = []
    raw_assignments = unit_context["assignments"]
    if not isinstance(raw_assignments, list):
        _error(unit_errors, "assignments_list_invalid", "units.assignments must be a list")
        raw_assignments = []

    artifact_refs = set(projection_context["artifact_refs"])
    content_ids = set(projection_context["content_ids"])
    candidate_by_id = relation_context["candidate_by_id"]
    unit_by_id: dict[str, dict[str, Any]] = {}
    unit_members: dict[str, set[str]] = {}
    unit_dependencies: dict[str, set[str]] = {}
    unit_ids: list[str] = []
    member_refs_resolved = True
    dependency_refs_resolved = True
    candidate_ids_resolved = True

    for index, raw in enumerate(raw_units):
        if not isinstance(raw, Mapping) or set(raw) != UNIT_FIELDS:
            _error(unit_errors, "unit_fields_invalid", f"unit[{index}] fields are not canonical", unit_index=index)
            continue
        unit = dict(raw)
        unit_id = unit.get("unit_id")
        if not _nonempty_string(unit_id):
            _error(unit_errors, "unit_id_invalid", f"unit[{index}] ID is invalid", unit_index=index)
        else:
            unit_ids.append(unit_id)
        if unit.get("role") not in ROLES:
            _error(unit_errors, "unit_role_invalid", f"unit[{index}] role is invalid", unit_index=index)
        if unit.get("status") not in UNIT_STATUSES:
            _error(unit_errors, "unit_promoted_status", f"unit[{index}] status is promoted or invalid", unit_index=index)
        if not _relative_path(unit.get("root_path")) or unit.get("root_path") not in projection_context["paths"]:
            _error(unit_errors, "unit_root_path_invalid", f"unit[{index}] root_path is synthetic or invalid", unit_index=index)
        for field in ("anchor_refs", "member_refs", "dependency_refs", "candidate_ids"):
            if not _sorted_unique_strings(unit.get(field)):
                _error(unit_errors, "unit_ref_list_invalid", f"unit[{index}].{field} is not sorted unique refs", unit_index=index)
        for field in ("evidence_for", "evidence_against", "alternatives", "missing_evidence"):
            if not _json_list(unit.get(field)):
                _error(unit_errors, "unit_evidence_list_invalid", f"unit[{index}].{field} is not a JSON list", unit_index=index)
        if not set(unit.get("anchor_refs", [])).issubset(set(unit.get("member_refs", []))):
            _error(unit_errors, "unit_anchor_membership_invalid", f"unit[{index}] anchor is not a member", unit_index=index)
        if set(unit.get("member_refs", [])) & set(unit.get("dependency_refs", [])):
            _error(unit_errors, "unit_member_dependency_overlap", f"unit[{index}] member/dependency overlap", unit_index=index)
        for field, resolved_flag in (("anchor_refs", None), ("member_refs", "member"), ("dependency_refs", "dependency")):
            for ref in unit.get(field, []):
                if ref not in artifact_refs:
                    _error(unit_errors, "unit_ref_dangling", f"unit[{index}].{field} unresolved:{ref}", unit_index=index)
                    if resolved_flag == "member":
                        member_refs_resolved = False
                    if resolved_flag == "dependency":
                        dependency_refs_resolved = False
                if ref in content_ids:
                    _error(unit_errors, "unit_content_id_endpoint", f"unit[{index}].{field} uses content_id:{ref}", unit_index=index)
        for candidate_id in unit.get("candidate_ids", []):
            if candidate_id not in candidate_by_id:
                candidate_ids_resolved = False
                _error(unit_errors, "unit_candidate_id_dangling", f"unit[{index}] candidate_id unresolved:{candidate_id}", unit_index=index)
        try:
            expected_id = unit_id_for(unit, str(projection_context.get("archive_id")), str(projection_context.get("snapshot_id")))
        except (ArchiveUnitEvaluationError, KeyError):
            expected_id = None
        if expected_id != unit_id:
            _error(unit_errors, "unit_id_mismatch", f"unit[{index}] ID is not canonical", unit_index=index)
        if unit_id in unit_by_id:
            _error(unit_errors, "duplicate_unit_id", f"duplicate unit_id:{unit_id}", unit_index=index)
        else:
            unit_by_id[unit_id] = unit
            unit_members[unit_id] = set(unit.get("member_refs", []))
            unit_dependencies[unit_id] = set(unit.get("dependency_refs", []))

        all_unit_refs = set(unit.get("anchor_refs", [])) | set(unit.get("member_refs", [])) | set(unit.get("dependency_refs", []))
        native_evidence = all_unit_refs & set(projection_context["native_anchor_refs"])
        output_evidence = all_unit_refs & set(projection_context["output_refs"])
        if unit.get("role") == "project_unit" and not (native_evidence or output_evidence):
            _error(unit_errors, "root_without_anchor_or_output_evidence", f"unit[{index}] has no anchor/output evidence", unit_index=index)
        if output_evidence and not native_evidence:
            missing = unit.get("missing_evidence", [])
            if unit.get("role") != "exported_product" or unit.get("status") != "unresolved_unit" or not ({"source_binding", "missing_source_binding"} & set(missing)):
                _error(unit_errors, "output_only_unit_invalid", f"unit[{index}] output-only unit is not unresolved exported_product", unit_index=index)

    if unit_ids != sorted(unit_ids):
        _error(unit_errors, "unit_order_invalid", "units must be sorted by unit_id")

    assignment_refs: list[str] = []
    assignment_by_ref: dict[str, dict[str, Any]] = {}
    assigned_refs: set[str] = set()
    ambiguous_refs_from_assignments: set[str] = set()
    unassigned_refs_from_assignments: set[str] = set()
    for index, raw in enumerate(raw_assignments):
        if not isinstance(raw, Mapping) or set(raw) != ASSIGNMENT_FIELDS:
            _error(unit_errors, "assignment_fields_invalid", f"assignment[{index}] fields are not canonical", assignment_index=index)
            continue
        assignment = dict(raw)
        ref = assignment.get("artifact_ref")
        if not _nonempty_string(ref):
            _error(unit_errors, "assignment_ref_invalid", f"assignment[{index}] artifact_ref invalid", assignment_index=index)
        else:
            assignment_refs.append(ref)
        if ref not in artifact_refs:
            _error(unit_errors, "assignment_ref_dangling", f"assignment[{index}] artifact_ref unresolved", assignment_index=index)
        if ref in content_ids:
            _error(unit_errors, "assignment_content_id_endpoint", f"assignment[{index}] uses content_id", assignment_index=index)
        status = assignment.get("status")
        if status not in ASSIGNMENT_STATUSES:
            _error(unit_errors, "assignment_status_invalid", f"assignment[{index}] status invalid", assignment_index=index)
        if not _sorted_unique_strings(assignment.get("reason_codes")) or not _sorted_unique_strings(assignment.get("candidate_ids")):
            _error(unit_errors, "assignment_list_invalid", f"assignment[{index}] reason/candidate list invalid", assignment_index=index)
        if not _json_list(assignment.get("alternatives")):
            _error(unit_errors, "assignment_alternatives_invalid", f"assignment[{index}] alternatives invalid", assignment_index=index)
        for candidate_id in assignment.get("candidate_ids", []):
            if candidate_id not in candidate_by_id:
                candidate_ids_resolved = False
                _error(unit_errors, "assignment_candidate_id_dangling", f"assignment[{index}] candidate_id unresolved:{candidate_id}", assignment_index=index)
        unit_id = assignment.get("unit_id")
        if status == "assigned":
            assigned_refs.add(ref)
            if not _nonempty_string(unit_id) or unit_id not in unit_by_id:
                _error(unit_errors, "assigned_unit_missing", f"assignment[{index}] assigned unit_id is missing", assignment_index=index)
            elif ref not in unit_members[unit_id]:
                _error(unit_errors, "assigned_membership_mismatch", f"assignment[{index}] is not a member of its unit", assignment_index=index)
        elif status == "ambiguous":
            ambiguous_refs_from_assignments.add(ref)
            if unit_id is not None:
                _error(unit_errors, "ambiguous_unit_present", f"assignment[{index}] ambiguous assignment has unit_id", assignment_index=index)
            if len(assignment.get("alternatives", [])) < 2 or not _unique_json_items(assignment.get("alternatives", [])):
                _error(unit_errors, "ambiguous_alternatives_insufficient", f"assignment[{index}] needs two distinct alternatives", assignment_index=index)
        elif status == "unassigned":
            unassigned_refs_from_assignments.add(ref)
            if unit_id is not None:
                _error(unit_errors, "unassigned_unit_present", f"assignment[{index}] unassigned record has unit_id", assignment_index=index)
        if ref in assignment_by_ref:
            _error(unit_errors, "duplicate_assignment", f"duplicate assignment for:{ref}", assignment_index=index)
        else:
            assignment_by_ref[ref] = assignment

    if assignment_refs != sorted(assignment_refs):
        _error(unit_errors, "assignment_order_invalid", "assignments must be sorted by artifact_ref",)

    unassigned_refs = unit_context["unassigned_refs"]
    ambiguous_refs = unit_context["ambiguous_refs"]
    if not _sorted_unique_strings(unassigned_refs):
        _error(unit_errors, "unassigned_refs_invalid", "unassigned_refs must be sorted unique refs")
        unassigned_refs = []
    if not _sorted_unique_strings(ambiguous_refs):
        _error(unit_errors, "ambiguous_refs_invalid", "ambiguous_refs must be sorted unique refs")
        ambiguous_refs = []
    if set(unassigned_refs) != unassigned_refs_from_assignments:
        _error(unit_errors, "unassigned_refs_mismatch", "unassigned_refs disagree with assignment statuses")
    if set(ambiguous_refs) != ambiguous_refs_from_assignments:
        _error(unit_errors, "ambiguous_refs_mismatch", "ambiguous_refs disagree with assignment statuses")

    for unit_id, refs in unit_members.items():
        for ref in refs:
            assignment = assignment_by_ref.get(ref)
            if assignment is None or assignment.get("status") != "assigned" or assignment.get("unit_id") != unit_id:
                _error(unit_errors, "unit_assignment_membership_mismatch", f"unit:{unit_id} ref:{ref} lacks matching assigned record")

    total_artifacts = len(artifact_refs)
    assignment_ref_set = set(assignment_refs)
    assignment_duplicates = len(assignment_refs) - len(assignment_ref_set)
    assignment_loss = len(artifact_refs - assignment_ref_set)
    partition_union = assigned_refs | ambiguous_refs_from_assignments | unassigned_refs_from_assignments
    partition_disjoint = (
        not (assigned_refs & ambiguous_refs_from_assignments)
        and not (assigned_refs & unassigned_refs_from_assignments)
        and not (ambiguous_refs_from_assignments & unassigned_refs_from_assignments)
    )
    balanced = (
        assignment_ref_set == artifact_refs
        and partition_disjoint
        and len(partition_union) == total_artifacts
        and assignment_loss == 0
        and assignment_duplicates == 0
        and len(assigned_refs) + len(ambiguous_refs_from_assignments) + len(unassigned_refs_from_assignments) == total_artifacts
    )
    if not balanced:
        _error(unit_errors, "assignment_partition_unbalanced", "assignment partition does not cover artifacts exactly once")

    role_counts: dict[str, int] = {}
    for unit in unit_by_id.values():
        role = str(unit.get("role"))
        role_counts[role] = role_counts.get(role, 0) + 1
    expected_reconciliation = {
        "total_artifacts": total_artifacts,
        "assigned": len(assigned_refs),
        "ambiguous": len(ambiguous_refs_from_assignments),
        "unassigned": len(unassigned_refs_from_assignments),
        "unit_count": len(unit_by_id),
        "units_by_role": dict(sorted(role_counts.items())),
        "assignment_count": len(raw_assignments),
        "duplicates": assignment_duplicates,
        "loss": assignment_loss,
        "balanced": balanced,
        "truth_promotions": 0,
        "relation_candidate_count": len(candidate_by_id),
        "unit_status_values": sorted(UNIT_STATUSES),
    }
    deterministic_order = unit_ids == sorted(unit_ids) and assignment_refs == sorted(assignment_refs)
    reconciliation_ok = _validate_reconciliation(unit_context["reconciliation"], expected_reconciliation, unit_errors)
    errors.extend(unit_errors)

    checks = {
        "upstream_schemas": {"passed": not projection_errors and not relation_errors, "details": {"projection": projection_context["schema"], "relations": relation_context["schema"]}},
        "archive_snapshot_input_match": {"passed": not any(error["code"].endswith("_mismatch") for error in unit_errors + relation_errors), "details": {"archive_id": projection_context["archive_id"], "snapshot_id": projection_context["snapshot_id"]}},
        "relation_hash": {"passed": unit_context["relation_hash"] == expected_relation_hash and expected_relation_hash is not None, "details": {"algorithm": RELATION_HASH_ALGORITHM}},
        "unit_ids": {"passed": not any(error["code"] in {"unit_id_invalid", "unit_id_mismatch", "duplicate_unit_id", "unit_order_invalid"} for error in unit_errors), "details": {"algorithm": UNIT_ID_ALGORITHM}},
        "artifact_refs": {"passed": not any(error["code"] in {"unit_ref_dangling", "unit_content_id_endpoint", "assignment_ref_dangling", "assignment_content_id_endpoint", "cross_archive_artifact"} for error in unit_errors + projection_errors), "details": {"artifact_count": total_artifacts}},
        "candidate_refs": {"passed": candidate_ids_resolved and not any(error["code"].startswith("relation_candidate") for error in relation_errors), "details": {"candidate_count": len(candidate_by_id)}},
        "assignments": {"passed": balanced, "details": {"assigned": len(assigned_refs), "ambiguous": len(ambiguous_refs_from_assignments), "unassigned": len(unassigned_refs_from_assignments), "total": total_artifacts}},
        "membership": {"passed": not any(error["code"] in {"assigned_membership_mismatch", "unit_assignment_membership_mismatch", "unit_anchor_membership_invalid", "unit_member_dependency_overlap"} for error in unit_errors), "details": {"units": len(unit_by_id)}},
        "duplicate_physical_refs": {"passed": assignment_duplicates == 0 and all(set(refs).issubset(assignment_ref_set) for refs in projection_context["content_ids"].values()), "details": {"duplicate_content_groups": {key: sorted(value) for key, value in projection_context["content_ids"].items() if len(value) > 1}}},
        "root_evidence": {"passed": not any(error["code"] in {"root_without_anchor_or_output_evidence", "output_only_unit_invalid", "unit_root_path_invalid"} for error in unit_errors), "details": {"policy": "observed_relative_paths_and_anchor_or_output_evidence"}},
        "no_promoted_truth": {"passed": not any(error["code"] in {"unit_promoted_status", "assignment_status_invalid", "reconciliation_truth_promotion", "relation_promoted_status"} for error in unit_errors + relation_errors), "details": {"unit_statuses": sorted(UNIT_STATUSES), "assignment_statuses": sorted(ASSIGNMENT_STATUSES)}},
        "reconciliation": {"passed": reconciliation_ok, "details": {"required_fields": sorted(RECONCILIATION_REQUIRED_FIELDS)}},
        "deterministic_order": {"passed": deterministic_order, "details": {"units": "unit_id", "assignments": "artifact_ref"}},
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "algorithm_version": "archive-unit-evaluator-v1",
        "unit_id_algorithm": UNIT_ID_ALGORITHM,
        "relation_hash_algorithm": RELATION_HASH_ALGORITHM,
        "report_hash_algorithm": REPORT_HASH_ALGORITHM,
        "source": {
            "projection_schema": projection_context["schema"],
            "relation_schema": relation_context["schema"],
            "unit_schema": unit_context["schema"],
            "archive_id": projection_context["archive_id"],
            "snapshot_id": projection_context["snapshot_id"],
            "input_hash": projection_context["input_hash"],
            "relation_hash": expected_relation_hash,
        },
        "checks": checks,
        "metrics": {
            "artifact_count": total_artifacts,
            "unit_count": len(unit_by_id),
            "assignment_count": len(raw_assignments),
            "assigned_count": len(assigned_refs),
            "ambiguous_count": len(ambiguous_refs_from_assignments),
            "unassigned_count": len(unassigned_refs_from_assignments),
            "duplicate_content_group_count": sum(1 for refs in projection_context["content_ids"].values() if len(refs) > 1),
            "assignment_duplicates": assignment_duplicates,
            "assignment_loss": assignment_loss,
        },
        "errors": _sort_errors(errors),
    }
    report["passed"] = not report["errors"] and all(check["passed"] for check in checks.values())
    report["valid"] = bool(report["passed"])
    report["status"] = "pass" if report["valid"] else "fail"
    report["report_hash"] = "report:" + _digest(report)
    return report


def assert_unit_payload(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
    units: Mapping[str, Any],
) -> bool:
    """Return ``True`` or raise with the complete deterministic report."""

    report = evaluate_unit_payload(projection, relations, units)
    if not report["valid"]:
        codes = ",".join(error["code"] for error in report["errors"])
        raise ArchiveUnitEvaluationError(f"archive_unit_payload_rejected:{codes}", report)
    return True


__all__ = [
    "ASSIGNMENT_STATUSES",
    "ArchiveUnitEvaluationError",
    "REPORT_SCHEMA",
    "RELATION_HASH_ALGORITHM",
    "ROLES",
    "UNIT_ID_ALGORITHM",
    "UNIT_SCHEMA",
    "UNIT_STATUSES",
    "assert_unit_payload",
    "candidate_id_for",
    "evaluate_unit_payload",
    "relation_hash_for",
    "unit_id_for",
]
