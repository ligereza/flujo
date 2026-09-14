from __future__ import annotations

import json
from pathlib import Path

from tools.build_application_intake import build_intake, scan_project_folder
from flujo.knowledge.project_ir import LearningStore


def test_project_folder_becomes_structured_application_package(tmp_path: Path) -> None:
    source = tmp_path / "obra"
    source.mkdir()
    (source / "scene.blend").write_bytes(b"blend fixture")
    (source / "notes.txt").write_text("project evidence", encoding="utf-8")
    output = tmp_path / "intake"
    index, _root, _summary = scan_project_folder(source, output / "source_index.sqlite")

    result = build_intake(index, output, "obra", ["Fondart"], 3, mak_db=tmp_path / "missing.db",
                          source_kind="project_folder")

    assert result["applications"] == ["obra-fondart"]
    manifest = json.loads((output / "intake.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["artifacts"] == 2
    assert manifest["status"] == "draft_with_evidence_gaps"
    package = json.loads((output / "applications" / "obra-fondart.json").read_text(encoding="utf-8"))
    assert package["project"]["asset_count"] == 2
    assert package["fund"]["status"] == "candidate_unverified"
    assert (output / "applications" / "obra-fondart.html").is_file()


def test_learning_materialization_is_explicit_and_review_required(tmp_path: Path) -> None:
    source = tmp_path / "obra"
    source.mkdir()
    (source / "scene.blend").write_bytes(b"blend fixture")
    output = tmp_path / "intake"
    learning_db = tmp_path / "learning.sqlite"
    index, _root, _summary = scan_project_folder(source, output / "source_index.sqlite")
    result = build_intake(index, output, "obra", ["Fondart"], 3,
                          mak_db=tmp_path / "missing.db", source_kind="project_folder",
                          learning_db=learning_db)
    assert result["learning_materialized"][0]["state"] == "review_required"
    assert LearningStore(learning_db).summary()["projects"] == {"review_required": 1}
