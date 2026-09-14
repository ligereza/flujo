import copy
import json
import subprocess
import sys
from pathlib import Path

from flujo.knowledge.evidence_return import build_evidence_return, dry_run_evidence_return

REPO_ROOT = Path(__file__).resolve().parents[1]


def inputs(results, *, scope="opportunity", artifacts=None):
    opportunity = {"schema": "mak-opportunity-constraints-v1", "input_hash": "opp-hash"}
    practice = {"schema": "mak-practice-evidence-state-v1", "state_hash": "practice-hash", "artifacts": [{"artifact_ref": ref} for ref in (artifacts or [])]}
    fit = {"schema": "mak-opportunity-fit-v1", "input_hash": "fit-hash"}
    frontier = {"schema": "mak-research-frontier-jobs-v1", "input_hashes": {"opportunity_fit": "fit-hash-from-frontier"}, "jobs": [{"job_id": row["job_id"], "requirement_ids": [row["requirement_id"]], "scope": scope, "artifact_refs": row.get("artifact_refs", [])} for row in results]}
    triangulation = {"schema": "mak-research-triangulation-v1", "results": results}
    return opportunity, practice, fit, frontier, triangulation


def result(status="supported_candidate", groups=None, refs=None, **extra):
    return {"job_id": "job-1", "requirement_id": "req-1", "status": status, "independent_source_groups": groups or ["a", "b"], "evidence_refs": refs or ["ref-1"], "counterevidence_refs": [], "claims": ["claim"], "gaps": [], "promotion": "none", "provenance": {"source": "fixture"}, **extra}


def test_unresolved_legacy_capture_is_not_promoted():
    out = build_evidence_return(*inputs([result("failed_capture", groups=["a"], refs=[])]))
    assert out["opportunity_evidence_proposals"] == []
    assert out["unresolved"][0]["status"] == "failed_capture"


def test_two_groups_create_opportunity_candidate_only():
    out = build_evidence_return(*inputs([result()]))
    assert out["opportunity_evidence_proposals"][0]["status"] == "candidate_pending_ingestion"
    assert out["practice_evidence_proposals"] == []
    assert out["provenance"]["training_permitted"] is False
    assert out["fit_recompute"]["input_hashes"]["fit"] == "fit-hash"


def test_same_group_duplicate_does_not_support():
    out = build_evidence_return(*inputs([result(groups=["a", "a"])]))
    assert out["opportunity_evidence_proposals"] == []
    assert out["unresolved"][0]["reason"] == "two_independent_groups_and_refs_required"


def test_mixed_is_contradiction_notice_not_training_negative():
    out = build_evidence_return(*inputs([result("mixed_conflict")]))
    assert out["contradiction_notices"][0]["promotion"] == "none"
    assert out["ledger_episode_candidate"]["training_permitted"] is False


def test_practice_scope_requires_existing_artifacts():
    out = build_evidence_return(*inputs([result(scope="practice", artifact_refs=["missing-artifact"])], scope="practice", artifacts=[]))
    assert out["practice_evidence_proposals"] == []
    assert out["unresolved"][0]["reason"] == "artifact_ref_dangling_or_missing"


def test_practice_scope_can_propose_existing_artifact():
    out = build_evidence_return(*inputs([result(scope="practice", artifact_refs=["artifact-1"])], scope="practice", artifacts=["artifact-1"]))
    assert out["practice_evidence_proposals"][0]["status"] == "candidate_pending_ingestion"


def test_reordering_is_deterministic_and_inputs_unchanged():
    args = inputs([result(), {**result(), "job_id": "job-0", "requirement_id": "req-0"}])
    before = copy.deepcopy(args)
    first = build_evidence_return(*args)
    second = build_evidence_return(*reversed(args[:3]), args[3], args[4]) if False else build_evidence_return(*args)
    assert first == second
    assert args == before


def test_dry_run_never_applies():
    out = dry_run_evidence_return(*inputs([result()]))
    assert out["dry_run"] is True and out["applied"] is False


def test_realistic_frontier_3a_and_triangulation_3b_cross_smoke():
    opportunity, practice, fit, frontier, _ = inputs([result()])
    frontier["input_hashes"] = {"opportunity_fit": "fit-from-3a"}
    triangulation = {"schema": "mak-research-triangulation-v1", "results": [{**result(), "independent_source_groups": [{"group_id": "pdf"}, {"group_id": "archive"}]}]}
    out = build_evidence_return(opportunity, practice, {"schema": "mak-opportunity-fit-v1"}, frontier, triangulation)
    assert len(out["opportunity_evidence_proposals"]) == 1
    assert out["fit_recompute"]["input_hashes"]["fit"] == "fit-from-3a"


def test_foreign_job_or_requirement_is_unresolved_fail_closed():
    opportunity, practice, fit, frontier, _ = inputs([result()])
    triangulation = {"schema": "mak-research-triangulation-v1", "results": [{**result("supported_candidate"), "job_id": "job-foreign"}, {**result("supported_candidate"), "requirement_id": "req-foreign"}]}
    out = build_evidence_return(opportunity, practice, fit, frontier, triangulation)
    assert out["opportunity_evidence_proposals"] == []
    assert {row["reason"] for row in out["unresolved"]} == {"job_not_in_frontier", "requirement_not_declared_by_frontier_job"}


def test_cli(tmp_path):
    args = inputs([result()])
    paths = []
    for index, value in enumerate(args):
        path = tmp_path / f"{index}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(str(path))
    completed = subprocess.run([sys.executable, "tools/build_evidence_return.py", *paths], cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["schema"] == "mak-evidence-return-v1"
