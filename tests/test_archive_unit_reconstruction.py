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
from src.flujo.knowledge.archive_relation_inference import infer_archive_relations
from src.flujo.knowledge.archive_unit_reconstruction import (
    ALGORITHM_VERSION,
    ArchiveUnitReconstructionError,
    SCHEMA,
    reconstruct_archive_units,
    unit_id_for,
    validate_unit_payload,
)


def _write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _fixture_root(root: Path, *, multi_anchor: bool = False) -> Path:
    _write(root / "projects/a/source/a.blend", b"a-source")
    _write(root / "projects/a/exports/a.mp4", b"a-output")
    _write(root / "projects/a/exports/frame_001.png", b"duplicate-frame")
    _write(root / "projects/a/exports/frame_002.png", b"frame-002")
    _write(root / "projects/a/exports/frame_001.png.xmp", b"sidecar")
    _write(root / "projects/a/exports/duplicate.png", b"same-content")
    _write(root / "projects/b/source/b.blend", b"b-source")
    _write(root / "projects/b/exports/b.mp4", b"b-output")
    _write(root / "projects/b/exports/duplicate.png", b"same-content")
    _write(root / "shared/library.bin", b"shared-dependency")
    _write(root / "orphan/renders/orphan.mp4", b"no-source")
    (root / "projects/a/exports/broken-link.mp4").symlink_to("missing.mp4")
    os.mkfifo(root / "projects/a/exports/special.pipe")
    if multi_anchor:
        _write(root / "projects/multi/left/left.blend", b"left-source")
        _write(root / "projects/multi/right/right.blend", b"right-source")
        _write(root / "projects/multi/exports/shared.mp4", b"shared-output")
    return root


def _pipeline(root: Path, tmp_path: Path, archive_id: str = "artist") -> tuple[dict, dict, dict, dict, dict]:
    batch = observe_archive(root, archive_id)
    assert validate_batch(batch) is True
    safe_id = archive_id.replace("/", "_").replace(chr(92), "_")
    database = tmp_path / f"{safe_id}.sqlite"
    ingest_observation_batch(database, batch)
    replay = replay_snapshot(database, archive_id=archive_id, snapshot_id=batch["snapshot_id"])
    projection = project_archive_snapshot(replay["snapshot"])
    relations = infer_archive_relations(projection)
    units = reconstruct_archive_units(projection, relations)
    assert validate_unit_payload(projection, relations, units) is True
    return batch, projection, relations, units, replay


def _artifact(projection: dict, path: str) -> dict:
    return next(item for item in projection["artifacts"] if item["relative_path"] == path)


def _assignment(units: dict, artifact_ref: str) -> dict:
    return next(item for item in units["assignments"] if item["artifact_ref"] == artifact_ref)


def _unit(units: dict, unit_id: str) -> dict:
    return next(item for item in units["units"] if item["unit_id"] == unit_id)


def test_two_native_projects_stay_separate_and_local_outputs_attach(tmp_path: Path) -> None:
    _batch, projection, _relations, units, _replay = _pipeline(_fixture_root(tmp_path / "archive"), tmp_path)
    native_a = _artifact(projection, "projects/a/source/a.blend")["artifact_ref"]
    native_b = _artifact(projection, "projects/b/source/b.blend")["artifact_ref"]
    output_a = _artifact(projection, "projects/a/exports/a.mp4")["artifact_ref"]
    output_b = _artifact(projection, "projects/b/exports/b.mp4")["artifact_ref"]
    assignment_a = _assignment(units, native_a)
    assignment_b = _assignment(units, native_b)
    assert assignment_a["status"] == "assigned"
    assert assignment_b["status"] == "assigned"
    assert assignment_a["unit_id"] != assignment_b["unit_id"]
    assert _assignment(units, output_a)["unit_id"] == assignment_a["unit_id"]
    assert _assignment(units, output_b)["unit_id"] == assignment_b["unit_id"]
    assert _unit(units, assignment_a["unit_id"])["role"] == "project_unit"
    assert _unit(units, assignment_b["unit_id"])["role"] == "project_unit"


def test_output_only_folder_is_unresolved_exported_product(tmp_path: Path) -> None:
    _batch, projection, _relations, units, _replay = _pipeline(_fixture_root(tmp_path / "archive"), tmp_path)
    orphan = _artifact(projection, "orphan/renders/orphan.mp4")["artifact_ref"]
    assignment = _assignment(units, orphan)
    assert assignment["status"] == "assigned"
    product = _unit(units, assignment["unit_id"])
    assert product["role"] == "exported_product"
    assert product["status"] == "unresolved_unit"
    assert "missing_source_binding" in product["missing_evidence"]
    assert product["anchor_refs"] == []


def test_shared_ancestors_are_not_promoted_and_duplicates_stay_physical(tmp_path: Path) -> None:
    _batch, projection, _relations, units, _replay = _pipeline(_fixture_root(tmp_path / "archive"), tmp_path)
    shared = _artifact(projection, "projects")["artifact_ref"]
    shared_assignment = _assignment(units, shared)
    assert shared_assignment["status"] in {"ambiguous", "unassigned"}
    assert all(unit["root_path"] != "projects" for unit in units["units"])

    duplicate_a = _artifact(projection, "projects/a/exports/duplicate.png")["artifact_ref"]
    duplicate_b = _artifact(projection, "projects/b/exports/duplicate.png")["artifact_ref"]
    assert duplicate_a != duplicate_b
    assert _assignment(units, duplicate_a)["unit_id"] != _assignment(units, duplicate_b)["unit_id"]


def test_multi_anchor_output_is_ambiguous_not_forced(tmp_path: Path) -> None:
    _batch, projection, _relations, units, _replay = _pipeline(
        _fixture_root(tmp_path / "archive", multi_anchor=True), tmp_path
    )
    shared_output = _artifact(projection, "projects/multi/exports/shared.mp4")["artifact_ref"]
    assignment = _assignment(units, shared_output)
    assert assignment["status"] == "ambiguous"
    assert assignment["unit_id"] is None
    assert len(assignment["alternatives"]) == 2
    assert shared_output in units["ambiguous_refs"]


def test_sidecar_sequence_symlink_and_special_are_accounted(tmp_path: Path) -> None:
    _batch, projection, relations, units, _replay = _pipeline(_fixture_root(tmp_path / "archive"), tmp_path)
    sidecar = _artifact(projection, "projects/a/exports/frame_001.png.xmp")["artifact_ref"]
    frame = _artifact(projection, "projects/a/exports/frame_001.png")["artifact_ref"]
    assert any(
        item["relation"] == "describes"
        and item["source_ref"] == sidecar
        and item["target_ref"] == frame
        for item in relations["candidates"]
    )
    assert any(item["relation"] == "same_series_candidate" for item in relations["candidates"])
    broken = _artifact(projection, "projects/a/exports/broken-link.mp4")
    special = _artifact(projection, "projects/a/exports/special.pipe")
    assert broken["content_id"] is None
    assert special["content_id"] is None
    assert _assignment(units, broken["artifact_ref"])["status"] == "assigned"
    assert _assignment(units, special["artifact_ref"])["status"] in {"assigned", "ambiguous", "unassigned"}


def test_zero_anchors_and_outputs_leave_everything_unassigned(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    _write(root / "notes/readme.txt", b"plain text")
    _batch, projection, _relations, units, _replay = _pipeline(root, tmp_path, "plain")
    assert units["units"] == []
    assert units["unassigned_refs"] == sorted(item["artifact_ref"] for item in projection["artifacts"])
    assert all(item["status"] == "unassigned" for item in units["assignments"])
    assert units["reconciliation"]["balanced"] is True


def test_two_archives_are_isolated_and_unit_identity_is_anchor_based(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path / "archive")
    batch_a, projection_a, relations_a, units_a, _replay_a = _pipeline(root, tmp_path, "artist/a")
    batch_b, projection_b, relations_b, units_b, _replay_b = _pipeline(root, tmp_path, r"artist\b")
    assert batch_a["archive_id"] != batch_b["archive_id"]
    assert projection_a["input_hash"] != projection_b["input_hash"]
    assert units_a["archive_id"] == "artist/a"
    assert units_b["archive_id"] == r"artist\b"
    assert {unit["unit_id"] for unit in units_a["units"]}.isdisjoint(
        {unit["unit_id"] for unit in units_b["units"]}
    )
    assert relations_a["archive_id"] != relations_b["archive_id"]


def test_unit_id_and_replay_are_deterministic_and_membership_does_not_change_identity(tmp_path: Path) -> None:
    _batch, projection, relations, first, _replay = _pipeline(_fixture_root(tmp_path / "archive"), tmp_path)
    second = reconstruct_archive_units(copy.deepcopy(projection), copy.deepcopy(relations))
    assert first == second
    encoded = json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert encoded == json.dumps(second, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    unit = first["units"][0]
    semantics = {"role": unit["role"], "root_path": unit["root_path"], "anchor_refs": unit["anchor_refs"]}
    assert unit_id_for(semantics, first["archive_id"], first["snapshot_id"]) == unit["unit_id"]
    altered = dict(semantics, member_refs=["new-physical-member"], evidence_for=["new-evidence"])
    assert unit_id_for(altered, first["archive_id"], first["snapshot_id"]) == unit["unit_id"]
    relation_material = copy.deepcopy(relations)
    expected_hash = "sha256:" + hashlib.sha256(
        json.dumps(relation_material, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    assert first["relation_hash"] == expected_hash


def test_malformed_upstream_and_assignment_fail_closed(tmp_path: Path) -> None:
    _batch, projection, relations, units, _replay = _pipeline(_fixture_root(tmp_path / "archive"), tmp_path)
    malformed_projection = copy.deepcopy(projection)
    malformed_projection["artifacts"][0]["artifact_ref"] = "artifact:ghost"
    with pytest.raises(ArchiveUnitReconstructionError):
        reconstruct_archive_units(malformed_projection, relations)

    malformed_relations = copy.deepcopy(relations)
    if malformed_relations["candidates"]:
        malformed_relations["candidates"][0]["status"] = "accepted"
    with pytest.raises(ArchiveUnitReconstructionError):
        reconstruct_archive_units(projection, malformed_relations)

    malformed_units = copy.deepcopy(units)
    malformed_units["assignments"][0]["status"] = "assigned"
    malformed_units["assignments"][0]["unit_id"] = "unit:missing"
    with pytest.raises(ArchiveUnitReconstructionError):
        validate_unit_payload(projection, relations, malformed_units)


def test_schema_and_public_contract_are_exact(tmp_path: Path) -> None:
    _batch, projection, relations, units, _replay = _pipeline(_fixture_root(tmp_path / "archive"), tmp_path)
    assert units["schema"] == SCHEMA
    assert units["algorithm_version"] == ALGORITHM_VERSION
    assert set(units) == {
        "schema", "source_projection_schema", "source_relation_schema", "algorithm_version",
        "archive_id", "snapshot_id", "input_hash", "relation_hash", "units", "assignments",
        "unassigned_refs", "ambiguous_refs", "reconciliation",
    }
    assert units["input_hash"] == projection["input_hash"]
    assert units["reconciliation"]["truth_promotions"] == 0
    assert validate_unit_payload(projection, relations, units) is True
