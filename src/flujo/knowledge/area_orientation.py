"""Read-only orientation map for the areas observed by MAK.

This contract joins existing diagnostics, operational status, learning status,
and the VIZZ measurement refusal. It is an orientation surface only: it does
not infer semantic relations, select work, advance state, or execute checks.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA = "mak-area-orientation-v1"
ALGORITHM_VERSION = "area-orientation-1"
AREA_IDS = ["core", "rd", "portfolio", "cultura", "research", "vizz", "learning"]
DEPARTMENT_IDS = ["rd", "cultura", "iskvw"]


def _text(value: Any, field: str, default: str | None = None) -> str:
    if value is None and default is not None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_required")
    return value.strip()


def _domain_map(domains: Mapping[str, Any]) -> Mapping[str, Any]:
    value = domains.get("domains") if isinstance(domains.get("domains"), Mapping) else domains
    if not isinstance(value, Mapping):
        raise ValueError("area_orientation_domains_invalid")
    return value


def _domain_item(domain_map: Mapping[str, Any], area_id: str) -> Mapping[str, Any]:
    item = domain_map.get(area_id)
    if not isinstance(item, Mapping):
        raise ValueError(f"area_orientation_domain_missing_{area_id}")
    return item


def _component(status: Mapping[str, Any], component_id: str) -> Mapping[str, Any] | None:
    components = status.get("components")
    item = components.get(component_id) if isinstance(components, Mapping) else None
    return item if isinstance(item, Mapping) else None


def _checks(item: Mapping[str, Any]) -> list[str]:
    checks = item.get("checks", [])
    if not isinstance(checks, list) or any(not isinstance(value, str) or not value for value in checks):
        raise ValueError("area_orientation_checks_invalid")
    return list(checks)


def _department_surfaces(catalog: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    areas = catalog.get("areas") if isinstance(catalog, Mapping) else None
    if not isinstance(areas, Mapping):
        raise ValueError("area_orientation_departments_invalid")
    result = []
    for department_id in DEPARTMENT_IDS:
        item = areas.get(department_id)
        if not isinstance(item, Mapping):
            raise ValueError(f"area_orientation_department_missing_{department_id}")
        links = item.get("tool_links", [])
        if not isinstance(links, list) or any(not isinstance(link, Mapping) or not isinstance(link.get("path"), str) for link in links):
            raise ValueError("area_orientation_department_links_invalid")
        root_checks = item.get("root_checks", {})
        ready = item.get("ready") is True and (not isinstance(root_checks, Mapping) or all(value is True for value in root_checks.values()))
        result.append({"id": department_id, "label": _text(item.get("label"), f"department.{department_id}.label"), "surface": _text(item.get("surface"), f"department.{department_id}.surface"), "observed_status": "ready" if ready else "attention", "runtime_mode": _text(item.get("runtime_mode"), f"department.{department_id}.runtime_mode"), "contract_dir": _text(item.get("contract_dir"), f"department.{department_id}.contract_dir"), "handoff_exists": item.get("handoff_exists") is True, "tool_routes": [link["path"] for link in links], "read_only": True, "semantic_claim": False, "execution_allowed": False})
    return result


def _area(area_id: str, label: str, kind: str, domain: Mapping[str, Any] | None, component: Mapping[str, Any] | None, *, observed_status: str | None = None, status_basis: list[str] | None = None, next_action: str, route: str) -> dict[str, Any]:
    domain = domain or {}
    component = component or {}
    status = observed_status or component.get("status") or "catalogued"
    basis = status_basis or (["diagnostics_domain"] if domain else ["not_observed"])
    if not isinstance(basis, list) or any(not isinstance(value, str) or not value for value in basis):
        raise ValueError("area_orientation_status_basis_invalid")
    return {"id": area_id, "label": label, "kind": kind, "observed_status": _text(status, f"area.{area_id}.observed_status"), "status_basis": list(basis), "route": route, "contract_ref": _text(domain.get("contract"), f"area.{area_id}.contract_ref", "not_declared"), "checks": _checks(domain), "next_action": next_action, "read_only": True, "semantic_claim": False, "execution_allowed": False, "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False}}


def build_area_orientation(status: Mapping[str, Any], domains: Mapping[str, Any], *, vizz_status: Mapping[str, Any] | None = None, learning: Mapping[str, Any] | None = None, departments: Mapping[str, Any] | None = None, generated_at: str | None = None) -> dict[str, Any]:
    if not isinstance(status, Mapping) or not isinstance(domains, Mapping):
        raise ValueError("area_orientation_input_invalid")
    domain_map = _domain_map(domains)
    vizz_status = vizz_status if isinstance(vizz_status, Mapping) else {}
    learning = learning if isinstance(learning, Mapping) else {}
    learning_policy = learning.get("policy") if isinstance(learning.get("policy"), Mapping) else {}
    areas = [
        _area("core", "Core / Hub", "diagnostic_domain", _domain_item(domain_map, "core"), _component(status, "hub"), status_basis=["diagnostics_domain", "hub_component"], next_action="review_core_contract_and_run_declared_check_only", route="/api/diagnostics/domains"),
        _area("rd", "Research & Development", "diagnostic_domain", _domain_item(domain_map, "rd"), None, next_action="select_one_rd_surface_before_running_its_declared_check", route="/api/diagnostics/domains"),
        _area("portfolio", "Portafolio", "diagnostic_domain", _domain_item(domain_map, "portfolio"), _component(status, "portfolio"), status_basis=["diagnostics_domain", "portfolio_component"], next_action="human_review_portfolio_orientation_before_any_editorial_choice", route="/api/portfolio/archive-orientation"),
        _area("cultura", "Cultura", "diagnostic_domain", _domain_item(domain_map, "cultura"), None, next_action="select_one_cultura_surface_before_running_its_declared_check", route="/api/diagnostics/domains"),
        _area("research", "Research", "diagnostic_domain", _domain_item(domain_map, "research"), _component(status, "research"), status_basis=["diagnostics_domain", "research_component"], next_action="continue_research_from_observed_job_state_and_evidence_gate", route="/api/research/jobs"),
        _area("vizz", "VIZZ", "measurement_boundary", None, None, observed_status=vizz_status.get("status", "unknown_measurement_refused"), status_basis=["vizz_measurement_status"], next_action="keep_measurement_refused_until_independent_calibration_evidence_exists", route="/api/portfolio/vizz-measurement-status"),
        _area("learning", "Aprendizaje", "operational_learning", None, None, observed_status=learning_policy.get("status", "not_observed"), status_basis=["project_learning"], next_action="keep_candidate_policy_separate_from_verified_knowledge", route="/api/project/learning"),
    ]
    result = {"schema": SCHEMA, "algorithm_version": ALGORITHM_VERSION, "available": True, "read_only": True, "generated_at": _text(generated_at, "generated_at", "not_attached"), "system": {"observed_status": _text(status.get("status"), "system.observed_status", "unknown"), "attention_count": int(((status.get("ledger") or {}).get("counts") or {}).get("attention", 0)), "next_actions": list(((status.get("ledger") or {}).get("next_actions") or []))}, "areas": areas, "departments": _department_surfaces(departments), "boundary": {"status_is_operational_observation": True, "catalogue_is_not_semantic_knowledge": True, "learning_is_not_promotion": True, "vizz_measurement_refusal_is_preserved": vizz_status.get("status", "unknown_measurement_refused") == "unknown_measurement_refused", "semantic_claim": False}, "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False}, "next_action": "human_review_area_orientation_before_selecting_a_repo_or_execution_lane"}
    validate_area_orientation(result)
    return result


def validate_area_orientation(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA or payload.get("algorithm_version") != ALGORITHM_VERSION or payload.get("available") is not True or payload.get("read_only") is not True:
        raise ValueError("area_orientation_header_invalid")
    expected = {"schema", "algorithm_version", "available", "read_only", "generated_at", "system", "areas", "departments", "boundary", "control", "next_action"}
    if set(payload) != expected:
        raise ValueError("area_orientation_fields_invalid")
    _text(payload["generated_at"], "generated_at")
    system = payload["system"]
    if not isinstance(system, Mapping) or set(system) != {"observed_status", "attention_count", "next_actions"}:
        raise ValueError("area_orientation_system_invalid")
    _text(system["observed_status"], "system.observed_status")
    if not isinstance(system["attention_count"], int) or system["attention_count"] < 0:
        raise ValueError("area_orientation_attention_count_invalid")
    if not isinstance(system["next_actions"], list) or any(not isinstance(value, str) for value in system["next_actions"]):
        raise ValueError("area_orientation_next_actions_invalid")
    areas = payload["areas"]
    if not isinstance(areas, list) or [item.get("id") for item in areas if isinstance(item, Mapping)] != AREA_IDS:
        raise ValueError("area_orientation_area_ids_invalid")
    area_fields = {"id", "label", "kind", "observed_status", "status_basis", "route", "contract_ref", "checks", "next_action", "read_only", "semantic_claim", "execution_allowed", "control"}
    control = {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False}
    for item in areas:
        if not isinstance(item, Mapping) or set(item) != area_fields or item.get("id") not in AREA_IDS:
            raise ValueError("area_orientation_area_shape_invalid")
        for field in ("id", "label", "kind", "observed_status", "route", "contract_ref", "next_action"):
            _text(item[field], f"area.{item['id']}.{field}")
        if not isinstance(item["status_basis"], list) or any(not isinstance(value, str) or not value for value in item["status_basis"]):
            raise ValueError("area_orientation_status_basis_invalid")
        if not isinstance(item["checks"], list) or any(not isinstance(value, str) or not value for value in item["checks"]):
            raise ValueError("area_orientation_checks_invalid")
        if item["read_only"] is not True or item["semantic_claim"] is not False or item["execution_allowed"] is not False or item["control"] != control:
            raise ValueError("area_orientation_area_control_invalid")
    departments = payload["departments"]
    if not isinstance(departments, list) or [item.get("id") for item in departments if isinstance(item, Mapping)] != DEPARTMENT_IDS:
        raise ValueError("area_orientation_department_ids_invalid")
    department_fields = {"id", "label", "surface", "observed_status", "runtime_mode", "contract_dir", "handoff_exists", "tool_routes", "read_only", "semantic_claim", "execution_allowed"}
    for item in departments:
        if not isinstance(item, Mapping) or set(item) != department_fields:
            raise ValueError("area_orientation_department_shape_invalid")
        for field in ("id", "label", "surface", "observed_status", "runtime_mode", "contract_dir"):
            _text(item[field], f"department.{item.get('id')}.{field}")
        if not isinstance(item["handoff_exists"], bool) or not isinstance(item["tool_routes"], list) or any(not isinstance(value, str) or not value for value in item["tool_routes"]):
            raise ValueError("area_orientation_department_fields_invalid")
        if item["read_only"] is not True or item["semantic_claim"] is not False or item["execution_allowed"] is not False:
            raise ValueError("area_orientation_department_control_invalid")
    if payload["boundary"] != {"status_is_operational_observation": True, "catalogue_is_not_semantic_knowledge": True, "learning_is_not_promotion": True, "vizz_measurement_refusal_is_preserved": True, "semantic_claim": False}:
        raise ValueError("area_orientation_boundary_invalid")
    if payload["control"] != {**control, "execution": False}:
        raise ValueError("area_orientation_control_invalid")
    _text(payload["next_action"], "next_action")
    return True


__all__ = ["ALGORITHM_VERSION", "AREA_IDS", "DEPARTMENT_IDS", "SCHEMA", "build_area_orientation", "validate_area_orientation"]
