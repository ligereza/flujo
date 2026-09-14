"""Read-only orientation matrix for the bounded archive portfolio view."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._contract_helpers import nonnegative_int as _int, required_text as _text


SCHEMA = "mak-portfolio-archive-orientation-v1"
ALGORITHM_VERSION = "portfolio-archive-orientation-1"
FORMAT_ROLES = {
    "declared-works": "source_declared_work",
    "documented-record": "named_record_not_work",
    "observed-field": "observed_field_without_title_inference",
    "practice-context": "code_technical_context_not_artwork",
}
FORMAT_IDS = list(FORMAT_ROLES)


def build_archive_orientation(archive_view: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize archive axes without adding titles, relations, or decisions."""
    if not isinstance(archive_view, Mapping) or archive_view.get("schema") != "mak-archive-portfolio-view-v1":
        raise ValueError("archive_view_schema_invalid")
    if archive_view.get("status") != "draft_only":
        raise ValueError("archive_view_must_be_draft_only")
    source = archive_view.get("source")
    formats = archive_view.get("formats")
    selection = archive_view.get("selection")
    reconciliation = archive_view.get("reconciliation")
    provenance = archive_view.get("provenance")
    if not all(isinstance(value, Mapping) for value in (source, selection, reconciliation, provenance)):
        raise ValueError("archive_orientation_source_shape_invalid")
    if not isinstance(formats, list):
        raise ValueError("archive_orientation_formats_invalid")
    by_id = {item.get("format_id"): item for item in formats if isinstance(item, Mapping)}
    if set(by_id) != set(FORMAT_IDS):
        raise ValueError("archive_orientation_formats_incomplete")
    axes = []
    for format_id in FORMAT_IDS:
        item = by_id[format_id]
        item_ids = item.get("item_ids")
        if not isinstance(item_ids, list) or any(not isinstance(value, str) or not value for value in item_ids):
            raise ValueError("archive_orientation_item_ids_invalid")
        rule = item.get("selection_rule")
        if not isinstance(rule, list) or any(not isinstance(value, str) or not value for value in rule):
            raise ValueError("archive_orientation_selection_rule_invalid")
        axes.append({
            "format_id": format_id,
            "role": FORMAT_ROLES[format_id],
            "purpose": _text(item.get("purpose"), f"format.{format_id}.purpose"),
            "selection_rule": list(rule),
            "item_count": len(item_ids),
            "omitted_count": _int(item.get("omitted_count"), f"format.{format_id}.omitted_count"),
        })
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "source": {
            "schema": archive_view["schema"],
            "path_hint": _text(source.get("path_hint"), "source.path_hint"),
            "input_hash": _text(source.get("input_hash"), "source.input_hash"),
            "source_piece_count": _int(reconciliation.get("source_piece_count"), "reconciliation.source_piece_count"),
            "source_link_count": _int(reconciliation.get("source_link_count"), "reconciliation.source_link_count"),
            "projected_link_count": _int(reconciliation.get("projected_link_count"), "reconciliation.projected_link_count"),
        },
        "axes": axes,
        "selection": {
            "visible_item_count": _int(selection.get("selected_item_count"), "selection.selected_item_count"),
            "declared_work_count": _int(selection.get("declared_work_count"), "selection.declared_work_count"),
            "documented_record_count": _int(selection.get("documented_record_count"), "selection.documented_record_count"),
            "observed_field_count": _int(selection.get("observed_field_count"), "selection.observed_field_count"),
            "practice_context_count": _int(selection.get("practice_context_count"), "selection.practice_context_count"),
            "omitted_piece_count": _int(reconciliation.get("omitted_piece_count"), "reconciliation.omitted_piece_count"),
        },
        "boundary": {
            "filename_is_not_authorship": provenance.get("filename_is_not_authorship") is True,
            "observed_text_is_not_author_statement": provenance.get("observed_text_is_not_author_statement") is True,
            "unselected_source_items_remain_in_input": provenance.get("unselected_source_items_remain_in_input") is True,
            "semantic_claim": False,
        },
        "control": {
            "database_write": False,
            "decision_write": False,
            "state_advance": False,
            "selection_effect": "none",
            "promotion": "none",
            "publication": False,
        },
        "next_action": "human_review_archive_orientation_axes_before_any_editorial_choice",
    }
    validate_archive_orientation(result)
    return result


def validate_archive_orientation(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True:
        raise ValueError("archive_orientation_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "source", "axes", "selection", "boundary", "control", "next_action"}
    if set(payload) != expected:
        raise ValueError("archive_orientation_fields_invalid")
    source = payload["source"]
    if set(source) != {"schema", "path_hint", "input_hash", "source_piece_count", "source_link_count", "projected_link_count"} or source["schema"] != "mak-archive-portfolio-view-v1":
        raise ValueError("archive_orientation_source_invalid")
    _text(source["path_hint"], "source.path_hint")
    _text(source["input_hash"], "source.input_hash")
    _int(source["source_piece_count"], "source.source_piece_count")
    _int(source["source_link_count"], "source.source_link_count")
    _int(source["projected_link_count"], "source.projected_link_count")
    axes = payload["axes"]
    if not isinstance(axes, list) or [axis.get("format_id") for axis in axes if isinstance(axis, Mapping)] != FORMAT_IDS:
        raise ValueError("archive_orientation_axes_invalid")
    axis_fields = {"format_id", "role", "purpose", "selection_rule", "item_count", "omitted_count"}
    for axis in axes:
        if not isinstance(axis, Mapping) or set(axis) != axis_fields or FORMAT_ROLES.get(axis["format_id"]) != axis["role"]:
            raise ValueError("archive_orientation_axis_shape_invalid")
        for field in ("format_id", "role", "purpose"):
            _text(axis[field], f"axis.{field}")
        if not isinstance(axis["selection_rule"], list) or any(not isinstance(value, str) or not value for value in axis["selection_rule"]):
            raise ValueError("archive_orientation_axis_rule_invalid")
        _int(axis["item_count"], "axis.item_count")
        _int(axis["omitted_count"], "axis.omitted_count")
    selection = payload["selection"]
    selection_fields = {"visible_item_count", "declared_work_count", "documented_record_count", "observed_field_count", "practice_context_count", "omitted_piece_count"}
    if set(selection) != selection_fields:
        raise ValueError("archive_orientation_selection_fields_invalid")
    for field in selection_fields:
        _int(selection[field], f"selection.{field}")
    if payload["boundary"] != {
        "filename_is_not_authorship": True,
        "observed_text_is_not_author_statement": True,
        "unselected_source_items_remain_in_input": True,
        "semantic_claim": False,
    }:
        raise ValueError("archive_orientation_boundary_invalid")
    if payload["control"] != {
        "database_write": False,
        "decision_write": False,
        "state_advance": False,
        "selection_effect": "none",
        "promotion": "none",
        "publication": False,
    }:
        raise ValueError("archive_orientation_control_invalid")
    _text(payload["next_action"], "next_action")
    return True


__all__ = ["ALGORITHM_VERSION", "FORMAT_IDS", "SCHEMA", "build_archive_orientation", "validate_archive_orientation"]
