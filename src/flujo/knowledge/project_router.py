"""Conservative Project IR router with explicit abstention.

The router chooses a declared consumer; it does not execute it.  A route is
valid only when the Project IR exposes a compatible format/domain and the
consumer contract is read-only or explicitly marked for later authorization.
Unknown inputs produce an abstention packet instead of a guessed tool call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .project_ir import PROJECT_STATES, SCHEMA, stable_json


ROUTER_SCHEMA = "mak-project-router-v1"


@dataclass(frozen=True)
class ToolContract:
    tool_id: str
    path: str
    purpose: str
    formats: tuple[str, ...]
    domains: tuple[str, ...]
    mode: str
    output: str


TOOL_CATALOG = (
    ToolContract(
        "math_kernel", "tools/math_kernel.py",
        "schedule metadata-only mathematical search on the cultural-research first layer",
        ("math_target",), ("mathematics",), "plan_only", "math_search_request",
    ),
    ToolContract(
        "source_learning_bridge", "tools/source_learning_bridge.py",
        "validate traceable source memory and preserve epistemic claim boundaries",
        ("text", "data"), ("source_memory",), "read_only", "source_learning_verification",
    ),
    ToolContract(
        "project_intake", "tools/build_application_intake.py",
        "convert a bounded source folder or SSD index into an application candidate",
        ("unknown", "text", "image", "video", "audio", "3d", "data", "document", "all"),
        ("mak", "funding", "general"), "read_only", "application_package",
    ),
    ToolContract(
        "research_job_router", "tools/research_job_router.py",
        "plan a research job with domain adapter and semantic steps",
        ("text", "document", "data", "unknown"),
        ("research", "funding", "curatoria", "portfolio", "cultura", "general"),
        "plan_only", "research_job",
    ),
    ToolContract(
        "blend_scene_audit", "tools/audit_blend_scene.py",
        "inspect a Blender scene without mutating its source",
        ("3d",), ("rd", "portfolio", "iskvw", "cultura"), "read_only", "scene_audit",
    ),
    ToolContract(
        "knowledge_reconciliation", "src/flujo/knowledge/reconciliation.py",
        "compare candidate and legacy databases without applying migration",
        ("database",), ("rd", "mak", "research", "general"), "read_only", "reconciliation_plan",
    ),
    ToolContract(
        "research_opportunity_gate", "tools/research_job_router.py",
        "prepare an opportunity/funding research route; official source remains required",
        ("text", "document", "data", "unknown"),
        ("funding", "opportunities", "research", "general"), "plan_only", "opportunity_gate",
    ),
    ToolContract(
        "tennis_shot_event_consumer", "tools/tennis_shot_events.py",
        "project local annotated tennis notation into loss-aware shot events",
        ("data",), ("tennis",), "read_only", "shot_event_jsonl",
    ),
    ToolContract(
        "research_source_capture", "tools/research_source_capture.py",
        "capture one reviewed public source with bounded provenance",
        ("text", "document", "data", "unknown"), ("scraping",), "plan_only", "source_capture",
    ),
    ToolContract(
        "deep_learning_gate", "tools/deep_learning_gate.py",
        "check labels, independent holdout and validator before model work",
        ("data", "image", "video", "3d"), ("deep_learning", "learning", "micelio"), "read_only", "learning_task_gate",
    ),
    ToolContract(
        "research_simulation_consumer", "tools/research_simulation.py",
        "run a bounded declared symbolic research simulation and label it as a model",
        ("data", "text"), ("plants", "simulation", "research"), "read_only", "research_simulation_result",
    ),
)


def _domain_values(project: Mapping[str, Any]) -> set[str]:
    values = project.get("domains", [])
    if isinstance(values, str):
        values = [values]
    return {str(item).casefold().strip() for item in values if str(item).strip()}


def _format_values(project: Mapping[str, Any]) -> set[str]:
    formats = set()
    artifacts = project.get("artifacts", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, Mapping):
                value = str(artifact.get("format_family") or "unknown").casefold()
                formats.add(value)
    return formats or {"unknown"}


def _promoted_rules(rules: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    output = []
    for rule in rules:
        if str(rule.get("status") or "") != "promoted":
            continue
        try:
            trigger = json.loads(str(rule.get("trigger_json") or "{}"))
            action = json.loads(str(rule.get("action_json") or "{}"))
        except json.JSONDecodeError:
            continue
        output.append({"trigger": trigger, "action": action, "rule_id": rule.get("rule_id")})
    return output


def _rule_matches(rule: Mapping[str, Any], domains: set[str], formats: set[str]) -> bool:
    trigger = rule.get("trigger")
    if not isinstance(trigger, Mapping):
        return False
    trigger_domain = str(trigger.get("domain") or trigger.get("consumer") or "").casefold()
    trigger_format = str(trigger.get("format_family") or "").casefold()
    return (not trigger_domain or trigger_domain in domains) and (not trigger_format or trigger_format in formats)


def route_project(
    project: Mapping[str, Any], *,
    rules: Iterable[Mapping[str, Any]] = (),
    min_score: int = 6,
    min_margin: int = 2,
) -> dict[str, Any]:
    """Return a route decision or an explicit abstention packet."""
    if project.get("schema") != SCHEMA:
        return _abstain("bad_project_ir_schema", project)
    state = str(project.get("state") or "unknown")
    if state not in PROJECT_STATES:
        return _abstain("bad_project_state", project)
    domains = _domain_values(project)
    formats = _format_values(project)
    candidates: list[dict[str, Any]] = []
    promoted = _promoted_rules(rules)
    for contract in TOOL_CATALOG:
        format_match = bool("all" in contract.formats or formats & set(contract.formats))
        domain_match = bool(not domains or domains & set(contract.domains))
        score = (4 if format_match else 0) + (3 if domain_match else 0)
        reasons = []
        if format_match:
            reasons.append("format_match")
        if domain_match:
            reasons.append("domain_match")
        for rule in promoted:
            if _rule_matches(rule, domains, formats) and str(rule.get("action", {}).get("tool") or "") == contract.tool_id:
                score += 3
                reasons.append("promoted_rule:" + str(rule.get("rule_id") or "unknown"))
        candidates.append({
            "tool_id": contract.tool_id,
            "path": contract.path,
            "purpose": contract.purpose,
            "mode": contract.mode,
            "output": contract.output,
            "score": score,
            "reasons": reasons,
        })
    candidates.sort(key=lambda item: (-item["score"], item["tool_id"]))
    top = candidates[0]
    second_score = candidates[1]["score"] if len(candidates) > 1 else -1
    if state in {"unknown", "review_required", "quarantined", "contradicted"}:
        return _abstain("project_state_requires_evidence", project, candidates)
    if not top["reasons"] or top["score"] < min_score:
        return _abstain("no_declared_consumer", project, candidates)
    if top["score"] - second_score < min_margin:
        return _abstain("route_ambiguous", project, candidates)
    return {
        "schema": ROUTER_SCHEMA,
        "project_id": project.get("project_id", ""),
        "decision": "select",
        "selected": top,
        "candidates": candidates,
        "reason": ";".join(top["reasons"]),
        "next_action": "execute_read_only" if top["mode"] == "read_only" else "prepare_plan_review",
        "abstention": False,
    }


def _abstain(reason: str, project: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    return {
        "schema": ROUTER_SCHEMA,
        "project_id": project.get("project_id", ""),
        "decision": "abstain",
        "selected": None,
        "candidates": list(candidates),
        "reason": reason,
        "next_action": "review_evidence" if reason != "no_declared_consumer" else "research_consumer",
        "abstention": True,
    }


def evaluate_route(decision: Mapping[str, Any], outcome: Mapping[str, Any]) -> dict[str, Any]:
    """Turn an execution result into a small episode outcome classification."""
    if decision.get("schema") != ROUTER_SCHEMA:
        return {"status": "rejected", "reason": "bad_router_schema"}
    if decision.get("decision") == "abstain":
        return {"status": "abstained", "reason": decision.get("reason", "unknown")}
    status = str(outcome.get("status") or "").casefold()
    validation = str(outcome.get("validation") or "").casefold()
    if status in {"ok", "success", "succeeded"} and validation in {"ok", "passed", "verified"}:
        return {"status": "succeeded", "reason": "validated_consumer_result"}
    if status in {"failed", "error"}:
        return {"status": "failed", "reason": "consumer_failed"}
    return {"status": "needs_evidence", "reason": "outcome_not_validated"}


def serialize_decision(decision: Mapping[str, Any]) -> str:
    return stable_json(decision)
