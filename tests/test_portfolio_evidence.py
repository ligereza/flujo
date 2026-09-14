"""Tests for the real-archive evidence queue substrate."""

from __future__ import annotations

import json
from pathlib import Path

from flujo.knowledge.portfolio_evidence import (
    apply_human_decision,
    build_project_record,
    load_record,
    queue_payload,
)
from flujo.knowledge.project_ir import LearningStore


def _record(tmp_path: Path) -> tuple[Path, str]:
    database = tmp_path / "mak.db"
    record = build_project_record(
        project_id="arica-test",
        title="ARICA test",
        source_root=tmp_path,
        observed_artifacts=[{
            "id": "artifact:MYRA/MYRA_final.mp4", "path": "MYRA/MYRA_final.mp4",
            "kind": "video", "bytes": 12, "sha256": "a" * 64,
            "evidence_refs": ["media#sha256"],
        }],
        relation_candidates=[{
            "id": "candidate:test", "source_id": "artifact:MYRA/MYRA_final.mp4",
            "target_id": None, "relation": "version_of", "status": "unresolved_candidate",
            "score": 0.18, "evidence_refs": ["media#sha256"],
            "missing_evidence": ["source_project"], "next_probe": "locate source",
        }],
        evidence=[{"kind": "fixture", "status": "observed"}],
        unknowns=["source_binding=unknown"],
        source_snapshot_hash="snapshot-test",
        graph_observation={"artifacts": [{
            "id": "artifact:MYRA/MYRA_final.mp4", "path": "MYRA/MYRA_final.mp4",
            "kind": "video", "bytes": 12, "sha256": "a" * 64,
            "evidence_refs": ["media#sha256"],
        }]},
    )
    LearningStore(database).save_project(record)
    return database, "candidate:test"


def test_queue_and_human_decision_persist_in_project_ir_and_episode(tmp_path: Path) -> None:
    database, candidate_id = _record(tmp_path)
    initial = queue_payload(load_record(database, "arica-test"))
    assert initial["counts"] == {"pending": 1}

    result = apply_human_decision(
        database, project_id="arica-test", candidate_id=candidate_id,
        action="correct", note="frame is a sequence component, not a standalone work",
        corrected_relation="component_of", corrected_target_id="artifact:MYRA/MYRA_final.mp4",
        source_snapshot_hash="snapshot-test",
    )
    assert result["ok"] is True
    assert result["queue"]["counts"] == {"correct": 1}
    stored = load_record(database, "arica-test")
    candidate = stored["relations"][0]
    assert candidate["status"] == "corrected_by_human"
    assert candidate["human_review"]["action"] == "correct"
    assert candidate["corrected_relation"] == "component_of"
    assert candidate["corrected_target_id"] == "artifact:MYRA/MYRA_final.mp4"
    with LearningStore(database).connect() as connection:
        row = connection.execute(
            "SELECT status, outcome_json FROM project_episodes WHERE project_id='arica-test'"
        ).fetchone()
    assert row[0] == "verified"
    assert json.loads(row[1])["human_decision"] == "correct"
    assert result["draft"]["audit"]["human_reviews"]
    assert result["draft"]["selection"]["human_accepted_relation_keys"] == [
        "artifact:MYRA/MYRA_final.mp4 -[component_of]-> artifact:MYRA/MYRA_final.mp4"
    ]
