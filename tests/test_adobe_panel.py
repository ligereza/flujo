from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_adobe_panel_fallback_points_to_tools_parent():
    src = (ROOT / "tools" / "adobe_panel" / "js" / "main.js").read_text(encoding="utf-8")

    assert "toolsRootIfValid(parentPath(currentDir))" in src
    assert 'illustrator/scripts/logo_clean_master.jsx' in src
    assert "$.fileName" not in src


def test_adobe_panel_readme_no_pide_editar_js_a_mano():
    readme = (ROOT / "tools" / "adobe_panel" / "README.md").read_text(encoding="utf-8")

    assert "edita `REPO_TOOLS`" not in readme
    assert "repo_tools_path" in readme


def test_adobe_panel_has_readonly_install_checker():
    checker = (ROOT / "tools" / "adobe_panel" / "check_install.ps1").read_text(encoding="utf-8")

    assert "Remove-Item" not in checker
    assert "New-Item -ItemType SymbolicLink" in checker
    assert "PlayerDebugMode" in checker
    assert "repo_tools_path" in checker
