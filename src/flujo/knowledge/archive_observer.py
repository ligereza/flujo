"""Deterministic, read-only observations of an explicitly supplied archive.

This module deliberately observes physical entries only.  It does not assign
artistic identity, project identity, series identity, or transformation
semantics to anything it finds.
"""

from __future__ import annotations

import errno
import fnmatch
import hashlib
import json
import mimetypes
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from ._contract_helpers import stable_json as _canonical_json


SCHEMA = "mak-archive-observation-batch-v1"


class ArchiveObservationError(ValueError):
    """Base error for invalid observer inputs or archive batches."""


class ArchiveObservationValidationError(ArchiveObservationError):
    """Raised when a batch does not satisfy the versioned contract."""


_BATCH_KEYS = {
    "schema",
    "archive_id",
    "snapshot_id",
    "limits",
    "artifacts",
    "observations",
    "change_set",
}
_LIMIT_KEYS = {"include", "exclude", "max_files", "follow_symlinks"}
_ARTIFACT_KEYS = {
    "archive_id",
    "artifact_id",
    "physical_id",
    "artifact_ref",
    "references",
    "relative_path",
    "kind",
    "availability",
    "size",
    "mtime_ns",
    "extension",
    "family",
    "media_type",
    "sha256",
    "content_id",
    "symlink_target",
    "error_code",
    "error_operation",
}
_OBSERVATION_KEYS = {
    "observation_id",
    "observation_type",
    "status",
    "artifact_refs",
    "evidence",
}
_CHANGE_KEYS = {"added", "changed", "unchanged", "missing"}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SEQUENCE_RE = re.compile(r"^(?P<prefix>.*?)(?P<number>[0-9]+)(?P<suffix>\.[^.]*)?$", re.IGNORECASE)
_SIDECAR_EXTENSIONS = {
    ".ass",
    ".caption",
    ".csv",
    ".cue",
    ".json",
    ".md",
    ".md5",
    ".metadata",
    ".nfo",
    ".srt",
    ".sha1",
    ".sha256",
    ".sub",
    ".txt",
    ".vtt",
    ".xmp",
    ".xml",
    ".yaml",
    ".yml",
}
_MANIFEST_WORDS = ("manifest", "metadata", "catalog", "catalogue", "index", "checksum", "checksums")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_archive_id(archive_id: Any) -> str:
    if not isinstance(archive_id, str) or not archive_id or archive_id != archive_id.strip():
        raise ArchiveObservationError("archive_id must be a non-empty string without surrounding whitespace")
    return archive_id


def _normalise_relative_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise ArchiveObservationValidationError("relative_path must be a non-empty string")
    if "\\" in path:
        raise ArchiveObservationValidationError("relative_path must use POSIX separators")
    posix = PurePosixPath(path).as_posix()
    if posix in {"", "."} or posix.startswith("/"):
        raise ArchiveObservationValidationError("relative_path must be relative and non-empty")
    parts = posix.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ArchiveObservationValidationError("relative_path must be normalized POSIX path")
    return posix


def _relative_path(root: str, full_path: str) -> str:
    relative = os.path.relpath(full_path, root)
    # The observer runs on the host filesystem, but emitting through
    # PurePosixPath also makes the contract explicit for an integrator.
    return PurePosixPath(*Path(relative).parts).as_posix()


def _normalise_patterns(patterns: Sequence[str] | None) -> list[str]:
    if patterns is None:
        return []
    if isinstance(patterns, (str, bytes)):
        raise ArchiveObservationError("include/exclude must be sequences of strings")
    result: list[str] = []
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            raise ArchiveObservationError("include/exclude patterns must be non-empty strings")
        normalised = pattern.replace(os.sep, "/") if os.sep != "/" else pattern
        normalised = PurePosixPath(normalised).as_posix()
        if normalised.startswith("/"):
            raise ArchiveObservationError("include/exclude patterns must be relative")
        result.append(normalised)
    return sorted(set(result))


def _validate_limits(limits: Any) -> None:
    if not isinstance(limits, dict) or set(limits) != _LIMIT_KEYS:
        raise ArchiveObservationValidationError("limits must contain exactly the versioned limit keys")
    for key in ("include", "exclude"):
        values = limits[key]
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise ArchiveObservationValidationError(f"limits.{key} must be a list of non-empty strings")
        try:
            expected_patterns = _normalise_patterns(values)
        except ArchiveObservationError as error:
            raise ArchiveObservationValidationError(f"limits.{key} contains an invalid pattern") from error
        if values != expected_patterns:
            raise ArchiveObservationValidationError(f"limits.{key} must be sorted and unique")
    max_files = limits["max_files"]
    if max_files is not None and (isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 0):
        raise ArchiveObservationValidationError("limits.max_files must be null or a non-negative integer")
    if not isinstance(limits["follow_symlinks"], bool):
        raise ArchiveObservationValidationError("limits.follow_symlinks must be boolean")


def _physical_ids(archive_id: str, relative_path: str) -> tuple[str, str, str]:
    digest = _sha256_text(_canonical_json({"archive_id": archive_id, "relative_path": relative_path}))
    return f"artifact:{digest}", f"physical:{digest}", f"archive-artifact:{digest}"


def _content_id(sha256: str | None) -> str | None:
    return f"content:sha256:{sha256}" if sha256 is not None else None


def _stable_symlink_target(raw_target: str, root: str) -> str:
    """Keep link evidence while preventing the scan root entering the digest."""

    if os.path.isabs(raw_target):
        target = os.path.normpath(raw_target)
        root_prefix = root.rstrip(os.sep) + os.sep
        if target == root:
            return "root-relative:."
        if target.startswith(root_prefix):
            relative = os.path.relpath(target, root)
            return f"root-relative:{PurePosixPath(*Path(relative).parts).as_posix()}"
        return f"absolute:{target}"
    return f"relative:{PurePosixPath(raw_target).as_posix()}"


def _error_code(error: BaseException) -> str:
    value = getattr(error, "errno", None)
    return errno.errorcode.get(value, "EIO")


def _media_details(relative_path: str) -> tuple[str, str, str]:
    suffix = Path(relative_path).suffix.lower()
    media_type = mimetypes.guess_type(relative_path, strict=False)[0] or "application/octet-stream"
    if media_type.startswith("image/"):
        family = "image"
    elif media_type.startswith("video/"):
        family = "video"
    elif media_type.startswith("audio/"):
        family = "audio"
    elif media_type.startswith("text/"):
        family = "text"
    elif media_type in {"application/pdf", "application/msword", "application/rtf"} or "document" in media_type:
        family = "document"
    elif media_type in {"application/zip", "application/gzip", "application/x-tar", "application/x-7z-compressed"}:
        family = "archive"
    elif media_type in {"application/json", "application/xml"} or suffix in {".yaml", ".yml"}:
        family = "data"
    elif suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sh", ".sql"}:
        family = "code"
    else:
        family = "unknown"
    return suffix, family, media_type


def _matches_path(path: str, pattern: str) -> bool:
    return (
        fnmatch.fnmatchcase(path, pattern)
        or fnmatch.fnmatchcase(PurePosixPath(path).name, pattern)
        or PurePosixPath(path).match(pattern)
    )


def _artifact_matches(artifact: Mapping[str, Any], *, include: list[str], exclude: list[str]) -> bool:
    path = artifact["relative_path"]
    if any(_matches_path(path, pattern) for pattern in exclude):
        return False
    if not include:
        return True
    return any(_matches_path(path, pattern) or pattern.rstrip("/").startswith(path.rstrip("/") + "/") for pattern in include)


def _new_artifact(archive_id: str, relative_path: str, kind: str, availability: str) -> dict[str, Any]:
    artifact_id, physical_id, artifact_ref = _physical_ids(archive_id, relative_path)
    extension, family, media_type = _media_details(relative_path)
    return {
        "archive_id": archive_id,
        "artifact_id": artifact_id,
        "physical_id": physical_id,
        "artifact_ref": artifact_ref,
        "references": [artifact_ref],
        "relative_path": relative_path,
        "kind": kind,
        "availability": availability,
        "size": None,
        "mtime_ns": None,
        "extension": extension,
        "family": family,
        "media_type": media_type,
        "sha256": None,
        "content_id": None,
        "symlink_target": None,
        "error_code": None,
        "error_operation": None,
    }


def _semantic_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    # mtime_ns is intentionally physical metadata, not semantic identity. A
    # copied archive can have a different filesystem clock while its relative
    # content remains identical.
    keys = (
        "archive_id",
        "artifact_id",
        "physical_id",
        "artifact_ref",
        "references",
        "relative_path",
        "kind",
        "availability",
        "size",
        "extension",
        "family",
        "media_type",
        "sha256",
        "content_id",
        "symlink_target",
        "error_code",
        "error_operation",
    )
    return {key: artifact[key] for key in keys}


def _observation(
    observation_type: str,
    artifact_refs: Iterable[str],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    refs = sorted(set(artifact_refs))
    material = {"observation_type": observation_type, "artifact_refs": refs, "evidence": evidence}
    observation_id = f"observation:{_sha256_text(_canonical_json(material))}"
    return {
        "observation_id": observation_id,
        "observation_type": observation_type,
        "status": "candidate",
        "artifact_refs": refs,
        "evidence": dict(evidence),
    }


def _observation_sort_key(observation: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(observation["observation_type"]),
        _canonical_json(observation["artifact_refs"]),
        _canonical_json(observation["evidence"]),
    )


def _semantic_snapshot_id(
    archive_id: str,
    limits: Mapping[str, Any],
    artifacts: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
) -> str:
    material = {
        "schema": SCHEMA,
        "archive_id": archive_id,
        "limits": limits,
        "artifacts": [_semantic_artifact(artifact) for artifact in artifacts],
        "observations": list(observations),
    }
    return f"snapshot:{_sha256_text(_canonical_json(material))}"


def _fingerprint(artifact: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        artifact["kind"],
        artifact["availability"],
        artifact["size"],
        artifact["mtime_ns"],
        artifact["extension"],
        artifact["family"],
        artifact["media_type"],
        artifact["sha256"],
        artifact["content_id"],
        artifact["symlink_target"],
        artifact["error_code"],
        artifact["error_operation"],
    )


def _change_set(current: Sequence[Mapping[str, Any]], prior: Mapping[str, Any] | None) -> dict[str, list[str]]:
    empty = {"added": [], "changed": [], "unchanged": [], "missing": []}
    if prior is None:
        return empty
    prior_by_path = {artifact["relative_path"]: artifact for artifact in prior["artifacts"]}
    current_by_path = {artifact["relative_path"]: artifact for artifact in current}
    result = {key: [] for key in empty}
    for path in sorted(current_by_path):
        if path not in prior_by_path:
            result["added"].append(path)
        elif _fingerprint(current_by_path[path]) == _fingerprint(prior_by_path[path]):
            result["unchanged"].append(path)
        else:
            result["changed"].append(path)
    result["missing"] = sorted(set(prior_by_path) - set(current_by_path))
    return result


def _validate_artifact(artifact: Any, archive_id: str) -> None:
    if not isinstance(artifact, dict) or set(artifact) != _ARTIFACT_KEYS:
        raise ArchiveObservationValidationError("artifact has an invalid field set")
    if artifact["archive_id"] != archive_id:
        raise ArchiveObservationValidationError("artifact archive_id does not match batch")
    relative_path = _normalise_relative_path(artifact["relative_path"])
    expected_artifact_id, expected_physical_id, expected_ref = _physical_ids(archive_id, relative_path)
    if artifact["artifact_id"] != expected_artifact_id or artifact["physical_id"] != expected_physical_id:
        raise ArchiveObservationValidationError("artifact physical identity is invalid")
    if artifact["artifact_ref"] != expected_ref or artifact["references"] != [expected_ref]:
        raise ArchiveObservationValidationError("artifact reference is invalid")
    if artifact["kind"] not in {"file", "directory", "symlink", "special", "error"}:
        raise ArchiveObservationValidationError("artifact kind is invalid")
    if artifact["availability"] not in {"available", "inaccessible", "unreadable", "unavailable", "error"}:
        raise ArchiveObservationValidationError("artifact availability is invalid")
    if artifact["size"] is not None and (isinstance(artifact["size"], bool) or not isinstance(artifact["size"], int) or artifact["size"] < 0):
        raise ArchiveObservationValidationError("artifact size is invalid")
    if artifact["mtime_ns"] is not None and (isinstance(artifact["mtime_ns"], bool) or not isinstance(artifact["mtime_ns"], int)):
        raise ArchiveObservationValidationError("artifact mtime_ns is invalid")
    for key in ("extension", "family", "media_type"):
        if not isinstance(artifact[key], str):
            raise ArchiveObservationValidationError(f"artifact {key} is invalid")
    sha256 = artifact["sha256"]
    if sha256 is not None and (not isinstance(sha256, str) or not _HEX64.fullmatch(sha256)):
        raise ArchiveObservationValidationError("artifact sha256 is invalid")
    expected_content_id = _content_id(sha256)
    if artifact["content_id"] != expected_content_id:
        raise ArchiveObservationValidationError("artifact content identity is invalid")
    if artifact["symlink_target"] is not None and not isinstance(artifact["symlink_target"], str):
        raise ArchiveObservationValidationError("artifact symlink_target is invalid")
    for key in ("error_code", "error_operation"):
        if artifact[key] is not None and not isinstance(artifact[key], str):
            raise ArchiveObservationValidationError(f"artifact {key} is invalid")


def validate_batch(batch: Any) -> bool:
    """Validate a batch strictly; raise instead of accepting malformed data."""

    if not isinstance(batch, dict) or set(batch) != _BATCH_KEYS:
        raise ArchiveObservationValidationError("batch has an invalid field set")
    if batch["schema"] != SCHEMA:
        raise ArchiveObservationValidationError("unsupported archive observation schema")
    archive_id = _validate_archive_id(batch["archive_id"])
    _validate_limits(batch["limits"])
    artifacts = batch["artifacts"]
    if not isinstance(artifacts, list):
        raise ArchiveObservationValidationError("artifacts must be a list")
    paths: set[str] = set()
    refs: set[str] = set()
    for artifact in artifacts:
        _validate_artifact(artifact, archive_id)
        path = artifact["relative_path"]
        if path in paths:
            raise ArchiveObservationValidationError("duplicate artifact relative_path")
        if artifact["artifact_ref"] in refs:
            raise ArchiveObservationValidationError("duplicate artifact reference")
        paths.add(path)
        refs.add(artifact["artifact_ref"])
    if artifacts != sorted(artifacts, key=lambda item: item["relative_path"]):
        raise ArchiveObservationValidationError("artifacts must be sorted by relative_path")
    observations = batch["observations"]
    if not isinstance(observations, list):
        raise ArchiveObservationValidationError("observations must be a list")
    observation_ids: set[str] = set()
    for observation in observations:
        if not isinstance(observation, dict) or set(observation) != _OBSERVATION_KEYS:
            raise ArchiveObservationValidationError("observation has an invalid field set")
        if not isinstance(observation["observation_id"], str) or not observation["observation_id"].startswith("observation:"):
            raise ArchiveObservationValidationError("observation_id is invalid")
        if observation["status"] != "candidate" or not isinstance(observation["observation_type"], str):
            raise ArchiveObservationValidationError("observation status or type is invalid")
        artifact_refs = observation["artifact_refs"]
        if not isinstance(artifact_refs, list) or artifact_refs != sorted(set(artifact_refs)):
            raise ArchiveObservationValidationError("observation artifact_refs must be sorted and unique")
        if any(ref not in refs for ref in artifact_refs):
            raise ArchiveObservationValidationError("observation references an unknown artifact")
        if not isinstance(observation["evidence"], dict):
            raise ArchiveObservationValidationError("observation evidence must be an object")
        expected_observation_id = f"observation:{_sha256_text(_canonical_json({'observation_type': observation['observation_type'], 'artifact_refs': artifact_refs, 'evidence': observation['evidence']}))}"
        if observation["observation_id"] != expected_observation_id:
            raise ArchiveObservationValidationError("observation_id does not match observation content")
        if observation["observation_id"] in observation_ids:
            raise ArchiveObservationValidationError("duplicate observation_id")
        observation_ids.add(observation["observation_id"])
    if observations != sorted(observations, key=_observation_sort_key):
        raise ArchiveObservationValidationError("observations must be deterministic and sorted")
    change_set = batch["change_set"]
    if not isinstance(change_set, dict) or set(change_set) != _CHANGE_KEYS:
        raise ArchiveObservationValidationError("change_set has an invalid field set")
    seen_change_paths: set[str] = set()
    for key in ("added", "changed", "unchanged", "missing"):
        values = change_set[key]
        if not isinstance(values, list) or values != sorted(set(values)):
            raise ArchiveObservationValidationError(f"change_set.{key} must be sorted and unique")
        for path in values:
            _normalise_relative_path(path)
            if path in seen_change_paths:
                raise ArchiveObservationValidationError("change_set contains duplicate paths")
            seen_change_paths.add(path)
    expected_snapshot = _semantic_snapshot_id(archive_id, batch["limits"], artifacts, observations)
    if batch["snapshot_id"] != expected_snapshot:
        raise ArchiveObservationValidationError("snapshot_id does not match semantic batch content")
    return True


def _json_object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArchiveObservationValidationError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def serialize_batch(batch: Mapping[str, Any], *, indent: int | None = None) -> str:
    """Serialize a validated batch with stable key ordering."""

    validate_batch(batch)
    return json.dumps(batch, ensure_ascii=False, sort_keys=True, indent=indent, separators=None if indent is not None else (",", ":"), allow_nan=False)


def deserialize_batch(payload: str | bytes | bytearray) -> dict[str, Any]:
    """Decode and validate a JSON batch, rejecting duplicate object keys."""

    if not isinstance(payload, (str, bytes, bytearray)):
        raise ArchiveObservationValidationError("JSON payload must be text or bytes")
    try:
        batch = json.loads(payload, object_pairs_hook=_json_object_no_duplicates)
    except ArchiveObservationValidationError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ArchiveObservationValidationError("invalid batch JSON") from error
    validate_batch(batch)
    return batch


def _load_prior(prior: Any, archive_id: str) -> dict[str, Any] | None:
    if prior is None:
        return None
    if isinstance(prior, Mapping):
        candidate = dict(prior)
    elif isinstance(prior, (str, bytes, bytearray)):
        if isinstance(prior, str) and os.path.exists(prior):
            try:
                candidate = deserialize_batch(Path(prior).read_bytes())
            except OSError as error:
                raise ArchiveObservationValidationError("cannot read prior batch") from error
        else:
            candidate = deserialize_batch(prior)
    elif isinstance(prior, os.PathLike):
        try:
            candidate = deserialize_batch(Path(prior).read_bytes())
        except OSError as error:
            raise ArchiveObservationValidationError("cannot read prior batch") from error
    else:
        raise ArchiveObservationValidationError("prior must be a batch mapping, JSON payload, or JSON path")
    validate_batch(candidate)
    if candidate["archive_id"] != archive_id:
        raise ArchiveObservationValidationError("prior archive_id does not match current archive_id")
    return candidate


def observe_archive(
    root: str | os.PathLike[str],
    archive_id: str,
    *,
    prior: Mapping[str, Any] | str | bytes | os.PathLike[str] | None = None,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    max_files: int | None = None,
    follow_symlinks: bool = False,
) -> dict[str, Any]:
    """Observe ``root`` without changing it and return a v1 batch.

    ``artifact_id``/``physical_id`` are scoped by ``archive_id`` and relative
    path. ``content_id`` is hash-based, so exact bytes may share content
    identity while remaining separate physical artifacts.
    """

    archive_id = _validate_archive_id(archive_id)
    if isinstance(root, (bytes, bytearray)) or not isinstance(root, (str, os.PathLike)):
        raise ArchiveObservationError("root must be an explicit filesystem path")
    if isinstance(max_files, bool) or (max_files is not None and (not isinstance(max_files, int) or max_files < 0)):
        raise ArchiveObservationError("max_files must be null or a non-negative integer")
    include_patterns = _normalise_patterns(include)
    exclude_patterns = _normalise_patterns(exclude)
    root_path = os.path.abspath(os.fspath(root))
    try:
        root_stat = os.lstat(root_path)
    except OSError as error:
        raise ArchiveObservationError("root cannot be read") from error
    if stat.S_ISLNK(root_stat.st_mode) and not follow_symlinks:
        raise ArchiveObservationError("root is a symlink and follow_symlinks is false")
    if stat.S_ISLNK(root_stat.st_mode) and follow_symlinks:
        try:
            root_stat = os.stat(root_path, follow_symlinks=True)
        except OSError as error:
            raise ArchiveObservationError("root symlink target cannot be read") from error
    if not stat.S_ISDIR(root_stat.st_mode):
        raise ArchiveObservationError("root must be a directory")

    limits = {
        "include": include_patterns,
        "exclude": exclude_patterns,
        "max_files": max_files,
        "follow_symlinks": bool(follow_symlinks),
    }
    prior_batch = _load_prior(prior, archive_id)
    artifacts_by_path: dict[str, dict[str, Any]] = {}
    skipped_paths: list[str] = []
    visited_directories: set[tuple[int, int]] = set()
    file_count = 0

    def add_entry(full_path: str, relative_path: str, entry_stat: os.stat_result | None, kind: str, availability: str) -> dict[str, Any] | None:
        if not _artifact_matches(
            {"relative_path": relative_path}, include=include_patterns, exclude=exclude_patterns
        ):
            return None
        artifact = _new_artifact(archive_id, relative_path, kind, availability)
        if entry_stat is not None:
            artifact["size"] = int(entry_stat.st_size)
            artifact["mtime_ns"] = int(getattr(entry_stat, "st_mtime_ns", int(entry_stat.st_mtime * 1_000_000_000)))
        artifacts_by_path[relative_path] = artifact
        return artifact

    def scan_file(full_path: str, relative_path: str, entry_stat: os.stat_result | None, kind: str) -> dict[str, Any] | None:
        nonlocal file_count
        if not _artifact_matches({"relative_path": relative_path}, include=include_patterns, exclude=exclude_patterns):
            return None
        if max_files is not None and file_count >= max_files:
            skipped_paths.append(relative_path)
            return None
        file_count += 1
        artifact = add_entry(full_path, relative_path, entry_stat, kind, "available")
        if artifact is None:
            return None
        if kind == "file":
            digest = hashlib.sha256()
            try:
                with open(full_path, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                artifact["sha256"] = digest.hexdigest()
                artifact["content_id"] = _content_id(artifact["sha256"])
            except OSError as error:
                artifact["availability"] = "unreadable"
                artifact["error_code"] = _error_code(error)
                artifact["error_operation"] = "hash"
        elif kind == "symlink":
            try:
                artifact["symlink_target"] = _stable_symlink_target(os.readlink(full_path), root_path)
            except OSError as error:
                artifact["availability"] = "unreadable"
                artifact["error_code"] = _error_code(error)
                artifact["error_operation"] = "readlink"
        return artifact

    def scan_directory(full_path: str, relative_directory: str, directory_artifact: dict[str, Any] | None) -> None:
        try:
            directory_stat = os.stat(full_path, follow_symlinks=follow_symlinks)
            key = (int(directory_stat.st_dev), int(directory_stat.st_ino))
        except OSError:
            key = (0, 0)
        if follow_symlinks and key in visited_directories:
            return
        if follow_symlinks:
            visited_directories.add(key)
        try:
            with os.scandir(full_path) as iterator:
                entries = sorted(iterator, key=lambda item: item.name)
                for entry in entries:
                    child_relative = _relative_path(root_path, entry.path)
                    if any(_matches_path(child_relative, pattern) for pattern in exclude_patterns):
                        continue
                    try:
                        entry_lstat = entry.stat(follow_symlinks=False)
                    except OSError as error:
                        artifact = add_entry(entry.path, child_relative, None, "error", "inaccessible")
                        if artifact is not None:
                            artifact["error_code"] = _error_code(error)
                            artifact["error_operation"] = "stat"
                        continue
                    mode = entry_lstat.st_mode
                    if stat.S_ISDIR(mode):
                        directory_child = add_entry(entry.path, child_relative, entry_lstat, "directory", "available")
                        # Filters apply to emitted entries, not traversal. This
                        # keeps include=*.ext useful for nested directories.
                        scan_directory(entry.path, child_relative, directory_child)
                        continue
                    if stat.S_ISREG(mode):
                        scan_file(entry.path, child_relative, entry_lstat, "file")
                        continue
                    if stat.S_ISLNK(mode):
                        symlink_artifact = scan_file(entry.path, child_relative, entry_lstat, "symlink")
                        if follow_symlinks and symlink_artifact is not None:
                            try:
                                target_stat = os.stat(entry.path, follow_symlinks=True)
                            except OSError:
                                target_stat = None
                            if target_stat is not None and stat.S_ISDIR(target_stat.st_mode):
                                scan_directory(entry.path, child_relative, None)
                        continue
                    scan_file(entry.path, child_relative, entry_lstat, "special")
        except OSError as error:
            if directory_artifact is None and not relative_directory:
                raise ArchiveObservationError("root directory cannot be scanned") from error
            if directory_artifact is not None:
                directory_artifact["availability"] = "inaccessible"
                directory_artifact["error_code"] = _error_code(error)
                directory_artifact["error_operation"] = "scan"

    scan_directory(root_path, "", None)
    artifacts = sorted(artifacts_by_path.values(), key=lambda artifact: artifact["relative_path"])

    observations: list[dict[str, Any]] = []
    ref_by_path = {artifact["relative_path"]: artifact["artifact_ref"] for artifact in artifacts}

    by_content: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        if artifact["kind"] == "file" and artifact["availability"] == "available" and artifact["content_id"]:
            by_content.setdefault(artifact["content_id"], []).append(artifact)
    for content_id, members in sorted(by_content.items()):
        if len(members) > 1:
            members = sorted(members, key=lambda artifact: artifact["relative_path"])
            observations.append(
                _observation(
                    "exact_duplicate_candidate",
                    (member["artifact_ref"] for member in members),
                    {
                        "content_id": content_id,
                        "sha256": members[0]["sha256"],
                        "count": len(members),
                    },
                )
            )

    sequences: dict[tuple[str, str, str], list[tuple[int, dict[str, Any]]]] = {}
    for artifact in artifacts:
        if artifact["kind"] not in {"file", "symlink"} or artifact["availability"] != "available":
            continue
        path = PurePosixPath(artifact["relative_path"])
        match = _SEQUENCE_RE.match(path.name)
        if not match:
            continue
        prefix = match.group("prefix")
        suffix = (match.group("suffix") or "").lower()
        key = (path.parent.as_posix() if path.parent.as_posix() != "." else "", prefix, suffix)
        sequences.setdefault(key, []).append((int(match.group("number")), artifact))
    for (directory, prefix, suffix), members in sorted(sequences.items()):
        numbers = sorted({number for number, _ in members})
        if len(numbers) < 2:
            continue
        member_by_number = {number: artifact for number, artifact in members}
        ordered_members = [member_by_number[number] for number in numbers]
        observations.append(
            _observation(
                "numbered_sequence_candidate",
                (member["artifact_ref"] for member in ordered_members),
                {
                    "directory": directory,
                    "prefix": prefix,
                    "extension": suffix,
                    "numbers": numbers,
                    "contiguous": numbers == list(range(numbers[0], numbers[-1] + 1)),
                },
            )
        )

    artifacts_by_name = {PurePosixPath(artifact["relative_path"]): artifact for artifact in artifacts}
    for artifact in artifacts:
        if artifact["kind"] != "file" or artifact["availability"] != "available":
            continue
        path = PurePosixPath(artifact["relative_path"])
        lower_name = path.name.lower()
        is_manifest = any(word in lower_name for word in _MANIFEST_WORDS) or path.suffix.lower() == ".manifest"
        if is_manifest:
            observations.append(
                _observation(
                    "manifest_candidate",
                    [artifact["artifact_ref"]],
                    {"relative_path": artifact["relative_path"], "extension": path.suffix.lower()},
                )
            )
        if path.suffix.lower() not in _SIDECAR_EXTENSIONS:
            continue
        base = path.name[: -len(path.suffix)] if path.suffix else path.name
        direct_target = artifacts_by_name.get(path.parent / base)
        siblings = [
            candidate
            for candidate_path, candidate in artifacts_by_name.items()
            if candidate_path.parent == path.parent
            and candidate_path != path
            and candidate["kind"] == "file"
            and candidate["availability"] == "available"
            and (candidate is direct_target or candidate_path.stem == base)
        ]
        if siblings:
            siblings.sort(key=lambda candidate: candidate["relative_path"])
            observations.append(
                _observation(
                    "sidecar_candidate",
                    [artifact["artifact_ref"], *(candidate["artifact_ref"] for candidate in siblings)],
                    {
                        "sidecar": artifact["relative_path"],
                        "targets": [candidate["relative_path"] for candidate in siblings],
                    },
                )
            )

    for artifact in artifacts:
        if artifact["availability"] != "available":
            observations.append(
                _observation(
                    "failure_candidate",
                    [artifact["artifact_ref"]],
                    {
                        "relative_path": artifact["relative_path"],
                        "availability": artifact["availability"],
                        "error_code": artifact["error_code"],
                        "error_operation": artifact["error_operation"],
                    },
                )
            )
    for path in sorted(skipped_paths):
        observations.append(
            _observation(
                "limit_reached",
                [],
                {"relative_path": path, "limit": "max_files"},
            )
        )
    observations.sort(key=_observation_sort_key)
    batch = {
        "schema": SCHEMA,
        "archive_id": archive_id,
        "snapshot_id": _semantic_snapshot_id(archive_id, limits, artifacts, observations),
        "limits": limits,
        "artifacts": artifacts,
        "observations": observations,
        "change_set": _change_set(artifacts, prior_batch),
    }
    validate_batch(batch)
    return batch


scan_archive = observe_archive


__all__ = [
    "SCHEMA",
    "ArchiveObservationError",
    "ArchiveObservationValidationError",
    "deserialize_batch",
    "observe_archive",
    "scan_archive",
    "serialize_batch",
    "validate_batch",
]
