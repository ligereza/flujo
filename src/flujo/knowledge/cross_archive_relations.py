"""Deterministic cross-archive relation candidates.

This is a read-only projection over accepted practice-evidence states and an
explicit local catalogue.  It connects physical artifacts through a declared
catalogue work/collaboration signal without merging physical identity, making
authorship claims, or deciding that a whole subarchive is one work.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from ._contract_helpers import sha256_ref as _sha256, stable_json as _stable_json

from .practice_evidence_state import validate_practice_evidence_state
from .project_context import validate_context


SCHEMA = "mak-cross-archive-relations-v1"
ALGORITHM_VERSION = "catalogue-collaboration-crosswalk-1"
_STATUS = "candidate"
_MAX_RELATIONS = 200
_REMOVABLE_TRACK_TOKENS = {"remix", "version", "edit", "extended", "radio"}


class CrossArchiveRelationError(ValueError):
    """Raised when the cross-archive boundary cannot be validated."""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _tokens(value: str, *, remove_track_qualifiers: bool = False) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", normalized.lower())
    if remove_track_qualifiers:
        words = [word for word in words if word not in _REMOVABLE_TRACK_TOKENS]
    return tuple(words)


def _archive_ref(archive_id: str, artifact_ref: str) -> str:
    if not archive_id or not artifact_ref:
        raise CrossArchiveRelationError("artifact_ref_required")
    return artifact_ref


def _descriptor(raw: Mapping[str, Any], index: int) -> dict[str, Any]:
    scope = raw.get("scope") if isinstance(raw.get("scope"), Mapping) else {}
    declared = raw.get("declared_identity") if isinstance(raw.get("declared_identity"), Mapping) else {}
    archive_id = _text(raw.get("archive_id")) or _text(scope.get("archive_id"))
    artist = (_text(raw.get("artist_identity")) or _text(scope.get("artist_identity"))
              or _text(declared.get("artist")))
    source_ref = _text(raw.get("source_ref"))
    if not archive_id:
        raise CrossArchiveRelationError(f"archive_{index}_missing_archive_id")
    if not artist:
        raise CrossArchiveRelationError(f"archive_{index}_missing_artist_identity")
    if not source_ref:
        raise CrossArchiveRelationError(f"archive_{index}_missing_source_ref")
    aliases = raw.get("aliases")
    if aliases is None:
        aliases = scope.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [aliases]
    if not isinstance(aliases, Sequence) or isinstance(aliases, (bytes, bytearray)):
        aliases = []
    alias_values = sorted({_text(item) for item in aliases if _text(item)})
    return {
        "archive_id": archive_id,
        "artist_identity": artist,
        "source_ref": source_ref,
        "aliases": alias_values,
        "binding_status": (
            _text(raw.get("binding_status"))
            or _text(declared.get("binding_status"))
            or ("reconstructed_reference_only" if raw.get("schema") == "mak-archive-context-federation-v1" else "observed")
        ),
    }


def _catalog_tracks(catalog: Mapping[str, Any], source_ref: str) -> list[dict[str, Any]]:
    containers = catalog.get("containers")
    if not isinstance(containers, Mapping) or not containers:
        raise CrossArchiveRelationError("catalog_containers_required")
    tracks: list[dict[str, Any]] = []
    for container_key in sorted(containers):
        container = containers[container_key]
        if not isinstance(container, Mapping):
            raise CrossArchiveRelationError(f"catalog_container_invalid:{container_key}")
        canonical_name = _text(container.get("canonical_name"))
        if not canonical_name:
            raise CrossArchiveRelationError(f"catalog_container_name_missing:{container_key}")
        raw_tracks = container.get("tracks", [])
        if not isinstance(raw_tracks, list):
            raise CrossArchiveRelationError(f"catalog_tracks_invalid:{container_key}")
        for index, row in enumerate(raw_tracks):
            if not isinstance(row, Mapping):
                raise CrossArchiveRelationError(f"catalog_track_invalid:{container_key}:{index}")
            title = _text(row.get("title"))
            url = _text(row.get("source_url"))
            features = row.get("features", [])
            if not title or not url or not isinstance(features, list):
                raise CrossArchiveRelationError(f"catalog_track_incomplete:{container_key}:{index}")
            feature_names = sorted({_text(item) for item in features if _text(item)})
            tracks.append({
                "work_id": "catalog-track:" + hashlib.sha256(
                    _stable_json({"container": container_key, "index": index,
                                 "title": title, "source_url": url}).encode("utf-8")
                ).hexdigest()[:32],
                "title": title,
                "container": container_key,
                "canonical_name": canonical_name,
                "participants": sorted({canonical_name, *feature_names}),
                "source_ref": f"{source_ref}#containers.{container_key}.tracks[{index}]",
                "source_url": url,
            })
    return tracks


def _participant_matches(track: Mapping[str, Any], artist: str) -> bool:
    wanted = set(_tokens(artist))
    for participant in track.get("participants", []):
        candidate = set(_tokens(_text(participant)))
        if wanted and (wanted == candidate or wanted <= candidate or candidate <= wanted):
            return True
    return False


def _artifact_rows(state: Mapping[str, Any], descriptor: Mapping[str, Any], index: int) -> list[dict[str, Any]]:
    errors = validate_practice_evidence_state(state)
    if errors:
        raise CrossArchiveRelationError(
            f"archive_{index}_practice_invalid:{','.join(errors)}"
        )
    rows = state.get("artifacts")
    if not isinstance(rows, list):
        raise CrossArchiveRelationError(f"archive_{index}_artifacts_invalid")
    result: list[dict[str, Any]] = []
    refs: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise CrossArchiveRelationError(f"archive_{index}_artifact_invalid")
        ref = _text(row.get("artifact_ref"))
        path = _text(row.get("relative_path"))
        if not ref or not path or ref in refs:
            raise CrossArchiveRelationError(f"archive_{index}_artifact_ref_invalid")
        refs.add(ref)
        result.append({
            "artifact_ref": _archive_ref(_text(descriptor["archive_id"]), ref),
            "relative_path": path,
            "stem_tokens": _tokens(path.rsplit("/", 1)[-1].rsplit(".", 1)[0], remove_track_qualifiers=True),
            "evidence_refs": sorted({_text(item) for item in row.get("evidence_refs", []) if _text(item)}),
            "content_id": _text(row.get("content_id")) or None,
        })
    return result


def _matching_artifacts(artifacts: Sequence[Mapping[str, Any]], track: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    wanted = set(_tokens(_text(track.get("title")), remove_track_qualifiers=True))
    if not wanted:
        return []
    result = []
    for artifact in artifacts:
        tokens = set(artifact.get("stem_tokens", ()))
        if not tokens:
            continue
        if wanted and (wanted == tokens or wanted <= tokens):
            result.append(artifact)
    return sorted(result, key=lambda row: str(row["artifact_ref"]))


def _copy_json(value: Any) -> Any:
    copied = copy.deepcopy(value)
    try:
        _stable_json(copied)
    except (TypeError, ValueError) as exc:
        raise CrossArchiveRelationError("input_not_json") from exc
    return copied


def compile_cross_archive_relations(
    archives: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
    *,
    catalog_source_ref: str = "catalog://local",
    _validate: bool = True,
) -> dict[str, Any]:
    """Compile bounded candidate relations across two or more archives.

    Each archive row has ``practice`` (a valid practice state) and descriptor
    fields accepted by :func:`_descriptor`.  At least two distinct archives
    are required.  The catalogue is a source of explicit work/collaboration
    evidence; path tokens only locate possible manifestations and never become
    artistic truth.
    """
    if not isinstance(archives, Sequence) or isinstance(archives, (str, bytes, bytearray)):
        raise CrossArchiveRelationError("archives_required")
    if len(archives) < 2:
        raise CrossArchiveRelationError("at_least_two_archives_required")
    if not isinstance(catalog, Mapping):
        raise CrossArchiveRelationError("catalog_required")
    catalog_source_ref = _text(catalog_source_ref)
    if not catalog_source_ref:
        raise CrossArchiveRelationError("catalog_source_ref_required")

    prepared: list[dict[str, Any]] = []
    seen_archive_ids: set[str] = set()
    for index, item in enumerate(archives):
        if not isinstance(item, Mapping) or not isinstance(item.get("practice"), Mapping):
            raise CrossArchiveRelationError(f"archive_{index}_shape_invalid")
        descriptor = _descriptor(item, index)
        archive_id = descriptor["archive_id"]
        if archive_id in seen_archive_ids:
            raise CrossArchiveRelationError(f"duplicate_archive_id:{archive_id}")
        seen_archive_ids.add(archive_id)
        state = _copy_json(item["practice"])
        artifacts = _artifact_rows(state, descriptor, index)
        prepared.append({
            "descriptor": descriptor,
            "state": state,
            "artifacts": artifacts,
        })
    prepared.sort(key=lambda row: row["descriptor"]["archive_id"])

    tracks = _catalog_tracks(catalog, catalog_source_ref)
    relations: list[dict[str, Any]] = []
    matched_work_ids: set[str] = set()
    skipped: list[dict[str, Any]] = []
    for track in tracks:
        for left_index, left in enumerate(prepared):
            left_desc = left["descriptor"]
            if not _participant_matches(track, left_desc["artist_identity"]):
                continue
            left_matches = _matching_artifacts(left["artifacts"], track)
            for right in prepared[left_index + 1:]:
                right_desc = right["descriptor"]
                if not _participant_matches(track, right_desc["artist_identity"]):
                    continue
                right_matches = _matching_artifacts(right["artifacts"], track)
                if not left_matches or not right_matches:
                    continue
                matched_work_ids.add(track["work_id"])
                for source in left_matches:
                    for target in right_matches:
                        if len(relations) >= _MAX_RELATIONS:
                            skipped.append({"reason": "relation_limit_reached", "work_id": track["work_id"]})
                            break
                        source_ref = str(source["artifact_ref"])
                        target_ref = str(target["artifact_ref"])
                        semantics = {
                            "source_archive_id": left_desc["archive_id"],
                            "source_ref": source_ref,
                            "target_archive_id": right_desc["archive_id"],
                            "target_ref": target_ref,
                            "relation": "shared_collaboration_track",
                            "work_id": track["work_id"],
                            "status": _STATUS,
                            "score": 0.9,
                            "reason_codes": ["explicit_catalog_track", "explicit_collaborator", "local_title_match"],
                            "evidence_refs": sorted({catalog_source_ref, track["source_ref"], source_ref, target_ref}),
                            "evidence_for": [
                                {"kind": "catalog_track", "source_ref": track["source_ref"], "title": track["title"]},
                                {"kind": "artifact_name_signal", "artifact_ref": source_ref, "relative_path": source["relative_path"]},
                                {"kind": "artifact_name_signal", "artifact_ref": target_ref, "relative_path": target["relative_path"]},
                            ],
                            "evidence_against": [
                                {"code": "exact_cross_archive_content_unavailable"}
                            ],
                            "missing_evidence": ["exact_cross_archive_content_or_delivery_binding"],
                            "next_probe": "Compare an explicit delivery or publication witness for this track; keep physical artifacts separate.",
                            "alternatives": ["same_title_different_work"],
                        }
                        relation = dict(semantics)
                        relation["relation_id"] = "cross-rel-" + hashlib.sha256(
                            _stable_json(semantics).encode("utf-8")
                        ).hexdigest()[:32]
                        relations.append(relation)
                    if len(relations) >= _MAX_RELATIONS:
                        break
                if len(relations) >= _MAX_RELATIONS:
                    break
            if len(relations) >= _MAX_RELATIONS:
                break
        if len(relations) >= _MAX_RELATIONS:
            break

    relations.sort(key=lambda row: row["relation_id"])
    archive_rows = []
    all_artifact_refs: set[str] = set()
    for row in prepared:
        descriptor = row["descriptor"]
        state = row["state"]
        all_artifact_refs.update(str(item["artifact_ref"]) for item in row["artifacts"])
        archive_rows.append({
            "archive_id": descriptor["archive_id"],
            "artist_identity": descriptor["artist_identity"],
            "source_ref": descriptor["source_ref"],
            "binding_status": descriptor["binding_status"],
            "snapshot_id": _text(state.get("snapshot_id")) or "unknown",
            "input_hash": _text(state.get("input_hash")),
            "state_hash": _text(state.get("state_hash")),
            "practice_binding": (
                "physical_snapshot"
                if _text(state.get("archive_id")) not in {"", "unknown"}
                and _text(state.get("snapshot_id")) not in {"", "unknown"}
                else "reconstructed_reference_only"
            ),
            "artifact_count": len(row["artifacts"]),
        })
    archive_rows.sort(key=lambda row: row["archive_id"])
    output = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "catalog_source_ref": catalog_source_ref,
        "catalog_hash": _sha256(catalog),
        "archives": archive_rows,
        "relations": relations,
        "skipped": sorted(skipped, key=lambda row: _stable_json(row)),
        "limits": {"max_relations": _MAX_RELATIONS, "relation_count": len(relations)},
        "control": {
            "source_rescan": False,
            "database_write": False,
            "network_called": False,
            "promotion": "none",
            "physical_merge": False,
            "truth_promotion": False,
        },
        "reconciliation": {
            "archive_count": len(archive_rows),
            "physical_artifact_count": len(all_artifact_refs),
            "cross_archive_relation_count": len(relations),
            "matched_catalog_work_count": len(matched_work_ids),
            "relation_ids_unique": len({row["relation_id"] for row in relations}) == len(relations),
            "endpoints_resolve": True,
            "physical_artifacts_merged": 0,
            "truth_promotions": 0,
            "deterministic_order": True,
            "coverage_truncated": bool(skipped),
        },
    }
    if _validate:
        validate_cross_archive_relations(output, archives, catalog)
    return output


def validate_cross_archive_relations(
    payload: Mapping[str, Any],
    archives: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
) -> bool:
    """Strictly validate output shape and physical endpoint resolution."""
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        return False
    if payload.get("algorithm_version") != ALGORITHM_VERSION:
        return False
    if not isinstance(payload.get("archives"), list) or not isinstance(payload.get("relations"), list):
        return False
    try:
        expected = compile_cross_archive_relations(
            archives, catalog, catalog_source_ref=_text(payload.get("catalog_source_ref")),
            _validate=False,
        )
    except (CrossArchiveRelationError, TypeError, ValueError):
        return False
    if _stable_json(expected) != _stable_json(payload):
        return False
    control = payload.get("control")
    reconciliation = payload.get("reconciliation")
    if not isinstance(control, Mapping) or not isinstance(reconciliation, Mapping):
        return False
    if control.get("physical_merge") is not False or control.get("truth_promotion") is not False:
        return False
    if reconciliation.get("physical_artifacts_merged") != 0 or reconciliation.get("truth_promotions") != 0:
        return False
    return True


def project_cross_archive_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Project candidates into the existing ``mak-project-context-v1`` shape.

    The result is a read-only package for the existing context consumer.  It
    contains only artifact-to-artifact candidate relations and a catalogue
    source; it deliberately does not create projects or write the database.
    """
    if not isinstance(payload, Mapping) or not validate_cross_archive_relations_payload_shape(payload):
        raise CrossArchiveRelationError("relation_payload_invalid")
    archives = {str(row["archive_id"]): row for row in payload["archives"]}
    if len(archives) < 2:
        raise CrossArchiveRelationError("context_requires_two_archives")

    def source_id(kind: str, ref: str) -> str:
        return "cross-source:" + hashlib.sha256(
            _stable_json({"kind": kind, "ref": ref}).encode("utf-8")
        ).hexdigest()[:32]

    artifact_info: dict[str, dict[str, Any]] = {}
    work_titles: dict[str, str] = {}
    for relation in payload["relations"]:
        for item in relation.get("evidence_for", []):
            if not isinstance(item, Mapping):
                continue
            if item.get("kind") == "catalog_track":
                work_titles[str(relation["work_id"])] = _text(item.get("title"))
            if item.get("kind") == "artifact_name_signal":
                ref = _text(item.get("artifact_ref"))
                if ref:
                    artifact_info[ref] = {
                        "display_name": _text(item.get("relative_path")) or ref,
                        "archive_id": str(relation["source_archive_id"])
                        if ref == relation["source_ref"]
                        else str(relation["target_archive_id"]),
                        "artifact_role": "candidate_visual_manifestation",
                        "authorship_status": "not_inferred",
                        "missing_evidence": [
                            "native_authoring_project_or_explicit_visual_credit"
                        ],
                    }
    archive_by_id = archives
    entities: list[dict[str, Any]] = []
    for ref in sorted(artifact_info):
        info = artifact_info[ref]
        binding = archive_by_id[info["archive_id"]].get("practice_binding")
        entities.append({
            "entity_id": "artifact:" + hashlib.sha256(ref.encode("utf-8")).hexdigest()[:32],
            "display_name": info["display_name"],
            "kind": "archive_artifact",
            "origin": "practice_evidence_state",
            "purpose": "Physical or reconstructed endpoint retained for a candidate cross-archive relation.",
            "idea": "Artifact identity is not merged across archives.",
            "status": "observed" if binding == "physical_snapshot" else "candidate",
            "artifact_role": info["artifact_role"],
            "holder_role": (
                "archive_observed"
                if binding == "physical_snapshot"
                else "reconstructed_reference"
            ),
            "authorship_status": info["authorship_status"],
        })
    for work_id in sorted(work_titles):
        entities.append({
            "entity_id": work_id,
            "display_name": work_titles[work_id] or work_id,
            "kind": "catalog_track",
            "origin": "explicit_local_catalogue",
            "purpose": "Catalogue work reference used to explain a candidate relation.",
            "idea": "Catalogue evidence is not proof of a file's delivery or authorship.",
            "status": "candidate",
        })
    entities.sort(key=lambda row: row["entity_id"])

    catalog_source_id = source_id("catalog", str(payload["catalog_source_ref"]))
    sources = [{
        "source_id": catalog_source_id,
        "source_type": "local_catalogue",
        "independence_group": "catalogue:" + str(payload["catalog_hash"]),
        "locator": str(payload["catalog_source_ref"]),
        "claim": "The local catalogue explicitly lists the track and its named collaborators; this supports a candidate cross-archive relation only.",
        "status": "observed",
        "metadata": {"catalog_hash": payload["catalog_hash"]},
    }]
    source_rows: dict[str, dict[str, Any]] = {catalog_source_id: sources[0]}
    for ref, info in sorted(artifact_info.items()):
        archive = archive_by_id[info["archive_id"]]
        sid = source_id("artifact", ref)
        source_rows[sid] = {
            "source_id": sid,
            "source_type": "practice_evidence_state",
            "independence_group": "archive:" + info["archive_id"],
            "locator": ref,
            "claim": "Artifact endpoint observed in the supplied practice-evidence state; filename/path is a locating signal, not cultural truth.",
            "status": "observed" if archive.get("practice_binding") == "physical_snapshot" else "candidate",
            "metadata": {"archive_id": info["archive_id"], "practice_binding": archive.get("practice_binding")},
        }
    sources = [source_rows[key] for key in sorted(source_rows)]
    relations: list[dict[str, Any]] = []
    role_bindings: list[dict[str, Any]] = []
    role_binding_keys: set[tuple[str, str, str]] = set()
    artifact_work_keys: set[tuple[str, str]] = set()

    def role_evidence(artifact_ref: str, work_id: str) -> dict[str, Any]:
        info = artifact_info[artifact_ref]
        binding = archive_by_id[info["archive_id"]].get("practice_binding")
        return {
            "kind": "artifact_role",
            "artifact_ref": artifact_ref,
            "work_id": work_id,
            "role": info["artifact_role"],
            "holder_role": (
                "archive_observed"
                if binding == "physical_snapshot"
                else "reconstructed_reference"
            ),
            "authorship_status": info["authorship_status"],
            "missing_evidence": list(info["missing_evidence"]),
        }

    for row in payload["relations"]:
        source_ref = str(row["source_ref"])
        target_ref = str(row["target_ref"])
        work_id = str(row["work_id"])
        for artifact_ref in (source_ref, target_ref):
            info = artifact_info[artifact_ref]
            archive_id = str(info["archive_id"])
            binding_key = (archive_id, artifact_ref, work_id)
            if binding_key not in role_binding_keys:
                role_binding_keys.add(binding_key)
                holder = (
                    "archive_observed"
                    if archive_by_id[archive_id].get("practice_binding") == "physical_snapshot"
                    else "reconstructed_reference"
                )
                binding_semantics = {
                    "archive_id": archive_id,
                    "artifact_ref": artifact_ref,
                    "work_id": work_id,
                    "artifact_role": info["artifact_role"],
                }
                role_bindings.append({
                    "binding_id": "role-binding:" + hashlib.sha256(
                        _stable_json(binding_semantics).encode("utf-8")
                    ).hexdigest()[:32],
                    **binding_semantics,
                    "holder_role": holder,
                    "authorship_status": info["authorship_status"],
                    "status": "candidate",
                    "missing_evidence": list(info["missing_evidence"]),
                    "source_ids": sorted({
                        catalog_source_id,
                        source_id("artifact", artifact_ref),
                    }),
                })
        relations.append({
            "subject": "artifact:" + hashlib.sha256(source_ref.encode("utf-8")).hexdigest()[:32],
            "predicate": "shared_collaboration_track",
            "object": "artifact:" + hashlib.sha256(target_ref.encode("utf-8")).hexdigest()[:32],
            "status": "candidate",
            "source_ids": sorted({
                catalog_source_id,
                source_id("artifact", source_ref),
                source_id("artifact", target_ref),
            }),
            "evidence": [
                role_evidence(source_ref, work_id),
                role_evidence(target_ref, work_id),
                {
                    "kind": "participation_scope",
                    "work_id": work_id,
                    "scope": "matched_archive_artists_only",
                    "exhaustive": False,
                    "roles": ["musical_participant"],
                },
            ],
        })
        for artifact_ref in (source_ref, target_ref):
            key = (artifact_ref, work_id)
            if key in artifact_work_keys:
                continue
            artifact_work_keys.add(key)
            relations.append({
                "subject": "artifact:" + hashlib.sha256(artifact_ref.encode("utf-8")).hexdigest()[:32],
                "predicate": "candidate_manifestation_of",
                "object": work_id,
                "status": "candidate",
                "source_ids": sorted({
                    catalog_source_id,
                    source_id("artifact", artifact_ref),
                }),
                "evidence": [
                    role_evidence(artifact_ref, work_id),
                    {
                        "kind": "authorship_gap",
                        "status": "unknown",
                        "missing_evidence": list(artifact_info[artifact_ref]["missing_evidence"]),
                    },
                ],
            })
    relations.sort(key=lambda row: (row["subject"], row["predicate"], row["object"]))
    role_bindings.sort(key=lambda row: row["binding_id"])
    archive_ids = sorted(archives)
    context_id = "cross-archive:" + hashlib.sha256(_stable_json({
        "archive_ids": archive_ids,
        "catalog_hash": payload["catalog_hash"],
        "relation_ids": [row["relation_id"] for row in payload["relations"]],
    }).encode("utf-8")).hexdigest()[:32]
    context = {
        "schema": "mak-project-context-v1",
        "context_id": context_id,
        "title": "Cross-archive collaboration candidates",
        "scope": "candidate_relation_projection",
        "unknowns": ["exact_cross_archive_content_or_delivery_binding"],
        "entities": entities,
        "sources": sources,
        "relations": relations,
        "role_bindings": role_bindings,
        "participation_scope": {
            "status": "candidate",
            "scope": "matched_archive_artists_only",
            "exhaustive": False,
            "note": (
                "The context records only archive artists matched to this relation; "
                "the catalogue may name additional collaborators."
            ),
        },
        "projects": [],
        "provenance": {
            "source_schema": SCHEMA,
            "relation_payload_hash": _sha256(payload),
            "database_write": False,
            "promotion": "none",
        },
    }
    errors = validate_context(context)
    if errors:
        raise CrossArchiveRelationError("project_context_invalid:" + ",".join(errors))
    return context


def validate_cross_archive_relations_payload_shape(payload: Mapping[str, Any]) -> bool:
    """Cheap shape check used by the context projection without recursion."""
    return (
        payload.get("schema") == SCHEMA
        and isinstance(payload.get("archives"), list)
        and isinstance(payload.get("relations"), list)
        and isinstance(payload.get("catalog_source_ref"), str)
        and isinstance(payload.get("catalog_hash"), str)
        and all(isinstance(row, Mapping) for row in payload["archives"])
        and all(isinstance(row, Mapping) for row in payload["relations"])
    )


def project_archive_catalog_context(
    archive: Mapping[str, Any],
    catalog: Mapping[str, Any],
    *,
    catalog_source_ref: str = "catalog://local",
) -> dict[str, Any]:
    """Project one archive's catalogue matches into the existing context graph.

    ``compile_cross_archive_relations`` intentionally requires two archives and
    therefore cannot represent a local output whose public work has no second
    physical endpoint.  This bounded projection closes that edge without
    changing the cross-archive contract: an artifact is a candidate
    manifestation of a catalogue work, never proof of authorship, delivery or
    physical identity.
    """
    if not isinstance(archive, Mapping) or not isinstance(archive.get("practice"), Mapping):
        raise CrossArchiveRelationError("archive_shape_invalid")
    if not isinstance(catalog, Mapping):
        raise CrossArchiveRelationError("catalog_required")
    catalog_source_ref = _text(catalog_source_ref)
    if not catalog_source_ref:
        raise CrossArchiveRelationError("catalog_source_ref_required")

    descriptor = _descriptor(archive, 0)
    state = _copy_json(archive["practice"])
    artifacts = _artifact_rows(state, descriptor, 0)
    tracks = _catalog_tracks(catalog, catalog_source_ref)
    artifact_by_ref = {str(row["artifact_ref"]): row for row in artifacts}

    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    skipped: list[dict[str, Any]] = []
    for track in tracks:
        if not _participant_matches(track, descriptor["artist_identity"]):
            continue
        for artifact in _matching_artifacts(artifacts, track):
            if len(matches) >= _MAX_RELATIONS:
                skipped.append({"reason": "relation_limit_reached", "work_id": track["work_id"]})
                continue
            matches.append((track, dict(artifact)))
    matches.sort(key=lambda pair: (str(pair[0]["work_id"]), str(pair[1]["artifact_ref"])))

    def source_id(kind: str, ref: str) -> str:
        return "archive-catalog-source:" + hashlib.sha256(
            _stable_json({"kind": kind, "ref": ref}).encode("utf-8")
        ).hexdigest()[:32]

    catalog_hash = _sha256(catalog)
    catalog_source_id = source_id("catalog", catalog_source_ref)
    binding_status = descriptor["binding_status"]
    holder_role = (
        "archive_observed"
        if binding_status == "physical_snapshot"
        else "reconstructed_reference"
    )
    artifact_info: dict[str, dict[str, Any]] = {}
    work_info: dict[str, dict[str, Any]] = {}
    for track, artifact in matches:
        artifact_ref = str(artifact["artifact_ref"])
        artifact_info[artifact_ref] = artifact
        work_info[str(track["work_id"])] = track

    entities: list[dict[str, Any]] = []
    for artifact_ref in sorted(artifact_info):
        artifact = artifact_info[artifact_ref]
        entities.append({
            "entity_id": "artifact:" + hashlib.sha256(artifact_ref.encode("utf-8")).hexdigest()[:32],
            "display_name": str(artifact["relative_path"]),
            "kind": "archive_artifact",
            "origin": "practice_evidence_state",
            "purpose": "Archive endpoint matched to a public catalogue work by an explicit title signal.",
            "idea": "The match is a candidate manifestation and does not promote authorship.",
            "status": "observed" if holder_role == "archive_observed" else "candidate",
            "artifact_role": "candidate_visual_manifestation",
            "holder_role": holder_role,
            "authorship_status": "not_inferred",
        })
    for work_id in sorted(work_info):
        track = work_info[work_id]
        entities.append({
            "entity_id": work_id,
            "display_name": str(track["title"]),
            "kind": "catalog_track",
            "origin": "explicit_local_catalogue",
            "purpose": "Public work anchor used to explain a local archive candidate.",
            "idea": "Catalogue evidence does not prove the local file's delivery or authorship.",
            "status": "candidate",
        })
    entities.sort(key=lambda row: str(row["entity_id"]))

    sources: dict[str, dict[str, Any]] = {
        catalog_source_id: {
            "source_id": catalog_source_id,
            "source_type": "local_catalogue",
            "independence_group": "catalogue:" + catalog_hash,
            "locator": catalog_source_ref,
            "claim": "The local catalogue explicitly lists the public work and named participants; this supports a candidate manifestation only.",
            "status": "observed",
            "metadata": {"catalog_hash": catalog_hash},
        }
    }
    for artifact_ref in sorted(artifact_info):
        sources[source_id("artifact", artifact_ref)] = {
            "source_id": source_id("artifact", artifact_ref),
            "source_type": "practice_evidence_state",
            "independence_group": "archive:" + descriptor["archive_id"],
            "locator": artifact_ref,
            "claim": "The archive endpoint is present in the supplied practice state; its path is a locating signal, not cultural truth.",
            "status": "observed" if holder_role == "archive_observed" else "candidate",
            "metadata": {
                "archive_id": descriptor["archive_id"],
                "snapshot_id": _text(state.get("snapshot_id")) or "unknown",
                "binding_status": binding_status,
            },
        }

    relations: list[dict[str, Any]] = []
    role_bindings: list[dict[str, Any]] = []
    for track, artifact in matches:
        artifact_ref = str(artifact["artifact_ref"])
        work_id = str(track["work_id"])
        artifact_entity_id = "artifact:" + hashlib.sha256(artifact_ref.encode("utf-8")).hexdigest()[:32]
        artifact_source_id = source_id("artifact", artifact_ref)
        missing = ["native_authoring_project_or_explicit_visual_credit"]
        evidence = [
            {
                "kind": "catalog_track",
                "source_ref": str(track["source_ref"]),
                "source_url": str(track["source_url"]),
                "title": str(track["title"]),
                "participants": list(track["participants"]),
            },
            {
                "kind": "artifact_role",
                "archive_id": descriptor["archive_id"],
                "artifact_ref": artifact_ref,
                "work_id": work_id,
                "role": "candidate_visual_manifestation",
                "holder_role": holder_role,
                "authorship_status": "not_inferred",
                "missing_evidence": missing,
            },
            {
                "kind": "artifact_name_signal",
                "artifact_ref": artifact_ref,
                "relative_path": str(artifact["relative_path"]),
                "signal_scope": "candidate_locator_only",
            },
            {
                "kind": "authorship_gap",
                "status": "unknown",
                "missing_evidence": missing,
            },
        ]
        relations.append({
            "subject": artifact_entity_id,
            "predicate": "candidate_manifestation_of",
            "object": work_id,
            "status": "candidate",
            "source_ids": [catalog_source_id, artifact_source_id],
            "evidence": evidence,
        })
        binding_semantics = {
            "archive_id": descriptor["archive_id"],
            "artifact_ref": artifact_ref,
            "work_id": work_id,
            "artifact_role": "candidate_visual_manifestation",
        }
        role_bindings.append({
            "binding_id": "archive-catalog-role-binding:" + hashlib.sha256(
                _stable_json(binding_semantics).encode("utf-8")
            ).hexdigest()[:32],
            **binding_semantics,
            "holder_role": holder_role,
            "authorship_status": "not_inferred",
            "status": "candidate",
            "missing_evidence": missing,
            "source_ids": [catalog_source_id, artifact_source_id],
        })
    relations.sort(key=lambda row: (str(row["subject"]), str(row["predicate"]), str(row["object"])))
    role_bindings.sort(key=lambda row: str(row["binding_id"]))

    archive_id = str(descriptor["archive_id"])
    snapshot_id = _text(state.get("snapshot_id")) or "unknown"
    input_hash = _text(state.get("input_hash")) or "unknown"
    state_hash = _text(state.get("state_hash")) or "unknown"
    context_id = "archive-catalog:" + hashlib.sha256(_stable_json({
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": input_hash,
        "state_hash": state_hash,
        "catalog_hash": catalog_hash,
        "matches": [
            {"artifact_ref": str(artifact["artifact_ref"]), "work_id": str(track["work_id"])}
            for track, artifact in matches
        ],
    }).encode("utf-8")).hexdigest()[:32]
    context = {
        "schema": "mak-project-context-v1",
        "context_id": context_id,
        "title": "Archive-to-catalog manifestation candidates",
        "scope": "archive_catalog_candidate_projection",
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "input_hash": input_hash,
        "state_hash": state_hash,
        "catalog_source_ref": catalog_source_ref,
        "catalog_hash": catalog_hash,
        "unknowns": ["native_authoring_or_delivery_binding"],
        "entities": entities,
        "sources": [sources[key] for key in sorted(sources)],
        "relations": relations,
        "role_bindings": role_bindings,
        "participation_scope": {
            "status": "candidate",
            "scope": "matched_archive_artist_only",
            "exhaustive": False,
            "note": "Only catalogue works whose explicit participants match the archive artist and whose title locates an archive artifact are projected.",
        },
        "projects": [],
        "provenance": {
            "source_schema": "mak-practice-evidence-state-v1",
            "practice_source_ref": str(archive.get("source_ref", "")),
            "practice_input_hash": input_hash,
            "practice_state_hash": state_hash,
            "catalog_hash": catalog_hash,
            "source_rescan": False,
            "database_write": False,
            "network_called": False,
            "promotion": "none",
        },
        "reconciliation": {
            "archive_id": archive_id,
            "snapshot_id": snapshot_id,
            "artifact_match_count": len(matches),
            "unique_artifact_count": len(artifact_info),
            "catalog_work_count": len(work_info),
            "relation_count": len(relations),
            "role_binding_count": len(role_bindings),
            "relation_ids_unique": len({
                (row["subject"], row["predicate"], row["object"]) for row in relations
            }) == len(relations),
            "endpoints_resolve": all(
                row["subject"] in {entity["entity_id"] for entity in entities}
                and row["object"] in {entity["entity_id"] for entity in entities}
                for row in relations
            ),
            "physical_artifacts_merged": 0,
            "truth_promotions": 0,
            "authorship_promotions": 0,
            "coverage_truncated": bool(skipped),
            "skipped": sorted(skipped, key=lambda row: _stable_json(row)),
            "deterministic_order": True,
        },
    }
    errors = validate_context(context)
    if errors:
        raise CrossArchiveRelationError("project_context_invalid:" + ",".join(errors))
    return context
