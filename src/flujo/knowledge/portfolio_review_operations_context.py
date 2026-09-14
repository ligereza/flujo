"""Read-only review context for one Portafolio item."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import hashlib
import json
import re

from ._contract_helpers import nonnegative_int as _int, required_bool as _bool, required_mapping as _map, required_text as _text

SCHEMA = "mak-portfolio-review-operations-context-v1"
ALGORITHM_VERSION = "portfolio-review-operations-context-1"
_CONTROL = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "context_only", "promotion": "none", "publication": False, "external_calls": False}

def _digest(value: Any, field: str) -> str:
    value = _text(value, field)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value): raise ValueError(f"{field}_invalid")
    return value
def _item_hash(item: Mapping[str, Any]) -> str:
    safe = {key: item.get(key) for key in ("id", "publicacion_id", "publicacion_archivo", "medio_indice", "fecha", "tipo_contenido", "status", "selection", "classification")}
    return "sha256:" + hashlib.sha256(json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def build_portfolio_review_operations_context(item_id: str, inbox_item: Mapping[str, Any], audit: Mapping[str, Any], direction: Mapping[str, Any], decision_index: Mapping[str, Any], candidates: Mapping[str, Any], learning: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    item_id = _text(item_id, "item_id")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,240}", item_id): raise ValueError("item_id_invalid")
    inbox_item = _map(inbox_item, "inbox_item"); audit = _map(audit, "audit"); direction = _map(direction, "direction"); decision_index = _map(decision_index, "decision_index"); candidates = _map(candidates, "candidates"); learning = _map(learning, "learning")
    audit_item = _map(audit.get("item"), "audit.item"); current = _map(audit_item.get("current", {}), "audit.item.current"); frame = _map(direction.get("frame"), "direction.frame"); vision = _map(frame.get("vision"), "direction.vision"); order = _map(frame.get("order"), "direction.order"); culture = _map(frame.get("culture_computation"), "direction.culture_computation")
    draft = current.get("decision_draft") if isinstance(current.get("decision_draft"), Mapping) else {}; instrument = _map(frame.get("instrument", {}), "direction.instrument"); policy = learning.get("policy") if isinstance(learning.get("policy"), Mapping) else {}; candidate_items = candidates.get("items") if isinstance(candidates.get("items"), list) else []
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "item_id": item_id, "source": {"reference_class": "logical_local_reference", "asset_path_exposed": False, "source_schema": str(inbox_item.get("schema") or "faro-portfolio-inbox-v1"), "source_hash": _item_hash(inbox_item), "content_type": str(inbox_item.get("tipo_contenido") or "unknown"), "date": str(inbox_item.get("fecha") or "unknown")}, "vision_order_culture_computation": {"source_schema": _text(direction.get("schema"), "direction.schema"), "source_hash": _text(vision.get("source_hash"), "direction.vision.source_hash"), "states": {"vision": _text(vision.get("state"), "direction.vision.state"), "order": _text(order.get("state"), "direction.order.state"), "culture_computation": _text(culture.get("state"), "direction.culture_computation.state")}}, "candidate": {"present": bool(candidate_items), "status": "candidate_present" if candidate_items else "unbound", "public_promotion": candidates.get("public_promotion") is True}, "decisions": {"current": {"selection": str(current.get("selection") or inbox_item.get("selection") or "unknown"), "triage": str(((current.get("classification") or {}).get("triage") or "unknown") if isinstance(current.get("classification"), Mapping) else "unknown"), "draft_status": str(draft.get("status") or "none")}, "history_count": _int(audit_item.get("timeline_total") or 0, "decisions.history_count"), "actor": "human" if draft.get("owner") == "human" else "human_or_none", "index_counts": {key: _int(value, f"decisions.index_counts.{key}") for key, value in (decision_index.get("counts") or {}).items() if isinstance(key, str)}}, "execution": {"portfolio_task_executed": False, "render_preview_executed": False, "publication": False}, "learning": {"evaluation_available": learning.get("available") is True, "automation_ready": bool((_map(audit.get("ordering_model", {}), "audit.ordering_model")).get("automation_ready")), "learning_demonstrated": False, "policy_status": str(policy.get("status") or "unavailable")}, "control": dict(_CONTROL), "next_action": "human_review_item_context_before_any_decision_or_publication"}
    result["vizz"] = {"state": _text(instrument.get("state"), "direction.instrument.state"), "measurement_status": _text(instrument.get("measurement_status"), "direction.instrument.measurement_status"), "triangulation_attempted": instrument.get("triangulation_attempted") is True, "depth_result_present": instrument.get("depth_result_present") is True, "measurement_claim_allowed": instrument.get("measurement_claim_allowed") is True}
    validate_portfolio_review_operations_context(result); return result

def validate_portfolio_review_operations_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("portfolio_review_operations_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "item_id", "source", "vision_order_culture_computation", "vizz", "candidate", "decisions", "execution", "learning", "control", "next_action"}
    if set(payload) != expected: raise ValueError("portfolio_review_operations_fields_invalid")
    _text(payload["generated_at"], "generated_at"); item_id = _text(payload["item_id"], "item_id")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,240}", item_id): raise ValueError("item_id_invalid")
    source = _map(payload["source"], "source")
    if set(source) != {"reference_class", "asset_path_exposed", "source_schema", "source_hash", "content_type", "date"} or source["reference_class"] != "logical_local_reference" or source["asset_path_exposed"] is not False: raise ValueError("portfolio_review_operations_source_invalid")
    for field in ("reference_class", "source_schema", "source_hash", "content_type", "date"): _text(source[field], f"source.{field}")
    _digest(source["source_hash"], "source.source_hash")
    voc = _map(payload["vision_order_culture_computation"], "vision_order_culture_computation")
    if set(voc) != {"source_schema", "source_hash", "states"}: raise ValueError("portfolio_review_operations_direction_invalid")
    _text(voc["source_schema"], "direction.source_schema"); _digest(voc["source_hash"], "direction.source_hash"); states = _map(voc["states"], "direction.states")
    if set(states) != {"vision", "order", "culture_computation"}: raise ValueError("portfolio_review_operations_states_invalid")
    for field in states: _text(states[field], f"direction.states.{field}")
    vizz = _map(payload["vizz"], "vizz")
    if set(vizz) != {"state", "measurement_status", "triangulation_attempted", "depth_result_present", "measurement_claim_allowed"} or vizz["state"] != "vizz_measurement_refused" or vizz["triangulation_attempted"] is not False or vizz["depth_result_present"] is not False or vizz["measurement_claim_allowed"] is not False: raise ValueError("portfolio_review_operations_vizz_invalid")
    _text(vizz["state"], "vizz.state"); _text(vizz["measurement_status"], "vizz.measurement_status")
    candidate = _map(payload["candidate"], "candidate")
    if set(candidate) != {"present", "status", "public_promotion"} or candidate["status"] not in {"unbound", "candidate_present"} or candidate["status"] != ("candidate_present" if candidate["present"] else "unbound") or candidate["public_promotion"] is not False: raise ValueError("portfolio_review_operations_candidate_invalid")
    _bool(candidate["present"], "candidate.present"); decisions = _map(payload["decisions"], "decisions"); current = _map(decisions["current"], "decisions.current")
    if set(decisions) != {"current", "history_count", "actor", "index_counts"} or set(current) != {"selection", "triage", "draft_status"}: raise ValueError("portfolio_review_operations_decisions_invalid")
    for field in current: _text(current[field], f"decisions.current.{field}")
    _int(decisions["history_count"], "decisions.history_count"); _text(decisions["actor"], "decisions.actor"); _map(decisions["index_counts"], "decisions.index_counts")
    if _map(payload["execution"], "execution") != {"portfolio_task_executed": False, "render_preview_executed": False, "publication": False}: raise ValueError("portfolio_review_operations_execution_invalid")
    learning = _map(payload["learning"], "learning")
    if set(learning) != {"evaluation_available", "automation_ready", "learning_demonstrated", "policy_status"} or learning["automation_ready"] is not False or learning["learning_demonstrated"] is not False: raise ValueError("portfolio_review_operations_learning_invalid")
    _bool(learning["evaluation_available"], "learning.evaluation_available"); _text(learning["policy_status"], "learning.policy_status")
    if payload["control"] != _CONTROL: raise ValueError("portfolio_review_operations_control_invalid")
    _text(payload["next_action"], "next_action"); return True

__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_portfolio_review_operations_context", "validate_portfolio_review_operations_context"]
