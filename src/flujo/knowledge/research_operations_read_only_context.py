"""Bounded Research operations context: observation is not execution or learning."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import count_map as _count_map, nonnegative_int as _int, required_mapping as _mapping, required_text as _text


SCHEMA = "mak-research-operations-context-v1"
ALGORITHM_VERSION = "research-operations-read-only-context-1"
_CONTROL = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False, "external_calls": False}
_BOUNDARY = {"job_state_is_not_execution": True, "recovery_is_not_execution": True, "execution_is_not_learning": True, "candidate_reports_are_not_knowledge": True, "provider_calls_not_allowed": True, "semantic_claim": False, "learning_demonstrated": False}


def _learning_snapshot(learning: Mapping[str, Any]) -> dict[str, Any]:
    policy = learning.get("policy") if isinstance(learning.get("policy"), Mapping) else {}
    evaluation = policy.get("evaluation") if isinstance(policy.get("evaluation"), Mapping) else {}
    return {"available": learning.get("available") is True, "policy_status": str(policy.get("status") or "unavailable"), "eligible_examples": _int(policy.get("eligible_examples") or 0, "learning.eligible_examples"), "evaluation_present": bool(evaluation), "holdout_accuracy": evaluation.get("holdout_accuracy"), "holdout_baseline": evaluation.get("holdout_baseline")}


def build_research_operations_read_only_context(catalog: Mapping[str, Any], jobs: Mapping[str, Any], legacy_reports: Mapping[str, Any], rescue: Mapping[str, Any], learning: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    catalog = _mapping(catalog, "catalog"); jobs = _mapping(jobs, "jobs"); legacy_reports = _mapping(legacy_reports, "legacy_reports"); rescue = _mapping(rescue, "rescue"); learning = _mapping(learning, "learning")
    job_items = jobs.get("jobs") if isinstance(jobs.get("jobs"), list) else []
    job_items = [item for item in job_items if isinstance(item, Mapping)]
    status_counts = Counter(str(item.get("status") or "unknown") for item in job_items)
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "catalog": {"available": catalog.get("available") is True, "schema": str(catalog.get("schema") or "unknown"), "adapter_count": len(catalog.get("adapters", [])) if isinstance(catalog.get("adapters"), list) else 0, "job_count": _int(catalog.get("jobs") or 0, "catalog.jobs")}, "job_state_observed": {"available": jobs.get("available") is True, "count": len(job_items), "status_counts": dict(status_counts), "items": [{"id": _int(item.get("id"), "job.id"), "status": _text(item.get("status"), "job.status"), "next_process": _text(item.get("next_process"), "job.next_process"), "steps": _int(item.get("steps") or 0, "job.steps"), "done_steps": _int(item.get("done_steps") or 0, "job.done_steps")} for item in job_items]}, "recovery": {"verified": False, "observed_receipts": 0, "reason": "job_listing_has_no_recovery_receipt"}, "real_execution": {"verified": False, "observed_runs": 0, "reason": "job_status_and_done_steps_are_not_execution_receipts"}, "candidate_outputs": {"legacy_reports": {"available": legacy_reports.get("status") != "unavailable", "status": str(legacy_reports.get("status") or "unavailable"), "total": _int(legacy_reports.get("total") or 0, "legacy_reports.total"), "returned": _int(legacy_reports.get("returned") or 0, "legacy_reports.returned"), "sampled": legacy_reports.get("sampled") is True, "counts": _count_map(legacy_reports.get("counts", {}), "legacy_reports.counts"), "promotion": str(legacy_reports.get("promotion") or "none")}, "rescue": {"available": rescue.get("status") != "unavailable", "status": str(rescue.get("status") or "unavailable"), "counts": _count_map(rescue.get("counts", {}), "rescue.counts"), "promotion": str(rescue.get("promotion") or "none")}}, "learning": _learning_snapshot(learning), "boundary": dict(_BOUNDARY), "control": dict(_CONTROL), "next_action": "review_one_observed_job_then_require_an_execution_receipt_before_claiming_learning"}
    validate_research_operations_read_only_context(result); return result


def validate_research_operations_read_only_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("research_operations_context_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "catalog", "job_state_observed", "recovery", "real_execution", "candidate_outputs", "learning", "boundary", "control", "next_action"}
    if set(payload) != expected: raise ValueError("research_operations_context_fields_invalid")
    _text(payload["generated_at"], "generated_at")
    catalog = _mapping(payload["catalog"], "catalog")
    if set(catalog) != {"available", "schema", "adapter_count", "job_count"} or not isinstance(catalog["available"], bool): raise ValueError("research_operations_catalog_invalid")
    _text(catalog["schema"], "catalog.schema"); _int(catalog["adapter_count"], "catalog.adapter_count"); _int(catalog["job_count"], "catalog.job_count")
    observed = _mapping(payload["job_state_observed"], "job_state_observed")
    if set(observed) != {"available", "count", "status_counts", "items"} or not isinstance(observed["available"], bool): raise ValueError("research_operations_jobs_invalid")
    _int(observed["count"], "jobs.count"); _count_map(observed["status_counts"], "jobs.status_counts")
    if not isinstance(observed["items"], list) or len(observed["items"]) != observed["count"]: raise ValueError("research_operations_job_items_invalid")
    for item in observed["items"]:
        item = _mapping(item, "job")
        if set(item) != {"id", "status", "next_process", "steps", "done_steps"}: raise ValueError("research_operations_job_shape_invalid")
        _int(item["id"], "job.id"); _text(item["status"], "job.status"); _text(item["next_process"], "job.next_process"); _int(item["steps"], "job.steps"); _int(item["done_steps"], "job.done_steps")
    for field in ("recovery", "real_execution"):
        section = _mapping(payload[field], field); counter = "observed_receipts" if field == "recovery" else "observed_runs"
        if set(section) != {"verified", counter, "reason"} or section["verified"] is not False: raise ValueError(f"research_operations_{field}_invalid")
        _int(section[counter], f"{field}.count"); _text(section["reason"], f"{field}.reason")
    outputs = _mapping(payload["candidate_outputs"], "candidate_outputs")
    if set(outputs) != {"legacy_reports", "rescue"}: raise ValueError("research_operations_outputs_invalid")
    legacy = _mapping(outputs["legacy_reports"], "legacy_reports")
    if set(legacy) != {"available", "status", "total", "returned", "sampled", "counts", "promotion"} or legacy["status"] not in {"candidate_only", "unavailable"} or legacy["promotion"] != "none": raise ValueError("research_operations_legacy_invalid")
    if not isinstance(legacy["available"], bool): raise ValueError("research_operations_legacy_available_invalid")
    _int(legacy["total"], "legacy_reports.total"); _int(legacy["returned"], "legacy_reports.returned"); _count_map(legacy["counts"], "legacy_reports.counts")
    if not isinstance(legacy["sampled"], bool): raise ValueError("research_operations_legacy_sampled_invalid")
    rescue = _mapping(outputs["rescue"], "rescue")
    if set(rescue) != {"available", "status", "counts", "promotion"} or rescue["status"] not in {"candidate_only", "unavailable"} or rescue["promotion"] != "none": raise ValueError("research_operations_rescue_invalid")
    if not isinstance(rescue["available"], bool): raise ValueError("research_operations_rescue_available_invalid")
    _count_map(rescue["counts"], "rescue.counts")
    learning = _mapping(payload["learning"], "learning")
    if set(learning) != {"available", "policy_status", "eligible_examples", "evaluation_present", "holdout_accuracy", "holdout_baseline"} or not isinstance(learning["available"], bool) or not isinstance(learning["evaluation_present"], bool): raise ValueError("research_operations_learning_invalid")
    _text(learning["policy_status"], "learning.policy_status"); _int(learning["eligible_examples"], "learning.eligible_examples")
    for field in ("holdout_accuracy", "holdout_baseline"):
        if learning[field] is not None and (not isinstance(learning[field], (int, float)) or isinstance(learning[field], bool) or not 0 <= learning[field] <= 1): raise ValueError(f"learning.{field}_invalid")
    if payload["boundary"] != _BOUNDARY or payload["control"] != _CONTROL: raise ValueError("research_operations_boundary_or_control_invalid")
    _text(payload["next_action"], "next_action"); return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_research_operations_read_only_context", "validate_research_operations_read_only_context"]
