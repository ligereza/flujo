"""Tests for tools/vj_set/git_performance.py.

The module has no package __init__.py under tools/, so it is loaded directly
by file path via importlib. Tests never depend on THIS repo's live git
history (unstable, grows every commit) -- read_commits() is exercised
against tiny throwaway git repos created in tmp_path, with _REPO_ROOT
monkeypatched to point at them (the module hardcodes cwd=_REPO_ROOT for its
`git log` subprocess call; there is no other injection point). compose()
and write_outputs() are exercised directly against synthetic commit dicts
that match read_commits()'s documented output schema -- the natural
injection point for everything downstream of git.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "vj_set" / "git_performance.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("vj_git_performance", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gp = _load_module()


# ---------------------------------------------------------------------------
# synthetic commit dicts (read_commits()' documented per-commit schema:
# hash, short, parents, t, subject, type)
# ---------------------------------------------------------------------------


def _commit(hash_char: str, t: int, subject: str, parents: int = 1) -> dict:
    h = hash_char * 40
    return {
        "hash": h,
        "short": h[:7],
        "parents": parents,
        "t": t,
        "subject": subject,
        "type": gp._commit_type(subject, parents),
    }


SAMPLE_COMMITS = [
    _commit("a", 1_700_000_000, "feat: add widget"),
    _commit("b", 1_700_000_100, "fix: broken widget"),
    _commit("c", 1_700_000_200, "chore: bump deps"),
    _commit("m", 1_700_000_300, "Merge branch 'feature'", parents=2),
]


# ---------------------------------------------------------------------------
# _commit_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("subject", "n_parents", "expected"),
    [
        ("feat: add thing", 1, "feat"),
        ("fix(scope): repair thing", 1, "fix"),
        ("feat!: breaking change", 1, "feat"),
        ("docs: update readme", 1, "docs"),
        ("random commit message", 1, "other"),
        ("weirdtype: something", 1, "other"),  # valid prefix, not in TYPE_LAYER
        ("Merge branch 'x' into y", 2, "merge"),
        ("feat: even if merge-like subject", 2, "merge"),  # parents wins over subject
    ],
)
def test_commit_type_classification(subject: str, n_parents: int, expected: str) -> None:
    assert gp._commit_type(subject, n_parents) == expected


# ---------------------------------------------------------------------------
# _smpte
# ---------------------------------------------------------------------------


def test_smpte_zero() -> None:
    assert gp._smpte(0.0, fps=30) == "00:00:00:00"


def test_smpte_one_second_30fps() -> None:
    assert gp._smpte(1.0, fps=30) == "00:00:01:00"


def test_smpte_rolls_minutes_and_hours() -> None:
    assert gp._smpte(3661.0, fps=25) == "01:01:01:00"


# ---------------------------------------------------------------------------
# compose()
# ---------------------------------------------------------------------------


def test_compose_empty_commits_returns_empty_list() -> None:
    """Edge case: compose() handles an empty commit list without crashing."""
    assert gp.compose([], duration=360.0) == []


def test_compose_produces_one_cue_per_commit() -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    assert len(cues) == len(SAMPLE_COMMITS)


def test_compose_first_and_last_cue_bound_the_duration() -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    assert cues[0]["t"] == 0.0
    assert cues[-1]["t"] == pytest.approx(360.0)


def test_compose_cue_schema() -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    required_keys = {"t", "smpte", "layer", "clip", "type", "subject", "short", "drop", "color"}
    for cue in cues:
        assert set(cue.keys()) == required_keys
        assert isinstance(cue["t"], float)
        assert isinstance(cue["smpte"], str)
        assert isinstance(cue["layer"], int)
        assert isinstance(cue["clip"], int)
        assert 1 <= cue["clip"] <= 8
        assert isinstance(cue["type"], str)
        assert isinstance(cue["subject"], str)
        assert isinstance(cue["short"], str)
        assert isinstance(cue["drop"], bool)
        assert isinstance(cue["color"], str) and cue["color"].startswith("#")


def test_compose_merge_commit_is_flagged_as_drop_on_layer_1() -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    merge_cue = cues[-1]
    assert merge_cue["type"] == "merge"
    assert merge_cue["drop"] is True
    assert merge_cue["layer"] == 1


def test_compose_is_deterministic() -> None:
    a = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    b = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    assert a == b


# ---------------------------------------------------------------------------
# write_outputs(): cue_sheet.json / osc_cues.csv / osc_score.json
# ---------------------------------------------------------------------------


def test_write_outputs_creates_three_parseable_files(tmp_path: Path) -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    out_dir = tmp_path / "out"
    gp.write_outputs(cues, out_dir, duration=360.0, fps=30)

    cue_sheet = json.loads((out_dir / "cue_sheet.json").read_text(encoding="utf-8"))
    assert cue_sheet == cues

    with (out_dir / "osc_cues.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["smpte", "seconds", "title", "layer", "clip", "osc_address", "value"]
    assert len(rows) == len(cues) + 1

    score = json.loads((out_dir / "osc_score.json").read_text(encoding="utf-8"))
    assert score["port"] == 7000
    assert score["fps"] == 30
    assert score["duration_s"] == 360.0
    assert len(score["messages"]) == len(cues)

    assert (out_dir / "timeline.html").exists()


def test_write_outputs_osc_cues_csv_rows_match_cues(tmp_path: Path) -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    out_dir = tmp_path / "out"
    gp.write_outputs(cues, out_dir, duration=360.0, fps=30)

    with (out_dir / "osc_cues.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    body = rows[1:]
    assert len(body) == len(cues)
    for cue, row in zip(cues, body):
        smpte, _seconds, title, layer, clip, osc_address, value = row
        assert smpte == cue["smpte"]
        assert int(layer) == cue["layer"]
        assert int(clip) == cue["clip"]
        assert osc_address == f"/composition/layers/{cue['layer']}/clips/{cue['clip']}/connect"
        assert value == "1"
        assert cue["short"] in title


def test_write_outputs_osc_score_messages_schema(tmp_path: Path) -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    out_dir = tmp_path / "out"
    gp.write_outputs(cues, out_dir, duration=360.0, fps=30)

    score = json.loads((out_dir / "osc_score.json").read_text(encoding="utf-8"))
    for cue, msg in zip(cues, score["messages"]):
        assert msg["t"] == cue["t"]
        assert msg["address"] == f"/composition/layers/{cue['layer']}/clips/{cue['clip']}/connect"
        assert msg["args"] == [1]
        assert msg["type"] == cue["type"]


def test_write_outputs_is_deterministic(tmp_path: Path) -> None:
    cues = gp.compose(SAMPLE_COMMITS, duration=360.0, fps=30)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    gp.write_outputs(cues, out_a, duration=360.0, fps=30)
    gp.write_outputs(cues, out_b, duration=360.0, fps=30)

    assert (out_a / "cue_sheet.json").read_text(encoding="utf-8") == (
        out_b / "cue_sheet.json"
    ).read_text(encoding="utf-8")
    assert (out_a / "osc_score.json").read_text(encoding="utf-8") == (
        out_b / "osc_score.json"
    ).read_text(encoding="utf-8")
    assert (out_a / "osc_cues.csv").read_text(encoding="utf-8") == (
        out_b / "osc_cues.csv"
    ).read_text(encoding="utf-8")


def test_write_outputs_handles_empty_cues_without_crash(tmp_path: Path) -> None:
    """Edge case: write_outputs() with zero cues produces valid, parseable
    (empty) outputs instead of crashing."""
    out_dir = tmp_path / "out_empty"
    gp.write_outputs([], out_dir, duration=360.0, fps=30)

    assert json.loads((out_dir / "cue_sheet.json").read_text(encoding="utf-8")) == []

    with (out_dir / "osc_cues.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows == [["smpte", "seconds", "title", "layer", "clip", "osc_address", "value"]]

    score = json.loads((out_dir / "osc_score.json").read_text(encoding="utf-8"))
    assert score["messages"] == []

    assert (out_dir / "timeline.html").exists()


# ---------------------------------------------------------------------------
# read_commits(): tiny throwaway git repos, never this repo's live history.
#
# read_commits() hardcodes `cwd=str(_REPO_ROOT)` for its `git log` subprocess
# call and takes no repo-path parameter, so the only injection point is
# monkeypatching the module-level _REPO_ROOT global to point at a repo built
# fresh in tmp_path.
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.email", "vj@test.local"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.name", "vj tester"], cwd=str(path), check=True)


def _commit_file(path: Path, name: str, message: str, iso_date: str) -> None:
    (path / name).write_text(f"{name}\n", encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=str(path), check=True)
    env = dict(os.environ)
    env["GIT_AUTHOR_DATE"] = iso_date
    env["GIT_COMMITTER_DATE"] = iso_date
    env["GIT_AUTHOR_NAME"] = "vj tester"
    env["GIT_AUTHOR_EMAIL"] = "vj@test.local"
    env["GIT_COMMITTER_NAME"] = "vj tester"
    env["GIT_COMMITTER_EMAIL"] = "vj@test.local"
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=str(path), check=True, env=env)


@pytest.fixture()
def throwaway_repo(tmp_path: Path) -> Path:
    """Small deterministic repo: known messages, known dates, linear history."""
    repo = tmp_path / "throwaway_repo"
    repo.mkdir()
    _init_repo(repo)
    _commit_file(repo, "a.txt", "feat: first feature", "2026-01-01T00:00:00")
    _commit_file(repo, "b.txt", "fix: repair bug", "2026-01-02T00:00:00")
    _commit_file(repo, "c.txt", "chore: housekeeping", "2026-01-03T00:00:00")
    _commit_file(repo, "d.txt", "docs: write docs", "2026-01-04T00:00:00")
    return repo


def test_read_commits_from_throwaway_repo(
    monkeypatch: pytest.MonkeyPatch, throwaway_repo: Path
) -> None:
    monkeypatch.setattr(gp, "_REPO_ROOT", throwaway_repo)
    commits = gp.read_commits(limit=None, all_refs=False)

    assert len(commits) == 4
    assert [c["subject"] for c in commits] == [
        "feat: first feature",
        "fix: repair bug",
        "chore: housekeeping",
        "docs: write docs",
    ]
    assert [c["type"] for c in commits] == ["feat", "fix", "chore", "docs"]
    times = [c["t"] for c in commits]
    assert times == sorted(times)  # chronological, per read_commits()' own sort
    for c in commits:
        assert set(c.keys()) == {"hash", "short", "parents", "t", "subject", "type"}
        assert c["short"] == c["hash"][:7]
    assert commits[0]["parents"] == 0  # root commit
    assert [c["parents"] for c in commits[1:]] == [1, 1, 1]  # linear history, no merges


def test_read_commits_full_pipeline_end_to_end(
    monkeypatch: pytest.MonkeyPatch, throwaway_repo: Path, tmp_path: Path
) -> None:
    """read_commits -> compose -> write_outputs, all from a real (throwaway) repo."""
    monkeypatch.setattr(gp, "_REPO_ROOT", throwaway_repo)
    commits = gp.read_commits(limit=None, all_refs=False)
    cues = gp.compose(commits, duration=120.0, fps=30)
    out_dir = tmp_path / "pipeline_out"
    gp.write_outputs(cues, out_dir, duration=120.0, fps=30)

    assert json.loads((out_dir / "cue_sheet.json").read_text(encoding="utf-8")) == cues
    assert (out_dir / "osc_cues.csv").exists()
    score = json.loads((out_dir / "osc_score.json").read_text(encoding="utf-8"))
    assert len(score["messages"]) == len(cues) == 4
    assert (out_dir / "timeline.html").exists()


# ---------------------------------------------------------------------------
# Regresiones de los 2 findings de la review T-A3 (2026-07-16), ya corregidos
# por el director en git_performance.py: repo sin commits ahora devuelve [] y
# limit=0 ahora manda -n0 de verdad (era truthiness).
# ---------------------------------------------------------------------------


def test_read_commits_on_zero_commit_repo_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Repo recien inicializado (0 commits): git log sale 128 con 'does not
    have any commits'; read_commits() lo traduce a [] para que el guard
    'sin commits' de main() sea alcanzable en vez de reventar con
    RuntimeError."""
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    _init_repo(empty_repo)
    monkeypatch.setattr(gp, "_REPO_ROOT", empty_repo)

    assert gp.read_commits(limit=None, all_refs=False) == []


def test_read_commits_limit_zero_returns_zero_commits(
    monkeypatch: pytest.MonkeyPatch, throwaway_repo: Path
) -> None:
    """limit=0 era ignorado por truthiness (`if limit:`); ahora
    `if limit is not None:` manda -n0 y git devuelve cero commits."""
    monkeypatch.setattr(gp, "_REPO_ROOT", throwaway_repo)
    limited = gp.read_commits(limit=0, all_refs=False)
    unlimited = gp.read_commits(limit=None, all_refs=False)
    assert limited == []
    assert len(unlimited) == 4
