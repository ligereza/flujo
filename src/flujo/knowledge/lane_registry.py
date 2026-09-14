"""Read-only loader and summary for MAK's cross-domain lane registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "mak-cross-domain-lane-registry-v1"
STATES = {"implemented", "partial", "proposal", "catalog_only", "blocked"}
SOURCE_STATUSES = {"verified", "provided_bundle", "partial", "proposal", "unavailable"}
EPISTEMIC_STATUSES = {"observed", "candidate", "derived", "predicted", "counterfactual", "unknown"}


class LaneRegistryError(ValueError):
    """Invalid or unreadable lane registry."""


def load_registry(path: str | Path) -> dict[str, Any]:
    file = Path(path).expanduser()
    try:
        value = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LaneRegistryError(f"registry_unreadable: {file}") from exc
    if not isinstance(value, dict):
        raise LaneRegistryError("registry_not_object")
    return value


def validate_registry(registry: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("schema") != SCHEMA:
        errors.append("bad_schema")
    if str(registry.get("layer") or "") != "cultural_research_first":
        errors.append("bad_first_layer")
    policy = registry.get("policy")
    if not isinstance(policy, Mapping):
        errors.append("missing_policy")
    else:
        for key in ("shared_infrastructure", "semantic_transfer_rule", "promotion_rule"):
            if not policy.get(key):
                errors.append("policy_missing_" + key)
    lanes = registry.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        errors.append("lanes_missing_or_empty")
        lanes = []
    seen: set[str] = set()
    for index, lane in enumerate(lanes):
        prefix = f"lanes[{index}]"
        if not isinstance(lane, Mapping):
            errors.append(prefix + "_not_object")
            continue
        lane_id = str(lane.get("lane_id") or "")
        if not lane_id or lane_id in seen:
            errors.append(prefix + "_bad_or_duplicate_id")
        seen.add(lane_id)
        for key in ("title", "next_gate"):
            if not str(lane.get(key) or "").strip():
                errors.append(prefix + "_missing_" + key)
        if not isinstance(lane.get("dialects"), list) or not lane.get("dialects"):
            errors.append(prefix + "_dialects_missing")
        if str(lane.get("epistemic_status") or "") not in EPISTEMIC_STATUSES:
            errors.append(prefix + "_bad_epistemic_status")
        if str(lane.get("source_status") or "") not in SOURCE_STATUSES:
            errors.append(prefix + "_bad_source_status")
        if str(lane.get("current_state") or "") not in STATES:
            errors.append(prefix + "_bad_current_state")
        if not isinstance(lane.get("evidence_refs"), list) or not lane.get("evidence_refs"):
            errors.append(prefix + "_evidence_refs_missing")
        if not isinstance(lane.get("guardrails"), list) or not lane.get("guardrails"):
            errors.append(prefix + "_guardrails_missing")
        if lane.get("current_state") == "implemented" and not isinstance(lane.get("consumer"), Mapping):
            errors.append(prefix + "_implemented_without_consumer")
    provenance = registry.get("provenance")
    if not isinstance(provenance, Mapping) or not provenance.get("source_refs") or not provenance.get("producer"):
        errors.append("bad_provenance")
    return errors


def summary(registry: Mapping[str, Any]) -> dict[str, Any]:
    rows = [lane for lane in registry.get("lanes", []) if isinstance(lane, Mapping)]
    return {
        "schema": SCHEMA,
        "registry_id": registry.get("registry_id", ""),
        "layer": registry.get("layer", ""),
        "lane_count": len(rows),
        "states": {state: sum(1 for lane in rows if lane.get("current_state") == state) for state in sorted(STATES)},
        "priorities": {str(priority): sum(1 for lane in rows if lane.get("priority") == priority) for priority in range(4)},
        "lanes": [
            {
                "lane_id": lane.get("lane_id", ""),
                "priority": lane.get("priority"),
                "state": lane.get("current_state", ""),
                "next_gate": lane.get("next_gate", ""),
                "consumer": (lane.get("consumer") or {}).get("tool_id") if isinstance(lane.get("consumer"), Mapping) else None,
            }
            for lane in sorted(rows, key=lambda item: (int(item.get("priority", 9)), str(item.get("lane_id", ""))))
        ],
    }
