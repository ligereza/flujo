"""Tests del sistema airdrop (engine + CLI).

Estos tests existen para evitar la regresión donde `cli.py` y `airdrop.py`
quedaron con APIs desincronizadas y TODOS los comandos `flujo airdrop`
dejaron de funcionar (ImportError / TypeError).
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

import flujo.airdrop as airdrop
from flujo.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Coherencia de API: cli.py importa lo que airdrop.py realmente expone.
# ---------------------------------------------------------------------------

def test_airdrop_public_api_exists():
    """Las funciones que la CLI importa deben existir en el módulo airdrop."""
    for name in (
        "scan_airdrop",
        "list_airdrop_files",
        "apply_airdrop",
        "run_auto_checkpoint",
        "rollback_last",
    ):
        assert hasattr(airdrop, name), f"falta airdrop.{name}"


def test_airdrop_signatures_are_versionless():
    """El diseño es 'sin versiones': scan/apply no reciben un arg de versión."""
    import inspect

    scan_params = list(inspect.signature(airdrop.scan_airdrop).parameters)
    assert scan_params == [], "scan_airdrop() no debe pedir versión"

    apply_params = list(inspect.signature(airdrop.apply_airdrop).parameters)
    # solo el flag opcional dry_run
    assert apply_params in ([], ["dry_run"]), apply_params


# ---------------------------------------------------------------------------
# Comportamiento del motor con un _airdrop/ simulado.
# ---------------------------------------------------------------------------

def _patch_root(monkeypatch, root: Path):
    monkeypatch.setattr(airdrop, "repo_root", lambda: root)


def test_scan_empty(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    assert airdrop.scan_airdrop() == []
    assert airdrop.list_airdrop_files() == []


def test_scan_detects_new_and_replace(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    (tmp_path / "_airdrop" / "docs").mkdir(parents=True)
    (tmp_path / "_airdrop" / "docs" / "nuevo.md").write_text("nuevo")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "existente.md").write_text("viejo")
    (tmp_path / "_airdrop" / "docs" / "existente.md").write_text("nuevo")

    by_rel = {c["rel"]: c["status"] for c in airdrop.scan_airdrop()}
    assert by_rel["docs/nuevo.md"] == "NEW"
    assert by_rel["docs/existente.md"] == "REPLACE"


def test_apply_copies_and_backs_up(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    (tmp_path / "_airdrop" / "docs").mkdir(parents=True)
    (tmp_path / "_airdrop" / "docs" / "nuevo.md").write_text("contenido nuevo")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "existente.md").write_text("ORIGINAL")
    (tmp_path / "_airdrop" / "docs" / "existente.md").write_text("ACTUALIZADO")

    airdrop.apply_airdrop()

    assert (tmp_path / "docs" / "nuevo.md").read_text() == "contenido nuevo"
    assert (tmp_path / "docs" / "existente.md").read_text() == "ACTUALIZADO"
    # se guardó backup del archivo reemplazado
    backups = list((tmp_path / "_airdrop_backups").rglob("existente.md"))
    assert backups, "no se creó backup del archivo reemplazado"
    assert backups[0].read_text() == "ORIGINAL"


def test_apply_dry_run_makes_no_changes(tmp_path, monkeypatch):
    _patch_root(monkeypatch, tmp_path)
    (tmp_path / "_airdrop" / "docs").mkdir(parents=True)
    (tmp_path / "_airdrop" / "docs" / "nuevo.md").write_text("x")

    airdrop.apply_airdrop(dry_run=True)
    assert not (tmp_path / "docs" / "nuevo.md").exists()


# ---------------------------------------------------------------------------
# CLI: los comandos deben arrancar sin ImportError/TypeError.
# ---------------------------------------------------------------------------

def test_cli_airdrop_list_runs(tmp_path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    monkeypatch.setattr(airdrop, "repo_root", lambda: tmp_path)
    result = runner.invoke(app, ["airdrop", "list"])
    assert result.exit_code == 0, result.output


def test_cli_airdrop_dry_run_runs(tmp_path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    monkeypatch.setattr(airdrop, "repo_root", lambda: tmp_path)
    result = runner.invoke(app, ["airdrop", "dry-run"])
    assert result.exit_code == 0, result.output


def test_cli_airdrop_status_runs():
    result = runner.invoke(app, ["airdrop", "status"])
    assert result.exit_code == 0, result.output
    assert "version" in result.output.lower()
