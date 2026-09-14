import json
import sqlite3

from flujo.knowledge.learning_policy import compile_dataset, fit_learning_policy, record_policy, record_verified_result
from flujo.knowledge.project_ir import LearningStore, build_project_ir


def _project(project_id: str, domain: str, format_family: str = "text"):
    suffix = "blend" if format_family == "3d" else "md"
    return build_project_ir(
        project_id=project_id,
        title=project_id,
        source_root="/tmp/learning-source",
        domains=[domain],
        artifacts=[{"relative_path": project_id + "/asset." + suffix, "format_family": format_family}],
        state="active",
        evidence=[{"kind": "fixture", "status": "verified"}],
    )


def _record(store: LearningStore, project_id: str, label: str) -> None:
    store.record_episode(
        project_id=project_id,
        objective="validated route",
        phase="consumer_probe",
        action={"decision": {"selected": {"tool_id": label}}},
        observation={"source": "fixture"},
        outcome={"status": "succeeded"},
        validation={"status": "passed", "check": "fixture"},
        status="succeeded",
        episode_id="episode-" + project_id,
    )


def test_unverified_episodes_do_not_become_labels(tmp_path):
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    project = _project("unknown-project", "research")
    store.save_project(project)
    store.record_episode(
        project_id=project["project_id"], objective="probe", phase="consumer_probe",
        action={"decision": {"selected": {"tool_id": "research_job_router"}}},
        observation={}, outcome={"status": "needs_evidence"},
        validation={"status": "needs_evidence"}, status="needs_evidence",
        episode_id="episode-unknown",
    )
    dataset = compile_dataset(database)
    result = fit_learning_policy(database)
    assert not dataset.examples
    assert result["status"] == "abstain"
    assert result["reason"] == "insufficient_verified_examples"
    assert result["excluded"] == {"episode_not_verified": 1}


def test_verified_examples_split_by_project_and_can_pass_gate(tmp_path):
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    for index in range(30):
        domain = "research" if index % 2 else "rd"
        label = "research_job_router" if domain == "research" else "blend_scene_audit"
        project = _project("project-" + str(index), domain, "text" if domain == "research" else "3d")
        store.save_project(project)
        _record(store, project["project_id"], label)
    result = fit_learning_policy(database)
    assert result["eligible_examples"] == 30
    assert result["evaluation"]["holdout_count"] >= 2
    assert result["status"] == "candidate"
    assert result["recordable"] is True
    assert result["evaluation"]["holdout_accuracy"] >= 0.60


def test_record_policy_persists_candidate_and_targeted_holdout_evaluation(tmp_path):
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    for index in range(30):
        domain = "research" if index % 2 else "rd"
        label = "research_job_router" if domain == "research" else "blend_scene_audit"
        project = _project("record-policy-project-" + str(index), domain, "text" if domain == "research" else "3d")
        store.save_project(project)
        _record(store, project["project_id"], label)
    result = fit_learning_policy(database)
    rule_id = record_policy(database, result)
    assert store.rules(status="candidate")[0]["rule_id"] == rule_id
    with sqlite3.connect(database) as con:
        row = con.execute(
            "SELECT target_kind,target_id,split_kind,status FROM learning_evaluations"
        ).fetchone()
    assert row == ("semantic_rule", rule_id, "holdout", "passed")
    assert store.rules(status="candidate")[0]["evaluation_id"] == "evaluation-policy-" + result["policy_version"]


def test_group_split_does_not_accidentally_leave_holdout_empty(tmp_path):
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    for index in range(5):
        domain = "research" if index % 2 else "rd"
        label = "research_job_router" if domain == "research" else "blend_scene_audit"
        project = _project("small-project-" + str(index), domain, "text" if domain == "research" else "3d")
        store.save_project(project)
        _record(store, project["project_id"], label)
    result = fit_learning_policy(database)
    evaluation = result.get("evaluation", result)
    assert evaluation["holdout_count"] >= 2
    assert len(evaluation.get("holdout_projects", [])) >= 2 or result.get("holdout_project_count", 0) >= 2


def test_holdout_label_missing_from_train_abstains_explicitly(tmp_path):
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    cases = [
        ("jardines-interpretativos-research", "research_job_router"),
        ("mak-research-capture-job4-20260820", "research_job_router"),
        ("mak-pnp-search-ecology-2026-08-19", "source_learning_bridge"),
        ("mak-tennis-decision-lab-fixture-20260820", "tennis_shot_event_consumer"),
        ("mak-research-simulation-candidate-20260820", "research_simulation_consumer"),
    ]
    for project_id, label in cases:
        project = _project(project_id, "research", "text")
        store.save_project(project)
        _record(store, project["project_id"], label)
    result = fit_learning_policy(database)
    assert result["status"] == "abstain"
    assert result["reason"] == "no_independent_holdout"


def test_verified_result_adapter_requires_validator_and_is_idempotent(tmp_path):
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    project = _project("verified-project", "rd", "3d")
    store.save_project(project)
    packet = tmp_path / "verified-result.json"
    packet.write_text(json.dumps({
        "schema": "mak-verified-result-v1",
        "project_id": project["project_id"],
        "tool_id": "blend_scene_audit",
        "episode_id": "episode-verified-result",
        "result": {"status": "verified", "artifact": "render_manifest.json"},
        "validation": {"status": "passed", "validator": "fixture-validator", "checks": ["manifest", "artifact"]},
        "evidence": [{"kind": "manifest", "ref": "render_manifest.json"}],
    }), encoding="utf-8")
    first = record_verified_result(database, packet)
    second = record_verified_result(database, packet)
    assert first == second == "episode-verified-result"
    assert len(compile_dataset(database).examples) == 1

    bad = tmp_path / "bad-result.json"
    bad.write_text(json.dumps({
        "schema": "mak-verified-result-v1", "project_id": project["project_id"],
        "tool_id": "blend_scene_audit", "result": {"status": "success"},
        "validation": {"status": "passed"}, "evidence": [{"ref": "x"}],
    }), encoding="utf-8")
    try:
        record_verified_result(database, bad)
    except ValueError as exc:
        assert str(exc) == "verified_result_validator_checks_required"
    else:
        raise AssertionError("invalid verification packet was accepted")


def test_explicit_tool_path_with_route_check_becomes_a_known_label(tmp_path):
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    project = _project("explicit-route-project", "tennis", "data")
    store.save_project(project)
    store.record_episode(
        project_id=project["project_id"], objective="external projection",
        phase="projection", action={"tool": "tools/tennis_shot_events.py"},
        observation={}, outcome={"status": "verified"},
        validation={"status": "passed", "checks": ["project_ir_route"]},
        status="verified", episode_id="episode-explicit-route",
    )
    dataset = compile_dataset(database)
    assert len(dataset.examples) == 1
    assert dataset.examples[0].label == "tennis_shot_event_consumer"
