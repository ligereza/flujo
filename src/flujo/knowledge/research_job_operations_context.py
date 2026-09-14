"""Read-only, job-specific continuation context for Research."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re

from ._contract_helpers import nonnegative_int as _int, required_mapping as _map, required_text as _text


SCHEMA = "mak-research-operations-context-v1"
ALGORITHM_VERSION = "research-job-operations-context-1"
_CONTROL = {"database_write": False, "decision_write": False, "promotion": "none", "publication": False, "execution": False, "external_calls": False}


def _sha(value: Any, field: str) -> str:
    value = _text(value, field).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value): raise ValueError(f"{field}_invalid")
    return value


def _same_hash(values: list[Mapping[str, Any]], field: str) -> str:
    hashes = [_sha(item.get("input_sha256"), field) for item in values if item.get("input_sha256")]
    if not hashes or len(set(hashes)) != 1: raise ValueError(f"{field}_mismatch")
    return hashes[0]


def build_research_job_operations_context(job_id: int, observed_job: Mapping[str, Any], readiness: Mapping[str, Any], plan: Mapping[str, Any], dry_run: Mapping[str, Any], license_review: Mapping[str, Any], source_review: Mapping[str, Any], compatibility: Mapping[str, Any], learning: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    observed_job = _map(observed_job, "observed_job"); readiness = _map(readiness, "readiness"); plan = _map(plan, "plan"); dry_run = _map(dry_run, "dry_run"); license_review = _map(license_review, "license_review"); source_review = _map(source_review, "source_review"); compatibility = _map(compatibility, "compatibility"); learning = _map(learning, "learning")
    job_id = _int(job_id, "job_id"); hashes = _same_hash([readiness, plan, dry_run, license_review, source_review, compatibility], "input_sha256")
    policy = learning.get("policy") if isinstance(learning.get("policy"), Mapping) else {}; execution = dry_run.get("execution") if isinstance(dry_run.get("execution"), Mapping) else {}; dry = dry_run.get("dry_run") if isinstance(dry_run.get("dry_run"), Mapping) else {}; human = readiness.get("human_attestation") if isinstance(readiness.get("human_attestation"), Mapping) else {}
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "job_id": job_id, "input_sha256": hashes, "observed_job": {"status": _text(observed_job.get("status"), "observed_job.status"), "next_process": _text(observed_job.get("next_process"), "observed_job.next_process")}, "recovery": {"status": "prepared_not_executed", "attestation_present": human.get("present") is True, "normalization_allowed": readiness.get("normalization_allowed") is True}, "execution": {"attempted": execution.get("attempted") is True, "external_calls": _int(execution.get("external_calls") or 0, "execution.external_calls"), "database_rows_created": _int(dry.get("database_rows_created") or 0, "execution.database_rows_created"), "state_advance": False}, "license_gate": {"ready_for_attestation": source_review.get("ready_for_attestation") is True and license_review.get("ready_for_attestation") is True, "pending_or_unknown": _int(source_review.get("unknown_or_pending") or 0, "license.pending_or_unknown"), "conflicts": _int(source_review.get("conflicts") or 0, "license.conflicts"), "source_review_sha256": _sha(source_review.get("source_review_sha256"), "source_review_sha256"), "legal_conclusion": compatibility.get("legal_conclusion") is True}, "learning": {"learning_demonstrated": False, "policy_status": str(policy.get("status") or "unavailable")}, "control": dict(_CONTROL), "next_action": "confirm_extraction_with_human_actor" if human.get("present") is not True else "review_license_compatibility_before_normalize"}
    validate_research_job_operations_context(result); return result


def validate_research_job_operations_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("research_job_operations_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "job_id", "input_sha256", "observed_job", "recovery", "execution", "license_gate", "learning", "control", "next_action"}
    if set(payload) != expected: raise ValueError("research_job_operations_fields_invalid")
    _text(payload["generated_at"], "generated_at"); _int(payload["job_id"], "job_id"); _sha(payload["input_sha256"], "input_sha256")
    observed = _map(payload["observed_job"], "observed_job")
    if set(observed) != {"status", "next_process"}: raise ValueError("research_job_operations_observed_job_invalid")
    _text(observed["status"], "observed_job.status"); _text(observed["next_process"], "observed_job.next_process")
    recovery = _map(payload["recovery"], "recovery")
    if set(recovery) != {"status", "attestation_present", "normalization_allowed"} or recovery["status"] != "prepared_not_executed" or recovery["attestation_present"] is not False or recovery["normalization_allowed"] is not False: raise ValueError("research_job_operations_recovery_invalid")
    execution = _map(payload["execution"], "execution")
    if set(execution) != {"attempted", "external_calls", "database_rows_created", "state_advance"} or execution["attempted"] is not False or execution["state_advance"] is not False: raise ValueError("research_job_operations_execution_invalid")
    _int(execution["external_calls"], "execution.external_calls"); _int(execution["database_rows_created"], "execution.database_rows_created")
    gate = _map(payload["license_gate"], "license_gate")
    if set(gate) != {"ready_for_attestation", "pending_or_unknown", "conflicts", "source_review_sha256", "legal_conclusion"} or gate["ready_for_attestation"] is not False or gate["legal_conclusion"] is not False: raise ValueError("research_job_operations_license_invalid")
    _int(gate["pending_or_unknown"], "license.pending_or_unknown"); _int(gate["conflicts"], "license.conflicts"); _sha(gate["source_review_sha256"], "source_review_sha256")
    learning = _map(payload["learning"], "learning")
    if set(learning) != {"learning_demonstrated", "policy_status"} or learning["learning_demonstrated"] is not False: raise ValueError("research_job_operations_learning_invalid")
    _text(learning["policy_status"], "learning.policy_status")
    if payload["control"] != _CONTROL: raise ValueError("research_job_operations_control_invalid")
    _text(payload["next_action"], "next_action"); return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_research_job_operations_context", "validate_research_job_operations_context"]
