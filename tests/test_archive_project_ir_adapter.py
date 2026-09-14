from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
from src.flujo.knowledge.archive_observer import observe_archive, validate_batch
from src.flujo.knowledge.archive_reconstruction import project_archive_snapshot
from src.flujo.knowledge.archive_relation_inference import infer_archive_relations
from src.flujo.knowledge.archive_unit_reconstruction import reconstruct_archive_units
from src.flujo.knowledge.archive_project_ir_adapter import (
    ALGORITHM_VERSION,
    ArchiveProjectIRAdapterError,
    PROJECT_SCHEMA,
    SCHEMA,
    adapt_archive_units_to_project_ir,
    project_ir_bundle_from_units,
    validate_project_ir_bundle,
)
from src.flujo.knowledge.project_ir import validate_project_ir


def _write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _root(root: Path) -> Path:
    _write(root / "work/left/left.blend", b"left-source")
    _write(root / "work/right/right.blend", b"right-source")
    _write(root / "work/exports/shared.mp4", b"ambiguous-output")
    _write(root / "solo/source.blend", b"solo-source")
    _write(root / "solo/output.mp4", b"solo-output")
    _write(root / "notes/readme.txt", b"unassigned-note")
    return root


def _pipeline(root: Path, tmp_path: Path, archive_id: str = "artist") -> tuple[dict, dict, dict, dict]:
    batch = observe_archive(root, archive_id)
    assert validate_batch(batch) is True
    database = tmp_path / "memory.sqlite"
    ingest_observation_batch(database, batch)
    replay = replay_snapshot(database, archive_id=archive_id, snapshot_id=batch["snapshot_id"])
    projection = project_archive_snapshot(replay["snapshot"])
    relations = infer_archive_relations(projection)
    units = reconstruct_archive_units(projection, relations)
    return projection, relations, units, replay


def _artifact_ref(projection: dict, path: str) -> str:
    return next(item["artifact_ref"] for item in projection["artifacts"] if item["relative_path"] == path)


def test_actual_stage2c_to_project_ir_bundle_is_lossless_and_valid(tmp_path: Path) -> None:
    projection, relations, units, _replay = _pipeline(_root(tmp_path / "archive"), tmp_path)
    bundle = adapt_archive_units_to_project_ir(projection, relations, units)
    assert validate_project_ir_bundle(projection, relations, units, bundle) is True
    assert bundle["schema"] == SCHEMA
    assert bundle["target_project_ir_schema"] == PROJECT_SCHEMA
    assert bundle["algorithm_version"] == ALGORITHM_VERSION
    assert bundle["input_hash"] == projection["input_hash"]
    assert bundle["relation_hash"] == units["relation_hash"]
    assert len(bundle["records"]) == len(units["units"])
    assert len(bundle["unit_project_map"]) == len(units["units"])
    assert all(validate_project_ir(record) == [] for record in bundle["records"])
    assert bundle["reconciliation"]["units_mapped_exactly_once"] is True
    assert bundle["reconciliation"]["truth_promotions"] == 0


def test_unit_mapping_and_physical_provenance_are_preserved(tmp_path: Path) -> None:
    projection, relations, units, _replay = _pipeline(_root(tmp_path / "archive"), tmp_path)
    bundle = project_ir_bundle_from_units(projection, relations, units)
    records_by_unit = {
        record["archive_unit"]["unit_id"]: record for record in bundle["records"]
    }
    for unit in units["units"]:
        record = records_by_unit[unit["unit_id"]]
        assert record["archive_unit"] == unit
        assert record["source"]["unit_id"] == unit["unit_id"]
        assert record["provenance"]["unit_id"] == unit["unit_id"]
        assert record["provenance"]["input_hash"] == projection["input_hash"]
        member_refs = {artifact["artifact_ref"] for artifact in record["artifacts"]}
        assert member_refs == set(unit["member_refs"])
        assert record["state"] in {"candidate", "unknown"}
        assert record["state"] not in {"active", "verified"}
        assert all(relation["status"] in {"provisional", "pending_relation", "unresolved_candidate"}
                   for relation in record["relations"])


def test_ambiguous_and_unassigned_artifacts_are_explicit_not_projects(tmp_path: Path) -> None:
    projection, relations, units, _replay = _pipeline(_root(tmp_path / "archive"), tmp_path)
    bundle = adapt_archive_units_to_project_ir(projection, relations, units)
    shared_output = _artifact_ref(projection, "work/exports/shared.mp4")
    note = _artifact_ref(projection, "notes/readme.txt")
    assert shared_output in bundle["ambiguous_refs"]
    assert note in bundle["unassigned_refs"]
    record_member_refs = {
        artifact["artifact_ref"]
        for record in bundle["records"]
        for artifact in record["artifacts"]
    }
    assert shared_output not in record_member_refs
    assert note not in record_member_refs
    assert all(record["archive_unit"]["unit_id"] for record in bundle["records"])


def test_deterministic_replay_has_no_wall_clock_provenance(tmp_path: Path) -> None:
    projection, relations, units, _replay = _pipeline(_root(tmp_path / "archive"), tmp_path)
    first = adapt_archive_units_to_project_ir(copy.deepcopy(projection), copy.deepcopy(relations), copy.deepcopy(units))
    second = adapt_archive_units_to_project_ir(copy.deepcopy(projection), copy.deepcopy(relations), copy.deepcopy(units))
    encoded_first = json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    encoded_second = json.dumps(second, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert first == second
    assert encoded_first == encoded_second
    assert all("created_at" not in record["provenance"] for record in first["records"])
    assert all("updated_at" not in record["provenance"] for record in first["records"])


def test_malformed_stage2c_or_bundle_fails_closed(tmp_path: Path) -> None:
    projection, relations, units, _replay = _pipeline(_root(tmp_path / "archive"), tmp_path)
    malformed_units = copy.deepcopy(units)
    malformed_units["assignments"][0]["unit_id"] = "unit:missing"
    with pytest.raises(ArchiveProjectIRAdapterError):
        adapt_archive_units_to_project_ir(projection, relations, malformed_units)

    bundle = adapt_archive_units_to_project_ir(projection, relations, units)
    malformed_bundle = copy.deepcopy(bundle)
    malformed_bundle["records"][0]["state"] = "verified"
    with pytest.raises(ArchiveProjectIRAdapterError):
        validate_project_ir_bundle(projection, relations, units, malformed_bundle)

    malformed_bundle = copy.deepcopy(bundle)
    malformed_bundle["unit_project_map"].pop()
    with pytest.raises(ArchiveProjectIRAdapterError):
        validate_project_ir_bundle(projection, relations, units, malformed_bundle)


def test_provenance_hash_tampering_and_projection_input_mismatch_fail(tmp_path: Path) -> None:
    projection, relations, units, _replay = _pipeline(_root(tmp_path / "archive"), tmp_path)
    bundle = adapt_archive_units_to_project_ir(projection, relations, units)
    tampered = copy.deepcopy(bundle)
    tampered["relation_hash"] = "sha256:tampered"
    with pytest.raises(ArchiveProjectIRAdapterError):
        validate_project_ir_bundle(projection, relations, units, tampered)

    tampered_projection = copy.deepcopy(projection)
    tampered_projection["input_hash"] = "sha256:tampered"
    with pytest.raises(ArchiveProjectIRAdapterError):
        adapt_archive_units_to_project_ir(tampered_projection, relations, units)
