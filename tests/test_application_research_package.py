import copy
import json
import subprocess
import sys
from pathlib import Path

from flujo.knowledge.application_research_package import (
    _stable_hash,
    compile_application_research_package,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def opportunity(source="current_verified", confirmed=True):
    return {"schema": "mak-opportunity-constraints-v1", "opportunity_id": "opp-1", "source": {"validity": {"status": source, "confirmed": confirmed}}, "hard_gates": ["gate"], "constraints": [{"constraint_id": "gate", "kind": "hard_gate", "required": True}, {"constraint_id": "doc", "kind": "required_document", "required": True}]}


def program(pid, *, source="pass", hard="pass", ready=True, missing=None):
    return {"program_id": pid, "selection": "selected", "rank": 1, "unit_ids": [f"unit-{pid}"], "evidence_refs": [f"artifact-{pid}"], "requirement_ids": ["gate", "doc"], "missing_requirement_ids": missing or [], "risk_flags": [], "source_gate_status": source, "hard_gate_status": hard, "ready": ready}


def plan(*, source="pass", target_app="draftable", target_research="not_required", programs=None, jobs=None, claim_index=None):
    return {"schema": "mak-product-plan-v1", "plan_id": "plan-1", "opportunity_id": "opp-1", "selected_programs": programs or [program("p1"), program("p2", ready=True)], "targets": {"application_draft": {"status": target_app}, "research_brief": {"status": target_research}}, "claim_index": claim_index or {}, "research_jobs": jobs or [], "control": {"submission": False, "dispatch": False}, "source_gate_status": source, "hard_gate_status": "pass"}


def job(job_id, reqs):
    return {"job_id": job_id, "requirement_ids": reqs, "question": "Confirm the document", "domain": "general", "priority_rank": 1, "independent_source_groups_required": 2, "status": "planned_not_dispatched", "source_policy": "local_first", "source_groups": ["call"]}


def test_verified_real_4a_shape_is_draftable_and_preserves_programs():
    out = compile_application_research_package(plan(), opportunity())
    assert out["application_draft"]["status"] == "draftable"
    assert out["application_draft"]["program_ids"] == ["p1", "p2"]
    assert out["research_brief"]["status"] == "not_required"
    assert out["research_brief"]["jobs"] == []


def test_observed_local_real_shape_blocks_application_but_keeps_two_jobs():
    jobs = [job("j1", ["source-validity:opp-1"]), job("j2", ["source-validity:opp-1"])]
    out = compile_application_research_package(plan(source="abstain", target_app="blocked", target_research="draftable", jobs=jobs), opportunity("observed_local", False))
    assert out["application_draft"]["status"] == "blocked_with_reasons"
    assert out["research_brief"]["status"] == "draftable"
    assert len(out["research_brief"]["jobs"]) == 2
    assert out["research_brief"]["rejected_jobs"] == []
    assert all(item["dispatch"] is False for item in out["research_brief"]["jobs"])


def test_required_document_missing_is_visible():
    out = compile_application_research_package(plan(programs=[program("p1", missing=["doc"])]), opportunity())
    assert out["application_draft"]["status"] == "blocked_with_reasons"
    assert next(row for row in out["application_draft"]["requirements"] if row["requirement_id"] == "doc")["status"] == "missing"


def test_foreign_job_rejected():
    out = compile_application_research_package(plan(target_research="draftable", jobs=[job("foreign", ["not-in-plan"])]), opportunity())
    assert out["research_brief"]["jobs"] == []
    assert out["research_brief"]["rejected_jobs"][0]["reason"] == "job_requirement_not_in_plan_or_opportunity"


def test_deterministic_and_no_mutation():
    p, o = plan(), opportunity()
    before = (copy.deepcopy(p), copy.deepcopy(o))
    assert compile_application_research_package(p, o) == compile_application_research_package(copy.deepcopy(p), copy.deepcopy(o))
    assert (p, o) == before


def test_package_declares_consumed_plan_and_opportunity_hashes():
    p, o = plan(), opportunity()
    out = compile_application_research_package(p, o)
    assert out["input_hashes"] == {
        "product_plan": _stable_hash(p),
        "opportunity_constraints": _stable_hash(o),
    }


def test_cli(tmp_path):
    pp, op = tmp_path / "plan.json", tmp_path / "opp.json"
    pp.write_text(json.dumps(plan()), encoding="utf-8")
    op.write_text(json.dumps(opportunity()), encoding="utf-8")
    run = subprocess.run([sys.executable, "tools/compile_application_research_package.py", str(pp), str(op)], cwd=REPO_ROOT, capture_output=True, text=True)
    assert run.returncode == 0
    assert json.loads(run.stdout)["schema"] == "mak-application-research-package-v1"
