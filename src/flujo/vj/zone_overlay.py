"""Read-only validation and projection for the XIO/VJ zone graph.

This module does not discover devices, open ports, send cues, or mutate a
Plano/Rider layout. It validates a declarative graph and returns a separate
proposal overlay so physical zones are not confused with RD service zones.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

CONTRACT = "mak-vj-zone-overlay-v1"
_TECH_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_ALLOWED_DIRECTIONS = {"observe", "proposal_only", "active_control"}


def _records(value: Any, key: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{key}_must_be_list")
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            errors.append(f"{key}[{index}]_must_be_object")
            continue
        records.append(dict(item))
    return records


def _check_id(value: Any, kind: str, index: int, errors: list[str]) -> str:
    if not isinstance(value, str) or not _TECH_ID.fullmatch(value):
        errors.append(f"{kind}[{index}]_invalid_ascii_id")
        return ""
    return value


def validate_zone_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Validate graph invariants without activating or rewriting the graph."""
    if not isinstance(graph, Mapping):
        return {
            "schema": CONTRACT, "valid": False, "proposal_only": True,
            "read_only": True, "errors": ["graph_must_be_object"], "warnings": [],
            "summary": {"zones": 0, "nodes": 0, "links": 0,
                        "defaultActiveWriterGroups": {}},
        }

    errors: list[str] = []
    warnings: list[str] = []
    zones = _records(graph.get("zones"), "zones", errors)
    nodes = _records(graph.get("nodes"), "nodes", errors)
    links = _records(graph.get("links"), "links", errors)
    policies = graph.get("policies") if isinstance(graph.get("policies"), Mapping) else {}

    zone_ids: set[str] = set()
    for index, zone in enumerate(zones):
        zone_id = _check_id(zone.get("zone_id"), "zones", index, errors)
        if zone_id and zone_id in zone_ids:
            errors.append(f"zones[{index}]_duplicate_id:{zone_id}")
        if zone_id:
            zone_ids.add(zone_id)

    node_ids: set[str] = set()
    node_by_id: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        node_id = _check_id(node.get("node_id"), "nodes", index, errors)
        if node_id and node_id in node_ids:
            errors.append(f"nodes[{index}]_duplicate_id:{node_id}")
        if node_id:
            node_ids.add(node_id)
            node_by_id[node_id] = node
        zone_id = node.get("zone_id")
        if not isinstance(zone_id, str) or zone_id not in zone_ids:
            errors.append(f"nodes[{index}]_unknown_zone:{zone_id}")

    link_ids: set[str] = set()
    for index, link in enumerate(links):
        link_id = _check_id(link.get("link_id"), "links", index, errors)
        if link_id and link_id in link_ids:
            errors.append(f"links[{index}]_duplicate_id:{link_id}")
        if link_id:
            link_ids.add(link_id)
        source = link.get("from")
        target = link.get("to")
        if source not in node_ids:
            errors.append(f"links[{index}]_unknown_from:{source}")
        if target not in node_ids:
            errors.append(f"links[{index}]_unknown_to:{target}")
        direction = link.get("direction")
        if direction not in _ALLOWED_DIRECTIONS:
            errors.append(f"links[{index}]_invalid_direction:{direction}")
        if source in node_by_id and node_by_id[source].get("role") == "foh_monitor":
            if direction == "active_control":
                errors.append(f"links[{index}]_foh_monitor_cannot_control:{source}")
            elif direction not in {"observe", "proposal_only"}:
                warnings.append(f"links[{index}]_foh_monitor_unclassified_direction:{source}")

    writers: dict[str, list[str]] = {}
    for node in nodes:
        if not node.get("active_writer") or node.get("enabled_by_default", True) is False:
            continue
        groups = node.get("writer_groups") or []
        if not isinstance(groups, list):
            errors.append(f"node_writer_groups_must_be_list:{node.get('node_id')}")
            continue
        for group in groups:
            if not isinstance(group, str) or not _TECH_ID.fullmatch(group):
                errors.append(f"node_invalid_writer_group:{node.get('node_id')}")
                continue
            writers.setdefault(group, []).append(str(node.get("node_id")))

    for group, node_list in writers.items():
        if len(node_list) > 1:
            errors.append(f"multiple_default_writers:{group}:{','.join(node_list)}")

    for node in nodes:
        if node.get("active_writer") and node.get("enabled_by_default", True) is False:
            if node.get("writer_groups"):
                warnings.append(f"dormant_writer_requires_explicit_enable:{node.get('node_id')}")

    if policies.get("single_active_writer_per_output") is not True:
        warnings.append("single_active_writer_policy_not_explicit")
    if policies.get("foh_monitor_must_not_send") is not True:
        warnings.append("foh_monitor_policy_not_explicit")

    return {
        "schema": CONTRACT,
        "valid": not errors,
        "proposal_only": True,
        "read_only": True,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "zones": len(zones), "nodes": len(nodes), "links": len(links),
            "defaultActiveWriterGroups": writers,
        },
    }


def prepare_zone_overlay(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Return a separate reviewable overlay, preserving invalid data visibly."""
    validation = validate_zone_graph(graph)
    if not isinstance(graph, Mapping):
        zones: list[dict[str, Any]] = []
        nodes: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []
    else:
        raw_zones = graph.get("zones")
        raw_nodes = graph.get("nodes")
        raw_links = graph.get("links")
        zones = [dict(item) for item in raw_zones
                 if isinstance(item, Mapping)] if isinstance(raw_zones, list) else []
        nodes = [dict(item) for item in raw_nodes
                 if isinstance(item, Mapping)] if isinstance(raw_nodes, list) else []
        links = [dict(item) for item in raw_links
                 if isinstance(item, Mapping)] if isinstance(raw_links, list) else []
    return {
        "schema": CONTRACT,
        "proposal_only": True,
        "read_only": True,
        "valid": validation["valid"],
        "validation": validation,
        "zones": zones,
        "nodes": nodes,
        "links": links,
    }


__all__ = ["CONTRACT", "prepare_zone_overlay", "validate_zone_graph"]
