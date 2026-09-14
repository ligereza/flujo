"""Tests for src/flujo/export/zipper.py -- export_flyer() delivery zip (client artifact).

Uses a minimal tmp job dir (no real workspace touched). Only export_flyer() is
public API here; the rest of the module is private helpers used internally.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from flujo.export.zipper import export_flyer


def _make_project(tmp_path: Path, name: str = "proj1", with_manifest: bool = True) -> Path:
    proj = tmp_path / name
    proj.mkdir(parents=True, exist_ok=True)
    if with_manifest:
        (proj / "manifest.json").write_text(
            json.dumps({"name": name, "instagram": {"owner": "someone", "shortcode": "XYZ1"}}),
            encoding="utf-8",
        )
    return proj


def test_export_flyer_raises_when_manifest_missing(tmp_path):
    proj = _make_project(tmp_path, with_manifest=False)

    with pytest.raises(FileNotFoundError):
        export_flyer(proj)


def test_export_flyer_happy_path_produces_zip_with_expected_contents(tmp_path):
    proj = _make_project(tmp_path)

    zip_path = export_flyer(proj)

    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    assert zip_path.parent == proj / "exports"

    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()

    assert "manifest.json" in names
    assert "LEEME.txt" in names
    assert "exports/respuesta_jefe.txt" in names
    assert "working/compose.jsx" in names
    assert "ai/compose_ai.jsx" in names
    assert "working/blender_setup.py" in names

    # working/ and ai/ scaffold files are created on disk too (not just in the zip).
    assert (proj / "working" / "compose.jsx").exists()
    assert (proj / "ai" / "compose_ai.jsx").exists()
    assert (proj / "working" / "blender_setup.py").exists()


def test_export_flyer_does_not_overwrite_existing_compose_jsx(tmp_path):
    proj = _make_project(tmp_path)
    working_dir = proj / "working"
    working_dir.mkdir(parents=True, exist_ok=True)
    compose_ps = working_dir / "compose.jsx"
    sentinel = "// CUSTOM EDITED BY USER -- must survive re-export"
    compose_ps.write_text(sentinel, encoding="utf-8")

    export_flyer(proj)

    # The compose_ps.exists() guard must prevent clobbering user edits.
    assert compose_ps.read_text(encoding="utf-8") == sentinel


def test_export_flyer_reexport_keeps_custom_compose_in_second_zip(tmp_path):
    proj = _make_project(tmp_path)
    working_dir = proj / "working"
    working_dir.mkdir(parents=True, exist_ok=True)
    sentinel = "// CUSTOM EDITED BY USER"
    (working_dir / "compose.jsx").write_text(sentinel, encoding="utf-8")

    zip_path = export_flyer(proj)

    with zipfile.ZipFile(zip_path) as z:
        content = z.read("working/compose.jsx").decode("utf-8")

    assert content == sentinel


def test_export_flyer_custom_output_dir(tmp_path):
    proj = _make_project(tmp_path)
    out_dir = tmp_path / "custom_out"

    zip_path = export_flyer(proj, output_dir=out_dir)

    assert zip_path.parent == out_dir
    assert zip_path.exists()
