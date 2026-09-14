"""Tests for the evidence-aware project context graph."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from flujo.knowledge.project_context import (
    load_context,
    link_context_to_project_ir,
    persist_context,
    read_context,
)
from flujo.knowledge.project_ir import LearningStore, build_project_ir


def _context(tmp_path: Path) -> Path:
    payload = {
        "schema": "mak-project-context-v1",
        "context_id": "fixture-context",
        "title": "Fixture context",
        "scope": "test",
        "unknowns": ["tour_scope_unknown"],
        "entities": [
            {"entity_id": "artist-a", "kind": "artist", "display_name": "Artist A", "status": "observed"},
            {"entity_id": "album-a", "kind": "album", "display_name": "Album A", "status": "observed"},
            {"entity_id": "show-a", "kind": "show", "display_name": "Show A", "status": "observed"},
        ],
        "sources": [
            {"source_id": "source-one", "source_type": "web", "independence_group": "venue", "locator": "https://venue.example", "claim": "show", "status": "observed"},
            {"source_id": "source-two", "source_type": "web", "independence_group": "ticketing", "locator": "https://ticket.example", "claim": "show", "status": "observed"},
            {"source_id": "source-three", "source_type": "web", "independence_group": "ticketing", "locator": "https://ticket-2.example", "claim": "show", "status": "observed"},
        ],
        "relations": [
            {"subject": "artist-a", "predicate": "created_album", "object": "album-a", "status": "verified", "source_ids": ["source-one", "source-two"]},
            {"subject": "show-a", "predicate": "presented_album", "object": "album-a", "status": "verified", "source_ids": ["source-one"]},
        ],
        "projects": [],
    }
    path = tmp_path / "context.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_verified_relation_requires_two_independent_source_groups(tmp_path: Path) -> None:
    context_path = _context(tmp_path)
    database = tmp_path / "knowledge.db"
    result = persist_context(database, load_context(context_path))

    assert result["relation_statuses"] == {"candidate": 1, "verified": 1}
    with sqlite3.connect(database) as con:
        rows = con.execute(
            "SELECT subject_key,status,decision_json FROM context_relations ORDER BY subject_key"
        ).fetchall()
    assert rows[0][1] == "verified"
    assert "two_independent_source_groups" in rows[0][2]
    assert rows[1][1] == "candidate"


def test_context_persistence_is_idempotent(tmp_path: Path) -> None:
    context_path = _context(tmp_path)
    payload = load_context(context_path)
    database = tmp_path / "knowledge.db"
    first = persist_context(database, payload)
    second = persist_context(database, payload)

    assert first["entity_count"] == second["entity_count"] == 3
    with sqlite3.connect(database) as con:
        counts = {
            table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("entities", "context_sources", "context_relations", "project_contexts")
        }
    assert counts == {"entities": 3, "context_sources": 3, "context_relations": 2, "project_contexts": 0}


def test_project_ir_context_link_preserves_review_gate_and_is_idempotent(tmp_path: Path) -> None:
    context_path = _context(tmp_path)
    payload = load_context(context_path)
    project = build_project_ir(
        project_id="project-demo", title="Demo", source_root=tmp_path,
        purpose="fixture", state="review_required", source_kind="fixture", source_ref="fixture",
    )
    database = tmp_path / "knowledge.db"
    store = LearningStore(database)
    store.save_project(project)
    payload["projects"] = [{
        "project_id": "project-demo", "title": "Demo", "role": "visual_project",
        "service_role": "vj_visual_project", "status": "review_required",
        "entity_ids": {"artist": "artist-a", "album": "album-a"},
    }]
    payload["source_package"] = str(context_path)

    persist_context(database, payload)
    updates = link_context_to_project_ir(database, payload)
    assert updates[0]["state_preserved"] is True
    with sqlite3.connect(database) as con:
        before = con.execute("SELECT version, state, ir_json FROM project_records WHERE project_id='project-demo'").fetchone()
    link_context_to_project_ir(database, payload)
    with sqlite3.connect(database) as con:
        after = con.execute("SELECT version, state, ir_json FROM project_records WHERE project_id='project-demo'").fetchone()
    assert before[0] == after[0]
    assert before[1] == after[1] == "review_required"
    record = json.loads(after[2])
    assert record["project_context"]["context_id"] == "fixture-context"
    assert any(item["kind"] == "project_context" for item in record["evidence"])


def test_read_context_is_filtered_and_read_only(tmp_path: Path) -> None:
    context_path = _context(tmp_path)
    database = tmp_path / "knowledge.db"
    payload = load_context(context_path)
    persist_context(database, payload)
    before = database.read_bytes()

    index = read_context(database)
    selected = read_context(database, context_id="fixture-context")

    assert index["available"] is True
    assert index["filtered"] is False
    assert index["contexts"] == [{"context_id": "fixture-context", "project_count": 0}]
    assert selected["filtered"] is True
    assert selected["contexts"][0]["relation_statuses"] == {"candidate": 1, "verified": 1}
    assert len(selected["contexts"][0]["sources"]) == 3
    assert database.read_bytes() == before
