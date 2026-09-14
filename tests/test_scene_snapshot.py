from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools.blender_scene_probe import SNAPSHOT_EXPRESSION, SNAPSHOT_MARKER, snapshot_file
from flujo.substrate.scene_snapshot import (
    SceneSnapshotError,
    assess_render_preconditions,
    build_scene_snapshot,
    finish_transformation,
    start_transformation,
    validate_scene_snapshot,
)


def _payload(*, dependency: dict | None = None, resolution: tuple[int, int] = (1920, 1080)) -> dict:
    dependencies = [] if dependency is None else [dependency]
    return {
        "filepath": "/work/scene.blend",
        "blender_version": "4.3.2",
        "dirty": False,
        "scenes": [
            {
                "name": "Main",
                "frame_current": 1,
                "frame_start": 1,
                "frame_end": 24,
                "render": {
                    "engine": "BLENDER_EEVEE_NEXT",
                    "resolution_x": resolution[0],
                    "resolution_y": resolution[1],
                    "resolution_percentage": 100,
                    "pixel_aspect_x": 1.0,
                    "pixel_aspect_y": 1.0,
                    "filepath": "/work/renders/",
                    "file_format": "PNG",
                    "color_mode": "RGBA",
                    "film_transparent": False,
                    "use_file_extension": True,
                },
                "camera": {"present": True, "name": "Camera", "type": "CAMERA"},
                "objects": [
                    {
                        "id": "object:hero",
                        "name": "Hero",
                        "type": "MESH",
                        "collections": ["Artwork"],
                        "location": [0.0, 0.0, 0.0],
                        "rotation": [0.0, 0.0, 0.0],
                        "scale": [1.0, 1.0, 1.0],
                        "visible": True,
                        "data": {"name": "HeroMesh", "type": "Mesh", "vertices_count": 8},
                        "materials": ["Blue"],
                        "modifiers": [],
                    }
                ],
                "collections": ["Artwork"],
                "view_layers": ["ViewLayer"],
                "compositor": {"use_nodes": False, "nodes": []},
            }
        ],
        "dependencies": dependencies,
    }


def _snapshot(tmp_path: Path, payload: dict | None = None, **kwargs) -> dict:
    source = tmp_path / "scene.blend"
    source.write_bytes(b"blend-fixture-v1")
    return build_scene_snapshot(
        source,
        payload or _payload(),
        root_id=kwargs.pop("root_id", "mak-test"),
        relative_path=kwargs.pop("relative_path", "scene.blend"),
        observed_at=kwargs.pop("observed_at", "2026-08-24T12:00:00+00:00"),
        **kwargs,
    )


def test_identical_native_snapshots_share_state_digest_but_observations_are_plural(tmp_path: Path):
    first = _snapshot(tmp_path, observed_at="2026-08-24T12:00:00+00:00")
    second = _snapshot(
        tmp_path,
        root_id="another-root",
        relative_path="nested/scene.blend",
        observed_at="2026-08-24T13:00:00+00:00",
    )

    assert first["snapshot_digest"] == second["snapshot_digest"]
    assert first["snapshot_id"] == second["snapshot_id"]
    assert first["observation"]["observation_id"] != second["observation"]["observation_id"]
    assert first["observation"]["relative_path"] != second["observation"]["relative_path"]


def test_changed_bytes_or_native_state_changes_snapshot_identity(tmp_path: Path):
    first = _snapshot(tmp_path)
    changed_native = _snapshot(tmp_path, _payload(resolution=(1080, 1080)))
    assert first["snapshot_digest"] != changed_native["snapshot_digest"]
    assert first["artifact_state"]["state_id"] != changed_native["artifact_state"]["state_id"]

    source = tmp_path / "scene.blend"
    source.write_bytes(b"blend-fixture-v2")
    changed_bytes = build_scene_snapshot(source, _payload(), observed_at="2026-08-24T14:00:00+00:00")
    assert first["snapshot_digest"] != changed_bytes["snapshot_digest"]
    assert first["artifact_state"]["content_id"] != changed_bytes["artifact_state"]["content_id"]


def test_snapshot_validation_is_integrity_only_and_detects_tampering(tmp_path: Path):
    snapshot = _snapshot(tmp_path)
    result = validate_scene_snapshot(snapshot)
    assert result["status"] == "PASS"
    assert result["scope"] == "snapshot_integrity_not_visual_quality"

    snapshot["native"]["scenes"][0]["render"]["engine"] = "CYCLES"
    tampered = validate_scene_snapshot(snapshot)
    assert tampered["status"] == "FAIL"


def test_render_preconditions_fail_missing_dependency_and_preserve_unknown(tmp_path: Path):
    missing = _snapshot(
        tmp_path,
        _payload(dependency={"kind": "image", "path": "textures/missing.png", "exists": False}),
    )
    result = assess_render_preconditions(missing, resolution=(1920, 1080))
    assert result["status"] == "FAIL"
    assert any(check["name"] == "dependencies_available" and check["status"] == "FAIL"
               for check in result["checks"])

    unknown = _snapshot(tmp_path, _payload(dependency={"kind": "image", "path": "texture.png"}))
    result = assess_render_preconditions(unknown)
    assert result["status"] == "UNKNOWN"
    assert any(check["name"] == "dependencies_available" and check["status"] == "UNKNOWN"
               for check in result["checks"])


def test_transformation_event_preserves_input_and_requires_new_output(tmp_path: Path):
    snapshot = _snapshot(tmp_path)
    event = start_transformation(
        snapshot,
        "renderizar",
        {"scene": "Main", "frame": 1},
        session_id="session-1",
        started_at="2026-08-24T15:00:00+00:00",
    )
    closed = finish_transformation(
        event,
        ["scene-state:render-output"],
        {"status": "PASS", "validation_id": "validation:render-1"},
        finished_at="2026-08-24T15:01:00+00:00",
    )

    assert event["status"] == "STARTED"
    assert event["output_versions"] == []
    assert closed["status"] == "COMPLETED"
    assert closed["input_versions"] == [snapshot["snapshot_id"]]
    assert closed["validation_id"] == "validation:render-1"

    with pytest.raises(SceneSnapshotError, match="reused_input"):
        finish_transformation(event, [snapshot["snapshot_id"]], {"status": "PASS"})


def test_unknown_validation_does_not_become_success(tmp_path: Path):
    snapshot = _snapshot(tmp_path)
    event = start_transformation(snapshot, "renderizar", {})
    closed = finish_transformation(event, [], {"status": "UNKNOWN"})
    assert closed["status"] == "UNKNOWN"


def test_native_probe_adapter_is_read_only_and_builds_existing_substrate_snapshot(
    tmp_path: Path, monkeypatch
):
    blend = tmp_path / "scene.blend"
    blend.write_bytes(b"blend-fixture-v1")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0, SNAPSHOT_MARKER + json.dumps(_payload()) + "\n", ""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    row = snapshot_file(blend, blender=tmp_path / "blender", timeout=5)

    assert row["status"] == "ok"
    assert row["snapshot"]["contract"] == "mak-blender-scene-snapshot-v1"
    assert "--background" in calls[0]
    assert "--disable-autoexec" in calls[0]
    assert "bpy.ops.render" not in SNAPSHOT_EXPRESSION
    assert "bpy.ops.wm.save" not in SNAPSHOT_EXPRESSION
