#!/usr/bin/env python3
"""tests/test_open_episode_state.py -- attention must track work, not history.

Measured on 2026-08-21: `operational_status` built its actionable attention list
from `SELECT status, COUNT(*) FROM project_episodes GROUP BY status`, which
counts every episode ever recorded. Episodes are append-only by design, so an
item like "3 episode(s) need evidence" could never be cleared by doing the work
its own next_action asked for ("attach verifiable evidence, then run the
validator again"): recording the verified execution left the old row counted and
the operator lost the difference between "there is work" and "the work was
done".

The defect was latent rather than active -- at the time all three
`needs_evidence` rows were the latest episode of their project, so the count was
still true -- which is exactly why it had to be fixed before closing them, not
after. After the repair the same ledger reported `needs_evidence` falling from
3 to 1 once two prepared consumers were actually executed and recorded.

Rule pinned here: a non-verified episode stays open only while its project has
no LATER accepted episode. History stays intact and visible in `episodes`; only
the attention list reads the open state.
"""
from __future__ import annotations

import sqlite3

import pytest

from flujo.knowledge.learning_policy import VERIFIED_OUTCOME_STATUSES
from flujo.knowledge.project_api import _open_episode_states


def _db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE project_episodes (project_id TEXT, status TEXT)")
    con.executemany("INSERT INTO project_episodes VALUES (?, ?)", rows)
    return con


def test_a_later_accepted_episode_closes_an_earlier_open_one():
    con = _db([("p1", "needs_evidence"), ("p1", "verified")])
    assert _open_episode_states(con) == {}


def test_an_open_episode_after_the_accepted_one_stays_open():
    """Order matters: finishing once does not excuse the next open step."""
    con = _db([("p1", "verified"), ("p1", "needs_evidence")])
    assert _open_episode_states(con) == {"needs_evidence": 1}


def test_projects_do_not_close_each_other():
    con = _db([("p1", "needs_evidence"), ("p2", "verified")])
    assert _open_episode_states(con) == {"needs_evidence": 1}


def test_accepted_states_are_never_counted_as_open():
    con = _db([("p1", status) for status in sorted(VERIFIED_OUTCOME_STATUSES)])
    assert _open_episode_states(con) == {}


def test_every_open_state_is_reported_with_its_own_name():
    con = _db([("p1", "needs_evidence"), ("p2", "abstained"), ("p3", "failed")])
    assert _open_episode_states(con) == {
        "needs_evidence": 1, "abstained": 1, "failed": 1}


def test_status_is_compared_case_insensitively():
    con = _db([("p1", "needs_evidence"), ("p1", "VERIFIED")])
    assert _open_episode_states(con) == {}


def test_an_empty_ledger_reports_nothing_open():
    assert _open_episode_states(_db([])) == {}


def test_the_open_set_is_the_recorder_set_not_a_second_copy():
    """Two lists of "what counts as done" is how the ledger would drift."""
    from flujo.knowledge import project_api

    assert project_api.VERIFIED_EPISODE_STATUSES is VERIFIED_OUTCOME_STATUSES


def test_the_real_ledger_keeps_history_while_reporting_open_work():
    """The live database must still expose both views, not one."""
    from pathlib import Path

    from flujo.knowledge.project_api import operational_status

    db = Path(__file__).resolve().parents[1] / "data" / "mak_knowledge.db"
    if not db.is_file():
        pytest.skip("local learning database is not present in this clone")
    status = operational_status(str(db))
    items = {item["id"]: item for item in (status.get("attention") or [])}
    open_evidence = items.get("episodes:needs_evidence")
    if open_evidence is not None:
        # Whatever the number is, it must not exceed the historical total.
        con = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True)
        total = con.execute(
            "SELECT COUNT(*) FROM project_episodes WHERE status='needs_evidence'"
        ).fetchone()[0]
        con.close()
        reported = int(open_evidence["reason"].split()[0])
        assert reported <= total, (
            f"attention reports {reported} open but history holds {total}")


def test_an_explicit_successor_replaces_only_its_parent_in_the_open_projection():
    con = sqlite3.connect(":memory:")
    con.execute(
        "CREATE TABLE project_episodes ("
        "episode_id TEXT, project_id TEXT, phase TEXT, status TEXT, "
        "parent_episode_id TEXT)"
    )
    con.executemany(
        "INSERT INTO project_episodes VALUES (?, ?, ?, ?, ?)",
        [
            ("old", "p1", "production", "needs_evidence", None),
            ("new", "p1", "production", "needs_evidence", "old"),
        ],
    )

    assert _open_episode_states(con) == {"needs_evidence": 1}
