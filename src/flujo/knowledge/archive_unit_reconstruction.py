"""Balanced provisional units over the frozen Stage 2A/2B contracts.

This module is deliberately a projection, not a truth compiler.  It groups
physical artifacts into provisional units only when the archive topology gives
one deterministic owner.  Candidate relations remain candidates, exact byte
duplicates remain separate physical artifacts, and every artifact receives
exactly one assignment status.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Mapping

from ._contract_helpers import sha256_ref as _hash, stable_json as _stable_json

from .archive_relation_inference import (
    ArchiveRelationInferenceError,
    validate_relation_payload,
)
from .project_reconstruction import (
    ROLE_EXPORTED_PRODUCT,
    ROLE_LIBRARY_DEPENDENCY,
    ROLE_PROJECT_UNIT,
    ROLE_SHARED_RESOURCE,
    ROLE_SUBPROJECT,
    ROLE_UNDECIDED,
)


SCHEMA = "mak-archive-unit-reconstruction-v1"
PROJECTION_SCHEMA = "mak-archive-reconstruction-input-v1"
RELATION_SCHEMA = "mak-archive-relation-candidates-v1"
ALGORITHM_VERSION = "balanced-provisional-archive-units-1"

STATUS_PROVISIONAL = "provisional_unit"
STATUS_UNRESOLVED = "unresolved_unit"
ALLOWED_UNIT_STATUSES = frozenset({STATUS_PROVISIONAL, STATUS_UNRESOLVED})
ALLOWED_ROLES = frozenset({
    ROLE_PROJECT_UNIT,
    ROLE_SUBPROJECT,
    ROLE_LIBRARY_DEPENDENCY,
    ROLE_SHARED_RESOURCE,
    ROLE_EXPORTED_PRODUCT,
    ROLE_UNDECIDED,
})
ALLOWED_ASSIGNMENT_STATUSES = frozenset({"assigned", "ambiguous", "unassigned"})

_PROJECTION_FIELDS = {
    "schema", "source_schema", "archive_id", "snapshot_id", "limits", "input_hash",
    "artifacts", "candidate_observations", "artifacts_by_parent", "artifacts_by_content",
    "native_anchor_refs", "probable_output_refs", "candidate_observation_ids",
    "reconciliation",
}
_ARTIFACT_FIELDS = {
    "artifact_id", "physical_id", "artifact_ref", "references", "relative_path",
    "parent_path", "basename", "stem", "suffix_chain", "kind", "availability",
    "family", "media_type", "size", "sha256", "content_id", "derived_flags",
}
_FLAG_FIELDS = {
    "native_authoring_anchor", "probable_output_media", "sidecar_or_manifest",
    "numbered_name_token", "duplicate_content_member", "directory_depth",
}
_OBSERVATION_FIELDS = {
    "record_type", "observation_id", "observation_type", "status", "artifact_refs",
    "evidence",
}
_UNIT_FIELDS = {
    "unit_id", "role", "status", "root_path", "anchor_refs", "member_refs",
    "dependency_refs", "candidate_ids", "evidence_for", "evidence_against",
    "alternatives", "missing_evidence",
}
_ASSIGNMENT_FIELDS = {
    "artifact_ref", "status", "unit_id", "reason_codes", "candidate_ids", "alternatives",
}


class ArchiveUnitReconstructionError(ValueError):
    """Invalid upstream input or invalid unit reconstruction payload."""


def _sorted_unique_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ArchiveUnitReconstructionError(f"{field}_invalid")
    result = sorted(set(value))
    if value != result:
        raise ArchiveUnitReconstructionError(f"{field}_not_sorted_unique")
    return result


def unit_id_for(unit_semantics: Mapping[str, Any], archive_id: str, snapshot_id: str) -> str:
    """Return the stable identity of a unit anchor.

    Membership, evidence and candidate scores are intentionally excluded.
    Adding an output or a new witness must not silently create a new unit
    identity for the same archive/snapshot/role/root/anchor set.
    """

    if not isinstance(unit_semantics, Mapping):
        raise ArchiveUnitReconstructionError("unit_semantics_must_be_mapping")
    if not isinstance(archive_id, str) or not archive_id:
        raise ArchiveUnitReconstructionError("unit_archive_id_invalid")
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise ArchiveUnitReconstructionError("unit_snapshot_id_invalid")
    role = unit_semantics.get("role")
    root_path = unit_semantics.get("root_path")
    anchors = unit_semantics.get("anchor_refs")
    if not isinstance(role, str) or role not in ALLOWED_ROLES:
        raise ArchiveUnitReconstructionError("unit_role_invalid")
    if not isinstance(root_path, str):
        raise ArchiveUnitReconstructionError("unit_root_path_invalid")
    if not isinstance(anchors, list) or any(not isinstance(item, str) for item in anchors):
        raise ArchiveUnitReconstructionError("unit_anchor_refs_invalid")
    material = {
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "role": role,
        "root_path": root_path,
        "anchor_refs": sorted(set(anchors)),
    }
    return "unit:" + hashlib.sha256(_stable_json(material).encode("utf-8")).hexdigest()


def _is_same_or_descendant(path: str, root: str) -> bool:
    if path == root:
        return True
    if not root:
        return bool(path)
    return path.startswith(root + "/")


def _is_strict_ancestor(path: str, descendant: str) -> bool:
    return bool(path) and descendant.startswith(path + "/")


def _validate_projection(projection: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Validate the frozen Stage 2A projection before any unit inference."""

    if not isinstance(projection, Mapping):
        raise ArchiveUnitReconstructionError("projection_must_be_mapping")
    if set(projection) != _PROJECTION_FIELDS:
        raise ArchiveUnitReconstructionError("projection_field_set_invalid")
    if projection["schema"] != PROJECTION_SCHEMA or projection["source_schema"] != "mak-archive-observation-batch-v1":
        raise ArchiveUnitReconstructionError("projection_schema_invalid")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if not isinstance(projection[field], str) or not projection[field]:
            raise ArchiveUnitReconstructionError(f"projection_{field}_invalid")
    if not isinstance(projection["limits"], Mapping) or not isinstance(projection["reconciliation"], Mapping):
        raise ArchiveUnitReconstructionError("projection_metadata_invalid")

    artifacts = projection["artifacts"]
    if not isinstance(artifacts, list):
        raise ArchiveUnitReconstructionError("projection_artifacts_invalid")
    artifacts_by_ref: dict[str, dict[str, Any]] = {}
    ref_by_path: dict[str, str] = {}
    for artifact in artifacts:
        if not isinstance(artifact, Mapping) or set(artifact) != _ARTIFACT_FIELDS:
            raise ArchiveUnitReconstructionError("projection_artifact_shape_invalid")
        ref = artifact["artifact_ref"]
        path = artifact["relative_path"]
        if not isinstance(ref, str) or not ref or ref in artifacts_by_ref:
            raise ArchiveUnitReconstructionError("projection_artifact_ref_invalid")
        if not isinstance(path, str) or path in ref_by_path:
            raise ArchiveUnitReconstructionError("projection_artifact_path_invalid")
        if not isinstance(artifact["parent_path"], str) or not isinstance(artifact["kind"], str):
            raise ArchiveUnitReconstructionError("projection_artifact_topology_invalid")
        if not isinstance(artifact["references"], list) or not isinstance(artifact["suffix_chain"], list):
            raise ArchiveUnitReconstructionError("projection_artifact_lists_invalid")
        if not isinstance(artifact["derived_flags"], Mapping) or set(artifact["derived_flags"]) != _FLAG_FIELDS:
            raise ArchiveUnitReconstructionError("projection_artifact_flags_invalid")
        artifacts_by_ref[ref] = dict(artifact)
        ref_by_path[path] = ref

    observations = projection["candidate_observations"]
    if not isinstance(observations, list):
        raise ArchiveUnitReconstructionError("projection_observations_invalid")
    observation_ids: list[str] = []
    for observation in observations:
        if not isinstance(observation, Mapping) or set(observation) != _OBSERVATION_FIELDS:
            raise ArchiveUnitReconstructionError("projection_observation_shape_invalid")
        observation_id = observation["observation_id"]
        refs = observation["artifact_refs"]
        if not isinstance(observation_id, str) or not observation_id or observation_id in observation_ids:
            raise ArchiveUnitReconstructionError("projection_observation_id_invalid")
        if observation["record_type"] != "candidate_observation" or observation["status"] != "candidate":
            raise ArchiveUnitReconstructionError("projection_observation_status_invalid")
        if not isinstance(refs, list) or refs != sorted(set(refs)) or any(ref not in artifacts_by_ref for ref in refs):
            raise ArchiveUnitReconstructionError("projection_observation_refs_invalid")
        if not isinstance(observation["evidence"], Mapping):
            raise ArchiveUnitReconstructionError("projection_observation_evidence_invalid")
        observation_ids.append(observation_id)
    if projection["candidate_observation_ids"] != sorted(observation_ids):
        raise ArchiveUnitReconstructionError("projection_observation_index_invalid")

    for field in ("native_anchor_refs", "probable_output_refs"):
        refs = projection[field]
        if not isinstance(refs, list) or refs != sorted(set(refs)) or any(ref not in artifacts_by_ref for ref in refs):
            raise ArchiveUnitReconstructionError(f"projection_{field}_invalid")
    for field in ("artifacts_by_parent", "artifacts_by_content"):
        index = projection[field]
        if not isinstance(index, Mapping):
            raise ArchiveUnitReconstructionError(f"projection_{field}_invalid")
        for key, refs in index.items():
            if not isinstance(key, str) or not isinstance(refs, list) or refs != sorted(set(refs)):
                raise ArchiveUnitReconstructionError(f"projection_{field}_ordering_invalid")
            if any(ref not in artifacts_by_ref for ref in refs):
                raise ArchiveUnitReconstructionError(f"projection_{field}_ref_invalid")

    reconciliation = projection["reconciliation"]
    if reconciliation.get("artifacts_projected") != len(artifacts):
        raise ArchiveUnitReconstructionError("projection_artifact_reconciliation_invalid")
    if reconciliation.get("observations_projected") != len(observations):
        raise ArchiveUnitReconstructionError("projection_observation_reconciliation_invalid")
    return dict(projection), artifacts_by_ref, ref_by_path


def _validate_upstream(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    projection_copy, artifacts_by_ref, ref_by_path = _validate_projection(projection)
    try:
        validate_relation_payload(projection_copy, relations)
    except (ArchiveRelationInferenceError, ValueError) as error:
        raise ArchiveUnitReconstructionError(f"relations_invalid:{error}") from error
    if relations.get("schema") != RELATION_SCHEMA:
        raise ArchiveUnitReconstructionError("relations_schema_invalid")
    return projection_copy, artifacts_by_ref, ref_by_path


def _new_unit(
    archive_id: str,
    snapshot_id: str,
    *,
    role: str,
    root_path: str,
    anchor_refs: list[str],
) -> dict[str, Any]:
    anchor_refs = sorted(set(anchor_refs))
    unit_id = unit_id_for(
        {"role": role, "root_path": root_path, "anchor_refs": anchor_refs},
        archive_id,
        snapshot_id,
    )
    return {
        "unit_id": unit_id,
        "role": role,
        "status": STATUS_PROVISIONAL,
        "root_path": root_path,
        "anchor_refs": anchor_refs,
        "member_refs": [],
        "dependency_refs": [],
        "candidate_ids": [],
        "evidence_for": [],
        "evidence_against": [],
        "alternatives": [],
        "missing_evidence": [],
        "_seed_evidence": set(),
        "_seed_against": set(),
        "_seed_alternatives": set(),
        "_seed_missing": set(),
    }


def _add_possible(
    possible: dict[str, dict[str, dict[str, set[str]]]],
    artifact_ref: str,
    unit_id: str,
    *,
    reason: str,
    candidate_id: str | None = None,
) -> bool:
    entry = possible.setdefault(artifact_ref, {}).setdefault(
        unit_id, {"reasons": set(), "candidate_ids": set()}
    )
    before = (len(entry["reasons"]), len(entry["candidate_ids"]))
    entry["reasons"].add(reason)
    if candidate_id:
        entry["candidate_ids"].add(candidate_id)
    return before != (len(entry["reasons"]), len(entry["candidate_ids"]))


def _candidate_relation_edges(candidate: Mapping[str, Any]) -> tuple[str, str, bool]:
    relation = candidate["relation"]
    source = str(candidate["source_ref"])
    target = str(candidate["target_ref"])
    if relation == "contains":
        return source, target, False
    if relation == "contained_by":
        return target, source, False
    if relation in {"depends_on", "depended_on_by", "shared_resource", "shared_resource_of"}:
        return source, target, True
    return source, target, False


def _attachable_relation(relation: str) -> bool:
    return relation in {
        "describes", "described_by", "manifestation_of", "has_manifestation",
        "component_of", "has_component", "version_of", "has_version",
        "same_series_candidate",
    }


def _finalize_unit(unit: dict[str, Any], relation_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    candidate_ids = set(unit["candidate_ids"])
    evidence_for = set(unit.pop("_seed_evidence"))
    evidence_against = set(unit.pop("_seed_against"))
    alternatives = set(unit.pop("_seed_alternatives"))
    missing = set(unit.pop("_seed_missing"))
    for candidate_id in sorted(candidate_ids):
        candidate = relation_by_id.get(candidate_id)
        if candidate is None:
            continue
        evidence_for.update(str(value) for value in candidate["evidence_for"])
        evidence_against.update(str(value) for value in candidate["evidence_against"])
        alternatives.update(str(value) for value in candidate["alternatives"])
        missing.update(str(value) for value in candidate["missing_evidence"])
    unit["candidate_ids"] = sorted(candidate_ids)
    unit["evidence_for"] = sorted(evidence_for)
    unit["evidence_against"] = sorted(evidence_against)
    unit["alternatives"] = sorted(alternatives)
    unit["missing_evidence"] = sorted(missing)
    unit["anchor_refs"] = sorted(set(unit["anchor_refs"]))
    unit["member_refs"] = sorted(set(unit["member_refs"]))
    unit["dependency_refs"] = sorted(set(unit["dependency_refs"]))
    unit["status"] = STATUS_UNRESOLVED if unit["missing_evidence"] or unit["alternatives"] else STATUS_PROVISIONAL
    if unit["role"] == ROLE_EXPORTED_PRODUCT:
        unit["status"] = STATUS_UNRESOLVED
    return unit


def reconstruct_archive_units(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
) -> dict[str, Any]:
    """Build balanced provisional units without promoting relation truth."""

    projection, artifacts_by_ref, ref_by_path = _validate_upstream(projection, relations)
    archive_id = str(projection["archive_id"])
    snapshot_id = str(projection["snapshot_id"])
    relation_hash = _hash(relations)
    relation_candidates = list(relations["candidates"])
    relation_by_id = {str(candidate["candidate_id"]): dict(candidate) for candidate in relation_candidates}

    units_by_id: dict[str, dict[str, Any]] = {}
    unit_by_root: dict[str, str] = {}
    anchor_ref_to_unit: dict[str, str] = {}
    native_by_parent: dict[str, list[str]] = defaultdict(list)
    for anchor_ref in projection["native_anchor_refs"]:
        artifact = artifacts_by_ref[anchor_ref]
        native_by_parent[str(artifact["parent_path"])].append(anchor_ref)
    for root_path, anchor_refs in sorted(native_by_parent.items()):
        unit = _new_unit(
            archive_id, snapshot_id, role=ROLE_PROJECT_UNIT,
            root_path=root_path, anchor_refs=anchor_refs,
        )
        unit["_seed_evidence"].add(f"native_anchor_parent:{root_path}")
        units_by_id[unit["unit_id"]] = unit
        unit_by_root[root_path] = unit["unit_id"]
        for anchor_ref in sorted(anchor_refs):
            anchor_ref_to_unit[anchor_ref] = unit["unit_id"]

    possible: dict[str, dict[str, dict[str, set[str]]]] = {}
    unit_root_paths = set(unit_by_root)
    for unit_id, unit in units_by_id.items():
        root_path = str(unit["root_path"])
        root_ref = ref_by_path.get(root_path)
        if root_ref:
            _add_possible(possible, root_ref, unit_id, reason="unit_root")
        for ref, artifact in artifacts_by_ref.items():
            path = str(artifact["relative_path"])
            if ref in anchor_ref_to_unit and anchor_ref_to_unit[ref] != unit_id:
                continue
            if path in unit_root_paths and unit_by_root.get(path) != unit_id:
                continue
            if str(artifact["parent_path"]) == root_path:
                _add_possible(possible, ref, unit_id, reason="direct_physical_child")

    # A directory above multiple native roots is explicitly ambiguous rather
    # than being promoted to a synthetic root project.
    for ref, artifact in artifacts_by_ref.items():
        if artifact["kind"] != "directory":
            continue
        path = str(artifact["relative_path"])
        descendants = [
            (root, unit_id) for root, unit_id in unit_by_root.items()
            if _is_strict_ancestor(path, root)
        ]
        if len(descendants) > 1:
            for _root, unit_id in descendants:
                _add_possible(possible, ref, unit_id, reason="shared_ancestor")

    # Propagate only topology that can join artifacts.  Dependency relations
    # are retained separately and never collapse a dependency into a work.
    changed = True
    while changed:
        changed = False
        for candidate in relation_candidates:
            relation = str(candidate["relation"])
            if relation in {"identity_undecided", "unrelated"}:
                continue
            left, right, dependency_edge = _candidate_relation_edges(candidate)
            if dependency_edge:
                continue
            if left not in possible and right not in possible:
                continue
            if _attachable_relation(relation):
                pairs = [(left, right), (right, left)]
            else:
                pairs = [(left, right)]
            for source_ref, target_ref in pairs:
                source_options = possible.get(source_ref, {})
                if len(source_options) != 1:
                    continue
                for unit_id, evidence in list(source_options.items()):
                    if target_ref in anchor_ref_to_unit and anchor_ref_to_unit[target_ref] != unit_id:
                        continue
                    target_path = str(artifacts_by_ref[target_ref]["relative_path"])
                    if target_path in unit_root_paths and unit_by_root.get(target_path) != unit_id:
                        continue
                    if _add_possible(
                        possible, target_ref, unit_id,
                        reason=f"candidate_topology:{relation}",
                        candidate_id=str(candidate["candidate_id"]),
                    ):
                        changed = True

    # Outputs without one native destination become local unresolved products.
    output_only_by_parent: dict[str, list[str]] = defaultdict(list)
    native_roots = sorted(unit_by_root)
    for output_ref in projection["probable_output_refs"]:
        if possible.get(output_ref):
            continue
        output = artifacts_by_ref[output_ref]
        parent = str(output["parent_path"])
        shared_native_units = {
            unit_by_root[root]
            for root in native_roots
            if _is_strict_ancestor(parent, root)
        }
        if len(shared_native_units) > 1:
            for unit_id in sorted(shared_native_units):
                _add_possible(possible, output_ref, unit_id, reason="shared_ancestor_output")
            continue
        output_only_by_parent[parent].append(output_ref)

    for root_path, output_refs in sorted(output_only_by_parent.items()):
        unit = _new_unit(
            archive_id, snapshot_id, role=ROLE_EXPORTED_PRODUCT,
            root_path=root_path, anchor_refs=[],
        )
        unit["_seed_evidence"].add(f"probable_output_parent:{root_path}")
        unit["_seed_against"].add("source_binding_not_observed")
        unit["_seed_alternatives"].update({ROLE_PROJECT_UNIT, ROLE_UNDECIDED})
        unit["_seed_missing"].add("missing_source_binding")
        units_by_id[unit["unit_id"]] = unit
        for output_ref in sorted(output_refs):
            _add_possible(possible, output_ref, unit["unit_id"], reason="output_only_local_parent")

    # Let sidecars and sequences join a newly created output-only unit too.
    changed = True
    while changed:
        changed = False
        for candidate in relation_candidates:
            relation = str(candidate["relation"])
            if not _attachable_relation(relation):
                continue
            left, right, _dependency_edge = _candidate_relation_edges(candidate)
            for source_ref, target_ref in ((left, right), (right, left)):
                source_options = possible.get(source_ref, {})
                if len(source_options) != 1:
                    continue
                for unit_id in list(source_options):
                    if target_ref in anchor_ref_to_unit and anchor_ref_to_unit[target_ref] != unit_id:
                        continue
                    if _add_possible(
                        possible, target_ref, unit_id,
                        reason=f"candidate_topology:{relation}",
                        candidate_id=str(candidate["candidate_id"]),
                    ):
                        changed = True

    assignments: list[dict[str, Any]] = []
    assigned_refs: set[str] = set()
    ambiguous_refs: list[str] = []
    unassigned_refs: list[str] = []
    for artifact_ref in sorted(artifacts_by_ref):
        options = possible.get(artifact_ref, {})
        if len(options) == 1:
            unit_id, evidence = next(iter(options.items()))
            assignment = {
                "artifact_ref": artifact_ref,
                "status": "assigned",
                "unit_id": unit_id,
                "reason_codes": sorted(evidence["reasons"]),
                "candidate_ids": sorted(evidence["candidate_ids"]),
                "alternatives": [],
            }
            assigned_refs.add(artifact_ref)
            units_by_id[unit_id]["member_refs"].append(artifact_ref)
            units_by_id[unit_id]["candidate_ids"].extend(evidence["candidate_ids"])
        elif len(options) > 1:
            alternatives = sorted(options)
            candidate_ids = sorted({
                candidate_id
                for evidence in options.values()
                for candidate_id in evidence["candidate_ids"]
            })
            assignment = {
                "artifact_ref": artifact_ref,
                "status": "ambiguous",
                "unit_id": None,
                "reason_codes": ["multiple_provisional_units"],
                "candidate_ids": candidate_ids,
                "alternatives": alternatives,
            }
            ambiguous_refs.append(artifact_ref)
        else:
            assignment = {
                "artifact_ref": artifact_ref,
                "status": "unassigned",
                "unit_id": None,
                "reason_codes": ["no_unambiguous_unit_topology"],
                "candidate_ids": [],
                "alternatives": [],
            }
            unassigned_refs.append(artifact_ref)
        assignments.append(assignment)

    # Explicit dependency edges enrich the owning unit without making the
    # dependency a project member or using content identity as assignment.
    for candidate in relation_candidates:
        relation = str(candidate["relation"])
        if relation not in {"depends_on", "depended_on_by", "shared_resource", "shared_resource_of"}:
            continue
        left, right, _dependency_edge = _candidate_relation_edges(candidate)
        owner_ref, dependency_ref = (left, right)
        if relation in {"depended_on_by", "shared_resource_of"}:
            owner_ref, dependency_ref = right, left
        owner_assignment = next((item for item in assignments if item["artifact_ref"] == owner_ref), None)
        if owner_assignment and owner_assignment["status"] == "assigned":
            unit = units_by_id[owner_assignment["unit_id"]]
            unit["dependency_refs"].append(dependency_ref)
            unit["candidate_ids"].append(str(candidate["candidate_id"]))

    for unit in units_by_id.values():
        _finalize_unit(unit, relation_by_id)
        for key in ("member_refs", "dependency_refs", "candidate_ids"):
            unit[key] = sorted(set(unit[key]))
        # Internal helper keys are removed by _finalize_unit; this assertion
        # keeps accidental implementation metadata out of the public schema.
        if any(key.startswith("_") for key in unit):
            raise ArchiveUnitReconstructionError("unit_internal_field_leaked")

    units = sorted(units_by_id.values(), key=lambda item: item["unit_id"])
    assignments.sort(key=lambda item: item["artifact_ref"])
    role_counts: dict[str, int] = defaultdict(int)
    for unit in units:
        role_counts[unit["role"]] += 1
    reconciliation = {
        "total_artifacts": len(artifacts_by_ref),
        "assigned": len(assigned_refs),
        "ambiguous": len(ambiguous_refs),
        "unassigned": len(unassigned_refs),
        "unit_count": len(units),
        "units_by_role": dict(sorted(role_counts.items())),
        "assignment_count": len(assignments),
        "duplicates": len(assignments) - len({item["artifact_ref"] for item in assignments}),
        "loss": len(artifacts_by_ref) - len(assignments),
        "balanced": (
            len(assigned_refs) + len(ambiguous_refs) + len(unassigned_refs) == len(artifacts_by_ref)
            and len(assignments) == len(artifacts_by_ref)
        ),
        "truth_promotions": 0,
        "relation_candidate_count": len(relation_candidates),
        "unit_status_values": sorted(ALLOWED_UNIT_STATUSES),
    }
    payload = {
        "schema": SCHEMA,
        "source_projection_schema": PROJECTION_SCHEMA,
        "source_relation_schema": RELATION_SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": projection["input_hash"],
        "relation_hash": relation_hash,
        "units": units,
        "assignments": assignments,
        "unassigned_refs": sorted(unassigned_refs),
        "ambiguous_refs": sorted(ambiguous_refs),
        "reconciliation": reconciliation,
    }
    validate_unit_payload(projection, relations, payload)
    return payload


def validate_unit_payload(
    projection: Mapping[str, Any],
    relations: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Strictly validate upstream provenance, unit identities and balance."""

    projection, artifacts_by_ref, _ref_by_path = _validate_upstream(projection, relations)
    relation_candidate_ids = {
        str(candidate["candidate_id"]) for candidate in relations["candidates"]
    }
    if not isinstance(payload, Mapping) or set(payload) != {
        "schema", "source_projection_schema", "source_relation_schema", "algorithm_version",
        "archive_id", "snapshot_id", "input_hash", "relation_hash", "units", "assignments",
        "unassigned_refs", "ambiguous_refs", "reconciliation",
    }:
        raise ArchiveUnitReconstructionError("unit_payload_field_set_invalid")
    if payload["schema"] != SCHEMA or payload["source_projection_schema"] != PROJECTION_SCHEMA or payload["source_relation_schema"] != RELATION_SCHEMA:
        raise ArchiveUnitReconstructionError("unit_payload_schema_invalid")
    if payload["algorithm_version"] != ALGORITHM_VERSION:
        raise ArchiveUnitReconstructionError("unit_payload_algorithm_version_invalid")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        if payload[field] != projection[field]:
            raise ArchiveUnitReconstructionError(f"unit_payload_{field}_mismatch")
    if payload["relation_hash"] != _hash(relations):
        raise ArchiveUnitReconstructionError("unit_payload_relation_hash_mismatch")

    units = payload["units"]
    if not isinstance(units, list):
        raise ArchiveUnitReconstructionError("unit_payload_units_invalid")
    unit_ids: list[str] = []
    for unit in units:
        if not isinstance(unit, Mapping) or set(unit) != _UNIT_FIELDS:
            raise ArchiveUnitReconstructionError("unit_shape_invalid")
        unit_id = unit["unit_id"]
        if not isinstance(unit_id, str) or not unit_id:
            raise ArchiveUnitReconstructionError("unit_id_invalid")
        if unit["role"] not in ALLOWED_ROLES or unit["status"] not in ALLOWED_UNIT_STATUSES:
            raise ArchiveUnitReconstructionError("unit_role_or_status_invalid")
        if not isinstance(unit["root_path"], str):
            raise ArchiveUnitReconstructionError("unit_root_path_invalid")
        for field in (
            "anchor_refs", "member_refs", "dependency_refs", "candidate_ids",
            "evidence_for", "evidence_against", "alternatives", "missing_evidence",
        ):
            _sorted_unique_strings(unit[field], f"unit_{field}")
        if any(candidate_id not in relation_candidate_ids for candidate_id in unit["candidate_ids"]):
            raise ArchiveUnitReconstructionError("unit_candidate_id_unresolved")
        for field in ("anchor_refs", "member_refs", "dependency_refs"):
            if any(ref not in artifacts_by_ref for ref in unit[field]):
                raise ArchiveUnitReconstructionError(f"unit_{field}_ref_unresolved")
        expected_id = unit_id_for(unit, str(projection["archive_id"]), str(projection["snapshot_id"]))
        if unit_id != expected_id:
            raise ArchiveUnitReconstructionError("unit_id_not_semantic")
        unit_ids.append(unit_id)
    if unit_ids != sorted(unit_ids) or len(unit_ids) != len(set(unit_ids)):
        raise ArchiveUnitReconstructionError("unit_ids_not_sorted_unique")

    assignments = payload["assignments"]
    if not isinstance(assignments, list):
        raise ArchiveUnitReconstructionError("assignments_invalid")
    assignment_refs: list[str] = []
    assigned_count = ambiguous_count = unassigned_count = 0
    unit_id_set = set(unit_ids)
    for assignment in assignments:
        if not isinstance(assignment, Mapping) or set(assignment) != _ASSIGNMENT_FIELDS:
            raise ArchiveUnitReconstructionError("assignment_shape_invalid")
        ref = assignment["artifact_ref"]
        if not isinstance(ref, str) or ref not in artifacts_by_ref:
            raise ArchiveUnitReconstructionError("assignment_ref_invalid")
        status = assignment["status"]
        if status not in ALLOWED_ASSIGNMENT_STATUSES:
            raise ArchiveUnitReconstructionError("assignment_status_invalid")
        _sorted_unique_strings(assignment["reason_codes"], "assignment_reason_codes")
        _sorted_unique_strings(assignment["candidate_ids"], "assignment_candidate_ids")
        _sorted_unique_strings(assignment["alternatives"], "assignment_alternatives")
        if any(candidate_id not in relation_candidate_ids for candidate_id in assignment["candidate_ids"]):
            raise ArchiveUnitReconstructionError("assignment_candidate_id_unresolved")
        if status == "assigned":
            if not isinstance(assignment["unit_id"], str) or assignment["unit_id"] not in unit_id_set:
                raise ArchiveUnitReconstructionError("assigned_unit_id_invalid")
            if assignment["alternatives"]:
                raise ArchiveUnitReconstructionError("assigned_alternatives_not_empty")
            assigned_count += 1
        else:
            if assignment["unit_id"] is not None:
                raise ArchiveUnitReconstructionError("nonassigned_unit_id_present")
            if status == "ambiguous":
                if not assignment["alternatives"]:
                    raise ArchiveUnitReconstructionError("ambiguous_alternatives_missing")
                ambiguous_count += 1
            else:
                if assignment["alternatives"]:
                    raise ArchiveUnitReconstructionError("unassigned_alternatives_present")
                unassigned_count += 1
        assignment_refs.append(ref)
    if assignment_refs != sorted(assignment_refs) or len(assignment_refs) != len(set(assignment_refs)):
        raise ArchiveUnitReconstructionError("assignment_refs_not_sorted_unique")
    if set(assignment_refs) != set(artifacts_by_ref):
        raise ArchiveUnitReconstructionError("assignment_artifact_loss")

    unassigned = _sorted_unique_strings(payload["unassigned_refs"], "unassigned_refs")
    ambiguous = _sorted_unique_strings(payload["ambiguous_refs"], "ambiguous_refs")
    if set(unassigned) & set(ambiguous):
        raise ArchiveUnitReconstructionError("unassigned_ambiguous_overlap")
    assignment_by_ref = {item["artifact_ref"]: item for item in assignments}
    if set(unassigned) != {
        ref for ref, item in assignment_by_ref.items() if item["status"] == "unassigned"
    }:
        raise ArchiveUnitReconstructionError("unassigned_refs_mismatch")
    if set(ambiguous) != {
        ref for ref, item in assignment_by_ref.items() if item["status"] == "ambiguous"
    }:
        raise ArchiveUnitReconstructionError("ambiguous_refs_mismatch")

    reconciliation = payload["reconciliation"]
    if not isinstance(reconciliation, Mapping):
        raise ArchiveUnitReconstructionError("unit_reconciliation_invalid")
    expected_reconciliation_fields = {
        "total_artifacts", "assigned", "ambiguous", "unassigned", "unit_count",
        "units_by_role", "assignment_count", "duplicates", "loss", "balanced",
        "truth_promotions", "relation_candidate_count", "unit_status_values",
    }
    if set(reconciliation) != expected_reconciliation_fields:
        raise ArchiveUnitReconstructionError("unit_reconciliation_field_set_invalid")
    if reconciliation["total_artifacts"] != len(artifacts_by_ref):
        raise ArchiveUnitReconstructionError("unit_reconciliation_total_invalid")
    if reconciliation["assigned"] != assigned_count or reconciliation["ambiguous"] != ambiguous_count or reconciliation["unassigned"] != unassigned_count:
        raise ArchiveUnitReconstructionError("unit_reconciliation_assignment_counts_invalid")
    if reconciliation["unit_count"] != len(units) or reconciliation["assignment_count"] != len(assignments):
        raise ArchiveUnitReconstructionError("unit_reconciliation_counts_invalid")
    if reconciliation["duplicates"] != 0 or reconciliation["loss"] != 0:
        raise ArchiveUnitReconstructionError("unit_reconciliation_loss_or_duplicates")
    if reconciliation["balanced"] is not True or reconciliation["truth_promotions"] != 0:
        raise ArchiveUnitReconstructionError("unit_reconciliation_invariant_failed")
    if reconciliation["unit_status_values"] != sorted(ALLOWED_UNIT_STATUSES):
        raise ArchiveUnitReconstructionError("unit_reconciliation_status_values_invalid")
    return True


__all__ = [
    "ALGORITHM_VERSION",
    "ALLOWED_ASSIGNMENT_STATUSES",
    "ALLOWED_ROLES",
    "ALLOWED_UNIT_STATUSES",
    "ArchiveUnitReconstructionError",
    "SCHEMA",
    "reconstruct_archive_units",
    "unit_id_for",
    "validate_unit_payload",
]
