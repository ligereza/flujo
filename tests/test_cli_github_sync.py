"""Tests for `flujo github-sync`.

The status path must name an unavailable git measurement, never read an empty
stdout from a failed command as a clean tree. The regression below keeps that
contract visible.
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from flujo.cli import app
import flujo.paths

runner = CliRunner()


def _completed(returncode: int, stdout: str = "", stderr: str = ""):
    return type("Completed", (), {"returncode": returncode, "stdout": stdout, "stderr": stderr})()


def _fake_run_factory(responses: dict):
    """responses maps a git subcommand (args[1]) to a _completed(...)."""
    def fake_run(cmd, cwd=None, text=True, capture_output=True, check=False, encoding=None, errors=None):
        sub = cmd[1] if len(cmd) > 1 else ""
        return responses.get(sub, _completed(0, "", ""))
    return fake_run


def test_status_reports_dirty_tree_when_there_are_local_changes(monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run_factory({
        "rev-parse": _completed(0, "main\n"),
        "remote": _completed(0, "https://example.invalid/repo.git\n"),
        "status": _completed(0, " M archivo.py\n"),
    }))
    result = runner.invoke(app, ["github-sync", "--status"])
    assert result.exit_code == 0
    assert "Cambios locales" in result.output
    assert "M archivo.py" in result.output


def test_status_on_a_broken_git_says_so_instead_of_claiming_a_clean_tree(
        monkeypatch, tmp_path: Path):
    """The defect this test used to pin, now fixed and pinned the other way.

    Until 2026-08-31 the assertions here were the opposite: they recorded that
    `rev-parse`, `remote` and `status` could ALL fail -- running outside a git
    repository, say -- and the command still printed "Working tree limpio" and
    "Estado de GitHub preparado" with exit code 0. Empty stdout from a failed
    `git status` reads exactly like a clean tree, so the failure of the check
    was indistinguishable from the check passing. It was the same class of bug
    as `flujo doctor` reporting `airdrop pendiente: OK` by testing a directory
    that did not exist.

    Pinning the defect was the right call: it made the fix a visible behaviour
    change instead of a silent one, and this file is the proof it worked.

    What the fixed command must do: name that the measurement failed, refuse to
    call the tree clean, and exit non-zero -- an unmeasured tree is not a clean
    tree.
    """
    monkeypatch.setattr("flujo.paths.repo_root", lambda: tmp_path)
    monkeypatch.setattr("subprocess.run", _fake_run_factory({
        "rev-parse": _completed(128, "", "fatal: not a git repository\n"),
        "remote": _completed(128, "", "fatal: not a git repository\n"),
        "status": _completed(128, "", "fatal: not a git repository\n"),
    }))
    result = runner.invoke(app, ["github-sync", "--status"])
    assert result.exit_code != 0, "una medicion que fallo no puede salir 0"
    assert "Working tree limpio" not in result.output, \
        "no se afirma limpio un arbol que no se pudo medir"
    assert "No se pudo medir el working tree" in result.output
    assert "128" in result.output, "el codigo de salida de git se reporta"
    assert "NO verificado" in result.output


def test_push_with_nothing_to_commit_still_attempts_the_push(monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run_factory({
        "rev-parse": _completed(0, "main\n"),
        "remote": _completed(0, "https://example.invalid/repo.git\n"),
        "status": _completed(0, ""),
        "push": _completed(0, "Everything up-to-date\n"),
    }))
    result = runner.invoke(app, ["github-sync", "--push"])
    assert result.exit_code == 0
    assert "No hay cambios para commitear" in result.output
    assert "Sincronizado con GitHub" in result.output


def test_push_reports_a_commit_failure_and_exits_nonzero(monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run_factory({
        "rev-parse": _completed(0, "main\n"),
        "remote": _completed(0, "https://example.invalid/repo.git\n"),
        "status": _completed(0, " M archivo.py\n"),
        "add": _completed(0, ""),
        "commit": _completed(1, "", "pre-commit hook failed\n"),
    }))
    result = runner.invoke(app, ["github-sync", "--push"])
    assert result.exit_code == 1
    assert "pre-commit hook failed" in result.output


def test_push_reports_a_push_failure_and_exits_nonzero(monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run_factory({
        "rev-parse": _completed(0, "main\n"),
        "remote": _completed(0, "https://example.invalid/repo.git\n"),
        "status": _completed(0, ""),
        "push": _completed(1, "", "remote rejected\n"),
    }))
    result = runner.invoke(app, ["github-sync", "--push"])
    assert result.exit_code == 1
    assert "remote rejected" in result.output


def test_status_without_a_remote_warns_instead_of_crashing(monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run_factory({
        "rev-parse": _completed(0, "main\n"),
        "remote": _completed(128, "", "No such remote 'origin'\n"),
        "status": _completed(0, ""),
    }))
    result = runner.invoke(app, ["github-sync", "--status"])
    assert result.exit_code == 0
    assert "No hay remote" in result.output
