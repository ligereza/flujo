from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.practice_evidence_state import (
    PracticeEvidenceStateError,
    build_practice_evidence_state,
    deserialize_practice_evidence_state,
    serialize_practice_evidence_state,
    validate_practice_evidence_state,
)


def _record(project_id: str, *, claim_without_refs: bool = False, dimensions: bool = True) -> dict:
    claim = {"claim_id": f"claim:{project_id}", "statement": "declared practice", "status": "candidate"}
    if not claim_without_refs:
        claim["evidence_refs"] = [f"artifact:{project_id}:a"]
    record = {
        "schema": "mak-project-ir-v1",
        "project_id": project_id,
        "title": "A title is not a claim",
        "state": "candidate",
        "source": {"kind": "archive_unit_reconstruction", "root_ref": "/not/read"},
        "purpose": "provisional",
        "domains": ["archive"],
        "artifacts": [
            {
                "artifact_id": f"artifact:{project_id}:a",
                "artifact_ref": f"artifact:{project_id}:a",
                "physical_id": f"physical:{project_id}:a",
                "content_id": "content:same",
                "relative_path": "work/a.bin",
                "availability": "available",
            },
            {
                "artifact_id": f"artifact:{project_id}:b",
                "artifact_ref": f"artifact:{project_id}:b",
                "physical_id": f"physical:{project_id}:b",
                "content_id": "content:same",
                "relative_path": "work/copy.bin",
                "availability": "available",
            },
        ],
        "relations": [
            {
                "relation_id": f"dep:{project_id}",
                "subject": project_id,
                "predicate": "provisional_dependency",
                "object": f"artifact:{project_id}:b",
                "status": "provisional",
                "evidence_refs": [f"artifact:{project_id}:b"],
            }
        ],
        "evidence": [],
        "unknowns": [],
        "next_action": "preserve_provisional_status",
        "provenance": {"producer": "fixture", "method": "fixture"},
        "archive_id": "archive-fixture",
        "snapshot_id": "snapshot-fixture",
        "input_hash": "sha256:fixture-input",
        "archive_unit": {
            "unit_id": f"unit:{project_id}",
            "role": "project_unit",
            "status": "provisional_unit",
            "member_refs": [f"artifact:{project_id}:a", f"artifact:{project_id}:b"],
            "dependency_refs": [f"artifact:{project_id}:b"],
            "candidate_ids": [],
            "evidence_for": ["fixture_declared"],
            "evidence_against": [],
            "alternatives": [],
            "missing_evidence": [],
        },
    }
    if claim_without_refs:
        record["claims"] = [claim]
    else:
        record["claims"] = [claim]
    if dimensions:
        record["media"] = [{"value": "audio", "status": "supported", "evidence_refs": [f"artifact:{project_id}:a"]}]
        record["capabilities"] = [{"value": "declared_tooling", "status": "candidate", "evidence_refs": [f"artifact:{project_id}:a"]}]
        record["temporality"] = [{"value": "period:2026", "status": "candidate", "evidence_refs": [f"artifact:{project_id}:a"]}]
        record["manifestations"] = [{"value": "output_ref", "status": "candidate", "evidence_refs": [f"artifact:{project_id}:b"]}]
        record["resources"] = [{"value": "shared_resource_ref", "status": "candidate", "evidence_refs": [f"artifact:{project_id}:b"]}]
    return record


def _bundle(*records: dict, ambiguous=None, unassigned=None) -> dict:
    return {
        "schema": "mak-archive-project-ir-bundle-v1",
        "source_unit_schema": "mak-archive-unit-reconstruction-v1",
        "target_project_ir_schema": "mak-project-ir-v1",
        "algorithm_version": "archive-units-to-project-ir-1",
        "archive_id": "archive-fixture",
        "snapshot_id": "snapshot-fixture",
        "input_hash": "sha256:fixture-input",
        "relation_hash": "sha256:relation-fixture",
        "records": list(records),
        "unit_project_map": [],
        "ambiguous_refs": sorted(ambiguous or []),
        "unassigned_refs": sorted(unassigned or []),
        "reconciliation": {},
    }


def test_order_is_irrelevant_and_source_is_not_mutated() -> None:
    first = _record("b")
    second = _record("a")
    source = _bundle(first, second, ambiguous=["artifact:amb"], unassigned=["artifact:none"])
    before = copy.deepcopy(source)
    left = build_practice_evidence_state(source)
    right = build_practice_evidence_state(_bundle(second, first, ambiguous=["artifact:amb"], unassigned=["artifact:none"]))
    assert source == before
    assert left == right
    assert left["state_hash"] == right["state_hash"]
    assert left["units"] == sorted(left["units"], key=lambda row: row["unit_id"])
    assert left["ambiguous_refs"] == ["artifact:amb"]
    assert left["unassigned_refs"] == ["artifact:none"]


def test_exact_duplicate_content_keeps_two_physical_artifacts() -> None:
    state = build_practice_evidence_state(_bundle(_record("one")))
    rows = state["units"][0]["artifact_refs"]
    assert rows == ["artifact:one:a", "artifact:one:b"]
    assert [row["physical_id"] for row in state["artifacts"]] == [
        "physical:one:a", "physical:one:b"
    ]
    assert {row["content_id"] for row in state["artifacts"]} == {"content:same"}
    assert state["reconciliation"]["duplicate_content_groups"] == 1
    assert state["reconciliation"]["duplicate_physical_refs_collapsed"] is False


def test_explicit_opportunity_requirements_are_preserved_and_sorted() -> None:
    record = _record("one")
    record["claims"][0]["requirement_ids"] = ["req:z", "req:a", "req:z"]
    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        record[dimension][0]["supports"] = ["req:z", "req:a", "req:z"]
    state = build_practice_evidence_state(_bundle(record))
    assert state["claims"]["candidate"][0]["requirement_ids"] == ["req:a", "req:z"]
    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        assert state[dimension][0]["requirement_ids"] == ["req:a", "req:z"]

    reordered = copy.deepcopy(record)
    reordered["claims"][0]["requirement_ids"].reverse()
    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        reordered[dimension][0]["supports"].reverse()
    assert state == build_practice_evidence_state(_bundle(reordered))


def test_requirement_links_are_not_inferred_from_values_or_text() -> None:
    record = _record("one")
    record["purpose"] = "supports req:looks-similar only in prose"
    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        record[dimension][0]["value"] = "req:looks-similar"
    state = build_practice_evidence_state(_bundle(record))
    assert state["claims"]["candidate"][0]["requirement_ids"] == []
    assert all(
        row["requirement_ids"] == []
        for dimension in ("media", "capabilities", "temporality", "manifestations", "resources")
        for row in state[dimension]
    )


def test_requirement_ids_validation_fails_closed() -> None:
    state = build_practice_evidence_state(_bundle(_record("one")))
    tampered = copy.deepcopy(state)
    tampered["media"][0]["requirement_ids"] = ["req:z", "req:a"]
    assert "media_requirement_ids_not_sorted_unique" in validate_practice_evidence_state(tampered)


def test_claim_without_evidence_abstains_to_unknown() -> None:
    state = build_practice_evidence_state(_bundle(_record("one", claim_without_refs=True)))
    assert len(state["claims"]["unknown"]) == 1
    assert not state["claims"]["supported"]
    assert any(gap["code"] == "claim_without_evidence_refs" for gap in state["gaps"])
    assert any(item["code"] == "claim_without_evidence_refs" for item in state["abstentions"])


def test_missing_dimensions_are_empty_and_explicitly_abstained() -> None:
    state = build_practice_evidence_state(_bundle(_record("one", dimensions=False)))
    for dimension in ("media", "capabilities", "temporality", "manifestations", "resources"):
        assert state[dimension] == []
        assert {gap.get("dimension") for gap in state["gaps"] if gap["code"] == "dimension_unobserved"} >= {dimension}


def test_standalone_records_and_json_round_trip() -> None:
    state = build_practice_evidence_state([_record("one")])
    encoded = serialize_practice_evidence_state(state)
    restored = deserialize_practice_evidence_state(encoded)
    assert restored == state
    assert validate_practice_evidence_state(restored) == []


def test_truth_status_is_not_promoted() -> None:
    record = _record("one")
    record["claims"] = [{"statement": "never promote", "status": "verified", "evidence_refs": ["artifact:one:a"]}]
    state = build_practice_evidence_state(_bundle(record))
    assert state["claims"]["supported"] == []
    assert state["claims"]["unknown"][0]["status"] == "unknown"
    assert any(gap["code"] == "truth_promotion_blocked" for gap in state["gaps"])
    assert "verified" not in json.dumps(state, ensure_ascii=False).casefold()


def test_cli_stdin_stdout_and_output_file(tmp_path: Path) -> None:
    payload = json.dumps(_bundle(_record("one")), ensure_ascii=False)
    command = [sys.executable, "tools/compile_practice_evidence_state.py"]
    result = subprocess.run(command, input=payload, text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)["schema"] == "mak-practice-evidence-state-v1"
    output = tmp_path / "state.json"
    result = subprocess.run(command + ["--output", str(output)], input=payload, text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert json.loads(output.read_text(encoding="utf-8"))["state_hash"].startswith("sha256:")


def test_malformed_input_fails_closed() -> None:
    with pytest.raises(PracticeEvidenceStateError):
        build_practice_evidence_state({"schema": "mak-project-ir-v1"})
