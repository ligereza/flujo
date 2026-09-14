from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.flujo.knowledge.opportunity_constraints import (
    ALGORITHM_VERSION,
    INPUT_SCHEMA,
    SCHEMA,
    OpportunityConstraintsError,
    compile_opportunity_constraints,
    stable_json,
    validate_opportunity_constraints,
)
from tools.compile_opportunity_constraints import main


def _package() -> dict:
    return {
        "schema": INPUT_SCHEMA,
        "opportunity_id": "fondart-investigacion-2027",
        "title": "Fondart Nacional Investigación 2027",
        "source": {
            "ref": "/home/mak/flujo/docs/recovered/claude_sessions_2026-08-12/raw/bases_pdf/fondart-nacional-investigacion-2027.pdf",
            "url": "https://www.fondosdecultura.cl/wp-content/uploads/2026/08/investigacion-fondart-nacional-2027.pdf",
            "content": "fondart-2027-local-snapshot-v1",
            "version": "2026-08-05",
            "validity": {"status": "observed_local", "confirmed": False},
        },
        "requirements": [
            {"id": "gate:field-study", "kind": "hard_gate", "field": "field_study_required", "evidence_refs": ["p2-field-study"]},
            {"id": "gate:transfer", "kind": "hard_gate", "field": "transfer_activity_required", "evidence_refs": ["p4-transfer"]},
            {"id": "date:start-window", "kind": "date", "field": "project_start_window", "evidence_refs": ["p4-start-window"]},
            {"id": "budget:group-a", "kind": "budget", "field": "group_a_budget", "evidence_refs": ["p5-budget"]},
            {"id": "document:advance", "kind": "required_document", "field": "advance_of_research", "evidence_refs": ["p27-advance"]},
        ],
        "evidence": [
            {"evidence_id": "p2-field-study", "kind": "hard_gate", "field": "field_study_required", "value": True, "locator": {"page": 2}},
            {"evidence_id": "p4-transfer", "kind": "hard_gate", "field": "transfer_activity_required", "value": True, "locator": {"page": 4}},
            {"evidence_id": "p4-start-window", "kind": "date", "field": "project_start_window", "value": {"start": "2027-03-01", "end": "2027-04-30"}, "locator": {"page": 4}},
            {"evidence_id": "p5-budget", "kind": "budget", "field": "group_a_budget", "value": {"min": 500000, "max": 15000000, "currency": "CLP"}, "locator": {"page": 5}},
            {"evidence_id": "p15-quality", "kind": "criterion", "field": "quality", "label": "Quality", "weight": 0.30, "locator": {"page": 15}},
            {"evidence_id": "p15-transfer-impact", "kind": "criterion", "field": "transfer_impact", "label": "Transfer impact", "weight": 0.40, "locator": {"page": 15}},
            {"evidence_id": "p27-advance", "kind": "required_document", "field": "advance_of_research", "value": {"pages": 15}, "locator": {"page": 27}},
        ],
    }


def test_compiles_realistic_fondart_constraints_and_is_deterministic() -> None:
    package = _package()
    first = compile_opportunity_constraints(package)
    second = compile_opportunity_constraints(copy.deepcopy(package))
    assert first == second
    assert stable_json(first) == stable_json(second)
    assert first["schema"] == SCHEMA
    assert first["algorithm_version"] == ALGORITHM_VERSION
    assert first["source"]["validity"]["status"] == "observed_local"
    assert first["source"]["source_hash"].startswith("sha256:")
    assert first["hard_gates"] == ["gate:field-study", "gate:transfer"]
    assert first["dates"] == ["date:start-window"]
    assert first["budget"] == ["budget:group-a"]
    assert first["required_documents"] == ["document:advance"]
    assert validate_opportunity_constraints(first) is True


def test_same_url_changed_content_changes_source_and_input_hash() -> None:
    first = compile_opportunity_constraints(_package())
    changed = _package()
    changed["source"]["content"] = "fondart-2027-local-snapshot-v2"
    second = compile_opportunity_constraints(changed)
    assert first["source"]["source_url"] == second["source"]["source_url"]
    assert first["source"]["source_hash"] != second["source"]["source_hash"]
    assert first["input_hash"] != second["input_hash"]


def test_pdf_hash_and_extracted_text_hash_are_preserved_separately() -> None:
    package = _package()
    package["source"]["sha256"] = "sha256:" + "a" * 64
    payload = compile_opportunity_constraints(package)
    assert payload["source"]["source_hash"] == "sha256:" + "a" * 64
    assert payload["source"]["content_hash"].startswith("sha256:")


def test_incomplete_weights_are_preserved_as_unknown() -> None:
    package = _package()
    package["evidence"] = [item for item in package["evidence"] if item["kind"] != "criterion"]
    package["evidence"].extend([
        {"evidence_id": "p15-quality", "kind": "criterion", "field": "quality", "weight": 0.30, "locator": {"page": 15}},
        {"evidence_id": "p15-transfer-impact", "kind": "criterion", "field": "transfer_impact", "weight": 0.40, "locator": {"page": 15}},
    ])
    payload = compile_opportunity_constraints(package)
    assert payload["reconciliation"]["criteria_weight_status"] == "incomplete_weights"
    assert any(row["code"] == "criteria_weights_incomplete" for row in payload["unknowns"])


def test_unconfirmed_date_does_not_become_supported() -> None:
    package = _package()
    for evidence in package["evidence"]:
        if evidence["evidence_id"] == "p4-start-window":
            evidence["confirmed"] = False
    payload = compile_opportunity_constraints(package)
    row = next(item for item in payload["constraints"] if item["constraint_id"] == "date:start-window")
    assert row["status"] == "unknown"
    assert any(item["code"] == "constraint_status_unknown" for item in payload["unknowns"])


def test_requirement_without_evidence_is_explicit_unknown() -> None:
    package = _package()
    package["requirements"].append({
        "id": "eligibility:applicant",
        "kind": "eligibility",
        "field": "eligible_applicant",
    })
    payload = compile_opportunity_constraints(package)
    row = next(item for item in payload["constraints"] if item["constraint_id"] == "eligibility:applicant")
    assert row["status"] == "unknown"
    assert row["evidence_refs"] == []
    assert any(item["code"] == "requirement_without_evidence" for item in payload["unknowns"])


def test_contradiction_is_retained_and_not_promoted() -> None:
    package = _package()
    package["requirements"].append({
        "id": "gate:one-application",
        "kind": "hard_gate",
        "field": "one_application_only",
        "evidence_refs": ["p8-one", "p9-conflict"],
    })
    package["evidence"].extend([
        {"evidence_id": "p8-one", "kind": "hard_gate", "field": "one_application_only", "value": True, "status": "supported", "locator": {"page": 8}},
        {"evidence_id": "p9-conflict", "kind": "hard_gate", "field": "one_application_only", "value": False, "status": "contradicted", "locator": {"page": 9}},
    ])
    payload = compile_opportunity_constraints(package)
    row = next(item for item in payload["constraints"] if item["constraint_id"] == "gate:one-application")
    assert row["status"] == "contradicted"
    assert payload["contradictions"][0]["reason"] == "support_and_contradictory_evidence"
    assert payload["reconciliation"]["claims_promoted"] == 0


def test_malformed_package_fails_closed() -> None:
    package = _package()
    package["evidence"][0]["locator"] = {}
    with pytest.raises(OpportunityConstraintsError):
        compile_opportunity_constraints(package)


def test_cli_file_to_file(tmp_path: Path) -> None:
    source = tmp_path / "package.json"
    output = tmp_path / "constraints.json"
    source.write_text(json.dumps(_package(), ensure_ascii=False), encoding="utf-8")
    assert main(["--input", str(source), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == SCHEMA
    assert validate_opportunity_constraints(payload) is True
