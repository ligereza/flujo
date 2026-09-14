from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from flujo.web import hub


pytestmark = pytest.mark.flujo


def test_project_review_queue_surface_is_read_only(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "mak_knowledge.db"
    record = {
        "title": "pending-project",
        "reconstruction": {},
        "unknowns": ["missing evidence"],
        "evidence": [],
    }
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE project_records (project_id TEXT, title TEXT, state TEXT, ir_json TEXT, updated_at TEXT)"
        )
        connection.execute(
            "INSERT INTO project_records VALUES (?, ?, ?, ?, ?)",
            ("project-1", "pending-project", "review_required", json.dumps(record), "2026-09-13"),
        )
        connection.commit()
    monkeypatch.setattr(hub, "project_learning_db", lambda: database)

    payload = hub.project_review_queue_read_only()

    assert payload["schema"] == "mak-review-queue-v1"
    assert payload["available"] is True
    assert payload["read_only"] is True
    assert payload["summary"]["pending"] == 1
    assert payload["items"][0]["project_id"] == "project-1"
    assert payload["items"][0]["unknowns"] == ["missing evidence"]
    assert payload["controls"] == {
        "database_write": False,
        "decision_write": False,
        "promotion": "none",
        "publication": False,
    }
    assert payload["provenance"]["decisions_require_external_human_actor"] is True


def test_project_review_queue_get_route_uses_contract(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "mak_knowledge.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE project_records (project_id TEXT, title TEXT, state TEXT, ir_json TEXT, updated_at TEXT)"
        )
        connection.commit()
    monkeypatch.setattr(hub, "project_learning_db", lambda: database)
    captured: dict = {}
    handler = hub.HubRequestHandler.__new__(hub.HubRequestHandler)
    handler.path = "/api/project/review-queue?pass=recognize"
    handler._send_json = lambda payload, status=200: captured.update(payload=payload, status=status)

    handler.do_GET()

    assert captured["status"] == 200
    assert captured["payload"]["schema"] == "mak-review-queue-v1"
    assert captured["payload"]["review_pass"] == "recognize"
    assert captured["payload"]["controls"]["decision_write"] is False


def test_archive_portfolio_view_is_read_only_and_binds_contracurator(
    tmp_path: Path, monkeypatch,
) -> None:
    archive_path = tmp_path / "iskvw" / "datos" / "archivo.json"
    archive_path.parent.mkdir(parents=True)
    archive_path.write_text(json.dumps({
        "version": 1,
        "fuente": "bounded-test-evidence",
        "generado": "2026-09-13T12:00:00",
        "piezas": [
            {
                "id": f"declared-{index}",
                "titulo": f"Declared {index}",
                "clase": "obra",
                "fecha": "2026",
                "resumen": "Source-declared summary.",
                "etiquetas": [],
                "peso": 1,
                "medio": {"tipo": "imagen", "src": f"assets/{index}.png"},
                "estado": "publicada",
            }
            for index in range(8)
        ],
        "vinculos": [],
    }), encoding="utf-8")
    monkeypatch.setattr(hub, "_portfolio_archive_path", lambda root: archive_path)

    payload = hub.archive_portfolio_view_read_only(tmp_path)

    assert payload["schema"] == "mak-archive-portfolio-view-v1"
    assert payload["status"] == "draft_only"
    assert payload["selection"]["selected_item_count"] == 8
    assert payload["control"]["promotion"] == "none"
    assert payload["control"]["publication"] is False
    assert payload["contracurator"]["input"]["visible_item_count"] == 8


def test_archive_portfolio_view_get_route_uses_same_origin_contract(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(hub, "archive_portfolio_view_read_only", lambda root: {
        "schema": "mak-archive-portfolio-view-v1",
        "status": "draft_only",
        "control": {"promotion": "none", "publication": False},
    })
    captured: dict = {}
    handler = hub.HubRequestHandler.__new__(hub.HubRequestHandler)
    handler.path = "/api/portfolio/archive-view"
    handler.root = tmp_path
    handler._send_json = lambda payload, status=200: captured.update(payload=payload, status=status)

    handler.do_GET()

    assert captured["status"] == 200
    assert captured["payload"]["schema"] == "mak-archive-portfolio-view-v1"


def test_portfolio_review_context_get_route_is_read_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(hub, "portfolio_review_context_read_only", lambda root, project_id: {
        "schema": "mak-portfolio-review-context-v1",
        "available": True,
        "read_only": True,
        "relation": {"status": "unbound", "selection_effect": "none"},
    })
    captured: dict = {}
    handler = hub.HubRequestHandler.__new__(hub.HubRequestHandler)
    handler.path = "/api/portfolio/review-context?project_id=project-1"
    handler.root = tmp_path
    handler._send_json = lambda payload, status=200: captured.update(payload=payload, status=status)

    handler.do_GET()

    assert captured["status"] == 200
    assert captured["payload"]["schema"] == "mak-portfolio-review-context-v1"


def test_operation_receipt_surface_is_read_only_and_scope_bound() -> None:
    payload = hub.operation_receipt_read_only()

    assert payload["schema"] == "mak-operation-receipt-v1"
    assert payload["status"] == "executed_structural_only"
    assert payload["operation"]["name"] == "expand_library_program"
    assert payload["operation"]["expanded_count"] == 16
    assert payload["control"]["database_write"] is False
    assert payload["control"]["decision_write"] is False
    assert payload["control"]["promotion"] == "none"
    assert payload["control"]["publication"] is False


def test_vizz_measurement_status_surface_preserves_unknown_and_controls() -> None:
    payload = hub.vizz_measurement_status_read_only()

    assert payload["schema"] == "mak-vizz-measurement-status-v1"
    assert payload["status"] == "unknown_measurement_refused"
    assert payload["measurement"]["unknown"] is True
    assert payload["measurement"]["triangulation_attempted"] is False
    assert payload["measurement"]["depth_result_present"] is False
    assert payload["control"]["selection_effect"] == "none"
    assert payload["control"]["promotion"] == "none"
    assert payload["control"]["publication"] is False


def test_vizz_lineage_status_surface_keeps_current_state_and_revision_context() -> None:
    payload = hub.vizz_lineage_status_read_only()

    assert payload["schema"] == "mak-vizz-lineage-status-v1"
    assert payload["status"] == "revision_context_only"
    assert payload["current"]["status"] == "unknown_measurement_refused"
    assert payload["revision"]["status"] == "revision_accepted"
    assert payload["revision"]["previous_artifact_sha256"] == payload["current"]["sha256"]
    assert payload["revision"]["current_artifact_sha256"] != payload["current"]["sha256"]
    assert payload["control"]["current_state_replaced"] is False
    assert payload["control"]["selection_effect"] == "none"
    assert payload["control"]["promotion"] == "none"
    assert payload["control"]["publication"] is False


def test_structural_delta_status_surface_preserves_revision_only_boundary() -> None:
    payload = hub.structural_delta_status_read_only()

    assert payload["schema"] == "mak-structural-delta-status-v1"
    assert payload["status"] == "revision_only_delta"
    assert payload["delta"]["evaluated_keys"] == 17
    assert payload["delta"]["shared_keys"] == 2
    assert payload["delta"]["residue_keys"] == 15
    assert payload["control"]["learning_demonstrated"] is False
    assert payload["control"]["selection_effect"] == "none"
    assert payload["control"]["promotion"] == "none"
    assert payload["control"]["publication"] is False
