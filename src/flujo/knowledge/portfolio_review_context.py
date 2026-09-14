"""Read-only boundary between the archive portfolio and project review.

The archive and the Project IR are useful in the same room, but a filename,
folder name or textual resemblance is not a relation between them. This
module therefore composes their measured summaries while refusing to bind a
project to an archive until a typed relation with explicit evidence exists.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA = "mak-portfolio-review-context-v1"
ALGORITHM_VERSION = "portfolio-review-context-1"


def _text(value: Any, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ValueError(f"{field}_must_be_string")
    result = value.strip()
    if required and not result:
        raise ValueError(f"{field}_required")
    return result


def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{field}_must_be_string_list")
    return list(value)


def _archive_summary(archive_view: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(archive_view, Mapping):
        raise ValueError("archive_view_must_be_object")
    if archive_view.get("schema") != "mak-archive-portfolio-view-v1":
        raise ValueError("archive_view_schema_invalid")
    source = archive_view.get("source")
    selection = archive_view.get("selection")
    reconciliation = archive_view.get("reconciliation")
    if not isinstance(source, Mapping) or not isinstance(selection, Mapping):
        raise ValueError("archive_view_summary_missing")
    if not isinstance(reconciliation, Mapping):
        raise ValueError("archive_view_reconciliation_missing")
    source_hash = _text(source.get("input_hash"), "archive.source_hash")
    visible = selection.get("selected_item_count")
    omitted = reconciliation.get("omitted_piece_count")
    if not isinstance(visible, int) or visible < 0:
        raise ValueError("archive.visible_item_count_invalid")
    if not isinstance(omitted, int) or omitted < 0:
        raise ValueError("archive.omitted_item_count_invalid")
    return {
        "schema": "mak-archive-portfolio-view-v1",
        "source_hash": source_hash,
        "source_ref": source.get("path_hint", "iskvw/datos/archivo.json"),
        "visible_item_count": visible,
        "omitted_item_count": omitted,
    }


def _project_summary(
    project_id: str | None,
    review_items: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], str, str]:
    normalized_id = (project_id or "").strip() or None
    selected = None
    if normalized_id:
        for item in review_items:
            if isinstance(item, Mapping) and item.get("project_id") == normalized_id:
                selected = item
                break
    if selected is None and normalized_id is None:
        return ({
            "project_id": None,
            "episode_id": None,
            "title": None,
            "state": None,
            "found_in_review_queue": False,
            "unknowns": [],
            "evidence": [],
            "next_action": "select_project_id_before_binding",
        }, "unbound", "No se seleccionó un proyecto; no se intenta inferir un vínculo.")
    if selected is None:
        return ({
            "project_id": normalized_id,
            "episode_id": None,
            "title": None,
            "state": None,
            "found_in_review_queue": False,
            "unknowns": [],
            "evidence": [],
            "next_action": "verify_project_record_and_typed_archive_relation",
        }, "unbound", "El proyecto no está en la cola observada; no se intenta inferir un vínculo.")
    unknowns = _strings(selected.get("unknowns", []), "project.unknowns")
    evidence = selected.get("evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(row, Mapping) for row in evidence):
        raise ValueError("project.evidence_invalid")
    return ({
        "project_id": normalized_id,
        "episode_id": None,
        "title": _text(selected.get("title"), "project.title"),
        "state": _text(selected.get("state"), "project.state"),
        "found_in_review_queue": True,
        "unknowns": unknowns,
        "evidence": [dict(row) for row in evidence],
        "next_action": "provide_typed_archive_project_relation_with_source_refs",
    }, "needs_evidence", "La cola no contiene una relación tipada archivo-proyecto con referencias explícitas.")


def compile_portfolio_review_context(
    archive_view: Mapping[str, Any],
    review_items: Sequence[Mapping[str, Any]],
    *,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Compose archive and review facts without creating a cross-link."""
    if not isinstance(review_items, Sequence) or isinstance(review_items, (str, bytes, bytearray)):
        raise ValueError("review_items_must_be_sequence")
    archive = _archive_summary(archive_view)
    project, relation_status, reason = _project_summary(project_id, review_items)
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "archive": archive,
        "project": project,
        "relation": {
            "status": relation_status,
            "typed_relation_present": False,
            "evidence_refs": [],
            "selection_effect": "none",
            "reason": reason,
        },
        "control": {
            "database_write": False,
            "decision_write": False,
            "promotion": "none",
            "publication": False,
        },
        "provenance": {
            "archive_source": "mak-archive-portfolio-view-v1",
            "project_source": "mak-review-queue-v1",
            "deterministic": True,
            "relation_inference": False,
            "name_or_path_matching": False,
            "decisions_require_external_human_actor": True,
        },
    }
    validate_portfolio_review_context(result)
    return result


def validate_portfolio_review_context(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise ValueError("portfolio_review_context_schema_invalid")
    if payload.get("algorithm_version") != ALGORITHM_VERSION:
        raise ValueError("portfolio_review_context_algorithm_version_invalid")
    if payload.get("available") is not True or payload.get("read_only") is not True:
        raise ValueError("portfolio_review_context_availability_invalid")
    expected = {
        "schema", "algorithm_version", "available", "read_only", "archive",
        "project", "relation", "control", "provenance",
    }
    if set(payload) != expected:
        raise ValueError("portfolio_review_context_fields_invalid")
    archive = payload["archive"]
    if set(archive) != {"schema", "source_hash", "source_ref", "visible_item_count", "omitted_item_count"}:
        raise ValueError("portfolio_review_context_archive_fields_invalid")
    if archive["schema"] != "mak-archive-portfolio-view-v1":
        raise ValueError("portfolio_review_context_archive_schema_invalid")
    _text(archive["source_hash"], "archive.source_hash")
    _text(archive["source_ref"], "archive.source_ref")
    for field in ("visible_item_count", "omitted_item_count"):
        if not isinstance(archive[field], int) or archive[field] < 0:
            raise ValueError(f"archive.{field}_invalid")
    project = payload["project"]
    if set(project) != {
        "project_id", "episode_id", "title", "state", "found_in_review_queue",
        "unknowns", "evidence", "next_action",
    }:
        raise ValueError("portfolio_review_context_project_fields_invalid")
    for field in ("project_id", "episode_id", "title", "state"):
        if project[field] is not None:
            _text(project[field], f"project.{field}")
    if not isinstance(project["found_in_review_queue"], bool):
        raise ValueError("project.found_in_review_queue_invalid")
    _strings(project["unknowns"], "project.unknowns")
    if not isinstance(project["evidence"], list) or any(
        not isinstance(row, Mapping) for row in project["evidence"]
    ):
        raise ValueError("project.evidence_invalid")
    _text(project["next_action"], "project.next_action")
    relation = payload["relation"]
    if set(relation) != {"status", "typed_relation_present", "evidence_refs", "selection_effect", "reason"}:
        raise ValueError("portfolio_review_context_relation_fields_invalid")
    if relation["status"] not in {"unbound", "needs_evidence"}:
        raise ValueError("portfolio_review_context_relation_status_invalid")
    if relation["typed_relation_present"] is not False:
        raise ValueError("portfolio_review_context_relation_must_be_unbound")
    _strings(relation["evidence_refs"], "relation.evidence_refs")
    if relation["selection_effect"] != "none":
        raise ValueError("portfolio_review_context_selection_effect_invalid")
    _text(relation["reason"], "relation.reason")
    if payload["control"] != {
        "database_write": False,
        "decision_write": False,
        "promotion": "none",
        "publication": False,
    }:
        raise ValueError("portfolio_review_context_control_invalid")
    if payload["provenance"] != {
        "archive_source": "mak-archive-portfolio-view-v1",
        "project_source": "mak-review-queue-v1",
        "deterministic": True,
        "relation_inference": False,
        "name_or_path_matching": False,
        "decisions_require_external_human_actor": True,
    }:
        raise ValueError("portfolio_review_context_provenance_invalid")
    return True


__all__ = [
    "ALGORITHM_VERSION",
    "SCHEMA",
    "compile_portfolio_review_context",
    "validate_portfolio_review_context",
]
