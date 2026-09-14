from __future__ import annotations

from copy import deepcopy
import copy
import json
from pathlib import Path

import pytest

from flujo.knowledge.archive_project_ir_evaluator import (
    ArchiveProjectIREvaluationError,
    assert_project_ir_payload,
    evaluate_project_ir_payload,
    project_id_for,
    relation_hash_for,
)


ARCHIVE_ID = "archive-a"
SNAPSHOT_ID = "snapshot:one"
INPUT_HASH = "input:stage2a-authoritative"


def _projection() -> dict:
    return {
        "schema": "mak-archive-reconstruction-input-v1",
        "source_schema": "mak-archive-observation-batch-v1",
        "archive_id": ARCHIVE_ID,
        "snapshot_id": SNAPSHOT_ID,
        "input_hash": INPUT_HASH,
        "artifacts": [
            {"artifact_ref": "archive-artifact:native", "physical_id": "physical:native", "relative_path": "project/source.blend", "content_id": "content:native"},
            {"artifact_ref": "archive-artifact:duplicate-a", "physical_id": "physical:duplicate-a", "relative_path": "project/a.bin", "content_id": "content:duplicate"},
            {"artifact_ref": "archive-artifact:duplicate-b", "physical_id": "physical:duplicate-b", "relative_path": "project/b.bin", "content_id": "content:duplicate"},
            {"artifact_ref": "archive-artifact:library", "physical_id": "physical:library", "relative_path": "shared/library.bin", "content_id": "content:library"},
            {"artifact_ref": "archive-artifact:orphan", "physical_id": "physical:orphan", "relative_path": "orphan/output.mp4", "content_id": "content:orphan"},
        ],
        "candidate_observations": [{
            "record_type": "candidate_observation", "observation_id": "observation:manifest",
            "observation_type": "manifest_candidate", "status": "candidate",
            "artifact_refs": ["archive-artifact:native"], "evidence": {},
        }],
    }


def _unit(projection: dict, role: str, status: str, root: str, anchors: list[str], members: list[str], dependencies: list[str] | None = None) -> dict:
    row = {
        "unit_id": "", "role": role, "status": status, "root_path": root,
        "anchor_refs": sorted(anchors), "member_refs": sorted(members),
        "dependency_refs": sorted(dependencies or []), "candidate_ids": [],
        "evidence_for": ["observed_structure"], "evidence_against": [],
        "alternatives": [], "missing_evidence": [],
    }
    semantic = {
        "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"],
        "role": role, "root_path": root, "anchor_refs": row["anchor_refs"],
    }
    row["unit_id"] = "unit:" + __import__("hashlib").sha256(
        json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return row


def _relations(projection: dict) -> dict:
    return {
        "schema": "mak-archive-relation-candidates-v1",
        "source_schema": "mak-archive-reconstruction-input-v1",
        "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"],
        "input_hash": projection["input_hash"], "algorithm_version": "fixture",
        "candidates": [], "skipped_observation_summary": {}, "coverage": {}, "reconciliation": {},
    }


def _units(projection: dict, relations: dict) -> dict:
    project = _unit(
        projection, "project_unit", "provisional_unit", "project", ["archive-artifact:native"],
        ["archive-artifact:native", "archive-artifact:duplicate-a", "archive-artifact:duplicate-b"],
        ["archive-artifact:library"],
    )
    library = _unit(projection, "library_dependency", "provisional_unit", "shared", [], ["archive-artifact:library"])
    rows = sorted([project, library], key=lambda row: row["unit_id"])
    assignments = sorted([
        {"artifact_ref": "archive-artifact:duplicate-a", "status": "assigned", "unit_id": project["unit_id"], "reason_codes": [], "candidate_ids": [], "alternatives": []},
        {"artifact_ref": "archive-artifact:duplicate-b", "status": "assigned", "unit_id": project["unit_id"], "reason_codes": [], "candidate_ids": [], "alternatives": []},
        {"artifact_ref": "archive-artifact:library", "status": "assigned", "unit_id": library["unit_id"], "reason_codes": [], "candidate_ids": [], "alternatives": []},
        {"artifact_ref": "archive-artifact:native", "status": "assigned", "unit_id": project["unit_id"], "reason_codes": [], "candidate_ids": [], "alternatives": []},
        {"artifact_ref": "archive-artifact:orphan", "status": "unassigned", "unit_id": None, "reason_codes": ["no_source_binding"], "candidate_ids": [], "alternatives": []},
    ], key=lambda row: row["artifact_ref"])
    result = {
        "schema": "mak-archive-unit-reconstruction-v1", "source_projection_schema": "mak-archive-reconstruction-input-v1",
        "source_relation_schema": "mak-archive-relation-candidates-v1", "algorithm_version": "fixture",
        "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"], "input_hash": projection["input_hash"],
        "relation_hash": relation_hash_for(relations), "units": rows, "assignments": assignments,
        "unassigned_refs": ["archive-artifact:orphan"], "ambiguous_refs": [],
        "reconciliation": {
            "total_artifacts": 5, "assigned": 4, "ambiguous": 0, "unassigned": 1,
            "unit_count": 2, "units_by_role": {"library_dependency": 1, "project_unit": 1},
            "assignment_count": 5, "duplicates": 0, "loss": 0, "balanced": True,
            "truth_promotions": 0, "relation_candidate_count": 0,
            "unit_status_values": ["provisional_unit", "unresolved_unit"],
        },
    }
    return result


def _relation(unit: dict, project_id: str, predicate: str, object_ref: str) -> dict:
    return {
        "relation_id": f"{predicate}:{unit['unit_id']}:{object_ref}", "subject": project_id,
        "predicate": predicate, "object": object_ref, "status": "provisional", "score": None,
        "evidence_refs": [], "evidence_for": ["preserved_ref"], "evidence_against": [],
        "alternatives": [], "missing_evidence": [], "next_probe": None,
        "archive_unit_id": unit["unit_id"],
    }


def _record(projection: dict, units: dict, unit: dict) -> dict:
    project_id = project_id_for(unit["unit_id"])
    artifacts = []
    for ref in unit["member_refs"]:
        source = next(item for item in projection["artifacts"] if item["artifact_ref"] == ref)
        artifacts.append({"artifact_ref": ref, "physical_id": source["physical_id"], "relative_path": source["relative_path"]})
    relations = [_relation(unit, project_id, "provisional_member", ref) for ref in unit["member_refs"]]
    relations += [_relation(unit, project_id, "provisional_dependency", ref) for ref in unit["dependency_refs"]]
    relations.sort(key=lambda row: (row["relation_id"], row["predicate"], row["object"]))
    state = "candidate" if unit["status"] == "provisional_unit" else "unknown"
    return {
        "schema": "mak-project-ir-v1", "project_id": project_id,
        "title": f"Provisional archive unit {unit['unit_id']}", "state": state,
        "source": {"kind": "archive_unit_reconstruction", "root_ref": f"archive:{ARCHIVE_ID}:snapshot:{SNAPSHOT_ID}:unit:{unit['unit_id']}", "root_exists": False, "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"], "unit_id": unit["unit_id"]},
        "purpose": "Deterministic provisional Project IR view; not a verified artistic claim.",
        "domains": ["archive", "reconstruction"], "artifacts": artifacts, "relations": relations,
        "evidence": [{"kind": "archive_unit_provenance", "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"], "input_hash": projection["input_hash"], "relation_hash": units["relation_hash"], "unit_id": unit["unit_id"], "status": unit["status"]}],
        "unknowns": [], "next_action": "preserve_provisional_status",
        "provenance": {"producer": "fixture", "method": "stage2c_unit_projection", "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"], "input_hash": projection["input_hash"], "relation_hash": units["relation_hash"], "unit_id": unit["unit_id"], "source_unit_schema": "mak-archive-unit-reconstruction-v1", "source_relation_schema": "mak-archive-relation-candidates-v1"},
        "archive_unit": deepcopy(unit), "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"], "input_hash": projection["input_hash"], "relation_hash": units["relation_hash"],
    }


def _bundle() -> tuple[dict, dict, dict, dict]:
    projection = _projection()
    relations = _relations(projection)
    units = _units(projection, relations)
    records = [_record(projection, units, unit) for unit in units["units"]]
    records.sort(key=lambda row: row["project_id"])
    unit_map = [{"unit_id": unit["unit_id"], "project_id": project_id_for(unit["unit_id"]), "role": unit["role"], "status": unit["status"]} for unit in units["units"]]
    unit_map.sort(key=lambda row: row["unit_id"])
    bundle = {
        "schema": "mak-archive-project-ir-bundle-v1", "source_unit_schema": "mak-archive-unit-reconstruction-v1", "target_project_ir_schema": "mak-project-ir-v1", "algorithm_version": "archive-units-to-project-ir-1",
        "archive_id": projection["archive_id"], "snapshot_id": projection["snapshot_id"], "input_hash": projection["input_hash"], "relation_hash": units["relation_hash"], "records": records, "unit_project_map": unit_map, "ambiguous_refs": [], "unassigned_refs": ["archive-artifact:orphan"],
        "reconciliation": {"units_input": 2, "records_output": 2, "unit_mappings": 2, "unit_ids_unique": True, "units_mapped_exactly_once": True, "project_ids_unique": True, "member_refs_total": 4, "member_refs_preserved": True, "dependency_refs_total": 1, "dependency_refs_preserved": True, "ambiguous_refs_count": 0, "unassigned_refs_count": 1, "duplicates": 0, "loss": 0, "balanced": True, "truth_promotions": 0, "deterministic_order": True, "ambiguous_and_unassigned_explicit": True},
    }
    return projection, relations, units, bundle


def test_minimal_valid_bundle_passes() -> None:
    projection, relations, units, bundle = _bundle()
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert report["valid"] is True
    assert report["status"] == "pass"
    assert report["errors"] == []
    assert assert_project_ir_payload(projection, relations, units, bundle) is True


def test_report_replay_is_deterministic_and_inputs_are_untouched() -> None:
    projection, relations, units, bundle = _bundle()
    before = deepcopy((projection, relations, units, bundle))
    first = evaluate_project_ir_payload(projection, relations, units, bundle)
    second = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert first == second
    assert (projection, relations, units, bundle) == before


@pytest.mark.parametrize(
    ("path", "mutation", "code"),
    [
        (("bundle", "archive_id"), "other-archive", "bundle_archive_id_mismatch"),
        (("bundle", "relation_hash"), "sha256:wrong", "bundle_relation_hash_mismatch"),
        (("bundle", "records", 0, "state"), "active", "project_truth_promoted"),
        (("bundle", "records", 0, "next_action"), "review_evidence", "mandatory_review_semantics_missing"),
        (("bundle", "records", 0, "project_id"), "random-project", "project_id_mismatch"),
        (("bundle", "records", 0, "archive_unit", "member_refs"), ["content:duplicate"], "project_archive_unit_loss"),
        (("bundle", "records", 0, "archive_unit", "unit_id"), "unit:missing", "project_archive_unit_loss"),
        (("bundle", "records", 0, "artifacts", 0, "artifact_ref"), "content:duplicate", "project_content_id_endpoint"),
    ],
)
def test_adversarial_mutations_fail_closed(path: tuple, mutation: object, code: str) -> None:
    projection, relations, units, bundle = _bundle()
    target: object = {"projection": projection, "relations": relations, "units": units, "bundle": bundle}
    cursor = target
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index]
    cursor[path[-1]] = mutation  # type: ignore[index]
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert report["valid"] is False
    assert code in {error["code"] for error in report["errors"]}
    with pytest.raises(ArchiveProjectIREvaluationError):
        assert_project_ir_payload(projection, relations, units, bundle)


def test_missing_duplicate_and_fabricated_unit_projections_fail() -> None:
    projection, relations, units, bundle = _bundle()
    bundle["records"] = bundle["records"][:1]
    bundle["unit_project_map"] = bundle["unit_project_map"][:1]
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert "missing_unit_projection" in {error["code"] for error in report["errors"]}

    projection, relations, units, bundle = _bundle()
    bundle["records"].append(deepcopy(bundle["records"][0]))
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert "duplicate_project_id" in {error["code"] for error in report["errors"]}

    projection, relations, units, bundle = _bundle()
    bundle["records"][0]["archive_unit"] = {**bundle["records"][0]["archive_unit"], "unit_id": "unit:fake"}
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert "project_archive_unit_loss" in {error["code"] for error in report["errors"]}


def test_ambiguous_unassigned_refs_and_reconciliation_lies_are_rejected() -> None:
    projection, relations, units, bundle = _bundle()
    units["ambiguous_refs"] = ["archive-artifact:orphan"]
    bundle["ambiguous_refs"] = ["archive-artifact:orphan"]
    bundle["unassigned_refs"] = []
    bundle["reconciliation"]["ambiguous_refs_count"] = 1
    bundle["reconciliation"]["unassigned_refs_count"] = 0
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert "ambiguous_refs_mismatch" in {error["code"] for error in report["errors"]}
    assert "bundle_reconciliation_mismatch" in {error["code"] for error in report["errors"]}

    projection, relations, units, bundle = _bundle()
    bundle["reconciliation"]["balanced"] = False
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert "bundle_reconciliation_mismatch" in {error["code"] for error in report["errors"]}


def test_relation_hash_and_three_argument_form_fail_closed() -> None:
    projection, relations, units, bundle = _bundle()
    changed = copy.deepcopy(relations)
    changed["algorithm_version"] = "tampered"
    report = evaluate_project_ir_payload(projection, changed, units, bundle)
    assert "unit_relation_hash_mismatch" in {error["code"] for error in report["errors"]}
    report = evaluate_project_ir_payload(projection, units, bundle)
    assert "relations_missing_for_hash" in {error["code"] for error in report["errors"]}


def test_authoritative_core_cross_smoke(tmp_path: Path) -> None:
    from flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
    from flujo.knowledge.archive_observer import observe_archive, validate_batch
    from flujo.knowledge.archive_reconstruction import project_archive_snapshot
    from flujo.knowledge.archive_relation_inference import infer_archive_relations
    from flujo.knowledge.archive_unit_reconstruction import reconstruct_archive_units
    from flujo.knowledge.archive_project_ir_adapter import adapt_archive_units_to_project_ir

    root = tmp_path / "archive"
    (root / "project").mkdir(parents=True)
    (root / "project" / "source.blend").write_bytes(b"source")
    (root / "project" / "output.mp4").write_bytes(b"output")
    batch = observe_archive(root, "cross-smoke")
    assert validate_batch(batch) is True
    database = tmp_path / "memory.sqlite"
    ingest_observation_batch(database, batch)
    replay = replay_snapshot(database, archive_id="cross-smoke", snapshot_id=batch["snapshot_id"])
    projection = project_archive_snapshot(replay["snapshot"])
    relations = infer_archive_relations(projection)
    units = reconstruct_archive_units(projection, relations)
    bundle = adapt_archive_units_to_project_ir(projection, relations, units)
    report = evaluate_project_ir_payload(projection, relations, units, bundle)
    assert report["valid"] is True, report
    assert report["errors"] == []
