from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from flujo.knowledge.pilot_run_manifest import (
    build_pilot_outputs,
    build_pilot_outputs_from_observation,
    sha256_json,
    validate_pilot_run,
)


def _opportunity() -> dict:
    source_ref = "fixture:official-call"
    evidence = [
        {
            "evidence_id": "deadline",
            "kind": "date",
            "field": "submission_deadline",
            "value": {"date": "2027-01-01"},
            "status": "supported",
            "confirmed": True,
            "locator": {
                "source_ref": source_ref,
                "page": 1,
                "section": "Deadline",
                "anchor": "",
                "quote": "Deadline 2027-01-01",
            },
            "weight": None,
            "label": "",
            "note": "",
        }
    ]
    return {
        "schema": "mak-opportunity-document-package-v1",
        "opportunity_id": "fixture-opportunity",
        "title": "Fixture opportunity",
        "source": {
            "ref": source_ref,
            "url": "https://example.test/call",
            "sha256": "a" * 64,
            "version": "fixture-1",
            "validity": {"status": "observed_local", "confirmed": False},
        },
        "requirements": [
            {
                "id": "date:deadline",
                "kind": "date",
                "field": "submission_deadline",
                "evidence_refs": ["deadline"],
            }
        ],
        "evidence": evidence,
    }


def _archive(root: Path) -> None:
    (root / "project" / "source").mkdir(parents=True)
    (root / "project" / "exports").mkdir(parents=True)
    (root / "project" / "source" / "scene.blend").write_bytes(b"native")
    (root / "project" / "exports" / "render.mp4").write_bytes(b"render")


def test_pilot_chain_is_deterministic_and_read_only(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    _archive(archive)
    before = {
        path.relative_to(archive).as_posix(): path.read_bytes()
        for path in archive.rglob("*") if path.is_file()
    }
    package = _opportunity()
    package_before = copy.deepcopy(package)
    first = build_pilot_outputs(str(archive), "fixture-archive", package)
    second = build_pilot_outputs(str(archive), "fixture-archive", package)
    assert validate_pilot_run(first) == []
    assert first == second
    assert package == package_before
    assert before == {
        path.relative_to(archive).as_posix(): path.read_bytes()
        for path in archive.rglob("*") if path.is_file()
    }
    assert first["manifest"]["controls"] == {
        "database_writes": False,
        "network_calls": False,
        "publication": False,
        "research_dispatch": False,
        "submission": False,
        "training": False,
    }


def test_manifest_hash_tamper_fails_closed(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    _archive(archive)
    result = build_pilot_outputs(str(archive), "fixture-archive", _opportunity())
    result["outputs"]["fit"]["decision"] = "tampered"
    assert any(error.startswith("output_hash_mismatch:fit") for error in validate_pilot_run(result))


def test_durable_observation_replays_without_source_access(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    _archive(archive)
    observed = build_pilot_outputs(str(archive), "fixture-archive", _opportunity())
    observation = copy.deepcopy(observed["outputs"]["observation"])
    for path in sorted(archive.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    replay = build_pilot_outputs_from_observation(observation, _opportunity())
    assert validate_pilot_run(replay) == []
    assert replay["manifest"]["inputs"]["source_rescan"] is False
    assert replay["manifest"]["inputs"]["archive_root"] is None
    assert replay["outputs"] == observed["outputs"]


def test_explicit_technical_context_survives_durable_replay(tmp_path: Path) -> None:
    from test_portfolio_dossier import _technical_context

    archive = tmp_path / "archive"
    _archive(archive)
    observed = build_pilot_outputs(str(archive), "fixture-archive", _opportunity())
    observation = copy.deepcopy(observed["outputs"]["observation"])
    context = copy.deepcopy(_technical_context())
    context["provenance"]["archive_id"] = observation["archive_id"]
    context["provenance"]["snapshot_id"] = observation["snapshot_id"]

    enriched = build_pilot_outputs_from_observation(
        observation, _opportunity(), technical_context=context
    )
    assert validate_pilot_run(enriched) == []
    assert enriched["manifest"]["inputs"]["technical_context_hash"] == sha256_json(context)
    assert enriched["outputs"]["portfolio-dossier"]["technical_context"]["relations"]
    assert enriched["outputs"]["portfolio-view"]["technical_evidence"]
    assert enriched["outputs"]["technical-context"] == context

    replay = build_pilot_outputs_from_observation(
        observation,
        _opportunity(),
        technical_context=copy.deepcopy(enriched["outputs"]["technical-context"]),
    )
    assert replay == enriched


def test_cli_materializes_explicit_technical_context(tmp_path: Path) -> None:
    from test_portfolio_dossier import _technical_context

    archive = tmp_path / "archive"
    _archive(archive)
    package = tmp_path / "opportunity.json"
    package.write_text(json.dumps(_opportunity()), encoding="utf-8")
    observed = build_pilot_outputs(str(archive), "fixture-archive", _opportunity())
    observation = tmp_path / "observation.json"
    observation.write_text(json.dumps(observed["outputs"]["observation"]), encoding="utf-8")
    context = _technical_context()
    context["provenance"]["archive_id"] = "fixture-archive"
    context["provenance"]["snapshot_id"] = observed["outputs"]["observation"]["snapshot_id"]
    context_path = tmp_path / "technical-context.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")
    output = tmp_path / "run-with-technical-context"
    command = [
        sys.executable,
        "tools/materialize_pilot_run.py",
        "--observation", str(observation),
        "--opportunity-package", str(package),
        "--technical-context", str(context_path),
        "--output-root", str(output),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["inputs"]["technical_context_hash"] == sha256_json(context)
    assert json.loads((output / "technical-context.json").read_text(encoding="utf-8")) == context
    assert json.loads((output / "portfolio-dossier.json").read_text(encoding="utf-8"))["technical_context"]["relations"]
    assert json.loads((output / "portfolio-view.json").read_text(encoding="utf-8"))["technical_evidence"]
    assert "Evidencia técnica auxiliar" in (output / "portfolio-view.md").read_text(encoding="utf-8")


def test_cli_materializes_explicit_output_only(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    _archive(archive)
    package = tmp_path / "opportunity.json"
    package.write_text(json.dumps(_opportunity()), encoding="utf-8")
    output = tmp_path / "run"
    command = [
        sys.executable,
        "tools/materialize_pilot_run.py",
        "--archive-root", str(archive),
        "--archive-id", "fixture-archive",
        "--opportunity-package", str(package),
        "--output-root", str(output),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "mak-pilot-run-manifest-v1"
    expected_files = ["manifest.json", *[row["file"] for row in manifest["outputs"]]]
    if any(row.get("name") == "portfolio-view" for row in manifest["outputs"]):
        expected_files.append("portfolio-view.md")
    assert sorted(path.name for path in output.iterdir()) == sorted(expected_files)
