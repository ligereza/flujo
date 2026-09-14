"""Read-only context separating evaluation, recording, promotion and learning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._contract_helpers import count_map as _count_map, nonnegative_int as _int, required_mapping as _mapping, required_text as _text

SCHEMA = "mak-learning-read-only-context-v1"
ALGORITHM_VERSION = "learning-read-only-context-1"
_CONTROL = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False}


def build_learning_read_only_context(status: Mapping[str, Any], learning: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    status = _mapping(status, "status"); learning = _mapping(learning, "learning"); policy = _mapping(learning.get("policy"), "learning.policy"); evaluation = _mapping(policy.get("evaluation"), "learning.policy.evaluation"); excluded = _count_map(policy.get("excluded", {}), "learning.policy.excluded")
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "source": {"status_schema": _text(status.get("schema"), "status.schema"), "learning_database": _text(learning.get("database"), "learning.database"), "learning_available": learning.get("available") is True}, "policy": {"schema": _text(policy.get("schema"), "policy.schema"), "status": _text(policy.get("status"), "policy.status"), "reason": _text(policy.get("reason"), "policy.reason"), "eligible_examples": _int(policy.get("eligible_examples"), "policy.eligible_examples"), "excluded": excluded, "recordable": policy.get("recordable") is True, "train_count": _int(evaluation.get("train_count"), "evaluation.train_count"), "holdout_count": _int(evaluation.get("holdout_count"), "evaluation.holdout_count"), "holdout_accuracy": evaluation.get("holdout_accuracy"), "holdout_baseline": evaluation.get("holdout_baseline")}, "ledger": {"projects": _count_map(learning.get("projects", {}), "learning.projects"), "episodes": _count_map(learning.get("episodes", {}), "learning.episodes"), "episodes_open": _count_map(learning.get("episodes_open", {}), "learning.episodes_open"), "rules": _count_map(learning.get("rules", {}), "learning.rules")}, "boundary": {"evaluation_is_not_learning": True, "candidate_policy_is_not_promotion": True, "recordable_is_not_execution": True, "abstentions_are_safe": True, "semantic_claim": False, "learning_demonstrated": False}, "control": dict(_CONTROL), "next_action": "keep_candidate_policy_separate_from_verified_knowledge_and_require_human_review"}
    validate_learning_read_only_context(result); return result


def validate_learning_read_only_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("learning_context_header_invalid")
    if set(payload) != {"schema", "algorithm_version", "available", "read_only", "generated_at", "source", "policy", "ledger", "boundary", "control", "next_action"}: raise ValueError("learning_context_fields_invalid")
    _text(payload["generated_at"], "generated_at"); source = payload["source"]
    if set(source) != {"status_schema", "learning_database", "learning_available"} or source["learning_available"] is not True: raise ValueError("learning_context_source_invalid")
    _text(source["status_schema"], "source.status_schema"); _text(source["learning_database"], "source.learning_database"); policy = payload["policy"]
    if set(policy) != {"schema", "status", "reason", "eligible_examples", "excluded", "recordable", "train_count", "holdout_count", "holdout_accuracy", "holdout_baseline"} or policy["status"] != "candidate" or policy["reason"] != "holdout_gate_passed" or policy["recordable"] is not True: raise ValueError("learning_context_policy_invalid")
    for field in ("schema", "status", "reason"): _text(policy[field], f"policy.{field}")
    for field in ("eligible_examples", "train_count", "holdout_count"): _int(policy[field], f"policy.{field}")
    _count_map(policy["excluded"], "policy.excluded")
    for field in ("holdout_accuracy", "holdout_baseline"):
        if not isinstance(policy[field], (int, float)) or isinstance(policy[field], bool) or not 0 <= policy[field] <= 1: raise ValueError(f"policy.{field}_invalid")
    ledger = payload["ledger"]
    if set(ledger) != {"projects", "episodes", "episodes_open", "rules"}: raise ValueError("learning_context_ledger_invalid")
    for field in ledger: _count_map(ledger[field], f"ledger.{field}")
    if payload["boundary"] != {"evaluation_is_not_learning": True, "candidate_policy_is_not_promotion": True, "recordable_is_not_execution": True, "abstentions_are_safe": True, "semantic_claim": False, "learning_demonstrated": False}: raise ValueError("learning_context_boundary_invalid")
    if payload["control"] != _CONTROL: raise ValueError("learning_context_control_invalid")
    _text(payload["next_action"], "next_action"); return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_learning_read_only_context", "validate_learning_read_only_context"]
