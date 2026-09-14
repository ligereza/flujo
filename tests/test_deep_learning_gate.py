"""Tests for the pre-training evidence gate."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from flujo.knowledge.deep_learning_gate import evaluate_manifest
from flujo.knowledge.project_ir import build_project_ir
from flujo.knowledge.project_router import route_project


ROOT = Path(__file__).resolve().parents[1]


def _manifest(validator_path: str = "validator.py") -> dict[str, object]:
    return {
        "schema": "mak-deep-learning-task-gate-v1",
        "task_id": "fixture-shot-classification",
        "project_id": "tennis-learning-fixture",
        "objective": "classify annotated shot type",
        "input_ref": "data/frames.parquet",
        "label_ref": "data/labels.jsonl",
        "split": {
            "train_ref": "data/train.jsonl",
            "holdout_ref": "data/holdout.jsonl",
            "independent": True,
            "group_key": "match_id",
            "holdout_count": 4,
        },
        "validator": {"path": validator_path, "status": "ready"},
    }


def test_eligible_manifest_is_still_not_training_authorization(tmp_path: Path) -> None:
    (tmp_path / "validator.py").write_text("# deterministic fixture validator\n", encoding="utf-8")
    manifest = _manifest()
    Draft202012Validator(json.loads((ROOT / "schemas/knowledge/deep_learning_task_gate.schema.json").read_text())).validate(manifest)
    result = evaluate_manifest(manifest, root=tmp_path)
    assert result["decision"] == "eligible"
    assert result["training_permitted"] is False
    assert result["evidence"]["independent_holdout"] is True


def test_missing_independent_holdout_abstains(tmp_path: Path) -> None:
    (tmp_path / "validator.py").write_text("# fixture\n", encoding="utf-8")
    manifest = _manifest()
    manifest["split"] = {**manifest["split"], "independent": False}  # type: ignore[index]
    result = evaluate_manifest(manifest, root=tmp_path)
    assert result["decision"] == "abstain"
    assert "holdout_not_independent" in result["errors"]


def test_project_ir_routes_learning_data_to_the_gate(tmp_path: Path) -> None:
    project = build_project_ir(
        project_id="learning-fixture",
        title="Learning fixture",
        source_root=tmp_path,
        domains=("deep_learning",),
        state="active",
        evidence=({"kind": "labels", "status": "observed"},),
        artifacts=({"relative_path": "frames.parquet", "format_family": "data"},),
    )
    decision = route_project(project)
    assert decision["decision"] == "select"
    assert decision["selected"]["tool_id"] == "deep_learning_gate"
