"""Tests for the door on the classification queue.

The queue held 8273 rows, all pending, with four question templates and no code
anywhere that writes ``status``. These tests pin the three claims that make it
answerable, each measured on the real data first:

- nearly half the rows carry a check a machine can repeat, so they are not
  questions for a person,
- the remaining rows fold into the unit the coarse half of each question is
  really asked in,
- and an answer that covers only the coarse half says so, instead of leaving the
  fine half quietly closed.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from flujo.knowledge import classification_queue as queue_module
from flujo.knowledge.classification_queue import (
    COVERS_BOTH,
    COVERS_COARSE_ONLY,
    QUESTION_PARTS,
    RULE_CANONICAL_COPY,
    RULE_VIRTUALENV,
    STATUS_CLASSIFIED,
    STATUS_INSTALLED_DEPENDENCY,
    STATUS_PENDING,
    ClassificationQueueError,
    apply_resolutions,
    canonical_index,
    coverage,
    load_candidates,
    machine_proposals,
    question_groups,
    summary,
    virtual_environment_root,
)

SCHEMA = """
CREATE TABLE artifacts (
    artifact_id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE,
    root_kind TEXT NOT NULL, relative_path TEXT NOT NULL, name TEXT NOT NULL,
    suffix TEXT NOT NULL, artifact_kind TEXT NOT NULL,
    size_bytes INTEGER NOT NULL, mode TEXT NOT NULL, sha256 TEXT);
CREATE TABLE classification_queue (
    queue_id INTEGER PRIMARY KEY, artifact_id INTEGER NOT NULL,
    candidate_kind TEXT NOT NULL, reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    evidence_packet TEXT NOT NULL DEFAULT '',
    UNIQUE(artifact_id, candidate_kind));
"""


def _add(con, path: str, kind: str, sha: str | None, size: int = 10) -> int:
    name = path.rsplit("/", 1)[-1]
    cur = con.execute(
        "INSERT INTO artifacts(path,root_kind,relative_path,name,suffix,"
        "artifact_kind,size_bytes,mode,sha256) VALUES(?,?,?,?,?,?,?,?,?)",
        (path, "active", path, name, "." + name.rsplit(".", 1)[-1], "text",
         size, "100644", sha))
    artifact_id = int(cur.lastrowid)
    con.execute("INSERT INTO classification_queue(artifact_id,candidate_kind,reason)"
                " VALUES(?,?,?)", (artifact_id, kind, f"{kind} needs classification"))
    return artifact_id


@pytest.fixture()
def queue_db(tmp_path: Path) -> Path:
    """A canonical tree, a byte-identical copy of it, and a real virtualenv."""
    canonical = tmp_path / "repo"
    (canonical / "tools").mkdir(parents=True)
    copy_root = tmp_path / "runner"
    copy_root.mkdir()
    env = tmp_path / "third_party" / "env"
    (env / "Lib" / "site-packages" / "flask").mkdir(parents=True)
    # The one file that makes a directory a virtual environment, by definition.
    (env / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    database = tmp_path / "knowledge.db"
    con = sqlite3.connect(database)
    con.executescript(SCHEMA)
    _add(con, f"{canonical}/tools/render.py", "tool", "sha_render")
    _add(con, f"{canonical}/tools/laser.py", "tool", "sha_laser")
    _add(con, f"{canonical}/docs/plan.md", "idea", "sha_plan")
    _add(con, f"{copy_root}/tools/render.py", "tool", "sha_render")
    _add(con, f"{copy_root}/tools/drifted.py", "tool", "sha_drifted")
    _add(con, f"{env}/Lib/site-packages/flask/app.py", "tool", "sha_flask")
    _add(con, f"{env}/Lib/site-packages/flask/ctx.py", "tool", "sha_ctx")
    con.commit()
    con.close()
    return database


@pytest.fixture()
def canonical_root(queue_db: Path) -> str:
    return str(queue_db.parent / "repo")


def test_a_virtualenv_is_recognised_by_the_file_python_writes(queue_db: Path) -> None:
    """A name list missed 1463 real rows; pyvenv.cfg is a definition.

    Measured on the live database: all 1463 site-packages rows came from ONE
    directory called ``env``, a Windows virtualenv copied onto the box. The skip
    list held ``venvs``, ``.venvs`` and ``venv-providers``.
    """
    env = queue_db.parent / "third_party" / "env"
    inside = f"{env}/Lib/site-packages/flask/app.py"
    assert virtual_environment_root(inside) == str(env)
    assert virtual_environment_root(f"{queue_db.parent}/repo/tools/render.py") is None


def test_a_path_that_is_gone_is_not_evidence(tmp_path: Path) -> None:
    """An unreadable disk must not be read as "not a virtualenv, definitely"."""
    assert virtual_environment_root(str(tmp_path / "absent" / "x.py")) is None


def test_installed_and_copied_rows_are_proposals_with_their_check(
        queue_db: Path, canonical_root: str) -> None:
    candidates = load_candidates(queue_db)
    assert len(candidates) == 7
    proposals = machine_proposals(
        candidates, canonical=canonical_index(queue_db, canonical_root),
        canonical_root=canonical_root)
    by_rule = {}
    for proposal in proposals:
        by_rule.setdefault(proposal.rule, []).append(proposal)
    assert len(by_rule[RULE_VIRTUALENV]) == 2
    assert len(by_rule[RULE_CANONICAL_COPY]) == 1
    copy = by_rule[RULE_CANONICAL_COPY][0]
    assert "runner/tools/render.py" in copy.path
    assert any("sha256 identical to" in item["detail"] for item in copy.evidence)
    assert all(any(item["kind"] == "ordering_policy" for item in proposal.evidence)
               for proposal in proposals)
    # The drifted copy is NOT byte-identical, so it stays a real question.
    assert not any("drifted" in p.path for p in proposals)


def test_a_canonical_file_is_never_proposed_as_a_copy_of_itself(
        queue_db: Path, canonical_root: str) -> None:
    proposals = machine_proposals(
        load_candidates(queue_db),
        canonical=canonical_index(queue_db, canonical_root),
        canonical_root=canonical_root)
    assert not any(p.path.startswith(canonical_root) for p in proposals)


def test_machine_proposals_fail_closed_when_policy_cannot_be_loaded(
        queue_db: Path, canonical_root: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*_args, **_kwargs):
        raise queue_module.FeaturePolicyError("registry unavailable")

    monkeypatch.setattr(queue_module, "may_decide", denied)
    with pytest.raises(ClassificationQueueError, match="ordering_policy_refused"):
        machine_proposals(
            load_candidates(queue_db),
            canonical=canonical_index(queue_db, canonical_root),
            canonical_root=canonical_root)


def test_the_virtualenv_rule_wins_over_content_identity(tmp_path: Path) -> None:
    """A repository may vendor the same file it also has installed.

    Order is a decision, not an accident: inside an environment the file is a
    dependency whatever its bytes match elsewhere.
    """
    canonical = tmp_path / "repo"
    canonical.mkdir()
    env = tmp_path / "env"
    env.mkdir()
    (env / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    database = tmp_path / "k.db"
    con = sqlite3.connect(database)
    con.executescript(SCHEMA)
    _add(con, f"{canonical}/six.py", "tool", "same_bytes")
    _add(con, f"{env}/six.py", "tool", "same_bytes")
    con.commit()
    con.close()
    proposals = machine_proposals(
        load_candidates(database), canonical=canonical_index(database, str(canonical)),
        canonical_root=str(canonical))
    assert [p.rule for p in proposals] == [RULE_VIRTUALENV]


def test_the_remaining_rows_are_grouped_in_the_unit_they_are_asked_in(
        queue_db: Path, canonical_root: str) -> None:
    candidates = load_candidates(queue_db)
    proposals = machine_proposals(
        candidates, canonical=canonical_index(queue_db, canonical_root),
        canonical_root=canonical_root)
    groups = question_groups(candidates, {p.queue_id for p in proposals})
    assert sum(group.rows for group in groups) == len(candidates) - len(proposals)
    tools = next(g for g in groups if g.candidate_kind == "tool"
                 and g.directory.endswith("repo/tools"))
    assert tools.rows == 2
    assert (tools.coarse_part, tools.coarse_unit) == QUESTION_PARTS["tool"][0]
    assert (tools.fine_part, tools.fine_unit) == QUESTION_PARTS["tool"][1]


def test_coverage_answers_how_many_questions_reach_a_fraction(
        queue_db: Path, canonical_root: str) -> None:
    candidates = load_candidates(queue_db)
    proposals = machine_proposals(
        candidates, canonical=canonical_index(queue_db, canonical_root),
        canonical_root=canonical_root)
    groups = question_groups(candidates, {p.queue_id for p in proposals})
    assert coverage(groups, 1.0) == len(groups)
    assert 1 <= coverage(groups, 0.5) <= len(groups)
    with pytest.raises(ClassificationQueueError, match="fraction_out_of_range"):
        coverage(groups, 0)


def test_a_resolution_needs_a_signature(queue_db: Path) -> None:
    row = load_candidates(queue_db)[0]
    decision = [{"queue_id": row.queue_id, "to_status": STATUS_CLASSIFIED}]
    with pytest.raises(ClassificationQueueError, match="needs_an_actor"):
        apply_resolutions(queue_db, decision, decided_by="", reason="because")
    with pytest.raises(ClassificationQueueError, match="needs_a_reason"):
        apply_resolutions(queue_db, decision, decided_by="test", reason=" ")
    assert len(load_candidates(queue_db)) == 7, "a refused resolution still wrote"


def test_an_unknown_status_is_refused(queue_db: Path) -> None:
    row = load_candidates(queue_db)[0]
    with pytest.raises(ClassificationQueueError, match="unknown_status"):
        apply_resolutions(queue_db, [{"queue_id": row.queue_id, "to_status": "maybe"}],
                          decided_by="test", reason="why")


def test_applying_twice_never_overwrites_an_answer(queue_db: Path) -> None:
    row = load_candidates(queue_db)[0]
    decision = [{"queue_id": row.queue_id, "to_status": STATUS_INSTALLED_DEPENDENCY,
                 "rule": RULE_VIRTUALENV}]
    first = apply_resolutions(queue_db, decision, decided_by="test", reason="first")
    second = apply_resolutions(queue_db, decision, decided_by="other", reason="second")
    assert len(first["applied"]) == 1 and not first["skipped"]
    assert not second["applied"]
    assert second["skipped"][0]["why"] == f"already_{STATUS_INSTALLED_DEPENDENCY}"
    with sqlite3.connect(queue_db) as con:
        rows = con.execute("SELECT decided_by, reason FROM classification_resolutions"
                           " ORDER BY resolution_id").fetchall()
    assert rows == [("test", "first")], "the second call left a second audit row"


def test_a_coarse_only_answer_stays_visible_as_an_open_question(
        queue_db: Path, canonical_root: str) -> None:
    """A group answer must not close a per-file half it never touched."""
    candidates = load_candidates(queue_db)
    group = next(g for g in question_groups(candidates)
                 if g.candidate_kind == "tool" and g.directory.endswith("repo/tools"))
    apply_resolutions(
        queue_db,
        [{"queue_id": qid, "to_status": STATUS_CLASSIFIED,
          "rule": COVERS_COARSE_ONLY,
          "evidence": [{"kind": "open_question", "detail": "consumer per file"}]}
         for qid in group.queue_ids],
        decided_by="test", reason="repo tooling")
    report = summary(queue_db, canonical_root=canonical_root)
    assert report["fine_questions_still_open"] == group.rows
    assert report["rows_by_status"][STATUS_CLASSIFIED] == group.rows
    assert report["rows_by_status"][STATUS_PENDING] == len(candidates) - group.rows


def test_an_answer_covering_both_halves_leaves_nothing_open(
        queue_db: Path, canonical_root: str) -> None:
    group = next(g for g in question_groups(load_candidates(queue_db))
                 if g.candidate_kind == "idea")
    apply_resolutions(
        queue_db,
        [{"queue_id": qid, "to_status": STATUS_CLASSIFIED, "rule": COVERS_BOTH}
         for qid in group.queue_ids],
        decided_by="test", reason="one document, both halves answered")
    assert summary(queue_db, canonical_root=canonical_root)[
        "fine_questions_still_open"] == 0


def test_the_summary_works_before_any_resolution_table_exists(
        queue_db: Path, canonical_root: str) -> None:
    """The audit table is created on first write, so reading must not require it."""
    with sqlite3.connect(queue_db) as con:
        assert not con.execute(
            "SELECT name FROM sqlite_master WHERE name='classification_resolutions'"
        ).fetchall()
    report = summary(queue_db, canonical_root=canonical_root)
    assert report["resolutions_recorded"] == 0
    assert report["fine_questions_still_open"] == 0
    assert report["machine_resolvable"] == 3


def test_a_missing_database_is_refused_not_reported_as_an_empty_queue(
        tmp_path: Path) -> None:
    with pytest.raises(ClassificationQueueError, match="knowledge_database_missing"):
        load_candidates(tmp_path / "absent.db")


def test_reading_the_queue_never_writes(queue_db: Path, canonical_root: str) -> None:
    before = queue_db.read_bytes()
    candidates = load_candidates(queue_db)
    machine_proposals(candidates, canonical=canonical_index(queue_db, canonical_root),
                      canonical_root=canonical_root)
    question_groups(candidates)
    summary(queue_db, canonical_root=canonical_root)
    assert queue_db.read_bytes() == before
