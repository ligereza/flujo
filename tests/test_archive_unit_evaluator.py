from __future__ import annotations

from copy import deepcopy
import importlib

import pytest

from flujo.knowledge.archive_unit_evaluator import (
    ArchiveUnitEvaluationError,
    assert_unit_payload,
    candidate_id_for,
    evaluate_unit_payload,
    relation_hash_for,
    unit_id_for,
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
            {
                "artifact_ref": "archive-artifact:native",
                "relative_path": "project/source/scene.blend",
                "content_id": "content:native",
                "derived_flags": {"native_authoring_anchor": True, "probable_output_media": False},
            },
            {
                "artifact_ref": "archive-artifact:output",
                "relative_path": "project/exports/render.mp4",
                "content_id": "content:output",
                "derived_flags": {"native_authoring_anchor": False, "probable_output_media": True},
            },
            {
                "artifact_ref": "archive-artifact:duplicate-a",
                "relative_path": "project/exports/duplicate-a.bin",
                "content_id": "content:duplicate",
                "derived_flags": {"native_authoring_anchor": False, "probable_output_media": False},
            },
            {
                "artifact_ref": "archive-artifact:duplicate-b",
                "relative_path": "project/exports/duplicate-b.bin",
                "content_id": "content:duplicate",
                "derived_flags": {"native_authoring_anchor": False, "probable_output_media": False},
            },
            {
                "artifact_ref": "archive-artifact:library",
                "relative_path": "assets/library.blend",
                "content_id": "content:library",
                "derived_flags": {"native_authoring_anchor": False, "probable_output_media": False},
            },
        ],
        "candidate_observations": [
            {
                "record_type": "candidate_observation",
                "observation_id": "observation:manifest",
                "observation_type": "manifest_candidate",
                "status": "candidate",
                "artifact_refs": ["archive-artifact:native", "archive-artifact:output"],
                "evidence": {},
            }
        ],
        "native_anchor_refs": ["archive-artifact:native"],
        "probable_output_refs": ["archive-artifact:output"],
    }


def _candidate(projection: dict) -> dict:
    candidate = {
        "candidate_id": "",
        "source_ref": "archive-artifact:output",
        "relation": "manifestation_of",
        "target_ref": "archive-artifact:native",
        "inverse_relation": "has_manifestation",
        "status": "unresolved_candidate",
        "score": 0.68,
        "reason_codes": ["local_native_anchor_output"],
        "evidence_refs": [
            "archive-artifact:native",
            "archive-artifact:output",
            "observation:manifest",
        ],
        "evidence_for": ["native_anchor_feature"],
        "evidence_against": ["export_witness_not_observed"],
        "alternatives": ["preview_or_intermediate_media"],
        "missing_evidence": ["export_witness"],
        "next_probe": "locate_export_witness",
    }
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    return candidate


def _relations(projection: dict) -> dict:
    candidate = _candidate(projection)
    payload = {
        "schema": "mak-archive-relation-candidates-v1",
        "source_schema": "mak-archive-reconstruction-input-v1",
        "archive_id": projection["archive_id"],
        "snapshot_id": projection["snapshot_id"],
        "input_hash": projection["input_hash"],
        "algorithm_version": "fixture",
        "candidates": [candidate],
        "skipped_observation_summary": {},
        "coverage": {
            "limits": {"max_candidates": 512, "max_pairs_per_group": 32, "max_local_group_pairs": 64},
            "projection_artifacts": 5,
            "projection_observations": 1,
            "limit_reached_observations": 0,
            "attempted_candidates": 1,
            "generated_candidates": 1,
            "truncated": False,
            "truncated_groups": [],
            "truncated_pair_count": 0,
            "coverage_incomplete": False,
        },
        "reconciliation": {
            "candidate_count": 1,
            "candidate_ids_unique": True,
            "endpoint_refs_resolved": True,
            "evidence_refs_resolved": True,
            "truth_promotions": 0,
            "deterministic_order": True,
            "status_values": ["pending_relation", "unresolved_candidate"],
        },
    }
    return payload


def _unit(projection: dict, *, role: str, status: str, root_path: str, anchors: list[str], members: list[str], dependencies: list[str] | None = None, candidate_ids: list[str] | None = None, missing: list[str] | None = None) -> dict:
    unit = {
        "unit_id": "",
        "role": role,
        "status": status,
        "root_path": root_path,
        "anchor_refs": sorted(anchors),
        "member_refs": sorted(members),
        "dependency_refs": sorted(dependencies or []),
        "candidate_ids": sorted(candidate_ids or []),
        "evidence_for": ["fixture_observed_structure"],
        "evidence_against": [],
        "alternatives": [],
        "missing_evidence": sorted(missing or []),
    }
    unit["unit_id"] = unit_id_for(unit, projection["archive_id"], projection["snapshot_id"])
    return unit


def _assignment(ref: str, status: str, unit_id: str | None, *, candidates: list[str] | None = None, alternatives: list[str] | None = None) -> dict:
    return {
        "artifact_ref": ref,
        "status": status,
        "unit_id": unit_id,
        "reason_codes": ["fixture_assignment"],
        "candidate_ids": sorted(candidates or []),
        "alternatives": list(alternatives or []),
    }


def _payload() -> tuple[dict, dict, dict]:
    projection = _projection()
    relations = _relations(projection)
    candidate_id = relations["candidates"][0]["candidate_id"]
    project = _unit(
        projection,
        role="project_unit",
        status="provisional_unit",
        root_path="project",
        anchors=["archive-artifact:native"],
        members=["archive-artifact:native", "archive-artifact:duplicate-a", "archive-artifact:duplicate-b"],
        candidate_ids=[candidate_id],
    )
    output = _unit(
        projection,
        role="exported_product",
        status="unresolved_unit",
        root_path="project/exports",
        anchors=[],
        members=["archive-artifact:output"],
        candidate_ids=[candidate_id],
        missing=["source_binding"],
    )
    library = _unit(
        projection,
        role="library_dependency",
        status="provisional_unit",
        root_path="assets",
        anchors=[],
        members=["archive-artifact:library"],
    )
    unit_list = sorted([project, output, library], key=lambda item: item["unit_id"])
    assignments = sorted([
        _assignment("archive-artifact:native", "assigned", project["unit_id"]),
        _assignment("archive-artifact:output", "assigned", output["unit_id"], candidates=[candidate_id]),
        _assignment("archive-artifact:duplicate-a", "assigned", project["unit_id"]),
        _assignment("archive-artifact:duplicate-b", "assigned", project["unit_id"]),
        _assignment("archive-artifact:library", "assigned", library["unit_id"]),
    ], key=lambda item: item["artifact_ref"])
    units = {
        "schema": "mak-archive-unit-reconstruction-v1",
        "source_projection_schema": "mak-archive-reconstruction-input-v1",
        "source_relation_schema": "mak-archive-relation-candidates-v1",
        "algorithm_version": "fixture",
        "archive_id": projection["archive_id"],
        "snapshot_id": projection["snapshot_id"],
        "input_hash": projection["input_hash"],
        "relation_hash": relation_hash_for(relations),
        "units": unit_list,
        "assignments": assignments,
        "unassigned_refs": [],
        "ambiguous_refs": [],
        "reconciliation": {
            "total_artifacts": 5,
            "assigned": 5,
            "ambiguous": 0,
            "unassigned": 0,
            "unit_count": 3,
            "units_by_role": {"exported_product": 1, "library_dependency": 1, "project_unit": 1},
            "assignment_count": 5,
            "duplicates": 0,
            "loss": 0,
            "balanced": True,
            "truth_promotions": 0,
            "relation_candidate_count": 1,
            "unit_status_values": ["provisional_unit", "unresolved_unit"],
        },
    }
    return projection, relations, units


def test_minimal_valid_payload_passes_and_replays() -> None:
    projection, relations, units = _payload()
    before = deepcopy((projection, relations, units))
    first = evaluate_unit_payload(projection, relations, units)
    second = evaluate_unit_payload(projection, relations, units)
    assert first["schema"] == "mak-archive-unit-evaluation-v1"
    assert first["valid"] is True
    assert first["status"] == "pass"
    assert first["report_hash"] == second["report_hash"]
    assert first["checks"]["duplicate_physical_refs"]["passed"] is True
    assert (projection, relations, units) == before
    assert assert_unit_payload(projection, relations, units) is True


def test_missing_and_duplicate_assignment_fail_closed() -> None:
    projection, relations, units = _payload()
    missing = deepcopy(units)
    missing["assignments"] = missing["assignments"][1:]
    report = evaluate_unit_payload(projection, relations, missing)
    assert any(error["code"] == "assignment_partition_unbalanced" for error in report["errors"])

    duplicate = deepcopy(units)
    duplicate["assignments"].append(deepcopy(duplicate["assignments"][0]))
    duplicate["assignments"].sort(key=lambda item: item["artifact_ref"])
    report = evaluate_unit_payload(projection, relations, duplicate)
    assert any(error["code"] == "duplicate_assignment" for error in report["errors"])


def test_dangling_member_wrong_unit_id_and_membership_mismatch_fail() -> None:
    projection, relations, units = _payload()
    dangling = deepcopy(units)
    target = dangling["units"][0]
    target["member_refs"].append("archive-artifact:missing")
    target["member_refs"].sort()
    target["unit_id"] = unit_id_for(target, projection["archive_id"], projection["snapshot_id"])
    report = evaluate_unit_payload(projection, relations, dangling)
    assert any(error["code"] == "unit_ref_dangling" for error in report["errors"])

    wrong_id = deepcopy(units)
    wrong_id["units"][0]["unit_id"] = "unit:wrong"
    report = evaluate_unit_payload(projection, relations, wrong_id)
    assert any(error["code"] == "unit_id_mismatch" for error in report["errors"])

    mismatch = deepcopy(units)
    output_ref = "archive-artifact:output"
    assignment = next(item for item in mismatch["assignments"] if item["artifact_ref"] == output_ref)
    assignment["unit_id"] = mismatch["units"][0]["unit_id"]
    report = evaluate_unit_payload(projection, relations, mismatch)
    assert any(error["code"] == "assigned_membership_mismatch" for error in report["errors"])


def test_relation_hash_and_candidate_resolution_are_canonical() -> None:
    projection, relations, units = _payload()
    wrong_hash = deepcopy(units)
    wrong_hash["relation_hash"] = "relation:wrong"
    report = evaluate_unit_payload(projection, relations, wrong_hash)
    assert any(error["code"] == "unit_relation_hash_mismatch" for error in report["errors"])

    dangling_candidate = deepcopy(units)
    dangling_candidate["units"][0]["candidate_ids"] = ["candidate:missing"]
    dangling_candidate["units"][0]["unit_id"] = unit_id_for(
        dangling_candidate["units"][0], projection["archive_id"], projection["snapshot_id"]
    )
    report = evaluate_unit_payload(projection, relations, dangling_candidate)
    assert any(error["code"] == "unit_candidate_id_dangling" for error in report["errors"])


def test_ambiguous_requires_two_alternatives_and_unassigned_has_no_unit() -> None:
    projection, relations, units = _payload()
    ambiguous = deepcopy(units)
    assignment = next(item for item in ambiguous["assignments"] if item["artifact_ref"] == "archive-artifact:output")
    assignment.update({"status": "ambiguous", "unit_id": None, "alternatives": ["one"]})
    ambiguous["ambiguous_refs"] = ["archive-artifact:output"]
    ambiguous["reconciliation"]["assigned"] = 4
    ambiguous["reconciliation"]["ambiguous"] = 1
    ambiguous["reconciliation"]["balanced"] = True
    report = evaluate_unit_payload(projection, relations, ambiguous)
    assert any(error["code"] == "ambiguous_alternatives_insufficient" for error in report["errors"])

    unassigned = deepcopy(units)
    assignment = next(item for item in unassigned["assignments"] if item["artifact_ref"] == "archive-artifact:output")
    assignment["status"] = "unassigned"
    assignment["unit_id"] = units["units"][0]["unit_id"]
    unassigned["unassigned_refs"] = ["archive-artifact:output"]
    report = evaluate_unit_payload(projection, relations, unassigned)
    assert any(error["code"] == "unassigned_unit_present" for error in report["errors"])


def test_root_evidence_output_only_and_promoted_status_gates() -> None:
    projection, relations, units = _payload()
    fake_root = deepcopy(units)
    library = next(item for item in fake_root["units"] if item["role"] == "library_dependency")
    library["role"] = "project_unit"
    library["unit_id"] = unit_id_for(library, projection["archive_id"], projection["snapshot_id"])
    for assignment in fake_root["assignments"]:
        if assignment["artifact_ref"] == "archive-artifact:library":
            assignment["unit_id"] = library["unit_id"]
    fake_root["units"].sort(key=lambda item: item["unit_id"])
    report = evaluate_unit_payload(projection, relations, fake_root)
    assert any(error["code"] == "root_without_anchor_or_output_evidence" for error in report["errors"])

    promoted = deepcopy(units)
    output = next(item for item in promoted["units"] if item["role"] == "exported_product")
    output["role"] = "project_unit"
    output["status"] = "provisional_unit"
    output["unit_id"] = unit_id_for(output, projection["archive_id"], projection["snapshot_id"])
    for assignment in promoted["assignments"]:
        if assignment["artifact_ref"] == "archive-artifact:output":
            assignment["unit_id"] = output["unit_id"]
    promoted["units"].sort(key=lambda item: item["unit_id"])
    report = evaluate_unit_payload(projection, relations, promoted)
    assert any(error["code"] == "output_only_unit_invalid" for error in report["errors"])

    promoted_status = deepcopy(units)
    promoted_status["units"][0]["status"] = "supported"
    report = evaluate_unit_payload(projection, relations, promoted_status)
    assert any(error["code"] == "unit_promoted_status" for error in report["errors"])


def test_cross_archive_content_id_reconciliation_and_order_fail() -> None:
    projection, relations, units = _payload()
    cross_archive = deepcopy(projection)
    cross_archive["artifacts"][0]["archive_id"] = "archive-b"
    report = evaluate_unit_payload(cross_archive, relations, units)
    assert any(error["code"] == "cross_archive_artifact" for error in report["errors"])

    content_endpoint = deepcopy(units)
    content_endpoint["units"][0]["member_refs"] = ["content:duplicate"]
    content_endpoint["units"][0]["anchor_refs"] = []
    content_endpoint["units"][0]["unit_id"] = unit_id_for(content_endpoint["units"][0], projection["archive_id"], projection["snapshot_id"])
    report = evaluate_unit_payload(projection, relations, content_endpoint)
    assert any(error["code"] == "unit_content_id_endpoint" for error in report["errors"])

    lie = deepcopy(units)
    lie["reconciliation"]["balanced"] = False
    report = evaluate_unit_payload(projection, relations, lie)
    assert any(error["code"] == "reconciliation_mismatch" for error in report["errors"])

    synthetic = deepcopy(units)
    synthetic["units"][0]["root_path"] = "synthetic/not-observed"
    synthetic["units"][0]["unit_id"] = unit_id_for(
        synthetic["units"][0], projection["archive_id"], projection["snapshot_id"]
    )
    report = evaluate_unit_payload(projection, relations, synthetic)
    assert any(error["code"] == "unit_root_path_invalid" for error in report["errors"])

    nondeterministic = deepcopy(units)
    nondeterministic["units"] = list(reversed(nondeterministic["units"]))
    report = evaluate_unit_payload(projection, relations, nondeterministic)
    assert any(error["code"] == "unit_order_invalid" for error in report["errors"])


def test_optional_real_stage2c_cross_smoke_if_core_exists(tmp_path) -> None:
    try:
        module = importlib.import_module("flujo.knowledge.archive_unit_reconstruction")
    except ModuleNotFoundError:
        pytest.skip("Stage 2C core is not present in this checkout")
    reconstruct = getattr(module, "reconstruct_archive_units", None)
    if not callable(reconstruct):
        pytest.skip("Stage 2C core has no reconstruct_archive_units entrypoint")
    from flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
    from flujo.knowledge.archive_observer import observe_archive
    from flujo.knowledge.archive_reconstruction import project_archive_snapshot
    from flujo.knowledge.archive_relation_inference import infer_archive_relations

    root = tmp_path / "archive"
    (root / "project" / "source").mkdir(parents=True)
    (root / "project" / "exports").mkdir(parents=True)
    (root / "project" / "source" / "scene.blend").write_bytes(b"native")
    (root / "project" / "exports" / "render.mp4").write_bytes(b"output")
    batch = observe_archive(root, "stage2c-smoke")
    database = tmp_path / "learning.sqlite"
    ingest_observation_batch(database, batch)
    replay = replay_snapshot(
        database,
        archive_id="stage2c-smoke",
        snapshot_id=batch["snapshot_id"],
    )
    projection = project_archive_snapshot(replay["snapshot"])
    relations = infer_archive_relations(projection)
    units = reconstruct(projection, relations)
    assert assert_unit_payload(projection, relations, units) is True
