#!/usr/bin/env python3
"""Compare the local MAK and FLUJO portfolio surfaces.

This is a bounded localhost smoke check. It does not start either server,
write files, mutate the learning database, or contact a remote service. Start
the temporal FLUJO surface separately when running it:

    python scripts/verify_portfolio_surface_parity.py
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen


def _get(base_url: str, path: str) -> dict:
    url = base_url.rstrip("/") + path
    try:
        with urlopen(url, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"{url}: HTTP {response.status}")
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{url}: {type(exc).__name__}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{url}: response_not_object")
    return dict(value)


def _archive_signature(payload: Mapping) -> dict:
    return {
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "source_hash": (payload.get("source") or {}).get("input_hash"),
        "visible_item_count": (payload.get("selection") or {}).get("selected_item_count"),
        "omitted_item_count": (payload.get("reconciliation") or {}).get("omitted_piece_count"),
        "promotion": (payload.get("control") or {}).get("promotion"),
        "publication": (payload.get("control") or {}).get("publication"),
        "truth_promotions": (payload.get("reconciliation") or {}).get("truth_promotions"),
    }


def _context_signature(payload: Mapping) -> dict:
    relation = payload.get("relation") or {}
    archive = payload.get("archive") or {}
    control = payload.get("control") or {}
    return {
        "schema": payload.get("schema"),
        "relation_status": relation.get("status"),
        "typed_relation_present": relation.get("typed_relation_present"),
        "selection_effect": relation.get("selection_effect"),
        "source_hash": archive.get("source_hash"),
        "visible_item_count": archive.get("visible_item_count"),
        "omitted_item_count": archive.get("omitted_item_count"),
        "promotion": control.get("promotion"),
        "publication": control.get("publication"),
    }


def _operation_receipt_signature(payload: Mapping) -> dict:
    operation = payload.get("operation") or {}
    control = payload.get("control") or {}
    return {
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "operation": operation.get("name"),
        "dialect": operation.get("dialect"),
        "expanded_count": operation.get("expanded_count"),
        "selection_effect": control.get("selection_effect"),
        "promotion": control.get("promotion"),
        "publication": control.get("publication"),
        "semantic_equivalence_authorized": control.get("semantic_equivalence_authorized"),
    }


def _direction_signature(payload: Mapping) -> dict:
    frame = payload.get("frame") or {}
    relation = (frame.get("culture_computation") or {}).get("project_relation_status")
    control = payload.get("control") or {}
    provenance = payload.get("provenance") or {}
    return {
        "schema": payload.get("schema"),
        "states": {name: (frame.get(name) or {}).get("state") for name in ("vision", "order", "culture_computation", "instrument")},
        "relation_status": relation,
        "control": {key: control.get(key) for key in ("database_write", "decision_write", "state_advance", "selection_effect", "promotion", "publication", "normalize_execution", "measurement_execution")},
        "claims": {key: provenance.get(key) for key in ("relation_inference", "semantic_claim", "semantic_equivalence", "learning_demonstrated")},
    }


def _archive_orientation_signature(payload: Mapping) -> dict:
    source = payload.get("source") or {}
    control = payload.get("control") or {}
    return {
        "schema": payload.get("schema"),
        "source_hash": source.get("input_hash"),
        "source_piece_count": source.get("source_piece_count"),
        "source_link_count": source.get("source_link_count"),
        "projected_link_count": source.get("projected_link_count"),
        "axes": [(axis.get("format_id"), axis.get("role"), axis.get("item_count"), axis.get("omitted_count")) for axis in (payload.get("axes") or [])],
        "semantic_claim": (payload.get("boundary") or {}).get("semantic_claim"),
        "control": {key: control.get(key) for key in ("database_write", "decision_write", "state_advance", "selection_effect", "promotion", "publication")},
    }


def _relation_plan_signature(payload: Mapping) -> dict:
    relation = payload.get("relation") or {}
    project = payload.get("project") or {}
    provenance = payload.get("provenance") or {}
    control = payload.get("control") or {}
    return {
        "schema": payload.get("schema"),
        "project_id": project.get("project_id"),
        "unknown_count": project.get("unknown_count"),
        "observed_evidence_count": project.get("observed_evidence_count"),
        "unresolved_count": payload.get("unresolved_count"),
        "relation": {key: relation.get(key) for key in ("status", "typed_relation_present", "selection_effect", "evidence_refs")},
        "provenance": {key: provenance.get(key) for key in ("relation_inference", "path_or_name_matching", "semantic_claim", "learning_demonstrated")},
        "control": {key: control.get(key) for key in ("database_write", "decision_write", "state_advance", "selection_effect", "promotion", "publication")},
    }


def _work_packet_signature(payload: Mapping) -> dict:
    source = payload.get("source") or {}
    execution = payload.get("execution") or {}
    control = payload.get("control") or {}
    return {
        "schema": payload.get("schema"),
        "project_id": source.get("project_id"),
        "relation_status": source.get("relation_status"),
        "tasks": [(task.get("id"), task.get("area"), task.get("state"), task.get("execution_allowed")) for task in (payload.get("tasks") or [])],
        "execution": execution,
        "control": control,
    }


def _work_preview_signature(payload: Mapping) -> dict:
    source = payload.get("source") or {}
    task = payload.get("task") or {}
    control = payload.get("control") or {}
    return {
        "schema": payload.get("schema"),
        "preview_only": payload.get("preview_only"),
        "source": {key: source.get(key) for key in ("schema", "task_id", "project_id", "relation_status")},
        "task": {key: task.get(key) for key in ("area", "layer", "state", "human_gate", "execution_allowed")},
        "control": {key: control.get(key) for key in ("database_write", "decision_write", "state_advance", "selection_effect", "promotion", "publication", "normalize_execution", "measurement_execution")},
    }


def _area_orientation_signature(payload: Mapping) -> dict:
    boundary = payload.get("boundary") or {}
    control = payload.get("control") or {}
    return {
        "schema": payload.get("schema"),
        "areas": [(area.get("id"), area.get("observed_status"), tuple(area.get("status_basis") or []), area.get("execution_allowed"), area.get("semantic_claim")) for area in (payload.get("areas") or [])],
        "departments": [(item.get("id"), item.get("observed_status"), tuple(item.get("tool_routes") or []), item.get("read_only"), item.get("execution_allowed")) for item in (payload.get("departments") or [])],
        "boundary": {key: boundary.get(key) for key in ("status_is_operational_observation", "catalogue_is_not_semantic_knowledge", "learning_is_not_promotion", "vizz_measurement_refusal_is_preserved", "semantic_claim")},
        "control": {key: control.get(key) for key in ("database_write", "decision_write", "state_advance", "selection_effect", "promotion", "publication", "execution")},
    }


def _operations_map_signature(payload: Mapping) -> dict:
    return {
        "schema": payload.get("schema"),
        # Runtime data belongs to each checkout; parity here compares the
        # shared contract/ownership/boundary, not local row counts or refs.
        "entries": [(item.get("domain"), item.get("endpoint"), item.get("source_schema"), item.get("surface_kind"), item.get("controls"), item.get("claims")) for item in (payload.get("entries") or [])],
        "boundary": payload.get("boundary"),
        "control": payload.get("control"),
    }


def _operations_source_snapshot_signature(payload: Mapping) -> dict:
    """Keep the contract and local snapshot data separable in the report."""
    return {
        "contract": {
            "schema": payload.get("schema"),
            "algorithm_version": payload.get("algorithm_version"),
            "available": payload.get("available"),
            "read_only": payload.get("read_only"),
            "scope": payload.get("scope"),
            "source_policy": payload.get("source_policy"),
            "boundary": payload.get("boundary"),
            "control": payload.get("control"),
            "next_action": payload.get("next_action"),
        },
        "entries": [
            {
                "endpoint": item.get("endpoint"),
                "source_schema": item.get("source_schema"),
                "source_fingerprint": item.get("source_fingerprint"),
                "counts": item.get("counts"),
                "source_ref": item.get("source_ref"),
            }
            for item in (payload.get("entries") or [])
            if isinstance(item, Mapping)
        ],
    }


def _operations_source_snapshot_differences(mak: Mapping, flujo: Mapping) -> list[dict]:
    """Report observed local divergence without treating it as contract drift."""
    mak_entries = {item.get("endpoint"): item for item in mak.get("entries", []) if isinstance(item, Mapping)}
    flujo_entries = {item.get("endpoint"): item for item in flujo.get("entries", []) if isinstance(item, Mapping)}
    differences = []
    for endpoint in sorted(set(mak_entries) | set(flujo_entries)):
        left = mak_entries.get(endpoint)
        right = flujo_entries.get(endpoint)
        left_view = None if left is None else {key: left.get(key) for key in ("source_schema", "source_fingerprint", "counts", "source_ref")}
        right_view = None if right is None else {key: right.get(key) for key in ("source_schema", "source_fingerprint", "counts", "source_ref")}
        if left_view != right_view:
            differences.append({"endpoint": endpoint, "mak": left_view, "flujo": right_view})
    return differences


def _operations_source_reconciliation(mak: Mapping, flujo: Mapping) -> dict:
    """Classify divergence without selecting a canonical source or syncing it."""
    grouped: dict[str, dict] = {}
    for side, payload in (("mak", mak), ("flujo", flujo)):
        for item in payload.get("entries", []):
            if not isinstance(item, Mapping):
                continue
            source_ref = item.get("source_ref")
            group = grouped.setdefault(source_ref, {"source_ref": source_ref, "endpoints": set(), "sides": {}})
            group["endpoints"].add(item.get("endpoint"))
            group["sides"].setdefault(side, {})[item.get("endpoint")] = {
                "source_schema": item.get("source_schema"),
                "source_fingerprint": item.get("source_fingerprint"),
                "counts": item.get("counts"),
            }
    groups = []
    divergent_groups = 0
    for source_ref in sorted(grouped):
        group = grouped[source_ref]
        endpoints = sorted(group["endpoints"])
        differences = []
        for endpoint in endpoints:
            left = group["sides"].get("mak", {}).get(endpoint)
            right = group["sides"].get("flujo", {}).get(endpoint)
            if left != right:
                differences.append(endpoint)
        if differences:
            divergent_groups += 1
        groups.append({
            "source_ref": source_ref,
            "endpoints": endpoints,
            "status": "divergent_local_snapshot" if differences else "aligned_local_snapshot",
            "divergent_endpoints": differences,
        })
    return {
        "schema": "mak-operations-source-reconciliation-v1",
        "status": "review_required" if divergent_groups else "aligned",
        "source_policy": "logical_refs_only",
        "canonical_source_selected": False,
        "automatic_sync": False,
        "divergent_group_count": divergent_groups,
        "groups": groups,
        "boundary": {"count_difference_is_not_semantic_knowledge": True, "snapshot_difference_is_not_learning": True, "canonical_selection_requires_human_review": True},
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "next_action": "human_review_source_ownership_before_any_sync",
    }


def _operations_area_review(reconciliation: Mapping) -> dict:
    """Route review work to MAK areas without asserting ownership."""
    by_area: dict[str, dict] = {}
    for group in reconciliation.get("groups", []):
        if group.get("status") != "divergent_local_snapshot":
            continue
        for endpoint in group.get("divergent_endpoints", []):
            if endpoint.startswith("/api/rd/"):
                area = "rd"
            elif endpoint.startswith("/api/cultura/"):
                area = "cultura"
            elif endpoint.startswith("/api/research/"):
                area = "research"
            elif endpoint.startswith("/api/project/"):
                area = "learning"
            elif endpoint.startswith("/api/portfolio/"):
                area = "portfolio"
            else:
                area = "core"
            item = by_area.setdefault(area, {"area": area, "source_refs": set(), "endpoints": []})
            item["source_refs"].add(group.get("source_ref"))
            item["endpoints"].append(endpoint)
    areas = [{
        "area": area,
        "source_refs": sorted(item["source_refs"]),
        "divergent_endpoints": sorted(set(item["endpoints"])),
        "ownership_status": "unassigned",
        "human_review_required": True,
    } for area, item in sorted(by_area.items())]
    return {
        "schema": "mak-operations-area-review-v1",
        "status": "review_required" if areas else "no_divergence",
        "areas": areas,
        "ownership_inferred": False,
        "boundary": {"area_routing_is_not_ownership": True, "source_ref_is_not_semantic_authority": True, "review_does_not_sync": True},
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "next_action": "human_assign_source_ownership_per_area_before_any_sync",
    }


def _operations_area_evidence_plan(area_review: Mapping) -> dict:
    """Turn an area review queue into evidence requirements, never permissions."""
    areas = []
    for item in area_review.get("areas", []):
        areas.append({
            "area": item.get("area"),
            "endpoints": item.get("divergent_endpoints", []),
            "source_refs": item.get("source_refs", []),
            "evidence_status": "missing",
            "requirements": ["human_ownership_confirmation", "source_provenance_review", "reconciliation_decision_record"],
            "semantic_authority": False,
            "sync_authorized": False,
            "human_gate": "required",
        })
    return {
        "schema": "mak-operations-area-evidence-plan-v1",
        "status": "evidence_required" if areas else "no_evidence_required",
        "areas": areas,
        "evidence_is_not_authority": True,
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "next_action": "collect_human_review_evidence_without_sync_or_semantic_promotion",
    }


def _operations_area_evidence_gate(plan: Mapping) -> dict:
    """Make missing evidence an explicit fail-closed authorization gate."""
    missing = [item.get("area") for item in plan.get("areas", []) if item.get("evidence_status") != "verified"]
    blocked = bool(missing)
    return {
        "schema": "mak-operations-area-evidence-gate-v1",
        "status": "blocked" if blocked else "open",
        "blocking_areas": missing,
        "authorization": {"sync": False, "execution": False, "promotion": False, "publication": False, "semantic_claim": False, "learning_demonstrated": False},
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "boundary": {"missing_evidence_blocks_authorization": True, "gate_is_not_evidence": True},
        "next_action": "collect_and_verify_required_evidence_before_authorization" if blocked else "retain_read_only_observation",
    }


def _operations_local_closeout(result: Mapping) -> dict:
    """Summarize verified operations without upgrading them to learning."""
    gate = result.get("operations_area_evidence_gate", {})
    vizz = result.get("vizz_measurement_status", {}).get("mak", {})
    stable_contract = result.get("same_source_and_contract") is True and not result.get("mismatches")
    return {
        "schema": "mak-operations-local-closeout-v1",
        "status": "operationally_stable_learning_unproven" if stable_contract else "review_required",
        "contract_parity": result.get("parity_scopes", {}).get("contract_parity") is True,
        "snapshot_parity": result.get("parity_scopes", {}).get("snapshot_parity") is True,
        "local_data_divergence_acknowledged": result.get("parity_scopes", {}).get("snapshot_parity") is False,
        "gate_status": gate.get("status"),
        "vizz_measurement_status": vizz.get("status"),
        "semantic_icons_baseline": "preserved",
        "observed_runtime": True,
        "domain_execution_demonstrated": False,
        "learning_demonstrated": False,
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "boundary": {"operational_stability_is_not_learning": True, "snapshot_difference_is_not_semantic_knowledge": True, "vizz_measurement_refusal_is_preserved": True},
        "next_action": "continue_with_bounded_evidence_review_without_semantic_promotion",
    }


def _operations_local_closeout_integrity(result: Mapping, closeout: Mapping) -> dict:
    """Cross-check the closeout against its upstream diagnostics before release."""
    scopes = result.get("parity_scopes", {})
    gate = result.get("operations_area_evidence_gate", {})
    vizz = result.get("vizz_measurement_status", {}).get("mak", {})
    checks = {
        "contract_parity": closeout.get("contract_parity") is (scopes.get("contract_parity") is True),
        "snapshot_parity": closeout.get("snapshot_parity") is (scopes.get("snapshot_parity") is True),
        "divergence_acknowledged": closeout.get("local_data_divergence_acknowledged") is (scopes.get("snapshot_parity") is False),
        "gate": closeout.get("gate_status") == gate.get("status"),
        "vizz": closeout.get("vizz_measurement_status") == vizz.get("status"),
        "baseline": closeout.get("semantic_icons_baseline") == "preserved",
        "learning": closeout.get("learning_demonstrated") is False,
        "domain_execution": closeout.get("domain_execution_demonstrated") is False,
        "control_closed": closeout.get("control") == {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "boundary_preserved": closeout.get("boundary") == {"operational_stability_is_not_learning": True, "snapshot_difference_is_not_semantic_knowledge": True, "vizz_measurement_refusal_is_preserved": True},
    }
    return {
        "schema": "mak-operations-local-closeout-integrity-v1",
        "status": "verified" if all(checks.values()) else "invalid",
        "checks": checks,
        "read_only": True,
        "mutation_detected": False,
        "next_action": "retain_closeout_without_learning_or_authorization_upgrade",
    }


def _portfolio_vizz_context_signature(payload: Mapping) -> dict:
    """Compare the bounded Portafolio/VIZZ context, excluding volatile timestamps."""
    return {
        "schema": payload.get("schema"),
        "source": payload.get("source"),
        "measurement": payload.get("measurement"),
        "lineage": payload.get("lineage"),
        "delta": payload.get("delta"),
        "preview": payload.get("preview"),
        "boundary": payload.get("boundary"),
        "control": payload.get("control"),
    }


def _portfolio_vizz_frontier(context: Mapping) -> dict:
    """Make the Portafolio-to-VIZZ handoff explicit and fail-closed."""
    measurement = context.get("measurement", {})
    lineage = context.get("lineage", {})
    preview = context.get("preview", {})
    delta = context.get("delta", {})
    return {
        "schema": "mak-portfolio-vizz-frontier-v1",
        "status": "context_only_measurement_refused",
        "context_available": context.get("schema") == "mak-vizz-portfolio-read-only-context-v1",
        "measurement_refused": measurement.get("status") == "unknown_measurement_refused" and measurement.get("claim_allowed") is False,
        "preview_only": preview.get("preview_only") is True and preview.get("execution_allowed") is False and preview.get("task_execution") is False,
        "lineage_authorization": False,
        "structural_delta_only": delta.get("status") == "revision_only_delta" and delta.get("learning_demonstrated") is False,
        "semantic_claim": False,
        "learning_demonstrated": False,
        "semantic_icons_baseline": "preserved",
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False, "measurement_execution": False},
        "boundary": {"portfolio_context_is_not_measurement": True, "vizz_refusal_is_preserved": True, "lineage_is_not_authorization": True, "delta_is_not_learning": True},
        "next_action": "provide_physical_calibration_evidence_before_any_metric_claim",
    }


def _research_operations_context_signature(payload: Mapping) -> dict:
    """Compare Research safety boundaries while omitting local counters."""
    return {
        "schema": payload.get("schema"),
        "algorithm_version": payload.get("algorithm_version"),
        "available": payload.get("available"),
        "read_only": payload.get("read_only"),
        "recovery_verified": (payload.get("recovery") or {}).get("verified"),
        "real_execution_verified": (payload.get("real_execution") or {}).get("verified"),
        "candidate_promotions": [(payload.get("candidate_outputs") or {}).get(name, {}).get("promotion") for name in ("legacy_reports", "rescue")],
        "learning_policy_status": (payload.get("learning") or {}).get("policy_status"),
        "boundary": payload.get("boundary"),
        "control": payload.get("control"),
    }


def _cultura_research_context_signature(payload: Mapping) -> dict:
    """Compare Cultura/Research safety boundaries while omitting local counters."""
    cultura = payload.get("cultura") or {}
    offline = cultura.get("offline") or {}
    return {
        "schema": payload.get("schema"),
        "algorithm_version": payload.get("algorithm_version"),
        "available": payload.get("available"),
        "read_only": payload.get("read_only"),
        "offline": {key: offline.get(key) for key in ("offline_first", "live_scrape_requires_explicit_gate", "proposal_is_draft_until_review", "secrets_in_payload")},
        "provider_policy": cultura.get("provider_policy"),
        "boundary": payload.get("boundary"),
        "control": payload.get("control"),
    }


def _research_cultura_alignment(result: Mapping) -> dict:
    """Check the cross-area safety contract without merging their evidence."""
    research = result.get("research_operations_context", {}).get("mak", {})
    cultura = result.get("cultura_research_context", {}).get("mak", {})
    frontier = result.get("portfolio_vizz_frontier", {})
    checks = {
        "research_is_read_only": research.get("read_only") is True and research.get("control", {}).get("database_write") is False,
        "research_execution_boundary": research.get("real_execution_verified") is False and (research.get("boundary") or {}).get("job_state_is_not_execution") is True and (research.get("boundary") or {}).get("execution_is_not_learning") is True,
        "research_learning_boundary": (research.get("boundary") or {}).get("learning_demonstrated") is False and research.get("learning_policy_status") == "candidate",
        "cultura_offline_boundary": (cultura.get("offline") or {}).get("offline_first") is True and (cultura.get("offline") or {}).get("live_scrape_requires_explicit_gate") is True and (cultura.get("offline") or {}).get("proposal_is_draft_until_review") is True,
        "cultura_provider_boundary": (cultura.get("provider_policy") or {}).get("network") == "not_called" and (cultura.get("provider_policy") or {}).get("ledger_mutation") == "not_called",
        "vizz_boundary_preserved": frontier.get("measurement_refused") is True and frontier.get("semantic_claim") is False and frontier.get("learning_demonstrated") is False,
    }
    return {
        "schema": "mak-research-cultura-vizz-alignment-v1",
        "status": "aligned_fail_closed" if all(checks.values()) else "misaligned",
        "checks": checks,
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "boundary": {"areas_remain_separate": True, "operational_status_is_not_learning": True, "offline_cultura_is_not_provider_execution": True, "vizz_refusal_is_preserved": True},
        "next_action": "retain_area_boundaries_and_review_each_source_independently",
    }


def _inter_area_claim_boundary(result: Mapping) -> dict:
    """Prove that cross-area alignment does not manufacture a relation or claim."""
    review = result.get("review_context", {}).get("mak", {})
    relation = result.get("relation_evidence_plan", {}).get("mak", {})
    research = result.get("research_operations_context", {}).get("mak", {})
    cultura = result.get("cultura_research_context", {}).get("mak", {})
    frontier = result.get("portfolio_vizz_frontier", {})
    checks = {
        "review_relation_unbound": review.get("typed_relation_present") is False and review.get("selection_effect") == "none",
        "evidence_plan_relation_unbound": (relation.get("relation") or {}).get("typed_relation_present") is False and (relation.get("relation") or {}).get("selection_effect") == "none",
        "research_claims_closed": (research.get("boundary") or {}).get("semantic_claim") is False and (research.get("boundary") or {}).get("learning_demonstrated") is False,
        "cultura_claim_closed": (cultura.get("boundary") or {}).get("semantic_claim") is False,
        "vizz_claims_closed": frontier.get("semantic_claim") is False and frontier.get("learning_demonstrated") is False,
    }
    return {
        "schema": "mak-inter-area-claim-boundary-v1",
        "status": "nonfusion_confirmed" if all(checks.values()) else "claim_boundary_breach",
        "checks": checks,
        "typed_relation_present": False,
        "semantic_claim": False,
        "learning_demonstrated": False,
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "boundary": {"alignment_does_not_create_relation": True, "context_does_not_create_learning": True, "area_routing_does_not_create_authority": True},
        "next_action": "retain_unbound_relations_until_explicit_provenance_and_human_review",
    }


def _portfolio_vizz_hub_alignment(result: Mapping) -> dict:
    """Cross-check Portafolio/VIZZ limits against the Hub's live projections."""
    frontier = result.get("portfolio_vizz_frontier", {})
    vizz = result.get("vizz_measurement_status", {}).get("mak", {})
    preview = result.get("work_preview", {}).get("vizz_calibration", {}).get("mak", {})
    receipt = result.get("operation_receipt", {}).get("mak", {})
    review = result.get("review_context", {}).get("mak", {})
    checks = {
        "measurement_refusal_matches_vizz": frontier.get("measurement_refused") is True and vizz.get("status") == "unknown_measurement_refused",
        "preview_matches_hub": frontier.get("preview_only") is True and preview.get("task", {}).get("execution_allowed") is False,
        "receipt_has_no_selection": receipt.get("selection_effect") == "none" and receipt.get("promotion") == "none" and receipt.get("publication") is False,
        "review_has_no_relation_effect": review.get("typed_relation_present") is False and review.get("selection_effect") == "none" and review.get("promotion") == "none" and review.get("publication") is False,
        "frontier_claims_closed": frontier.get("semantic_claim") is False and frontier.get("learning_demonstrated") is False,
    }
    return {
        "schema": "mak-portfolio-vizz-hub-alignment-v1",
        "status": "aligned_fail_closed" if all(checks.values()) else "misaligned",
        "checks": checks,
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False, "measurement_execution": False},
        "boundary": {"alignment_is_not_semantic_authority": True, "hub_projection_is_not_measurement": True, "vizz_refusal_is_preserved": True},
        "next_action": "retain_aligned_read_only_surfaces_until_evidence_changes",
    }


def _bundle_signature(path: str) -> dict:
    content = Path(path).read_text(encoding="utf-8")
    markers = (
        "Marco de trabajo · visión / orden / cultura-computación",
        "Orientación del archivo · 4 capas",
        "Relación · plan de evidencia",
        "Paquete de trabajo · Portafolio",
        "portfolioDirectionContext",
        "portfolioWorkPreview",
        "Mapa de áreas MAK",
        "areaOrientation",
        "Índice de operaciones observables",
        "operationsReadOnlyMap",
        "VIZZ · contexto de instrumento",
        "portfolioVizzReadOnlyContext",
        "typed_relation_present",
        "execution_allowed",
    )
    return {
        "exists": True,
        "markers": {marker: marker in content for marker in markers},
        "all_markers_present": all(marker in content for marker in markers),
    }


def _unsafe_surface_names(result: Mapping) -> list[str]:
    """Return surfaces that are symmetric but violate their fail-closed contract."""
    unsafe: list[str] = []
    for side in ("mak", "flujo"):
        archive = result["archive"][side]
        if archive.get("promotion") != "none" or archive.get("publication") is not False:
            unsafe.append("archive")
        context = result["review_context"][side]
        if context.get("typed_relation_present") is not False or context.get("selection_effect") != "none" or context.get("promotion") != "none" or context.get("publication") is not False:
            unsafe.append("review_context")
        receipt = result["operation_receipt"][side]
        if receipt.get("selection_effect") != "none" or receipt.get("promotion") != "none" or receipt.get("publication") is not False or receipt.get("semantic_equivalence_authorized") is not False:
            unsafe.append("operation_receipt")
        orientation = result["archive_orientation"][side]
        if orientation.get("semantic_claim") is not False or orientation.get("control", {}).get("selection_effect") != "none" or orientation.get("control", {}).get("promotion") != "none" or orientation.get("control", {}).get("publication") is not False:
            unsafe.append("archive_orientation")
        direction = result["direction_context"][side]
        if any(value is not False for value in direction.get("claims", {}).values()) or any(direction.get("control", {}).get(key) is not False for key in ("database_write", "decision_write", "state_advance", "publication", "normalize_execution", "measurement_execution")) or direction.get("control", {}).get("selection_effect") != "none" or direction.get("control", {}).get("promotion") != "none":
            unsafe.append("direction_context")
        relation = result["relation_evidence_plan"][side]
        if relation.get("relation", {}).get("typed_relation_present") is not False or relation.get("relation", {}).get("selection_effect") != "none" or any(value is not False for value in relation.get("provenance", {}).values() if isinstance(value, bool)) or relation.get("control", {}).get("publication") is not False:
            unsafe.append("relation_evidence_plan")
        packet = result["work_packet"][side]
        if packet.get("execution", {}).get("execution_allowed") is not False or packet.get("execution", {}).get("executed_task_count") != 0 or any(task[3] is not False for task in packet.get("tasks", [])):
            unsafe.append("work_packet")
        preview = result["work_preview"]["vizz_calibration"][side]
        if preview.get("preview_only") is not True or preview.get("task", {}).get("execution_allowed") is not False or preview.get("control", {}).get("selection_effect") != "context_only" or preview.get("control", {}).get("publication") is not False or preview.get("control", {}).get("measurement_execution") is not False:
            unsafe.append("work_preview")
        area_map = result["area_orientation"][side]
        if any(area[3] is not False or area[4] is not False for area in area_map.get("areas", [])) or area_map.get("boundary", {}).get("semantic_claim") is not False or area_map.get("control", {}).get("execution") is not False or area_map.get("control", {}).get("publication") is not False:
            unsafe.append("area_orientation")
        if any(item[3] is not True or item[4] is not False for item in area_map.get("departments", [])):
            unsafe.append("area_orientation")
        operations = result["operations_read_only_map"][side]
        if any(entry[4] != {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False} or entry[5].get("semantic_claim") is not False or entry[5].get("relation_inference") is not False or entry[5].get("learning_demonstrated") not in {"unknown", False} for entry in operations.get("entries", [])) or operations.get("control", {}).get("external_calls") is not False:
            unsafe.append("operations_read_only_map")
        if side == "mak":
            frontier = result.get("portfolio_vizz_frontier", {})
            if frontier.get("status") != "context_only_measurement_refused" or frontier.get("context_available") is not True or frontier.get("measurement_refused") is not True or frontier.get("preview_only") is not True or frontier.get("lineage_authorization") is not False or frontier.get("structural_delta_only") is not True or frontier.get("semantic_claim") is not False or frontier.get("learning_demonstrated") is not False:
                unsafe.append("portfolio_vizz_frontier")
            if result.get("portfolio_vizz_hub_alignment", {}).get("status") != "aligned_fail_closed":
                unsafe.append("portfolio_vizz_hub_alignment")
            if result.get("inter_area_claim_boundary", {}).get("status") != "nonfusion_confirmed":
                unsafe.append("inter_area_claim_boundary")
        measurement = result["vizz_measurement_status"][side]
        if measurement.get("status") != "unknown_measurement_refused" or measurement.get("measurement", {}).get("triangulation_attempted") is not False or measurement.get("measurement", {}).get("depth_result_present") is not False or measurement.get("control", {}).get("publication") is not False:
            unsafe.append("vizz_measurement_status")
        lineage = result["vizz_lineage_status"][side]
        if lineage.get("control", {}).get("current_state_replaced") is not False or lineage.get("control", {}).get("publication") is not False:
            unsafe.append("vizz_lineage_status")
        delta = result["structural_delta_status"][side]
        if delta.get("control", {}).get("learning_demonstrated") is not False or delta.get("control", {}).get("selection_effect") != "none" or delta.get("control", {}).get("promotion") != "none" or delta.get("control", {}).get("publication") is not False:
            unsafe.append("structural_delta_status")
    return sorted(set(unsafe))


def compare_surfaces(
    mak_url: str,
    flujo_url: str,
    project_id: str,
    mak_bundle: str = "/home/mak/context/flujo_hub.html",
    flujo_bundle: str = "/home/mak/flujo/context/flujo_hub.html",
) -> dict:
    project_path = "/api/portfolio/review-context?project_id=" + quote(project_id, safe="")
    preview_base = "/api/portfolio/work-preview?project_id=" + quote(project_id, safe="") + "&task_id="
    task_ids = ("archive_orientation", "structural_order", "practice_relation", "vizz_calibration")
    result = {
        "archive": {
            "mak": _archive_signature(_get(mak_url, "/api/portfolio/archive-view")),
            "flujo": _archive_signature(_get(flujo_url, "/api/portfolio/archive-view")),
        },
        "review_context": {
            "mak": _context_signature(_get(mak_url, project_path)),
            "flujo": _context_signature(_get(flujo_url, project_path)),
        },
        "operation_receipt": {
            "mak": _operation_receipt_signature(_get(mak_url, "/api/portfolio/operation-receipt")),
            "flujo": _operation_receipt_signature(_get(flujo_url, "/api/portfolio/operation-receipt")),
        },
        "archive_orientation": {
            "mak": _archive_orientation_signature(_get(mak_url, "/api/portfolio/archive-orientation")),
            "flujo": _archive_orientation_signature(_get(flujo_url, "/api/portfolio/archive-orientation")),
        },
        "direction_context": {
            "mak": _direction_signature(_get(mak_url, "/api/portfolio/direction-context?project_id=" + quote(project_id, safe=""))),
            "flujo": _direction_signature(_get(flujo_url, "/api/portfolio/direction-context?project_id=" + quote(project_id, safe=""))),
        },
        "relation_evidence_plan": {
            "mak": _relation_plan_signature(_get(mak_url, "/api/portfolio/relation-evidence-plan?project_id=" + quote(project_id, safe=""))),
            "flujo": _relation_plan_signature(_get(flujo_url, "/api/portfolio/relation-evidence-plan?project_id=" + quote(project_id, safe=""))),
        },
        "work_packet": {
            "mak": _work_packet_signature(_get(mak_url, "/api/portfolio/work-packet?project_id=" + quote(project_id, safe=""))),
            "flujo": _work_packet_signature(_get(flujo_url, "/api/portfolio/work-packet?project_id=" + quote(project_id, safe=""))),
        },
        "work_preview": {
            task_id: {
                "mak": _work_preview_signature(_get(mak_url, preview_base + task_id)),
                "flujo": _work_preview_signature(_get(flujo_url, preview_base + task_id)),
            }
            for task_id in task_ids
        },
        "area_orientation": {
            "mak": _area_orientation_signature(_get(mak_url, "/api/mak/area-orientation")),
            "flujo": _area_orientation_signature(_get(flujo_url, "/api/mak/area-orientation")),
        },
        "operations_read_only_map": {
            "mak": _operations_map_signature(_get(mak_url, "/api/operations/read-only-map")),
            "flujo": _operations_map_signature(_get(flujo_url, "/api/operations/read-only-map")),
        },
        "operations_source_snapshot": {
            "mak": _operations_source_snapshot_signature(_get(mak_url, "/api/operations/source-snapshot?scope=read_only")),
            "flujo": _operations_source_snapshot_signature(_get(flujo_url, "/api/operations/source-snapshot?scope=read_only")),
        },
        "portfolio_vizz_context": {
            "mak": _portfolio_vizz_context_signature(_get(mak_url, "/api/portfolio/vizz-read-only-context")),
            "flujo": _portfolio_vizz_context_signature(_get(flujo_url, "/api/portfolio/vizz-read-only-context")),
        },
        "research_operations_context": {
            "mak": _research_operations_context_signature(_get(mak_url, "/api/research/operations-read-only-context")),
            "flujo": _research_operations_context_signature(_get(flujo_url, "/api/research/operations-read-only-context")),
        },
        "cultura_research_context": {
            "mak": _cultura_research_context_signature(_get(mak_url, "/api/cultura/research-read-only-context")),
            "flujo": _cultura_research_context_signature(_get(flujo_url, "/api/cultura/research-read-only-context")),
        },
        "vizz_measurement_status": {
            "mak": _get(mak_url, "/api/portfolio/vizz-measurement-status"),
            "flujo": _get(flujo_url, "/api/portfolio/vizz-measurement-status"),
        },
        "vizz_lineage_status": {
            "mak": _get(mak_url, "/api/portfolio/vizz-lineage-status"),
            "flujo": _get(flujo_url, "/api/portfolio/vizz-lineage-status"),
        },
        "structural_delta_status": {
            "mak": _get(mak_url, "/api/portfolio/structural-delta-status"),
            "flujo": _get(flujo_url, "/api/portfolio/structural-delta-status"),
        },
        "bundle_contract_markers": {
            "mak": _bundle_signature(mak_bundle),
            "flujo": _bundle_signature(flujo_bundle),
        },
    }
    mismatches = []
    for surface, values in result.items():
        if surface == "work_preview":
            if any(task_values["mak"] != task_values["flujo"] for task_values in values.values()):
                mismatches.append(surface)
        elif surface == "bundle_contract_markers":
            if values["mak"]["markers"] != values["flujo"]["markers"] or not values["mak"]["all_markers_present"] or not values["flujo"]["all_markers_present"]:
                mismatches.append(surface)
        elif surface == "operations_source_snapshot":
            if values["mak"]["contract"] != values["flujo"]["contract"]:
                mismatches.append("operations_source_snapshot_contract")
        elif values["mak"] != values["flujo"]:
            mismatches.append(surface)
    snapshot_values = result["operations_source_snapshot"]
    result["parity_scopes"] = {
        "contract_parity": "operations_source_snapshot_contract" not in mismatches,
        "snapshot_parity": snapshot_values["mak"]["entries"] == snapshot_values["flujo"]["entries"],
        "snapshot_differences": _operations_source_snapshot_differences(snapshot_values["mak"], snapshot_values["flujo"]),
    }
    result["operations_source_reconciliation"] = _operations_source_reconciliation(snapshot_values["mak"], snapshot_values["flujo"])
    result["operations_area_review"] = _operations_area_review(result["operations_source_reconciliation"])
    result["operations_area_evidence_plan"] = _operations_area_evidence_plan(result["operations_area_review"])
    result["operations_area_evidence_gate"] = _operations_area_evidence_gate(result["operations_area_evidence_plan"])
    result["portfolio_vizz_frontier"] = _portfolio_vizz_frontier(result["portfolio_vizz_context"]["mak"])
    result["research_cultura_alignment"] = _research_cultura_alignment(result)
    result["inter_area_claim_boundary"] = _inter_area_claim_boundary(result)
    result["portfolio_vizz_hub_alignment"] = _portfolio_vizz_hub_alignment(result)
    result["same_source_and_contract"] = not mismatches
    unsafe = _unsafe_surface_names(result)
    if unsafe:
        mismatches.extend(f"unsafe:{name}" for name in unsafe if f"unsafe:{name}" not in mismatches)
        result["same_source_and_contract"] = False
    result["mismatches"] = mismatches
    result["operations_local_closeout"] = _operations_local_closeout(result)
    result["operations_local_closeout_integrity"] = _operations_local_closeout_integrity(result, result["operations_local_closeout"])
    if result["operations_local_closeout_integrity"]["status"] != "verified":
        mismatches.append("operations_local_closeout_integrity")
        result["same_source_and_contract"] = False
        result["mismatches"] = mismatches
    if mismatches:
        raise RuntimeError(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mak-url", default="http://127.0.0.1:8900")
    parser.add_argument("--flujo-url", default="http://127.0.0.1:8765")
    parser.add_argument("--project-id", default="project-5047cc3a2269b5031460")
    parser.add_argument("--mak-bundle", default="/home/mak/context/flujo_hub.html")
    parser.add_argument("--flujo-bundle", default="/home/mak/flujo/context/flujo_hub.html")
    args = parser.parse_args()
    try:
        print(json.dumps(
            compare_surfaces(
                args.mak_url,
                args.flujo_url,
                args.project_id,
                args.mak_bundle,
                args.flujo_bundle,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ))
    except RuntimeError as exc:
        print(f"portfolio surface parity failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
