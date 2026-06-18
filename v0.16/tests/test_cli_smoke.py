"""Tests smoke para la CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from flujo.cli import app


runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "flujo" in result.output.lower()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "v0" in result.output or "versión" in result.output.lower()


def test_health_command(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0


def test_job_list_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "jobs").mkdir()
    result = runner.invoke(app, ["job", "list"])
    assert result.exit_code == 0
    assert "no hay jobs" in result.output.lower() or "0" in result.output


def test_daily_command(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "context").mkdir()
    (tmp_path / "jobs").mkdir()
    result = runner.invoke(app, ["daily"])
    assert result.exit_code == 0


def test_render_formats_no_index(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    (tmp_path / "tools" / "piezas_vectoriales" / "plantillas").mkdir(parents=True)
    result = runner.invoke(app, ["render", "formats"])
    assert result.exit_code == 0
