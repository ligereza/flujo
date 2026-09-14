"""Reproducible native snapshots and transformation events for creative scenes.

This module is deliberately smaller than a project model.  It anchors one
native scene observation to the existing identity substrate and records a
render transition without pretending that a product is the source of truth.

The snapshot digest excludes observation-only fields such as filesystem path
and capture time.  Consequently, observing the same bytes and native payload
twice yields the same scene state, while each observation remains separately
dated in the existing ``Observation`` entity.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .schema import ArtifactState, Content, Observation


CONTRACT = "mak-blender-scene-snapshot-v1"
TRANSFORMATION_CONTRACT = "mak-transformation-event-v1"
RENDER_OPERATION = "renderizar"
VALIDATION_STATUSES = {"PASS", "FAIL", "UNKNOWN"}


class SceneSnapshotError(ValueError):
    """The native snapshot cannot support a reproducible claim."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SceneSnapshotError(f"snapshot_{field}_not_object")
    return copy.deepcopy(dict(value))


def _normalise_object(value: Any) -> dict[str, Any]:
    row = _mapping(value, "object")
    object_id = str(row.get("id") or row.get("name") or "")
    if not object_id:
        raise SceneSnapshotError("snapshot_object_missing_id")
    row["id"] = object_id
    for key in ("collections", "materials", "modifiers"):
        values = row.get(key)
        if isinstance(values, list):
            row[key] = sorted(values, key=lambda item: _json(item))
    return row


def _normalise_scene(value: Any) -> dict[str, Any]:
    scene = _mapping(value, "scene")
    name = str(scene.get("name") or "")
    if not name:
        raise SceneSnapshotError("snapshot_scene_missing_name")
    scene["name"] = name
    scene["render"] = _mapping(scene.get("render") or {}, "render")
    camera = scene.get("camera")
    scene["camera"] = copy.deepcopy(camera) if isinstance(camera, Mapping) else camera
    objects = scene.get("objects")
    if objects is None:
        objects = []
    if not isinstance(objects, list):
        raise SceneSnapshotError("snapshot_objects_not_list")
    normalised = [_normalise_object(item) for item in objects]
    ids = [item["id"] for item in normalised]
    if len(ids) != len(set(ids)):
        raise SceneSnapshotError("snapshot_duplicate_object_ids")
    scene["objects"] = sorted(normalised, key=lambda item: item["id"])
    for key in ("collections", "view_layers"):
        values = scene.get(key)
        if isinstance(values, list):
            scene[key] = sorted(values, key=lambda item: _json(item))
    return scene


def _native_payload(payload: Mapping[str, Any], content_id: str,
                    extractor_config: Mapping[str, Any]) -> dict[str, Any]:
    """Return only state-bearing fields used by the snapshot digest."""
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SceneSnapshotError("snapshot_scenes_missing")
    dependencies = payload.get("dependencies") or []
    if not isinstance(dependencies, list):
        raise SceneSnapshotError("snapshot_dependencies_not_list")
    deps = [copy.deepcopy(dict(item)) for item in dependencies
            if isinstance(item, Mapping)]
    deps.sort(key=lambda item: _json(item))
    return {
        "content_id": content_id,
        "blender_version": str(payload.get("blender_version") or "UNKNOWN"),
        "dirty": bool(payload.get("dirty", False)),
        "scenes": sorted((_normalise_scene(item) for item in scenes),
                         key=lambda item: item["name"]),
        "dependencies": deps,
        "extractor_config": copy.deepcopy(dict(extractor_config)),
    }


def build_scene_snapshot(
    path: str | Path,
    payload: Mapping[str, Any],
    *,
    root_id: str = "filesystem",
    relative_path: str | None = None,
    observed_at: str | None = None,
    extractor: str = "tools.blender_scene_probe.snapshot_file",
    extractor_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a native snapshot without changing the source ``.blend``.

    ``payload`` is expected to come from Blender's read-only Python probe.  The
    source path is an observation locator; it is intentionally not part of the
    semantic snapshot digest.
    """
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise SceneSnapshotError(f"snapshot_source_not_file:{source}")
    config = dict(extractor_config or {
        "factory_startup": True,
        "disable_autoexec": True,
        "renders": False,
        "saves": False,
    })
    content = Content.of_file(source)
    native = _native_payload(payload, content.content_id, config)
    snapshot_digest = _digest(native)
    state_id = f"scene-state:{snapshot_digest}"
    observation_time = observed_at or _now()
    rel = relative_path or source.name
    observation_id = "observation:" + _digest({
        "state_id": state_id,
        "root_id": root_id,
        "relative_path": rel,
        "observed_at": observation_time,
    })[:32]
    state = ArtifactState(
        state_id=state_id,
        content_id=content.content_id,
        creator_tool=f"Blender {native['blender_version']}",
        id_source="snapshot_digest",
    )
    observation = Observation(
        observation_id=observation_id,
        state_id=state_id,
        root_id=root_id,
        relative_path=rel,
        observed_at=observation_time,
        basename=source.name,
        extension=source.suffix.lower(),
        fs_size=content.size,
        fs_mtime=str(source.stat().st_mtime_ns),
    )
    return {
        "contract": CONTRACT,
        "snapshot_id": state_id,
        "snapshot_digest": snapshot_digest,
        "artifact_state": {
            "state_id": state.state_id,
            "content_id": state.content_id,
            "creator_tool": state.creator_tool,
            "id_source": state.id_source,
        },
        "observation": {
            "observation_id": observation.observation_id,
            "state_id": observation.state_id,
            "root_id": observation.root_id,
            "relative_path": observation.relative_path,
            "observed_at": observation.observed_at,
            "basename": observation.basename,
            "extension": observation.extension,
            "fs_size": observation.fs_size,
            "fs_mtime": observation.fs_mtime,
        },
        "native": native,
        "provenance": {
            "authority": "blender_python_snapshot",
            "extractor": extractor,
            "method": "background_factory_startup_disable_autoexec_read_only",
            "source_path": str(source),
            "search_completeness": "declared_native_fields_only",
            "negative_is_evidence": False,
        },
    }


def validate_scene_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate snapshot integrity, without certifying artistic intent."""
    checks: list[dict[str, Any]] = []
    if snapshot.get("contract") != CONTRACT:
        checks.append({"name": "contract", "status": "FAIL"})
        return {"status": "FAIL", "checks": checks}
    native = snapshot.get("native")
    if not isinstance(native, Mapping):
        return {"status": "FAIL", "checks": [{"name": "native", "status": "FAIL"}]}
    state = snapshot.get("artifact_state")
    if not isinstance(state, Mapping) or not state.get("content_id"):
        checks.append({"name": "artifact_state", "status": "FAIL"})
    else:
        config = native.get("extractor_config")
        config = config if isinstance(config, Mapping) else {}
        expected = _digest(native)
        checks.append({
            "name": "snapshot_digest",
            "status": "PASS" if expected == snapshot.get("snapshot_digest") else "FAIL",
        })
    scenes = native.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        checks.append({"name": "scenes", "status": "FAIL"})
    else:
        checks.append({"name": "scenes", "status": "PASS"})
    statuses = {item["status"] for item in checks}
    status = "FAIL" if "FAIL" in statuses else "PASS"
    return {"status": status, "checks": checks,
            "scope": "snapshot_integrity_not_visual_quality"}


def assess_render_preconditions(
    snapshot: Mapping[str, Any], *, frame: int | None = None,
    resolution: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Return PASS/FAIL/UNKNOWN for render applicability."""
    native = snapshot.get("native")
    if not isinstance(native, Mapping):
        return {"status": "FAIL", "checks": [{"name": "native", "status": "FAIL"}]}
    scenes = native.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return {"status": "FAIL", "checks": [{"name": "scene_exists", "status": "FAIL"}]}
    scene = scenes[0]
    checks: list[dict[str, Any]] = [{"name": "scene_exists", "status": "PASS"}]
    camera = scene.get("camera")
    checks.append({"name": "camera_valid",
                   "status": "PASS" if isinstance(camera, Mapping)
                   and camera.get("present", True) else "FAIL"})
    render = scene.get("render")
    if not isinstance(render, Mapping):
        checks.append({"name": "render_settings", "status": "UNKNOWN"})
    else:
        checks.append({"name": "render_settings", "status": "PASS"})
        if resolution is not None:
            actual = (render.get("resolution_x"), render.get("resolution_y"))
            checks.append({"name": "resolution_matches",
                           "status": "PASS" if actual == resolution else "FAIL",
                           "expected": list(resolution), "actual": list(actual)})
        if frame is not None and scene.get("frame_current") is None:
            checks.append({"name": "frame_known", "status": "UNKNOWN"})
    dependencies = native.get("dependencies")
    if not isinstance(dependencies, list):
        checks.append({"name": "dependencies_available", "status": "UNKNOWN"})
    else:
        missing = [item for item in dependencies
                   if isinstance(item, Mapping)
                   and item.get("packed") is not True
                   and item.get("exists") is False]
        unknown = [item for item in dependencies
                   if isinstance(item, Mapping)
                   and item.get("packed") is not True
                   and "exists" not in item]
        checks.append({"name": "dependencies_available",
                       "status": "FAIL" if missing else ("UNKNOWN" if unknown else "PASS"),
                       "missing": missing, "unknown": unknown})
    statuses = {item["status"] for item in checks}
    status = "FAIL" if "FAIL" in statuses else ("UNKNOWN" if "UNKNOWN" in statuses else "PASS")
    return {"status": status, "checks": checks,
            "scope": "technical_render_preconditions_only"}


def start_transformation(
    input_snapshot: Mapping[str, Any], operation: str,
    parameters: Mapping[str, Any], *, session_id: str = "",
    actor: str = "mak", started_at: str | None = None,
    correction_of: str | None = None,
) -> dict[str, Any]:
    """Create an immutable STARTED event; no operation is executed here."""
    input_id = str(input_snapshot.get("snapshot_id") or "")
    if not input_id:
        raise SceneSnapshotError("transformation_missing_input_snapshot")
    started = started_at or _now()
    identity = {"input": input_id, "operation": operation,
                "parameters": dict(parameters), "started_at": started}
    return {
        "contract": TRANSFORMATION_CONTRACT,
        "event_id": "transformation:" + _digest(identity)[:32],
        "session_id": session_id,
        "input_versions": [input_id],
        "operation": operation,
        "parameters": copy.deepcopy(dict(parameters)),
        "actor": actor,
        "started_at": started,
        "finished_at": None,
        "output_versions": [],
        "validation_id": None,
        "correction_of": correction_of,
        "status": "STARTED",
    }


def finish_transformation(
    event: Mapping[str, Any], output_versions: list[str],
    validation: Mapping[str, Any], *, finished_at: str | None = None,
) -> dict[str, Any]:
    """Close an event without mutating the STARTED event or its input."""
    if event.get("contract") != TRANSFORMATION_CONTRACT:
        raise SceneSnapshotError("transformation_contract_invalid")
    status = str(validation.get("status") or "UNKNOWN").upper()
    if status not in VALIDATION_STATUSES:
        raise SceneSnapshotError(f"validation_status_invalid:{status}")
    inputs = set(str(item) for item in event.get("input_versions") or [])
    outputs = [str(item) for item in output_versions]
    if any(item in inputs for item in outputs):
        raise SceneSnapshotError("transformation_reused_input_as_output")
    closed = copy.deepcopy(dict(event))
    closed.update({
        "finished_at": finished_at or _now(),
        "output_versions": outputs,
        "validation_id": str(validation.get("validation_id") or "validation:" + _digest(validation)[:32]),
        "status": {"PASS": "COMPLETED", "FAIL": "FAILED", "UNKNOWN": "UNKNOWN"}[status],
    })
    return closed
