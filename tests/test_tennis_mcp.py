"""Tests for the first bounded tennis lane slice."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from flujo.knowledge.project_ir import build_project_ir
from flujo.knowledge.project_router import route_project
from flujo.tennis.mcp import ingest_rows, parse_minimal, write_jsonl
from flujo.tennis.shot_events import ingest_shot_events


ROOT = Path(__file__).resolve().parents[1]
SHOT_EVENT_SCHEMA = ROOT / "schemas" / "tennis" / "shot_event.schema.json"


def test_parser_preserves_unknown_tokens_without_guessing() -> None:
    parsed = parse_minimal("4f18q#")
    assert parsed["serve_direction"] == "wide"
    assert parsed["shots"] == [{"type": "forehand", "raw": "f18", "direction": "to_receiver_forehand_side", "return_depth": "medium_deep"}]
    assert parsed["point_end"] == {"type": "forced_error", "raw": "#"}
    assert parsed["unknown_tokens"] == [{"index": 4, "raw": "q"}]


def test_ingest_links_raw_rows_to_one_source_hash(tmp_path: Path) -> None:
    source = tmp_path / "charting.csv"
    source.write_text("match_id,1st,2nd\nM1,4f18q#,5b2@\n", encoding="utf-8")
    destination = tmp_path / "events.jsonl"
    assert write_jsonl(source, destination) == 1
    row = json.loads(destination.read_text(encoding="utf-8").splitlines()[0])
    assert row["source_id"] == "SRC_MCP"
    assert row["epistemic_status"] == "ANNOTATED"
    assert row["raw"]["1st"] == "4f18q#"
    assert row["parsed"]["first_serve_sequence"]["unknown_tokens"] == [{"index": 4, "raw": "q"}]
    assert len(row["source_sha256"]) == 64
    assert list(ingest_rows(source))[0]["source_sha256"] == row["source_sha256"]


def test_shot_event_projection_is_loss_aware_and_schema_shaped(tmp_path: Path) -> None:
    source = tmp_path / "charting.csv"
    source.write_text("match_id,point_id,1st,2nd\nM1,P7,4f18q#,5b2@\n", encoding="utf-8")
    events = list(ingest_shot_events(source, project_id="tennis-fixture"))
    assert len(events) == 4
    Draft202012Validator(json.loads(SHOT_EVENT_SCHEMA.read_text(encoding="utf-8"))).validate(events[0])
    assert events[0]["match_id"] == "M1"
    assert events[0]["point_id"] == "P7"
    assert events[0]["provenance"]["project_ref"] == "project:tennis-fixture"
    assert events[1]["derived"]["uncertainty"]["unknown_tokens"] == [{"index": 4, "raw": "q"}]
    assert events[1]["provenance"]["transform_chain"] == ["mcp-minimal-v0.1->shot-event-v0.1"]


def test_project_ir_routes_tennis_data_to_the_declared_consumer(tmp_path: Path) -> None:
    project = build_project_ir(
        project_id="tennis-fixture",
        title="Tennis fixture",
        source_root=tmp_path,
        domains=("tennis",),
        state="active",
        evidence=({"kind": "source", "status": "observed"},),
        artifacts=({"relative_path": "charting.csv", "format_family": "data"},),
    )
    decision = route_project(project)
    assert decision["decision"] == "select"
    assert decision["selected"]["tool_id"] == "tennis_shot_event_consumer"
