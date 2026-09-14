"""Pin the title-resolution defect fix (2026-08-24 audit).

Two write paths used to resolve a human- or JSON-supplied TITLE against
``project_records.title`` and treat the result as one specific project:

- ``tools/project_review.py`` ``_find`` (the ``decide`` command, plus its
  ``--cascade`` path via ``review_queue.decide``'s ``by_title`` dict), and
- ``project_context.py`` ``_resolve_project`` (``persist_context`` /
  ``link_context_to_project_ir``).

``project_records.title`` has no UNIQUE constraint in the DDL (plain
``title TEXT NOT NULL``) and is written by three different producers, so a
title lookup can return 0, 1 or N rows. The old code silently picked one
(first match, or "whichever dict entry was built last") and wrote to it.
These tests build two rows that share a title and assert the new resolvers
report the collision instead of guessing, and that every write path refuses
to write anything when it cannot resolve to exactly one project.

Each test below fails if the pre-fix behaviour (first-match / last-wins)
comes back, because that behaviour picks a project silently instead of
reporting Many or refusing to write.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

from flujo.knowledge.project_context import (
    link_context_to_project_ir,
    persist_context,
)
from flujo.knowledge.project_ir import LearningStore, build_project_ir
from flujo.knowledge.review_queue import (
    ReviewQueueError,
    decide,
    inherited_proposals,
    load_queue,
    resolve_title,
)
from flujo.substrate import AmbiguousResolutionError, Absent, Many, Unique, require_unique

# Same pattern used by tests/test_mak_delegar.py to reach a tools/ script that
# is not part of the installed package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import project_review  # noqa: E402


def _seed(database: Path, records) -> None:
    """Write project_records rows straight through the real schema/writer.

    ``records`` is an iterable of (project_id, title, state, relations).
    Using ``build_project_ir`` + ``LearningStore.save_project`` (the same
    writer every producer uses) rather than hand-rolling INSERTs is the point:
    the defect is about how a title is looked back UP out of this exact
    table, so the fixture must populate it the real way.
    """
    store = LearningStore(database)
    for project_id, title, state, relations in records:
        store.save_project(build_project_ir(
            project_id=project_id, title=title, source_root=database.parent,
            state=state, relations=relations))


def _states(database: Path) -> dict[str, str]:
    with sqlite3.connect(database) as con:
        return dict(con.execute("SELECT project_id, state FROM project_records"))


def _transition_count(database: Path) -> int:
    with sqlite3.connect(database) as con:
        return con.execute("SELECT COUNT(*) FROM project_transitions").fetchone()[0]


# --------------------------------------------------------------- resolve_title


def test_two_same_titled_rows_resolve_as_many_not_a_silent_pick(tmp_path: Path) -> None:
    database = tmp_path / "learning.db"
    _seed(database, [
        ("proj-a", "Duplicate Title", "review_required", ()),
        ("proj-b", "Duplicate Title", "review_required", ()),
    ])
    items = load_queue(database)
    resolution = resolve_title(items, "Duplicate Title")
    assert isinstance(resolution, Many)
    assert resolution.k == 2
    assert {c.project_id for c in resolution.candidates} == {"proj-a", "proj-b"}
    with pytest.raises(AmbiguousResolutionError):
        require_unique(resolution, claim="decide:Duplicate Title")


def test_one_row_resolves_unique_and_the_decide_path_still_works(tmp_path: Path) -> None:
    database = tmp_path / "learning.db"
    _seed(database, [("proj-a", "Solo Title", "review_required", ())])
    items = load_queue(database)
    resolution = resolve_title(items, "Solo Title")
    assert isinstance(resolution, Unique)
    item = require_unique(resolution, claim="decide:Solo Title")
    result = decide(database, item.project_id, "candidate", reason="fixture", actor="test")
    assert result["applied"] == [{"project_id": "proj-a", "to_state": "candidate"}]
    assert _states(database) == {"proj-a": "candidate"}


def test_a_title_matching_nothing_is_absent_not_a_crash(tmp_path: Path) -> None:
    database = tmp_path / "learning.db"
    _seed(database, [("proj-a", "Real Title", "review_required", ())])
    items = load_queue(database)
    resolution = resolve_title(items, "Nowhere To Be Found")
    assert isinstance(resolution, Absent)
    # require_unique still names a remedy rather than raising a bare KeyError
    # or similar internal exception -- the operator gets an explanation.
    with pytest.raises(AmbiguousResolutionError, match="absent"):
        require_unique(resolution, claim="decide:Nowhere To Be Found")


# ------------------------------------------------------- the CLI decide path


def test_ambiguous_target_via_cli_show_is_reported_not_crashed(
        tmp_path: Path, capsys) -> None:
    database = tmp_path / "learning.db"
    _seed(database, [
        ("proj-a", "Duplicate Title", "review_required", ()),
        ("proj-b", "Duplicate Title", "review_required", ()),
    ])
    rc = project_review.main(["--db", str(database), "show", "Duplicate Title"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "Traceback" not in captured.err
    assert "proj-a" in captured.err and "proj-b" in captured.err
    assert "ambiguous" in captured.err


def test_absent_target_via_cli_is_a_clear_error_not_a_crash(
        tmp_path: Path, capsys) -> None:
    database = tmp_path / "learning.db"
    _seed(database, [("proj-a", "Real Title", "review_required", ())])
    rc = project_review.main(["--db", str(database), "show", "Nowhere"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "Traceback" not in captured.err
    assert "not_pending" in captured.err


def test_LOAD_BEARING_ambiguous_decide_target_writes_nothing(
        tmp_path: Path, capsys) -> None:
    """The audit's headline case: two same-titled rows, one 'decide' call.

    Before the fix this silently mutated whichever row the broken resolver
    returned first. After the fix it must write NOTHING and exit non-zero.
    """
    database = tmp_path / "learning.db"
    _seed(database, [
        ("proj-a", "Duplicate Title", "review_required", ()),
        ("proj-b", "Duplicate Title", "review_required", ()),
    ])
    before_states = _states(database)
    assert before_states == {"proj-a": "review_required", "proj-b": "review_required"}

    rc = project_review.main([
        "--db", str(database), "decide", "Duplicate Title",
        "--to", "quarantined", "--reason", "audit fixture", "--actor", "tester",
    ])
    captured = capsys.readouterr()

    assert rc != 0, "an ambiguous decide target must not exit 0"
    assert "Traceback" not in captured.err
    assert _transition_count(database) == 0, "a transition row was written for an ambiguous target"
    assert _states(database) == before_states, "a project's state changed for an ambiguous target"


def test_project_id_still_resolves_uniquely_when_titles_collide(
        tmp_path: Path, capsys) -> None:
    """The escape hatch: project_id is the PRIMARY KEY and stays unambiguous."""
    database = tmp_path / "learning.db"
    _seed(database, [
        ("proj-a", "Duplicate Title", "review_required", ()),
        ("proj-b", "Duplicate Title", "review_required", ()),
    ])
    rc = project_review.main([
        "--db", str(database), "decide", "proj-a",
        "--to", "candidate", "--reason", "audit fixture", "--actor", "tester",
    ])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert _states(database) == {"proj-a": "candidate", "proj-b": "review_required"}
    assert _transition_count(database) == 1


# --------------------------------------------------------------- the cascade


def test_dry_run_over_an_ambiguous_cascade_title_shows_the_ambiguity(
        tmp_path: Path, capsys) -> None:
    database = tmp_path / "learning.db"
    _seed(database, [
        ("container", "Container", "review_required", ()),
        ("child-a", "Child", "review_required",
         [{"subject": "child-a", "predicate": "contained_by",
           "object": "reconstruction://scope/Container"}]),
        ("child-b", "Child", "review_required", ()),
    ])
    rc = project_review.main([
        "--db", str(database), "decide", "container", "--to", "quarantined",
        "--reason", "audit fixture", "--actor", "tester", "--cascade", "--dry-run",
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert '"ambiguous": true' in captured.out
    assert "child-a" in captured.out and "child-b" in captured.out
    assert _transition_count(database) == 0


def test_cascade_with_one_ambiguous_title_refuses_the_WHOLE_cascade(
        tmp_path: Path) -> None:
    """Requirement 4: a partial cascade is worse than none.

    Two structural children of ``container`` -- Child1 is unambiguous, Child2
    collides with an unrelated row that merely happens to share its title.
    The whole cascade (including the container's own transition) must be
    refused: not "quarantine Child1, skip Child2".
    """
    database = tmp_path / "learning.db"
    _seed(database, [
        ("container", "Container", "review_required", ()),
        ("child-1", "Child1", "review_required",
         [{"subject": "child-1", "predicate": "contained_by",
           "object": "reconstruction://scope/Container"}]),
        ("child-2", "Child2", "review_required",
         [{"subject": "child-2", "predicate": "contained_by",
           "object": "reconstruction://scope/Container"}]),
        ("child-2-collision", "Child2", "review_required", ()),
    ])
    items = load_queue(database)
    container_item = next(i for i in items if i.title == "Container")
    assert set(container_item.pending_descendants) == {"Child1", "Child2"}
    cascade_titles = inherited_proposals(container_item, "quarantined")

    before_states = _states(database)
    with pytest.raises(ReviewQueueError, match="cascade_ambiguous"):
        decide(database, container_item.project_id, "quarantined",
              reason="audit fixture", actor="tester", cascade_titles=cascade_titles)

    assert _transition_count(database) == 0, "no transition rows at all, not some"
    assert _states(database) == before_states, "not even the container's own state may move"


def test_cascade_with_ambiguous_parent_title_refuses_before_crossing_subtrees(
        tmp_path: Path) -> None:
    """A project_id is enough for a direct decision, not for a title-built tree.

    ``load_queue`` uses the declared title in ``contained_by`` to reconstruct
    the pending tree. If two containers share that title, their children are
    indistinguishable at this layer. A cascade must therefore abstain before
    applying children from both subtrees to the one project_id.
    """
    database = tmp_path / "learning.db"
    _seed(database, [
        ("container-a", "Same Container", "review_required", ()),
        ("container-b", "Same Container", "review_required", ()),
        ("child-a", "Child A", "review_required", [{
            "subject": "child-a", "predicate": "contained_by",
            "object": "reconstruction://scope/Same Container",
        }]),
        ("child-b", "Child B", "review_required", [{
            "subject": "child-b", "predicate": "contained_by",
            "object": "reconstruction://scope/Same Container",
        }]),
    ])
    items = load_queue(database)
    container = next(item for item in items if item.project_id == "container-a")
    assert set(inherited_proposals(container, "quarantined")) == {"Child A", "Child B"}

    before_states = _states(database)
    with pytest.raises(ReviewQueueError, match="cascade_ambiguous: parent"):
        decide(database, "container-a", "quarantined", reason="audit fixture",
               actor="tester", cascade_titles=inherited_proposals(container, "quarantined"))

    assert _transition_count(database) == 0
    assert _states(database) == before_states


# ------------------------------------------------------------ project_context


def _context_payload(project_entry: dict) -> dict:
    return {
        "schema": "mak-project-context-v1",
        "context_id": "ctx-test",
        "title": "Test context",
        "entities": [],
        "sources": [],
        "relations": [],
        "projects": [project_entry],
    }


def test_project_context_ambiguous_title_writes_nothing(tmp_path: Path) -> None:
    database = tmp_path / "knowledge.db"
    _seed(database, [
        ("ctx-a", "Ambiguous Project", "review_required", ()),
        ("ctx-b", "Ambiguous Project", "review_required", ()),
    ])
    with sqlite3.connect(database) as con:
        before_ir = dict(con.execute(
            "SELECT project_id, ir_json FROM project_records ORDER BY project_id"))

    payload = _context_payload({
        "title": "Ambiguous Project", "role": "visual_project",
        "service_role": "test_role", "status": "review_required", "entity_ids": {},
    })

    result = persist_context(database, payload)
    assert result["projects"][0]["resolved"] is False
    assert result["projects"][0]["ambiguous"] is True
    assert {c["project_id"] for c in result["projects"][0]["candidates"]} == {"ctx-a", "ctx-b"}
    with sqlite3.connect(database) as con:
        assert con.execute("SELECT COUNT(*) FROM project_contexts").fetchone()[0] == 0

    updates = link_context_to_project_ir(database, payload)
    assert len(updates) == 1
    assert updates[0]["resolved"] is False
    assert updates[0]["ambiguous"] is True

    with sqlite3.connect(database) as con:
        after_ir = dict(con.execute(
            "SELECT project_id, ir_json FROM project_records ORDER BY project_id"))
    assert after_ir == before_ir, "an ambiguous title must not mutate either project's IR"


def test_project_context_project_id_still_resolves_when_titles_collide(
        tmp_path: Path) -> None:
    database = tmp_path / "knowledge.db"
    _seed(database, [
        ("ctx-a", "Ambiguous Project", "review_required", ()),
        ("ctx-b", "Ambiguous Project", "review_required", ()),
    ])
    payload = _context_payload({
        "project_id": "ctx-a", "title": "Ambiguous Project", "role": "visual_project",
        "service_role": "test_role", "status": "review_required", "entity_ids": {},
    })
    result = persist_context(database, payload)
    assert result["projects"][0]["resolved"] is True
    assert result["projects"][0]["project_id"] == "ctx-a"
    with sqlite3.connect(database) as con:
        assert con.execute(
            "SELECT COUNT(*) FROM project_contexts WHERE project_id='ctx-a'"
        ).fetchone()[0] == 1
