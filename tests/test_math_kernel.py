"""Tests for the cultural-first metadata-only Math Kernel MVP."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from flujo.knowledge.math_kernel import (
    CARD_SCHEMA,
    build_math_project,
    classify_result,
    fingerprint,
    load_target,
    math_summary,
    record_result_card,
    run_cycle,
    save_target,
    validate_target,
)
from flujo.knowledge.project_router import route_project


ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = ROOT / "knowledge" / "math_targets" / "p_vs_np_target_capsule_2026-08-19.json"
OFFICIAL_CAPTURE_PATH = ROOT / "knowledge" / "math_targets" / "p_vs_np_official_statement_capture_2026-08-20.json"
FORMAL_TARGET_PATH = Path("/home/mak/curatoria_inbox/MAK_TODO_SESION_2026-08-19/ARTIFACTS/MAK_AUDIT_P_EQUALS_NP_PEDIGREE_POLYTOPES_2026-08-19.md")


def _card(target: dict, *, status: str = "SURVIVED") -> dict:
    return {
        "schema": CARD_SCHEMA,
        "card_id": "card-fixture-" + status.lower(),
        "target_id": target["target_id"],
        "candidate_id": "candidate-fixture",
        "status": status,
        "validator": "fixture-counterexample-engine",
        "validator_version": "1",
        "candidate_hash": "candidate-hash",
        "target_hash": fingerprint(target),
        "semantic_fidelity": target["semantic_fidelity_status"],
        "failure_class": "NO_COUNTEREXAMPLE_FOUND" if status == "SURVIVED" else "candidate_check",
        "next_actions": [],
        "artifact_refs": ["blob://sha256/fixture"],
        "scope": "fixture",
    }


def test_pnp_capsule_is_cultural_first_and_untrusted() -> None:
    target = load_target(TARGET_PATH)
    assert validate_target(target) == []
    assert target["layer"] == "cultural_research_first"
    assert target["conceptual_frame"]["theorem_claim_excluded"] is True
    project = build_math_project(target, TARGET_PATH)
    assert project["state"] == "review_required"
    assert project["layer"] == "cultural_research_first"
    assert {"cultura", "curatoria", "portfolio", "research", "mathematics"} <= set(project["domains"])


def test_pnp_statement_and_formal_target_hashes_are_captured() -> None:
    target = load_target(TARGET_PATH)
    capture = json.loads(OFFICIAL_CAPTURE_PATH.read_text(encoding="utf-8"))
    assert capture["source_url"].startswith("https://www.claymath.org/")
    assert capture["page_status"] == "Unsolved"
    canonical = capture["canonical_statement"].encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == capture["canonical_statement_hash"]
    assert target["official_statement_hash"] == capture["canonical_statement_hash"]
    if not FORMAL_TARGET_PATH.is_file():
        pytest.skip("external formal-target artifact is not present in this clone")
    assert hashlib.sha256(FORMAL_TARGET_PATH.read_bytes()).hexdigest() == target["formal_target_hash"]
    assert target["semantic_fidelity_status"] == "UNTRUSTED"


def test_curated_math_target_has_a_typed_common_layer_route() -> None:
    target = load_target(TARGET_PATH)
    project = build_math_project(target, TARGET_PATH)
    project["state"] = "active"  # simulate the post-curation gate only
    decision = route_project(project)
    assert decision["decision"] == "select"
    assert decision["selected"]["tool_id"] == "math_kernel"


def test_cycle_queues_metadata_only_work_and_blocks_truth_promotion(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite"
    result = run_cycle(database, TARGET_PATH, iterations=2, compute_units=3, max_expanded_cost=41)
    assert result["target_fidelity"] == "UNTRUSTED"
    assert result["truth_promotion"] == "blocked_until_semantic_fidelity_and_trusted_verifier"
    assert len(result["requests"]) == 2
    assert {item["policy"] for item in result["requests"]} == {"SIMPLE"}
    assert all(item["visibility"] == "METADATA_ONLY" for item in result["requests"])
    assert all(item["next_gate"] == "semantic_target_curator_before_truth_promotion" for item in result["requests"])
    summary = math_summary(database)
    assert summary["requests"] == {"queued": 2}


def test_untrusted_target_downgrades_formal_proof_card() -> None:
    target = load_target(TARGET_PATH)
    card = _card(target, status="PROOF_VERIFIED")
    card.update({
        "certificate_ref": "blob://sha256/certificate",
        "axiom_report": "CLEAN",
        "dependency_lock_hash": "lock-hash",
    })
    classified = classify_result(target, card)
    assert classified["status"] == "FORMAL_TARGET_UNTRUSTED"
    assert classified["failure_class"] == "TARGET_SEMANTIC_UNTRUSTED"
    assert "ESCALATE_MATH_CURATOR" in classified["next_actions"]


def test_no_counterexample_is_survival_not_truth(tmp_path: Path) -> None:
    target = load_target(TARGET_PATH)
    save_target(tmp_path / "learning.sqlite", TARGET_PATH)
    card = _card(target, status="SURVIVED")
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps(card), encoding="utf-8")
    recorded = record_result_card(tmp_path / "learning.sqlite", card_path)
    assert recorded["status"] == "SURVIVED"
    assert recorded["scope"] == "metadata_verifier_result_only"
    assert math_summary(tmp_path / "learning.sqlite")["cards"] == {"SURVIVED": 1}


def test_verified_target_can_accept_clean_proof_metadata(tmp_path: Path) -> None:
    target = load_target(TARGET_PATH)
    verified = copy.deepcopy(target)
    verified["semantic_fidelity_status"] = "VERIFIED"
    verified["formal_target_hash"] = "curated-formal-target-hash"
    verified_path = tmp_path / "verified-target.json"
    verified_path.write_text(json.dumps(verified), encoding="utf-8")
    save_target(tmp_path / "learning.sqlite", verified_path)
    card = _card(verified, status="PROOF_VERIFIED")
    card.update({
        "certificate_ref": "blob://sha256/certificate",
        "axiom_report": "CLEAN",
        "dependency_lock_hash": "lock-hash",
    })
    card_path = tmp_path / "proof-card.json"
    card_path.write_text(json.dumps(card), encoding="utf-8")
    recorded = record_result_card(tmp_path / "learning.sqlite", card_path)
    assert recorded["status"] == "PROOF_VERIFIED"
