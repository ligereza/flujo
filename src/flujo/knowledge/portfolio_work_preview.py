"""Read-only preview of one portfolio work item."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .portfolio_work_packet import (
    SCHEMA as PACKET_SCHEMA,
    build_portfolio_work_packet,
    validate_portfolio_work_packet,
)
from ._contract_helpers import required_text as _text


SCHEMA = "mak-portfolio-work-preview-v1"
ALGORITHM_VERSION = "portfolio-work-preview-1"
TASK_IDS = ["archive_orientation", "structural_order", "practice_relation", "vizz_calibration"]


def build_portfolio_work_preview(
    work_packet: Mapping[str, Any],
    task_id: str,
) -> dict[str, Any]:
    """Select one task for display only; never claim execution or approval."""
    validate_portfolio_work_packet(work_packet)
    normalized_id = _text(task_id, "task_id")
    task = next((item for item in work_packet["tasks"] if item["id"] == normalized_id), None)
    if task is None:
        raise ValueError("portfolio_work_task_not_found")
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "preview_only": True,
        "source": {
            "schema": PACKET_SCHEMA,
            "task_id": normalized_id,
            "task_count": work_packet["execution"]["task_count"],
            "project_id": work_packet["source"]["project_id"],
            "relation_status": work_packet["source"]["relation_status"],
        },
        "task": dict(task),
        "next_action": "human_review_selected_work_preview_before_execution",
        "control": {
            "database_write": False,
            "decision_write": False,
            "state_advance": False,
            "selection_effect": "context_only",
            "promotion": "none",
            "publication": False,
            "normalize_execution": False,
            "measurement_execution": False,
        },
        "provenance": {
            "packet_schema": PACKET_SCHEMA,
            "project_id": work_packet["source"]["project_id"],
            "relation_status": work_packet["source"]["relation_status"],
            "typed_relation_present": False,
            "deterministic": True,
            "task_execution": False,
            "semantic_claim": False,
            "learning_demonstrated": False,
            "decisions_require_external_human_actor": True,
        },
    }
    validate_portfolio_work_preview(result)
    return result


def validate_portfolio_work_preview(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise ValueError("portfolio_work_preview_schema_invalid")
    if payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True or payload.get("preview_only") is not True:
        raise ValueError("portfolio_work_preview_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "preview_only", "source", "task", "next_action", "control", "provenance"}
    if set(payload) != expected:
        raise ValueError("portfolio_work_preview_fields_invalid")
    source = payload["source"]
    if set(source) != {"schema", "task_id", "task_count", "project_id", "relation_status"} or source["schema"] != PACKET_SCHEMA or source["task_id"] not in TASK_IDS or source["task_count"] != 4:
        raise ValueError("portfolio_work_preview_source_invalid")
    if source["project_id"] is not None and (not isinstance(source["project_id"], str) or not source["project_id"].strip()):
        raise ValueError("portfolio_work_preview_project_id_invalid")
    if source["relation_status"] not in {"unbound", "needs_evidence"}:
        raise ValueError("portfolio_work_preview_relation_status_invalid")
    task = payload["task"]
    task_fields = {"id", "area", "layer", "state", "evidence", "action", "human_gate", "execution_allowed"}
    if not isinstance(task, Mapping) or set(task) != task_fields or task["id"] != source["task_id"]:
        raise ValueError("portfolio_work_preview_task_invalid")
    for field in ("id", "area", "layer", "state", "evidence", "action", "human_gate"):
        _text(task[field], f"task.{field}")
    if task["execution_allowed"] is not False:
        raise ValueError("portfolio_work_preview_execution_invalid")
    _text(payload["next_action"], "next_action")
    if payload["control"] != {
        "database_write": False,
        "decision_write": False,
        "state_advance": False,
        "selection_effect": "context_only",
        "promotion": "none",
        "publication": False,
        "normalize_execution": False,
        "measurement_execution": False,
    }:
        raise ValueError("portfolio_work_preview_control_invalid")
    if payload["provenance"] != {
        "packet_schema": PACKET_SCHEMA,
        "project_id": source["project_id"],
        "relation_status": source["relation_status"],
        "typed_relation_present": False,
        "deterministic": True,
        "task_execution": False,
        "semantic_claim": False,
        "learning_demonstrated": False,
        "decisions_require_external_human_actor": True,
    }:
        raise ValueError("portfolio_work_preview_provenance_invalid")
    return True


__all__ = [
    "ALGORITHM_VERSION",
    "SCHEMA",
    "TASK_IDS",
    "build_portfolio_work_preview",
    "validate_portfolio_work_preview",
]
