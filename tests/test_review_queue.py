"""Tests for the door on the review queue.

Before this module the queue had no door: 34 records waiting, zero rows in
``project_transitions``, and ``transition_project`` called once in the whole
repository -- inside its own test. These tests pin the three things that make the
door safe to use, each of which was a real defect or a real refusal:

- containment direction, so a rejection propagates the right way,
- the asymmetry between rejecting and accepting,
- and that nothing propagates unless a caller asked for it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flujo.knowledge.project_ir import LearningStore
from flujo.knowledge.project_reconstruction import reconstruct, to_payload
from flujo.knowledge.reconstruction_adapter import project_irs_from_reconstruction
from flujo.knowledge.review_queue import (
    NOT_RECONSTRUCTED,
    PASS_PRUNE,
    PASS_RECOGNIZE,
    ReviewQueueError,
    decide,
    inherited_proposals,
    load_queue,
    summary,
)
from tests.test_project_reconstruction import make_index


@pytest.fixture()
def queue_db(tmp_path: Path) -> Path:
    """A real chain: index -> reconstruction -> Project IR -> store."""
    index = tmp_path / "index.sqlite"
    make_index(index)
    payload = to_payload(reconstruct(index, "DREFGIRA"))
    records = project_irs_from_reconstruction(payload, source_ref="fixture.json")
    database = tmp_path / "learning.db"
    store = LearningStore(database)
    for record in records:
        store.save_project(record)
    return database


def test_the_queue_knows_which_record_contains_which(queue_db: Path) -> None:
    """This is the whole reason the direction defect had to be fixed first.

    With the old inverted edges every record reported no container, so every
    rejection leverage was 1 and the queue looked flat when it is a tree.
    """
    items = {item.title: item for item in load_queue(queue_db)}
    assert items["DREFGIRA/SHOW"].parent_title == "DREFGIRA"
    assert items["DREFGIRA"].parent_title is None
    assert "DREFGIRA/SHOW" in items["DREFGIRA"].pending_descendants
    assert items["DREFGIRA"].rejection_leverage == 2
    assert items["DREFGIRA/SHOW"].rejection_leverage == 1


def test_a_rejection_is_inheritable_and_an_acceptance_is_not(queue_db: Path) -> None:
    """A container that is not a work cannot hold one; a work holds scrap."""
    container = next(i for i in load_queue(queue_db) if i.title == "DREFGIRA")
    assert inherited_proposals(container, "quarantined") == ["DREFGIRA/SHOW"]
    assert inherited_proposals(container, "contradicted") == ["DREFGIRA/SHOW"]
    assert inherited_proposals(container, "active") == []
    assert inherited_proposals(container, "verified") == []
    assert inherited_proposals(container, "candidate") == []


def test_nothing_propagates_unless_the_caller_named_it(queue_db: Path) -> None:
    container = next(i for i in load_queue(queue_db) if i.title == "DREFGIRA")
    decide(queue_db, container.project_id, "quarantined",
           reason="fixture", actor="test")
    remaining = {item.title for item in load_queue(queue_db)}
    assert "DREFGIRA/SHOW" in remaining, "a child was quarantined without being named"


def test_a_named_cascade_is_applied_and_says_it_was_inherited(queue_db: Path) -> None:
    container = next(i for i in load_queue(queue_db) if i.title == "DREFGIRA")
    result = decide(queue_db, container.project_id, "quarantined",
                    reason="an auto-save folder holds no delivered work",
                    actor="test", cascade_titles=["DREFGIRA/SHOW"])
    assert not result["refused"]
    assert len(result["applied"]) == 2
    assert load_queue(queue_db) == []

    import sqlite3
    with sqlite3.connect(queue_db) as con:
        reasons = [row[0] for row in con.execute(
            "SELECT reason FROM project_transitions ORDER BY rowid")]
        actors = {row[0] for row in con.execute(
            "SELECT actor FROM project_transitions")}
    assert actors == {"test"}
    assert any(reason.startswith("inherited from") for reason in reasons)


def test_a_decision_without_a_signature_is_refused(queue_db: Path) -> None:
    item = load_queue(queue_db)[0]
    with pytest.raises(ReviewQueueError, match="needs_a_reason"):
        decide(queue_db, item.project_id, "candidate", reason="  ", actor="test")
    with pytest.raises(ReviewQueueError, match="needs_an_actor"):
        decide(queue_db, item.project_id, "candidate", reason="because", actor="")
    assert len(load_queue(queue_db)) == 2, "a refused decision still wrote"


def test_accepting_demands_evidence_and_names_why(queue_db: Path) -> None:
    """The schema refuses this too; the door says which rule fired."""
    item = next(i for i in load_queue(queue_db) if i.title == "DREFGIRA")
    with pytest.raises(ReviewQueueError, match="active_requires_evidence"):
        decide(queue_db, item.project_id, "active", reason="looks real", actor="test")
    result = decide(queue_db, item.project_id, "active", reason="looks real",
                    actor="test",
                    evidence=[{"kind": "human_attestation", "detail": "delivered"}])
    assert result["applied"] == [{"project_id": item.project_id, "to_state": "active"}]


def test_an_impossible_transition_is_reported_not_swallowed(queue_db: Path) -> None:
    item = load_queue(queue_db)[0]
    result = decide(queue_db, item.project_id, "stale", reason="wrong door",
                    actor="test")
    assert result["applied"] == []
    assert result["refused"] and "transition_not_allowed" in result["refused"][0]["error"]


def test_the_two_passes_order_differently_and_both_are_deterministic(
        queue_db: Path) -> None:
    prune = [item.title for item in load_queue(queue_db, review_pass=PASS_PRUNE)]
    recognize = [item.title for item in load_queue(queue_db,
                                                   review_pass=PASS_RECOGNIZE)]
    assert prune == [item.title for item in load_queue(queue_db,
                                                       review_pass=PASS_PRUNE)]
    assert sorted(prune) == sorted(recognize)
    assert prune[0] == "DREFGIRA", "the prune pass leads with the largest subtree"
    with pytest.raises(ReviewQueueError, match="unknown_review_pass"):
        load_queue(queue_db, review_pass="guess")


def test_subtree_bytes_never_undercounts_the_direct_bytes(queue_db: Path) -> None:
    """A container can be far smaller than what it holds; both are reported."""
    for item in load_queue(queue_db):
        assert item.subtree_bytes >= item.bytes_total
    container = next(i for i in load_queue(queue_db) if i.title == "DREFGIRA")
    child = next(i for i in load_queue(queue_db) if i.title == "DREFGIRA/SHOW")
    assert container.subtree_bytes == container.bytes_total + child.bytes_total


def test_the_summary_counts_answers_not_records(queue_db: Path) -> None:
    items = load_queue(queue_db)
    report = summary(items)
    assert report["pending"] == 2
    assert report["roots"] == 1
    assert report["answers_to_clear_by_containment"] == 1
    assert report["max_rejection_leverage"] == 2


def test_a_record_without_a_reconstruction_is_not_called_unknown(tmp_path: Path) -> None:
    """``unknown`` is an epistemic label here and means something else."""
    from flujo.knowledge.project_ir import build_project_ir, inventory_source
    root = tmp_path / "incoming"
    root.mkdir()
    (root / "notes.md").write_text("seed\n", encoding="utf-8")
    database = tmp_path / "learning.db"
    LearningStore(database).save_project(build_project_ir(
        project_id="plain", title="Plain", source_root=root,
        artifacts=inventory_source(root), state="review_required"))
    item = load_queue(database)[0]
    assert item.role == NOT_RECONSTRUCTED
    assert item.pending_descendants == ()


def test_a_missing_database_is_refused_not_reported_as_an_empty_queue(
        tmp_path: Path) -> None:
    with pytest.raises(ReviewQueueError, match="learning_database_missing"):
        load_queue(tmp_path / "absent.db")


def test_the_queue_never_writes_to_the_database(queue_db: Path) -> None:
    before = queue_db.read_bytes()
    load_queue(queue_db)
    load_queue(queue_db, review_pass=PASS_RECOGNIZE)
    summary(load_queue(queue_db))
    assert queue_db.read_bytes() == before
