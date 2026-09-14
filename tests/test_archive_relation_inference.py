from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from src.flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
from src.flujo.knowledge.archive_observer import observe_archive, validate_batch
from src.flujo.knowledge.archive_reconstruction import project_archive_snapshot
from src.flujo.knowledge.archive_relation_inference import (
    ArchiveRelationInferenceError,
    candidate_id_for,
    infer_archive_relations,
    validate_relation_payload,
)


def _write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _archive_root(root: Path) -> Path:
    _write(root / "projects/native/source/scene.blend", b"blend-source")
    _write(root / "projects/native/exports/render.mp4", b"render-output")
    _write(root / "projects/native/exports/frame_001.png", b"frame-one")
    _write(root / "projects/native/exports/frame_002.png", b"frame-two")
    _write(root / "projects/native/exports/frame_001.png.xmp", b"sidecar")
    _write(root / "projects/native/exports/manifest.json", b'{"frames":["frame_001.png"]}')
    _write(root / "duplicates/duplicate-a.bin", b"same-bytes")
    _write(root / "duplicates/duplicate-b.bin", b"same-bytes")
    (root / "projects/native/exports/link-to-render.mp4").symlink_to("render.mp4")
    os.mkfifo(root / "special.pipe")
    return root


def _pipeline(root: Path, tmp_path: Path, archive_id: str = "artist") -> tuple[dict, dict, dict, dict]:
    batch = observe_archive(root, archive_id)
    assert validate_batch(batch) is True
    database = tmp_path / f"{archive_id.replace('/', '_').replace(chr(92), '_')}.sqlite"
    ingest = ingest_observation_batch(database, batch)
    replay = replay_snapshot(
        database,
        archive_id=archive_id,
        snapshot_id=batch["snapshot_id"],
    )
    projection = project_archive_snapshot(replay["snapshot"])
    relations = infer_archive_relations(projection)
    assert validate_relation_payload(projection, relations) is True
    return batch, ingest, projection, relations


def _artifact(projection: dict, relative_path: str) -> dict:
    return next(item for item in projection["artifacts"] if item["relative_path"] == relative_path)


def _candidates(relations: dict, relation: str) -> list[dict]:
    return [item for item in relations["candidates"] if item["relation"] == relation]


def test_actual_pipeline_emits_bounded_physical_relations(tmp_path: Path) -> None:
    root = _archive_root(tmp_path / "archive")
    _batch, _ingest, projection, relations = _pipeline(root, tmp_path)
    refs = {item["artifact_ref"] for item in projection["artifacts"]}

    native = _artifact(projection, "projects/native/source/scene.blend")
    output = _artifact(projection, "projects/native/exports/render.mp4")
    native_parent = _artifact(projection, "projects/native/source")
    assert any(
        item["source_ref"] == native_parent["artifact_ref"]
        and item["relation"] == "contains"
        and item["target_ref"] == native["artifact_ref"]
        for item in relations["candidates"]
    )
    local = [
        item for item in _candidates(relations, "manifestation_of")
        if item["source_ref"] == output["artifact_ref"]
        and item["target_ref"] == native["artifact_ref"]
    ]
    assert local and local[0]["status"] == "unresolved_candidate"
    assert "export_witness" in local[0]["missing_evidence"]
    assert all(
        item["source_ref"] in refs and item["target_ref"] in refs
        for item in relations["candidates"]
    )
    assert relations["reconciliation"]["truth_promotions"] == 0


def test_candidate_ids_use_full_semantics_and_final_order_is_by_id(tmp_path: Path) -> None:
    _batch, _ingest, projection, relations = _pipeline(_archive_root(tmp_path / "archive"), tmp_path)
    candidates = relations["candidates"]
    assert candidates == sorted(candidates, key=lambda item: item["candidate_id"])
    candidate = candidates[0]
    semantic = {
        "archive_id": projection["archive_id"],
        **{
            key: candidate[key]
            for key in (
                "source_ref", "relation", "target_ref", "inverse_relation", "status",
                "score", "reason_codes", "evidence_refs", "evidence_for",
                "evidence_against", "alternatives", "missing_evidence", "next_probe",
            )
        },
    }
    expected = "candidate:" + hashlib.sha256(
        json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    assert candidate["candidate_id"] == expected
    assert candidate_id_for(candidate, projection["archive_id"]) == expected
    changed = copy.deepcopy(candidate)
    changed["alternatives"] = list(changed["alternatives"]) + ["another_alternative"]
    assert candidate_id_for(changed, projection["archive_id"]) != expected


def test_next_probe_null_is_only_allowed_for_pending_without_missing_evidence(tmp_path: Path) -> None:
    _batch, _ingest, projection, relations = _pipeline(_archive_root(tmp_path / "archive"), tmp_path)
    direct = next(item for item in relations["candidates"] if item["relation"] == "contains")
    nullable = copy.deepcopy(relations)
    nullable_direct = next(item for item in nullable["candidates"] if item["candidate_id"] == direct["candidate_id"])
    nullable_direct["next_probe"] = None
    nullable_direct["candidate_id"] = candidate_id_for(nullable_direct, projection["archive_id"])
    nullable["candidates"].sort(key=lambda item: item["candidate_id"])
    assert validate_relation_payload(projection, nullable) is True

    invalid = copy.deepcopy(relations)
    unresolved = next(item for item in invalid["candidates"] if item["status"] == "unresolved_candidate")
    unresolved["next_probe"] = None
    unresolved["candidate_id"] = candidate_id_for(unresolved, projection["archive_id"])
    invalid["candidates"].sort(key=lambda item: item["candidate_id"])
    with pytest.raises(ArchiveRelationInferenceError, match="candidate_next_probe_null_not_permitted"):
        validate_relation_payload(projection, invalid)


def test_exact_duplicates_remain_physical_and_identity_undecided(tmp_path: Path) -> None:
    _batch, _ingest, projection, relations = _pipeline(_archive_root(tmp_path / "archive"), tmp_path)
    left = _artifact(projection, "duplicates/duplicate-a.bin")
    right = _artifact(projection, "duplicates/duplicate-b.bin")
    assert left["artifact_ref"] != right["artifact_ref"]
    assert left["content_id"] == right["content_id"]
    assert any(
        item["relation"] == "identity_undecided"
        and {item["source_ref"], item["target_ref"]} == {left["artifact_ref"], right["artifact_ref"]}
        for item in relations["candidates"]
    )
    assert all(item["relation"] != "same_work" for item in relations["candidates"])


def test_sidecar_describes_and_sequence_has_only_real_endpoints(tmp_path: Path) -> None:
    _batch, _ingest, projection, relations = _pipeline(_archive_root(tmp_path / "archive"), tmp_path)
    sidecar = _artifact(projection, "projects/native/exports/frame_001.png.xmp")
    frame = _artifact(projection, "projects/native/exports/frame_001.png")
    assert any(
        item["relation"] == "describes"
        and item["source_ref"] == sidecar["artifact_ref"]
        and item["target_ref"] == frame["artifact_ref"]
        for item in relations["candidates"]
    )
    refs = {item["artifact_ref"] for item in projection["artifacts"]}
    for item in _candidates(relations, "same_series_candidate"):
        assert item["source_ref"] in refs
        assert item["target_ref"] in refs
        assert not item["target_ref"].startswith("sequence:")


def test_unrelated_same_basenames_do_not_pair_across_roots(tmp_path: Path) -> None:
    root = tmp_path / "unrelated"
    _write(root / "left/source/scene.blend", b"blend")
    _write(root / "right/exports/scene.mp4", b"video")
    _batch, _ingest, projection, relations = _pipeline(root, tmp_path, "artist-unrelated")
    native = _artifact(projection, "left/source/scene.blend")["artifact_ref"]
    output = _artifact(projection, "right/exports/scene.mp4")["artifact_ref"]
    assert not any(
        item["relation"] == "manifestation_of"
        and item["source_ref"] == output
        and item["target_ref"] == native
        for item in relations["candidates"]
    )


def test_limit_reached_is_compact_diagnostic_without_candidate_explosion(tmp_path: Path) -> None:
    root = tmp_path / "limited"
    for index in range(80):
        _write(root / f"files/file_{index:03d}.dat", str(index).encode())
    batch = observe_archive(root, "limited", max_files=0)
    assert validate_batch(batch) is True
    database = tmp_path / "limited.sqlite"
    ingest_observation_batch(database, batch)
    replay = replay_snapshot(database, archive_id="limited", snapshot_id=batch["snapshot_id"])
    projection = project_archive_snapshot(replay["snapshot"])
    relations = infer_archive_relations(projection)
    assert relations["coverage"]["limit_reached_observations"] > 0
    assert relations["skipped_observation_summary"]["limit_reached"]["count"] > 0
    limit_ids = set(relations["skipped_observation_summary"]["limit_reached"].get("observation_ids", []))
    assert not any(
        candidate["relation"] for candidate in relations["candidates"]
        if limit_ids.intersection(candidate["evidence_refs"])
    )
    assert len(relations["candidates"]) < 100


def test_symlink_null_content_is_preserved_but_not_paired_as_output(tmp_path: Path) -> None:
    _batch, _ingest, projection, relations = _pipeline(_archive_root(tmp_path / "archive"), tmp_path)
    symlink = _artifact(projection, "projects/native/exports/link-to-render.mp4")
    special = _artifact(projection, "special.pipe")
    assert symlink["kind"] == "symlink"
    assert symlink["content_id"] is None
    assert special["kind"] == "special"
    assert special["content_id"] is None
    assert not any(
        ref in {item["source_ref"], item["target_ref"]}
        and item["relation"] == "manifestation_of"
        for item in relations["candidates"]
        for ref in (symlink["artifact_ref"], special["artifact_ref"])
    )


def test_invalid_projection_and_payload_fail_closed(tmp_path: Path) -> None:
    _batch, _ingest, projection, relations = _pipeline(_archive_root(tmp_path / "archive"), tmp_path)
    malformed_projection = copy.deepcopy(projection)
    malformed_projection["artifacts"][0]["artifact_ref"] = "artifact:ghost"
    with pytest.raises(ArchiveRelationInferenceError):
        infer_archive_relations(malformed_projection)

    malformed_payload = copy.deepcopy(relations)
    malformed_payload["candidates"][0]["status"] = "accepted"
    with pytest.raises(ArchiveRelationInferenceError):
        validate_relation_payload(projection, malformed_payload)


def test_two_archive_ids_are_isolated_and_valid_observer_ids_ingest(tmp_path: Path) -> None:
    root = _archive_root(tmp_path / "archive")
    batch_a = observe_archive(root, "artist/a")
    batch_b = observe_archive(root, r"artist\b")
    database = tmp_path / "isolated.sqlite"
    ingest_observation_batch(database, batch_a)
    ingest_observation_batch(database, batch_b)
    projection_a = project_archive_snapshot(replay_snapshot(
        database, archive_id="artist/a", snapshot_id=batch_a["snapshot_id"]
    )["snapshot"])
    projection_b = project_archive_snapshot(replay_snapshot(
        database, archive_id=r"artist\b", snapshot_id=batch_b["snapshot_id"]
    )["snapshot"])
    relations_a = infer_archive_relations(projection_a)
    relations_b = infer_archive_relations(projection_b)
    assert projection_a["archive_id"] != projection_b["archive_id"]
    assert {item["artifact_ref"] for item in projection_a["artifacts"]}.isdisjoint(
        {item["artifact_ref"] for item in projection_b["artifacts"]}
    )
    assert relations_a["archive_id"] == "artist/a"
    assert relations_b["archive_id"] == r"artist\b"


def test_same_projection_is_byte_identical_and_payload_serializes_deterministically(tmp_path: Path) -> None:
    _batch, _ingest, projection, relations = _pipeline(_archive_root(tmp_path / "archive"), tmp_path)
    repeat = infer_archive_relations(copy.deepcopy(projection))
    encoded = json.dumps(relations, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    repeated_encoded = json.dumps(repeat, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert relations == repeat
    assert encoded == repeated_encoded
    assert validate_relation_payload(projection, repeat) is True
