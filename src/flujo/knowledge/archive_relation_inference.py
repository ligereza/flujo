"""Bounded, evidence-first relation candidates over the Stage 2A projection.

This module does not reconstruct works, projects or series.  It emits only
typed, deterministic candidates whose endpoints are physical
``artifact_ref`` values already present in the archive projection.  Candidate
status is deliberately limited to ``pending_relation`` and
``unresolved_candidate``; no relation is promoted to truth here.
"""

from __future__ import annotations

import hashlib
import math
from itertools import combinations
from typing import Any, Mapping

from ._contract_helpers import stable_json as _stable_json

from .project_reconstruction import (
    RELATION_INVERSES,
    REL_CONTAINS,
    REL_IDENTITY_UNDECIDED,
)


SCHEMA = "mak-archive-relation-candidates-v1"
PROJECTION_SCHEMA = "mak-archive-reconstruction-input-v1"
PENDING_RELATION = "pending_relation"
UNRESOLVED_CANDIDATE = "unresolved_candidate"
ALLOWED_STATUSES = frozenset({PENDING_RELATION, UNRESOLVED_CANDIDATE})

ARCHIVE_RELATION_INVERSES = dict(RELATION_INVERSES)
ARCHIVE_RELATION_INVERSES.update({
    "describes": "described_by",
    "described_by": "describes",
    "manifestation_of": "has_manifestation",
    "has_manifestation": "manifestation_of",
    "component_of": "has_component",
    "has_component": "component_of",
    "version_of": "has_version",
    "has_version": "version_of",
    "same_series_candidate": "same_series_candidate",
})

MAX_CANDIDATES = 512
MAX_PAIRS_PER_GROUP = 32
MAX_LOCAL_GROUP_PAIRS = 64
_CANDIDATE_SEMANTIC_FIELDS = (
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
)


class ArchiveRelationInferenceError(ValueError):
    """Invalid Stage 2A input or invalid relation-candidate payload."""


def _require_projection(projection: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(projection, Mapping):
        raise ArchiveRelationInferenceError("projection_must_be_mapping")
    required = {
        "schema", "source_schema", "archive_id", "snapshot_id", "limits", "input_hash",
        "artifacts", "candidate_observations", "artifacts_by_parent", "artifacts_by_content",
        "native_anchor_refs", "probable_output_refs", "candidate_observation_ids", "reconciliation",
    }
    if set(projection) != required:
        raise ArchiveRelationInferenceError("projection_invalid_field_set")
    if projection["schema"] != PROJECTION_SCHEMA:
        raise ArchiveRelationInferenceError("projection_bad_schema")
    if projection["source_schema"] != "mak-archive-observation-batch-v1":
        raise ArchiveRelationInferenceError("projection_bad_source_schema")
    if not isinstance(projection["archive_id"], str) or not projection["archive_id"]:
        raise ArchiveRelationInferenceError("projection_archive_id_invalid")
    if not isinstance(projection["snapshot_id"], str) or not projection["snapshot_id"]:
        raise ArchiveRelationInferenceError("projection_snapshot_id_invalid")
    if not isinstance(projection["input_hash"], str) or not projection["input_hash"]:
        raise ArchiveRelationInferenceError("projection_input_hash_invalid")
    artifacts = projection["artifacts"]
    observations = projection["candidate_observations"]
    if not isinstance(artifacts, list) or not isinstance(observations, list):
        raise ArchiveRelationInferenceError("projection_lists_invalid")
    artifact_by_ref: dict[str, dict[str, Any]] = {}
    artifact_by_path: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise ArchiveRelationInferenceError("projection_artifact_invalid")
        for key in (
            "artifact_id", "physical_id", "artifact_ref", "relative_path", "parent_path",
            "kind", "availability", "family", "media_type", "content_id", "derived_flags",
        ):
            if key not in artifact:
                raise ArchiveRelationInferenceError(f"projection_artifact_missing_{key}")
        ref = artifact["artifact_ref"]
        path = artifact["relative_path"]
        if not isinstance(ref, str) or not ref or ref in artifact_by_ref:
            raise ArchiveRelationInferenceError("projection_artifact_ref_invalid")
        if not isinstance(path, str) or not path or path in artifact_by_path:
            raise ArchiveRelationInferenceError("projection_artifact_path_invalid")
        artifact_by_ref[ref] = dict(artifact)
        artifact_by_path[path] = dict(artifact)
    observation_by_id: dict[str, dict[str, Any]] = {}
    for observation in observations:
        if not isinstance(observation, Mapping):
            raise ArchiveRelationInferenceError("projection_observation_invalid")
        if set(observation) != {
            "record_type", "observation_id", "observation_type", "status",
            "artifact_refs", "evidence",
        }:
            raise ArchiveRelationInferenceError("projection_observation_invalid_field_set")
        observation_id = observation["observation_id"]
        if not isinstance(observation_id, str) or not observation_id or observation_id in observation_by_id:
            raise ArchiveRelationInferenceError("projection_observation_id_invalid")
        if observation["record_type"] != "candidate_observation" or observation["status"] != "candidate":
            raise ArchiveRelationInferenceError("projection_observation_not_candidate")
        refs = observation["artifact_refs"]
        if not isinstance(refs, list) or refs != sorted(set(refs)):
            raise ArchiveRelationInferenceError("projection_observation_refs_invalid")
        if any(ref not in artifact_by_ref for ref in refs):
            raise ArchiveRelationInferenceError("projection_observation_ref_unresolved")
        if not isinstance(observation["evidence"], Mapping):
            raise ArchiveRelationInferenceError("projection_observation_evidence_invalid")
        observation_by_id[observation_id] = dict(observation)
    if projection["candidate_observation_ids"] != sorted(observation_by_id):
        raise ArchiveRelationInferenceError("projection_observation_index_invalid")
    for key in ("native_anchor_refs", "probable_output_refs"):
        refs = projection[key]
        if not isinstance(refs, list) or refs != sorted(set(refs)):
            raise ArchiveRelationInferenceError(f"projection_{key}_invalid")
        if any(ref not in artifact_by_ref for ref in refs):
            raise ArchiveRelationInferenceError(f"projection_{key}_unresolved")
    for index_name in ("artifacts_by_parent", "artifacts_by_content"):
        index = projection[index_name]
        if not isinstance(index, Mapping):
            raise ArchiveRelationInferenceError(f"projection_{index_name}_invalid")
        for key, refs in index.items():
            if not isinstance(key, str) or not isinstance(refs, list) or refs != sorted(set(refs)):
                raise ArchiveRelationInferenceError(f"projection_{index_name}_ordering_invalid")
            if any(ref not in artifact_by_ref for ref in refs):
                raise ArchiveRelationInferenceError(f"projection_{index_name}_unresolved")
    return dict(projection), artifact_by_ref, observation_by_id


def _common_parent(left: str, right: str) -> str:
    left_parts = [part for part in left.split("/") if part]
    right_parts = [part for part in right.split("/") if part]
    common: list[str] = []
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part != right_part:
            break
        common.append(left_part)
    return "/".join(common)


def _evidence_sort_key(value: str) -> str:
    return str(value)


def candidate_id_for(candidate: Mapping[str, Any], archive_id: str) -> str:
    """Return the canonical ID over every semantic candidate field.

    ``snapshot_id`` is intentionally absent.  A candidate's identity is the
    archive namespace plus its complete semantic payload, matching the
    independent evaluator contract.
    """

    if not isinstance(candidate, Mapping):
        raise ArchiveRelationInferenceError("candidate_semantic_fields_invalid")
    if not isinstance(archive_id, str) or not archive_id:
        raise ArchiveRelationInferenceError("candidate_archive_id_invalid")
    try:
        semantic = {"archive_id": archive_id}
        semantic.update({field: candidate[field] for field in _CANDIDATE_SEMANTIC_FIELDS})
        encoded = _stable_json(semantic).encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise ArchiveRelationInferenceError("candidate_semantic_fields_not_json") from error
    return "candidate:" + hashlib.sha256(encoded).hexdigest()


def _candidate(
    archive_id: str,
    snapshot_id: str,
    *,
    source_ref: str,
    relation: str,
    target_ref: str,
    status: str,
    score: float,
    reason_codes: list[str],
    evidence_refs: list[str],
    evidence_for: list[str],
    evidence_against: list[str],
    alternatives: list[str],
    missing_evidence: list[str],
    next_probe: str | None,
) -> dict[str, Any]:
    reason_codes = sorted(set(reason_codes))
    evidence_refs = sorted(set(evidence_refs), key=_evidence_sort_key)
    evidence_for = sorted(set(evidence_for))
    evidence_against = sorted(set(evidence_against))
    alternatives = sorted(set(alternatives))
    missing_evidence = sorted(set(missing_evidence))
    if relation not in ARCHIVE_RELATION_INVERSES:
        raise ArchiveRelationInferenceError(f"relation_without_inverse:{relation}")
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ArchiveRelationInferenceError("candidate_score_invalid")
    candidate = {
        "candidate_id": "",
        "source_ref": source_ref,
        "relation": relation,
        "target_ref": target_ref,
        "inverse_relation": ARCHIVE_RELATION_INVERSES[relation],
        "status": status,
        "score": float(score),
        "reason_codes": reason_codes,
        "evidence_refs": evidence_refs,
        "evidence_for": evidence_for,
        "evidence_against": evidence_against,
        "alternatives": alternatives,
        "missing_evidence": missing_evidence,
        "next_probe": next_probe,
    }
    candidate["candidate_id"] = candidate_id_for(candidate, archive_id)
    return candidate


def _pairwise_refs(refs: list[str], limit: int) -> tuple[list[tuple[str, str]], bool, int]:
    pairs = list(combinations(sorted(refs), 2))
    return pairs[:limit], len(pairs) > limit, max(0, len(pairs) - limit)


def _skip(summary: dict[str, dict[str, Any]], key: str, reason: str, observation_id: str | None = None) -> None:
    entry = summary.setdefault(key, {"count": 0, "reason": reason})
    entry["count"] += 1
    if observation_id is not None and key != "limit_reached":
        entry.setdefault("observation_ids", []).append(observation_id)


def _sort_skip_summary(summary: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for key in sorted(summary):
        entry = dict(summary[key])
        if "observation_ids" in entry:
            entry["observation_ids"] = sorted(set(entry["observation_ids"]))
        output[key] = entry
    return output


def infer_archive_relations(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Infer bounded relation candidates from a Stage 2A projection."""

    projection, artifact_by_ref, observation_by_id = _require_projection(projection)
    archive_id = str(projection["archive_id"])
    snapshot_id = str(projection["snapshot_id"])
    candidates: list[dict[str, Any]] = []
    candidate_ids: set[str] = set()
    skipped: dict[str, dict[str, Any]] = {}
    truncated_groups: set[str] = set()
    truncated_pairs = 0
    attempted_candidates = 0

    def emit(candidate: dict[str, Any], group: str) -> None:
        nonlocal attempted_candidates
        attempted_candidates += 1
        if len(candidates) >= MAX_CANDIDATES:
            truncated_groups.add(group)
            return
        if candidate["candidate_id"] in candidate_ids:
            raise ArchiveRelationInferenceError("candidate_id_collision")
        candidates.append(candidate)
        candidate_ids.add(candidate["candidate_id"])

    # 1. Physical parent-child containment, never a project claim.
    for child in sorted(artifact_by_ref.values(), key=lambda item: item["artifact_ref"]):
        parent_path = str(child["parent_path"])
        parent = next((item for item in artifact_by_ref.values()
                       if item["relative_path"] == parent_path and item["kind"] == "directory"), None)
        if parent is None:
            continue
        emit(_candidate(
            archive_id, snapshot_id,
            source_ref=str(parent["artifact_ref"]), relation=REL_CONTAINS,
            target_ref=str(child["artifact_ref"]), status=PENDING_RELATION, score=1.0,
            reason_codes=["physical_parent_child"],
            evidence_refs=[str(parent["artifact_ref"]), str(child["artifact_ref"])],
            evidence_for=["relative_path_parent_matches_directory"],
            evidence_against=[], alternatives=["nested_asset_not_project"],
            missing_evidence=[], next_probe="none_required",
        ), "parent_child")

    # 2. Exact byte groups are still separate physical artifacts.
    for content_id, refs in sorted(projection["artifacts_by_content"].items()):
        if len(refs) < 2:
            continue
        pairs, truncated, omitted = _pairwise_refs(list(refs), MAX_PAIRS_PER_GROUP)
        if truncated:
            truncated_groups.add(f"content:{content_id}")
            truncated_pairs += omitted
        for source_ref, target_ref in pairs:
            emit(_candidate(
                archive_id, snapshot_id,
                source_ref=source_ref, relation=REL_IDENTITY_UNDECIDED,
                target_ref=target_ref, status=UNRESOLVED_CANDIDATE, score=0.82,
                reason_codes=["exact_content_shared", "physical_artifacts_distinct"],
                evidence_refs=[source_ref, target_ref],
                evidence_for=["content_id_equal"],
                evidence_against=["content_identity_is_not_work_identity"],
                alternatives=["same_content", "same_work_candidate", "duplicate_render_candidate"],
                missing_evidence=["native_reference_or_export_witness"],
                next_probe="compare_native_references_before_identity_claim",
            ), f"content:{content_id}")

    path_by_ref = {ref: str(artifact["relative_path"]) for ref, artifact in artifact_by_ref.items()}
    ref_by_path = {path: ref for ref, path in path_by_ref.items()}

    # 3. Observer sidecar candidates are the only source of describes edges.
    for observation_id, observation in sorted(observation_by_id.items()):
        observation_type = str(observation["observation_type"])
        refs = [str(ref) for ref in observation["artifact_refs"]]
        evidence = observation["evidence"]
        if observation_type == "sidecar_candidate":
            sidecar_path = evidence.get("sidecar") if isinstance(evidence, Mapping) else None
            target_paths = evidence.get("targets", []) if isinstance(evidence, Mapping) else []
            source_ref = ref_by_path.get(str(sidecar_path)) if sidecar_path else None
            target_refs = [ref_by_path[path] for path in target_paths if path in ref_by_path]
            target_refs = sorted(set(ref for ref in target_refs if ref != source_ref))
            if source_ref is None or not target_refs:
                _skip(skipped, "sidecar_candidate", "sidecar_source_or_target_unresolved", observation_id)
                continue
            for target_ref in target_refs:
                emit(_candidate(
                    archive_id, snapshot_id,
                    source_ref=source_ref, relation="describes", target_ref=target_ref,
                    status=PENDING_RELATION, score=0.9,
                    reason_codes=["observer_sidecar_candidate", "declared_sidecar_target"],
                    evidence_refs=[observation_id, source_ref, target_ref],
                    evidence_for=["observer_declared_sibling_target", "sidecar_ref_resolved"],
                    evidence_against=[], alternatives=["unresolved_attachment"],
                    missing_evidence=[], next_probe="read_sidecar_semantics",
                ), f"observation:{observation_id}")
            continue

        # 4. Sequence observations may propose a pair but never a synthetic node
        # or a promoted series. Only readable physical files are eligible.
        if observation_type == "numbered_sequence_candidate":
            valid_refs = [
                ref for ref in refs
                if ref in artifact_by_ref
                and artifact_by_ref[ref]["kind"] == "file"
                and artifact_by_ref[ref]["availability"] == "available"
            ]
            if len(valid_refs) < 2:
                _skip(skipped, "numbered_sequence_candidate", "no_valid_artifact_target", observation_id)
                continue
            pairs, truncated, omitted = _pairwise_refs(valid_refs, MAX_PAIRS_PER_GROUP)
            if truncated:
                truncated_groups.add(f"observation:{observation_id}")
                truncated_pairs += omitted
            for source_ref, target_ref in pairs:
                emit(_candidate(
                    archive_id, snapshot_id,
                    source_ref=source_ref, relation="same_series_candidate",
                    target_ref=target_ref, status=UNRESOLVED_CANDIDATE, score=0.7,
                    reason_codes=["observer_numbered_sequence_candidate", "same_sequence_evidence"],
                    evidence_refs=[observation_id, source_ref, target_ref],
                    evidence_for=["observer_numbered_sequence"],
                    evidence_against=["sequence_does_not_prove_series"],
                    alternatives=["frame_sequence", "same_series_candidate", "independent_outputs"],
                    missing_evidence=["series_or_manifest_evidence"],
                    next_probe="compare_sequence_manifest_or_native_reference",
                ), f"observation:{observation_id}")
            continue

        if observation_type == "manifest_candidate":
            _skip(skipped, "manifest_candidate", "no_valid_artifact_target", observation_id)
        elif observation_type == "limit_reached":
            _skip(skipped, "limit_reached", "coverage_incomplete", observation_id)
        elif observation_type == "failure_candidate":
            _skip(skipped, "failure_candidate", "diagnostic_only", observation_id)

    # 5. Local native-anchor/output candidates. The pair must share a nearest
    # real directory group; equal basenames in different groups never pair.
    native_refs = [ref for ref in projection["native_anchor_refs"] if ref in artifact_by_ref]
    output_refs = [ref for ref in projection["probable_output_refs"] if ref in artifact_by_ref]
    directory_paths = {
        str(item["relative_path"])
        for item in artifact_by_ref.values()
        if item["kind"] == "directory"
    }
    local_pairs: dict[str, list[tuple[str, str]]] = {}
    for native_ref in sorted(native_refs):
        native = artifact_by_ref[native_ref]
        if native["kind"] != "file" or native["availability"] != "available":
            continue
        for output_ref in sorted(output_refs):
            output = artifact_by_ref[output_ref]
            if output_ref == native_ref or output["kind"] != "file" or output["availability"] != "available":
                continue
            group = _common_parent(str(native["parent_path"]), str(output["parent_path"]))
            if not group or group not in directory_paths:
                continue
            native_distance = len([p for p in str(native["parent_path"]).split("/") if p]) - len(group.split("/"))
            output_distance = len([p for p in str(output["parent_path"]).split("/") if p]) - len(group.split("/"))
            if native_distance > 1 or output_distance > 1:
                continue
            local_pairs.setdefault(group, []).append((native_ref, output_ref))
    for group, pairs in sorted(local_pairs.items()):
        pairs = sorted(set(pairs))
        if len(pairs) > MAX_LOCAL_GROUP_PAIRS:
            truncated_groups.add(f"local:{group}")
            truncated_pairs += len(pairs) - MAX_LOCAL_GROUP_PAIRS
            pairs = pairs[:MAX_LOCAL_GROUP_PAIRS]
        for native_ref, output_ref in pairs:
            emit(_candidate(
                archive_id, snapshot_id,
                source_ref=output_ref, relation="manifestation_of", target_ref=native_ref,
                status=UNRESOLVED_CANDIDATE, score=0.68,
                reason_codes=["local_native_anchor_output", "nearest_shared_directory"],
                evidence_refs=[native_ref, output_ref],
                evidence_for=["native_anchor_feature", "probable_output_media_feature"],
                evidence_against=["export_witness_not_observed"],
                alternatives=["exported_product", "preview_or_intermediate_media", "unrelated_local_media"],
                missing_evidence=["export_witness"],
                next_probe="locate_export_witness",
            ), f"local:{group}")

    candidates.sort(key=lambda item: item["candidate_id"])
    skipped = _sort_skip_summary(skipped)
    coverage = {
        "limits": {
            "max_candidates": MAX_CANDIDATES,
            "max_pairs_per_group": MAX_PAIRS_PER_GROUP,
            "max_local_group_pairs": MAX_LOCAL_GROUP_PAIRS,
        },
        "projection_artifacts": len(artifact_by_ref),
        "projection_observations": len(observation_by_id),
        "limit_reached_observations": skipped.get("limit_reached", {}).get("count", 0),
        "attempted_candidates": attempted_candidates,
        "generated_candidates": len(candidates),
        "truncated": bool(truncated_groups) or attempted_candidates > MAX_CANDIDATES,
        "truncated_groups": sorted(truncated_groups),
        "truncated_pair_count": truncated_pairs,
        "coverage_incomplete": bool(skipped.get("limit_reached", {}).get("count", 0)),
    }
    reconciliation = {
        "candidate_count": len(candidates),
        "candidate_ids_unique": len({item["candidate_id"] for item in candidates}) == len(candidates),
        "endpoint_refs_resolved": all(
            item["source_ref"] in artifact_by_ref and item["target_ref"] in artifact_by_ref
            for item in candidates
        ),
        "evidence_refs_resolved": all(
            ref in artifact_by_ref or ref in observation_by_id
            for item in candidates for ref in item["evidence_refs"]
        ),
        "truth_promotions": 0,
        "deterministic_order": candidates == sorted(candidates, key=lambda item: item["candidate_id"]),
        "status_values": sorted(ALLOWED_STATUSES),
    }
    payload = {
        "schema": SCHEMA,
        "source_schema": PROJECTION_SCHEMA,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": projection["input_hash"],
        "algorithm_version": "bounded-archive-relations-1",
        "candidates": candidates,
        "skipped_observation_summary": skipped,
        "coverage": coverage,
        "reconciliation": reconciliation,
    }
    validate_relation_payload(projection, payload)
    return payload


def _validate_string_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ArchiveRelationInferenceError(f"{field}_invalid")
    if value != sorted(set(value)):
        raise ArchiveRelationInferenceError(f"{field}_not_sorted")


def validate_relation_payload(projection: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    """Strictly validate this module's candidate payload and its references."""

    projection, artifact_by_ref, observation_by_id = _require_projection(projection)
    if not isinstance(payload, Mapping):
        raise ArchiveRelationInferenceError("relation_payload_must_be_mapping")
    required = {
        "schema", "source_schema", "archive_id", "snapshot_id", "input_hash",
        "algorithm_version", "candidates", "skipped_observation_summary", "coverage",
        "reconciliation",
    }
    if set(payload) != required:
        raise ArchiveRelationInferenceError("relation_payload_invalid_field_set")
    if payload["schema"] != SCHEMA or payload["source_schema"] != PROJECTION_SCHEMA:
        raise ArchiveRelationInferenceError("relation_payload_bad_schema")
    if payload["algorithm_version"] != "bounded-archive-relations-1":
        raise ArchiveRelationInferenceError("relation_payload_algorithm_version_invalid")
    for key in ("archive_id", "snapshot_id", "input_hash"):
        if payload[key] != projection[key]:
            raise ArchiveRelationInferenceError(f"relation_payload_{key}_mismatch")
    candidates = payload["candidates"]
    if not isinstance(candidates, list):
        raise ArchiveRelationInferenceError("relation_payload_candidates_invalid")
    candidate_ids: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping) or set(candidate) != {
            "candidate_id", "source_ref", "relation", "target_ref", "inverse_relation",
            "status", "score", "reason_codes", "evidence_refs", "evidence_for",
            "evidence_against", "alternatives", "missing_evidence", "next_probe",
        }:
            raise ArchiveRelationInferenceError("candidate_invalid_field_set")
        source_ref = candidate["source_ref"]
        target_ref = candidate["target_ref"]
        relation = candidate["relation"]
        if any(not isinstance(candidate[field], str) or not candidate[field] for field in (
            "candidate_id", "source_ref", "relation", "target_ref", "inverse_relation", "status",
        )):
            raise ArchiveRelationInferenceError("candidate_identity_fields_invalid")
        if source_ref not in artifact_by_ref or target_ref not in artifact_by_ref:
            raise ArchiveRelationInferenceError("candidate_endpoint_unresolved")
        if relation not in ARCHIVE_RELATION_INVERSES:
            raise ArchiveRelationInferenceError("candidate_relation_without_inverse")
        if candidate["inverse_relation"] != ARCHIVE_RELATION_INVERSES[relation]:
            raise ArchiveRelationInferenceError("candidate_inverse_mismatch")
        if candidate["status"] not in ALLOWED_STATUSES:
            raise ArchiveRelationInferenceError("candidate_truth_or_status_promotion")
        score = candidate["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ArchiveRelationInferenceError("candidate_score_invalid")
        for field in ("reason_codes", "evidence_refs", "evidence_for", "evidence_against", "alternatives", "missing_evidence"):
            _validate_string_list(candidate[field], f"candidate_{field}")
        if any(ref not in artifact_by_ref and ref not in observation_by_id for ref in candidate["evidence_refs"]):
            raise ArchiveRelationInferenceError("candidate_evidence_unresolved")
        next_probe = candidate["next_probe"]
        if next_probe is None:
            if candidate["status"] != PENDING_RELATION or candidate["missing_evidence"]:
                raise ArchiveRelationInferenceError("candidate_next_probe_null_not_permitted")
        elif not isinstance(next_probe, str) or not next_probe.strip():
            raise ArchiveRelationInferenceError("candidate_next_probe_invalid")
        expected_id = candidate_id_for(candidate, str(projection["archive_id"]))
        if candidate["candidate_id"] != expected_id:
            raise ArchiveRelationInferenceError("candidate_id_not_semantic")
        candidate_ids.append(str(candidate["candidate_id"]))
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ArchiveRelationInferenceError("candidate_ids_not_unique")
    expected_order = sorted(candidates, key=lambda item: item["candidate_id"])
    if candidates != expected_order:
        raise ArchiveRelationInferenceError("candidates_not_deterministically_sorted")
    skipped = payload["skipped_observation_summary"]
    if not isinstance(skipped, Mapping):
        raise ArchiveRelationInferenceError("skipped_summary_invalid")
    for key, entry in skipped.items():
        if not isinstance(key, str) or not isinstance(entry, Mapping):
            raise ArchiveRelationInferenceError("skipped_summary_entry_invalid")
        if set(entry) not in ({"count", "reason"}, {"count", "reason", "observation_ids"}):
            raise ArchiveRelationInferenceError("skipped_summary_field_set_invalid")
        if not isinstance(entry.get("count"), int) or entry["count"] < 0:
            raise ArchiveRelationInferenceError("skipped_summary_count_invalid")
        if not isinstance(entry.get("reason"), str) or not entry["reason"]:
            raise ArchiveRelationInferenceError("skipped_summary_reason_invalid")
        if "observation_ids" in entry:
            _validate_string_list(entry["observation_ids"], "skipped_observation_ids")
            if any(item not in observation_by_id for item in entry["observation_ids"]):
                raise ArchiveRelationInferenceError("skipped_observation_unresolved")
    coverage = payload["coverage"]
    if not isinstance(coverage, Mapping) or set(coverage) != {
        "limits", "projection_artifacts", "projection_observations", "limit_reached_observations",
        "attempted_candidates", "generated_candidates", "truncated", "truncated_groups",
        "truncated_pair_count", "coverage_incomplete",
    } or not isinstance(coverage.get("limits"), Mapping):
        raise ArchiveRelationInferenceError("coverage_invalid")
    if set(coverage["limits"]) != {"max_candidates", "max_pairs_per_group", "max_local_group_pairs"}:
        raise ArchiveRelationInferenceError("coverage_limits_invalid")
    if coverage["limits"] != {
        "max_candidates": MAX_CANDIDATES,
        "max_pairs_per_group": MAX_PAIRS_PER_GROUP,
        "max_local_group_pairs": MAX_LOCAL_GROUP_PAIRS,
    }:
        raise ArchiveRelationInferenceError("coverage_limits_mismatch")
    for field in (
        "max_candidates", "max_pairs_per_group", "max_local_group_pairs",
        "projection_artifacts", "projection_observations", "limit_reached_observations",
        "attempted_candidates", "generated_candidates", "truncated_pair_count",
    ):
        value = coverage["limits"].get(field) if field in coverage["limits"] else coverage[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ArchiveRelationInferenceError(f"coverage_{field}_invalid")
    if coverage["projection_artifacts"] != len(artifact_by_ref) or coverage["projection_observations"] != len(observation_by_id):
        raise ArchiveRelationInferenceError("coverage_projection_counts_invalid")
    if coverage["generated_candidates"] != len(candidates) or coverage["attempted_candidates"] < coverage["generated_candidates"]:
        raise ArchiveRelationInferenceError("coverage_candidate_counts_invalid")
    if coverage["limit_reached_observations"] != skipped.get("limit_reached", {}).get("count", 0):
        raise ArchiveRelationInferenceError("coverage_limit_count_invalid")
    _validate_string_list(coverage["truncated_groups"], "coverage_truncated_groups")
    if not isinstance(coverage["truncated"], bool) or not isinstance(coverage["coverage_incomplete"], bool):
        raise ArchiveRelationInferenceError("coverage_flags_invalid")
    if coverage["truncated"] != bool(coverage["truncated_groups"] or coverage["attempted_candidates"] > coverage["limits"]["max_candidates"]):
        raise ArchiveRelationInferenceError("coverage_truncation_mismatch")
    if coverage["coverage_incomplete"] != bool(coverage["limit_reached_observations"]):
        raise ArchiveRelationInferenceError("coverage_completeness_mismatch")
    reconciliation = payload["reconciliation"]
    if not isinstance(reconciliation, Mapping) or set(reconciliation) != {
        "candidate_count", "candidate_ids_unique", "endpoint_refs_resolved", "evidence_refs_resolved",
        "truth_promotions", "deterministic_order", "status_values",
    }:
        raise ArchiveRelationInferenceError("reconciliation_invalid")
    if reconciliation.get("candidate_count") != len(candidates):
        raise ArchiveRelationInferenceError("reconciliation_candidate_count_invalid")
    if reconciliation.get("candidate_ids_unique") is not True or reconciliation.get("endpoint_refs_resolved") is not True or reconciliation.get("evidence_refs_resolved") is not True:
        raise ArchiveRelationInferenceError("reconciliation_resolution_failed")
    if reconciliation.get("truth_promotions") != 0:
        raise ArchiveRelationInferenceError("reconciliation_truth_promotion")
    if reconciliation.get("deterministic_order") is not True:
        raise ArchiveRelationInferenceError("reconciliation_order_failed")
    if reconciliation.get("status_values") != sorted(ALLOWED_STATUSES):
        raise ArchiveRelationInferenceError("reconciliation_status_values_invalid")
    return True


__all__ = [
    "ARCHIVE_RELATION_INVERSES",
    "ArchiveRelationInferenceError",
    "SCHEMA",
    "candidate_id_for",
    "infer_archive_relations",
    "validate_relation_payload",
]
