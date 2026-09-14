from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.archive_observer import (
    ArchiveObservationValidationError,
    deserialize_batch,
    observe_archive,
    serialize_batch,
    validate_batch,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "tools" / "archive_observer.py"


def _artifact(batch: dict, relative_path: str) -> dict:
    return next(item for item in batch["artifacts"] if item["relative_path"] == relative_path)


def test_identical_relative_content_replays_across_absolute_roots(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        (root / "nested").mkdir(parents=True)
        (root / "nested" / "same.txt").write_bytes(b"same\n")
        (root / "root.bin").write_bytes(b"bytes")
    left = observe_archive(first, "archive-a")
    right = observe_archive(second, "archive-a")
    assert left["snapshot_id"] == right["snapshot_id"]
    left_semantic = json.loads(serialize_batch(left))
    right_semantic = json.loads(serialize_batch(right))
    for batch in (left_semantic, right_semantic):
        for artifact in batch["artifacts"]:
            artifact["mtime_ns"] = None
    assert left_semantic == right_semantic


def test_archive_ids_isolate_physical_artifact_ids_but_not_content_ids(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"duplicate")
    left = observe_archive(tmp_path, "tenant-a")
    right = observe_archive(tmp_path, "tenant-b")
    left_file = _artifact(left, "a.bin")
    right_file = _artifact(right, "a.bin")
    assert left_file["artifact_id"] != right_file["artifact_id"]
    assert left_file["physical_id"] != right_file["physical_id"]
    assert left_file["content_id"] == right_file["content_id"]


def test_exact_duplicates_are_distinct_and_emit_candidate(tmp_path: Path) -> None:
    (tmp_path / "one.dat").write_bytes(b"same")
    (tmp_path / "two.dat").write_bytes(b"same")
    batch = observe_archive(tmp_path, "archive")
    files = [_artifact(batch, "one.dat"), _artifact(batch, "two.dat")]
    assert files[0]["artifact_id"] != files[1]["artifact_id"]
    duplicate = next(item for item in batch["observations"] if item["observation_type"] == "exact_duplicate_candidate")
    assert duplicate["status"] == "candidate"
    assert set(duplicate["artifact_refs"]) == {item["artifact_ref"] for item in files}


def test_numbered_sequences_sidecars_and_manifests_are_candidates(tmp_path: Path) -> None:
    (tmp_path / "frame_001.png").write_bytes(b"1")
    (tmp_path / "frame_002.png").write_bytes(b"2")
    (tmp_path / "photo.jpg").write_bytes(b"jpg")
    (tmp_path / "photo.jpg.xmp").write_bytes(b"xmp")
    (tmp_path / "manifest.json").write_bytes(b"{}")
    types = {item["observation_type"] for item in observe_archive(tmp_path, "archive")["observations"]}
    assert {"numbered_sequence_candidate", "sidecar_candidate", "manifest_candidate"} <= types


def test_symlink_is_observed_without_following(tmp_path: Path) -> None:
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "inside.txt").write_bytes(b"inside")
    (tmp_path / "link").symlink_to(tmp_path / "target", target_is_directory=True)
    batch = observe_archive(tmp_path, "archive")
    assert _artifact(batch, "link")["kind"] == "symlink"
    assert not any(item["relative_path"].startswith("link/") for item in batch["artifacts"])


def test_empty_root_is_valid_and_deterministic(tmp_path: Path) -> None:
    first = observe_archive(tmp_path, "empty")
    second = observe_archive(tmp_path, "empty")
    assert first["artifacts"] == []
    assert first["observations"] == []
    assert first["snapshot_id"] == second["snapshot_id"]


def test_hash_error_is_an_observation_when_read_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "blocked.bin"
    path.write_bytes(b"bytes")
    real_open = open

    def blocked_open(name, *args, **kwargs):
        if os.fspath(name) == os.fspath(path):
            raise PermissionError("blocked")
        return real_open(name, *args, **kwargs)

    monkeypatch.setattr("builtins.open", blocked_open)
    batch = observe_archive(tmp_path, "archive")
    item = _artifact(batch, "blocked.bin")
    assert item["availability"] == "unreadable"
    assert item["sha256"] is None
    assert any(item["observation_type"] == "failure_candidate" for item in batch["observations"])


def test_incremental_added_changed_unchanged_missing(tmp_path: Path) -> None:
    (tmp_path / "same.txt").write_bytes(b"same")
    (tmp_path / "change.txt").write_bytes(b"old")
    (tmp_path / "remove.txt").write_bytes(b"remove")
    prior = observe_archive(tmp_path, "archive")
    (tmp_path / "change.txt").write_bytes(b"new")
    (tmp_path / "remove.txt").unlink()
    (tmp_path / "add.txt").write_bytes(b"add")
    current = observe_archive(tmp_path, "archive", prior=prior)
    assert current["change_set"] == {
        "added": ["add.txt"],
        "changed": ["change.txt"],
        "unchanged": ["same.txt"],
        "missing": ["remove.txt"],
    }
    assert prior["artifacts"][-1]["relative_path"] == "same.txt"


def test_replay_json_is_deterministic_and_validates_round_trip(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_bytes(b"content")
    batch = observe_archive(tmp_path, "archive")
    encoded = serialize_batch(batch)
    decoded = deserialize_batch(encoded)
    assert decoded == batch
    assert serialize_batch(decoded) == encoded
    assert validate_batch(decoded) is True


def test_malformed_prior_and_duplicate_refs_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_bytes(b"content")
    with pytest.raises(ArchiveObservationValidationError):
        observe_archive(tmp_path, "archive", prior={"schema": "wrong"})
    batch = observe_archive(tmp_path, "archive")
    malformed = json.loads(serialize_batch(batch))
    malformed["observations"].append(
        {
            "observation_id": "observation:bad",
            "observation_type": "failure_candidate",
            "status": "candidate",
            "artifact_refs": [batch["artifacts"][0]["artifact_ref"]] * 2,
            "evidence": {},
        }
    )
    with pytest.raises(ArchiveObservationValidationError):
        validate_batch(malformed)
    with pytest.raises(ArchiveObservationValidationError):
        deserialize_batch('{"schema":"mak-archive-observation-batch-v1","schema":"duplicate"}')


def test_max_files_bounds_file_like_entries(tmp_path: Path) -> None:
    for name in ("a.txt", "b.txt", "c.txt"):
        (tmp_path / name).write_bytes(name.encode())
    batch = observe_archive(tmp_path, "archive", max_files=2)
    file_like = [item for item in batch["artifacts"] if item["kind"] == "file"]
    assert len(file_like) == 2
    assert any(item["observation_type"] == "limit_reached" for item in batch["observations"])


def test_source_bytes_and_mtimes_are_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "source.dat"
    path.write_bytes(b"immutable")
    before_bytes = path.read_bytes()
    before_mtime = path.stat().st_mtime_ns
    observe_archive(tmp_path, "archive")
    assert path.read_bytes() == before_bytes
    assert path.stat().st_mtime_ns == before_mtime


def test_cli_stdout_and_output_are_explicit(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("cli", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CLI), str(tmp_path), "--archive-id", "cli-archive"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["schema"] == "mak-archive-observation-batch-v1"
    output = tmp_path / "batch.json"
    result_with_output = subprocess.run(
        [sys.executable, str(CLI), "--root", str(tmp_path), "--archive-id", "cli-archive", "--output", str(output)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result_with_output.returncode == 0
    assert result_with_output.stdout == ""
    assert json.loads(output.read_text(encoding="utf-8"))["schema"] == "mak-archive-observation-batch-v1"
