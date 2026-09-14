from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.artistic_program_evaluator import (
    ArtisticProgramEvaluationError,
    evaluate_artistic_program_payload,
    fit_input_hash_for,
    program_id_for,
    stable_json,
)
from flujo.knowledge.opportunity_constraints import compile_opportunity_constraints
from flujo.knowledge.opportunity_fit import evaluate_opportunity_fit


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _practice() -> dict:
    state = {
        "schema": "mak-practice-evidence-state-v1",
        "algorithm_version": "practice-evidence-state-1",
        "tenant": "mak",
        "archive_id": "archive-fixture",
        "snapshot_id": "snapshot-fixture",
        "input_hash": "sha256:archive-input",
        "source_schema": "mak-archive-project-ir-bundle-v1",
        "units": [{
            "unit_id": "unit:one",
            "project_id": "project-one",
            "role": "project_unit",
            "status": "provisional_unit",
            "source_state": "candidate",
            "artifact_refs": ["artifact:gate", "artifact:media", "artifact:resource"],
            "member_refs": ["artifact:gate", "artifact:media", "artifact:resource"],
            "dependency_refs": [],
            "candidate_ids": [],
            "evidence_refs": ["artifact:gate", "artifact:media", "artifact:resource"],
            "evidence_for": ["fixture"],
            "evidence_against": [],
            "alternatives": [],
            "missing_evidence": [],
            "provenance_ref": "unit:unit:one",
            "provenance": {"source_rescan": False},
        }],
        "artifacts": [{
            "artifact_ref": "artifact:gate",
            "artifact_id": "artifact:gate",
            "physical_id": "physical:gate",
            "content_id": "content:one",
            "relative_path": "work/gate.bin",
            "availability": "available",
            "kind": "file",
            "role": "source",
            "evidence_refs": ["artifact:gate"],
            "unit_id": "unit:one",
        }, {
            "artifact_ref": "artifact:media",
            "artifact_id": "artifact:media",
            "physical_id": "physical:media",
            "content_id": "content:one",
            "relative_path": "work/media.bin",
            "availability": "available",
            "kind": "file",
            "role": "source",
            "evidence_refs": ["artifact:media"],
            "unit_id": "unit:one",
        }, {
            "artifact_ref": "artifact:resource",
            "artifact_id": "artifact:resource",
            "physical_id": "physical:resource",
            "content_id": "content:resource",
            "relative_path": "work/resource.bin",
            "availability": "available",
            "kind": "file",
            "role": "source",
            "evidence_refs": ["artifact:resource"],
            "unit_id": "unit:one",
        }],
        "media": [{
            "dimension": "media", "value": "audio", "status": "supported",
            "evidence_refs": ["artifact:media"], "requirement_ids": ["req:media"],
            "unit_id": "unit:one", "provenance_ref": "unit:unit:one", "source_index": 0,
        }],
        "capabilities": [], "temporality": [], "manifestations": [],
        "resources": [{
            "dimension": "resources", "value": "resource:one", "status": "supported",
            "evidence_refs": ["artifact:resource"], "requirement_ids": [],
            "unit_id": "unit:one", "provenance_ref": "unit:unit:one", "source_index": 0,
        }],
        "claims": {
            "supported": [
                {
                    "claim_id": "claim:gate", "unit_id": "unit:one", "status": "supported",
                    "statement": "explicit gate evidence", "evidence_refs": ["artifact:gate"],
                    "requirement_ids": ["req:gate"], "source_status": "supported",
                    "provenance_ref": "unit:unit:one",
                },
            ],
            "candidate": [],
            "unknown": [],
        },
        "dependencies": [],
        "ambiguous_refs": [],
        "unassigned_refs": [],
        "gaps": [],
        "abstentions": [],
        "provenance": {"producer": "fixture", "source_rescan": False},
        "reconciliation": {"duplicate_physical_refs_collapsed": False},
    }
    state["state_hash"] = _hash(state)
    return state


def _opportunity(*, source_status: str = "current_verified", confirmed: bool = True) -> dict:
    package = {
        "schema": "mak-opportunity-document-package-v1",
        "opportunity_id": "opportunity:fixture",
        "title": "Fixture opportunity",
        "source": {
            "ref": "fixture:bases.pdf", "content": "bases-v1", "version": "v1",
            "validity": {"status": source_status, "confirmed": confirmed},
        },
        "requirements": [
            {"id": "req:gate", "kind": "hard_gate", "field": "eligibility", "evidence_refs": ["pdf:gate"]},
            {"id": "req:media", "kind": "criterion", "field": "media", "evidence_refs": ["pdf:media"]},
        ],
        "evidence": [
            {"evidence_id": "pdf:gate", "kind": "hard_gate", "field": "eligibility", "value": True, "locator": {"page": 1}},
            {"evidence_id": "pdf:media", "kind": "criterion", "field": "media", "value": "audio", "weight": 1, "locator": {"page": 2}},
        ],
    }
    return compile_opportunity_constraints(package)


def _candidate(opportunity: dict, practice: dict, fit: dict, **changes: object) -> dict:
    identity = fit["practice_identity"]
    program = {
        "program_id": "pending",
        "basis": "opportunity_conditioned",
        "status": "candidate",
        "unit_ids": ["unit:one"],
        "requirement_ids": ["req:gate", "req:media"],
        "supported_claim_ids": ["claim:gate"],
        "candidate_claim_ids": [],
        "evidence_refs": ["artifact:gate", "artifact:media", "artifact:resource"],
        "counterevidence_refs": [],
        "missing_requirement_ids": [],
        "research_action_ids": [],
        "resource_refs": ["resource:one"],
        "alternatives": [],
        "generation_reasons": ["explicit_bindings"],
        "risk_flags": [],
        "provenance": {
            "opportunity_id": opportunity["opportunity_id"],
            "opportunity_input_hash": opportunity["input_hash"],
            "practice_identity": identity,
            "practice_state_hash": practice["state_hash"],
            "fit_input_hash": fit_input_hash_for(fit),
            "source_rescan": False,
            "claims_promoted": 0,
        },
    }
    program.update(changes)
    program["program_id"] = program_id_for(
        program, opportunity_id=opportunity["opportunity_id"], practice_identity=identity
    )
    return program


def _payload(opportunity: dict, practice: dict, fit: dict, programs: list[dict]) -> dict:
    return {
        "schema": "mak-artistic-program-candidates-v1",
        "algorithm_version": "artistic-program-generator-fixture-1",
        "opportunity_id": opportunity["opportunity_id"],
        "candidates": sorted(programs, key=lambda row: row["program_id"]),
    }


def _inputs(*, source_status: str = "current_verified", confirmed: bool = True):
    opportunity = _opportunity(source_status=source_status, confirmed=confirmed)
    practice = _practice()
    fit = evaluate_opportunity_fit(opportunity, practice)
    return opportunity, practice, fit


def test_minimal_valid_candidate_passes_independent_gate() -> None:
    opportunity, practice, fit = _inputs()
    payload = _payload(opportunity, practice, fit, [_candidate(opportunity, practice, fit)])
    first = evaluate_artistic_program_payload(opportunity, practice, fit, payload)
    second = evaluate_artistic_program_payload(copy.deepcopy(opportunity), copy.deepcopy(practice), copy.deepcopy(fit), copy.deepcopy(payload))
    assert first == second
    assert first["schema"] == "mak-artistic-program-evaluation-v1"
    assert first["valid"] is True
    result = next(iter(first["results"].values()))
    assert result["result"] == "accepted"
    assert result["learning_features"]["training_permitted"] is False
    assert first["reconciliation"]["truth_promotions"] == 0


def test_existing_generator_payload_cross_smoke_passes_gate() -> None:
    from flujo.knowledge.artistic_program_hypotheses import generate_artistic_program_hypotheses

    opportunity, practice, fit = _inputs()
    generated = generate_artistic_program_hypotheses(opportunity, practice, fit)
    report = evaluate_artistic_program_payload(opportunity, practice, fit, generated)
    assert report["valid"] is True
    assert report["status"] == "pass"
    assert len(generated["candidates"]) == 2
    assert all(result["result"] == "accepted" for result in report["results"].values())
    assert report["report_hash"] == evaluate_artistic_program_payload(
        opportunity, practice, fit, copy.deepcopy(generated)
    )["report_hash"]


def test_native_duplicate_content_refs_must_remain_distinct() -> None:
    from flujo.knowledge.artistic_program_hypotheses import generate_artistic_program_hypotheses

    opportunity, practice, fit = _inputs()
    payload = generate_artistic_program_hypotheses(opportunity, practice, fit)
    native = next(row for row in payload["candidates"] if row["basis"] == "practice_native")
    native["evidence_refs"] = [ref for ref in native["evidence_refs"] if ref != "artifact:media"]
    native["program_id"] = program_id_for(native)
    payload["candidates"] = sorted(payload["candidates"], key=lambda row: row["program_id"])
    report = evaluate_artistic_program_payload(opportunity, practice, fit, payload)
    assert report["valid"] is False
    assert any(error["code"] == "duplicate_physical_ref_collapsed" for error in report["errors"])


def test_top_input_hash_tampering_fails_closed() -> None:
    opportunity, practice, fit = _inputs()
    candidate = _candidate(opportunity, practice, fit)
    payload = _payload(opportunity, practice, fit, [candidate])
    payload["input_hashes"] = {
        "opportunity_constraints": "sha256:tampered",
        "practice_evidence_state": practice["state_hash"],
        "opportunity_fit": fit_input_hash_for(fit),
    }
    report = evaluate_artistic_program_payload(opportunity, practice, fit, payload)
    assert report["valid"] is False
    assert any(error["code"] == "candidate_input_hashes_mismatch" for error in report["errors"])


def test_source_gate_false_green_is_rejected() -> None:
    opportunity, practice, fit = _inputs(source_status="observed_local", confirmed=False)
    tampered_fit = copy.deepcopy(fit)
    tampered_fit["source_gate_status"] = "pass"
    candidate = _candidate(opportunity, practice, tampered_fit)
    payload = _payload(opportunity, practice, tampered_fit, [candidate])
    report = evaluate_artistic_program_payload(opportunity, practice, tampered_fit, payload)
    assert report["valid"] is False
    assert any(error["code"] == "source_gate_false_green" for error in report["errors"])


def test_hard_gate_false_green_is_rejected() -> None:
    opportunity, practice, fit = _inputs()
    reduced = copy.deepcopy(practice)
    reduced["claims"]["supported"] = [row for row in reduced["claims"]["supported"] if row["claim_id"] != "claim:gate"]
    reduced["state_hash"] = _hash({key: value for key, value in reduced.items() if key != "state_hash"})
    abstaining_fit = evaluate_opportunity_fit(opportunity, reduced)
    tampered_fit = copy.deepcopy(abstaining_fit)
    tampered_fit["hard_gate_status"] = "pass"
    candidate = _candidate(opportunity, reduced, tampered_fit, supported_claim_ids=[], missing_requirement_ids=["req:gate"])
    payload = _payload(opportunity, reduced, tampered_fit, [candidate])
    report = evaluate_artistic_program_payload(opportunity, reduced, tampered_fit, payload)
    assert report["valid"] is False
    assert any(error["code"] == "hard_gate_false_green" for error in report["errors"])


@pytest.mark.parametrize("mutation,expected", [
    ("unit", "program_unit_dangling"),
    ("content", "content_id_endpoint"),
    ("documentary", "documentary_evidence_ref_used_as_internal"),
    ("promoted", "program_truth_promotion"),
    ("binding", "provenance_binding_missing"),
])
def test_adversarial_mutations_fail_closed(mutation: str, expected: str) -> None:
    opportunity, practice, fit = _inputs()
    changes: dict[str, object] = {}
    if mutation == "unit":
        changes["unit_ids"] = ["unit:missing"]
    elif mutation == "content":
        changes["evidence_refs"] = ["content:one"]
    elif mutation == "documentary":
        changes["evidence_refs"] = ["pdf:media"]
    elif mutation == "promoted":
        changes["status"] = "accepted"
    elif mutation == "binding":
        changes["provenance"] = {}
    candidate = _candidate(opportunity, practice, fit, **changes)
    report = evaluate_artistic_program_payload(opportunity, practice, fit, _payload(opportunity, practice, fit, [candidate]))
    assert report["valid"] is False
    assert any(error["code"] == expected for error in report["errors"])


def test_supported_claim_without_explicit_binding_is_rejected() -> None:
    opportunity, practice, fit = _inputs()
    tampered_practice = copy.deepcopy(practice)
    tampered_practice["claims"]["supported"][0]["requirement_ids"] = []
    tampered_practice["state_hash"] = _hash({key: value for key, value in tampered_practice.items() if key != "state_hash"})
    tampered_fit = evaluate_opportunity_fit(opportunity, tampered_practice)
    candidate = _candidate(opportunity, tampered_practice, tampered_fit)
    report = evaluate_artistic_program_payload(opportunity, tampered_practice, tampered_fit, _payload(opportunity, tampered_practice, tampered_fit, [candidate]))
    assert report["valid"] is False
    assert any(error["code"] in {"supported_claim_unbound", "fit_matrix_status_mismatch"} for error in report["errors"])


def test_duplicate_physical_ref_cannot_be_collapsed() -> None:
    opportunity, practice, fit = _inputs()
    tampered = copy.deepcopy(practice)
    tampered["artifacts"].append(copy.deepcopy(tampered["artifacts"][0]))
    tampered["state_hash"] = _hash({key: value for key, value in tampered.items() if key != "state_hash"})
    candidate = _candidate(opportunity, tampered, fit)
    report = evaluate_artistic_program_payload(opportunity, tampered, fit, _payload(opportunity, tampered, fit, [candidate]))
    assert report["valid"] is False
    assert any(error["code"] == "practice_physical_ref_duplicate" for error in report["errors"])


def test_resource_conflict_is_metadata_between_accepted_alternatives() -> None:
    opportunity, practice, fit = _inputs()
    first = _candidate(opportunity, practice, fit, generation_reasons=["a"])
    second = _candidate(opportunity, practice, fit, generation_reasons=["b"])
    report = evaluate_artistic_program_payload(opportunity, practice, fit, _payload(opportunity, practice, fit, [first, second]))
    assert report["valid"] is True
    assert all(result["result"] == "accepted" for result in report["results"].values())
    assert all(result["resource_conflicts"] for result in report["results"].values())
    assert all("resource_conflict" in result["warnings"] for result in report["results"].values())
    assert all(result["learning_features"]["training_permitted"] is False for result in report["results"].values())


def test_assertion_raises_and_cli_is_pure_json(tmp_path: Path) -> None:
    opportunity, practice, fit = _inputs()
    candidate = _candidate(opportunity, practice, fit, status="accepted")
    payload = _payload(opportunity, practice, fit, [candidate])
    with pytest.raises(ArtisticProgramEvaluationError):
        from flujo.knowledge.artistic_program_evaluator import assert_artistic_program_payload
        assert_artistic_program_payload(opportunity, practice, fit, payload)

    paths = {}
    for name, value in (("opportunity", opportunity), ("practice", practice), ("fit", fit), ("candidates", payload)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        paths[name] = path
    command = [
        sys.executable, "tools/evaluate_artistic_program_hypotheses.py",
        "--opportunity", str(paths["opportunity"]), "--practice", str(paths["practice"]),
        "--fit", str(paths["fit"]), "--candidates", str(paths["candidates"]),
    ]
    completed = subprocess.run(command, cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["schema"] == "mak-artistic-program-evaluation-v1"
