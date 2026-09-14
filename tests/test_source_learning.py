"""Tests for traceable source-memory ingestion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from flujo.knowledge.learning_policy import compile_dataset
from flujo.knowledge.source_learning import build_learning_project, ingest_case, verify_case


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    conversation_id = "conversation-fixture"
    message_id = "message-fixture"
    text = "Choosing an ordering dimension changes the search."
    export = tmp_path / "conversations.json"
    export.write_text(json.dumps([{
        "uuid": conversation_id,
        "chat_messages": [{"uuid": message_id, "sender": "human", "text": text}],
    }]), encoding="utf-8")
    audit = tmp_path / "audit.md"
    audit.write_text("The verification claim fails; underlying truth remains open.\n", encoding="utf-8")
    case = tmp_path / "case.json"
    case.write_text(json.dumps({
        "schema": "mak-source-learning-case-v1",
        "case_id": "fixture-source-learning",
        "title": "Fixture source learning",
        "objective": "Join one hypothesis and one bounded audit.",
        "source_sets": [
            {
                "source_id": "dialogue-set", "root": str(tmp_path),
                "role": "hypothesis_memory", "selection_policy": "Select one message by hash.",
            },
            {
                "source_id": "audit-set", "root": str(tmp_path),
                "role": "bounded_audit", "selection_policy": "Select one audit by hash.",
            },
        ],
        "source_artifacts": [
            {
                "artifact_id": "dialogue", "source_set": "dialogue-set",
                "path": str(export), "sha256": _sha256(export),
                "kind": "conversation_export", "role": "hypothesis_origin",
            },
            {
                "artifact_id": "audit", "source_set": "audit-set",
                "path": str(audit), "sha256": _sha256(audit),
                "kind": "research_artifact", "role": "audited_result",
            },
        ],
        "message_refs": [{
            "ref_id": "message-order", "artifact_id": "dialogue",
            "conversation_id": conversation_id, "message_id": message_id,
            "sender": "human", "epistemic_class": "user_hypothesis",
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "contribution": "Ordering hypothesis.",
        }],
        "findings": [{
            "finding_id": "finding-order", "statement": "Treat order as a search variable.",
            "epistemic_class": "synthesis_candidate", "status": "candidate",
            "evidence_refs": ["message-order", "audit"],
        }],
        "learning_units": [{
            "unit_id": "unit-order", "lesson": "Representation affects search.",
            "action": "Declare it before search.", "guardrail": "Do not promote truth from compression.",
            "status": "candidate", "evidence_refs": ["finding-order"],
        }],
        "verification_ladder": [
            {"order": 1, "gate": "Freeze target.", "failure_action": "abstain"},
        ],
        "non_claims": [
            {
                "claim_id": "p_equals_np_proven", "statement": "P equals NP is proven.",
                "status": "excluded", "reason": "Outside ingestion scope.",
            },
            {
                "claim_id": "handwritten_argument_refuted", "statement": "All arguments are refuted.",
                "status": "excluded", "reason": "Outside audit scope.",
            },
        ],
    }), encoding="utf-8")
    return case, export


def test_case_verifies_and_routes_to_source_learning_bridge(tmp_path):
    case, _ = _fixture(tmp_path)
    verification = verify_case(case)
    assert verification["status"] == "passed"
    assert verification["mathematical_truth_validated"] is False
    project = build_learning_project(case, verification)
    assert project["state"] == "active"
    assert project["source"]["kind"] == "source_memory"
    assert project["layer"] == "cultural_research_first"
    result = ingest_case(case)
    assert result["route_contract_passed"] is True
    assert result["route"]["selected"]["tool_id"] == "source_learning_bridge"


def test_changed_source_fails_closed(tmp_path):
    case, export = _fixture(tmp_path)
    export.write_text("[]", encoding="utf-8")
    result = ingest_case(case)
    assert result["verification"]["status"] == "failed"
    assert result["recorded"] is False
    failed = [item for item in result["verification"]["checks"] if item["status"] == "failed"]
    assert {item["check"] for item in failed} == {
        "source_artifact_sha256", "conversation_message_sha256",
    }


def test_verified_ingestion_is_idempotent_learning_episode(tmp_path):
    case, _ = _fixture(tmp_path)
    database = tmp_path / "learning.sqlite"
    first = ingest_case(case, database=database, record=True)
    payload = json.loads(case.read_text(encoding="utf-8"))
    case.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    second = ingest_case(case, database=database, record=True)
    assert first["recorded"] is True
    assert first["episode_id"] == second["episode_id"]
    dataset = compile_dataset(database)
    assert len(dataset.examples) == 1
    assert dataset.examples[0].label == "source_learning_bridge"


def test_required_non_claim_boundaries_fail_closed(tmp_path):
    case, _ = _fixture(tmp_path)
    payload = json.loads(case.read_text(encoding="utf-8"))
    payload["non_claims"] = payload["non_claims"][:1]
    case.write_text(json.dumps(payload), encoding="utf-8")
    verification = verify_case(case)
    assert verification["status"] == "failed"
    contract = next(item for item in verification["checks"] if item["check"] == "epistemic_contract")
    assert "required_non_claim_missing:handwritten_argument_refuted" in contract["errors"]
