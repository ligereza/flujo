"""Adversarial, read-only validation of archive relation candidates.

This module is a falsification gate.  It validates a candidate payload against
an archive-memory reconstruction projection; it never infers a relation,
rescans a source tree, opens a database, consults user labels, or mutates its
inputs.

Input contract
--------------
``mak-archive-reconstruction-input-v1`` is a mapping with ``archive_id``,
``snapshot_id``, ``input_hash``, ``artifacts`` and ``candidate_observations``.
An artifact contributes its stable ``artifact_ref`` to the endpoint namespace.
Candidate-observation IDs are valid evidence references, not relation
endpoints.  ``input_hash`` is authoritative metadata emitted by Stage 2A;
the evaluator never recomputes it as a validity requirement.

Candidate ID contract
---------------------
``candidate_id`` is ``candidate:<sha256>`` where the digest is over canonical
JSON (UTF-8, sorted keys, compact separators) of the following fields, in the
current archive namespace::

    archive_id, source_ref, relation, target_ref, inverse_relation, status,
    score, reason_codes, evidence_refs, evidence_for, evidence_against,
    alternatives, missing_evidence, next_probe

The report exposes this algorithm version so a producer and evaluator can
replay it independently.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from ._contract_helpers import stable_json as _canonical


INPUT_SCHEMA = "mak-archive-reconstruction-input-v1"
OBSERVER_SCHEMA = "mak-archive-observation-batch-v1"
CANDIDATE_SCHEMA = "mak-archive-relation-candidates-v1"
REPORT_SCHEMA = "mak-archive-relation-evaluation-v1"
ALGORITHM_VERSION = "archive-relation-evaluator-v1"
INPUT_HASH_ALGORITHM = "sha256-canonical-projection-without-input-hash-v1"
CANDIDATE_ID_ALGORITHM = "sha256-canonical-candidate-semantic-fields-v1"
REPORT_HASH_ALGORITHM = "sha256-canonical-report-without-report-hash-v1"
PROJECTION_DIGEST_ALGORITHM = "sha256-canonical-projection-without-input-hash-report-only-v1"

PENDING = "pending_relation"
UNRESOLVED = "unresolved_candidate"
ALLOWED_STATUSES = frozenset({PENDING, UNRESOLVED})

# Existing reconstruction vocabulary plus the archive relation vocabulary.
RELATION_INVERSES: dict[str, str] = {
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
SYMMETRIC_RELATIONS = frozenset(
    relation for relation, inverse in RELATION_INVERSES.items() if relation == inverse
)

CANDIDATE_FIELDS = frozenset(
    {
        "candidate_id",
        "source_ref",
        "relation",
        "target_ref",
        "inverse_relation",
        "status",
        "score",
        "reason_codes",
        "evidence_refs",
        "evidence_for",
        "evidence_against",
        "alternatives",
        "missing_evidence",
        "next_probe",
    }
)
_PAYLOAD_REQUIRED_FIELDS = frozenset(
    {"schema", "source_schema", "archive_id", "snapshot_id", "input_hash", "candidates"}
)
_PAYLOAD_OPTIONAL_FIELDS = frozenset({
    "algorithm_version", "source", "truncated", "truncation", "coverage",
    "reconciliation", "skipped_observation_summary",
})
_DIAGNOSTIC_TYPES = frozenset({"failure", "failure_candidate", "limit_reached"})
_DIRECT_REF_KEYS = frozenset({"artifact_ref", "artifact_refs", "source_ref", "target_ref"})


class ArchiveRelationEvaluationError(ValueError):
    """Raised by ``assert_relation_payload`` when any falsification gate fails."""

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


def input_hash_for_projection(projection: Mapping[str, Any]) -> str:
    """Return the documented deterministic hash of a projection.

    The existing ``input_hash`` field is excluded, making the operation
    replayable without mutating or temporarily removing that field.
    """

    if not isinstance(projection, Mapping):
        raise ArchiveRelationEvaluationError("projection_must_be_object")
    material = {key: value for key, value in projection.items() if key != "input_hash"}
    if not _is_json_value(material):
        raise ArchiveRelationEvaluationError("projection_contains_non_json_value")
    return "input:" + _digest(material)


def candidate_semantic_fields(candidate: Mapping[str, Any], archive_id: str) -> dict[str, Any]:
    """Return the exact semantic material used by ``candidate_id_for``."""

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
    """Compute the public deterministic candidate ID."""

    semantic = candidate_semantic_fields(candidate, archive_id)
    if not _is_json_value(semantic):
        raise ArchiveRelationEvaluationError("candidate_semantic_fields_not_json")
    return "candidate:" + _digest(semantic)


def inverse_relation(relation: str) -> str:
    """Return the declared inverse, failing closed for unknown vocabulary."""

    try:
        return RELATION_INVERSES[relation]
    except KeyError as error:
        raise ArchiveRelationEvaluationError(f"relation_without_inverse:{relation}") from error


def _error(errors: list[dict[str, Any]], code: str, detail: str, index: int | None = None) -> None:
    item: dict[str, Any] = {"code": code, "detail": detail}
    if index is not None:
        item["candidate_index"] = index
    errors.append(item)


def _check(passed: bool, details: Any) -> dict[str, Any]:
    return {"passed": bool(passed), "details": details}


def _sort_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        errors,
        key=lambda item: (
            str(item.get("code", "")),
            int(item.get("candidate_index", -1)),
            str(item.get("detail", "")),
        ),
    )


def _embedded_refs(value: Any) -> list[str]:
    """Extract explicitly named refs from evidence/alternative objects."""

    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in _DIRECT_REF_KEYS or key.endswith("_refs"):
                if isinstance(item, str):
                    found.append(item)
                elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
                    found.extend(str(ref) for ref in item if isinstance(ref, str))
            found.extend(_embedded_refs(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            found.extend(_embedded_refs(item))
    return found


def _projection_context(projection: Any, errors: list[dict[str, Any]]) -> dict[str, Any]:
    context: dict[str, Any] = {
        "valid": True,
        "schema": None,
        "source_schema": None,
        "archive_id": None,
        "snapshot_id": None,
        "input_hash": None,
        "projection_digest": None,
        "artifact_refs": {},
        "content_ids": {},
        "observation_ids": {},
        "diagnostic_observation_ids": set(),
        "local_group_count": 0,
        "local_group_bound": 0,
        "candidate_bound": 1,
    }
    if not isinstance(projection, Mapping):
        _error(errors, "projection_not_object", "projection must be a mapping")
        context["valid"] = False
        return context
    context["schema"] = projection.get("schema")
    context["source_schema"] = projection.get("source_schema")
    context["archive_id"] = projection.get("archive_id")
    context["snapshot_id"] = projection.get("snapshot_id")
    context["input_hash"] = projection.get("input_hash")
    if context["schema"] != INPUT_SCHEMA:
        _error(errors, "input_schema_mismatch", "projection schema is not the canonical input schema")
    if context["source_schema"] != OBSERVER_SCHEMA:
        _error(errors, "input_source_schema_mismatch", "projection source_schema is not the observer schema")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if not _nonempty_string(context[field]):
            _error(errors, f"input_{field}_invalid", f"projection.{field} must be a non-empty string")
    try:
        context["projection_digest"] = "projection:" + _digest(
            {key: value for key, value in projection.items() if key != "input_hash"}
        )
    except (TypeError, ValueError):
        _error(errors, "projection_digest_uncomputable", "projection is not canonically JSON serializable")

    artifacts = projection.get("artifacts")
    if not isinstance(artifacts, list):
        _error(errors, "artifacts_not_list", "projection.artifacts must be a list")
        artifacts = []
    for index, raw in enumerate(artifacts):
        if not isinstance(raw, Mapping):
            _error(errors, "artifact_not_object", f"artifact[{index}] is not an object")
            continue
        ref = raw.get("artifact_ref")
        if not _nonempty_string(ref):
            _error(errors, "artifact_ref_invalid", f"artifact[{index}].artifact_ref is invalid")
            continue
        if ref in context["artifact_refs"]:
            _error(errors, "duplicate_artifact_ref", f"duplicate artifact_ref:{ref}")
            continue
        if "archive_id" in raw and raw.get("archive_id") != context["archive_id"]:
            _error(errors, "archive_isolation", f"artifact_ref:{ref} belongs to another archive")
        context["artifact_refs"][ref] = raw
        content_id = raw.get("content_id")
        if _nonempty_string(content_id):
            context["content_ids"].setdefault(content_id, []).append(ref)

    observations = projection.get("candidate_observations")
    if not isinstance(observations, list):
        _error(errors, "candidate_observations_not_list", "projection.candidate_observations must be a list")
        observations = []
    for index, raw in enumerate(observations):
        if not isinstance(raw, Mapping):
            _error(errors, "observation_not_object", f"observation[{index}] is not an object")
            continue
        observation_id = raw.get("observation_id")
        refs = raw.get("artifact_refs")
        if not _nonempty_string(observation_id):
            _error(errors, "observation_id_invalid", f"observation[{index}].observation_id is invalid")
            continue
        if observation_id in context["observation_ids"]:
            _error(errors, "duplicate_observation_id", f"duplicate observation_id:{observation_id}")
            continue
        if raw.get("record_type") != "candidate_observation" or raw.get("status") != "candidate":
            _error(errors, "observation_not_candidate", f"observation:{observation_id} is not a candidate observation")
        if not _nonempty_string(raw.get("observation_type")):
            _error(errors, "observation_type_invalid", f"observation:{observation_id} type is invalid")
        if not isinstance(refs, list) or any(not _nonempty_string(ref) for ref in refs):
            _error(errors, "observation_refs_invalid", f"observation[{index}].artifact_refs is invalid")
        else:
            for ref in refs:
                if ref not in context["artifact_refs"]:
                    _error(errors, "observation_ref_dangling", f"observation:{observation_id} -> {ref}")
        context["observation_ids"][observation_id] = raw
        if raw.get("observation_type") in _DIAGNOSTIC_TYPES:
            context["diagnostic_observation_ids"].add(observation_id)

    for observation_id, raw in context["observation_ids"].items():
        evidence = raw.get("evidence")
        if not isinstance(evidence, Mapping) or not _is_json_value(evidence):
            _error(errors, "observation_evidence_invalid", f"observation:{observation_id} evidence is invalid")
            continue
        for embedded in _embedded_refs(evidence):
            if embedded not in context["artifact_refs"] and embedded not in context["observation_ids"]:
                _error(errors, "observation_evidence_ref_dangling", f"observation:{observation_id} -> {embedded}")

    local_groups = projection.get("local_groups")
    if local_groups is not None and not isinstance(local_groups, list):
        _error(errors, "local_groups_not_list", "projection.local_groups must be a list when present")
        local_groups = []
    local_group_bound = 0
    if isinstance(local_groups, list) and local_groups:
        for index, raw in enumerate(local_groups):
            if not isinstance(raw, Mapping):
                _error(errors, "local_group_not_object", f"local_groups[{index}] is not an object")
                continue
            refs = raw.get("artifact_refs")
            if not isinstance(refs, list):
                _error(errors, "local_group_refs_invalid", f"local_groups[{index}].artifact_refs is invalid")
                continue
            unique_refs = set()
            for ref in refs:
                if not _nonempty_string(ref) or ref not in context["artifact_refs"]:
                    _error(errors, "local_group_ref_dangling", f"local_groups[{index}] contains an unresolved artifact_ref")
                else:
                    unique_refs.add(ref)
            local_group_bound += len(unique_refs) * max(0, len(unique_refs) - 1) * len(RELATION_INVERSES)
    non_diagnostic_observations = [
        observation_id
        for observation_id, raw in context["observation_ids"].items()
        if raw.get("observation_type") not in _DIAGNOSTIC_TYPES
    ]
    context["local_group_count"] = len(local_groups) if local_groups else max(1, len(non_diagnostic_observations))
    artifact_count = len(context["artifact_refs"])
    context["local_group_bound"] = local_group_bound
    global_bound = artifact_count * max(0, artifact_count - 1) * len(RELATION_INVERSES)
    context["candidate_bound"] = max(1, local_group_bound if local_groups else global_bound)
    context["valid"] = not errors
    return context


def _payload_context(payload: Any, errors: list[dict[str, Any]]) -> dict[str, Any]:
    context: dict[str, Any] = {
        "valid": True,
        "schema": None,
        "source_schema": None,
        "archive_id": None,
        "snapshot_id": None,
        "input_hash": None,
        "candidates": [],
        "truncated": False,
        "truncation": None,
        "coverage": None,
        "reconciliation": None,
        "skipped_observation_summary": None,
    }
    if not isinstance(payload, Mapping):
        _error(errors, "payload_not_object", "payload must be a mapping")
        context["valid"] = False
        return context
    payload_keys = set(payload)
    allowed_keys = _PAYLOAD_REQUIRED_FIELDS | _PAYLOAD_OPTIONAL_FIELDS
    unknown_keys = sorted(str(key) for key in payload_keys - allowed_keys)
    if unknown_keys:
        _error(errors, "payload_fields_unknown", ",".join(unknown_keys))
    context["schema"] = payload.get("schema")
    context["source_schema"] = payload.get("source_schema")
    if context["source_schema"] is None:
        source = payload.get("source")
        if isinstance(source, Mapping):
            context["source_schema"] = source.get("schema")
        elif isinstance(source, str):
            context["source_schema"] = source
    context["archive_id"] = payload.get("archive_id")
    context["snapshot_id"] = payload.get("snapshot_id")
    context["input_hash"] = payload.get("input_hash")
    context["candidates"] = payload.get("candidates")
    context["truncated"] = payload.get("truncated", False)
    context["truncation"] = payload.get("truncation")
    context["coverage"] = payload.get("coverage")
    context["reconciliation"] = payload.get("reconciliation")
    context["skipped_observation_summary"] = payload.get("skipped_observation_summary")
    if context["schema"] != CANDIDATE_SCHEMA:
        _error(errors, "candidate_schema_mismatch", "payload schema is not the canonical candidate schema")
    if not _nonempty_string(context["source_schema"]):
        _error(errors, "source_schema_missing", "payload source_schema is required")
    if not _nonempty_string(context["archive_id"]):
        _error(errors, "payload_archive_id_invalid", "payload archive_id is invalid")
    if not _nonempty_string(context["snapshot_id"]):
        _error(errors, "payload_snapshot_id_invalid", "payload snapshot_id is invalid")
    if not _nonempty_string(context["input_hash"]):
        _error(errors, "payload_input_hash_invalid", "payload input_hash is invalid")
    if not isinstance(context["candidates"], list):
        _error(errors, "candidates_not_list", "payload.candidates must be a list")
        context["candidates"] = []
    if not isinstance(context["truncated"], bool):
        _error(errors, "truncated_invalid", "payload truncated must be boolean")
        context["truncated"] = False
    if context["truncated"]:
        truncation = context["truncation"]
        if not isinstance(truncation, Mapping):
            _error(errors, "truncation_missing", "truncated payload needs a truncation declaration")
        else:
            if not _nonempty_string(truncation.get("reason")):
                _error(errors, "truncation_reason_missing", "truncation.reason is required")
            omitted = truncation.get("omitted_count")
            if isinstance(omitted, bool) or not isinstance(omitted, int) or omitted <= 0:
                _error(errors, "truncation_count_invalid", "truncation.omitted_count must be positive")
    elif context["truncation"] not in (None, {}):
        _error(errors, "unexpected_truncation", "truncation must be absent when truncated is false")
    context["valid"] = not errors
    return context


def _validate_canonical_payload_fields(
    payload_context: Mapping[str, Any],
    projection_context: Mapping[str, Any],
    candidate_count: int,
    errors: list[dict[str, Any]],
) -> dict[str, bool]:
    """Validate the canonical inference summaries without interpreting them."""

    summary = payload_context.get("skipped_observation_summary")
    summary_ok = True
    limit_count = 0
    if summary is not None:
        if not isinstance(summary, Mapping):
            summary_ok = False
            _error(errors, "skipped_summary_invalid", "skipped_observation_summary must be an object")
        else:
            for key, entry in summary.items():
                if not isinstance(key, str) or not isinstance(entry, Mapping):
                    summary_ok = False
                    _error(errors, "skipped_summary_entry_invalid", "skipped summary entries must be objects")
                    continue
                if set(entry) not in ({"count", "reason"}, {"count", "reason", "observation_ids"}):
                    summary_ok = False
                    _error(errors, "skipped_summary_fields_invalid", f"skipped summary fields invalid:{key}")
                    continue
                count = entry.get("count")
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    summary_ok = False
                    _error(errors, "skipped_summary_count_invalid", f"skipped summary count invalid:{key}")
                if not _nonempty_string(entry.get("reason")):
                    summary_ok = False
                    _error(errors, "skipped_summary_reason_invalid", f"skipped summary reason invalid:{key}")
                observation_ids = entry.get("observation_ids")
                if observation_ids is not None:
                    if not isinstance(observation_ids, list) or any(not _nonempty_string(item) for item in observation_ids) or observation_ids != sorted(set(observation_ids)):
                        summary_ok = False
                        _error(errors, "skipped_summary_observation_ids_invalid", f"skipped summary observation_ids invalid:{key}")
                    elif any(item not in projection_context["observation_ids"] for item in observation_ids):
                        summary_ok = False
                        _error(errors, "skipped_summary_observation_ref_dangling", f"skipped summary observation_ids unresolved:{key}")
                if key == "limit_reached" and isinstance(count, int) and not isinstance(count, bool):
                    limit_count = count
    coverage = payload_context.get("coverage")
    coverage_ok = True
    canonical_truncated = False
    if coverage is not None:
        expected_fields = {
            "limits", "projection_artifacts", "projection_observations", "limit_reached_observations",
            "attempted_candidates", "generated_candidates", "truncated", "truncated_groups",
            "truncated_pair_count", "coverage_incomplete",
        }
        if not isinstance(coverage, Mapping) or set(coverage) != expected_fields:
            coverage_ok = False
            _error(errors, "coverage_fields_invalid", "coverage fields do not match the canonical contract")
        else:
            limits = coverage["limits"]
            if not isinstance(limits, Mapping) or set(limits) != {"max_candidates", "max_pairs_per_group", "max_local_group_pairs"}:
                coverage_ok = False
                _error(errors, "coverage_limits_invalid", "coverage.limits fields are invalid")
            else:
                for key in limits:
                    value = limits[key]
                    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                        coverage_ok = False
                        _error(errors, "coverage_limit_invalid", f"coverage.limits.{key} must be positive")
            for key in (
                "projection_artifacts", "projection_observations", "limit_reached_observations",
                "attempted_candidates", "generated_candidates", "truncated_pair_count",
            ):
                value = coverage[key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    coverage_ok = False
                    _error(errors, "coverage_count_invalid", f"coverage.{key} must be non-negative")
            if coverage["projection_artifacts"] != len(projection_context["artifact_refs"]):
                coverage_ok = False
                _error(errors, "coverage_artifact_count_mismatch", "coverage artifact count does not match projection")
            if coverage["projection_observations"] != len(projection_context["observation_ids"]):
                coverage_ok = False
                _error(errors, "coverage_observation_count_mismatch", "coverage observation count does not match projection")
            if coverage["generated_candidates"] != candidate_count or coverage["attempted_candidates"] < candidate_count:
                coverage_ok = False
                _error(errors, "coverage_candidate_count_mismatch", "coverage candidate counts do not match payload")
            if coverage["limit_reached_observations"] != limit_count:
                coverage_ok = False
                _error(errors, "coverage_limit_count_mismatch", "coverage limit count does not match summary")
            groups = coverage["truncated_groups"]
            if not isinstance(groups, list) or any(not _nonempty_string(item) for item in groups) or groups != sorted(set(groups)):
                coverage_ok = False
                _error(errors, "coverage_truncated_groups_invalid", "coverage.truncated_groups must be sorted unique strings")
            if not isinstance(coverage["truncated"], bool) or not isinstance(coverage["coverage_incomplete"], bool):
                coverage_ok = False
                _error(errors, "coverage_flags_invalid", "coverage flags must be boolean")
            canonical_truncated = bool(groups or coverage["attempted_candidates"] > limits.get("max_candidates", 0))
            if coverage["truncated"] != canonical_truncated:
                coverage_ok = False
                _error(errors, "coverage_truncation_mismatch", "coverage.truncated is inconsistent with its declaration")
            if coverage["coverage_incomplete"] != bool(limit_count):
                coverage_ok = False
                _error(errors, "coverage_completeness_mismatch", "coverage completeness is inconsistent with diagnostics")
    reconciliation = payload_context.get("reconciliation")
    reconciliation_ok = True
    if reconciliation is not None:
        expected_fields = {
            "candidate_count", "candidate_ids_unique", "endpoint_refs_resolved", "evidence_refs_resolved",
            "truth_promotions", "deterministic_order", "status_values",
        }
        if not isinstance(reconciliation, Mapping) or set(reconciliation) != expected_fields:
            reconciliation_ok = False
            _error(errors, "reconciliation_fields_invalid", "reconciliation fields do not match the canonical contract")
        else:
            if reconciliation["candidate_count"] != candidate_count:
                reconciliation_ok = False
                _error(errors, "reconciliation_candidate_count_mismatch", "reconciliation candidate count does not match payload")
            for key in ("candidate_ids_unique", "endpoint_refs_resolved", "evidence_refs_resolved", "deterministic_order"):
                if reconciliation[key] is not True:
                    reconciliation_ok = False
                    _error(errors, "reconciliation_boolean_failed", f"reconciliation.{key} must be true")
            if reconciliation["truth_promotions"] != 0:
                reconciliation_ok = False
                _error(errors, "reconciliation_truth_promotion", "reconciliation reports promoted truth")
            if reconciliation["status_values"] != sorted(ALLOWED_STATUSES):
                reconciliation_ok = False
                _error(errors, "reconciliation_status_values_invalid", "reconciliation status values are not canonical")
    return {
        "summary_ok": summary_ok,
        "coverage_ok": coverage_ok,
        "reconciliation_ok": reconciliation_ok,
        "canonical_truncated": canonical_truncated,
    }


def evaluate_relation_payload(projection: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic falsification report without mutating inputs."""

    projection_errors: list[dict[str, Any]] = []
    payload_errors: list[dict[str, Any]] = []
    projection_context = _projection_context(projection, projection_errors)
    payload_context = _payload_context(payload, payload_errors)
    errors = projection_errors + payload_errors
    candidates = payload_context["candidates"]
    canonical_fields = _validate_canonical_payload_fields(
        payload_context, projection_context, len(candidates), errors
    )
    artifact_refs = set(projection_context["artifact_refs"])
    observation_ids = set(projection_context["observation_ids"])
    diagnostic_ids = set(projection_context["diagnostic_observation_ids"])
    content_ids = set(projection_context["content_ids"])
    candidate_ids: list[str] = []
    valid_candidates: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    edge_errors: list[str] = []
    required_fields_ok = True
    endpoints_ok = True
    evidence_ok = True
    inverse_ok = True
    statuses_ok = True
    self_edges_ok = True
    scores_ok = True
    diagnostics_ok = True
    id_recomputation_ok = True

    for index, raw in enumerate(candidates):
        if not isinstance(raw, Mapping):
            required_fields_ok = False
            _error(errors, "candidate_not_object", f"candidate[{index}] is not an object", index)
            continue
        candidate = dict(raw)
        if set(candidate) != CANDIDATE_FIELDS:
            required_fields_ok = False
            _error(errors, "candidate_fields_exact", f"candidate[{index}] fields do not match the exact contract", index)
            continue
        candidate_id = candidate.get("candidate_id")
        if not _nonempty_string(candidate_id):
            id_recomputation_ok = False
            _error(errors, "candidate_id_invalid", f"candidate[{index}].candidate_id is invalid", index)
        else:
            candidate_ids.append(candidate_id)
        source_ref = candidate.get("source_ref")
        target_ref = candidate.get("target_ref")
        for endpoint_name, endpoint in (("source_ref", source_ref), ("target_ref", target_ref)):
            if endpoint in content_ids:
                endpoints_ok = False
                _error(errors, "content_id_endpoint", f"candidate[{index}].{endpoint_name} uses content_id", index)
            elif endpoint not in artifact_refs:
                endpoints_ok = False
                _error(errors, "endpoint_dangling", f"candidate[{index}].{endpoint_name} does not resolve to artifact_ref", index)
            if endpoint in diagnostic_ids or endpoint in observation_ids:
                diagnostics_ok = False
                _error(errors, "diagnostic_endpoint", f"candidate[{index}].{endpoint_name} is not an artifact endpoint", index)
        if source_ref == target_ref:
            self_edges_ok = False
            _error(errors, "self_edge", f"candidate[{index}] has identical endpoints", index)

        relation = candidate.get("relation")
        inverse = candidate.get("inverse_relation")
        if relation in _DIAGNOSTIC_TYPES:
            diagnostics_ok = False
            _error(errors, "diagnostic_relation", f"candidate[{index}] diagnostic type cannot be a relation", index)
        if relation not in RELATION_INVERSES or inverse != RELATION_INVERSES.get(relation):
            inverse_ok = False
            _error(errors, "inverse_relation_invalid", f"candidate[{index}] inverse is not declared/correct", index)
        if candidate.get("status") not in ALLOWED_STATUSES:
            statuses_ok = False
            _error(errors, "promoted_or_invalid_status", f"candidate[{index}] status is not pending/unresolved", index)

        score = candidate.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
            scores_ok = False
            _error(errors, "score_out_of_range", f"candidate[{index}] score must be finite in [0,1]", index)

        for field in ("reason_codes", "evidence_refs", "evidence_for", "evidence_against", "alternatives", "missing_evidence"):
            if not isinstance(candidate.get(field), list):
                required_fields_ok = False
                _error(errors, "candidate_field_type", f"candidate[{index}].{field} must be a list", index)
        for field in ("reason_codes", "evidence_refs", "missing_evidence"):
            values = candidate.get(field)
            if isinstance(values, list):
                if any(not _nonempty_string(value) for value in values) or values != sorted(set(values)):
                    required_fields_ok = False
                    _error(errors, "candidate_list_not_canonical", f"candidate[{index}].{field} must be sorted unique strings", index)
        for field in ("evidence_for", "evidence_against", "alternatives"):
            if isinstance(candidate.get(field), list):
                for item in candidate[field]:
                    if not _is_json_value(item):
                        required_fields_ok = False
                        _error(errors, "candidate_evidence_not_json", f"candidate[{index}].{field} contains a non-JSON value", index)
        direct_evidence_refs = candidate.get("evidence_refs")
        if isinstance(direct_evidence_refs, list):
            for ref in direct_evidence_refs:
                if ref not in artifact_refs and ref not in observation_ids:
                    evidence_ok = False
                    _error(errors, "evidence_ref_dangling", f"candidate[{index}] evidence ref does not resolve:{ref}", index)
                if ref in content_ids:
                    evidence_ok = False
                    _error(errors, "content_id_evidence_ref", f"candidate[{index}] evidence ref is content_id", index)
                if ref in diagnostic_ids:
                    evidence_ok = False
                    _error(errors, "diagnostic_evidence_ref", f"candidate[{index}] evidence ref is diagnostic:{ref}", index)
        for embedded in _embedded_refs(candidate.get("evidence_for")) + _embedded_refs(candidate.get("evidence_against")) + _embedded_refs(candidate.get("alternatives")):
            if embedded not in artifact_refs and embedded not in observation_ids:
                evidence_ok = False
                _error(errors, "embedded_evidence_ref_dangling", f"candidate[{index}] embedded ref does not resolve:{embedded}", index)
            if embedded in diagnostic_ids:
                evidence_ok = False
                _error(errors, "diagnostic_evidence_ref", f"candidate[{index}] embedded evidence ref is diagnostic:{embedded}", index)

        missing_evidence = candidate.get("missing_evidence")
        next_probe = candidate.get("next_probe")
        if next_probe is not None and not _nonempty_string(next_probe):
            required_fields_ok = False
            _error(errors, "next_probe_invalid", f"candidate[{index}].next_probe must be null or a non-empty string", index)
        missing_evidence_required = isinstance(missing_evidence, list) and bool(missing_evidence)
        if (candidate.get("status") != PENDING or missing_evidence_required) and not _nonempty_string(next_probe):
            required_fields_ok = False
            _error(errors, "next_probe_missing", f"candidate[{index}].next_probe is required for unresolved evidence", index)

        if set(candidate) == CANDIDATE_FIELDS and _is_json_value(candidate):
            try:
                expected_id = candidate_id_for(candidate, str(projection_context["archive_id"]))
            except ArchiveRelationEvaluationError:
                expected_id = None
            if expected_id is None or candidate_id != expected_id:
                id_recomputation_ok = False
                _error(errors, "candidate_id_mismatch", f"candidate[{index}] ID does not match semantic fields", index)
        else:
            id_recomputation_ok = False

        if relation in RELATION_INVERSES and source_ref in artifact_refs and target_ref in artifact_refs:
            edge = (str(source_ref), str(relation), str(target_ref))
            reciprocal = (str(target_ref), RELATION_INVERSES[relation], str(source_ref))
            if edge in seen_edges:
                edge_errors.append(f"duplicate:{edge}")
            if reciprocal in seen_edges:
                edge_errors.append(f"forward_inverse_duplicate:{edge}")
            seen_edges.add(edge)
        if set(candidate) == CANDIDATE_FIELDS:
            valid_candidates.append(candidate)

    duplicate_ids = sorted({candidate_id for candidate_id in candidate_ids if candidate_ids.count(candidate_id) > 1})
    if duplicate_ids:
        id_recomputation_ok = False
        _error(errors, "duplicate_candidate_id", ",".join(duplicate_ids))
    if edge_errors:
        _error(errors, "duplicate_semantic_edge", ";".join(sorted(edge_errors)))

    candidate_count = len(candidates)
    bound = int(projection_context["candidate_bound"])
    truncated = bool(payload_context["truncated"] or canonical_fields["canonical_truncated"])
    truncation_declared = (
        isinstance(payload_context["truncation"], Mapping)
        and _nonempty_string(payload_context["truncation"].get("reason"))
        and isinstance(payload_context["truncation"].get("omitted_count"), int)
        and payload_context["truncation"].get("omitted_count", 0) > 0
    ) or canonical_fields["canonical_truncated"]
    bounded = candidate_count <= bound or (truncated and truncation_declared)
    if not bounded:
        _error(errors, "candidate_count_exceeds_bound", f"{candidate_count}>{bound} without truncation declaration")

    order_deterministic = len(candidate_ids) == len(candidates) and candidate_ids == sorted(candidate_ids)
    if not order_deterministic:
        _error(errors, "candidate_order_nondeterministic", "candidates must be ordered by candidate_id")

    duplicate_groups = {
        content_id: sorted(refs)
        for content_id, refs in projection_context["content_ids"].items()
        if len(refs) > 1
    }
    duplicate_refs_preserved = all(len(refs) == len(set(refs)) and len(refs) > 1 for refs in duplicate_groups.values())

    checks = {
        "input_contract": _check(not projection_errors, {"schema": projection_context["schema"], "errors": len(projection_errors)}),
        "source_contract": _check(payload_context["source_schema"] == INPUT_SCHEMA, {"source_schema": payload_context["source_schema"]}),
        "candidate_contract": _check(not payload_errors, {"schema": payload_context["schema"], "errors": len(payload_errors)}),
        "archive_match": _check(payload_context["archive_id"] == projection_context["archive_id"], {"projection": projection_context["archive_id"], "payload": payload_context["archive_id"]}),
        "snapshot_match": _check(payload_context["snapshot_id"] == projection_context["snapshot_id"], {"projection": projection_context["snapshot_id"], "payload": payload_context["snapshot_id"]}),
        "input_hash_match": _check(payload_context["input_hash"] == projection_context["input_hash"], {"projection": projection_context["input_hash"], "payload": payload_context["input_hash"]}),
        "candidate_ids": _check(id_recomputation_ok and not duplicate_ids, {"algorithm": CANDIDATE_ID_ALGORITHM, "duplicate_ids": duplicate_ids}),
        "endpoints_resolve": _check(endpoints_ok, {"artifact_ref_count": len(artifact_refs)}),
        "evidence_refs_resolve": _check(evidence_ok, {"observation_id_count": len(observation_ids)}),
        "inverse_relations": _check(inverse_ok, {"vocabulary_size": len(RELATION_INVERSES)}),
        "no_promoted_truth": _check(statuses_ok, {"allowed_statuses": sorted(ALLOWED_STATUSES)}),
        "no_self_edges": _check(self_edges_ok, {"symmetric_relations": sorted(SYMMETRIC_RELATIONS), "policy": "reject_all_self_edges"}),
        "no_duplicate_edges": _check(not edge_errors, {"edge_errors": sorted(edge_errors)}),
        "finite_scores": _check(scores_ok, {"range": [0.0, 1.0]}),
        "required_candidate_fields": _check(required_fields_ok, {"fields": sorted(CANDIDATE_FIELDS)}),
        "coverage": _check(canonical_fields["coverage_ok"], {"present": payload_context["coverage"] is not None}),
        "reconciliation": _check(canonical_fields["reconciliation_ok"], {"present": payload_context["reconciliation"] is not None}),
        "skipped_observation_summary": _check(canonical_fields["summary_ok"], {"present": payload_context["skipped_observation_summary"] is not None}),
        "diagnostics_not_candidates": _check(diagnostics_ok, {"diagnostic_types": sorted(_DIAGNOSTIC_TYPES)}),
        "candidate_count_bounded": _check(bounded, {"candidate_count": candidate_count, "candidate_bound": bound, "local_group_bound": projection_context["local_group_bound"], "truncated": truncated}),
        "duplicate_physical_refs": _check(duplicate_refs_preserved, {"duplicate_content_groups": duplicate_groups}),
        "archive_isolation": _check(not any(item.get("code") == "archive_isolation" for item in projection_errors), {"archive_id": projection_context["archive_id"]}),
        "deterministic_order": _check(order_deterministic, {"ordered_by": "candidate_id"}),
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "candidate_id_algorithm": CANDIDATE_ID_ALGORITHM,
        "input_hash_algorithm": INPUT_HASH_ALGORITHM,
        "projection_digest_algorithm": PROJECTION_DIGEST_ALGORITHM,
        "source": {
            "input_schema": projection_context["schema"],
            "projection_source_schema": projection_context["source_schema"],
            "candidate_schema": payload_context["schema"],
            "archive_id": projection_context["archive_id"],
            "snapshot_id": projection_context["snapshot_id"],
            "input_hash": projection_context["input_hash"],
            "projection_digest": projection_context["projection_digest"],
        },
        "checks": checks,
        "metrics": {
            "candidate_count": candidate_count,
            "candidate_bound": bound,
            "local_group_bound": projection_context["local_group_bound"],
            "artifact_ref_count": len(artifact_refs),
            "observation_id_count": len(observation_ids),
            "local_group_count": projection_context["local_group_count"],
            "duplicate_content_group_count": len(duplicate_groups),
            "truncated": truncated,
            "canonical_summaries_present": all(
                payload_context[field] is not None
                for field in ("coverage", "reconciliation", "skipped_observation_summary")
            ),
        },
        "errors": _sort_errors(errors),
    }
    report["passed"] = not report["errors"] and all(check["passed"] for check in checks.values())
    report["valid"] = bool(report["passed"])
    report["status"] = "pass" if report["valid"] else "fail"
    report_hash_material = dict(report)
    report_hash = "report:" + _digest(report_hash_material)
    report["report_hash"] = report_hash
    return report


def assert_relation_payload(projection: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    """Return ``True`` or raise with the complete deterministic report."""

    report = evaluate_relation_payload(projection, payload)
    if not report["passed"]:
        codes = ",".join(error["code"] for error in report["errors"])
        raise ArchiveRelationEvaluationError(f"archive_relation_payload_rejected:{codes}", report)
    return True


__all__ = [
    "ALGORITHM_VERSION",
    "ALLOWED_STATUSES",
    "ArchiveRelationEvaluationError",
    "CANDIDATE_ID_ALGORITHM",
    "CANDIDATE_SCHEMA",
    "INPUT_HASH_ALGORITHM",
    "INPUT_SCHEMA",
    "OBSERVER_SCHEMA",
    "PROJECTION_DIGEST_ALGORITHM",
    "RELATION_INVERSES",
    "REPORT_SCHEMA",
    "SYMMETRIC_RELATIONS",
    "assert_relation_payload",
    "candidate_id_for",
    "candidate_semantic_fields",
    "evaluate_relation_payload",
    "input_hash_for_projection",
    "inverse_relation",
]
