"""`flujo doctor` must fail closed when `git status --short` cannot run.

`doctor` runs three git calls to build its report. All three now check
`returncode == 0` and show AVISO when git fails. The regression below points
`repo_root()` at a directory with no `.git` and ensures the working-tree row
names the failed measurement rather than claiming "limpio".

This is the same class of bug fixed in `flujo github-sync --status`: an empty
stdout from a failed command must never be treated as a successful empty
measurement.

The regression test keeps the failure mode visible: a missing repository must
be named as an unmeasured working tree, never reported as clean.
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from flujo.cli import app
import flujo.paths as paths

runner = CliRunner()


def test_doctor_names_an_unmeasured_working_tree_when_git_status_fails(
        tmp_path: Path, monkeypatch):
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    # The other two git checks over the SAME failed git invocation correctly
    # name the failure:
    assert "git branch" in result.output
    assert "git remote" in result.output
    # The working-tree row must name the failed measurement rather than claim
    # that an unmeasured tree is clean.
    assert "git working tree" in result.output
    assert "AVISO" in result.output
    assert "No se pudo medir" in result.output
    assert "limpio" not in result.output
