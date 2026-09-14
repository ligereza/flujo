"""Read-only context for Cultura sources and its Research support lane."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from ._contract_helpers import nonnegative_int as _count, required_mapping as _mapping, required_text as _text, without_ok as _without_ok

SCHEMA = "mak-cultura-research-read-only-context-v1"
ALGORITHM_VERSION = "cultura-research-read-only-context-1"
_CONTROL = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False, "network": False}


def build_cultura_research_read_only_context(sources: Mapping[str, Any], capabilities: Mapping[str, Any], opportunity_gate: Mapping[str, Any], research_catalog: Mapping[str, Any], research_jobs: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    sources = _without_ok(_mapping(sources, "sources")); capabilities = _without_ok(_mapping(capabilities, "capabilities")); opportunity_gate = _without_ok(_mapping(opportunity_gate, "opportunity_gate")); research_catalog = _without_ok(_mapping(research_catalog, "research_catalog")); research_jobs = _without_ok(_mapping(research_jobs, "research_jobs"))
    policy = _mapping(capabilities.get("policy"), "capabilities.policy"); provider_policy = _mapping(opportunity_gate.get("provider_policy"), "opportunity_gate.provider_policy"); jobs = research_jobs.get("jobs")
    if not isinstance(jobs, list): raise ValueError("research_jobs_list_invalid")
    statuses = Counter(job.get("status", "unknown") for job in jobs if isinstance(job, Mapping))
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "cultura": {"sources_schema": _text(sources.get("schema"), "sources.schema"), "root_count": len(sources.get("roots", [])) if isinstance(sources.get("roots"), list) else -1, "entry_count": len(sources.get("entries", [])) if isinstance(sources.get("entries"), list) else -1, "truncated": sources.get("truncated") is True, "capabilities_schema": _text(capabilities.get("schema"), "capabilities.schema"), "offline": {key: policy.get(key) is True for key in ("offline_first", "live_scrape_requires_explicit_gate", "proposal_is_draft_until_review", "secrets_in_payload")}, "output_format_count": len(capabilities.get("output_formats", [])) if isinstance(capabilities.get("output_formats"), list) else -1, "opportunity_gate_schema": _text(opportunity_gate.get("schema"), "opportunity_gate.schema"), "opportunity_mode": _text(opportunity_gate.get("mode"), "opportunity_gate.mode"), "required_field_count": len(opportunity_gate.get("required_fields", [])) if isinstance(opportunity_gate.get("required_fields"), list) else -1, "provider_policy": {key: _text(provider_policy.get(key), f"provider_policy.{key}") for key in ("scrape", "proposal", "network", "ledger_mutation")}}, "research": {"catalog_schema": str(research_catalog.get("schema") or "unknown"), "jobs_schema": str(research_jobs.get("schema") or "unknown"), "adapter_count": len(research_catalog.get("adapters", [])) if isinstance(research_catalog.get("adapters"), list) else -1, "catalog_job_count": research_catalog.get("jobs") if isinstance(research_catalog.get("jobs"), int) and research_catalog.get("jobs") >= 0 else -1, "observed_job_count": len(jobs), "job_status_counts": dict(sorted(statuses.items()))}, "boundary": {"cultura_is_offline_first": policy.get("offline_first") is True, "live_scrape_requires_explicit_gate": policy.get("live_scrape_requires_explicit_gate") is True, "proposal_is_draft_until_review": policy.get("proposal_is_draft_until_review") is True, "research_supports_not_claim": True, "job_state_is_not_learning": True, "semantic_claim": False}, "control": dict(_CONTROL), "next_action": "human_review_cultura_source_and_research_job_before_any_explicit_scrape_or_proposal_gate"}
    validate_cultura_research_read_only_context(result); return result


def validate_cultura_research_read_only_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("cultura_research_context_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "cultura", "research", "boundary", "control", "next_action"}
    if set(payload) != expected: raise ValueError("cultura_research_context_fields_invalid")
    _text(payload["generated_at"], "generated_at")
    cultura = payload["cultura"]; cultura_fields = {"sources_schema", "root_count", "entry_count", "truncated", "capabilities_schema", "offline", "output_format_count", "opportunity_gate_schema", "opportunity_mode", "required_field_count", "provider_policy"}
    if set(cultura) != cultura_fields: raise ValueError("cultura_research_context_cultura_fields_invalid")
    for field in ("sources_schema", "capabilities_schema", "opportunity_gate_schema", "opportunity_mode"): _text(cultura[field], f"cultura.{field}")
    for field in ("root_count", "entry_count", "output_format_count", "required_field_count"): _count(cultura[field], f"cultura.{field}")
    if not isinstance(cultura["truncated"], bool) or cultura["offline"] != {"offline_first": True, "live_scrape_requires_explicit_gate": True, "proposal_is_draft_until_review": True, "secrets_in_payload": False}: raise ValueError("cultura_research_context_cultura_policy_invalid")
    if cultura["provider_policy"] != {"scrape": "optional_and_explicit", "proposal": "draft_until_human_review", "network": "not_called", "ledger_mutation": "not_called"}: raise ValueError("cultura_research_context_provider_policy_invalid")
    research = payload["research"]; research_fields = {"catalog_schema", "jobs_schema", "adapter_count", "catalog_job_count", "observed_job_count", "job_status_counts"}
    if set(research) != research_fields: raise ValueError("cultura_research_context_research_fields_invalid")
    for field in ("catalog_schema", "jobs_schema"): _text(research[field], f"research.{field}")
    for field in ("adapter_count", "catalog_job_count", "observed_job_count"): _count(research[field], f"research.{field}")
    if not isinstance(research["job_status_counts"], Mapping) or any(not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0 for key, value in research["job_status_counts"].items()): raise ValueError("cultura_research_context_job_status_counts_invalid")
    if payload["boundary"] != {"cultura_is_offline_first": True, "live_scrape_requires_explicit_gate": True, "proposal_is_draft_until_review": True, "research_supports_not_claim": True, "job_state_is_not_learning": True, "semantic_claim": False}: raise ValueError("cultura_research_context_boundary_invalid")
    if payload["control"] != _CONTROL: raise ValueError("cultura_research_context_control_invalid")
    _text(payload["next_action"], "next_action"); return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_cultura_research_read_only_context", "validate_cultura_research_read_only_context"]
