from __future__ import annotations

import pytest

from flujo.knowledge.canary import CanaryError, evaluate_canary, record_canary_evaluation
from flujo.knowledge.project_ir import LearningStore


CASES = [
    {
        "case_id": "canary-a",
        "project_id": "new-project-a",
        "group_id": "new-group-a",
        "expected_label": "source_learning_bridge",
        "source_refs": ["evidence/new-a.json"],
        "validator": {"kind": "reviewed_route_packet", "target": "new-a"},
        "validation": {"status": "passed", "checks": ["route_identity"]},
    },
    {
        "case_id": "canary-b",
        "project_id": "new-project-b",
        "group_id": "new-group-b",
        "expected_label": "blend_scene_audit",
        "source_refs": ["evidence/new-b.json"],
        "validator": {"kind": "reviewed_route_packet", "target": "new-b"},
        "validation": {"status": "verified", "checks": ["route_identity"]},
    },
]


def test_canary_requires_projects_outside_training_and_scores_explicit_labels():
    report = evaluate_canary(
        CASES,
        {"canary-a": "source_learning_bridge", "canary-b": "blend_scene_audit"},
        candidate_policy_id="policy-v1",
        training_project_ids={"old-project"},
        training_group_ids={"old-group"},
    )
    assert report["status"] == "passed"
    assert report["new_project_count"] == 2
    assert report["accuracy"] == 1.0
    with pytest.raises(CanaryError, match="project_in_training"):
        evaluate_canary(
            [{**CASES[0], "project_id": "old-project"}],
            {"canary-a": "source_learning_bridge"},
            candidate_policy_id="policy-v1", training_project_ids={"old-project"},
            training_group_ids={"old-group"},
        )
    with pytest.raises(CanaryError, match="group_in_training"):
        evaluate_canary(
            [{**CASES[0], "group_id": "old-group"}],
            {"canary-a": "source_learning_bridge"},
            candidate_policy_id="policy-v1", training_project_ids={"old-project"},
            training_group_ids={"old-group"},
        )


def test_canary_abstention_is_distinct_and_can_be_recorded_as_evidence(tmp_path):
    report = evaluate_canary(
        CASES, {"canary-a": "source_learning_bridge"},
        candidate_policy_id="policy-v1", training_project_ids={"old-project"},
        training_group_ids={"old-group"},
    )
    assert report["status"] == "abstained"
    store = LearningStore(tmp_path / "learning.sqlite")
    evaluation_id = record_canary_evaluation(
        store.database, report, target_kind="semantic_rule", target_id="rule-candidate",
        evaluation_id="evaluation-canary",
    )
    assert evaluation_id == "evaluation-canary"
    assert store.rules() == []


def test_canary_requires_declared_labels_and_nonempty_training_population():
    with pytest.raises(CanaryError, match="expected_label"):
        evaluate_canary(
            [{**CASES[0], "expected_label": ""}], {"canary-a": "x"},
            candidate_policy_id="policy-v1", training_project_ids={"old-project"},
            training_group_ids={"old-group"},
        )
    with pytest.raises(CanaryError, match="training_population"):
        evaluate_canary(
            CASES, {}, candidate_policy_id="policy-v1", training_project_ids=set(),
            training_group_ids={"old-group"},
        )
    with pytest.raises(CanaryError, match="missing_validator"):
        evaluate_canary(
            [{**CASES[0], "validator": {}}], {"canary-a": "x"},
            candidate_policy_id="policy-v1", training_project_ids={"old-project"},
            training_group_ids={"old-group"},
        )
