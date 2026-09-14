#!/usr/bin/env python3
"""tests/test_repo_scan.py -- the gates must see what is about to enter.

Two ratchets on this repository enumerated with plain ``git ls-files``, which
lists only TRACKED files, so a brand-new file passed the local gate unseen and
failed once it was already committed.

Both instances were real, and one of them had been known for weeks:

- ``test_higiene_docs.py`` documented it in its own docstring -- "cuatro README
  vendorizados pasaron el pytest local y tumbaron el CI" -- and resolved it with
  a manual workaround, ``git add`` before running the suite. A workaround kept in
  a person's memory fails again.
- ``test_privacidad_repo.py`` hit it on 2026-08-21 when a new test file carried a
  real Windows username straight through the local gate.

Fixing only one of them would have left the class open, so both now share
``repo_scan.versionable_files()`` and this file pins the behaviour of the shared
enumerator itself.
"""
from __future__ import annotations

import subprocess

import pytest

from repo_scan import REPO, versionable_files


def _git_ok() -> bool:
    return subprocess.run(["git", "rev-parse", "--git-dir"], cwd=REPO,
                          capture_output=True).returncode == 0


def test_tracked_files_are_still_enumerated():
    if not _git_ok():
        pytest.skip("not a usable git checkout")
    names = versionable_files()
    assert "tests/test_repo_scan.py" in names or "tests/repo_scan.py" in names
    assert "pyproject.toml" in names


def test_a_pattern_narrows_the_result():
    if not _git_ok():
        pytest.skip("not a usable git checkout")
    markdown = versionable_files(("*.md",))
    assert markdown, "no markdown found at all"
    assert all(name.endswith(".md") for name in markdown)
    assert len(markdown) < len(versionable_files())


def test_a_new_untracked_file_is_visible_before_it_is_committed():
    """The whole point. Without this the gates guard history, not entry."""
    if not _git_ok():
        pytest.skip("not a usable git checkout")
    probe = REPO / "_repo_scan_probe_tmp.md"
    try:
        probe.write_text("sonda\n", encoding="utf-8")
        assert "_repo_scan_probe_tmp.md" in versionable_files(("*.md",))
    finally:
        probe.unlink(missing_ok=True)
    assert "_repo_scan_probe_tmp.md" not in versionable_files(("*.md",))


def test_ignored_files_stay_out():
    """--exclude-standard must hold, or every gate starts scanning .venv."""
    if not _git_ok():
        pytest.skip("not a usable git checkout")
    names = versionable_files()
    assert not [n for n in names if n.startswith((".venv/", "node_modules/"))]


def test_the_result_has_no_duplicates_and_is_stable():
    if not _git_ok():
        pytest.skip("not a usable git checkout")
    first = versionable_files(("*.md",))
    assert first == list(dict.fromkeys(first)), "duplicate entries"
    assert first == versionable_files(("*.md",)), "unstable ordering"


def test_no_git_returns_empty_so_a_caller_can_skip(tmp_path):
    """Empty must be distinguishable, so a gate skips instead of passing blind."""
    assert versionable_files(repo=tmp_path) == []


def test_both_entry_gates_use_the_shared_enumerator():
    """Fixing one instance and leaving the other is how the class survived.

    Named both gates unconditionally until 2026-09-02. `test_higiene_docs.py`
    stayed in MAK with the rest of the doc ratchets, so reading it from here
    raised FileNotFoundError -- an absent counterpart reported as a defect.
    The pair is checked wherever both exist; each checkout checks what it
    physically carries, and measuring nothing is an error.
    """
    presentes = [name for name in ("test_privacidad_repo.py",
                                   "test_higiene_docs.py")
                 if (REPO / "tests" / name).is_file()]
    assert presentes, "neither entry gate is in this checkout: nothing measured"
    for name in presentes:
        source = (REPO / "tests" / name).read_text(encoding="utf-8")
        assert "versionable_files" in source, (
            f"{name} no longer uses the shared enumerator")
        assert '["git", "ls-files"]' not in source, (
            f"{name} went back to enumerating only tracked files")
