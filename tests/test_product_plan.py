from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.artistic_program_evaluator import evaluate_artistic_program_payload
from flujo.knowledge.artistic_program_hypotheses import generate_artistic_program_hypotheses
from flujo.knowledge.evidence_return import build_evidence_return
from flujo.knowledge.possibility_field import build_possibility_field
from flujo.knowledge.product_plan import (
    ProductPlanError,
    SCHEMA,
    compile_product_plan,
    stable_json,
    validate_product_plan,
)
from flujo.knowledge.portfolio_dossier import compile_portfolio_dossier
from flujo.knowledge.research_evidence_triangulation import triangulate_research_evidence
from flujo.knowledge.research_frontier_bridge import compile_research_frontier


def _chain(*, source_status: str = "current_verified", confirmed: bool = True) -> tuple[dict, ...]:
    from test_artistic_program_evaluator import _inputs

    opportunity, practice, fit = _inputs(source_status=source_status, confirmed=confirmed)
    programs = generate_artistic_program_hypotheses(opportunity, practice, fit)
    evaluations = evaluate_artistic_program_payload(opportunity, practice, fit, programs)
    possibility = build_possibility_field(programs, evaluations)
    frontier = compile_research_frontier(possibility, fit, opportunity)
    triangulation = triangulate_research_evidence(frontier, [])
    evidence_return = build_evidence_return(
        opportunity, practice, fit, frontier, triangulation
    )
    return opportunity, practice, fit, programs, possibility, frontier, evidence_return


def test_verified_ready_builds_all_shared_product_targets() -> None:
    inputs = _chain()
    plan = compile_product_plan(*inputs)
    assert plan["schema"] == SCHEMA
    assert len(plan["selected_programs"]) == 2
    assert {row["selection"] for row in plan["selected_programs"]} == {"ranked"}
    assert all(row["ready"] for row in plan["selected_programs"])
    assert plan["targets"]["portfolio_dossier"]["status"] == "draftable"
    assert plan["targets"]["application_draft"]["status"] == "draftable"
    assert plan["targets"]["research_brief"]["status"] == "not_required"
    assert plan["control"] == {
        "promotion": "none",
        "training_permitted": False,
        "publication": False,
        "submission": False,
        "dispatch": False,
        "user_review_required": False,
    }


def test_observed_local_preserves_abstained_programs_as_research_first() -> None:
    inputs = _chain(source_status="observed_local", confirmed=False)
    plan = compile_product_plan(*inputs)
    assert plan["selected_programs"]
    assert all(row["selection"] == "abstained_research_first" for row in plan["selected_programs"])
    assert all(row["ready"] is False for row in plan["selected_programs"])
    assert plan["targets"]["portfolio_dossier"]["status"] == "draftable"
    assert plan["targets"]["application_draft"]["status"] == "blocked"
    assert plan["targets"]["research_brief"]["status"] == "draftable"
    assert len(plan["research_jobs"]) == 1
    assert plan["research_jobs"][0]["candidate_id"] == "opportunity-scope:opportunity:fixture"
    assert all(row["dispatch"] is False for row in plan["research_jobs"])
    assert all(row["evidence_return_status"] == "pending_ingestion" for row in plan["research_jobs"])


def test_claim_and_asset_indexes_are_practice_only() -> None:
    opportunity, practice, fit, programs, possibility, frontier, evidence_return = _chain()
    plan = compile_product_plan(
        opportunity, practice, fit, programs, possibility, frontier, evidence_return
    )
    practice_refs = {
        row["artifact_ref"] for row in practice["artifacts"]
    }
    opportunity_refs = {
        row["evidence_id"] for row in opportunity["evidence"]
    }
    assert all(row["evidence_scope"] == "practice" for row in plan["claim_index"])
    assert all(row["evidence_scope"] == "practice" for row in plan["asset_index"])
    assert all(
        set(row["evidence_refs"]).issubset(practice_refs)
        for row in plan["claim_index"]
    )
    assert not any(
        set(row["evidence_refs"]) & opportunity_refs
        for row in plan["claim_index"]
    )
    assert plan["reconciliation"]["external_evidence_in_claim_index"] == 0


def test_selected_claims_and_asset_program_links_survive_portfolio_cross_smoke() -> None:
    inputs = _chain()
    opportunity, practice, fit, programs, possibility, frontier, evidence_return = inputs
    plan = compile_product_plan(*inputs)
    source_by_id = {row["program_id"]: row for row in programs["candidates"]}

    for selected in plan["selected_programs"]:
        source = source_by_id[selected["program_id"]]
        assert selected["supported_claim_ids"] == source["supported_claim_ids"]
        assert selected["candidate_claim_ids"] == source["candidate_claim_ids"]
        assert set(selected["supported_claim_ids"] + selected["candidate_claim_ids"]).issubset(
            {row["claim_id"] for row in plan["claim_index"]}
        )

    selected_ids = {row["program_id"] for row in plan["selected_programs"]}
    assert all(set(row["program_ids"]).issubset(selected_ids) for row in plan["asset_index"])
    assert all(row["program_ids"] for row in plan["asset_index"])
    assert len(plan["asset_index"]) == len({row["artifact_ref"] for row in practice["artifacts"]})
    assert len({row["content_id"] for row in practice["artifacts"]}) < len(plan["asset_index"])

    dossier = compile_portfolio_dossier(plan, practice)
    assert any(atom["type"] == "documented_fact" for atom in dossier["narrative_atoms"])
    gate = next(row for row in dossier["requirement_coverage"] if row["requirement_id"] == "req:gate")
    assert gate["missing"] is False
    assert gate["supported_claim_ids"] == ["claim:gate"]
    assert len(dossier["asset_manifest"]) == len(plan["asset_index"])


def test_foreign_claim_and_asset_program_refs_fail_closed() -> None:
    inputs = _chain()
    plan = compile_product_plan(*inputs)

    bad_claims = copy.deepcopy(plan)
    bad_claims["selected_programs"][0]["supported_claim_ids"] = ["claim:foreign"]
    with pytest.raises(ProductPlanError):
        validate_product_plan(*inputs, bad_claims)

    bad_programs = copy.deepcopy(plan)
    bad_programs["asset_index"][0]["program_ids"] = ["program:foreign"]
    with pytest.raises(ProductPlanError):
        validate_product_plan(*inputs, bad_programs)


def test_evidence_return_stays_pending_and_never_promotes() -> None:
    inputs = _chain(source_status="observed_local", confirmed=False)
    plan = compile_product_plan(*inputs)
    assert plan["provenance"]["evidence_return_status"] == "pending_ingestion"
    assert plan["reconciliation"]["truth_promotions"] == 0
    assert plan["control"]["promotion"] == "none"
    assert plan["control"]["training_permitted"] is False
    assert plan["gaps"]


def test_compile_is_deterministic_and_does_not_mutate_inputs() -> None:
    inputs = _chain(source_status="observed_local", confirmed=False)
    original = copy.deepcopy(inputs)
    first = compile_product_plan(*inputs)
    second = compile_product_plan(*copy.deepcopy(inputs))
    assert first == second
    assert stable_json(first) == stable_json(second)
    assert inputs == original
    assert validate_product_plan(*inputs, first) is True


def test_foreign_program_evidence_fails_closed() -> None:
    inputs = list(_chain())
    bad_programs = copy.deepcopy(inputs[3])
    bad_programs["candidates"][0]["evidence_refs"].append("web:foreign")
    with pytest.raises(ProductPlanError):
        compile_product_plan(*inputs[:3], bad_programs, *inputs[4:])


def test_invalid_evidence_return_job_reference_fails_closed() -> None:
    inputs = list(_chain(source_status="observed_local", confirmed=False))
    bad_return = copy.deepcopy(inputs[6])
    bad_return["unresolved"].append({
        "job_id": "foreign-job",
        "requirement_id": "foreign-requirement",
        "status": "unresolved",
    })
    with pytest.raises(ProductPlanError):
        compile_product_plan(*inputs[:6], bad_return)


def test_cli_compiles_seven_contract_files(tmp_path: Path) -> None:
    inputs = _chain(source_status="observed_local", confirmed=False)
    paths = []
    for index, value in enumerate(inputs):
        path = tmp_path / f"input-{index}.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        paths.append(str(path))
    completed = subprocess.run(
        [sys.executable, "tools/compile_product_plan.py", *paths],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["schema"] == SCHEMA
    assert output["targets"]["application_draft"]["status"] == "blocked"


def test_malformed_contract_fails_closed_before_product_projection() -> None:
    inputs = list(_chain())
    bad_frontier = copy.deepcopy(inputs[5])
    bad_frontier["schema"] = "wrong"
    with pytest.raises(ProductPlanError):
        compile_product_plan(*inputs[:5], bad_frontier, inputs[6])
