"""Turn a router decision into a bounded, auditable consumer probe.

This layer deliberately stops before arbitrary execution.  It can say that a
consumer is selected, unavailable, plan-only or abstained, and can persist the
result as an episode.  A later authorized executor may consume the command
plan; the router itself never runs it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any, Mapping

from .project_ir import LearningStore, ProjectIRError, stable_json
from .project_router import evaluate_route
from .runtime_tools import resolve_blender


def probe_declared_consumer(
    project: Mapping[str, Any], decision: Mapping[str, Any], *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Prepare a read-only probe result without spawning a process."""
    if decision.get("decision") == "abstain":
        return {
            "status": "abstained",
            "reason": decision.get("reason", "router_abstained"),
            "command": [],
            "validation": {"status": "verified", "check": "router_state_gate"},
        }
    selected = decision.get("selected")
    if not isinstance(selected, Mapping):
        return {
            "status": "needs_evidence",
            "reason": "selected_consumer_missing",
            "command": [],
            "validation": {"status": "not_run", "check": "route_contract"},
        }
    tool_id = str(selected.get("tool_id") or "")
    if selected.get("mode") != "read_only":
        if tool_id in {"research_job_router", "research_opportunity_gate"}:
            from .project_research import build_research_plan
            plan = build_research_plan(project)
            if plan.get("decision") == "abstain":
                return {
                    "status": "abstained",
                    "reason": plan.get("reason", "research_plan_abstained"),
                    "tool_id": tool_id,
                    "command": [],
                    "plan": plan,
                    "validation": {"status": "verified", "check": "research_state_gate"},
                }
            return {
                "status": "needs_evidence",
                "reason": "research_plan_ready_no_job_created",
                "tool_id": tool_id,
                "command": [],
                "plan": plan,
                "validation": {"status": "planned", "check": "research_plan_only"},
            }
        return {
            "status": "needs_evidence",
            "reason": "consumer_is_plan_only",
            "tool_id": tool_id,
            "command": [],
            "validation": {"status": "not_run", "check": "mutating_or_plan_only_gate"},
        }
    if tool_id == "tennis_shot_event_consumer":
        source = project.get("source") if isinstance(project.get("source"), Mapping) else {}
        root = Path(str(source.get("root_ref") or ""))
        csv_path = None
        for artifact in project.get("artifacts", []) if isinstance(project.get("artifacts"), list) else []:
            if not isinstance(artifact, Mapping):
                continue
            candidate = root / str(artifact.get("relative_path") or "")
            if candidate.is_file() and candidate.suffix.casefold() == ".csv":
                csv_path = candidate
                break
        if csv_path is None:
            return {
                "status": "needs_evidence",
                "reason": "tennis_csv_source_not_available",
                "tool_id": tool_id,
                "command": [],
                "validation": {"status": "not_run", "check": "bounded_csv_source_gate"},
            }
        return {
            "status": "succeeded",
            "reason": "local_shot_event_consumer_ready",
            "tool_id": tool_id,
            "command": [sys.executable, "tools/tennis_shot_events.py", str(csv_path), "<local-jsonl-output>"],
            "validation": {"status": "ready", "check": "bounded_command_plan"},
        }
    if tool_id == "research_simulation_consumer":
        source = project.get("source") if isinstance(project.get("source"), Mapping) else {}
        root = Path(str(source.get("root_ref") or ""))
        manifest_path = None
        for artifact in project.get("artifacts", []) if isinstance(project.get("artifacts"), list) else []:
            if not isinstance(artifact, Mapping):
                continue
            candidate = root / str(artifact.get("relative_path") or "")
            if candidate.is_file() and (
                candidate.name.endswith("simulation_manifest.json")
                or "candidate" in candidate.name.casefold()
            ):
                manifest_path = candidate
                break
        if manifest_path is None:
            return {
                "status": "needs_evidence",
                "reason": "simulation_manifest_not_available",
                "tool_id": tool_id,
                "command": [],
                "validation": {"status": "not_run", "check": "declared_manifest_gate"},
            }
        return {
            "status": "succeeded",
            "reason": "bounded_simulation_consumer_ready",
            "tool_id": tool_id,
            "command": [sys.executable, "tools/research_simulation.py", str(manifest_path), "--output", "<local-simulation-result.json>"],
            "validation": {"status": "ready", "check": "bounded_command_plan"},
        }
    if tool_id == "blend_scene_audit":
        blender_path = resolve_blender(repo_root)
        artifacts = project.get("artifacts", [])
        source = project.get("source") if isinstance(project.get("source"), Mapping) else {}
        root = Path(str(source.get("root_ref") or ""))
        blend = None
        for artifact in artifacts if isinstance(artifacts, list) else []:
            if not isinstance(artifact, Mapping) or artifact.get("format_family") != "3d":
                continue
            candidate = root / str(artifact.get("relative_path") or "")
            if candidate.is_file():
                blend = candidate
                break
        if not blender_path:
            reason = "blender_not_installed"
        elif blend is None:
            reason = "blend_source_not_available"
        else:
            reason = "read_only_blender_probe_ready"
        return {
            "status": "succeeded" if reason == "read_only_blender_probe_ready" else "needs_evidence",
            "reason": reason,
            "tool_id": tool_id,
            "command": [str(blender_path), "--background", str(blend), "--python", "tools/audit_blend_scene.py"] if blender_path and blend else [],
            "validation": {"status": "planned" if reason != "read_only_blender_probe_ready" else "ready", "check": "bounded_command_plan"},
        }
    return {
        "status": "needs_evidence",
        "reason": "consumer_probe_not_implemented",
        "tool_id": tool_id,
        "command": [],
        "validation": {"status": "not_run", "check": "consumer_adapter_gate"},
    }


def record_probe(
    store: LearningStore, project: Mapping[str, Any], decision: Mapping[str, Any],
    probe: Mapping[str, Any], *, phase: str = "consumer_probe",
    episode_id: str | None = None,
    source_snapshot_hash: str = "", code_commit: str = "",
    tool_versions: Mapping[str, Any] | None = None,
) -> str:
    """Persist one probe result using the router's conservative classification."""
    project_id = str(project.get("project_id") or "").strip()
    if not project_id:
        raise ProjectIRError("probe_missing_project_id")
    evaluated = evaluate_route(
        decision,
        {"status": probe.get("status"), "validation": (probe.get("validation") or {}).get("status")},
    )
    plan = probe.get("plan") if isinstance(probe.get("plan"), Mapping) else None
    plan_fingerprint = hashlib.sha256(stable_json(plan).encode("utf-8")).hexdigest() if plan else ""
    return store.record_episode(
        project_id=project_id,
        objective="probe declared project consumer",
        phase=phase,
        action={"decision": decision, "command": list(probe.get("command") or []), "plan": plan},
        observation={"reason": probe.get("reason"), "tool_id": probe.get("tool_id"), "plan_fingerprint": plan_fingerprint},
        outcome={"status": probe.get("status"), "classification": evaluated, "plan_fingerprint": plan_fingerprint},
        validation=probe.get("validation") if isinstance(probe.get("validation"), Mapping) else {},
        status=evaluated["status"], provider="local", model="policy-router",
        episode_id=episode_id,
        source_snapshot_hash=source_snapshot_hash, code_commit=code_commit,
        tool_versions=tool_versions,
    )
