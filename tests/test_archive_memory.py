"""Focused tests for the strict observer -> archive-memory boundary."""

from __future__ import annotations

import copy
import hashlib
import os
import sqlite3
from pathlib import Path

import pytest

from flujo.knowledge.archive_memory import (
    ArchiveMemoryError,
    ingest_observation_batch,
    list_artifacts,
    list_archives,
    list_observations,
    list_snapshots,
    list_transformations,
    replay_snapshot,
)
from flujo.knowledge.archive_observer import observe_archive
from flujo.knowledge.project_ir import LearningStore, inspect_learning_target


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_migration_is_additive_and_keeps_legacy_rows(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite"
    store = LearningStore(database)
    store.ensure_schema()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO archive_memory_archives(archive_id,source_root_ref,created_at,updated_at) VALUES (?,?,?,?)",
            ("legacy", "archive:legacy", "t0", "t0"),
        )
        connection.execute(
            "INSERT INTO archive_memory_artifacts(archive_id,artifact_id,content_sha256,first_seen_at) VALUES (?,?,?,?)",
            ("legacy", "artifact:legacy", "sha256:" + "a" * 64, "t0"),
        )
    store.ensure_schema()
    report = inspect_learning_target(database)
    assert report["materialization"] == "already_applied"
    assert report["missing"] == []
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "archive_memory_v2_artifacts" in tables
        assert connection.execute(
            "SELECT COUNT(*) FROM archive_memory_artifacts WHERE archive_id='legacy'"
        ).fetchone()[0] == 1


def test_duplicate_bytes_are_distinct_physical_entities_and_reingest_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    root.mkdir()
    (root / "one.bin").write_bytes(b"same")
    (root / "two.bin").write_bytes(b"same")
    (root / "folder").mkdir()
    (root / "link").symlink_to("one.bin")
    database = tmp_path / "learning.sqlite"
    batch = observe_archive(root, "archive-a")

    first = ingest_observation_batch(database, batch)
    repeat = ingest_observation_batch(database, batch)

    assert first["input_schema"] == "mak-archive-observation-batch-v1"
    assert first["inserted"] == {
        "archive": 1, "snapshot": 1, "artifacts": 4,
        "states": 4, "observations": len(batch["observations"]), "events": 0,
    }
    assert all(value == 0 for value in repeat["inserted"].values())
    states = list_artifacts(database, "archive-a", batch["snapshot_id"])
    assert len(list_artifacts(database, "archive-a")) == 4
    assert len(states) == 4
    assert len({row["artifact_id"] for row in states}) == 4
    assert [row["content_sha256"] for row in states].count(_sha(b"same")) == 2
    assert sum(row["content_sha256"] is None for row in states) == 2
    assert list_transformations(database, "archive-a", snapshot_id=batch["snapshot_id"]) == []
    assert len(list_archives(database)) == 1
    assert len(list_snapshots(database, "archive-a")) == 1
    assert all(row["status"] == "candidate" for row in list_observations(database, "archive-a"))


def test_touch_same_semantic_snapshot_keeps_first_mtime_and_replay(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    root.mkdir()
    path = root / "touch.bin"
    path.write_bytes(b"touch")
    database = tmp_path / "learning.sqlite"
    first_batch = observe_archive(root, "archive-a")
    ingest_observation_batch(database, first_batch)
    first_mtime = next(item["mtime_ns"] for item in first_batch["artifacts"] if item["relative_path"] == "touch.bin")
    replay_one = replay_snapshot(database, archive_id="archive-a", snapshot_id=first_batch["snapshot_id"])

    touched_mtime = os.stat(path).st_mtime_ns + 1000
    os.utime(path, ns=(touched_mtime, touched_mtime))
    touched_batch = observe_archive(root, "archive-a", prior=first_batch)
    repeat = ingest_observation_batch(database, touched_batch)
    replay_two = replay_snapshot(database, archive_id="archive-a", snapshot_id=first_batch["snapshot_id"])

    assert touched_batch["snapshot_id"] == first_batch["snapshot_id"]
    assert all(value == 0 for value in repeat["inserted"].values())
    assert replay_one["replay_hash"] == replay_two["replay_hash"]
    assert list_artifacts(database, "archive-a", first_batch["snapshot_id"])[0]["mtime_ns"] == first_mtime


def test_same_physical_artifact_gets_new_state_when_content_changes(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    root.mkdir()
    path = root / "scene.blend"
    path.write_bytes(b"old")
    database = tmp_path / "learning.sqlite"
    first_batch = observe_archive(root, "archive-a")
    ingest_observation_batch(database, first_batch)
    path.write_bytes(b"new")
    second_batch = observe_archive(root, "archive-a", prior=first_batch)
    result = ingest_observation_batch(database, second_batch)

    first_artifact = next(item for item in first_batch["artifacts"] if item["relative_path"] == "scene.blend")
    second_artifact = next(item for item in second_batch["artifacts"] if item["relative_path"] == "scene.blend")
    assert first_artifact["artifact_id"] == second_artifact["artifact_id"]
    assert first_batch["snapshot_id"] != second_batch["snapshot_id"]
    assert result["inserted"]["artifacts"] == 0
    assert result["inserted"]["states"] == 1
    assert len(list_artifacts(database, "archive-a")) == 1
    assert list_artifacts(database, "archive-a", second_batch["snapshot_id"])[0]["content_sha256"] == _sha(b"new")


def test_observer_valid_archive_id_with_slash_is_accepted(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    root.mkdir()
    (root / "x.bin").write_bytes(b"x")
    database = tmp_path / "learning.sqlite"
    batch = observe_archive(root, "artist/edition\\one")

    ingest_observation_batch(database, batch)

    assert [row["archive_id"] for row in list_archives(database)] == ["artist/edition\\one"]


def test_invalid_observer_batch_fails_closed_before_persistence(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    root.mkdir()
    (root / "one.bin").write_bytes(b"same")
    (root / "two.bin").write_bytes(b"same")
    database = tmp_path / "learning.sqlite"
    invalid = copy.deepcopy(observe_archive(root, "archive-a"))
    invalid["observations"][0]["artifact_refs"] = ["archive-artifact:not-real"]

    with pytest.raises(ArchiveMemoryError, match="batch_invalid:.*unknown artifact"):
        ingest_observation_batch(database, invalid)
    assert not database.exists()
