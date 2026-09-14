"""Read-only reconciliation for the unified knowledge database target.

This module does not migrate data. It inspects SQLite inputs, compares their
schemas and deterministic row fingerprints, and emits a reviewable plan for a
future engine-specific migration. Source databases are opened in read-only
mode and no output database is created by the reconciliation itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from ._io_helpers import sha256_file as _sha256_file


RECONCILIATION_SCHEMA = "mak-unified-knowledge-reconciliation-v1"
TARGET_SCHEMA = "mak-unified-knowledge-db-target-v1"
NAMESPACES = ("core", "mak", "rd", "portfolio", "relations", "products", "audit")
PROVENANCE_FIELDS = (
    "source_or_evidence",
    "producer",
    "owner",
    "confidence_or_status",
    "visibility",
    "timestamp_or_version",
)
NAMESPACE_OWNERS = {
    "core": "shared",
    "mak": "MAK",
    "rd": "RD",
    "portfolio": "Portfolio",
    "relations": "shared",
    "products": "shared",
    "audit": "shared",
}


class ReconciliationInputError(RuntimeError):
    """A source could not be inspected without making a trust decision."""


class SourceChangedDuringReadError(ReconciliationInputError):
    """A source changed while its read-only snapshot was being built."""


def _json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes__": value.hex()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ReconciliationInputError(f"source database is missing: {path.name}")
    encoded_path = quote(path.resolve().as_posix(), safe="/:")
    uri = f"file:{encoded_path}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=0.2)
    except sqlite3.DatabaseError as exc:
        raise ReconciliationInputError(
            f"cannot open source database read-only: {path.name}: {exc}"
        ) from exc
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _table_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return sorted(str(row[0]) for row in rows)


def _table_columns(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA table_xinfo({_identifier(table)})").fetchall()
    return [
        {
            "cid": int(row[0]),
            "name": str(row[1]),
            "type": str(row[2] or ""),
            "notnull": int(row[3]),
            "default": _json_value(row[4]),
            "pk": int(row[5]),
            "hidden": int(row[6] or 0),
        }
        for row in rows
    ]


def _table_sql(connection: sqlite3.Connection, table: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return " ".join(str(row[0] or "").split()) if row else ""


def _foreign_keys(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA foreign_key_list({_identifier(table)})").fetchall()
    fields = ("id", "seq", "table", "from", "to", "on_update", "on_delete", "match")
    values = [
        {field: _json_value(row[index]) for index, field in enumerate(fields)}
        for row in rows
    ]
    return sorted(values, key=lambda item: tuple(str(item[field]) for field in fields))


def _indexes(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA index_list({_identifier(table)})").fetchall()
    indexes: list[dict[str, Any]] = []
    for row in rows:
        name = str(row[1])
        info_rows = connection.execute(f"PRAGMA index_xinfo({_identifier(name)})").fetchall()
        columns = [
            {
                "seqno": int(info[0]),
                "cid": int(info[1]),
                "name": _json_value(info[2]),
                "desc": int(info[3] or 0),
                "coll": str(info[4] or ""),
                "key": int(info[5] or 0),
            }
            for info in info_rows
        ]
        sql_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)
        ).fetchone()
        indexes.append(
            {
                "name": name,
                "unique": int(row[2] or 0),
                "origin": str(row[3] or ""),
                "partial": int(row[4] or 0),
                "columns": sorted(columns, key=lambda item: item["seqno"]),
                "sql": " ".join(str(sql_row[0] or "").split()) if sql_row else "",
            }
        )
    return sorted(indexes, key=lambda item: item["name"])


def _provenance_report(columns: list[dict[str, Any]]) -> dict[str, Any]:
    names = {column["name"] for column in columns}
    present = [field for field in PROVENANCE_FIELDS if field in names]
    missing = [field for field in PROVENANCE_FIELDS if field not in names]
    return {
        "required_fields": list(PROVENANCE_FIELDS),
        "present_fields": present,
        "missing_fields": missing,
        "complete": not missing,
        "status": "complete" if not missing else "missing_fields_review_required",
    }


def _canonical_row(row: sqlite3.Row, columns: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return {column["name"]: _json_value(row[column["name"]]) for column in columns}


def _row_digest(row: dict[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(row)).hexdigest()


def _key_value(row: dict[str, Any], primary_key: list[str]) -> str:
    return _json_bytes([row.get(column) for column in primary_key]).decode("ascii")


def _multiset_digest(digests: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for item in sorted(digests):
        digest.update(item.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _table_snapshot(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    columns = _table_columns(connection, table)
    primary_key = [
        column["name"]
        for column in sorted(
            (column for column in columns if column["pk"]), key=lambda item: item["pk"]
        )
    ]
    rows = connection.execute(f"SELECT * FROM {_identifier(table)}").fetchall()
    canonical_rows = [_canonical_row(row, columns) for row in rows]
    row_digests = [_row_digest(row) for row in canonical_rows]
    keyed_rows = {}
    if primary_key:
        keyed_rows = {
            key: row
            for key, row in sorted(
                ((_key_value(row, primary_key), row) for row in canonical_rows),
                key=lambda item: item[0],
            )
        }
    return {
        "name": table,
        "columns": columns,
        "primary_key": primary_key,
        "sql": _table_sql(connection, table),
        "foreign_keys": _foreign_keys(connection, table),
        "indexes": _indexes(connection, table),
        "provenance": _provenance_report(columns),
        "row_count": len(canonical_rows),
        "row_hash": _multiset_digest(row_digests),
        "row_digest_counts": dict(sorted(Counter(row_digests).items())),
        "keyed_rows": keyed_rows,
    }


def _public_table(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: snapshot[key]
        for key in (
            "name",
            "columns",
            "primary_key",
            "sql",
            "foreign_keys",
            "indexes",
            "provenance",
            "row_count",
            "row_hash",
        )
    }


def inspect_sqlite(path: str | Path, *, source_id: str, role: str) -> dict[str, Any]:
    """Return a deterministic, read-only snapshot of a SQLite database."""
    db_path = Path(path).resolve()
    if not db_path.is_file():
        raise ReconciliationInputError(f"source database is missing: {db_path.name}")
    before = (db_path.stat().st_size, _sha256_file(db_path))
    try:
        with _connect_read_only(db_path) as connection:
            tables = [_table_snapshot(connection, table) for table in _table_names(connection)]
    except sqlite3.DatabaseError as exc:
        raise ReconciliationInputError(
            f"cannot inspect source database read-only: {db_path.name}: {exc}"
        ) from exc
    after = (db_path.stat().st_size, _sha256_file(db_path))
    if before != after:
        raise SourceChangedDuringReadError(
            f"source database changed during read: {db_path.name}"
        )
    schema_hash = hashlib.sha256(
        _json_bytes([_public_table(table) for table in tables])
    ).hexdigest()
    return {
        "source_id": source_id,
        "role": role,
        "path": db_path.name,
        "path_disclosure": "basename_only",
        "bytes": after[0],
        "sha256": after[1],
        "read_only": True,
        "accepted_truth": False,
        "authority_status": "unaccepted_input",
        "empty_database": not tables,
        "table_count": len(tables),
        "schema_hash": schema_hash,
        "tables": {table["name"]: _public_table(table) for table in tables},
        "_private_tables": {table["name"]: table for table in tables},
    }


def _row_delta(candidate: dict[str, Any], legacy: dict[str, Any]) -> dict[str, int]:
    candidate_counts = Counter(candidate.get("row_digest_counts", {}))
    legacy_counts = Counter(legacy.get("row_digest_counts", {}))
    candidate_only = sum((candidate_counts - legacy_counts).values())
    legacy_only = sum((legacy_counts - candidate_counts).values())
    shared = sum((candidate_counts & legacy_counts).values())
    return {
        "candidate_only": candidate_only,
        "legacy_only": legacy_only,
        "shared": shared,
        "different_digest_kinds": len(set(candidate_counts) ^ set(legacy_counts)),
    }


def _set_delta(candidate: list[dict[str, Any]], legacy: list[dict[str, Any]]) -> tuple[list[Any], list[Any]]:
    candidate_map = {_json_bytes(item).decode("ascii"): item for item in candidate}
    legacy_map = {_json_bytes(item).decode("ascii"): item for item in legacy}
    return (
        [candidate_map[key] for key in sorted(set(candidate_map) - set(legacy_map))],
        [legacy_map[key] for key in sorted(set(legacy_map) - set(candidate_map))],
    )


def _schema_delta(candidate: dict[str, Any], legacy: dict[str, Any]) -> dict[str, Any]:
    candidate_columns = {column["name"]: column for column in candidate["columns"]}
    legacy_columns = {column["name"]: column for column in legacy["columns"]}
    foreign_keys = _set_delta(candidate["foreign_keys"], legacy["foreign_keys"])
    indexes = _set_delta(candidate["indexes"], legacy["indexes"])
    return {
        "candidate_only_columns": sorted(set(candidate_columns) - set(legacy_columns)),
        "legacy_only_columns": sorted(set(legacy_columns) - set(candidate_columns)),
        "changed_common_columns": sorted(
            name
            for name in set(candidate_columns) & set(legacy_columns)
            if candidate_columns[name] != legacy_columns[name]
        ),
        "candidate_only_foreign_keys": foreign_keys[0],
        "legacy_only_foreign_keys": foreign_keys[1],
        "candidate_only_indexes": indexes[0],
        "legacy_only_indexes": indexes[1],
        "changed_primary_key": candidate["primary_key"] != legacy["primary_key"],
        "changed_table_sql": candidate["sql"] != legacy["sql"],
    }


def _compare_table(candidate: dict[str, Any] | None, legacy: dict[str, Any] | None) -> dict[str, Any]:
    if candidate is None:
        return {
            "status": "legacy_only",
            "proposed_action": "preserve_legacy_evidence",
            "review_required": True,
            "legacy": legacy,
        }
    if legacy is None:
        return {
            "status": "candidate_only",
            "proposed_action": "map_candidate_to_rd_after_review",
            "review_required": True,
            "candidate": candidate,
        }

    same_schema = (
        candidate["columns"] == legacy["columns"]
        and candidate["primary_key"] == legacy["primary_key"]
        and candidate["sql"] == legacy["sql"]
        and candidate["foreign_keys"] == legacy["foreign_keys"]
        and candidate["indexes"] == legacy["indexes"]
    )
    same_rows = candidate["row_hash"] == legacy["row_hash"]
    result: dict[str, Any] = {
        "status": "identical" if same_schema and same_rows else "conflict",
        "proposed_action": "retain_one_logical_representation" if same_schema and same_rows else "quarantine_conflict_for_review",
        "review_required": not (same_schema and same_rows),
        "schema_equal": same_schema,
        "row_equal": same_rows,
        "row_delta": _row_delta(candidate, legacy),
        "candidate": candidate,
        "legacy": legacy,
        "schema_delta": _schema_delta(candidate, legacy),
    }
    comparable_key = candidate["primary_key"]
    if comparable_key and comparable_key == legacy["primary_key"]:
        candidate_rows = candidate.get("keyed_rows", {})
        legacy_rows = legacy.get("keyed_rows", {})
        candidate_keys = set(candidate_rows)
        legacy_keys = set(legacy_rows)
        conflicts = []
        for key in sorted(candidate_keys & legacy_keys):
            common_columns = sorted(set(candidate_rows[key]) & set(legacy_rows[key]))
            changed = [
                column
                for column in common_columns
                if candidate_rows[key].get(column) != legacy_rows[key].get(column)
            ]
            if changed:
                conflicts.append(
                    {
                        "key": json.loads(key),
                        "changed_columns": changed,
                        "candidate_row_hash": _row_digest(candidate_rows[key]),
                        "legacy_row_hash": _row_digest(legacy_rows[key]),
                    }
                )
        result["key_coverage"] = {
            "candidate_only": len(candidate_keys - legacy_keys),
            "legacy_only": len(legacy_keys - candidate_keys),
            "shared": len(candidate_keys & legacy_keys),
            "conflicting": len(conflicts),
        }
        result["conflicts"] = conflicts[:20]
        result["common_column_row_equal"] = not conflicts
    else:
        result["key_coverage"] = None
        result["conflicts"] = []
        result["common_column_row_equal"] = None
    return result


def _strip_private(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = dict(snapshot)
    result.pop("_private_tables", None)
    result.pop("_private_table_data", None)
    result.pop("keyed_rows", None)
    result.pop("row_digest_counts", None)
    return result


def build_reconciliation_plan(
    candidate_path: str | Path,
    legacy_path: str | Path,
) -> dict[str, Any]:
    """Build a deterministic plan without writing to either source."""
    candidate = inspect_sqlite(candidate_path, source_id="windows_rd", role="CANDIDATE_AUTHORITY")
    legacy = inspect_sqlite(legacy_path, source_id="mak_rd", role="LEGACY_PROJECTION")
    for snapshot in (candidate, legacy):
        private = snapshot.pop("_private_tables")
        snapshot["_private_table_data"] = {
            table_name: {
                "keyed_rows": table.get("keyed_rows", {}),
                "row_digest_counts": table.get("row_digest_counts", {}),
            }
            for table_name, table in private.items()
        }

    def attach(snapshot: dict[str, Any], table_name: str) -> dict[str, Any]:
        public = dict(snapshot["tables"][table_name])
        private = snapshot["_private_table_data"].get(table_name, {})
        public["keyed_rows"] = private.get("keyed_rows", {})
        public["row_digest_counts"] = private.get("row_digest_counts", {})
        return public

    table_names = sorted(set(candidate["tables"]) | set(legacy["tables"]))
    comparisons = {
        name: _compare_table(
            attach(candidate, name) if name in candidate["tables"] else None,
            attach(legacy, name) if name in legacy["tables"] else None,
        )
        for name in table_names
    }
    for comparison in comparisons.values():
        comparison.pop("keyed_rows", None)
        comparison.pop("row_digest_counts", None)
        for key in ("candidate", "legacy"):
            if key in comparison:
                comparison[key].pop("keyed_rows", None)
                comparison[key].pop("row_digest_counts", None)

    return {
        "schema": RECONCILIATION_SCHEMA,
        "target": {
            "logical_database_id": "knowledge_db",
            "schema_contract": TARGET_SCHEMA,
            "engine": "engine_neutral",
            "materialization": "not_applied",
            "assertion_contract": {
                "required_fields": list(PROVENANCE_FIELDS),
                "typed_relations": True,
            },
            "namespaces": {
                name: {
                    "status": "NOT_CONFIGURED" if name == "portfolio" else "target_namespace",
                    "owner": NAMESPACE_OWNERS[name],
                }
                for name in NAMESPACES
            },
            "assertion_required_fields": list(PROVENANCE_FIELDS),
        },
        "inputs": {
            "candidate": _strip_private(candidate),
            "legacy": _strip_private(legacy),
        },
        "comparison": {
            "table_count": len(table_names),
            "identical_tables": sum(item["status"] == "identical" for item in comparisons.values()),
            "conflict_tables": sum(item["status"] == "conflict" for item in comparisons.values()),
            "candidate_only_tables": sum(item["status"] == "candidate_only" for item in comparisons.values()),
            "legacy_only_tables": sum(item["status"] == "legacy_only" for item in comparisons.values()),
            "tables": comparisons,
        },
        "migration": {
            "execution": "none",
            "writes_performed": False,
            "reversible": True,
            "primary_writer": "not_configured",
            "sync_direction": "not_defined_until_human_review",
            "promotion": "human_review_required",
            "candidate_authority_accepted": False,
        },
    }


def write_plan(plan: dict[str, Any], output: str | Path) -> None:
    """Write a canonical JSON plan; repeated runs produce identical bytes."""
    Path(output).write_text(
        json.dumps(plan, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a read-only SQLite reconciliation plan")
    parser.add_argument("reconcile", nargs="?")
    parser.add_argument("--candidate", required=True, help="Windows RD migration candidate SQLite")
    parser.add_argument("--legacy", required=True, help="MAK RD legacy projection SQLite")
    parser.add_argument("--output", required=True, help="Deterministic JSON plan path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    plan = build_reconciliation_plan(args.candidate, args.legacy)
    write_plan(plan, args.output)
    print(
        json.dumps(
            {
                "schema": plan["schema"],
                "output": Path(args.output).name,
                "output_disclosure": "basename_only",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
