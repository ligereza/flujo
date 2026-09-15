"""Read-only evidence plan for a portfolio/project relation still needing proof."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._contract_helpers import required_text as _text


SCHEMA = "mak-portfolio-relation-evidence-plan-v1"
ALGORITHM_VERSION = "portfolio-relation-evidence-plan-1"
REQUIRED_EVIDENCE = {
    "official_call": "official_call_source",
    "problem_and_context": "project_statement_source",
    "method": "method_description_source",
    "budget": "authorized_budget_source",
    "schedule": "verifiable_schedule_source",
    "team": "team_attribution_source",
}


def build_relation_evidence_plan(review_context: Mapping[str, Any]) -> dict[str, Any]:
    """Convert observed unknowns into review requirements, never into claims."""
    if not isinstance(review_context, Mapping) or review_context.get("schema") != "mak-portfolio-review-context-v1":
        raise ValueError("review_context_schema_invalid")
    if review_context.get("available") is not True or review_context.get("read_only") is not True:
        raise ValueError("review_context_must_be_read_only")
    project = review_context.get("project")
    relation = review_context.get("relation")
    if not isinstance(project, Mapping) or not isinstance(relation, Mapping):
        raise ValueError("review_context_project_relation_invalid")
    project_id_value = project.get("project_id")
    title_value = project.get("title")
    state_value = project.get("state")
    unbound = project_id_value is None or not str(project_id_value).strip()
    if unbound:
        project_id = None
        title = None
        state = None
    else:
        project_id = _text(project_id_value, "project.project_id")
        title = (_text(title_value, "project.title")
                 if title_value is not None else None)
        state = (_text(state_value, "project.state")
                 if state_value is not None else None)
    unknowns = project.get("unknowns")
    evidence = project.get("evidence")
    if not isinstance(unknowns, list) or any(not isinstance(item, str) or not item.strip() for item in unknowns):
        raise ValueError("project.unknowns_invalid")
    if not isinstance(evidence, list) or any(not isinstance(item, Mapping) for item in evidence):
        raise ValueError("project.evidence_invalid")
    requirements = []
    for unknown in unknowns:
        key = unknown.split(":", 1)[0].strip()
        requirements.append({
            "requirement_id": key,
            "unknown": unknown,
            "expected_evidence_kind": REQUIRED_EVIDENCE.get(key, "project_specific_source"),
            "status": "missing",
            "candidate_count": 0,
        })
    observed = []
    for item in evidence:
        observed.append({
            "kind": _text(item.get("kind"), "evidence.kind"),
            "status": _text(item.get("status"), "evidence.status"),
            "reference_present": bool(item.get("source_ref")),
            "reference_class": "local_source_reference" if item.get("source_ref") else "unbound_evidence",
        })
    result = {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "available": True,
        "read_only": True,
        "project": {
            "project_id": project_id,
            "title": title,
            "state": state,
            "unknown_count": len(unknowns),
            "observed_evidence_count": len(observed),
        },
        "relation": {
            "status": "unbound" if unbound else _text(
                relation.get("status"), "relation.status"),
            "typed_relation_present": False,
            "selection_effect": "none",
            "evidence_refs": [],
        },
        "requirements": [] if unbound else requirements,
        "observed_evidence": [] if unbound else observed,
        "unresolved_count": 0 if unbound else len(requirements),
        "next_action": ("select_project_id_before_planning_relation_evidence"
                        if unbound else
                        "human_review_relation_requirements_and_supply_source_refs"),
        "control": {
            "database_write": False,
            "decision_write": False,
            "state_advance": False,
            "selection_effect": "none",
            "promotion": "none",
            "publication": False,
        },
        "provenance": {
            "source_schema": "mak-portfolio-review-context-v1",
            "deterministic": True,
            "relation_inference": False,
            "path_or_name_matching": False,
            "semantic_claim": False,
            "learning_demonstrated": False,
            "decisions_require_external_human_actor": True,
        },
    }
    validate_relation_evidence_plan(result)
    return result


def validate_relation_evidence_plan(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True:
        raise ValueError("relation_evidence_plan_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "project", "relation", "requirements", "observed_evidence", "unresolved_count", "next_action", "control", "provenance"}
    if set(payload) != expected:
        raise ValueError("relation_evidence_plan_fields_invalid")
    project = payload["project"]
    if set(project) != {"project_id", "title", "state", "unknown_count", "observed_evidence_count"}:
        raise ValueError("relation_evidence_plan_project_invalid")
    for field in ("unknown_count", "observed_evidence_count"):
        if not isinstance(project[field], int) or project[field] < 0:
            raise ValueError(f"project.{field}_invalid")
    relation = payload["relation"]
    if not isinstance(relation, Mapping) or set(relation) != {
        "status", "typed_relation_present", "selection_effect", "evidence_refs"
    } or relation["status"] not in {"needs_evidence", "unbound"} \
            or relation["typed_relation_present"] is not False \
            or relation["selection_effect"] != "none" \
            or relation["evidence_refs"] != []:
        raise ValueError("relation_evidence_plan_relation_invalid")
    unbound = relation["status"] == "unbound"
    if unbound:
        if project["project_id"] is not None:
            _text(project["project_id"], "project.project_id")
        if project["title"] is not None or project["state"] is not None:
            raise ValueError("relation_evidence_plan_unbound_project_invalid")
        if project["unknown_count"] != 0 or project["observed_evidence_count"] != 0:
            raise ValueError("relation_evidence_plan_unbound_counts_invalid")
    else:
        for field in ("project_id", "title", "state"):
            _text(project[field], f"project.{field}")
    requirements = payload["requirements"]
    if not isinstance(requirements, list) or len(requirements) != project["unknown_count"]:
        raise ValueError("relation_evidence_plan_requirements_invalid")
    fields = {"requirement_id", "unknown", "expected_evidence_kind", "status", "candidate_count"}
    for item in requirements:
        if not isinstance(item, Mapping) or set(item) != fields or item["status"] != "missing" or item["candidate_count"] != 0:
            raise ValueError("relation_evidence_plan_requirement_shape_invalid")
        for field in ("requirement_id", "unknown", "expected_evidence_kind"):
            _text(item[field], f"requirement.{field}")
    observed = payload["observed_evidence"]
    if not isinstance(observed, list) or len(observed) != project["observed_evidence_count"]:
        raise ValueError("relation_evidence_plan_observed_invalid")
    for item in observed:
        if not isinstance(item, Mapping) or set(item) != {"kind", "status", "reference_present", "reference_class"}:
            raise ValueError("relation_evidence_plan_observed_shape_invalid")
        _text(item["kind"], "observed.kind")
        _text(item["status"], "observed.status")
        if not isinstance(item["reference_present"], bool) or item["reference_class"] not in {"local_source_reference", "unbound_evidence"}:
            raise ValueError("relation_evidence_plan_observed_boundary_invalid")
    if payload["unresolved_count"] != len(requirements):
        raise ValueError("relation_evidence_plan_unresolved_invalid")
    _text(payload["next_action"], "next_action")
    if payload["control"] != {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False}:
        raise ValueError("relation_evidence_plan_control_invalid")
    if payload["provenance"] != {"source_schema": "mak-portfolio-review-context-v1", "deterministic": True, "relation_inference": False, "path_or_name_matching": False, "semantic_claim": False, "learning_demonstrated": False, "decisions_require_external_human_actor": True}:
        raise ValueError("relation_evidence_plan_provenance_invalid")
    return True


__all__ = ["ALGORITHM_VERSION", "SCHEMA", "build_relation_evidence_plan", "validate_relation_evidence_plan"]
