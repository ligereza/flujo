from __future__ import annotations

from copy import deepcopy

import pytest

from flujo.knowledge.archive_memory import ingest_observation_batch, replay_snapshot
from flujo.knowledge.archive_observer import observe_archive
from flujo.knowledge.archive_reconstruction import project_archive_snapshot
from flujo.knowledge.archive_relation_inference import infer_archive_relations
from flujo.knowledge.archive_relation_evaluator import (
    CANDIDATE_SCHEMA,
    INPUT_SCHEMA,
    REPORT_SCHEMA,
    ArchiveRelationEvaluationError,
    assert_relation_payload,
    candidate_id_for,
    evaluate_relation_payload,
    input_hash_for_projection,
)


def _projection() -> dict:
    projection = {
        "schema": INPUT_SCHEMA,
        "source_schema": "mak-archive-observation-batch-v1",
        "archive_id": "archive-a",
        "snapshot_id": "snapshot:one",
        "input_hash": "",
        "artifacts": [
            {"archive_id": "archive-a", "artifact_ref": "archive-artifact:one", "content_id": "content:sha256:" + "a" * 64},
            {"archive_id": "archive-a", "artifact_ref": "archive-artifact:two", "content_id": "content:sha256:" + "a" * 64},
            {"archive_id": "archive-a", "artifact_ref": "archive-artifact:three", "content_id": None},
        ],
        "candidate_observations": [
            {
                "record_type": "candidate_observation",
                "observation_id": "observation:manifest",
                "observation_type": "manifest_candidate",
                "status": "candidate",
                "artifact_refs": ["archive-artifact:one", "archive-artifact:three"],
                "evidence": {"manifest": "manifest.json"},
            },
            {
                "record_type": "candidate_observation",
                "observation_id": "observation:limit",
                "observation_type": "limit_reached",
                "status": "candidate",
                "artifact_refs": [],
                "evidence": {"relative_path": "omitted.bin"},
            },
        ],
        "local_groups": [{"group_id": "g1", "artifact_refs": ["archive-artifact:one", "archive-artifact:three"]}],
    }
    projection["input_hash"] = input_hash_for_projection(projection)
    return projection


def _candidate(projection: dict, *, source: str = "archive-artifact:one", target: str = "archive-artifact:three", relation: str = "component_of") -> dict:
    candidate = {
        "candidate_id": "",
        "source_ref": source,
        "relation": relation,
        "target_ref": target,
        "inverse_relation": "has_component" if relation == "component_of" else relation,
        "status": "pending_relation",
        "score": 0.8,
        "reason_codes": ["manifest_reference"],
        "evidence_refs": ["observation:manifest"],
        "evidence_for": [{"code": "manifest_reference", "detail": "manifest names both physical artifacts"}],
        "evidence_against": [{"code": "no_native_witness", "detail": "native source is not observed"}],
        "alternatives": [],
        "missing_evidence": ["explicit_export_witness"],
        "next_probe": "inspect the manifest and native reference",
    }
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    return candidate


def _payload(projection: dict, candidates: list[dict] | None = None) -> dict:
    candidates = list(candidates or [])
    candidates.sort(key=lambda item: item["candidate_id"])
    return {
        "schema": CANDIDATE_SCHEMA,
        "source_schema": INPUT_SCHEMA,
        "archive_id": projection["archive_id"],
        "snapshot_id": projection["snapshot_id"],
        "input_hash": projection["input_hash"],
        "algorithm_version": "fixture",
        "candidates": candidates,
        "truncated": False,
        "truncation": None,
    }


def test_minimal_valid_payload_passes_and_report_hash_replays() -> None:
    projection = _projection()
    payload = _payload(projection, [_candidate(projection)])
    before_projection = deepcopy(projection)
    before_payload = deepcopy(payload)
    first = evaluate_relation_payload(projection, payload)
    second = evaluate_relation_payload(projection, payload)
    assert first["schema"] == REPORT_SCHEMA
    assert first["passed"] is True
    assert first["report_hash"] == second["report_hash"]
    assert first["checks"]["duplicate_physical_refs"]["passed"] is True
    assert projection == before_projection
    assert payload == before_payload
    assert assert_relation_payload(projection, payload) is True


def test_authoritative_stage2a_hash_is_not_recomputed_by_evaluator() -> None:
    projection = _projection()
    projection["input_hash"] = "input:authoritative-stage2a-hash"
    payload = _payload(projection, [_candidate(projection)])
    report = evaluate_relation_payload(projection, payload)
    assert report["valid"] is True
    assert report["source"]["input_hash"] == projection["input_hash"]
    assert report["source"]["projection_digest"].startswith("projection:")


def test_dangling_endpoint_and_content_id_endpoint_fail() -> None:
    projection = _projection()
    candidate = _candidate(projection)
    candidate["target_ref"] = "archive-artifact:missing"
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    assert report["passed"] is False
    assert any(error["code"] == "endpoint_dangling" for error in report["errors"])

    candidate = _candidate(projection)
    candidate["source_ref"] = projection["artifacts"][0]["content_id"]
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    assert any(error["code"] == "content_id_endpoint" for error in report["errors"])


def test_wrong_inverse_promoted_status_and_score_fail_closed() -> None:
    projection = _projection()
    candidate = _candidate(projection)
    candidate["inverse_relation"] = "has_version"
    candidate["status"] = "supported"
    candidate["score"] = 1.5
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    codes = {error["code"] for error in report["errors"]}
    assert {"inverse_relation_invalid", "promoted_or_invalid_status", "score_out_of_range"} <= codes
    with pytest.raises(ArchiveRelationEvaluationError):
        assert_relation_payload(projection, _payload(projection, [candidate]))


def test_nan_score_is_rejected() -> None:
    projection = _projection()
    candidate = _candidate(projection)
    candidate["score"] = float("nan")
    # The evaluator must reject the score before attempting a semantic ID.
    candidate["candidate_id"] = "candidate:nan"
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    assert any(error["code"] == "score_out_of_range" for error in report["errors"])


def test_duplicate_edge_and_forward_inverse_duplicate_fail() -> None:
    projection = _projection()
    first = _candidate(projection)
    second = deepcopy(first)
    second["candidate_id"] = "candidate:manually-duplicated"
    report = evaluate_relation_payload(projection, _payload(projection, [first, second]))
    assert any(error["code"] == "duplicate_semantic_edge" for error in report["errors"])

    reverse = _candidate(projection, source="archive-artifact:three", target="archive-artifact:one", relation="has_component")
    report = evaluate_relation_payload(projection, _payload(projection, [first, reverse]))
    assert any(error["code"] == "duplicate_semantic_edge" for error in report["errors"])


def test_self_edge_is_rejected_even_for_symmetric_relation() -> None:
    projection = _projection()
    candidate = _candidate(projection, source="archive-artifact:one", target="archive-artifact:one", relation="same_series_candidate")
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    assert any(error["code"] == "self_edge" for error in report["errors"])


def test_cross_archive_projection_and_limit_diagnostic_endpoint_fail() -> None:
    projection = _projection()
    cross_archive = deepcopy(projection)
    cross_archive["artifacts"].append({"archive_id": "archive-b", "artifact_ref": "archive-artifact:other", "content_id": None})
    cross_archive["input_hash"] = input_hash_for_projection(cross_archive)
    candidate = _candidate(cross_archive, source="archive-artifact:other")
    report = evaluate_relation_payload(cross_archive, _payload(cross_archive, [candidate]))
    codes = {error["code"] for error in report["errors"]}
    assert "archive_isolation" in codes

    candidate = _candidate(projection, source="observation:limit")
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    assert any(error["code"] in {"endpoint_dangling", "diagnostic_endpoint"} for error in report["errors"])

    candidate = _candidate(projection)
    candidate["relation"] = "limit_reached"
    candidate["inverse_relation"] = "limit_reached"
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    assert any(error["code"] == "diagnostic_relation" for error in report["errors"])

    candidate = _candidate(projection)
    candidate["evidence_refs"] = ["observation:limit"]
    candidate["candidate_id"] = candidate_id_for(candidate, projection["archive_id"])
    report = evaluate_relation_payload(projection, _payload(projection, [candidate]))
    assert any(error["code"] == "diagnostic_evidence_ref" for error in report["errors"])


def test_wrong_and_nondeterministic_candidate_ids_are_rejected() -> None:
    projection = _projection()
    first = _candidate(projection)
    first["candidate_id"] = "candidate:wrong"
    report = evaluate_relation_payload(projection, _payload(projection, [first]))
    assert any(error["code"] == "candidate_id_mismatch" for error in report["errors"])

    second = _candidate(projection, source="archive-artifact:two", target="archive-artifact:three")
    payload = _payload(projection, [first, second])
    payload["candidates"] = list(reversed(payload["candidates"]))
    report = evaluate_relation_payload(projection, payload)
    assert any(error["code"] == "candidate_order_nondeterministic" for error in report["errors"])


def test_candidate_field_set_and_truncation_bound_are_enforced() -> None:
    projection = _projection()
    candidate = _candidate(projection)
    extra = deepcopy(candidate)
    extra["unexpected"] = True
    report = evaluate_relation_payload(projection, _payload(projection, [extra]))
    assert any(error["code"] == "candidate_fields_exact" for error in report["errors"])

    many = []
    for index in range(120):
        item = _candidate(projection, source="archive-artifact:one", target="archive-artifact:three")
        item["reason_codes"] = [f"reason_{index}"]
        item["candidate_id"] = candidate_id_for(item, projection["archive_id"])
        many.append(item)
    payload = _payload(projection, many)
    report = evaluate_relation_payload(projection, payload)
    assert any(error["code"] == "candidate_count_exceeds_bound" for error in report["errors"])

    payload["truncated"] = True
    payload["truncation"] = {"reason": "bounded local group", "omitted_count": 4}
    report = evaluate_relation_payload(projection, payload)
    assert report["checks"]["candidate_count_bounded"]["passed"] is True


def test_real_observe_memory_replay_projection_inference_passes(tmp_path) -> None:
    root = tmp_path / "archive"
    (root / "projects" / "native" / "source").mkdir(parents=True)
    (root / "projects" / "native" / "exports").mkdir(parents=True)
    (root / "projects" / "native" / "source" / "scene.blend").write_bytes(b"native")
    (root / "projects" / "native" / "exports" / "render.mp4").write_bytes(b"render")
    (root / "projects" / "native" / "exports" / "frame_001.png").write_bytes(b"frame")
    (root / "projects" / "native" / "exports" / "frame_001.png.xmp").write_bytes(b"sidecar")
    (root / "projects" / "native" / "exports" / "manifest.json").write_text("{}", encoding="utf-8")

    batch = observe_archive(root, "integration-archive")
    database = tmp_path / "learning.sqlite"
    ingest_observation_batch(database, batch)
    replay = replay_snapshot(
        database,
        archive_id="integration-archive",
        snapshot_id=batch["snapshot_id"],
    )
    projection = project_archive_snapshot(replay["snapshot"])
    payload = infer_archive_relations(projection)
    report = evaluate_relation_payload(projection, payload)

    assert report["valid"] is True
    assert report["status"] == "pass"
    assert report["passed"] is True
    assert assert_relation_payload(projection, payload) is True
