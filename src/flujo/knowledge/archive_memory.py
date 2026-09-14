"""Append-only materialisation of the physical archive observer contract.

The observer is deliberately the only filesystem reader.  This module stores
its canonical ``mak-archive-observation-batch-v1`` batches in the existing
``LearningStore``.  The v2 tables are additive because the former tables used
content as artifact identity and therefore could not represent two physical
paths containing the same bytes.

The important boundary is:

* ``artifact_id``/``physical_id``/``artifact_ref`` identify one physical path
  within one archive and remain stable across snapshots;
* bytes and all physical attributes live in an immutable snapshot state;
* ``content_sha256`` and ``content_id`` are nullable observations of bytes,
  never the identity of a physical artifact;
* observer ``observations`` remain candidates with their evidence; this layer
  does not assert an artistic relation;
* ``change_set`` is retained as observer diagnostics only and is never turned
  into a fact or transformation event.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .archive_observer import ArchiveObservationError, validate_batch
from .project_ir import LearningStore, now_iso, stable_json


SCHEMA = "mak-archive-memory-v2"
BATCH_SCHEMA = "mak-archive-observation-batch-v1"
HASH_RE = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")


class ArchiveMemoryError(ValueError):
    """Invalid, conflicting or incomplete archive-memory input."""


def _text(value: Any, field: str, *, required: bool = True, limit: int = 1000) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ArchiveMemoryError(f"{field}_required")
    return result[:limit]


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArchiveMemoryError(f"{field}_must_be_object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ArchiveMemoryError(f"{field}_must_be_list")
    return value


def _json(value: Any) -> str:
    return stable_json(value if value is not None else {})


def _decode(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _database_path(database: str | Path | LearningStore) -> Path:
    if isinstance(database, LearningStore):
        return database.database
    return Path(database).expanduser()


def _readonly(database: str | Path | LearningStore) -> sqlite3.Connection:
    path = _database_path(database)
    if not path.is_file():
        raise ArchiveMemoryError("database_not_found")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _archive_id(batch: Mapping[str, Any]) -> str:
    archive_id = batch.get("archive_id")
    if not isinstance(archive_id, str) or not archive_id or archive_id != archive_id.strip():
        raise ArchiveMemoryError("archive_id_invalid")
    return archive_id


def _optional_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ArchiveMemoryError(f"{field}_must_be_integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ArchiveMemoryError(f"{field}_must_be_integer") from exc


def _optional_sha256(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    raw = _text(value, field, limit=80)
    match = HASH_RE.fullmatch(raw)
    if not match:
        raise ArchiveMemoryError(f"{field}_must_be_sha256")
    return match.group(1).lower()


def _content_id(value: Any, sha256: str | None, field: str) -> str | None:
    if value is None or value == "":
        return f"content:sha256:{sha256}" if sha256 is not None else None
    content_id = _text(value, field, limit=160)
    expected = f"content:sha256:{sha256}" if sha256 is not None else None
    if expected is None or content_id != expected:
        raise ArchiveMemoryError(f"{field}_inconsistent_with_sha256")
    return content_id


def _artifact_rows(batch: Mapping[str, Any], archive_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_list(batch.get("artifacts"), "artifacts")):
        item = _mapping(raw, f"artifacts[{index}]")
        item_archive = _text(item.get("archive_id"), f"artifacts[{index}].archive_id")
        if item_archive != archive_id:
            raise ArchiveMemoryError(f"artifacts[{index}].archive_id_conflict")
        artifact_id = _text(item.get("artifact_id"), f"artifacts[{index}].artifact_id", limit=240)
        physical_id = _text(item.get("physical_id"), f"artifacts[{index}].physical_id", limit=240)
        artifact_ref = _text(item.get("artifact_ref"), f"artifacts[{index}].artifact_ref", limit=320)
        references = _list(item.get("references", []), f"artifacts[{index}].references")
        sha256 = _optional_sha256(item.get("sha256"), f"artifacts[{index}].sha256")
        content_id = _content_id(item.get("content_id"), sha256, f"artifacts[{index}].content_id")
        canonical = {
            "archive_id": archive_id,
            "artifact_id": artifact_id,
            "physical_id": physical_id,
            "artifact_ref": artifact_ref,
            "references": references,
            "relative_path": _text(item.get("relative_path"), f"artifacts[{index}].relative_path", limit=2000),
            "kind": _text(item.get("kind"), f"artifacts[{index}].kind", limit=80),
            "availability": _text(item.get("availability"), f"artifacts[{index}].availability", limit=80),
            "size": _optional_int(item.get("size"), f"artifacts[{index}].size"),
            "mtime_ns": _optional_int(item.get("mtime_ns"), f"artifacts[{index}].mtime_ns"),
            "extension": _text(item.get("extension"), f"artifacts[{index}].extension", required=False, limit=40),
            "family": _text(item.get("family"), f"artifacts[{index}].family", limit=80),
            "media_type": _text(item.get("media_type"), f"artifacts[{index}].media_type", limit=200),
            "sha256": sha256,
            "content_id": content_id,
            "symlink_target": item.get("symlink_target"),
            "error_code": item.get("error_code"),
            "error_operation": item.get("error_operation"),
        }
        stable = dict(canonical)
        stable.pop("mtime_ns", None)
        rows.append({"canonical": canonical, "stable": stable})
    return rows


def _observation_rows(batch: Mapping[str, Any], archive_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_list(batch.get("observations"), "observations")):
        item = _mapping(raw, f"observations[{index}]")
        artifact_refs = _list(item.get("artifact_refs", []), f"observations[{index}].artifact_refs")
        if any(not isinstance(ref, str) or not ref for ref in artifact_refs):
            raise ArchiveMemoryError(f"observations[{index}].artifact_refs_invalid")
        observation_type = _text(item.get("observation_type"), f"observations[{index}].observation_type", limit=160)
        status = _text(item.get("status") or "candidate", f"observations[{index}].status", limit=80)
        evidence = item.get("evidence") if item.get("evidence") is not None else {}
        provided_id = item.get("observation_id")
        if isinstance(provided_id, str) and provided_id.strip():
            observation_id = provided_id.strip()[:320]
        else:
            observation_id = "observation:" + _hash({
                "archive_id": archive_id,
                "observation_type": observation_type,
                "status": status,
                "artifact_refs": artifact_refs,
                "evidence": evidence,
            })
        rows.append({
            "observation_id": observation_id,
            "archive_id": archive_id,
            "observation_type": observation_type,
            "status": status,
            "artifact_refs": artifact_refs,
            "evidence": evidence,
            "method": item.get("method"),
            "tool_version": item.get("tool_version"),
            "observed_at": item.get("observed_at"),
        })
    return rows


def _semantic_payload(
    batch: Mapping[str, Any],
    archive_id: str,
    snapshot_id: str,
    artifacts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": batch["schema"],
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "limits": batch.get("limits") if batch.get("limits") is not None else {},
        "artifacts": [row["stable"] for row in artifacts],
        "observations": [
            {key: value for key, value in row.items()
             if key not in {"method", "tool_version", "observed_at"}}
            for row in observations
        ],
    }


def _row_tuple(row: sqlite3.Row | None) -> tuple[Any, ...] | None:
    return tuple(row) if row is not None else None


def ingest_observation_batch(
    database: str | Path | LearningStore,
    batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Ingest one canonical observer batch into the existing LearningStore.

    The observer's semantic ``snapshot_id`` intentionally ignores ``mtime_ns``
    and ``change_set``.  When a touch therefore produces the same snapshot ID,
    the first stored volatile mtime is retained and no second state is made.
    """
    if not isinstance(batch, Mapping):
        raise ArchiveMemoryError("batch_must_be_object")
    if batch.get("schema") != BATCH_SCHEMA:
        raise ArchiveMemoryError("batch_bad_schema")
    try:
        validate_batch(batch)
    except ArchiveObservationError as error:
        raise ArchiveMemoryError(f"batch_invalid:{error}") from error
    archive_id = _archive_id(batch)
    snapshot_id = _text(batch.get("snapshot_id"), "snapshot_id", limit=320)
    limits = batch.get("limits") if batch.get("limits") is not None else {}
    _mapping(limits, "limits")
    change_set = batch.get("change_set") if batch.get("change_set") is not None else {}
    _mapping(change_set, "change_set")
    artifacts = _artifact_rows(batch, archive_id)
    observations = _observation_rows(batch, archive_id)
    semantic = _semantic_payload(batch, archive_id, snapshot_id, artifacts, observations)
    semantic_json = _json(semantic)
    semantic_hash = _hash(semantic)
    source_root_ref = f"archive:{archive_id}"
    path = _database_path(database)
    store = database if isinstance(database, LearningStore) else LearningStore(path)
    inserted = {"archive": 0, "snapshot": 0, "artifacts": 0, "states": 0, "observations": 0, "events": 0}

    with store.connect() as connection:
        store.ensure_schema(connection)
        first_ingested_at = now_iso()
        archive = connection.execute(
            "SELECT source_root_ref,metadata_json FROM archive_memory_v2_archives WHERE archive_id=?",
            (archive_id,),
        ).fetchone()
        archive_values = (source_root_ref, _json({"observer_schema": BATCH_SCHEMA}))
        if archive is None:
            connection.execute(
                "INSERT INTO archive_memory_v2_archives(archive_id,source_root_ref,first_ingested_at,metadata_json) VALUES (?,?,?,?)",
                (archive_id, source_root_ref, first_ingested_at, archive_values[1]),
            )
            inserted["archive"] = 1
        elif _row_tuple(archive) != archive_values:
            raise ArchiveMemoryError(f"archive_id_conflict:{archive_id}")

        snapshot = connection.execute(
            "SELECT semantic_hash,semantic_json,input_schema,limits_json,source_root_ref FROM archive_memory_v2_snapshots WHERE archive_id=? AND snapshot_id=?",
            (archive_id, snapshot_id),
        ).fetchone()
        snapshot_values = (
            semantic_hash, semantic_json, BATCH_SCHEMA, _json(limits),
        )
        if snapshot is None:
            connection.execute(
                "INSERT INTO archive_memory_v2_snapshots(archive_id,snapshot_id,semantic_hash,semantic_json,input_schema,limits_json,change_set_json,source_root_ref,first_ingested_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (archive_id, snapshot_id, *snapshot_values, _json(change_set), source_root_ref, first_ingested_at),
            )
            inserted["snapshot"] = 1
        elif _row_tuple(snapshot) != (*snapshot_values, source_root_ref):
            raise ArchiveMemoryError(f"snapshot_id_conflict:{snapshot_id}")

        for row in artifacts:
            item = row["canonical"]
            stable = row["stable"]
            entity = connection.execute(
                "SELECT physical_id,artifact_ref FROM archive_memory_v2_artifacts WHERE archive_id=? AND artifact_id=?",
                (archive_id, item["artifact_id"]),
            ).fetchone()
            entity_values = (item["physical_id"], item["artifact_ref"])
            if entity is None:
                connection.execute(
                    "INSERT INTO archive_memory_v2_artifacts(archive_id,artifact_id,physical_id,artifact_ref,first_ingested_at) VALUES (?,?,?,?,?)",
                    (archive_id, item["artifact_id"], *entity_values, first_ingested_at),
                )
                inserted["artifacts"] += 1
            elif _row_tuple(entity) != entity_values:
                raise ArchiveMemoryError(f"artifact_id_conflict:{item['artifact_id']}")

            state_id = "state:" + _hash({
                "archive_id": archive_id,
                "snapshot_id": snapshot_id,
                "artifact_id": item["artifact_id"],
                "state": stable,
            })
            existing_state = connection.execute(
                "SELECT state_id,physical_id,artifact_ref,relative_path,references_json,kind,availability,size,extension,family,media_type,content_sha256,content_id,symlink_target,error_code,error_operation FROM archive_memory_v2_artifact_states WHERE archive_id=? AND snapshot_id=? AND artifact_id=?",
                (archive_id, snapshot_id, item["artifact_id"]),
            ).fetchone()
            state_values = (
                item["physical_id"], item["artifact_ref"], item["relative_path"], _json(item["references"]),
                item["kind"], item["availability"], item["size"], item["extension"], item["family"],
                item["media_type"], item["sha256"], item["content_id"], item["symlink_target"],
                item["error_code"], item["error_operation"],
            )
            if existing_state is None:
                connection.execute(
                    "INSERT INTO archive_memory_v2_artifact_states(state_id,archive_id,snapshot_id,artifact_id,physical_id,artifact_ref,relative_path,references_json,kind,availability,size,mtime_ns,extension,family,media_type,content_sha256,content_id,symlink_target,error_code,error_operation,artifact_json,first_ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        state_id, archive_id, snapshot_id, item["artifact_id"], item["physical_id"],
                        item["artifact_ref"], item["relative_path"], _json(item["references"]), item["kind"],
                        item["availability"], item["size"], item["mtime_ns"], item["extension"], item["family"],
                        item["media_type"], item["sha256"], item["content_id"], item["symlink_target"],
                        item["error_code"], item["error_operation"], _json(item), first_ingested_at,
                    ),
                )
                inserted["states"] += 1
            else:
                existing_state_values = tuple(existing_state[1:])
                if existing_state_values != state_values:
                    raise ArchiveMemoryError(f"state_id_conflict:{state_id}")
                # mtime_ns is intentionally absent from the comparison.  It is
                # volatile observer metadata; the first value is retained.

        for row in observations:
            values = (
                snapshot_id,
                row["observation_type"], row["status"], _json(row["artifact_refs"]), _json(row["evidence"]),
                row["method"], row["tool_version"], row["observed_at"],
            )
            # The same stable observer observation may recur in a later
            # snapshot.  Its occurrence is keyed by that snapshot, while the
            # observer-provided observation_id is preserved verbatim.
            existing = connection.execute(
                "SELECT snapshot_id,observation_type,status,artifact_refs_json,evidence_json,method,tool_version,observed_at FROM archive_memory_v2_observations WHERE archive_id=? AND snapshot_id=? AND observation_id=?",
                (archive_id, snapshot_id, row["observation_id"]),
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO archive_memory_v2_observations(archive_id,observation_id,snapshot_id,observation_type,status,artifact_refs_json,evidence_json,method,tool_version,observed_at,first_ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (archive_id, row["observation_id"], *values, first_ingested_at),
                )
                inserted["observations"] += 1
            elif _row_tuple(existing) != values:
                raise ArchiveMemoryError(f"observation_id_conflict:{row['observation_id']}")

    replay = replay_snapshot(path, archive_id=archive_id, snapshot_id=snapshot_id)
    return {
        "schema": SCHEMA,
        "batch_schema": BATCH_SCHEMA,
        "input_schema": batch["schema"],
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "source_root_ref": source_root_ref,
        "inserted": inserted,
        "replay_hash": replay["replay_hash"],
        "counts": {"artifacts": len(artifacts), "observations": len(observations), "events": 0},
    }


def list_archives(database: str | Path | LearningStore) -> list[dict[str, Any]]:
    with _readonly(database) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT archive_id,source_root_ref,first_ingested_at,metadata_json FROM archive_memory_v2_archives ORDER BY archive_id"
        ).fetchall()]


def list_snapshots(database: str | Path | LearningStore, archive_id: str) -> list[dict[str, Any]]:
    archive_id = _text(archive_id, "archive_id")
    with _readonly(database) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT archive_id,snapshot_id,semantic_hash,input_schema,limits_json,change_set_json,source_root_ref,first_ingested_at FROM archive_memory_v2_snapshots WHERE archive_id=? ORDER BY snapshot_id",
            (archive_id,),
        ).fetchall()]


def list_artifacts(
    database: str | Path | LearningStore,
    archive_id: str,
    snapshot_id: str | None = None,
) -> list[dict[str, Any]]:
    archive_id = _text(archive_id, "archive_id")
    with _readonly(database) as connection:
        if snapshot_id:
            rows = connection.execute(
                "SELECT state_id,archive_id,snapshot_id,artifact_id,physical_id,artifact_ref,relative_path,references_json,kind,availability,size,mtime_ns,extension,family,media_type,content_sha256,content_id,symlink_target,error_code,error_operation,artifact_json,first_ingested_at FROM archive_memory_v2_artifact_states WHERE archive_id=? AND snapshot_id=? ORDER BY relative_path,artifact_id",
                (archive_id, snapshot_id),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT archive_id,artifact_id,physical_id,artifact_ref,first_ingested_at FROM archive_memory_v2_artifacts WHERE archive_id=? ORDER BY artifact_ref",
                (archive_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def list_observations(
    database: str | Path | LearningStore,
    archive_id: str,
    *,
    snapshot_id: str | None = None,
    subject_id: str | None = None,
) -> list[dict[str, Any]]:
    archive_id = _text(archive_id, "archive_id")
    clauses = ["archive_id=?"]
    args: list[Any] = [archive_id]
    if snapshot_id:
        clauses.append("snapshot_id=?")
        args.append(snapshot_id)
    if subject_id:
        clauses.append("artifact_refs_json LIKE ?")
        args.append("%" + subject_id + "%")
    with _readonly(database) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT archive_id,observation_id,snapshot_id,observation_type,status,artifact_refs_json,evidence_json,method,tool_version,observed_at,first_ingested_at FROM archive_memory_v2_observations WHERE "
            + " AND ".join(clauses) + " ORDER BY observation_id", args,
        ).fetchall()]


def list_transformations(
    database: str | Path | LearningStore,
    archive_id: str,
    *,
    snapshot_id: str | None = None,
) -> list[dict[str, Any]]:
    archive_id = _text(archive_id, "archive_id")
    clauses = ["archive_id=?"]
    args: list[Any] = [archive_id]
    if snapshot_id:
        clauses.append("snapshot_id=?")
        args.append(snapshot_id)
    with _readonly(database) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT archive_id,event_id,snapshot_id,operation,inputs_json,outputs_json,witness_json,status,tool_version,occurred_at,metadata_json FROM archive_memory_v2_transformation_events WHERE "
            + " AND ".join(clauses) + " ORDER BY event_id", args,
        ).fetchall()]


def _replay_artifact(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "archive_id": row["archive_id"],
        "artifact_id": row["artifact_id"],
        "physical_id": row["physical_id"],
        "artifact_ref": row["artifact_ref"],
        "references": _decode(row["references_json"], []),
        "relative_path": row["relative_path"],
        "kind": row["kind"],
        "availability": row["availability"],
        "size": row["size"],
        "mtime_ns": row["mtime_ns"],
        "extension": row["extension"],
        "family": row["family"],
        "media_type": row["media_type"],
        "sha256": row["content_sha256"],
        "content_id": row["content_id"],
        "symlink_target": row["symlink_target"],
        "error_code": row["error_code"],
        "error_operation": row["error_operation"],
    }


def replay_snapshot(
    database: str | Path | LearningStore,
    *,
    archive_id: str,
    snapshot_id: str,
) -> dict[str, Any]:
    """Return a deterministic read-only projection of one stored snapshot."""
    archive_id = _text(archive_id, "archive_id")
    snapshot_id = _text(snapshot_id, "snapshot_id")
    with _readonly(database) as connection:
        snapshot = connection.execute(
            "SELECT archive_id,snapshot_id,semantic_hash,input_schema,limits_json,change_set_json,source_root_ref FROM archive_memory_v2_snapshots WHERE archive_id=? AND snapshot_id=?",
            (archive_id, snapshot_id),
        ).fetchone()
        if snapshot is None:
            raise ArchiveMemoryError(f"snapshot_not_found:{archive_id}:{snapshot_id}")
        artifacts = [_replay_artifact(row) for row in connection.execute(
            "SELECT archive_id,artifact_id,physical_id,artifact_ref,relative_path,references_json,kind,availability,size,mtime_ns,extension,family,media_type,content_sha256,content_id,symlink_target,error_code,error_operation FROM archive_memory_v2_artifact_states WHERE archive_id=? AND snapshot_id=? ORDER BY relative_path,artifact_id",
            (archive_id, snapshot_id),
        ).fetchall()]
        observations = [{
            "observation_id": row["observation_id"],
            "observation_type": row["observation_type"],
            "status": row["status"],
            "artifact_refs": _decode(row["artifact_refs_json"], []),
            "evidence": _decode(row["evidence_json"], {}),
        } for row in connection.execute(
            "SELECT observation_id,observation_type,status,artifact_refs_json,evidence_json,method,tool_version,observed_at FROM archive_memory_v2_observations WHERE archive_id=? AND snapshot_id=? ORDER BY observation_id",
            (archive_id, snapshot_id),
        ).fetchall()]
    observations.sort(key=lambda item: (
        str(item["observation_type"]),
        stable_json(item["artifact_refs"]),
        stable_json(item["evidence"]),
    ))
    payload = {
        "schema": BATCH_SCHEMA,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "limits": _decode(snapshot["limits_json"], {}),
        "artifacts": artifacts,
        "observations": observations,
        "change_set": _decode(snapshot["change_set_json"], {}),
    }
    return {
        "schema": SCHEMA,
        "batch_schema": BATCH_SCHEMA,
        "archive_id": archive_id,
        "snapshot_id": snapshot_id,
        "replay_hash": _hash(payload),
        "snapshot": payload,
    }


__all__ = [
    "ArchiveMemoryError",
    "BATCH_SCHEMA",
    "SCHEMA",
    "ingest_observation_batch",
    "list_archives",
    "list_snapshots",
    "list_artifacts",
    "list_observations",
    "list_transformations",
    "replay_snapshot",
]
