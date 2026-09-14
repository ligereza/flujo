"""Bounded read-only context joining MAK's VIZZ-facing portfolio surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._contract_helpers import integer as _int, integer as _signed_int, required_mapping as _mapping, required_text as _text, without_ok as _without_ok

SCHEMA = "mak-vizz-portfolio-read-only-context-v1"
ALGORITHM_VERSION = "vizz-portfolio-read-only-context-1"
_CONTROL = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "measurement_execution": False, "metric_depth_authorized": False, "network": False, "execution": False}


def _optional_text(value: Any, field: str) -> str | None:
    if value is None: return None
    return _text(value, field)


def build_portfolio_vizz_read_only_context(measurement: Mapping[str, Any], lineage: Mapping[str, Any], delta: Mapping[str, Any], preview: Mapping[str, Any], *, generated_at: str = "not_attached") -> dict[str, Any]:
    measurement = _without_ok(_mapping(measurement, "measurement")); lineage = _without_ok(_mapping(lineage, "lineage")); delta = _without_ok(_mapping(delta, "delta")); preview = _without_ok(_mapping(preview, "preview"))
    md = _mapping(measurement.get("measurement"), "measurement.measurement"); lc = _mapping(lineage.get("current"), "lineage.current"); lr = _mapping(lineage.get("revision"), "lineage.revision"); dd = _mapping(delta.get("delta"), "delta.delta"); pt = _mapping(preview.get("task"), "preview.task"); ps = _mapping(preview.get("source"), "preview.source"); pp = _mapping(preview.get("provenance"), "preview.provenance")
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at"), "source": {"measurement_schema": _text(measurement.get("schema"), "measurement.schema"), "lineage_schema": _text(lineage.get("schema"), "lineage.schema"), "delta_schema": _text(delta.get("schema"), "delta.schema"), "preview_schema": _text(preview.get("schema"), "preview.schema")}, "measurement": {"status": _text(measurement.get("status"), "measurement.status"), "calibration_status": _text(md.get("calibration_status"), "measurement.calibration_status"), "triangulation_attempted": md.get("triangulation_attempted") is True, "depth_result_present": md.get("depth_result_present") is True, "claim_allowed": False}, "lineage": {"status": _text(lineage.get("status"), "lineage.status"), "current_status": _text(lc.get("status"), "lineage.current.status"), "revision_status": _text(lr.get("status"), "lineage.revision.status"), "current_state_replaced": (lineage.get("control") or {}).get("current_state_replaced") is True, "current_ref": _text(lc.get("ref"), "lineage.current.ref")}, "delta": {"status": _text(delta.get("status"), "delta.status"), "shared_keys": _int(dd.get("shared_keys"), "delta.shared_keys"), "residue_keys": _int(dd.get("residue_keys"), "delta.residue_keys"), "serialized_savings_bytes": _signed_int(dd.get("serialized_savings_bytes"), "delta.serialized_savings_bytes"), "learning_demonstrated": False}, "preview": {"task_id": _text(pt.get("id"), "preview.task.id"), "state": _text(pt.get("state"), "preview.task.state"), "human_gate": _text(pt.get("human_gate"), "preview.task.human_gate"), "project_id": _optional_text(ps.get("project_id"), "preview.source.project_id"), "relation_status": _text(ps.get("relation_status"), "preview.source.relation_status"), "preview_only": preview.get("preview_only") is True, "execution_allowed": pt.get("execution_allowed") is True, "task_execution": pp.get("task_execution") is True}, "boundary": {"measurement_refused": measurement.get("status") == "unknown_measurement_refused", "calibration_required": md.get("calibration_status") == "CALIBRATION_EVIDENCE_REQUIRED", "lineage_is_not_authorization": True, "delta_is_structural_only": delta.get("status") == "revision_only_delta", "preview_is_not_execution": preview.get("preview_only") is True and pt.get("execution_allowed") is False, "semantic_claim": False, "learning_demonstrated": False}, "control": dict(_CONTROL), "next_action": "provide_physical_calibration_evidence_before_metric_measurement"}
    validate_portfolio_vizz_read_only_context(result); return result


def validate_portfolio_vizz_read_only_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True: raise ValueError("vizz_context_header_invalid")
    if set(payload) != {"schema", "algorithm_version", "available", "read_only", "generated_at", "source", "measurement", "lineage", "delta", "preview", "boundary", "control", "next_action"}: raise ValueError("vizz_context_fields_invalid")
    _text(payload["generated_at"], "generated_at"); source = payload["source"]
    if set(source) != {"measurement_schema", "lineage_schema", "delta_schema", "preview_schema"}: raise ValueError("vizz_context_source_invalid")
    for field in source: _text(source[field], f"source.{field}")
    m = payload["measurement"]
    if set(m) != {"status", "calibration_status", "triangulation_attempted", "depth_result_present", "claim_allowed"} or m["status"] != "unknown_measurement_refused" or m["calibration_status"] != "CALIBRATION_EVIDENCE_REQUIRED" or m["triangulation_attempted"] is not False or m["depth_result_present"] is not False or m["claim_allowed"] is not False: raise ValueError("vizz_context_measurement_invalid")
    l = payload["lineage"]
    if set(l) != {"status", "current_status", "revision_status", "current_state_replaced", "current_ref"} or l["status"] != "revision_context_only" or l["current_status"] != "unknown_measurement_refused" or l["revision_status"] != "revision_accepted" or l["current_state_replaced"] is not False: raise ValueError("vizz_context_lineage_invalid")
    d = payload["delta"]
    if set(d) != {"status", "shared_keys", "residue_keys", "serialized_savings_bytes", "learning_demonstrated"} or d["status"] != "revision_only_delta" or d["learning_demonstrated"] is not False: raise ValueError("vizz_context_delta_invalid")
    _int(d["shared_keys"], "delta.shared_keys"); _int(d["residue_keys"], "delta.residue_keys"); _signed_int(d["serialized_savings_bytes"], "delta.serialized_savings_bytes")
    p = payload["preview"]
    if set(p) != {"task_id", "state", "human_gate", "project_id", "relation_status", "preview_only", "execution_allowed", "task_execution"} or p["task_id"] != "vizz_calibration" or p["state"] != "vizz_measurement_refused" or p["human_gate"] != "physical_calibration_evidence" or p["preview_only"] is not True or p["execution_allowed"] is not False or p["task_execution"] is not False: raise ValueError("vizz_context_preview_invalid")
    if p["project_id"] is not None: _text(p["project_id"], "preview.project_id")
    if payload["boundary"] != {"measurement_refused": True, "calibration_required": True, "lineage_is_not_authorization": True, "delta_is_structural_only": True, "preview_is_not_execution": True, "semantic_claim": False, "learning_demonstrated": False}: raise ValueError("vizz_context_boundary_invalid")
    if payload["control"] != _CONTROL: raise ValueError("vizz_context_control_invalid")
    _text(payload["next_action"], "next_action"); return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_portfolio_vizz_read_only_context", "validate_portfolio_vizz_read_only_context"]
