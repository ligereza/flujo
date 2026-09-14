"""git_state()/_git_state() over a non-repo directory: fixed defect.

Three copies of the same helper -- `flujo.runrecord.git_state`,
`tools/substrate_scan.py::git_state`, and `tools/png_xmp_witness.py::_git_state`
-- built a run-record's git provenance by shelling out to git and folding a
FAILED call (not a repository, git missing, timeout) into the same empty
string as a successful call with no output. `tree_dirty = bool(status)` then
read False, and `commit`/`branch` read "", for a check that never ran at all --
indistinguishable from a genuinely clean repository with no history. Same
family as `flujo doctor` reporting `airdrop pendiente: OK` for a directory
that did not exist.

Fixed 2026-08-31: each function now reports an explicit `available` flag, and
`tree_dirty` is `None` (not `False`) when the measurement did not run, so a
consumer cannot mistake "we could not tell" for "it was clean".
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "src"))
from flujo.runrecord import git_state as runrecord_git_state  # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runrecord_git_state_names_a_git_call_that_could_not_be_measured():
    not_a_repo = Path(tempfile.mkdtemp())
    state = runrecord_git_state(not_a_repo)
    assert state["available"] is False, "a failed git call must say so"
    assert state["tree_dirty"] is None, (
        "must not read as False (clean) when the check never ran")
    assert state["commit"] == ""
    assert state["dirty_paths"] == []


def test_runrecord_git_state_reports_available_on_the_real_repo():
    # Sanity: the fix must not turn a WORKING repo into a false negative.
    state = runrecord_git_state(REPO_ROOT)
    assert state["available"] is True
    assert state["tree_dirty"] in (True, False)
    assert len(state["commit"]) == 40


def test_substrate_scan_git_state_names_a_git_call_that_could_not_be_measured(
        monkeypatch):
    module = _load(REPO_ROOT / "tools" / "substrate_scan.py",
                    "substrate_scan_defect_check")
    monkeypatch.setattr(module, "ROOT", Path(tempfile.mkdtemp()))
    state = module.git_state()
    assert state["available"] is False
    assert state["tree_dirty"] is None
    assert state["commit"] == ""


def test_png_xmp_witness_git_state_names_a_git_call_that_could_not_be_measured(
        monkeypatch):
    module = _load(REPO_ROOT / "tools" / "png_xmp_witness.py",
                    "png_xmp_witness_defect_check")
    monkeypatch.setattr(module, "ROOT", Path(tempfile.mkdtemp()))
    state = module._git_state()
    assert state["available"] is False
    assert state["tree_dirty"] is None
    assert state["commit"] == ""
