"""Tests for src/flujo/index/db.py -- flyer index (file integrity, dedup).

Uses tmp_path + monkeypatch so the real workspace/db is never touched:
- flujo.paths.flyer_base() is monkeypatched to a tmp dir (rebuild_index imports it
  locally via `from ..paths import flyer_base` on every call, so patching the
  attribute on the paths module is picked up).
- flujo.index.db.db_path() is monkeypatched directly (same-module global lookup,
  so patching the module attribute affects rebuild_index/list_flyers/find_duplicates).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flujo import paths as paths_module
from flujo.index import db as db_module


def _make_job(base: Path, name: str, manifest: dict | None, raw_text: str | None = None) -> Path:
    proj = base / name
    proj.mkdir(parents=True, exist_ok=True)
    mf = proj / "manifest.json"
    if raw_text is not None:
        mf.write_text(raw_text, encoding="utf-8")
    elif manifest is not None:
        mf.write_text(json.dumps(manifest), encoding="utf-8")
    return proj


@pytest.fixture
def isolated_index(tmp_path, monkeypatch):
    """Point flyer_base() and db_path() at a throwaway tmp_path tree."""
    flyer_base_dir = tmp_path / "flyer_eventos"
    flyer_base_dir.mkdir(parents=True, exist_ok=True)
    fake_db_path = tmp_path / "flujo.db"

    monkeypatch.setattr(paths_module, "flyer_base", lambda: flyer_base_dir)
    monkeypatch.setattr(db_module, "db_path", lambda: fake_db_path)

    return flyer_base_dir, fake_db_path


def test_rebuild_index_scans_manifests(isolated_index):
    base, _ = isolated_index
    _make_job(
        base,
        "proj_a",
        {
            "name": "Proj A",
            "status": "created",
            "instagram": {"shortcode": "AAA111", "url": "https://instagram.com/p/AAA111", "owner": "ownerA"},
        },
    )
    _make_job(
        base,
        "proj_b",
        {
            "name": "Proj B",
            "status": "in_progress",
            "instagram": {"shortcode": "BBB222", "url": "https://instagram.com/p/BBB222", "owner": "ownerB"},
        },
    )

    result = db_module.rebuild_index()

    assert result["indexed"] == 2
    rows = db_module.list_flyers()
    shortcodes = {r["shortcode"] for r in rows}
    assert shortcodes == {"AAA111", "BBB222"}
    names = {r["name"] for r in rows}
    assert names == {"Proj A", "Proj B"}


def test_rebuild_index_skips_malformed_manifest_without_crashing(isolated_index):
    base, _ = isolated_index
    _make_job(
        base,
        "proj_good",
        {"name": "Good", "status": "created", "instagram": {"shortcode": "GOOD01"}},
    )
    # Malformed JSON -- must be skipped via the bare except:continue, not raise.
    _make_job(base, "proj_bad", manifest=None, raw_text="{ this is not valid json ,,, ")

    result = db_module.rebuild_index()

    assert result["indexed"] == 1
    rows = db_module.list_flyers()
    assert len(rows) == 1
    assert rows[0]["name"] == "Good"


def test_rebuild_index_skips_dir_without_manifest(isolated_index):
    base, _ = isolated_index
    (base / "no_manifest_dir").mkdir()
    _make_job(base, "proj_ok", {"name": "OK", "status": "created", "instagram": {"shortcode": "OK001"}})

    result = db_module.rebuild_index()

    assert result["indexed"] == 1


def test_find_duplicates_detects_shared_shortcode(isolated_index):
    base, _ = isolated_index
    _make_job(
        base,
        "proj_dup1",
        {"name": "Dup1", "status": "created", "instagram": {"shortcode": "SHARED1"}},
    )
    _make_job(
        base,
        "proj_dup2",
        {"name": "Dup2", "status": "created", "instagram": {"shortcode": "SHARED1"}},
    )
    _make_job(
        base,
        "proj_unique",
        {"name": "Unique", "status": "created", "instagram": {"shortcode": "UNIQUE1"}},
    )

    db_module.rebuild_index()
    dups = db_module.find_duplicates()

    assert len(dups) == 1
    dup = dups[0]
    assert dup["shortcode"] == "SHARED1"
    assert dup["c"] == 2
    paths = dup["paths"].split("|")
    assert len(paths) == 2
    assert any("proj_dup1" in p for p in paths)
    assert any("proj_dup2" in p for p in paths)


def test_find_duplicates_empty_when_all_shortcodes_unique(isolated_index):
    base, _ = isolated_index
    _make_job(base, "proj_a", {"name": "A", "status": "created", "instagram": {"shortcode": "A1"}})
    _make_job(base, "proj_b", {"name": "B", "status": "created", "instagram": {"shortcode": "B1"}})

    db_module.rebuild_index()
    dups = db_module.find_duplicates()

    assert dups == []
