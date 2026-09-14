"""Turn the portfolio direction frame into an actionable read-only packet."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .portfolio_direction_context import (
    SCHEMA as DIRECTION_SCHEMA,
    validate_portfolio_direction_context,
)
from ._contract_helpers import required_text as _text


SCHEMA = "mak-portfolio-work-packet-v1"
ALGORITHM_VERSION = "portfolio-work-packet-1"


def build_portfolio_work_packet(
    direction_context: Mapping[str, Any],
    project_id: str | None = None,
) -> dict[str, Any]:
    """Create work items from an already validated direction context."""
    validate_portfolio_direction_context(direction_context)
    frame = direction_context["frame"]
    tasks = [
        {
            "id": "archive_orientation",
            "area": "mak-hub/portfolio",
            "layer": "vision",
            "state": frame["vision"]["state"],
            "evidence": "mak-archive-portfolio-view-v1",
            "action": frame["vision"]["next_action"],
            "human_gate": "interpretation_and_editorial_context",
            "execution_allowed": False,
        },
        {
            "id": "structural_order",
            "area": "flujo/knowledge",
            "layer": "order",
            "state": frame["order"]["state"],
            "evidence": "mak-operation-receipt-v1 + mak-structural-delta-status-v1",
            "action": frame["order"]["next_action"],
            "human_gate": "semantic_reuse_or_equivalence",
            "execution_allowed": False,
        },
        {
            "id": "practice_relation",
            "area": "mak-hub/portfolio",
            "layer": "culture_computation",
            "state": frame["culture_computation"]["project_relation_status"],
            "evidence": "mak-portfolio-review-context-v1",
            "action": frame["culture_computation"]["next_action"],
            "human_gate": "typed_relation_and_attribution",
            "execution_allowed": False,
        },
        {
            "id": "vizz_calibration",
            "area": "vizz/measurement",
            "layer": "instrument",
            "state": frame["instrument"]["state"],
            "evidence": "mak-vizz-measurement-status-v1 + mak-vizz-lineage-status-v1",
            "action": frame["instrument"]["next_action"],
            "human_gate": "physical_calibration_evidence",
            "execution_allowed": False,
        },
    ]
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "source": {
            "schema": DIRECTION_SCHEMA,
            "purpose": _text(direction_context["purpose"], "direction.purpose"),
            "next_action": _text(direction_context["next_action"], "direction.next_action"),
            "project_id": project_id.strip() if isinstance(project_id, str) and project_id.strip() else None,
            "relation_status": direction_context["frame"]["culture_computation"]["project_relation_status"],
        },
        "tasks": tasks,
        "execution": {
            "task_count": len(tasks),
            "executed_task_count": 0,
            "execution_allowed": False,
            "state_advance": False,
        },
        "next_action": "human_review_portfolio_work_packet_and_choose_one_task",
        "control": {
            "database_write": False,
            "decision_write": False,
            "state_advance": False,
            "selection_effect": "none",
            "promotion": "none",
            "publication": False,
            "normalize_execution": False,
            "measurement_execution": False,
        },
        "provenance": {
            "direction_schema": DIRECTION_SCHEMA,
            "deterministic": True,
            "task_execution": False,
            "semantic_claim": False,
            "learning_demonstrated": False,
            "decisions_require_external_human_actor": True,
        },
    }
    validate_portfolio_work_packet(result)
    return result


def validate_portfolio_work_packet(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise ValueError("portfolio_work_packet_schema_invalid")
    if payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True:
        raise ValueError("portfolio_work_packet_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "source", "tasks", "execution", "next_action", "control", "provenance"}
    if set(payload) != expected:
        raise ValueError("portfolio_work_packet_fields_invalid")
    source = payload["source"]
    if set(source) != {"schema", "purpose", "next_action", "project_id", "relation_status"} or source["schema"] != DIRECTION_SCHEMA:
        raise ValueError("portfolio_work_packet_source_invalid")
    _text(source["purpose"], "source.purpose")
    _text(source["next_action"], "source.next_action")
    if source["project_id"] is not None:
        _text(source["project_id"], "source.project_id")
    if source["relation_status"] not in {"unbound", "needs_evidence"}:
        raise ValueError("portfolio_work_packet_relation_status_invalid")
    tasks = payload["tasks"]
    if not isinstance(tasks, list) or len(tasks) != 4:
        raise ValueError("portfolio_work_packet_tasks_invalid")
    expected_ids = ["archive_orientation", "structural_order", "practice_relation", "vizz_calibration"]
    if [task.get("id") for task in tasks if isinstance(task, Mapping)] != expected_ids:
        raise ValueError("portfolio_work_packet_task_ids_invalid")
    expected_fields = {"id", "area", "layer", "state", "evidence", "action", "human_gate", "execution_allowed"}
    for task in tasks:
        if not isinstance(task, Mapping) or set(task) != expected_fields:
            raise ValueError("portfolio_work_packet_task_shape_invalid")
        for field in ("id", "area", "layer", "state", "evidence", "action", "human_gate"):
            _text(task[field], f"task.{field}")
        if task["execution_allowed"] is not False:
            raise ValueError("portfolio_work_packet_task_execution_invalid")
    if payload["execution"] != {"task_count": 4, "executed_task_count": 0, "execution_allowed": False, "state_advance": False}:
        raise ValueError("portfolio_work_packet_execution_invalid")
    _text(payload["next_action"], "next_action")
    if payload["control"] != {
        "database_write": False,
        "decision_write": False,
        "state_advance": False,
        "selection_effect": "none",
        "promotion": "none",
        "publication": False,
        "normalize_execution": False,
        "measurement_execution": False,
    }:
        raise ValueError("portfolio_work_packet_control_invalid")
    if payload["provenance"] != {
        "direction_schema": DIRECTION_SCHEMA,
        "deterministic": True,
        "task_execution": False,
        "semantic_claim": False,
        "learning_demonstrated": False,
        "decisions_require_external_human_actor": True,
    }:
        raise ValueError("portfolio_work_packet_provenance_invalid")
    return True


__all__ = [
    "ALGORITHM_VERSION",
    "SCHEMA",
    "build_portfolio_work_packet",
    "validate_portfolio_work_packet",
]
