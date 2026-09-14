import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.opportunity_constraints import compile_opportunity_constraints
from flujo.knowledge.opportunity_fit import evaluate_opportunity_fit
from flujo.knowledge.practice_evidence_state import build_practice_evidence_state


def opportunity(constraints, *, criteria=None, hard_gates=None, contradictions=None, source=None):
    return {
        "schema": "mak-opportunity-constraints-v1",
        "opportunity_id": "fondart-2027-investigacion",
        "constraints": constraints,
        "hard_gates": hard_gates or [],
        "criteria": criteria if criteria is not None else [],
        "contradictions": contradictions or [],
        "source": source or {"validity": {"status": "current_verified", "confirmed": True}},
    }


def practice_state(rows=None):
    rows = rows or []
    return {
        "schema": "mak-practice-evidence-state-v1",
        "tenant": "mak",
        "archive_id": "archive-fixture",
        "snapshot_id": "snapshot-fixture",
        "units": [],
        "artifacts": [{"artifact_ref": "artifact:only"}],
        "claims": {"supported": rows, "candidate": [], "unknown": []},
        "media": [],
        "capabilities": [],
        "temporality": [],
        "manifestations": [],
        "resources": [],
        "dependencies": [],
        "provenance": {"source_rescan": False},
        "gaps": [],
    }


def constraint(rid, field, **extra):
    return {"constraint_id": rid, "field": field, "kind": "criterion", "required": True, "value": None, "status": "unknown", "evidence_refs": [], "locator_refs": [], **extra}


def criteria(*pairs):
    return [{"criterion_id": f"criterion:{field}", "field": field, "weight": weight} for field, weight in pairs]


def claim(ref, status="supported", provenance="unit:u", requirement_ids=None):
    row = {"claim_id": f"claim:{ref}", "status": status, "statement": ref, "evidence_refs": [ref], "provenance_ref": provenance}
    if requirement_ids is not None:
        row["requirement_ids"] = requirement_ids
    return row


def test_matrix_coverage_and_unknown_are_separate():
    result = evaluate_opportunity_fit(
        opportunity([constraint("c1", "trayectoria", evidence_refs=["e1"]), constraint("c2", "metodologia")], criteria=criteria(("trayectoria", 0.25), ("metodologia", 0.75))),
        practice_state([claim("e1", requirement_ids=["c1"])]),
    )
    assert result["decision"] == "abstain"
    assert result["weighted_coverage"] == 0.25
    assert [row["status"] for row in result["matrix"]] == ["supported", "missing"]
    assert result["practice_identity"] == "practice:mak:archive-fixture:snapshot-fixture"


def test_missing_hard_gate_abstains_closed():
    result = evaluate_opportunity_fit(
        opportunity([constraint("gate", "residencia")], criteria=criteria(("residencia", 1)), hard_gates=["gate"]),
        practice_state(),
    )
    assert result["hard_gate_status"] == "abstain"
    assert result["decision"] == "abstain"


def test_opportunity_contradiction_fails_closed_but_is_not_practice_evidence():
    result = evaluate_opportunity_fit(
        opportunity([constraint("gate", "condicion")], criteria=criteria(("condicion", 1)), hard_gates=["gate"], contradictions=[{"constraint_id": "gate"}]),
        practice_state(),
    )
    assert result["hard_gate_status"] == "fail"
    assert result["decision"] == "contradicted"
    assert result["allowed_claims"] == []


def test_non_gate_contradiction_does_not_fail_unrelated_hard_gate():
    result = evaluate_opportunity_fit(
        opportunity(
            [constraint("gate", "condicion", kind="hard_gate", evidence_refs=[]), constraint("other", "otro", kind="criterion")],
            criteria=criteria(("otro", 1)), hard_gates=["gate"], contradictions=[{"constraint_id": "other"}],
        ),
        practice_state([claim("gate-evidence", requirement_ids=["gate"])]),
    )
    assert result["hard_gate_status"] == "pass"
    assert result["decision"] == "contradicted"


def test_source_validity_abstains_even_when_practice_supports():
    result = evaluate_opportunity_fit(
        opportunity([constraint("c1", "criterio", evidence_refs=["pdf:c1"])], criteria=criteria(("criterio", 1)), source={"validity": {"status": "observed_local", "confirmed": False}}),
        practice_state([claim("internal:c1", requirement_ids=["c1"])]),
    )
    assert result["matrix"][0]["status"] == "supported"
    assert result["source_gate_status"] == "abstain"
    assert result["decision"] == "abstain"


def test_expired_source_fails_closed():
    result = evaluate_opportunity_fit(
        opportunity([constraint("c1", "criterio")], criteria=criteria(("criterio", 1)), source={"validity": {"status": "expired", "confirmed": True}}),
        practice_state([claim("internal:c1", requirement_ids=["c1"])]),
    )
    assert result["source_gate_status"] == "fail"
    assert result["decision"] == "contradicted"


def test_unweighted_hard_gate_does_not_enter_criteria_coverage():
    result = evaluate_opportunity_fit(
        opportunity(
            [constraint("score", "criterio", evidence_refs=["pdf:score"]), constraint("gate", "elegibilidad", kind="hard_gate")],
            criteria=criteria(("criterio", 1)), hard_gates=["gate"],
        ),
        practice_state([claim("internal:score", requirement_ids=["score"]), claim("internal:gate", requirement_ids=["gate"])]),
    )
    assert result["weighted_coverage"] == 1
    assert result["coverage_reason"] == "criteria_complete_and_unambiguous"


def test_zero_cost_is_explicit_and_never_dispatched():
    result = evaluate_opportunity_fit(
        opportunity([constraint("c1", "dato", research={"cost": 0, "time": 0, "risk_avoided": 2})], criteria=criteria(("dato", 1))),
        practice_state(),
    )
    candidate = result["research_job_candidates"][0]
    assert candidate["voi"] is None
    assert candidate["voi_status"] == "undefined_zero_cost"
    assert candidate["dispatched"] is False


def test_incomplete_weights_abstain_without_defaulting():
    result = evaluate_opportunity_fit(opportunity([constraint("c1", "sin_peso")]), practice_state())
    assert result["decision"] == "abstain"
    assert result["validation"]["valid"] is True
    assert result["weighted_coverage"] is None
    assert result["coverage_reason"] == "criteria_weight_status:incomplete_weights"


def test_missing_evidence_ref_is_explicit():
    result = evaluate_opportunity_fit(
        opportunity([constraint("c1", "referencia", evidence_refs=["does-not-exist"])], criteria=criteria(("referencia", 1))),
        practice_state(),
    )
    assert result["decision"] == "abstain"
    assert result["validation"]["errors"] == []
    assert result["matrix"][0]["status"] == "missing"
    assert result["matrix"][0]["cells"] == []


def test_artifact_ref_alone_is_not_support():
    result = evaluate_opportunity_fit(
        opportunity([constraint("c1", "archivo", evidence_refs=["artifact:only"])], criteria=criteria(("archivo", 1))),
        practice_state(),
    )
    assert result["matrix"][0]["status"] == "missing"


def test_one_receipt_may_support_multiple_claims_without_identity_collision():
    shared = "receipt:shared"
    rows = [
        {**claim(shared, requirement_ids=["c1"]), "claim_id": "claim:first"},
        {**claim(shared, requirement_ids=["c1"]), "claim_id": "claim:second"},
    ]
    result = evaluate_opportunity_fit(
        opportunity([constraint("c1", "criterio")], criteria=criteria(("criterio", 1))),
        practice_state(rows),
    )
    assert result["validation"] == {"valid": True, "errors": []}
    assert result["matrix"][0]["status"] == "supported"


def test_candidates_are_sorted_by_explainable_voi():
    constraints = [
        constraint("low", "baja", research={"resolution_probability": 0.5, "utility_delta": 1, "cost": 2, "time": 2}),
        constraint("high", "alta", research={"resolution_probability": 1, "utility_delta": 4, "cost": 1, "time": 1}),
    ]
    result = evaluate_opportunity_fit(opportunity(constraints, criteria=criteria(("baja", 0.5), ("alta", 0.5))), practice_state())
    assert [item["requirement_id"] for item in result["research_job_candidates"]] == ["high", "low"]


def _project_ir_bundle():
    record = {
        "schema": "mak-project-ir-v1", "project_id": "p1", "title": "Fixture", "state": "candidate",
        "source": {"kind": "fixture", "root_ref": "/not/read"}, "purpose": "provisional", "domains": ["archive"],
        "artifacts": [{"artifact_id": "artifact:p1:a", "artifact_ref": "artifact:p1:a", "physical_id": "physical:p1:a", "content_id": "content:a", "relative_path": "a.bin", "availability": "available"}],
        "relations": [], "evidence": [], "unknowns": [], "next_action": "preserve_provisional_status",
        "provenance": {"producer": "fixture", "method": "fixture"}, "archive_id": "archive-fixture", "snapshot_id": "snapshot-fixture", "input_hash": "sha256:fixture-input",
        "archive_unit": {"unit_id": "unit:p1", "role": "project_unit", "status": "provisional_unit", "member_refs": ["artifact:p1:a"], "dependency_refs": [], "candidate_ids": [], "evidence_for": [], "evidence_against": [], "alternatives": [], "missing_evidence": []},
        "claims": [{"claim_id": "claim:p1", "statement": "declared practice", "status": "candidate", "evidence_refs": ["artifact:p1:a"], "requirement_ids": ["criterion:audio"]}],
        "media": [{"value": "audio", "status": "supported", "evidence_refs": ["artifact:p1:a"], "requirement_ids": ["criterion:audio"]}],
        "capabilities": [], "temporality": [], "manifestations": [], "resources": [],
    }
    return {"schema": "mak-archive-project-ir-bundle-v1", "source_unit_schema": "mak-archive-unit-reconstruction-v1", "target_project_ir_schema": "mak-project-ir-v1", "algorithm_version": "archive-units-to-project-ir-1", "archive_id": "archive-fixture", "snapshot_id": "snapshot-fixture", "input_hash": "sha256:fixture-input", "relation_hash": "sha256:relation-fixture", "records": [record], "unit_project_map": [], "ambiguous_refs": [], "unassigned_refs": [], "reconciliation": {}}


def test_real_stage2d_to_practice_state_to_fit_integration():
    practice = build_practice_evidence_state(_project_ir_bundle())
    opportunity_payload = {
        "schema": "mak-opportunity-document-package-v1", "opportunity_id": "fondart-2027-investigacion", "title": "Fondart",
        "source": {"ref": "local:bases", "content": "fixture", "version": "v1", "validity": {"status": "observed_local", "confirmed": False}},
        "requirements": [{"id": "criterion:audio", "kind": "criterion", "field": "media", "evidence_refs": ["pdf:media-requirement"]}],
        "evidence": [{"evidence_id": "pdf:media-requirement", "kind": "criterion", "field": "media", "value": "audio", "weight": 1, "locator": {"page": 1}}],
    }
    compiled = compile_opportunity_constraints(opportunity_payload)
    fit = evaluate_opportunity_fit(compiled, practice)
    assert "practice_id" not in practice and "evidence" not in practice
    internal_rows = practice["media"] + practice["claims"]["candidate"]
    if not any("requirement_ids" in row for row in internal_rows):
        pytest.fail("Stage 1B no preserva requirement_ids/supports en mak-practice-evidence-state-v1")
    assert fit["practice_identity"] == "practice:mak:archive-fixture:snapshot-fixture"
    assert fit["matrix"][0]["status"] == "supported"


def test_cli_emits_json_and_supports_output_file(tmp_path):
    opportunity_path = tmp_path / "opportunity.json"
    practice_path = tmp_path / "practice.json"
    output_path = tmp_path / "fit.json"
    opportunity_path.write_text(json.dumps(opportunity([constraint("c1", "archivo")], criteria=criteria(("archivo", 1)))), encoding="utf-8")
    practice_path.write_text(json.dumps(practice_state()), encoding="utf-8")
    command = [sys.executable, "tools/evaluate_opportunity_fit.py", str(opportunity_path), str(practice_path), "--output", str(output_path)]
    completed = subprocess.run(command, cwd=Path(__file__).parents[1], capture_output=True, text=True)
    assert completed.returncode == 0
    assert json.loads(output_path.read_text(encoding="utf-8"))["schema"] == "mak-opportunity-fit-v1"
