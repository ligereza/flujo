from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.flujo.knowledge.artistic_program_hypotheses import (
    SCHEMA,
    ArtisticProgramHypothesesError,
    generate_artistic_program_hypotheses,
    program_id_for,
    validate_program_payload,
)
from src.flujo.knowledge.opportunity_constraints import compile_opportunity_constraints
from src.flujo.knowledge.opportunity_fit import evaluate_opportunity_fit
from src.flujo.knowledge.practice_evidence_state import build_practice_evidence_state


def _record(project_id: str, *, claim_status: str = "supported", requirement_ids=None) -> dict:
    ref_a = f"artifact:{project_id}:a"
    ref_b = f"artifact:{project_id}:b"
    return {
        "schema": "mak-project-ir-v1",
        "project_id": project_id,
        "title": "Technical fixture title is not a program title",
        "state": "candidate",
        "source": {"kind": "archive_unit_reconstruction", "root_ref": "/not/read"},
        "purpose": "provisional",
        "domains": ["archive"],
        "artifacts": [
            {"artifact_id": ref_a, "artifact_ref": ref_a, "physical_id": f"physical:{project_id}:a", "content_id": "content:same", "relative_path": "work/a.bin", "availability": "available"},
            {"artifact_id": ref_b, "artifact_ref": ref_b, "physical_id": f"physical:{project_id}:b", "content_id": "content:same", "relative_path": "work/b.bin", "availability": "available"},
        ],
        "relations": [],
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
            "member_refs": [ref_a, ref_b],
            "dependency_refs": [],
            "candidate_ids": [],
            "evidence_for": ["fixture_declared"],
            "evidence_against": [],
            "alternatives": ["unit-alternative:fixture"],
            "missing_evidence": [],
        },
        "claims": [{
            "claim_id": f"claim:{project_id}",
            "statement": "declared practice",
            "status": claim_status,
            "evidence_refs": [ref_a],
            "requirement_ids": list(requirement_ids or []),
        }],
        "media": [{"value": "audio", "status": "supported", "evidence_refs": [ref_a], "requirement_ids": list(requirement_ids or [])}],
        "capabilities": [{"value": "declared_tooling", "status": "candidate", "evidence_refs": [ref_a], "requirement_ids": list(requirement_ids or [])}],
        "temporality": [{"value": "period:2026", "status": "candidate", "evidence_refs": [ref_a], "requirement_ids": []}],
        "manifestations": [{"value": "output_ref", "status": "candidate", "evidence_refs": [ref_b], "requirement_ids": []}],
        "resources": [{"value": "resource_ref", "status": "candidate", "evidence_refs": [ref_b], "requirement_ids": []}],
    }


def _practice(*records: dict) -> dict:
    return build_practice_evidence_state({
        "schema": "mak-archive-project-ir-bundle-v1",
        "source_unit_schema": "mak-archive-unit-reconstruction-v1",
        "target_project_ir_schema": "mak-project-ir-v1",
        "algorithm_version": "archive-units-to-project-ir-1",
        "archive_id": "archive-fixture",
        "snapshot_id": "snapshot-fixture",
        "input_hash": "sha256:fixture-input",
        "relation_hash": "sha256:fixture-relation",
        "records": list(records),
        "unit_project_map": [],
        "ambiguous_refs": [],
        "unassigned_refs": [],
        "reconciliation": {},
    })


def _opportunity(*, source_status: str = "current_verified", hard_gate: bool = True) -> dict:
    package = {
        "schema": "mak-opportunity-document-package-v1",
        "opportunity_id": "fondart-fixture-2027",
        "title": "Fondart technical fixture",
        "source": {
            "ref": "local:fondart-fixture.pdf",
            "content": "fondart-fixture-content",
            "version": "v1",
            "validity": {"status": source_status, "confirmed": source_status == "current_verified"},
        },
        "requirements": [
            {"id": "gate:field-study", "kind": "hard_gate", "field": "field_study", "evidence_refs": ["doc:field"]},
            {"id": "criterion:method", "kind": "criterion", "field": "method", "evidence_refs": ["doc:method"]},
        ],
        "evidence": [
            {"evidence_id": "doc:field", "kind": "hard_gate", "field": "field_study", "value": True, "locator": {"page": 2}},
            {"evidence_id": "doc:method", "kind": "criterion", "field": "method", "weight": 1.0, "locator": {"page": 15}},
        ],
    }
    if not hard_gate:
        package["requirements"][0]["kind"] = "eligibility"
    return compile_opportunity_constraints(package)


def _inputs(*, source_status: str = "current_verified", bound: bool = True, hard_gate: bool = True):
    reqs = ["gate:field-study", "criterion:method"] if bound else []
    practice = _practice(_record("one", requirement_ids=reqs))
    opportunity = _opportunity(source_status=source_status, hard_gate=hard_gate)
    fit = evaluate_opportunity_fit(opportunity, practice)
    return opportunity, practice, fit


def test_generates_native_and_conditioned_candidates_without_narrative() -> None:
    opportunity, practice, fit = _inputs()
    payload = generate_artistic_program_hypotheses(opportunity, practice, fit)
    assert payload["schema"] == SCHEMA
    assert {row["basis"] for row in payload["candidates"]} == {"practice_native", "opportunity_conditioned"}
    for candidate in payload["candidates"]:
        assert set(candidate) == {
            "program_id", "basis", "status", "unit_ids", "requirement_ids", "supported_claim_ids",
            "candidate_claim_ids", "evidence_refs", "counterevidence_refs", "missing_requirement_ids",
            "research_action_ids", "resource_refs", "alternatives", "generation_reasons", "risk_flags",
            "provenance",
        }
        assert "title" not in candidate
        assert "statement" not in candidate
    conditioned = next(row for row in payload["candidates"] if row["basis"] == "opportunity_conditioned")
    assert conditioned["unit_ids"] == ["unit:one"]
    assert "gate:field-study" in conditioned["requirement_ids"]
    assert conditioned["supported_claim_ids"] == ["claim:one"]
    assert validate_program_payload(opportunity, practice, fit, payload) is True


def test_input_reordering_is_byte_deterministic() -> None:
    opportunity, practice, fit = _inputs()
    second = _practice(_record("one", requirement_ids=["criterion:method", "gate:field-study"]))
    second_fit = evaluate_opportunity_fit(opportunity, second)
    first = generate_artistic_program_hypotheses(opportunity, practice, fit)
    reordered = generate_artistic_program_hypotheses(opportunity, second, second_fit)
    assert first == reordered
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(reordered, sort_keys=True, separators=(",", ":"))


def test_evidence_id_collision_between_document_and_practice_fails_closed() -> None:
    opportunity, practice, fit = _inputs()
    collision = copy.deepcopy(opportunity)
    collision["evidence"][0]["evidence_id"] = "artifact:one:a"
    for constraint in collision["constraints"]:
        if constraint["field"] == "field_study":
            constraint["evidence_refs"] = ["artifact:one:a"]
    with pytest.raises(ArtisticProgramHypothesesError, match="namespace_collision"):
        generate_artistic_program_hypotheses(collision, practice, fit)


def test_source_not_current_preserves_fit_abstention_and_unknown_candidate() -> None:
    opportunity, practice, fit = _inputs(source_status="observed_local")
    payload = generate_artistic_program_hypotheses(opportunity, practice, fit)
    conditioned = next(row for row in payload["candidates"] if row["basis"] == "opportunity_conditioned")
    assert conditioned["status"] == "unknown"
    assert "source_gate_abstain" in conditioned["risk_flags"]
    assert any(row["code"] == "source_gate_abstain" for row in payload["abstentions"])
    assert payload["fit_summary"]["source_gate_status"] == "abstain"


def test_claim_without_binding_stays_native_and_does_not_condition_program() -> None:
    opportunity, practice, fit = _inputs(bound=False)
    payload = generate_artistic_program_hypotheses(opportunity, practice, fit)
    conditioned = next(row for row in payload["candidates"] if row["basis"] == "opportunity_conditioned")
    assert conditioned["unit_ids"] == []
    assert conditioned["supported_claim_ids"] == []
    native = next(row for row in payload["candidates"] if row["basis"] == "practice_native")
    assert native["supported_claim_ids"] == ["claim:one"]


def test_missing_hard_gate_is_unknown_and_reconciled() -> None:
    opportunity, practice, fit = _inputs()
    tampered_fit = copy.deepcopy(fit)
    for row in tampered_fit["matrix"]:
        if row["requirement_id"] == "gate:field-study":
            row["status"] = "missing"
            row["cells"] = []
    tampered_fit["hard_gate_status"] = "abstain"
    tampered_fit["decision"] = "abstain"
    payload = generate_artistic_program_hypotheses(opportunity, practice, tampered_fit)
    conditioned = next(row for row in payload["candidates"] if row["basis"] == "opportunity_conditioned")
    assert conditioned["status"] == "unknown"
    assert "gate:field-study" in conditioned["missing_requirement_ids"]
    assert payload["reconciliation"]["hard_gate_status"] == "abstain"


def test_program_ids_recompute_and_duplicate_physical_refs_remain_distinct() -> None:
    opportunity, practice, fit = _inputs()
    payload = generate_artistic_program_hypotheses(opportunity, practice, fit)
    for candidate in payload["candidates"]:
        assert candidate["program_id"] == program_id_for(candidate)
    native = next(row for row in payload["candidates"] if row["basis"] == "practice_native")
    assert set(native["evidence_refs"]) >= {"artifact:one:a", "artifact:one:b"}
    assert practice["reconciliation"]["duplicate_physical_refs_collapsed"] is False


def test_malformed_fit_fails_closed() -> None:
    opportunity, practice, fit = _inputs()
    malformed = copy.deepcopy(fit)
    malformed["matrix"][0]["status"] = "invented_truth"
    with pytest.raises(ArtisticProgramHypothesesError):
        generate_artistic_program_hypotheses(opportunity, practice, malformed)


def test_cli_file_inputs_and_output(tmp_path: Path) -> None:
    opportunity, practice, fit = _inputs()
    paths = []
    for name, value in (("opportunity.json", opportunity), ("practice.json", practice), ("fit.json", fit)):
        path = tmp_path / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        paths.append(path)
    output = tmp_path / "programs.json"
    result = subprocess.run(
        [sys.executable, "tools/generate_artistic_program_hypotheses.py", *(str(path) for path in paths), "--output", str(output)],
        cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["schema"] == SCHEMA
