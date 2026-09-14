"""Acceptance tests for the read-only Stage 2A archive projection."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
from flujo.knowledge.archive_observer import observe_archive, validate_batch
from flujo.knowledge.archive_reconstruction import (
    ArchiveReconstructionError,
    project_archive_snapshot,
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "artist-archive"
    native = root / "projects" / "native" / "source"
    output = root / "projects" / "native" / "exports"
    sequence = output / "frames"
    native.mkdir(parents=True)
    sequence.mkdir(parents=True)
    (native / "scene.blend").write_bytes(b"native-scene")
    (output / "render.mp4").write_bytes(b"rendered-video")
    (sequence / "frame_001.png").write_bytes(b"frame-1")
    (sequence / "frame_002.png").write_bytes(b"frame-2")
    (sequence / "frame_001.png.xmp").write_bytes(b"sidecar")
    (output / "manifest.json").write_text("{}", encoding="utf-8")
    (output / "duplicate-a.dat").write_bytes(b"same-content")
    (output / "duplicate-b.dat").write_bytes(b"same-content")
    (root / "link-to-render.mp4").symlink_to(output / "render.mp4")
    return root


def test_real_observe_ingest_replay_projects_everything_once(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    database = tmp_path / "learning.sqlite"
    batch = observe_archive(root, "artist-a")
    ingest_observation_batch(database, batch)
    replay = replay_snapshot(database, archive_id="artist-a", snapshot_id=batch["snapshot_id"])

    assert validate_batch(replay["snapshot"]) is True
    projection = project_archive_snapshot(replay["snapshot"])
    assert projection["schema"] == "mak-archive-reconstruction-input-v1"
    assert projection["archive_id"] == "artist-a"
    assert projection["snapshot_id"] == batch["snapshot_id"]
    assert projection["reconciliation"] == {
        "artifacts_observed": len(batch["artifacts"]),
        "artifacts_projected": len(batch["artifacts"]),
        "artifact_identity_count": len(batch["artifacts"]),
        "artifact_identity_duplicates": 0,
        "artifact_loss": 0,
        "observations_observed": len(batch["observations"]),
        "observations_projected": len(batch["observations"]),
        "observation_identity_count": len(batch["observations"]),
        "observation_identity_duplicates": 0,
        "observation_loss": 0,
        "status": "consistent",
    }
    assert len(projection["artifacts"]) == len(batch["artifacts"])
    assert len(projection["candidate_observations"]) == len(batch["observations"])
    assert all(item["status"] == "candidate" for item in projection["candidate_observations"])
    assert all(item["record_type"] == "candidate_observation" for item in projection["candidate_observations"])
    assert str(root) not in _json(projection)
    assert "mtime_ns" not in _json(projection)
    assert "change_set" not in _json(projection)


def test_nested_features_and_indexes_are_observations_not_truth(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    database = tmp_path / "learning.sqlite"
    batch = observe_archive(root, "artist-a")
    ingest_observation_batch(database, batch)
    projection = project_archive_snapshot(
        replay_snapshot(database, archive_id="artist-a", snapshot_id=batch["snapshot_id"])["snapshot"]
    )

    by_path = {item["relative_path"]: item for item in projection["artifacts"]}
    native = by_path["projects/native/source/scene.blend"]
    output = by_path["projects/native/exports/render.mp4"]
    frame = by_path["projects/native/exports/frames/frame_001.png"]
    sidecar = by_path["projects/native/exports/frames/frame_001.png.xmp"]
    manifest = by_path["projects/native/exports/manifest.json"]
    link = by_path["link-to-render.mp4"]
    directory = by_path["projects/native"]

    assert native["derived_flags"]["native_authoring_anchor"] is True
    assert native["artifact_ref"] in projection["native_anchor_refs"]
    assert output["derived_flags"]["probable_output_media"] is True
    assert output["artifact_ref"] in projection["probable_output_refs"]
    assert frame["derived_flags"]["numbered_name_token"] == "001"
    assert sidecar["derived_flags"]["sidecar_or_manifest"] is True
    assert manifest["derived_flags"]["sidecar_or_manifest"] is True
    assert link["kind"] == "symlink"
    assert link["content_id"] is None
    assert link["sha256"] is None
    assert directory["kind"] == "directory"
    assert directory["content_id"] is None
    assert len(projection["artifacts_by_content"]) >= 1
    duplicate_refs = [
        item["artifact_ref"]
        for item in projection["artifacts"]
        if item["relative_path"].endswith(("duplicate-a.dat", "duplicate-b.dat"))
    ]
    duplicate_group = next(
        refs for refs in projection["artifacts_by_content"].values()
        if set(refs) == set(duplicate_refs)
    )
    assert sorted(duplicate_group) == sorted(duplicate_refs)
    assert all(
        by_path[path]["derived_flags"]["duplicate_content_member"]
        for path in ("projects/native/exports/duplicate-a.dat", "projects/native/exports/duplicate-b.dat")
    )
    assert projection["artifacts_by_parent"]["projects/native/exports"]
    assert projection["candidate_observation_ids"] == sorted(projection["candidate_observation_ids"])


def test_touch_projection_is_byte_identical_and_json_is_deterministic(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    database = tmp_path / "learning.sqlite"
    first_batch = observe_archive(root, "artist-a")
    ingest_observation_batch(database, first_batch)
    first_projection = project_archive_snapshot(first_batch)
    first_json = _json(first_projection)
    touch_path = root / "projects" / "native" / "source" / "scene.blend"
    touched_mtime = os.stat(touch_path).st_mtime_ns + 1000
    os.utime(touch_path, ns=(touched_mtime, touched_mtime))
    touched_batch = observe_archive(root, "artist-a", prior=first_batch)
    ingest_observation_batch(database, touched_batch)

    touched_projection = project_archive_snapshot(touched_batch)
    replay_projection = project_archive_snapshot(
        replay_snapshot(database, archive_id="artist-a", snapshot_id=first_batch["snapshot_id"])["snapshot"]
    )
    assert touched_batch["snapshot_id"] == first_batch["snapshot_id"]
    assert _json(touched_projection) == first_json
    assert _json(replay_projection) == first_json
    assert _json(json.loads(first_json)) == first_json


def test_two_archive_ids_are_isolated_in_projection(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    database = tmp_path / "learning.sqlite"
    first_batch = observe_archive(root, "artist-a")
    second_batch = observe_archive(root, "artist/edition\\two")
    ingest_observation_batch(database, first_batch)
    ingest_observation_batch(database, second_batch)

    first = project_archive_snapshot(first_batch)
    second = project_archive_snapshot(second_batch)
    first_refs = {item["artifact_ref"] for item in first["artifacts"]}
    second_refs = {item["artifact_ref"] for item in second["artifacts"]}
    assert first["archive_id"] != second["archive_id"]
    assert first_refs.isdisjoint(second_refs)
    assert first["input_hash"] != second["input_hash"]


def test_malformed_batch_fails_closed_before_projection(tmp_path: Path) -> None:
    batch = observe_archive(_fixture_root(tmp_path), "artist-a")
    malformed = copy.deepcopy(batch)
    malformed["artifacts"][0]["artifact_id"] = "artifact:not-derived-from-path"

    with pytest.raises(ArchiveReconstructionError, match="batch_invalid:.*physical identity"):
        project_archive_snapshot(malformed)
