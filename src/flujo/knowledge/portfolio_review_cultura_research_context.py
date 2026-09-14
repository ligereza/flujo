"""Read-only bridge between Portfolio review and Cultura/Research context."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import hashlib, json, re

from ._contract_helpers import nonnegative_int as _int, required_bool as _bool, required_mapping as _map, required_text as _text

SCHEMA = "mak-portfolio-review-cultura-research-context-v1"
ALGORITHM_VERSION = "portfolio-review-cultura-research-context-1"
_CONTROL = {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False, "semantic_claim": False, "learning_demonstrated": False}
def _sha(value: Any, field: str) -> str:
    value = _text(value, field).lower()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value): raise ValueError(f"{field}_invalid")
    return value
def _context_hash(value: Mapping[str, Any]) -> str:
    safe = dict(value); safe.pop("generated_at", None)
    return "sha256:" + hashlib.sha256(json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def build_portfolio_review_cultura_research_context(item_id: str, portfolio: Mapping[str, Any], cultura: Mapping[str, Any], research: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    item_id = _text(item_id, "item_id")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,240}", item_id): raise ValueError("item_id_invalid")
    portfolio = _map(portfolio, "portfolio"); cultura = _map(cultura, "cultura"); research = _map(research, "research")
    psource = _map(portfolio.get("source"), "portfolio.source"); candidate = _map(portfolio.get("candidate"), "portfolio.candidate"); decisions = _map(portfolio.get("decisions"), "portfolio.decisions"); current = _map(decisions.get("current"), "portfolio.decisions.current")
    cscope = _map(cultura.get("cultura", {}), "cultura.cultura") if isinstance(cultura.get("cultura"), Mapping) else {}; offline = _map(cscope.get("offline", {}), "cultura.cultura.offline") if isinstance(cscope.get("offline"), Mapping) else {}
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "item_id": item_id, "portfolio": {"source_hash": _sha(psource.get("source_hash"), "portfolio.source_hash"), "candidate_present": candidate.get("present") is True, "decision_state": _text(current.get("selection"), "portfolio.decision_state"), "human_history_count": _int(decisions.get("history_count"), "portfolio.human_history_count")}, "cultura": {"context_schema": _text(cultura.get("schema"), "cultura.schema"), "source_hash": _context_hash(cultura), "scope": "offline_first" if offline.get("offline_first") is True else "policy_observed"}, "research": {"context_schema": _text(research.get("schema"), "research.schema"), "source_hash": _sha("sha256:" + str(research.get("input_sha256") or ""), "research.input_sha256"), "job_state_is_not_execution": True, "learning_demonstrated": False}, "origin_guard": {"status": "unbound", "join_basis": "explicit_item_id_only", "typed_relation_present": False, "selection_effect": "none"}, "control": dict(_CONTROL), "next_action": "human_review_origin_before_any_typed_relation_or_decision"}
    validate_portfolio_review_cultura_research_context(result); return result
def validate_portfolio_review_cultura_research_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("portfolio_review_cultura_research_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "item_id", "portfolio", "cultura", "research", "origin_guard", "control", "next_action"}
    if set(payload) != expected: raise ValueError("portfolio_review_cultura_research_fields_invalid")
    _text(payload["generated_at"], "generated_at"); _text(payload["item_id"], "item_id"); portfolio = _map(payload["portfolio"], "portfolio")
    if set(portfolio) != {"source_hash", "candidate_present", "decision_state", "human_history_count"}: raise ValueError("portfolio_review_cultura_research_portfolio_invalid")
    _sha(portfolio["source_hash"], "portfolio.source_hash"); _bool(portfolio["candidate_present"], "portfolio.candidate_present"); _text(portfolio["decision_state"], "portfolio.decision_state"); _int(portfolio["human_history_count"], "portfolio.human_history_count"); cultura = _map(payload["cultura"], "cultura")
    if set(cultura) != {"context_schema", "source_hash", "scope"}: raise ValueError("portfolio_review_cultura_research_cultura_invalid")
    _text(cultura["context_schema"], "cultura.context_schema"); _sha(cultura["source_hash"], "cultura.source_hash"); _text(cultura["scope"], "cultura.scope"); research = _map(payload["research"], "research")
    if set(research) != {"context_schema", "source_hash", "job_state_is_not_execution", "learning_demonstrated"} or research["job_state_is_not_execution"] is not True or research["learning_demonstrated"] is not False: raise ValueError("portfolio_review_cultura_research_research_invalid")
    _text(research["context_schema"], "research.context_schema"); _sha(research["source_hash"], "research.source_hash")
    if _map(payload["origin_guard"], "origin_guard") != {"status": "unbound", "join_basis": "explicit_item_id_only", "typed_relation_present": False, "selection_effect": "none"}: raise ValueError("portfolio_review_cultura_research_origin_invalid")
    if payload["control"] != _CONTROL: raise ValueError("portfolio_review_cultura_research_control_invalid")
    _text(payload["next_action"], "next_action"); return True
__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_portfolio_review_cultura_research_context", "validate_portfolio_review_cultura_research_context"]
