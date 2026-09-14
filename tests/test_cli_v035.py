from pathlib import Path

from typer.testing import CliRunner

from flujo.cli import app


runner = CliRunner()


def test_doctor_command_runs_without_heavy_checks(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "doctor" in result.output.lower()
    assert "python" in result.output.lower()


def test_init_fresh_creates_workspace_dirs_without_rebuild(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("FLUJO_WORKSPACE_ROOT", str(workspace))
    result = runner.invoke(app, ["init", "--fresh", "--no-rebuild-index"])
    assert result.exit_code == 0
    assert (workspace / "jobs" / "_template" / "brief.yaml").exists()
    assert (workspace / "inbox").is_dir()
    assert (workspace / "data").is_dir()
    assert (workspace / "datadrops" / "incoming").is_dir()
