"""Read-only working frame for the MAK portfolio.

The portfolio needs a legible place where vision, order, and
culture/computation can be discussed together.  This module composes already
measured surfaces; it does not infer authorship, create archive relations,
turn structure into meaning, or promote anything to publication.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._contract_helpers import nonnegative_int as _nonnegative_int, required_text as _text


SCHEMA = "mak-portfolio-direction-context-v1"
ALGORITHM_VERSION = "portfolio-direction-context-1"


def _obj(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field}_must_be_object")
    return value


def _read_only_surface(payload: Mapping[str, Any], field: str, schema: str) -> Mapping[str, Any]:
    if payload.get("schema") != schema:
        raise ValueError(f"{field}_schema_invalid")
    if payload.get("available") is not True or payload.get("read_only") is not True:
        raise ValueError(f"{field}_must_be_available_read_only")
    return payload


def build_portfolio_direction_context(
    archive_view: Mapping[str, Any],
    review_context: Mapping[str, Any],
    operation_receipt: Mapping[str, Any],
    vizz_measurement: Mapping[str, Any],
    vizz_lineage: Mapping[str, Any],
    structural_delta: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose portfolio orientation without opening an editorial gate."""
    archive = _obj(archive_view, "archive_view")
    if archive.get("schema") != "mak-archive-portfolio-view-v1":
        raise ValueError("archive_view_schema_invalid")
    if archive.get("status") != "draft_only":
        raise ValueError("archive_view_must_be_draft_only")
    review = _read_only_surface(
        _obj(review_context, "review_context"),
        "review_context",
        "mak-portfolio-review-context-v1",
    )
    receipt = _read_only_surface(
        _obj(operation_receipt, "operation_receipt"),
        "operation_receipt",
        "mak-operation-receipt-v1",
    )
    measurement = _read_only_surface(
        _obj(vizz_measurement, "vizz_measurement"),
        "vizz_measurement",
        "mak-vizz-measurement-status-v1",
    )
    lineage = _read_only_surface(
        _obj(vizz_lineage, "vizz_lineage"),
        "vizz_lineage",
        "mak-vizz-lineage-status-v1",
    )
    delta = _read_only_surface(
        _obj(structural_delta, "structural_delta"),
        "structural_delta",
        "mak-structural-delta-status-v1",
    )

    source = _obj(archive.get("source"), "archive.source")
    selection = _obj(archive.get("selection"), "archive.selection")
    reconciliation = _obj(archive.get("reconciliation"), "archive.reconciliation")
    project = _obj(review.get("project"), "review.project")
    relation = _obj(review.get("relation"), "review.relation")
    operation = _obj(receipt.get("operation"), "operation_receipt.operation")
    measurement_data = _obj(measurement.get("measurement"), "vizz_measurement.measurement")
    delta_data = _obj(delta.get("delta"), "structural_delta.delta")
    contracurator = archive.get("contracurator")
    contracurator_status = (
        _text(_obj(contracurator, "archive.contracurator").get("status"), "archive.contracurator.status")
        if isinstance(contracurator, Mapping)
        else "not_available"
    )

    project_unknowns = project.get("unknowns", [])
    project_evidence = project.get("evidence", [])
    if not isinstance(project_unknowns, list) or not all(isinstance(item, str) for item in project_unknowns):
        raise ValueError("review.project.unknowns_invalid")
    if not isinstance(project_evidence, list) or not all(isinstance(item, Mapping) for item in project_evidence):
        raise ValueError("review.project.evidence_invalid")

    visible = _nonnegative_int(selection.get("selected_item_count"), "archive.selection.selected_item_count")
    declared = _nonnegative_int(selection.get("declared_work_count"), "archive.selection.declared_work_count")
    observed = _nonnegative_int(selection.get("observed_field_count"), "archive.selection.observed_field_count")
    practice = _nonnegative_int(selection.get("practice_context_count"), "archive.selection.practice_context_count")
    omitted = _nonnegative_int(reconciliation.get("omitted_piece_count"), "archive.reconciliation.omitted_piece_count")
    expanded = _nonnegative_int(operation.get("expanded_count"), "operation.expanded_count")
    evaluated = _nonnegative_int(delta_data.get("evaluated_keys"), "structural_delta.evaluated_keys")
    shared = _nonnegative_int(delta_data.get("shared_keys"), "structural_delta.shared_keys")
    residue = _nonnegative_int(delta_data.get("residue_keys"), "structural_delta.residue_keys")
    evidence_count = len(project_evidence)
    unknown_count = len(project_unknowns)

    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "purpose": "vision_order_culture_computation_read_only_frame",
        "frame": {
            "vision": {
                "state": "bounded_observation",
                "archive_status": _text(archive.get("status"), "archive.status"),
                "source_hash": _text(source.get("input_hash"), "archive.source.input_hash"),
                "visible_item_count": visible,
                "declared_work_count": declared,
                "internal_hypothesis_status": contracurator_status,
                "semantic_claim_established": False,
                "next_action": "review_archive_observations_with_human_context",
            },
            "order": {
                "state": "structural_order_only",
                "operation_status": _text(receipt.get("status"), "operation_receipt.status"),
                "operation_name": _text(operation.get("name"), "operation.name"),
                "expanded_count": expanded,
                "delta_status": _text(delta.get("status"), "structural_delta.status"),
                "evaluated_keys": evaluated,
                "shared_keys": shared,
                "residue_keys": residue,
                "semantic_equivalence_established": False,
                "next_action": "preserve_provenance_before_any_reuse_claim",
            },
            "culture_computation": {
                "state": "observed_practice_context",
                "practice_context_count": practice,
                "observed_field_count": observed,
                "documented_record_count": _nonnegative_int(selection.get("documented_record_count"), "archive.selection.documented_record_count"),
                "omitted_piece_count": omitted,
                "project_relation_status": _text(relation.get("status"), "review.relation.status"),
                "project_evidence_count": evidence_count,
                "project_unknown_count": unknown_count,
                "relation_inference": False,
                "next_action": _text(project.get("next_action"), "review.project.next_action"),
            },
            "instrument": {
                "state": "vizz_measurement_refused",
                "measurement_status": _text(measurement.get("status"), "vizz_measurement.status"),
                "measurement_unknown": measurement_data.get("unknown") is True,
                "triangulation_attempted": measurement_data.get("triangulation_attempted") is True,
                "depth_result_present": measurement_data.get("depth_result_present") is True,
                "lineage_status": _text(lineage.get("status"), "vizz_lineage.status"),
                "measurement_claim_allowed": False,
                "next_action": _text(measurement.get("next_action"), "vizz_measurement.next_action"),
            },
        },
        "directions": [
            {
                "id": "vision",
                "kind": "orientation",
                "state": "bounded_observation",
                "human_gate": "interpretation_and_editorial_context",
            },
            {
                "id": "order",
                "kind": "computation",
                "state": "structural_order_only",
                "human_gate": "semantic_reuse_or_equivalence",
            },
            {
                "id": "culture_computation",
                "kind": "practice_context",
                "state": "observed_not_authored",
                "human_gate": "typed_relation_and_attribution",
            },
        ],
        "next_action": "human_review_portfolio_direction_and_source_scope",
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
            "components": [
                "mak-archive-portfolio-view-v1",
                "mak-portfolio-review-context-v1",
                "mak-operation-receipt-v1",
                "mak-vizz-measurement-status-v1",
                "mak-vizz-lineage-status-v1",
                "mak-structural-delta-status-v1",
            ],
            "deterministic": True,
            "relation_inference": False,
            "semantic_claim": False,
            "semantic_equivalence": False,
            "learning_demonstrated": False,
            "decisions_require_external_human_actor": True,
        },
    }
    validate_portfolio_direction_context(result)
    return result


def validate_portfolio_direction_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise ValueError("portfolio_direction_context_schema_invalid")
    if payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ValueError("portfolio_direction_context_algorithm_version_invalid")
    if payload.get("available") is not True or payload.get("read_only") is not True:
        raise ValueError("portfolio_direction_context_availability_invalid")
    expected = {
        "schema", "algorithm_version", "available", "read_only", "purpose",
        "frame", "directions", "next_action", "control", "provenance",
    }
    if set(payload) != expected:
        raise ValueError("portfolio_direction_context_fields_invalid")
    frame = _obj(payload["frame"], "frame")
    if set(frame) != {"vision", "order", "culture_computation", "instrument"}:
        raise ValueError("portfolio_direction_context_frame_fields_invalid")
    vision = _obj(frame["vision"], "frame.vision")
    if set(vision) != {
        "state", "archive_status", "source_hash", "visible_item_count",
        "declared_work_count", "internal_hypothesis_status",
        "semantic_claim_established", "next_action",
    }:
        raise ValueError("portfolio_direction_context_vision_fields_invalid")
    if vision["state"] != "bounded_observation" or vision["archive_status"] != "draft_only" or vision["semantic_claim_established"] is not False:
        raise ValueError("portfolio_direction_context_vision_boundary_invalid")
    _text(vision["source_hash"], "frame.vision.source_hash")
    _text(vision["internal_hypothesis_status"], "frame.vision.internal_hypothesis_status")
    _text(vision["next_action"], "frame.vision.next_action")
    _nonnegative_int(vision["visible_item_count"], "frame.vision.visible_item_count")
    _nonnegative_int(vision["declared_work_count"], "frame.vision.declared_work_count")

    order = _obj(frame["order"], "frame.order")
    if set(order) != {
        "state", "operation_status", "operation_name", "expanded_count",
        "delta_status", "evaluated_keys", "shared_keys", "residue_keys",
        "semantic_equivalence_established", "next_action",
    }:
        raise ValueError("portfolio_direction_context_order_fields_invalid")
    if order["state"] != "structural_order_only" or order["semantic_equivalence_established"] is not False:
        raise ValueError("portfolio_direction_context_order_boundary_invalid")
    for field in ("operation_status", "operation_name", "delta_status", "next_action"):
        _text(order[field], f"frame.order.{field}")
    for field in ("expanded_count", "evaluated_keys", "shared_keys", "residue_keys"):
        _nonnegative_int(order[field], f"frame.order.{field}")

    culture = _obj(frame["culture_computation"], "frame.culture_computation")
    if set(culture) != {
        "state", "practice_context_count", "observed_field_count",
        "documented_record_count", "omitted_piece_count",
        "project_relation_status", "project_evidence_count",
        "project_unknown_count", "relation_inference", "next_action",
    }:
        raise ValueError("portfolio_direction_context_culture_fields_invalid")
    if culture["state"] != "observed_practice_context" or culture["relation_inference"] is not False:
        raise ValueError("portfolio_direction_context_culture_boundary_invalid")
    for field in ("practice_context_count", "observed_field_count", "documented_record_count", "omitted_piece_count", "project_evidence_count", "project_unknown_count"):
        _nonnegative_int(culture[field], f"frame.culture_computation.{field}")
    if culture["project_relation_status"] not in {"unbound", "needs_evidence"}:
        raise ValueError("portfolio_direction_context_relation_status_invalid")
    _text(culture["next_action"], "frame.culture_computation.next_action")

    instrument = _obj(frame["instrument"], "frame.instrument")
    if set(instrument) != {
        "state", "measurement_status", "measurement_unknown",
        "triangulation_attempted", "depth_result_present", "lineage_status",
        "measurement_claim_allowed", "next_action",
    }:
        raise ValueError("portfolio_direction_context_instrument_fields_invalid")
    if instrument["state"] != "vizz_measurement_refused" or instrument["measurement_status"] != "unknown_measurement_refused":
        raise ValueError("portfolio_direction_context_instrument_state_invalid")
    if instrument["measurement_unknown"] is not True or instrument["triangulation_attempted"] is not False or instrument["depth_result_present"] is not False or instrument["measurement_claim_allowed"] is not False:
        raise ValueError("portfolio_direction_context_instrument_boundary_invalid")
    _text(instrument["lineage_status"], "frame.instrument.lineage_status")
    _text(instrument["next_action"], "frame.instrument.next_action")
    directions = payload["directions"]
    if not isinstance(directions, list) or len(directions) != 3:
        raise ValueError("portfolio_direction_context_directions_invalid")
    if [item.get("id") for item in directions if isinstance(item, Mapping)] != ["vision", "order", "culture_computation"]:
        raise ValueError("portfolio_direction_context_direction_ids_invalid")
    if any(not isinstance(item, Mapping) or set(item) != {"id", "kind", "state", "human_gate"} for item in directions):
        raise ValueError("portfolio_direction_context_direction_shape_invalid")
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
        raise ValueError("portfolio_direction_context_control_invalid")
    provenance = payload["provenance"]
    if set(provenance) != {
        "components", "deterministic", "relation_inference", "semantic_claim",
        "semantic_equivalence", "learning_demonstrated",
        "decisions_require_external_human_actor",
    }:
        raise ValueError("portfolio_direction_context_provenance_fields_invalid")
    if provenance["components"] != [
        "mak-archive-portfolio-view-v1",
        "mak-portfolio-review-context-v1",
        "mak-operation-receipt-v1",
        "mak-vizz-measurement-status-v1",
        "mak-vizz-lineage-status-v1",
        "mak-structural-delta-status-v1",
    ]:
        raise ValueError("portfolio_direction_context_components_invalid")
    if any(provenance[key] is not False for key in ("relation_inference", "semantic_claim", "semantic_equivalence", "learning_demonstrated")):
        raise ValueError("portfolio_direction_context_claim_boundary_invalid")
    if provenance["deterministic"] is not True or provenance["decisions_require_external_human_actor"] is not True:
        raise ValueError("portfolio_direction_context_provenance_boundary_invalid")
    return True


__all__ = [
    "ALGORITHM_VERSION",
    "SCHEMA",
    "build_portfolio_direction_context",
    "validate_portfolio_direction_context",
]
