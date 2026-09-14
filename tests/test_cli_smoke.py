"""Tests smoke para la CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

import flujo.paths  # noqa: F401 -- monkeypatch("flujo.paths.repo_root") necesita el submodulo ya importado
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


def test_verify_fails_closed_when_a_subprocess_fails(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return type("Completed", (), {"returncode": 7, "stdout": "", "stderr": "boom"})()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = runner.invoke(app, ["verify", "--no-pytest", "--no-hub-smoke"])

    assert result.exit_code == 1
    assert "verify falló en compileall" in result.output
    assert "verify OK" not in result.output
    assert len(calls) == 1


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


def test_app_alias_help():
    result = runner.invoke(app, ["app", "--help"])
    assert result.exit_code == 0
    assert "interfaz web" in result.output.lower() or "alias" in result.output.lower()


def test_ai_prompt_command():
    result = runner.invoke(app, ["ai-prompt", "Necesito cotizar suplementos", "--area", "suplementos"])
    assert result.exit_code == 0
    assert "Repo: ligereza/vibecodeine" in result.output
    assert "Texto a procesar" in result.output
    assert "suplementos" in result.output.lower()


def test_github_sync_status(monkeypatch):
    def fake_run(cmd, cwd=None, text=True, capture_output=True, check=False, encoding=None, errors=None):
        return type("Completed", (), {"returncode": 0, "stdout": "On branch main\n", "stderr": ""})()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = runner.invoke(app, ["github-sync", "--status"])
    assert result.exit_code == 0
    assert "github" in result.output.lower()
