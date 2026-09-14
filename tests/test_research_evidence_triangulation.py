from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.research_evidence_triangulation import (
    ResearchTriangulationError,
    adapt_execute_research_report,
    assert_research_triangulation,
    stable_json,
    triangulate_research_evidence,
)


def _hash(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _frontier(required: int = 2) -> dict:
    return {
        "schema": "mak-research-frontier-jobs-v1",
        "algorithm_version": "frontier-fixture-1",
        "independent_source_groups_required": required,
        "jobs": [{
            "job_id": "job:one",
            "question": "Which source-backed condition is observed?",
            "requirement_ids": ["req:one"],
            "independent_source_groups_required": required,
            "dispatch": False,
        }],
    }


def _source(source_id: str, group: str, domain: str) -> dict:
    return {
        "source_id": source_id,
        "source_group": group,
        "url": f"https://{domain}/page",
        "raw_sha256": _hash(source_id + ":raw"),
        "text_sha256": _hash(source_id + ":text"),
        "capture_status": "captured",
        "license_state": "unknown_pending_source_review",
    }


def _claim(claim_id: str, relation: str, sources: list[str], refs: list[str], *, value: str = "observed") -> dict:
    return {
        "claim_id": claim_id,
        "requirement_id": "req:one",
        "relation": relation,
        "statement": "The bounded evidence reports the same condition.",
        "value": value,
        "evidence_refs": refs,
        "source_ids": sources,
        "extraction_status": "candidate",
    }


def _batch(*, claims: list[dict], sources: list[dict], status: str = "captured") -> dict:
    return {
        "schema": "mak-research-result-batch-v1",
        "algorithm_version": "result-fixture-1",
        "results": [{
            "job_id": "job:one",
            "requirement_id": "req:one",
            "status": status,
            "sources": sources,
            "claims": claims,
        }],
    }


def _support_batch() -> dict:
    sources = [_source("source:a", "group:a", "a.example"), _source("source:b", "group:b", "b.example")]
    return _batch(claims=[
        _claim("claim:a", "supports", ["source:a"], ["evidence:a"]),
        _claim("claim:b", "supports", ["source:b"], ["evidence:b"]),
    ], sources=sources)


def test_two_independent_groups_produce_supported_candidate() -> None:
    report = triangulate_research_evidence(_frontier(), _support_batch())
    assert report["valid"] is True
    row = report["results"][0]
    assert row["status"] == "supported_candidate"
    assert row["independent_source_groups"] == ["group:a", "group:b"]
    assert row["evidence_refs"] == ["evidence:a", "evidence:b"]
    assert row["promotion"] == "none"
    assert row["learning_features"]["training_permitted"] is False


def test_same_group_or_domain_does_not_count_as_independence() -> None:
    same_group = _batch(
        claims=[
            _claim("claim:a", "supports", ["source:a"], ["evidence:a"]),
            _claim("claim:b", "supports", ["source:b"], ["evidence:b"]),
        ],
        sources=[_source("source:a", "group:a", "same.example"), _source("source:b", "group:a", "other.example")],
    )
    same_domain = _batch(
        claims=[
            _claim("claim:a", "supports", ["source:a"], ["evidence:a"]),
            _claim("claim:b", "supports", ["source:b"], ["evidence:b"]),
        ],
        sources=[_source("source:a", "group:a", "same.example"), _source("source:b", "group:b", "same.example")],
    )
    for batch in (same_group, same_domain):
        row = triangulate_research_evidence(_frontier(), batch)["results"][0]
        assert row["status"] == "unresolved"
        assert "insufficient_independent_source_groups" in row["gaps"]


def test_contradiction_and_support_reaching_threshold_are_mixed_conflict() -> None:
    sources = [
        _source("source:a", "group:a", "a.example"),
        _source("source:b", "group:b", "b.example"),
        _source("source:c", "group:c", "c.example"),
        _source("source:d", "group:d", "d.example"),
    ]
    claims = [
        _claim("support:a", "supports", ["source:a"], ["evidence:sa"]),
        _claim("support:b", "supports", ["source:b"], ["evidence:sb"]),
        _claim("contra:c", "contradicts", ["source:c"], ["evidence:ca"], value="different"),
        _claim("contra:d", "contradicts", ["source:d"], ["evidence:cb"], value="different"),
    ]
    row = triangulate_research_evidence(_frontier(), _batch(claims=claims, sources=sources))["results"][0]
    assert row["status"] == "mixed_conflict"
    assert row["counterevidence_refs"] == ["evidence:ca", "evidence:cb", "evidence:sa", "evidence:sb"]


def test_one_relation_reaching_threshold_is_contradicted_candidate() -> None:
    sources = [_source("source:a", "group:a", "a.example"), _source("source:b", "group:b", "b.example")]
    claims = [
        _claim("claim:a", "contradicts", ["source:a"], ["evidence:a"], value="no"),
        _claim("claim:b", "contradicts", ["source:b"], ["evidence:b"], value="no"),
    ]
    row = triangulate_research_evidence(_frontier(), _batch(claims=claims, sources=sources))["results"][0]
    assert row["status"] == "contradicted_candidate"
    assert row["promotion"] == "none"


def test_execute_report_adapter_with_no_claims_can_never_support() -> None:
    report = {
        "job_id": 17,
        "question": "A bounded capture question",
        "status": "captured",
        "sources": [{
            "url": "https://official.example/page",
            "raw_sha256": _hash("raw"),
            "text_sha256": _hash("text"),
            "status": "captured",
            "license_state": "unknown_pending_source_review",
        }],
    }
    adapted = adapt_execute_research_report(report, requirement_id="req:one")
    assert adapted["results"][0]["question"] == report["question"]
    adapter_frontier = _frontier(required=1)
    adapter_frontier["jobs"][0]["job_id"] = "17"
    result = triangulate_research_evidence(adapter_frontier, adapted)
    assert result["valid"] is True
    assert result["results"][0]["question"] == adapter_frontier["jobs"][0]["question"]
    assert result["results"][0]["status"] == "unresolved"
    assert "no_extracted_claims" in result["results"][0]["gaps"]


def test_failed_capture_is_distinguished_from_no_claims() -> None:
    source = _source("source:failed", "group:failed", "failed.example")
    source["capture_status"] = "failed"
    source["raw_sha256"] = ""
    source["text_sha256"] = ""
    row = triangulate_research_evidence(_frontier(), _batch(claims=[], sources=[source], status="capture_failed"))["results"][0]
    assert row["status"] == "failed_capture"


@pytest.mark.parametrize("mutation,expected", [
    ("claim_refs", "claim_evidence_refs_missing"),
    ("claim_sources", "claim_source_ids_missing"),
    ("wrong_relation", "claim_relation_invalid"),
    ("wrong_extraction", "claim_extraction_status_invalid"),
    ("source_hash", "source_text_hash_missing_or_invalid"),
    ("source_group", "source_group_missing"),
])
def test_malformed_claim_or_source_fails_closed(mutation: str, expected: str) -> None:
    batch = _support_batch()
    if mutation == "claim_refs":
        batch["results"][0]["claims"][0]["evidence_refs"] = []
    elif mutation == "claim_sources":
        batch["results"][0]["claims"][0]["source_ids"] = []
    elif mutation == "wrong_relation":
        batch["results"][0]["claims"][0]["relation"] = "supports_or_truth"
    elif mutation == "wrong_extraction":
        batch["results"][0]["claims"][0]["extraction_status"] = "supported"
    elif mutation == "source_hash":
        batch["results"][0]["sources"][0]["text_sha256"] = ""
    elif mutation == "source_group":
        batch["results"][0]["sources"][0]["source_group"] = ""
    report = triangulate_research_evidence(_frontier(), batch)
    assert report["valid"] is False
    assert any(error["code"] == expected for error in report["errors"])
    assert report["results"][0]["status"] != "supported_candidate"


def test_duplicate_claim_and_source_replay_is_deterministic_and_non_mutating() -> None:
    frontier = _frontier()
    batch = _support_batch()
    original = copy.deepcopy(batch)
    reordered = copy.deepcopy(batch)
    reordered["results"][0]["sources"].reverse()
    reordered["results"][0]["claims"].reverse()
    first = triangulate_research_evidence(frontier, [batch, batch])
    second = triangulate_research_evidence(copy.deepcopy(frontier), [reordered])
    assert first == second
    assert batch == original


def test_frontier_or_batch_schema_mismatch_is_reported() -> None:
    bad_frontier = _frontier()
    bad_frontier["schema"] = "wrong"
    bad_batch = _support_batch()
    bad_batch["schema"] = "wrong"
    report = triangulate_research_evidence(bad_frontier, bad_batch)
    assert report["valid"] is False
    assert {error["code"] for error in report["errors"]} >= {
        "frontier_schema_invalid", "result_batch_schema_invalid",
    }


def test_result_pair_not_declared_by_frontier_is_reconciled_and_invalid() -> None:
    batch = _support_batch()
    batch["results"][0]["job_id"] = "job:foreign"
    report = triangulate_research_evidence(_frontier(), batch)
    assert report["valid"] is False
    assert report["results"][0]["status"] == "unresolved"
    assert report["reconciliation"]["unexpected_result_pair_count"] == 1
    assert report["reconciliation"]["unexpected_result_pairs"] == [{
        "job_id": "job:foreign",
        "requirement_id": "req:one",
        "statuses": ["captured"],
        "source_count": 2,
        "claim_count": 2,
    }]
    assert any(error["code"] == "result_pair_not_in_frontier" for error in report["errors"])
    assert report["promotion"] == "none"
    assert report["learning_features"]["training_permitted"] is False


def test_realistic_3a_refresh_gets_one_unresolved_technical_requirement() -> None:
    frontier = {
        "schema": "mak-research-frontier-jobs-v1",
        "algorithm_version": "possibility-to-research-frontier-1",
        "opportunity_id": "opp:fondart-2027",
        "jobs": [{
            "job_id": "job:refresh",
            "candidate_id": "program:bounded",
            "opportunity_id": "opp:fondart-2027",
            "requirement_ids": [],
            "research_action_ids": [],
            "question": "Verify current validity of opportunity opp:fondart-2027 from an official source",
            "domain": "general",
            "priority_rank": 1,
            "voi": {"value": None, "status": "unresolved", "numerator": None, "denominator": None},
            "source_policy": "official-source-only",
            "independent_source_groups_required": 1,
            "status": "planned_not_dispatched",
            "dispatch": False,
            "provenance": {"frontier_kind": "refresh_source_validity"},
        }],
    }
    adapted = adapt_execute_research_report(
        {
            "job_id": "job:refresh",
            "question": frontier["jobs"][0]["question"],
            "status": "captured",
            "sources": [],
        },
        requirement_id="source-validity:opp:fondart-2027",
        independent_source_groups_required=1,
    )
    report = triangulate_research_evidence(frontier, adapted)
    assert report["valid"] is True
    assert len(report["results"]) == 1
    assert report["results"][0]["requirement_id"] == "source-validity:opp:fondart-2027"
    assert report["results"][0]["status"] == "unresolved"
    assert report["results"][0]["promotion"] == "none"
    assert report["results"][0]["learning_features"]["training_permitted"] is False


def test_non_json_claim_semantics_fail_closed_without_raising() -> None:
    batch = _support_batch()
    batch["results"][0]["claims"][0]["value"] = float("nan")
    report = triangulate_research_evidence(_frontier(), batch)
    assert report["valid"] is False
    assert any(error["code"] == "claim_semantics_not_serializable" for error in report["errors"])


def test_assertion_and_cli_stdout_output(tmp_path: Path) -> None:
    frontier_path = tmp_path / "frontier.json"
    result_path = tmp_path / "result.json"
    frontier = _frontier()
    batch = _support_batch()
    frontier_path.write_text(json.dumps(frontier), encoding="utf-8")
    result_path.write_text(json.dumps(batch), encoding="utf-8")
    assert assert_research_triangulation(frontier, batch) is True
    with pytest.raises(ResearchTriangulationError):
        assert_research_triangulation(frontier, {"schema": "wrong"})
    completed = subprocess.run([
        sys.executable, "tools/triangulate_research_evidence.py",
        "--frontier", str(frontier_path), "--results", str(result_path),
    ], cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    cli_report = json.loads(completed.stdout)
    assert cli_report["schema"] == "mak-research-triangulation-v1"
    assert cli_report["report_hash"].startswith("report:sha256:")
