from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.opportunity_constraints import compile_opportunity_constraints
from flujo.knowledge.research_frontier_bridge import (
    ResearchFrontierBridgeError,
    SCHEMA,
    compile_research_frontier,
    stable_json,
    validate_research_frontier_payload,
)
from flujo.knowledge.research_evidence_triangulation import triangulate_research_evidence


def _opportunity() -> dict:
    return compile_opportunity_constraints({
        "schema": "mak-opportunity-document-package-v1",
        "opportunity_id": "fondart-investigacion-2027",
        "title": "Fondart Nacional Investigación 2027",
        "source": {
            "ref": "local:fondart-nacional-investigacion-2027.pdf",
            "content": "fondart-nacional-investigacion-2027-local-snapshot-v1",
            "version": "2026-08-12-local",
            "validity": {"status": "observed_local", "confirmed": False},
        },
        "requirements": [
            {"id": "req:field-study", "kind": "hard_gate", "field": "field_study", "evidence_refs": ["pdf:field-study"]},
            {"id": "req:transfer", "kind": "criterion", "field": "transfer", "evidence_refs": ["pdf:transfer"]},
        ],
        "evidence": [
            {"evidence_id": "pdf:field-study", "kind": "hard_gate", "field": "field_study", "value": True, "locator": {"page": 2}},
            {"evidence_id": "pdf:transfer", "kind": "criterion", "field": "transfer", "value": True, "weight": 1, "locator": {"page": 4}},
        ],
    })


def _fit(
    actions: list[dict] | None = None,
    *,
    source_gate_status: str = "abstain",
    decision: str = "abstain",
    valid: bool = True,
    errors: list[str] | None = None,
) -> dict:
    rows = []
    for index, spec in enumerate(actions or []):
        action_id = spec.get("candidate_id", f"action:{index}")
        rows.append({
            "candidate_id": action_id,
            "requirement_id": spec.get("requirement_id", f"req:{index}"),
            "question": spec.get("question", f"Question for {action_id}"),
            "domain": spec.get("domain", "curatoria"),
            "status": "planned_not_dispatched",
            "dispatched": False,
            "resolution_probability": 0.8,
            "utility_delta": 2.0,
            "risk_avoided": 0.5,
            "cost": 1.0,
            "time": 1.0,
            "voi_numerator": 2.1,
            "voi_denominator": 2.0,
            "voi": 1.05,
            "voi_status": "defined",
        })
    return {
        "schema": "mak-opportunity-fit-v1",
        "decision": decision,
        "validation": {"valid": valid, "errors": sorted(errors or [])},
        "matrix": [],
        "hard_gate_status": "abstain",
        "weighted_coverage": None,
        "required_but_unsupported": [],
        "research_job_candidates": rows,
        "source_gate_status": source_gate_status,
        "source_gate_reason": "source_validity_not_current_verified_or_unconfirmed",
    }


def _possibility(
    candidates: list[dict],
    *,
    frontier: list[dict] | None = None,
    rejected: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict:
    ranked = []
    for index, spec in enumerate(candidates, 1):
        ranked.append({
            "candidate_id": spec["candidate_id"],
            "rank": index,
            "basis": "opportunity_conditioned",
            "requirement_ids": sorted(spec.get("requirement_ids", [])),
            "missing_requirement_ids": sorted(spec.get("missing_requirement_ids", [])),
            "research_action_ids": sorted(spec.get("research_action_ids", [])),
            "risk_flags": sorted(spec.get("risk_flags", [])),
            "source_gate_status": spec.get("source_gate_status", "pass"),
            "hard_gate_status": spec.get("hard_gate_status", "abstain"),
        })
    return {
        "schema": "mak-possibility-field-v1",
        "decision": "abstain" if not ranked else "supported",
        "candidates_ranked": ranked,
        "rejected": [{"candidate_id": candidate_id} for candidate_id in sorted(rejected or [])],
        "abstained": [],
        "research_frontier": copy.deepcopy(frontier if frontier is not None else []),
        "resource_conflicts": [],
        "provenance": {"errors": sorted(errors or [])},
    }


def _action(action_id: str, requirement_id: str, *, domain: str = "curatoria") -> dict:
    return {"candidate_id": action_id, "requirement_id": requirement_id, "domain": domain, "question": f"Preserve this exact question for {action_id}"}


def test_real_observed_local_frontier_is_planned_but_never_dispatched() -> None:
    opportunity = _opportunity()
    action = _action("research:fondart:req:field-study", "req:field-study")
    fit = _fit([action])
    possibility = _possibility(
        [{
            "candidate_id": "program:field-study",
            "research_action_ids": [action["candidate_id"]],
            "source_gate_status": "abstain",
            "risk_flags": ["source_validity_unverified"],
        }],
        frontier=[
            {"candidate_id": "program:field-study", "kind": "research_action", "research_action_id": action["candidate_id"], "dispatch": False},
            {"candidate_id": "program:field-study", "kind": "refresh_source_validity", "dispatch": False},
        ],
    )

    payload = compile_research_frontier(possibility, fit, opportunity)
    assert payload["schema"] == SCHEMA
    assert payload["control"]["source_gate_status"] == "abstain"
    assert len(payload["jobs"]) == 2
    assert all(job["status"] == "planned_not_dispatched" and job["dispatch"] is False for job in payload["jobs"])
    action_job = next(job for job in payload["jobs"] if job["research_action_ids"])
    assert action_job["question"] == action["question"]
    assert action_job["requirement_ids"] == ["req:field-study"]
    refresh_job = next(job for job in payload["jobs"] if not job["research_action_ids"])
    assert refresh_job["requirement_ids"] == ["source-validity:fondart-investigacion-2027"]
    assert refresh_job["source_policy"] == "official-source-only"
    assert "official source" in refresh_job["question"]
    assert payload["provenance"]["network_called"] is False
    assert validate_research_frontier_payload(possibility, fit, opportunity, payload) is True


def test_real_observed_local_refresh_reaches_triangulation_as_unresolved() -> None:
    from test_artistic_program_evaluator import _inputs
    from flujo.knowledge.artistic_program_evaluator import evaluate_artistic_program_payload
    from flujo.knowledge.artistic_program_hypotheses import generate_artistic_program_hypotheses
    from flujo.knowledge.possibility_field import build_possibility_field

    opportunity, practice, fit = _inputs(source_status="observed_local", confirmed=False)
    generated = generate_artistic_program_hypotheses(opportunity, practice, fit)
    evaluated = evaluate_artistic_program_payload(opportunity, practice, fit, generated)
    possibility = build_possibility_field(generated, evaluated)
    frontier = compile_research_frontier(possibility, fit, opportunity)

    report = triangulate_research_evidence(frontier, [])
    assert frontier["jobs"]
    assert all(job["provenance"]["frontier_kind"] == "refresh_source_validity" for job in frontier["jobs"])
    assert all(job["requirement_ids"] == ["source-validity:opportunity:fixture"] for job in frontier["jobs"])
    assert report["results"]
    assert report["reconciliation"]["job_requirement_count"] == len(frontier["jobs"])
    assert all(row["status"] == "unresolved" for row in report["results"])
    assert all("result_missing" in row["gaps"] for row in report["results"])


def test_actual_possibility_builder_output_is_accepted() -> None:
    from flujo.knowledge.possibility_field import build_possibility_field

    opportunity = _opportunity()
    action = _action("research:actual:req", "req:transfer", domain="general")
    fit = _fit([action])
    field = build_possibility_field(
        {"schema": "mak-artistic-program-candidates-v1", "candidates": [{
            "program_id": "program:actual",
            "title": "technical fixture",
            "status": "candidate",
            "unit_ids": ["unit:actual"],
            "evidence_refs": ["evidence:actual"],
            "source_gate_status": "abstain",
            "hard_gate_status": "abstain",
            "requirement_ids": ["req:transfer"],
            "missing_requirement_ids": ["req:transfer"],
            "research_action_ids": [action["candidate_id"]],
            "risk_flags": ["source_validity_unverified"],
            "resource_refs": [],
        }]},
        {"schema": "mak-artistic-program-evaluation-v1", "results": {"program:actual": {
            "program_id": "program:actual",
            "result": "abstain",
            "source_gate_alignment": {"declared": "abstain", "passed": False},
            "hard_gate_alignment": {"declared": "abstain", "passed": False},
            "learning_features": {"training_permitted": False},
        }}},
    )
    payload = compile_research_frontier(field, fit, opportunity)
    assert field["schema"] == "mak-possibility-field-v1"
    assert field["abstained"]
    assert any(job["candidate_id"] == "program:actual" for job in payload["jobs"])


def test_missing_action_reference_is_unresolved_and_not_dispatchable() -> None:
    opportunity = _opportunity()
    missing_id = "research:missing"
    fit = _fit([])
    possibility = _possibility(
        [{"candidate_id": "program:missing", "research_action_ids": [missing_id]}],
        frontier=[{"candidate_id": "program:missing", "kind": "research_action", "research_action_id": missing_id, "dispatch": False}],
    )
    payload = compile_research_frontier(possibility, fit, opportunity)
    assert len(payload["jobs"]) == 1
    job = payload["jobs"][0]
    assert job["research_action_ids"] == []
    assert job["provenance"]["action_resolved"] is False
    assert job["status"] == "planned_not_dispatched"
    assert payload["reconciliation"]["unresolved_action_job_count"] == 1


def test_multiple_candidates_and_duplicate_frontier_rows_are_traceable() -> None:
    opportunity = _opportunity()
    actions = [_action("research:a", "req:a"), _action("research:b", "req:b")]
    fit = _fit(actions, source_gate_status="pass", decision="supported")
    frontier = [
        {"candidate_id": "program:a", "kind": "research_action", "research_action_id": "research:a", "dispatch": False},
        {"candidate_id": "program:a", "kind": "research_action", "research_action_id": "research:a", "dispatch": False},
        {"candidate_id": "program:b", "kind": "research_action", "research_action_id": "research:b", "dispatch": False},
    ]
    possibility = _possibility([
        {"candidate_id": "program:a", "research_action_ids": ["research:a"]},
        {"candidate_id": "program:b", "research_action_ids": ["research:b"]},
    ], frontier=frontier)
    payload = compile_research_frontier(possibility, fit, opportunity)
    assert {job["candidate_id"] for job in payload["jobs"]} == {"program:a", "program:b"}
    assert payload["reconciliation"]["duplicate_frontier_groups_collapsed"] >= 1
    assert all(job["provenance"]["frontier_sources"] for job in payload["jobs"])


def test_unknown_declared_domain_falls_back_to_general() -> None:
    opportunity = _opportunity()
    action = _action("research:unknown-domain", "req:unknown", domain="not-a-router-domain")
    fit = _fit([action], source_gate_status="pass", decision="supported")
    possibility = _possibility(
        [{"candidate_id": "program:unknown-domain", "research_action_ids": [action["candidate_id"]]}],
        frontier=[{"candidate_id": "program:unknown-domain", "kind": "research_action", "research_action_id": action["candidate_id"], "dispatch": False}],
    )
    job = compile_research_frontier(possibility, fit, opportunity)["jobs"][0]
    assert job["domain"] == "general"
    assert job["provenance"]["domain_source"] == "unknown_domain_fallback"


def test_rejected_program_preserves_fit_research_but_invalid_inputs_create_no_jobs() -> None:
    opportunity = _opportunity()
    action = _action("research:rejected", "req:rejected")
    fit = _fit([action])
    rejected_field = _possibility(
        [{"candidate_id": "program:rejected", "research_action_ids": [action["candidate_id"]]}],
        frontier=[{"candidate_id": "program:rejected", "kind": "research_action", "research_action_id": action["candidate_id"], "dispatch": False}],
        rejected=["program:rejected"],
    )
    rejected_payload = compile_research_frontier(rejected_field, fit, opportunity)
    assert len(rejected_payload["jobs"]) == 1
    assert rejected_payload["jobs"][0]["candidate_id"] == "opportunity-scope:fondart-investigacion-2027"
    assert rejected_payload["jobs"][0]["research_action_ids"] == [action["candidate_id"]]
    invalid_fit = _fit([action], valid=False, errors=["fit_input_invalid"])
    invalid_payload = compile_research_frontier(_possibility([{"candidate_id": "program:invalid", "research_action_ids": [action["candidate_id"]]}]), invalid_fit, opportunity)
    assert invalid_payload["jobs"] == []
    assert invalid_payload["reconciliation"]["invalid_input"] is True
    invalid_possibility = _possibility(
        [{"candidate_id": "program:invalid-field", "research_action_ids": [action["candidate_id"]]}],
        errors=["candidate_bundle_invalid"],
    )
    assert compile_research_frontier(invalid_possibility, fit, opportunity)["jobs"] == []


def test_reordering_is_byte_deterministic_and_validates() -> None:
    opportunity = _opportunity()
    actions = [_action("research:z", "req:z"), _action("research:a", "req:a")]
    fit = _fit(actions, source_gate_status="pass", decision="supported")
    possibility = _possibility([
        {"candidate_id": "program:z", "research_action_ids": ["research:z"]},
        {"candidate_id": "program:a", "research_action_ids": ["research:a"]},
    ], frontier=[
        {"candidate_id": "program:z", "kind": "research_action", "research_action_id": "research:z", "dispatch": False},
        {"candidate_id": "program:a", "kind": "research_action", "research_action_id": "research:a", "dispatch": False},
    ])
    first = compile_research_frontier(possibility, fit, opportunity)
    shuffled_possibility = copy.deepcopy(possibility)
    shuffled_possibility["candidates_ranked"].reverse()
    shuffled_possibility["research_frontier"].reverse()
    shuffled_fit = copy.deepcopy(fit)
    shuffled_fit["research_job_candidates"].reverse()
    second = compile_research_frontier(shuffled_possibility, shuffled_fit, copy.deepcopy(opportunity))
    assert first == second
    assert stable_json(first) == stable_json(second)
    assert validate_research_frontier_payload(shuffled_possibility, shuffled_fit, opportunity, first) is True


def test_cli_file_to_stdout(tmp_path: Path) -> None:
    opportunity = _opportunity()
    action = _action("research:cli", "req:cli")
    possibility = _possibility(
        [{"candidate_id": "program:cli", "research_action_ids": [action["candidate_id"]]}],
        frontier=[{"candidate_id": "program:cli", "kind": "research_action", "research_action_id": action["candidate_id"], "dispatch": False}],
    )
    fit = _fit([action], source_gate_status="pass", decision="supported")
    possibility_path = tmp_path / "possibility.json"
    fit_path = tmp_path / "fit.json"
    opportunity_path = tmp_path / "opportunity.json"
    for path, value in ((possibility_path, possibility), (fit_path, fit), (opportunity_path, opportunity)):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "tools/compile_research_frontier.py", str(possibility_path), str(fit_path), str(opportunity_path)],
        cwd=Path(__file__).parents[1], capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["schema"] == SCHEMA


def test_malformed_frontier_fails_closed() -> None:
    opportunity = _opportunity()
    fit = _fit([])
    possibility = _possibility([{"candidate_id": "program:bad"}], frontier=[{"candidate_id": "program:bad", "kind": "not-a-kind", "dispatch": False}])
    with pytest.raises(ResearchFrontierBridgeError):
        compile_research_frontier(possibility, fit, opportunity)
