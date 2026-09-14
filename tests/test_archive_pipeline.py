"""Real observer-to-memory integration tests (no handcrafted observer schema)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flujo.knowledge.archive_memory import (
    ingest_observation_batch,
    list_artifacts,
    list_archives,
    replay_snapshot,
)
from flujo.knowledge.archive_observer import observe_archive, serialize_batch, validate_batch


def _by_path(batch: dict, path: str) -> dict:
    return next(item for item in batch["artifacts"] if item["relative_path"] == path)


def test_observe_ingest_reingest_change_and_replay(tmp_path: Path) -> None:
    root = tmp_path / "artist-archive"
    root.mkdir()
    (root / "renders").mkdir()
    (root / "renders" / "one.bin").write_bytes(b"same")
    (root / "renders" / "two.bin").write_bytes(b"same")
    (root / "renders" / "mutable.bin").write_bytes(b"before")
    (root / "renders" / "link.bin").symlink_to("one.bin")
    database = tmp_path / "learning.sqlite"

    first_batch = observe_archive(root, "artist-a")
    first = ingest_observation_batch(database, first_batch)
    exact_repeat = ingest_observation_batch(database, first_batch)

    assert first["batch_schema"] == "mak-archive-observation-batch-v1"
    assert first["inserted"]["artifacts"] == len(first_batch["artifacts"])
    assert first["inserted"]["states"] == len(first_batch["artifacts"])
    assert all(value == 0 for value in exact_repeat["inserted"].values())
    first_snapshot = first_batch["snapshot_id"]
    touched_path = root / "renders" / "one.bin"
    touched_mtime = os.stat(touched_path).st_mtime_ns + 1000
    os.utime(touched_path, ns=(touched_mtime, touched_mtime))
    touched_batch = observe_archive(root, "artist-a", prior=first_batch)
    assert touched_batch["snapshot_id"] == first_snapshot
    touch_repeat = ingest_observation_batch(database, touched_batch)
    assert all(value == 0 for value in touch_repeat["inserted"].values())
    first_states = list_artifacts(database, "artist-a", first_snapshot)
    assert len(first_states) == len(first_batch["artifacts"])
    assert len({row["artifact_id"] for row in first_states}) == len(first_states)
    one = _by_path(first_batch, "renders/one.bin")
    two = _by_path(first_batch, "renders/two.bin")
    assert one["content_id"] == two["content_id"]
    assert one["artifact_id"] != two["artifact_id"]
    link = _by_path(first_batch, "renders/link.bin")
    assert link["sha256"] is None
    link_state = next(row for row in first_states if row["relative_path"] == "renders/link.bin")
    assert json.loads(link_state["references_json"]) == [link["artifact_ref"]]

    (root / "renders" / "mutable.bin").write_bytes(b"after")
    second_batch = observe_archive(root, "artist-a", prior=first_batch)
    second = ingest_observation_batch(database, second_batch)
    mutable_first = _by_path(first_batch, "renders/mutable.bin")
    mutable_second = _by_path(second_batch, "renders/mutable.bin")
    assert first_snapshot != second_batch["snapshot_id"]
    assert mutable_first["artifact_id"] == mutable_second["artifact_id"]
    assert second["inserted"]["artifacts"] == 0
    assert second["inserted"]["states"] >= 1
    assert len(list_artifacts(database, "artist-a", second_batch["snapshot_id"])) == len(second_batch["artifacts"])
    assert _by_path(second_batch, "renders/mutable.bin")["content_id"] != mutable_first["content_id"]

    second_archive_batch = observe_archive(root, "artist-b")
    ingest_observation_batch(database, second_archive_batch)
    assert len(list_archives(database)) == 2
    assert len(list_artifacts(database, "artist-b")) == len(second_archive_batch["artifacts"])
    assert {
        row["artifact_id"] for row in list_artifacts(database, "artist-a")
    }.isdisjoint({row["artifact_id"] for row in list_artifacts(database, "artist-b")})

    replay_one = replay_snapshot(database, archive_id="artist-a", snapshot_id=first_snapshot)
    replay_two = replay_snapshot(database, archive_id="artist-a", snapshot_id=first_snapshot)
    assert replay_one["replay_hash"] == replay_two["replay_hash"]
    assert validate_batch(replay_one["snapshot"]) is True
    assert serialize_batch(replay_one["snapshot"]) == serialize_batch(replay_two["snapshot"])
