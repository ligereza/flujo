"""Tests for the bounded MAK Learn v2 director."""

from __future__ import annotations

import pytest

from flujo.knowledge.director import DirectorError, MakDirector
from flujo.knowledge.project_ir import LearningStore, build_project_ir, inventory_source
from flujo.knowledge.project_router import ROUTER_SCHEMA


def _fixture(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "notes.md").write_text("director fixture\n", encoding="utf-8")
    store = LearningStore(tmp_path / "learning.sqlite")
    project = build_project_ir(
        project_id="director-demo", title="Director demo", source_root=root,
        artifacts=inventory_source(root), state="candidate",
    )
    store.save_project(project)
    decision = {
        "schema": ROUTER_SCHEMA,
        "project_id": "director-demo",
        "decision": "select",
        "selected": {
            "tool_id": "source_learning_bridge",
            "mode": "read_only",
        },
        "candidates": [],
        "reason": "fixture",
    }
    director = MakDirector(
        store, repo_root=tmp_path, source_snapshot_hash="sha256:source",
        code_commit="abc1234", tool_versions={"python": "3.12"},
    )
    return store, project, decision, director


def test_director_persists_full_checkpoint_chain_and_episode(tmp_path):
    store, project, decision, director = _fixture(tmp_path)
    result = director.run_read_only_probe(project, decision, run_id="run-director-demo")

    assert result["run"]["state"] == "recorded"
    assert result["run"]["episode_id"]
    assert [event["state"] for event in result["events"]["events"]] == [
        "proposed", "running", "observed", "validated", "recorded",
    ]
    assert result["events"]["state"] == "recorded"
    assert store.summary("director-demo")["episodes"] == {"needs_evidence": 1}
    with store.connect() as con:
        row = con.execute(
            "SELECT source_snapshot_hash,code_commit,tool_versions_json FROM project_episodes"
        ).fetchone()
    assert tuple(row) == ("sha256:source", "abc1234", '{"python":"3.12"}')


def test_director_attaches_replay_gate_and_reconstructs_checkpoint(tmp_path):
    store, project, decision, director = _fixture(tmp_path)
    evaluation = {
        "status": "passed",
        "dataset_fingerprint": "sha256:replay",
        "suite_id": "fixture-suite",
    }
    result = director.run_read_only_probe(
        project, decision, run_id="run-gated", replay_evaluation=evaluation,
    )
    assert result["run"]["replay_gate"] == "passed"
    resumed = director.resume("run-gated")
    assert resumed["checkpoint"]["resumable"] is False
    assert resumed["run"]["state"] == "recorded"
    assert resumed["run"]["replay_evaluation"]["suite_id"] == "fixture-suite"


def test_director_rejects_unknown_or_mutating_tools_before_persisting(tmp_path):
    store, project, decision, director = _fixture(tmp_path)
    bad = {**decision, "selected": {"tool_id": "shell", "mode": "read_only"}}
    with pytest.raises(DirectorError, match="not_allowlisted"):
        director.propose(project, bad, run_id="run-bad")

    plan_only = {**decision, "selected": {"tool_id": "research_job_router", "mode": "plan_only"}}
    with pytest.raises(DirectorError, match="not_allowlisted"):
        director.propose(project, plan_only, run_id="run-plan-only")
    assert store.run_events("run-bad") == []
    assert store.run_events("run-plan-only") == []


def test_director_rejects_invalid_transition_and_tool_mismatch(tmp_path):
    store, project, decision, director = _fixture(tmp_path)
    run = director.propose(project, decision, run_id="run-transition")
    with pytest.raises(DirectorError, match="invalid_transition"):
        director.validate(run)
    run = director.start(run)
    with pytest.raises(DirectorError, match="tool_mismatch"):
        director.observe(run, {
            "status": "needs_evidence",
            "tool_id": "deep_learning_gate",
            "validation": {"status": "not_run"},
        })


def test_director_recovery_plan_is_read_only_and_requires_reprobe(tmp_path):
    store, project, decision, director = _fixture(tmp_path)
    run = director.propose(project, decision, run_id="run-recovery")
    run = director.start(run)
    plan = director.recovery_plan("run-recovery")
    assert plan["state"] == "running"
    assert plan["action"] == "reprobe_required"
    assert plan["mutated"] is False
    assert len(store.run_events("run-recovery")) == 2


def test_director_cannot_record_failed_validation(tmp_path):
    store, project, decision, director = _fixture(tmp_path)
    run = director.propose(project, decision, run_id="run-failed-validation")
    run = director.start(run)
    run = director.observe(run, {
        "status": "failed", "tool_id": "source_learning_bridge",
        "validation": {"status": "failed"},
    })
    run = director.validate(run)
    assert director.recovery_plan("run-failed-validation")["action"] == "quarantine_failed_validation"
    with pytest.raises(DirectorError, match="validation_failed"):
        director.record(run, project)
