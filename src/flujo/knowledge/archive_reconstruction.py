"""Deterministic Stage 2A projection from archive memory to reconstruction input.

This module is intentionally narrower than the reconstruction engine.  It
accepts one strict, replayed ``mak-archive-observation-batch-v1`` payload and
projects physical artifacts plus candidate observations into a vocabulary that
the next inference stage can consume.  It does not assign works, projects,
series, authorship or artistic truth.

``mtime_ns`` and ``change_set`` are observer diagnostics, not semantic
identity.  The projection therefore omits both from its output and its input
hash.  Exact duplicate bytes remain separate physical artifacts and are joined
only through a content index.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Mapping

from ._contract_helpers import sha256_ref as _hash, stable_json as _stable_json

from .archive_observer import ArchiveObservationError, validate_batch
from .project_reconstruction import OUTPUT_MEDIA


SCHEMA = "mak-archive-reconstruction-input-v1"
OBSERVER_SCHEMA = "mak-archive-observation-batch-v1"

NATIVE_AUTHORING_EXTENSIONS = frozenset({
    ".aep", ".afdesign", ".afphoto", ".blend", ".c4d", ".clip",
    ".hip", ".hiplc", ".indd", ".kra", ".ma", ".mb", ".max", ".psd",
    ".spp", ".uasset", ".umap", ".uproject", ".xcf",
})
SIDECAR_EXTENSIONS = frozenset({
    ".ass", ".caption", ".csv", ".cue", ".json", ".md", ".md5",
    ".metadata", ".nfo", ".srt", ".sha1", ".sha256", ".sub", ".txt",
    ".vtt", ".xmp", ".xml", ".yaml", ".yml",
})
MANIFEST_TOKENS = (
    "catalog", "catalogue", "checksum", "index", "manifest", "metadata",
)
NUMBER_TOKEN = re.compile(r"(?<!\d)(\d{2,})(?!\d)")


class ArchiveReconstructionError(ValueError):
    """Invalid observer input or impossible projection invariant."""


def _parent_path(relative_path: str) -> str:
    parent = PurePosixPath(relative_path).parent.as_posix()
    return "" if parent == "." else parent


def _name_parts(relative_path: str) -> tuple[str, str, list[str]]:
    basename = PurePosixPath(relative_path).name
    suffix_chain = list(PurePosixPath(basename).suffixes)
    suffix_text = "".join(suffix_chain)
    if suffix_text and basename.endswith(suffix_text):
        stem = basename[: -len(suffix_text)] or basename
    else:
        stem = basename
    return basename, stem, suffix_chain


def _numbered_name_token(stem: str) -> str | None:
    match = NUMBER_TOKEN.search(stem)
    return match.group(1) if match else None


def _content_group_id(artifact: Mapping[str, Any]) -> str | None:
    content_id = artifact.get("content_id")
    if isinstance(content_id, str) and content_id:
        return content_id
    return None


def _semantic_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Return observer artifact semantics without volatile mtime metadata."""

    return {
        key: artifact[key]
        for key in sorted(artifact)
        if key != "mtime_ns"
    }


def _artifact_projection(
    artifact: Mapping[str, Any],
    duplicate_content_ids: set[str],
) -> dict[str, Any]:
    relative_path = str(artifact["relative_path"])
    basename, stem, suffix_chain = _name_parts(relative_path)
    suffix = suffix_chain[-1].lower() if suffix_chain else ""
    family = str(artifact["family"])
    media_type = str(artifact["media_type"])
    lower_stem = stem.casefold()
    content_id = _content_group_id(artifact)
    numbered_token = _numbered_name_token(stem)
    sidecar_or_manifest = (
        suffix in SIDECAR_EXTENSIONS
        or any(token in lower_stem for token in MANIFEST_TOKENS)
    )
    return {
        "artifact_id": artifact["artifact_id"],
        "physical_id": artifact["physical_id"],
        "artifact_ref": artifact["artifact_ref"],
        "references": list(artifact["references"]),
        "relative_path": relative_path,
        "parent_path": _parent_path(relative_path),
        "basename": basename,
        "stem": stem,
        "suffix_chain": suffix_chain,
        "kind": artifact["kind"],
        "availability": artifact["availability"],
        "family": family,
        "media_type": media_type,
        "size": artifact["size"],
        "sha256": artifact["sha256"],
        "content_id": content_id,
        "derived_flags": {
            "native_authoring_anchor": suffix in NATIVE_AUTHORING_EXTENSIONS,
            "probable_output_media": family in OUTPUT_MEDIA
            or media_type.startswith("image/")
            or media_type.startswith("video/"),
            "sidecar_or_manifest": sidecar_or_manifest,
            "numbered_name_token": numbered_token,
            "duplicate_content_member": content_id in duplicate_content_ids
            if content_id is not None else False,
            "directory_depth": relative_path.count("/"),
        },
    }


def _candidate_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Keep an observer candidate typed without promoting its status."""

    return {
        "record_type": "candidate_observation",
        "observation_id": observation["observation_id"],
        "observation_type": observation["observation_type"],
        "status": observation["status"],
        "artifact_refs": list(observation["artifact_refs"]),
        "evidence": observation["evidence"],
    }


def _observation_sort_key(observation: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(observation["observation_type"]),
        _stable_json(observation["artifact_refs"]),
        _stable_json(observation["evidence"]),
    )


def _validate_json_surface(value: Any, path: str = "output") -> None:
    """Reject accidental Path/set/other non-JSON values before returning."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_surface(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ArchiveReconstructionError(f"non_string_output_key:{path}")
            _validate_json_surface(item, f"{path}.{key}")
        return
    raise ArchiveReconstructionError(f"non_json_output_value:{path}")


def project_archive_snapshot(batch: Mapping[str, Any]) -> dict[str, Any]:
    """Project one strict observer batch into reconstruction features.

    Validation happens before any derived field is read.  The result contains
    only physical identity, observed metadata, typed candidate evidence and
    deterministic features; it cannot claim a work or project.
    """

    if not isinstance(batch, Mapping):
        raise ArchiveReconstructionError("batch_must_be_mapping")
    candidate = dict(batch)
    try:
        validate_batch(candidate)
    except ArchiveObservationError as error:
        raise ArchiveReconstructionError(f"batch_invalid:{error}") from error

    artifacts = list(candidate["artifacts"])
    observations = list(candidate["observations"])
    content_counts: dict[str, int] = {}
    for artifact in artifacts:
        content_id = _content_group_id(artifact)
        if content_id is not None:
            content_counts[content_id] = content_counts.get(content_id, 0) + 1
    duplicate_content_ids = {
        content_id for content_id, count in content_counts.items() if count > 1
    }

    projected_artifacts = [
        _artifact_projection(artifact, duplicate_content_ids)
        for artifact in artifacts
    ]
    projected_artifacts.sort(key=lambda item: (item["relative_path"], item["artifact_id"]))
    projected_observations = [_candidate_observation(item) for item in observations]
    projected_observations.sort(key=_observation_sort_key)

    artifacts_by_parent: dict[str, list[str]] = {}
    artifacts_by_content: dict[str, list[str]] = {}
    native_anchor_refs: list[str] = []
    probable_output_refs: list[str] = []
    for artifact in projected_artifacts:
        ref = str(artifact["artifact_ref"])
        artifacts_by_parent.setdefault(str(artifact["parent_path"]), []).append(ref)
        content_id = artifact["content_id"]
        if content_id is not None:
            artifacts_by_content.setdefault(str(content_id), []).append(ref)
        flags = artifact["derived_flags"]
        if flags["native_authoring_anchor"]:
            native_anchor_refs.append(ref)
        if flags["probable_output_media"]:
            probable_output_refs.append(ref)

    for index in (artifacts_by_parent, artifacts_by_content):
        for refs in index.values():
            refs.sort()
    artifacts_by_parent = dict(sorted(artifacts_by_parent.items()))
    artifacts_by_content = dict(sorted(artifacts_by_content.items()))
    native_anchor_refs.sort()
    probable_output_refs.sort()
    candidate_observation_ids = sorted(
        str(item["observation_id"]) for item in projected_observations
    )

    semantic_input = {
        "schema": candidate["schema"],
        "archive_id": candidate["archive_id"],
        "snapshot_id": candidate["snapshot_id"],
        "limits": candidate["limits"],
        "artifacts": [_semantic_artifact(item) for item in artifacts],
        "observations": sorted(observations, key=_observation_sort_key),
    }
    artifact_ids = [str(item["artifact_id"]) for item in projected_artifacts]
    observation_ids = [str(item["observation_id"]) for item in projected_observations]
    reconciliation = {
        "artifacts_observed": len(artifacts),
        "artifacts_projected": len(projected_artifacts),
        "artifact_identity_count": len(set(artifact_ids)),
        "artifact_identity_duplicates": len(artifact_ids) - len(set(artifact_ids)),
        "artifact_loss": len(artifacts) - len(projected_artifacts),
        "observations_observed": len(observations),
        "observations_projected": len(projected_observations),
        "observation_identity_count": len(set(observation_ids)),
        "observation_identity_duplicates": len(observation_ids) - len(set(observation_ids)),
        "observation_loss": len(observations) - len(projected_observations),
        "status": "consistent",
    }
    if any(
        reconciliation[key] != 0
        for key in (
            "artifact_identity_duplicates", "artifact_loss",
            "observation_identity_duplicates", "observation_loss",
        )
    ):
        raise ArchiveReconstructionError("reconciliation_invariant_failed")

    output = {
        "schema": SCHEMA,
        "source_schema": OBSERVER_SCHEMA,
        "archive_id": candidate["archive_id"],
        "snapshot_id": candidate["snapshot_id"],
        "limits": candidate["limits"],
        "input_hash": _hash(semantic_input),
        "artifacts": projected_artifacts,
        "candidate_observations": projected_observations,
        "artifacts_by_parent": artifacts_by_parent,
        "artifacts_by_content": artifacts_by_content,
        "native_anchor_refs": native_anchor_refs,
        "probable_output_refs": probable_output_refs,
        "candidate_observation_ids": candidate_observation_ids,
        "reconciliation": reconciliation,
    }
    _validate_json_surface(output)
    return output


__all__ = [
    "ArchiveReconstructionError",
    "SCHEMA",
    "project_archive_snapshot",
]
