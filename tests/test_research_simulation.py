"""Tests for the bounded, model-labelled Research 4 simulation consumer."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from flujo.knowledge.project_ir import build_project_ir
from flujo.knowledge.project_router import route_project
from flujo.knowledge.research_simulation import simulate_manifest


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict[str, object]:
    return {
        "schema": "mak-research-simulation-manifest-v1",
        "simulation_id": "fixture-lsystem",
        "project_id": "garden-fixture",
        "domain": "visual_growth_grammar",
        "axiom": "A",
        "rules": {"A": "AB", "B": "A"},
        "iterations": 4,
        "max_symbols": 100,
        "claim_scope": "visual_grammar",
        "environment": {"projection": "symbolic_2d"},
        "provenance": {"evidence_refs": ["fixture/source.json"]},
    }


def test_simulation_is_deterministic_and_marked_as_model(tmp_path: Path) -> None:
    manifest = _manifest()
    schema = json.loads((ROOT / "schemas/knowledge/research_simulation_manifest.schema.json").read_text())
    Draft202012Validator(schema).validate(manifest)
    result = simulate_manifest(manifest)
    assert result["decision"] == "simulated"
    assert result["model_not_reality"] is True
    assert result["observed_or_simulated"] == "simulated"
    assert [row["state"] for row in result["trajectory"]] == ["A", "AB", "ABA", "ABAAB", "ABAABABA"]


def test_symbol_budget_abstains_without_truncating_as_success() -> None:
    manifest = _manifest()
    manifest["max_symbols"] = 2
    result = simulate_manifest(manifest)
    assert result["decision"] == "abstain"
    assert "symbol_budget_exceeded" in result["errors"]


def test_project_ir_routes_plant_simulation_to_declared_consumer(tmp_path: Path) -> None:
    manifest_path = tmp_path / "job4_simulation_manifest.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    project = build_project_ir(
        project_id="garden-fixture",
        title="Garden simulation fixture",
        source_root=tmp_path,
        domains=("plants",),
        state="active",
        evidence=({"kind": "manifest", "status": "candidate"},),
        artifacts=({"relative_path": manifest_path.name, "format_family": "data"},),
    )
    decision = route_project(project)
    assert decision["decision"] == "select"
    assert decision["selected"]["tool_id"] == "research_simulation_consumer"
