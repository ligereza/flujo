"""Build a Research Job plan from Project IR without creating a job or calling APIs."""

from __future__ import annotations

import importlib.util
from typing import Any, Mapping

from .project_ir import PROJECT_STATES, SCHEMA


PLAN_SCHEMA = "mak-project-research-plan-v1"
BLOCKED_STATES = {"unknown", "review_required", "quarantined", "contradicted"}
SUPPORTED_FORMATS = {"text", "document", "data"}
DOMAIN_ALIASES = {
    "plant": "plants", "botany": "plants", "botanical": "plants",
    "cultura": "curatoria", "cultural": "curatoria",
    "iskvw": "curatoria", "visual": "vj", "visuals": "vj",
    "opportunity": "general", "opportunities": "general", "funding": "general",
}


def _values(project: Mapping[str, Any], key: str) -> list[str]:
    raw = project.get(key, [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple, set)):
        return []
    return [str(value).strip().casefold() for value in raw if str(value).strip()]


def _format_families(project: Mapping[str, Any]) -> list[str]:
    values = []
    artifacts = project.get("artifacts", [])
    for artifact in artifacts if isinstance(artifacts, list) else []:
        if isinstance(artifact, Mapping):
            value = str(artifact.get("format_family") or "unknown").casefold()
            if value not in values:
                values.append(value)
    return values or ["unknown"]


def _question(project: Mapping[str, Any], domains: list[str], unknowns: list[str]) -> str:
    title = str(project.get("title") or "Untitled project").strip()
    parts = [title]
    if domains:
        parts.append("domains: " + ", ".join(domains))
    if unknowns:
        parts.append("open evidence: " + "; ".join(unknowns[:8]))
    return " | ".join(parts)


def _select_domain(domains: list[str], question: str) -> tuple[str | None, str | None]:
    for value in domains:
        normalized = DOMAIN_ALIASES.get(value, value)
        if normalized in {"plants", "vj", "curatoria", "rd", "portfolio", "general"}:
            return normalized, None
    try:
        from tools.research_job_router import detect_domain
        detected, _scores = detect_domain(question)
        return detected, None
    except (ImportError, OSError):
        return None, "research_adapter_unavailable"


def _dependency_checks() -> list[dict[str, Any]]:
    checks = [
        ("python3", True),
        ("tools.research_job_router", importlib.util.find_spec("tools.research_job_router") is not None),
        ("cultura.mak_plataforma.research_router", importlib.util.find_spec("cultura.mak_plataforma.research_router") is not None),
    ]
    return [{"name": name, "available": available} for name, available in checks]


def build_research_plan(project: Mapping[str, Any]) -> dict[str, Any]:
    """Return a plan-only packet; never writes a research job or calls a provider."""
    if project.get("schema") != SCHEMA:
        return {"schema": PLAN_SCHEMA, "decision": "abstain", "reason": "bad_project_ir_schema"}
    state = str(project.get("state") or "unknown")
    if state not in PROJECT_STATES:
        return {"schema": PLAN_SCHEMA, "decision": "abstain", "reason": "bad_project_state"}
    if state in BLOCKED_STATES:
        return {"schema": PLAN_SCHEMA, "decision": "abstain", "reason": "project_state_requires_evidence", "state": state}
    formats = _format_families(project)
    unsupported = sorted(set(formats) - SUPPORTED_FORMATS)
    if unsupported:
        return {"schema": PLAN_SCHEMA, "decision": "abstain", "reason": "research_format_not_supported", "formats": formats}
    dependencies = _dependency_checks()
    if not all(check["available"] for check in dependencies):
        return {
            "schema": PLAN_SCHEMA,
            "decision": "abstain",
            "reason": "research_dependency_missing",
            "dependencies": dependencies,
        }
    domains = _values(project, "domains")
    unknowns = _values(project, "unknowns")
    question = _question(project, domains, unknowns)
    domain, error = _select_domain(domains, question)
    if error or not domain:
        return {"schema": PLAN_SCHEMA, "decision": "abstain", "reason": error or "research_domain_missing"}
    try:
        from tools.interpretive_garden_workflow import SEMANTICS
        from cultura.mak_plataforma.research_router import route_research_task
        route = route_research_task("atender", question)
    except (ImportError, KeyError, OSError) as exc:
        return {"schema": PLAN_SCHEMA, "decision": "abstain", "reason": "research_semantics_unavailable", "detail": type(exc).__name__}
    steps = [
        {
            "order": order,
            "process": process_key,
            "input": input_semantics,
            "output": output_semantics,
            "output_kind": output_kind,
            "policy": policy,
            "status": "pending",
        }
        for order, (process_key, _label_es, input_semantics, output_semantics, output_kind, policy)
        in enumerate(SEMANTICS, 1)
    ]
    return {
        "schema": PLAN_SCHEMA,
        "decision": "select",
        "status": "plan_only",
        "project_id": project.get("project_id", ""),
        "question": question,
        "domain": domain,
        "formats": formats,
        "route": {
            "domain": route.domain,
            "intent": route.intent,
            "format": route.formato,
            "epistemic_mode": route.epistemic_mode,
            "required_fields": list(route.required_fields),
            "reason": route.reason,
        },
        "steps": steps,
        "dependencies": dependencies,
        "external_calls": 0,
        "writes": 0,
        "next_action": "review_plan_then_authorize_research_job",
    }
