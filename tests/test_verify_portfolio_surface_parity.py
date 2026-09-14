from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import verify_portfolio_surface_parity as parity  # noqa: E402


pytestmark = pytest.mark.flujo


def _responses():
    archive = {
        "schema": "mak-archive-portfolio-view-v1", "status": "draft_only",
        "source": {"input_hash": "sha256:archive"},
        "selection": {"selected_item_count": 65},
        "reconciliation": {"omitted_piece_count": 1969, "truth_promotions": 0},
        "control": {"promotion": "none", "publication": False},
    }
    context = {
        "schema": "mak-portfolio-review-context-v1",
        "archive": {"source_hash": "sha256:archive", "visible_item_count": 65, "omitted_item_count": 1969},
        "relation": {"status": "needs_evidence", "typed_relation_present": False, "selection_effect": "none"},
        "control": {"promotion": "none", "publication": False},
    }
    receipt = {
        "schema": "mak-operation-receipt-v1", "status": "executed_structural_only",
        "operation": {"name": "expand_library_program", "dialect": "super-mario-feature-v1", "expanded_count": 16},
        "control": {"selection_effect": "none", "promotion": "none", "publication": False, "semantic_equivalence_authorized": False},
    }
    orientation = {
        "schema": "mak-portfolio-archive-orientation-v1",
        "source": {"input_hash": "sha256:archive", "source_piece_count": 2034, "source_link_count": 5812, "projected_link_count": 61},
        "axes": [], "boundary": {"semantic_claim": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False},
    }
    direction = {
        "schema": "mak-portfolio-direction-context-v1",
        "frame": {name: {"state": name} for name in ("vision", "order", "culture_computation", "instrument")},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "normalize_execution": False, "measurement_execution": False},
        "provenance": {"relation_inference": False, "semantic_claim": False, "semantic_equivalence": False, "learning_demonstrated": False},
    }
    relation = {
        "schema": "mak-portfolio-relation-evidence-plan-v1",
        "project": {"project_id": "project-1", "unknown_count": 6, "observed_evidence_count": 1},
        "relation": {"status": "needs_evidence", "typed_relation_present": False, "selection_effect": "none", "evidence_refs": []},
        "unresolved_count": 6,
        "provenance": {"relation_inference": False, "path_or_name_matching": False, "semantic_claim": False, "learning_demonstrated": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False},
    }
    packet = {
        "schema": "mak-portfolio-work-packet-v1",
        "source": {"project_id": "project-1", "relation_status": "needs_evidence"},
        "tasks": [{"id": "archive_orientation", "area": "mak-hub/portfolio", "state": "bounded_observation", "execution_allowed": False}],
        "execution": {"executed_task_count": 0, "execution_allowed": False, "state_advance": False, "task_count": 4},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "normalize_execution": False, "measurement_execution": False},
    }
    preview = {
        "schema": "mak-portfolio-work-preview-v1", "preview_only": True,
        "source": {"schema": "mak-portfolio-work-packet-v1", "task_id": "vizz_calibration", "project_id": "project-1", "relation_status": "needs_evidence"},
        "task": {"area": "vizz/measurement", "layer": "instrument", "state": "vizz_measurement_refused", "human_gate": "physical_calibration_evidence", "execution_allowed": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "context_only", "promotion": "none", "publication": False, "normalize_execution": False, "measurement_execution": False},
    }
    area_orientation = {
        "schema": "mak-area-orientation-v1",
        "areas": [{"id": area_id, "observed_status": "catalogued", "status_basis": ["diagnostics_domain"], "execution_allowed": False, "semantic_claim": False} for area_id in ("core", "rd", "portfolio", "cultura", "research", "vizz", "learning")],
        "departments": [{"id": department_id, "observed_status": "ready", "tool_routes": [], "read_only": True, "execution_allowed": False} for department_id in ("rd", "cultura", "iskvw")],
        "boundary": {"status_is_operational_observation": True, "catalogue_is_not_semantic_knowledge": True, "learning_is_not_promotion": True, "vizz_measurement_refusal_is_preserved": True, "semantic_claim": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False},
    }
    operations_map = {
        "schema": "mak-operations-read-only-map-v1",
        "entries": [{"domain": "rd", "endpoint": endpoint, "source_schema": "schema", "surface_kind": "evidence", "observed_status": "observed", "counts": {}, "source_hash_or_ref": "fixture", "next_action": "review", "controls": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False}, "claims": {"semantic_claim": False, "relation_inference": False, "learning_demonstrated": "unknown"}} for endpoint in ("/api/status", "/api/portfolio/review-operations-context?item_id=18114751558928682.mp4", "/api/portfolio/review-cultura-research-context?item_id=18114751558928682.mp4", "/api/portfolio/review-operations-context?item_id=18099845974735838.mp4", "/api/portfolio/review-cultura-research-context?item_id=18099845974735838.mp4", "/api/rd/summary", "/api/rd/read-only-context", "/api/rd/topics", "/api/rd/crosswalk", "/api/rd/cultura-relations", "/api/cultura/sources", "/api/cultura/capabilities", "/api/cultura/opportunity-gate", "/api/cultura/research-read-only-context", "/api/research/catalog", "/api/research/jobs", "/api/research/operations-context?job_id=3", "/api/research/operations-read-only-context", "/api/project/learning-read-only-context", "/api/portfolio/operation-receipt", "/api/portfolio/work-packet", "/api/portfolio/archive-view", "/api/portfolio/vizz-measurement-status", "/api/portfolio/vizz-read-only-context")],
        "boundary": {"get_whitelist_only": True, "status_is_not_semantic_knowledge": True, "catalogue_is_not_evidence_of_learning": True, "vizz_parent_lane": "portfolio_instrument", "semantic_claim": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False, "external_calls": False},
    }
    source_snapshot = {
        "schema": "mak-operations-source-snapshot-v1", "algorithm_version": "operations-source-snapshot-1",
        "available": True, "read_only": True, "generated_at": "fixture", "scope": "read_only", "source_policy": "logical_refs_only",
        "entries": [],
        "boundary": {"contract_parity_is_not_snapshot_parity": True, "local_counts_may_differ": True, "semantic_claim": False, "learning_demonstrated": False},
        "control": {"read_only": True, "database_write": False, "decision_write": False, "state_advance": False, "execution": False, "external_calls": False, "promotion": "none", "publication": False},
        "next_action": "compare_contract_parity_separately_from_local_snapshot_differences",
    }
    vizz_context = {
        "schema": "mak-vizz-portfolio-read-only-context-v1",
        "source": {"measurement_schema": "mak-vizz-measurement-status-v1", "lineage_schema": "mak-vizz-lineage-status-v1", "delta_schema": "mak-structural-delta-status-v1", "preview_schema": "mak-portfolio-work-preview-v1"},
        "measurement": {"status": "unknown_measurement_refused", "calibration_status": "CALIBRATION_EVIDENCE_REQUIRED", "triangulation_attempted": False, "depth_result_present": False, "claim_allowed": False},
        "lineage": {"status": "revision_context_only", "current_status": "unknown_measurement_refused", "revision_status": "revision_accepted", "current_state_replaced": False, "current_ref": "grammar-lab:Q-650:artifact"},
        "delta": {"status": "revision_only_delta", "shared_keys": 2, "residue_keys": 15, "serialized_savings_bytes": -131, "learning_demonstrated": False},
        "preview": {"task_id": "vizz_calibration", "state": "vizz_measurement_refused", "human_gate": "physical_calibration_evidence", "project_id": "project-1", "relation_status": "needs_evidence", "preview_only": True, "execution_allowed": False, "task_execution": False},
        "boundary": {"measurement_refused": True, "calibration_required": True, "lineage_is_not_authorization": True, "delta_is_structural_only": True, "preview_is_not_execution": True, "semantic_claim": False, "learning_demonstrated": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "measurement_execution": False, "metric_depth_authorized": False, "network": False, "execution": False},
    }
    research_operations = {
        "schema": "mak-research-operations-context-v1", "algorithm_version": "research-operations-read-only-context-1", "available": True, "read_only": True,
        "recovery": {"verified": False}, "real_execution": {"verified": False},
        "candidate_outputs": {"legacy_reports": {"promotion": "none"}, "rescue": {"promotion": "none"}},
        "learning": {"policy_status": "candidate"},
        "boundary": {"job_state_is_not_execution": True, "recovery_is_not_execution": True, "execution_is_not_learning": True, "candidate_reports_are_not_knowledge": True, "provider_calls_not_allowed": True, "semantic_claim": False, "learning_demonstrated": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False, "external_calls": False},
    }
    cultura_research = {
        "schema": "mak-cultura-research-read-only-context-v1", "algorithm_version": "cultura-research-read-only-context-1", "available": True, "read_only": True,
        "cultura": {"offline": {"offline_first": True, "live_scrape_requires_explicit_gate": True, "proposal_is_draft_until_review": True, "secrets_in_payload": False}, "provider_policy": {"network": "not_called", "ledger_mutation": "not_called"}},
        "boundary": {"cultura_is_offline_first": True, "live_scrape_requires_explicit_gate": True, "proposal_is_draft_until_review": True, "research_supports_not_claim": True, "job_state_is_not_learning": True, "semantic_claim": False},
        "control": {"database_write": False, "decision_write": False, "state_advance": False, "selection_effect": "none", "promotion": "none", "publication": False, "execution": False, "network": False},
    }
    return {
        "archive": archive, "context": context, "receipt": receipt,
        "orientation": orientation, "direction": direction, "relation": relation,
        "packet": packet, "preview": preview,
        "area_orientation": area_orientation, "operations_map": operations_map, "source_snapshot": source_snapshot, "vizz_context": vizz_context, "research_operations": research_operations, "cultura_research": cultura_research,
        "vizz_measurement": {
            "schema": "mak-vizz-measurement-status-v1",
            "status": "unknown_measurement_refused",
            "measurement": {"triangulation_attempted": False, "depth_result_present": False},
            "control": {"publication": False},
        },
        "vizz_lineage": {
            "schema": "mak-vizz-lineage-status-v1",
            "control": {"current_state_replaced": False, "publication": False},
        },
        "delta": {
            "schema": "mak-structural-delta-status-v1",
            "control": {"learning_demonstrated": False, "selection_effect": "none", "promotion": "none", "publication": False},
        },
    }


def test_compare_surfaces_covers_all_new_contracts(monkeypatch):
    responses = _responses()
    requested = []

    def fake_get(base, path):
        requested.append(path)
        if "archive-view" in path:
            return responses["archive"]
        if "review-context" in path:
            return responses["context"]
        if "operation-receipt" in path:
            return responses["receipt"]
        if "archive-orientation" in path:
            return responses["orientation"]
        if "direction-context" in path:
            return responses["direction"]
        if "relation-evidence-plan" in path:
            return responses["relation"]
        if "work-packet" in path:
            return responses["packet"]
        if "work-preview" in path:
            return responses["preview"]
        if "area-orientation" in path:
            return responses["area_orientation"]
        if "operations/read-only-map" in path:
            return responses["operations_map"]
        if "operations/source-snapshot" in path:
            return responses["source_snapshot"]
        if "portfolio/vizz-read-only-context" in path:
            return responses["vizz_context"]
        if "research/operations-read-only-context" in path:
            return responses["research_operations"]
        if "cultura/research-read-only-context" in path:
            return responses["cultura_research"]
        if "vizz-measurement-status" in path:
            return responses["vizz_measurement"]
        if "vizz-lineage-status" in path:
            return responses["vizz_lineage"]
        if "structural-delta-status" in path:
            return responses["delta"]
        raise AssertionError(path)

    monkeypatch.setattr(parity, "_get", fake_get)
    monkeypatch.setattr(parity, "_bundle_signature", lambda path: {"exists": True, "markers": {"marker": True}, "all_markers_present": True})
    result = parity.compare_surfaces("mak", "flujo", "project-1", "mak.html", "flujo.html")

    assert result["same_source_and_contract"] is True
    assert result["mismatches"] == []
    assert set(result["work_preview"]) == {"archive_orientation", "structural_order", "practice_relation", "vizz_calibration"}
    assert {path.rsplit("task_id=", 1)[-1] for path in requested if "work-preview" in path} == {
        "archive_orientation", "structural_order", "practice_relation", "vizz_calibration"
    }
    assert len(result) >= 15
    assert result["parity_scopes"]["contract_parity"] is True
    assert result["parity_scopes"]["snapshot_parity"] is True
    assert result["operations_source_reconciliation"]["status"] == "aligned"
    assert result["operations_source_reconciliation"]["automatic_sync"] is False
    assert result["operations_area_review"]["status"] == "no_divergence"
    assert result["operations_area_review"]["ownership_inferred"] is False
    assert result["operations_area_evidence_plan"]["status"] == "no_evidence_required"
    assert result["operations_area_evidence_gate"]["status"] == "open"
    assert result["operations_local_closeout"]["status"] == "operationally_stable_learning_unproven"
    assert result["operations_local_closeout"]["domain_execution_demonstrated"] is False
    assert result["operations_local_closeout_integrity"]["status"] == "verified"
    assert result["portfolio_vizz_frontier"]["status"] == "context_only_measurement_refused"
    assert result["portfolio_vizz_frontier"]["measurement_refused"] is True
    assert result["research_cultura_alignment"]["status"] == "aligned_fail_closed"
    assert result["inter_area_claim_boundary"]["status"] == "nonfusion_confirmed"
    assert result["inter_area_claim_boundary"]["typed_relation_present"] is False
    assert result["portfolio_vizz_hub_alignment"]["status"] == "aligned_fail_closed"


def test_compare_surfaces_rejects_bundle_marker_drift(monkeypatch):
    responses = _responses()
    monkeypatch.setattr(parity, "_get", lambda base, path: responses["archive"] if "archive-view" in path else responses["context"] if "review-context" in path else responses["receipt"] if "operation-receipt" in path else responses["orientation"] if "archive-orientation" in path else responses["direction"] if "direction-context" in path else responses["relation"] if "relation-evidence-plan" in path else responses["packet"] if "work-packet" in path else responses["preview"] if "work-preview" in path else responses["area_orientation"] if "area-orientation" in path else responses["operations_map"] if "operations/read-only-map" in path else responses["source_snapshot"] if "operations/source-snapshot" in path else responses["vizz_context"] if "portfolio/vizz-read-only-context" in path else responses["vizz_measurement"] if "vizz-measurement-status" in path else responses["vizz_lineage"] if "vizz-lineage-status" in path else responses["delta"])
    monkeypatch.setattr(parity, "_bundle_signature", lambda path: {"exists": True, "markers": {"marker": path == "mak.html"}, "all_markers_present": path == "mak.html"})

    with pytest.raises(RuntimeError, match="bundle_contract_markers"):
        parity.compare_surfaces("mak", "flujo", "project-1", "mak.html", "flujo.html")


def test_bundle_signature_exercises_each_marker(tmp_path):
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
    path = tmp_path / "bundle.html"
    path.write_text("\n".join(markers), encoding="utf-8")
    assert parity._bundle_signature(str(path))["all_markers_present"] is True
    for marker in markers:
        path.write_text("\n".join(value for value in markers if value != marker), encoding="utf-8")
        assert parity._bundle_signature(str(path))["all_markers_present"] is False


def test_compare_surfaces_rejects_symmetric_unsafe_measurement(monkeypatch):
    responses = _responses()
    responses["vizz_measurement"]["status"] = "unknown_measurement_refused"
    responses["vizz_measurement"]["measurement"] = {"triangulation_attempted": True, "depth_result_present": False}
    responses["vizz_measurement"]["control"] = {"publication": True}
    monkeypatch.setattr(parity, "_get", lambda base, path: responses["archive"] if "archive-view" in path else responses["context"] if "review-context" in path else responses["receipt"] if "operation-receipt" in path else responses["orientation"] if "archive-orientation" in path else responses["direction"] if "direction-context" in path else responses["relation"] if "relation-evidence-plan" in path else responses["packet"] if "work-packet" in path else responses["preview"] if "work-preview" in path else responses["area_orientation"] if "area-orientation" in path else responses["operations_map"] if "operations/read-only-map" in path else responses["source_snapshot"] if "operations/source-snapshot" in path else responses["vizz_context"] if "portfolio/vizz-read-only-context" in path else responses["vizz_measurement"] if "vizz-measurement-status" in path else responses["vizz_lineage"] if "vizz-lineage-status" in path else responses["delta"])
    monkeypatch.setattr(parity, "_bundle_signature", lambda path: {"exists": True, "markers": {"marker": True}, "all_markers_present": True})

    with pytest.raises(RuntimeError, match="unsafe:vizz_measurement_status"):
        parity.compare_surfaces("mak", "flujo", "project-1", "mak.html", "flujo.html")


def test_source_reconciliation_requires_review_without_sync():
    mak = {"entries": [{"endpoint": "/api/rd/topics", "source_ref": "data/rd.db", "source_schema": "schema", "source_fingerprint": "mak", "counts": {"rows": 1}}]}
    flujo = {"entries": [{"endpoint": "/api/rd/topics", "source_ref": "data/rd.db", "source_schema": "schema", "source_fingerprint": "flujo", "counts": {"rows": 2}}]}

    result = parity._operations_source_reconciliation(mak, flujo)

    assert result["status"] == "review_required"
    assert result["canonical_source_selected"] is False
    assert result["automatic_sync"] is False
    assert result["groups"][0]["status"] == "divergent_local_snapshot"


def test_area_review_routes_divergence_without_assigning_ownership():
    reconciliation = {
        "groups": [{"source_ref": "data/rd.db", "status": "divergent_local_snapshot", "divergent_endpoints": ["/api/rd/topics"]}]
    }

    result = parity._operations_area_review(reconciliation)

    assert result["status"] == "review_required"
    assert result["ownership_inferred"] is False
    assert result["areas"] == [{"area": "rd", "source_refs": ["data/rd.db"], "divergent_endpoints": ["/api/rd/topics"], "ownership_status": "unassigned", "human_review_required": True}]


def test_area_evidence_plan_requires_human_evidence_without_sync():
    result = parity._operations_area_evidence_plan({"areas": [{"area": "rd", "source_refs": ["data/rd.db"], "divergent_endpoints": ["/api/rd/topics"]}]})

    assert result["schema"] == "mak-operations-area-evidence-plan-v1"
    assert result["status"] == "evidence_required"
    assert result["areas"][0]["evidence_status"] == "missing"
    assert result["areas"][0]["sync_authorized"] is False
    assert result["areas"][0]["human_gate"] == "required"


def test_missing_area_evidence_closes_authorization_gate():
    result = parity._operations_area_evidence_gate({"areas": [{"area": "cultura", "evidence_status": "missing"}]})

    assert result["status"] == "blocked"
    assert result["blocking_areas"] == ["cultura"]
    assert result["authorization"] == {"sync": False, "execution": False, "promotion": False, "publication": False, "semantic_claim": False, "learning_demonstrated": False}


def test_local_closeout_preserves_vizz_refusal_and_baseline():
    result = parity._operations_local_closeout({
        "same_source_and_contract": True,
        "mismatches": [],
        "parity_scopes": {"contract_parity": True, "snapshot_parity": False},
        "operations_area_evidence_gate": {"status": "blocked"},
        "vizz_measurement_status": {"mak": {"status": "unknown_measurement_refused"}},
    })

    assert result["status"] == "operationally_stable_learning_unproven"
    assert result["semantic_icons_baseline"] == "preserved"
    assert result["vizz_measurement_status"] == "unknown_measurement_refused"
    assert result["learning_demonstrated"] is False
    assert result["control"]["execution"] is False


def test_closeout_integrity_rejects_tampered_learning_claim():
    base = {
        "same_source_and_contract": True,
        "mismatches": [],
        "parity_scopes": {"contract_parity": True, "snapshot_parity": False},
        "operations_area_evidence_gate": {"status": "blocked"},
        "vizz_measurement_status": {"mak": {"status": "unknown_measurement_refused"}},
    }
    closeout = parity._operations_local_closeout(base)
    closeout["learning_demonstrated"] = True

    result = parity._operations_local_closeout_integrity(base, closeout)

    assert result["status"] == "invalid"
    assert result["checks"]["learning"] is False
