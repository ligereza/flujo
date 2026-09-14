"""Falsification and consumer tests for the SSD project reconstruction slice."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from flujo.knowledge.project_reconstruction import (
    ROLE_LIBRARY_DEPENDENCY,
    ROLE_PROJECT_UNIT,
    ROLE_SUBPROJECT,
    UNKNOWN,
    reconstruct,
    to_payload,
    write_payload,
)
from tools.build_application_intake import select_candidates


UUID_PATH = "DREFGIRA/assets/models/waves_55443377-da0f-4033-84f6-63f3eb112270"


def make_index(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY, project_path TEXT, container_root TEXT,
            dimensionality TEXT, storage_role TEXT, asset_count INTEGER,
            bytes INTEGER, anchor_count INTEGER, strategy TEXT, confidence REAL
        );
        CREATE TABLE assets (
            asset_id TEXT PRIMARY KEY, relative_path TEXT, extension TEXT,
            media_kind TEXT, bytes INTEGER, mtime_ns INTEGER,
            full_sha256 TEXT, sample_sha256 TEXT
        );
        CREATE TABLE project_members (
            asset_id TEXT, project_id TEXT, family_id TEXT,
            member_role TEXT, is_representative INTEGER
        );
        """
    )
    projects = [
        ("root", "DREFGIRA", "DREFGIRA", "mixto", "working", 3, 300, 2, "root", 0.8),
        ("child", "DREFGIRA/SHOW", "DREFGIRA", "motion", "working", 1, 100, 1, "child", 0.6),
        ("library", UUID_PATH, "DREFGIRA", "3d", "working", 1, 50, 1, "asset", 0.5),
        ("ambiguous", "DREFGIRA/assets/scenes/scenario_uuid_55443377-da0f-4033-84f6-63f3eb112270", "DREFGIRA", "3d", "working", 2, 70, 2, "asset", 0.5),
    ]
    con.executemany("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?)", projects)
    assets = [
        ("a-root", "DREFGIRA/master.blend", ".blend", "structural", 100, 1, None, "sample-root"),
        ("a-video", "DREFGIRA/show.mp4", ".mp4", "video", 100, 2, None, "sample-video"),
        ("a-child", "DREFGIRA/SHOW/show.aep", ".aep", "structural", 100, 3, None, "sample-child"),
        ("a-library", f"{UUID_PATH}/asset.blend", ".blend", "structural", 50, 4, None, "sample-lib"),
        ("a-amb-1", "DREFGIRA/assets/scenes/scenario_uuid_55443377-da0f-4033-84f6-63f3eb112270/scene.blend", ".blend", "structural", 40, 5, None, "sample-amb"),
        ("a-amb-2", "DREFGIRA/assets/scenes/scenario_uuid_55443377-da0f-4033-84f6-63f3eb112270/notes.txt", ".txt", "other", 30, 6, None, "sample-amb-2"),
    ]
    con.executemany("INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)", assets)
    con.executemany(
        "INSERT INTO project_members VALUES (?,?,?,?,?)",
        [
            ("a-root", "root", "f-root", "representative", 1),
            ("a-video", "root", "f-video", "member", 0),
            ("a-child", "child", "f-child", "representative", 1),
            ("a-library", "library", "f-library", "representative", 1),
            ("a-amb-1", "ambiguous", "f-amb", "representative", 1),
            ("a-amb-2", "ambiguous", "f-amb", "member", 0),
        ],
    )
    con.commit()
    con.close()


def test_reconstruction_preserves_roles_and_balances_assets(tmp_path: Path) -> None:
    index = tmp_path / "index.sqlite"
    make_index(index)

    result = reconstruct(index, "DREFGIRA")
    decisions = result.decisions

    assert decisions["DREFGIRA"].role == ROLE_PROJECT_UNIT
    assert decisions["DREFGIRA/SHOW"].role == ROLE_SUBPROJECT
    assert decisions[UUID_PATH].role == ROLE_LIBRARY_DEPENDENCY
    assert decisions["DREFGIRA/assets/scenes/scenario_uuid_55443377-da0f-4033-84f6-63f3eb112270"].epistemic_status == UNKNOWN
    assert result.reconciliation == {
        "assets_in_scope": 6,
        "assigned": 6,
        "unassigned": 0,
        "balanced": True,
    }


def test_payload_is_inspectable_and_reopenable(tmp_path: Path) -> None:
    index = tmp_path / "index.sqlite"
    make_index(index)
    result = reconstruct(index, "DREFGIRA")
    paths = write_payload(result, tmp_path / "out")

    payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert payload["schema"] == "mak-project-reconstruction-v1"
    assert payload["summary"]["reconciliation"]["balanced"] is True
    assert any(unit["project_id"] == "root" for unit in payload["units"])
    assert Path(paths["html"]).read_text(encoding="utf-8").count("DREFGIRA") >= 1
    assert to_payload(result)["index_fingerprint"] == payload["index_fingerprint"]


def test_intake_consumes_units_and_excludes_dependencies(tmp_path: Path) -> None:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE intake_projects (
            run_id TEXT, project_id TEXT, title TEXT, relative_path TEXT,
            dimensionality TEXT, strategy TEXT, asset_count INTEGER,
            bytes INTEGER, confidence REAL, status TEXT, source_evidence TEXT
        );
        CREATE TABLE intake_assets (
            run_id TEXT, project_id TEXT, media_kind TEXT
        );
        CREATE TABLE mak_links (
            run_id TEXT, project_id TEXT
        );
        CREATE TABLE project_candidates (
            run_id TEXT, rank INTEGER, project_id TEXT, score REAL,
            reason TEXT, evidence_json TEXT, status TEXT
        );
        """
    )
    con.executemany(
        "INSERT INTO intake_projects VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("run", "root", "DREFGIRA", "DREFGIRA", "mixto", "root", 3, 300, .8, "candidate", "{}"),
            ("run", "library", "Waves", UUID_PATH, "3d", "asset", 1, 50, .5, "candidate", "{}"),
        ],
    )
    con.executemany(
        "INSERT INTO intake_assets VALUES (?,?,?)",
        [("run", "root", "video"), ("run", "library", "structural")],
    )
    reconstruction = {
        "decisions": {
            "DREFGIRA": {"role": "project_unit"},
            UUID_PATH: {"role": "library_dependency"},
        }
    }

    selected = select_candidates(con, "run", None, 10, reconstruction)

    assert [item["path"] for item in selected] == ["DREFGIRA"]
    assert "reconstruction:project_unit" in selected[0]["reason"]
