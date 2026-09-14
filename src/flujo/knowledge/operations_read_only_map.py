"""Validated, read-only index of MAK operational surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:
    from ._contract_helpers import nonnegative_int as _int, required_text as _text
except ImportError:  # pragma: no cover - compatibility with direct file loading
    from flujo.knowledge._contract_helpers import nonnegative_int as _int, required_text as _text


SCHEMA = "mak-operations-read-only-map-v1"
ALGORITHM_VERSION = "operations-read-only-map-1"
ENDPOINTS = ["/api/status", "/api/portfolio/review-operations-context?item_id=18114751558928682.mp4", "/api/portfolio/review-cultura-research-context?item_id=18114751558928682.mp4", "/api/portfolio/review-operations-context?item_id=18099845974735838.mp4", "/api/portfolio/review-cultura-research-context?item_id=18099845974735838.mp4", "/api/rd/summary", "/api/rd/read-only-context", "/api/rd/topics", "/api/rd/crosswalk", "/api/rd/cultura-relations", "/api/cultura/sources", "/api/cultura/capabilities", "/api/cultura/opportunity-gate", "/api/cultura/research-read-only-context", "/api/research/catalog", "/api/research/jobs", "/api/research/operations-context?job_id=3", "/api/research/operations-read-only-context", "/api/project/learning-read-only-context", "/api/portfolio/operation-receipt", "/api/portfolio/work-packet", "/api/portfolio/archive-view", "/api/portfolio/vizz-measurement-status", "/api/portfolio/vizz-read-only-context"]
_MUTATING_TOKENS = ("/commit", "/resume", "/sync", "/probe", "/render", "/execute", "/write")
_CONTROL = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False}
_CLAIMS = {"semantic_claim": False, "relation_inference": False, "learning_demonstrated": "unknown"}
_CONTEXT_CLAIMS = {"semantic_claim": False, "relation_inference": False, "learning_demonstrated": False}


def _snapshot(snapshots: Mapping[str, Any], endpoint: str) -> Mapping[str, Any]:
    item = snapshots.get(endpoint)
    if not isinstance(item, Mapping): raise ValueError(f"operations_map_snapshot_missing_{endpoint}")
    return item


def _payload(item: Mapping[str, Any]) -> Mapping[str, Any]:
    value = item.get("payload")
    return value if isinstance(value, Mapping) else {}


def _count(value: Any, field: str) -> int:
    return _int(value, field) if value is not None else 0


def _assert_source_read_only(payload: Mapping[str, Any]) -> None:
    """Reject an unsafe child payload before projecting a closed map entry."""
    if "read_only" in payload and payload["read_only"] is not True: raise ValueError("operations_map_source_read_only_invalid")
    for key in ("database_write", "decision_write", "state_advance", "publication", "execution", "external_calls", "normalize_execution", "measurement_execution"):
        for container in (payload.get("control"), payload.get("controls")):
            if isinstance(container, Mapping) and key in container and container[key] is not False: raise ValueError("operations_map_source_control_invalid")
    for container in (payload.get("control"), payload.get("controls")):
        if isinstance(container, Mapping) and container.get("promotion") not in (None, "none"): raise ValueError("operations_map_source_control_invalid")
    for key in ("semantic_claim", "relation_inference", "learning_demonstrated"):
        if payload.get(key) is True: raise ValueError("operations_map_source_claim_invalid")
        for container in (payload.get("boundary"), payload.get("control")):
            if isinstance(container, Mapping) and container.get(key) is True: raise ValueError("operations_map_source_claim_invalid")


def _source_claims(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Project an explicit child learning boundary; never infer one."""
    for container in (payload.get("boundary"), payload.get("control")):
        if isinstance(container, Mapping) and container.get("learning_demonstrated") is False: return _CONTEXT_CLAIMS
    return _CLAIMS


def _entry(domain: str, endpoint: str, surface_kind: str, snapshot: Mapping[str, Any], *, observed_status: str, counts: Mapping[str, int], source_hash_or_ref: str, next_action: str, source_schema: str | None = None, claims: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = _payload(snapshot)
    if snapshot.get("http_status") == 200: _assert_source_read_only(payload)
    if snapshot.get("http_status") != 200:
        status_code = snapshot.get("http_status")
        observed_status = f"unavailable_http_{status_code if isinstance(status_code, int) else 'unknown'}"; counts = {}; source_hash_or_ref = "not_available"
    return {"domain": domain, "endpoint": endpoint, "source_schema": source_schema or str(payload.get("schema") or "unknown"), "surface_kind": surface_kind, "observed_status": observed_status, "counts": dict(counts), "source_hash_or_ref": source_hash_or_ref, "next_action": next_action, "controls": dict(_CONTROL), "claims": dict(claims or _source_claims(payload))}


def _build_entries(snapshots: Mapping[str, Any]) -> list[dict[str, Any]]:
    p = {endpoint: _payload(_snapshot(snapshots, endpoint)) for endpoint in ENDPOINTS}; s = {endpoint: _snapshot(snapshots, endpoint) for endpoint in ENDPOINTS}
    return [
        _entry("core", "/api/status", "evidence", s["/api/status"], observed_status="operational_status_observed", counts={}, source_hash_or_ref="mak-system-status-v1", next_action="treat_ledger_attention_as_operational_review_not_semantic_knowledge", source_schema="mak-system-status-v1"),
        _entry("portfolio", "/api/portfolio/review-operations-context?item_id=18114751558928682.mp4", "evidence", s["/api/portfolio/review-operations-context?item_id=18114751558928682.mp4"], observed_status="bounded_item_review", counts={"history": _count((p["/api/portfolio/review-operations-context?item_id=18114751558928682.mp4"].get("decisions") or {}).get("history_count"), "portfolio.review.history"), "candidate": int(bool((p["/api/portfolio/review-operations-context?item_id=18114751558928682.mp4"].get("candidate") or {}).get("present"))), "automation_ready": int(bool((p["/api/portfolio/review-operations-context?item_id=18114751558928682.mp4"].get("learning") or {}).get("automation_ready")))}, source_hash_or_ref="mak-portfolio-review-operations-context-v1", next_action="human_review_item_context_before_any_decision_or_publication", source_schema="mak-portfolio-review-operations-context-v1", claims=_CONTEXT_CLAIMS),
        _entry("portfolio", "/api/portfolio/review-cultura-research-context?item_id=18114751558928682.mp4", "evidence", s["/api/portfolio/review-cultura-research-context?item_id=18114751558928682.mp4"], observed_status="unbound_cross_area_context", counts={"typed_relation": int(bool((p["/api/portfolio/review-cultura-research-context?item_id=18114751558928682.mp4"].get("origin_guard") or {}).get("typed_relation_present"))), "candidate": int(bool((p["/api/portfolio/review-cultura-research-context?item_id=18114751558928682.mp4"].get("portfolio") or {}).get("candidate_present")))}, source_hash_or_ref="mak-portfolio-review-cultura-research-context-v1", next_action="require_explicit_origin_before_any_typed_cross_area_relation", source_schema="mak-portfolio-review-cultura-research-context-v1", claims=_CONTEXT_CLAIMS),
        _entry("portfolio", "/api/portfolio/review-operations-context?item_id=18099845974735838.mp4", "evidence", s["/api/portfolio/review-operations-context?item_id=18099845974735838.mp4"], observed_status="bounded_candidate_item_review", counts={"history": _count((p["/api/portfolio/review-operations-context?item_id=18099845974735838.mp4"].get("decisions") or {}).get("history_count"), "portfolio.candidate_review.history"), "candidate": int(bool((p["/api/portfolio/review-operations-context?item_id=18099845974735838.mp4"].get("candidate") or {}).get("present"))), "automation_ready": int(bool((p["/api/portfolio/review-operations-context?item_id=18099845974735838.mp4"].get("learning") or {}).get("automation_ready")))}, source_hash_or_ref="mak-portfolio-review-operations-context-v1", next_action="keep_candidate_separate_from_approval_and_publication", source_schema="mak-portfolio-review-operations-context-v1", claims=_CONTEXT_CLAIMS),
        _entry("portfolio", "/api/portfolio/review-cultura-research-context?item_id=18099845974735838.mp4", "evidence", s["/api/portfolio/review-cultura-research-context?item_id=18099845974735838.mp4"], observed_status="unbound_cross_area_candidate_context", counts={"typed_relation": int(bool((p["/api/portfolio/review-cultura-research-context?item_id=18099845974735838.mp4"].get("origin_guard") or {}).get("typed_relation_present"))), "candidate": int(bool((p["/api/portfolio/review-cultura-research-context?item_id=18099845974735838.mp4"].get("portfolio") or {}).get("candidate_present")))}, source_hash_or_ref="mak-portfolio-review-cultura-research-context-v1", next_action="require_explicit_origin_before_any_typed_candidate_relation", source_schema="mak-portfolio-review-cultura-research-context-v1", claims=_CONTEXT_CLAIMS),
        _entry("rd", "/api/rd/summary", "evidence", s["/api/rd/summary"], observed_status="projection_observed", counts={}, source_hash_or_ref="data/rd.db", next_action="review_rd_projection_before_any_crosswalk_decision"),
        _entry("rd", "/api/rd/read-only-context", "evidence", s["/api/rd/read-only-context"], observed_status="bounded_context", counts={"topics": _count((p["/api/rd/read-only-context"].get("topics") or {}).get("topic_count"), "rd.context.topics"), "crosswalk_entities": _count((p["/api/rd/read-only-context"].get("crosswalk") or {}).get("entity_count"), "rd.context.crosswalk_entities"), "relations": _count((p["/api/rd/read-only-context"].get("relations") or {}).get("relation_count"), "rd.context.relations")}, source_hash_or_ref="data/rd.db", next_action="human_review_rd_context_before_any_crosswalk_or_relation_decision"),
        _entry("rd", "/api/rd/topics", "evidence", s["/api/rd/topics"], observed_status="read_only", counts={"topics": len(p["/api/rd/topics"].get("topics", [])), "canonical_rows": _count((p["/api/rd/topics"].get("database") or {}).get("canonical_rows"), "rd.canonical_rows"), "runtime_rows": _count((p["/api/rd/topics"].get("database") or {}).get("runtime_rows"), "rd.runtime_rows")}, source_hash_or_ref="data/rd.db", next_action="choose_one_rd_topic_for_a_bounded_human_review"),
        _entry("rd", "/api/rd/crosswalk", "policy", s["/api/rd/crosswalk"], observed_status=str(p["/api/rd/crosswalk"].get("status") or "unknown"), counts={"entities": len(p["/api/rd/crosswalk"].get("entities", []))}, source_hash_or_ref="data/rd_fuentes/candidates/rd_portfolio_entity_crosswalk.json", next_action="keep_rd_crosswalk_in_review_only_until_explicit_provenance_is_reviewed"),
        _entry("rd", "/api/rd/cultura-relations", "evidence", s["/api/rd/cultura-relations"], observed_status=str(p["/api/rd/cultura-relations"].get("status") or "unknown"), counts={"producers": len(p["/api/rd/cultura-relations"].get("producers", [])), "venues": len(p["/api/rd/cultura-relations"].get("venues", [])), "relations": len(p["/api/rd/cultura-relations"].get("relations", []))}, source_hash_or_ref="mak-rd-cultura-relations-v1", next_action="keep_candidate_graph_unpromoted_until_explicit_venue_provenance"),
        _entry("cultura", "/api/cultura/sources", "catalog", s["/api/cultura/sources"], observed_status="catalogued", counts={"roots": len(p["/api/cultura/sources"].get("roots", [])), "entries": len(p["/api/cultura/sources"].get("entries", []))}, source_hash_or_ref="cultura/mak_research", next_action="select_a_declared_source_before_any_live_research_call"),
        _entry("cultura", "/api/cultura/capabilities", "policy", s["/api/cultura/capabilities"], observed_status="offline_first" if (p["/api/cultura/capabilities"].get("policy") or {}).get("offline_first") is True else "policy_observed", counts={"output_formats": len(p["/api/cultura/capabilities"].get("output_formats", []))}, source_hash_or_ref="mak-cultura-capabilities-v1", next_action="keep_live_scrape_explicit_and_proposals_in_draft"),
        _entry("cultura", "/api/cultura/opportunity-gate", "policy", s["/api/cultura/opportunity-gate"], observed_status=str(p["/api/cultura/opportunity-gate"].get("mode") or "unknown"), counts={"required_fields": len(p["/api/cultura/opportunity-gate"].get("required_fields", []))}, source_hash_or_ref="mak-cultura-opportunity-gate-v1", next_action="supply_declared_opportunity_fields_before_any_proposal_review"),
        _entry("cultura", "/api/cultura/research-read-only-context", "evidence", s["/api/cultura/research-read-only-context"], observed_status="bounded_context", counts={"sources": _count((p["/api/cultura/research-read-only-context"].get("cultura") or {}).get("entry_count"), "cultura.context.sources"), "adapters": _count((p["/api/cultura/research-read-only-context"].get("research") or {}).get("adapter_count"), "cultura.context.adapters"), "jobs": _count((p["/api/cultura/research-read-only-context"].get("research") or {}).get("observed_job_count"), "cultura.context.jobs")}, source_hash_or_ref="mak-cultura-research-read-only-context-v1", next_action="human_review_cultura_source_and_research_job_before_any_explicit_scrape_or_proposal_gate"),
        _entry("research", "/api/research/catalog", "catalog", s["/api/research/catalog"], observed_status="available_untyped" if "schema" not in p["/api/research/catalog"] else "available", counts={"adapters": len(p["/api/research/catalog"].get("adapters", [])), "jobs": _count(p["/api/research/catalog"].get("jobs"), "research.jobs")}, source_hash_or_ref="research/jardines_interpretativos", next_action="continue_from_a_specific_job_state_and_evidence_gate", source_schema=str(p["/api/research/catalog"].get("schema") or "unknown")),
        _entry("research", "/api/research/jobs", "evidence", s["/api/research/jobs"], observed_status="jobs_observed", counts={"jobs": len(p["/api/research/jobs"].get("jobs", [])), "interpreted": sum(job.get("status") == "interpreted" for job in p["/api/research/jobs"].get("jobs", []) if isinstance(job, Mapping)), "extracted": sum(job.get("status") == "extracted" for job in p["/api/research/jobs"].get("jobs", []) if isinstance(job, Mapping)), "planned": sum(job.get("status") == "planned" for job in p["/api/research/jobs"].get("jobs", []) if isinstance(job, Mapping))}, source_hash_or_ref="research/jobs", next_action="resume_only_after_human_confirmation_of_the_observed_job"),
        _entry("research", "/api/research/operations-context?job_id=3", "evidence", s["/api/research/operations-context?job_id=3"], observed_status="bounded_job_context", counts={"job_id": _count(p["/api/research/operations-context?job_id=3"].get("job_id"), "research.job_context.id"), "license_conflicts": _count((p["/api/research/operations-context?job_id=3"].get("license_gate") or {}).get("conflicts"), "research.job_context.license_conflicts"), "license_pending": _count((p["/api/research/operations-context?job_id=3"].get("license_gate") or {}).get("pending_or_unknown"), "research.job_context.license_pending")}, source_hash_or_ref="mak-research-operations-context-v1", next_action="require_human_attestation_and_license_scope_review_before_normalize", claims=_CONTEXT_CLAIMS),
        _entry("research", "/api/research/operations-read-only-context", "evidence", s["/api/research/operations-read-only-context"], observed_status="bounded_context", counts={"observed_jobs": _count((p["/api/research/operations-read-only-context"].get("job_state_observed") or {}).get("count"), "research.operations.jobs"), "recovery_verified": int(bool((p["/api/research/operations-read-only-context"].get("recovery") or {}).get("verified"))), "execution_verified": int(bool((p["/api/research/operations-read-only-context"].get("real_execution") or {}).get("verified")))}, source_hash_or_ref="mak-research-operations-context-v1", next_action="require_execution_receipt_before_claiming_learning", claims=_CONTEXT_CLAIMS),
        _entry("learning", "/api/project/learning-read-only-context", "evidence", s["/api/project/learning-read-only-context"], observed_status="candidate_policy", counts={"eligible_examples": _count((p["/api/project/learning-read-only-context"].get("policy") or {}).get("eligible_examples"), "learning.eligible_examples"), "train": _count((p["/api/project/learning-read-only-context"].get("policy") or {}).get("train_count"), "learning.train"), "holdout": _count((p["/api/project/learning-read-only-context"].get("policy") or {}).get("holdout_count"), "learning.holdout"), "projects_review_required": _count(((p["/api/project/learning-read-only-context"].get("ledger") or {}).get("projects") or {}).get("review_required"), "learning.projects_review_required")}, source_hash_or_ref="mak_knowledge.db", next_action="keep_candidate_policy_separate_from_verified_knowledge_and_require_human_review"),
        _entry("portfolio", "/api/portfolio/operation-receipt", "evidence", s["/api/portfolio/operation-receipt"], observed_status=str(p["/api/portfolio/operation-receipt"].get("status") or "unknown"), counts={"expanded": _count((p["/api/portfolio/operation-receipt"].get("operation") or {}).get("expanded_count"), "portfolio.receipt.expanded"), "rejected_attempts": len(p["/api/portfolio/operation-receipt"].get("rejected_attempts", []))}, source_hash_or_ref=str((p["/api/portfolio/operation-receipt"].get("source") or {}).get("ref") or "unknown"), next_action="keep_structural_receipt_separate_from_semantic_equivalence"),
        _entry("portfolio", "/api/portfolio/work-packet", "policy", s["/api/portfolio/work-packet"], observed_status="read_only" if (p["/api/portfolio/work-packet"].get("execution") or {}).get("execution_allowed") is False else "review", counts={"tasks": _count((p["/api/portfolio/work-packet"].get("execution") or {}).get("task_count"), "portfolio.work_packet.tasks"), "executed": _count((p["/api/portfolio/work-packet"].get("execution") or {}).get("executed_task_count"), "portfolio.work_packet.executed")}, source_hash_or_ref="mak-portfolio-work-packet-v1", next_action="human_review_one_portfolio_task_before_any_execution"),
        _entry("iskvw", "/api/portfolio/archive-view", "evidence", s["/api/portfolio/archive-view"], observed_status=str(p["/api/portfolio/archive-view"].get("status") or "unknown"), counts={"visible": _count((p["/api/portfolio/archive-view"].get("selection") or {}).get("selected_item_count"), "iskvw.visible"), "omitted": _count((p["/api/portfolio/archive-view"].get("reconciliation") or {}).get("omitted_piece_count"), "iskvw.omitted")}, source_hash_or_ref=str((p["/api/portfolio/archive-view"].get("source") or {}).get("input_hash") or "unknown"), next_action="keep_archive_draft_only_until_human_editorial_review"),
        _entry("vizz", "/api/portfolio/vizz-measurement-status", "policy", s["/api/portfolio/vizz-measurement-status"], observed_status=str(p["/api/portfolio/vizz-measurement-status"].get("status") or "unknown"), counts={"triangulation_attempted": int(bool((p["/api/portfolio/vizz-measurement-status"].get("measurement") or {}).get("triangulation_attempted"))), "depth_result_present": int(bool((p["/api/portfolio/vizz-measurement-status"].get("measurement") or {}).get("depth_result_present")))}, source_hash_or_ref=str((p["/api/portfolio/vizz-measurement-status"].get("provenance") or {}).get("ref") or "unknown"), next_action="keep_vizz_measurement_refused_until_independent_physical_calibration_evidence"),
        _entry("vizz", "/api/portfolio/vizz-read-only-context", "evidence", s["/api/portfolio/vizz-read-only-context"], observed_status="bounded_context", counts={"shared_keys": _count((p["/api/portfolio/vizz-read-only-context"].get("delta") or {}).get("shared_keys"), "vizz.context.shared_keys"), "residue_keys": _count((p["/api/portfolio/vizz-read-only-context"].get("delta") or {}).get("residue_keys"), "vizz.context.residue_keys")}, source_hash_or_ref="mak-vizz-portfolio-read-only-context-v1", next_action="provide_physical_calibration_evidence_before_metric_measurement"),
    ]


def build_operations_read_only_map(snapshots: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    if not isinstance(snapshots, Mapping):
        raise ValueError("operations_map_snapshots_invalid")
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "entries": _build_entries(snapshots), "boundary": {"get_whitelist_only": True, "status_is_not_semantic_knowledge": True, "catalogue_is_not_evidence_of_learning": True, "vizz_parent_lane": "portfolio_instrument", "semantic_claim": False}, "control": {**_CONTROL, "external_calls": False}, "next_action": "human_review_operations_map_then_choose_one_bounded_area_experiment"}
    validate_operations_read_only_map(result); return result


def validate_operations_read_only_map(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("operations_map_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "entries", "boundary", "control", "next_action"}
    if set(payload) != expected: raise ValueError("operations_map_fields_invalid")
    _text(payload["generated_at"], "generated_at")
    entries = payload["entries"]
    if not isinstance(entries, list) or [item.get("endpoint") for item in entries if isinstance(item, Mapping)] != ENDPOINTS: raise ValueError("operations_map_endpoint_order_invalid")
    fields = {"domain", "endpoint", "source_schema", "surface_kind", "observed_status", "counts", "source_hash_or_ref", "next_action", "controls", "claims"}
    for item in entries:
        if not isinstance(item, Mapping) or set(item) != fields: raise ValueError("operations_map_entry_shape_invalid")
        for field in ("domain", "endpoint", "source_schema", "surface_kind", "observed_status", "source_hash_or_ref", "next_action"): _text(item[field], f"entry.{field}")
        if any(token in item["endpoint"] for token in _MUTATING_TOKENS) or not item["endpoint"].startswith("/api/"): raise ValueError("operations_map_endpoint_not_read_only")
        if not isinstance(item["counts"], Mapping) or any(not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0 for key, value in item["counts"].items()): raise ValueError("operations_map_counts_invalid")
        if item["controls"] != _CONTROL or item["claims"] not in (_CLAIMS, _CONTEXT_CLAIMS): raise ValueError("operations_map_entry_control_invalid")
    if payload["boundary"] != {"get_whitelist_only": True, "status_is_not_semantic_knowledge": True, "catalogue_is_not_evidence_of_learning": True, "vizz_parent_lane": "portfolio_instrument", "semantic_claim": False}: raise ValueError("operations_map_boundary_invalid")
    if payload["control"] != {**_CONTROL, "external_calls": False}: raise ValueError("operations_map_control_invalid")
    _text(payload["next_action"], "next_action"); return True


__all__ = ["ALGORITHM_VERSION", "ENDPOINTS", "SCHEMA", "build_operations_read_only_map", "validate_operations_read_only_map"]
