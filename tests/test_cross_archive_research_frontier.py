from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.cross_archive_relations import compile_cross_archive_relations
from flujo.knowledge.cross_archive_research_frontier import (
    SCHEMA,
    CrossArchiveResearchFrontierError,
    compile_cross_archive_research_frontier,
    validate_cross_archive_research_frontier,
)
from flujo.knowledge.research_evidence_triangulation import triangulate_research_evidence


ROOT = Path(__file__).resolve().parents[1]
RELATIONS = ROOT / "experiments/pilots/DREFQUILA/runs/cross-archive-escarlata-20260826/relations.json"


def _payload() -> dict:
    if not RELATIONS.is_file():
        pytest.skip("experiments/pilots/DREFQUILA is not in this clone")
    return json.loads(RELATIONS.read_text(encoding="utf-8"))


def test_real_escarlata_frontier_is_one_grouped_non_dispatched_job():
    relations = _payload()
    frontier = compile_cross_archive_research_frontier(relations)
    assert frontier["schema"] == SCHEMA
    assert len(frontier["jobs"]) == 1
    job = frontier["jobs"][0]
    assert job["requirement_ids"] == ["relation-binding:catalog-track:b1f1a69c33797bd851e92d872cb8eb35"]
    assert len(job["provenance"]["relation_ids"]) == 6
    assert job["dispatch"] is False
    assert job["status"] == "planned_not_dispatched"
    assert job["domain"] == "curatoria"
    assert frontier["provenance"]["opportunity_id_is_namespace_only"] is True
    assert frontier["reconciliation"] == {
        "relation_count": 6,
        "relation_ids_unique": True,
        "relations_with_jobs": 6,
        "relations_without_jobs": 0,
        "job_count": 1,
        "job_ids_unique": True,
        "dispatch_count": 0,
        "truth_promotions": 0,
        "deterministic_order": True,
        "relation_loss": 0,
    }
    assert validate_cross_archive_research_frontier(frontier, relations)


def test_existing_triangulator_returns_unresolved_not_empty():
    frontier = compile_cross_archive_research_frontier(_payload())
    report = triangulate_research_evidence(frontier, [])
    assert len(report["results"]) == 1
    assert report["results"][0]["status"] == "unresolved"
    assert report["results"][0]["requirement_id"].startswith("relation-binding:")
    assert report["results"][0]["gaps"] == ["result_missing"]


def test_reorder_is_byte_deterministic_and_no_input_mutation():
    relations = _payload()
    before = copy.deepcopy(relations)
    first = compile_cross_archive_research_frontier(relations)
    altered = copy.deepcopy(relations)
    altered["relations"] = list(reversed(altered["relations"]))
    second = compile_cross_archive_research_frontier(altered)
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(second, ensure_ascii=False, sort_keys=True)
    assert relations == before


def test_relation_without_missing_evidence_is_explicitly_abstained():
    relations = _payload()
    relations["relations"][0]["missing_evidence"] = []
    relations["relations"][0]["next_probe"] = ""
    frontier = compile_cross_archive_research_frontier(relations)
    assert len(frontier["jobs"]) == 1
    assert frontier["reconciliation"]["relations_without_jobs"] == 1
    assert frontier["abstentions"] == [{
        "relation_id": relations["relations"][0]["relation_id"],
        "reason": "no_missing_evidence_declared",
    }]


def test_invalid_endpoint_or_missing_probe_fails_closed():
    relations = _payload()
    relations["relations"][0]["target_archive_id"] = "other"
    with pytest.raises(CrossArchiveResearchFrontierError):
        compile_cross_archive_research_frontier(relations)
    relations = _payload()
    relations["relations"][0]["next_probe"] = ""
    with pytest.raises(CrossArchiveResearchFrontierError):
        compile_cross_archive_research_frontier(relations)


def test_tampered_frontier_and_duplicate_archive_fail_validation():
    relations = _payload()
    frontier = compile_cross_archive_research_frontier(relations)
    tampered = copy.deepcopy(frontier)
    tampered["jobs"][0]["dispatch"] = True
    assert not validate_cross_archive_research_frontier(tampered, relations)
    duplicate = copy.deepcopy(relations)
    duplicate["archives"].append(copy.deepcopy(duplicate["archives"][0]))
    with pytest.raises(CrossArchiveResearchFrontierError):
        compile_cross_archive_research_frontier(duplicate)


def test_cli_materializes_frontier_without_db_or_dispatch(tmp_path: Path):
    # This one builds the command from RELATIONS directly instead of going
    # through the guarded loader, so guarding the loader did not cover it.
    if not RELATIONS.is_file():
        pytest.skip("experiments/pilots/DREFQUILA is not in this clone")
    output = tmp_path / "research-frontier.json"
    command = [
        sys.executable,  # not `.venv/bin/python`: that file does not exist in CI
        str(ROOT / "tools/compile_cross_archive_research_frontier.py"),
        "--relations", str(RELATIONS),
        "--output", str(output),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == SCHEMA
    assert payload["reconciliation"]["dispatch_count"] == 0
