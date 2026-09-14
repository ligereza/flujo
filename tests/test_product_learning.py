from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.product_learning import (
    ProductLearningError,
    assert_product_learning,
    compile_learning_dataset,
    evaluate_product_learning,
    stable_json,
    validate_product_learning,
)


ROOT = Path(__file__).resolve().parents[1]


def _episode(
    episode_id: str,
    archive_id: str,
    artist_identity: str,
    *,
    signal: str = "ranking",
    action: str = "research",
    outcome: str = "success",
    status: str = "verified",
    baseline_action: str = "observe",
    alternatives: list[str] | None = None,
    counterfactuals: dict | None = None,
) -> dict:
    return {
        "schema": "mak-product-episode-candidate-v1",
        "episode_id": episode_id,
        "decision": {
            "signal": signal,
            "action": action,
            "baseline_action": baseline_action,
            "alternatives": alternatives or ["wait"],
            "context": {"source_validity": "current_verified", "gap_count": 0},
        },
        "observation": {
            "archive_id": archive_id,
            "artist_identity": artist_identity,
            "snapshot_id": "snapshot:" + archive_id,
            "evidence_refs": ["observation:" + episode_id],
        },
        "outcome": {
            "status": outcome,
            "external": True,
            "evidence_refs": ["external:" + episode_id],
            "counterfactuals": counterfactuals or {},
        },
        "validation": {
            "status": "verified",
            "external_verified": True,
            "checks": ["external_outcome", "binding"],
            "evidence_refs": ["validator:" + episode_id],
        },
        "learning_gate": {
            "status": "eligible",
            "signals": [signal],
            "training_permitted": False,
        },
        "control": {
            "promotion": "none",
            "training_permitted": False,
            "dispatch": False,
        },
        "provenance": {
            "archive_id": archive_id,
            "artist_identity": artist_identity,
            "snapshot_id": "snapshot:" + archive_id,
            "source_refs": ["source:" + episode_id],
        },
    }


def _verified_examples() -> list[dict]:
    rows: list[dict] = []
    cases = [
        ("e-a1", "archive:a", "artist:a", "success"),
        ("e-a2", "archive:a", "artist:a", "success"),
        ("e-b1", "archive:b", "artist:b", "failure"),
        ("e-b2", "archive:b", "artist:b", "failure"),
        ("e-c1", "archive:c", "artist:c", "success"),
        ("e-c2", "archive:c", "artist:c", "success"),
        ("e-d1", "archive:d", "artist:d", "failure"),
        ("e-d2", "archive:d", "artist:d", "failure"),
    ]
    for episode_id, archive_id, artist_identity, outcome in cases:
        rows.append(_episode(
            episode_id, archive_id, artist_identity, outcome=outcome,
            action="research" if outcome == "success" else "wait",
            signal="ranking" if outcome == "success" else "attention",
        ))
    return rows


def _real_product_episode(
    episode_id: str,
    group_id: str,
    *,
    eligible: bool,
    scopes: list[str] | None = None,
    label: str = "success",
) -> dict:
    scopes = scopes or ["ranking"]
    return {
        "schema": "mak-product-episode-candidate-v1",
        "algorithm_version": "product-episode-adapter-1",
        "status": "candidate" if eligible else "open",
        "episode_id": episode_id,
        "decision": {
            "kind": "common_product_plan_selection",
            "selected_program_ids": ["program:one"],
            "selected_product_ids": ["portfolio_dossier"],
            "target_statuses": {"portfolio_dossier": "draftable"},
        },
        "observation": {
            "status": "observed",
            "snapshot_id": "snapshot:" + episode_id,
            "identity_group": {
                "group_id": group_id,
                "stable": True,
                "snapshot_independent": True,
            },
            "practice_gates": {"truth_promotions": 0},
            "product_gates": {"portfolio_dossier": "draft_only"},
        },
        "outcome": {
            "status": "succeeded" if eligible else "unresolved",
            "eligible": eligible,
            "eligibility": "verified_external_receipt" if eligible else "not_observed",
            "source_refs": [{"ref": "external:" + episode_id, "sha256": "a" * 64}],
            "label_candidate": (
                {
                    "status": "candidate",
                    "label": label,
                    "signal_scopes": scopes,
                    "training_permitted": False,
                }
                if eligible else None
            ),
            "validation": {
                "status": "passed",
                "checks": ["binding", "source_digest", "external_receipt"],
            },
        },
        "learning_scope": ["attention", "query_selection", "ranking", "voi_calibration"],
        "control": {
            "promotion": "none",
            "training_permitted": False,
            "database_write": False,
        },
        "provenance": {
            "source_schemas": ["mak-product-plan-v1"],
            "deterministic": True,
            "training_permitted": False,
        },
        "record_episode_projection": {
            "validation": {
                "status": "passed" if eligible else "abstained",
                "checks": ["external_receipt", "binding", "source_digest"],
                "outcome_eligible": eligible,
            },
        },
    }


def test_few_episodes_abstain_without_policy_candidate() -> None:
    report = evaluate_product_learning(_verified_examples()[:2])
    assert report["status"] == "abstain"
    assert report["policy_candidate"] is False
    assert report["training_permitted"] is False
    assert report["split"]["independent"] is False
    assert "deep_learning_manifest_not_eligible" in report["warnings"]


def test_open_outcomes_are_excluded_not_negative() -> None:
    rows = _verified_examples()[:2]
    rows[0]["outcome"]["status"] = "open"
    rows[0]["outcome"].pop("external")
    rows[1]["outcome"]["status"] = "unknown"
    dataset = compile_learning_dataset(rows)
    assert dataset["eligible_count"] == 0
    assert dataset["excluded"]["outcome_open_not_negative"] == 2
    assert "failure" not in [row.get("label") for row in dataset["examples"]]


def test_real_5a_open_episode_is_valid_abstention_without_structural_error() -> None:
    report = evaluate_product_learning([
        _real_product_episode("episode:open", "identity:artist-a", eligible=False),
    ])
    assert report["valid"] is True
    assert report["status"] == "abstain"
    assert report["dataset"]["eligible_count"] == 0
    assert report["dataset"]["excluded"]["outcome_open_not_negative"] == 1
    assert report["structural_errors"] == []
    assert report["errors"] == []


def test_real_5a_eligible_episode_uses_identity_group_and_label_scopes_only() -> None:
    report = evaluate_product_learning([
        _real_product_episode(
            "episode:eligible", "identity:artist-a", eligible=True,
            scopes=["ranking", "attention"],
        ),
    ])
    assert report["valid"] is True
    assert report["dataset"]["eligible_count"] == 2
    assert report["dataset"]["group_key"] == "identity_group.group_id"
    assert {row["signal"] for row in report["dataset"]["examples"]} == {"ranking", "attention"}
    assert report["learning_features"]["signals"] == ["attention", "ranking"]
    assert report["deep_learning_manifest_candidate"]["signals"] == ["attention", "ranking"]
    assert report["dataset"]["examples"][0]["group_id"] == "identity:artist-a"
    assert report["training_permitted"] is False
    assert report["status"] == "abstain"  # one identity group cannot make an independent holdout
    assert assert_product_learning(report) is True


def test_real_5a_identity_group_excludes_snapshot_from_split_key() -> None:
    rows = [
        _real_product_episode("episode:snapshot-1", "identity:artist-a", eligible=True),
        _real_product_episode("episode:snapshot-2", "identity:artist-a", eligible=True),
    ]
    rows[1]["observation"]["snapshot_id"] = "snapshot:other"
    dataset = compile_learning_dataset(rows)
    assert {row["group_id"] for row in dataset["examples"]} == {"identity:artist-a"}
    assert dataset["group_key"] == "identity_group.group_id"


def test_real_5a_prohibited_scope_invalidates_the_batch() -> None:
    report = evaluate_product_learning([
        _real_product_episode(
            "episode:truth-scope", "identity:artist-a", eligible=True,
            scopes=["truth"],
        ),
    ])
    assert report["valid"] is False
    assert report["status"] == "abstain"
    assert report["dataset"]["eligible_count"] == 0
    assert "prohibited_learning_signal_in_input:truth" in report["errors"]


def test_verified_success_and_failure_are_explicit_labels() -> None:
    rows = _verified_examples()
    for row in rows:
        row["status"] = "candidate"
    report = evaluate_product_learning(rows)
    labels = {row["label"] for row in report["dataset"]["examples"]}
    assert labels == {"success", "failure"}
    assert report["dataset"]["eligible_count"] == 8
    assert report["dataset"]["identity_used_as_feature"] is False
    assert all(
        feature[0] not in {"truth", "authorship", "identity", "claim_status", "artistic_worth"}
        for row in report["dataset"]["examples"]
        for feature in row["features"]
    )


def test_group_split_never_leaks_archive_artist_group() -> None:
    rows = _verified_examples()
    rows.extend([
        _episode("e-a3", "archive:a", "artist:a", outcome="success"),
        _episode("e-d3", "archive:d", "artist:d", outcome="failure"),
    ])
    report = evaluate_product_learning(rows)
    train_groups = set(report["split"]["train_group_ids"])
    holdout_groups = set(report["split"]["holdout_group_ids"])
    assert train_groups.isdisjoint(holdout_groups)
    assert report["split"]["leakage_detected"] is False
    assert report["split"]["group_key"] == "archive_id+artist_identity"


def test_prohibited_truth_signal_fails_closed() -> None:
    rows = _verified_examples()
    rows[0]["decision"]["signal"] = "truth"
    report = evaluate_product_learning(rows)
    assert report["valid"] is False
    assert report["status"] == "abstain"
    assert report["dataset"]["eligible_count"] == 7
    assert report["dataset"]["excluded"]["prohibited_signal:truth"] == 1
    assert "truth" not in stable_json(report["dataset"]["examples"])
    with pytest.raises(ProductLearningError):
        assert_product_learning(report)


def test_deterministic_counterfactuals_and_no_mutation() -> None:
    rows = _verified_examples()
    rows[0]["outcome"]["counterfactuals"] = {
        "wait": {
            "status": "failure",
            "external": True,
            "evidence_refs": ["external:cf-a1"],
        }
    }
    original = copy.deepcopy(rows)
    first = evaluate_product_learning(rows)
    shuffled = list(reversed(copy.deepcopy(rows)))
    second = evaluate_product_learning(shuffled)
    assert first == second
    assert rows == original
    alternatives = {row["action"]: row for row in first["counterfactual_alternatives"]}
    assert alternatives["wait"]["status"] == "observed_external"
    assert alternatives["wait"]["training_permitted"] is False
    assert first["control"]["promotion"] == "none"
    assert assert_product_learning(first) is True
    assert validate_product_learning(first) == []


def test_binding_mismatch_is_excluded_fail_closed() -> None:
    rows = _verified_examples()
    rows[0]["provenance"]["archive_id"] = "archive:other"
    report = evaluate_product_learning(rows)
    assert report["dataset"]["eligible_count"] == 7
    assert report["dataset"]["excluded"]["archive_binding_mismatch"] == 1


def test_manifest_candidate_uses_deep_learning_gate_but_never_authorizes_training() -> None:
    report = evaluate_product_learning(_verified_examples())
    manifest = report["deep_learning_manifest_candidate"]
    assert manifest["schema"] == "mak-deep-learning-task-gate-v1"
    assert manifest["split"]["group_key"] == "archive_id+artist_identity"
    assert report["deep_learning_gate"]["training_permitted"] is False
    assert report["control"]["database_write"] is False
    assert report["control"]["policy_activation"] is False


def test_cli_reads_file_and_writes_stdout_or_output(tmp_path: Path) -> None:
    input_path = tmp_path / "episodes.json"
    input_path.write_text(json.dumps(_verified_examples()), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "tools/evaluate_product_learning.py", str(input_path)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    stdout_report = json.loads(result.stdout)
    assert stdout_report["schema"] == "mak-product-learning-evaluation-v1"
    output_path = tmp_path / "evaluation.json"
    written = subprocess.run(
        [sys.executable, "tools/evaluate_product_learning.py", "--input", str(input_path), "--output", str(output_path)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert written.returncode == 0
    assert written.stdout == ""
    assert json.loads(output_path.read_text(encoding="utf-8")) == stdout_report


def test_assert_rejects_mutated_training_authorization() -> None:
    report = evaluate_product_learning(_verified_examples())
    mutated = copy.deepcopy(report)
    mutated["training_permitted"] = True
    with pytest.raises(ProductLearningError):
        assert_product_learning(mutated)
