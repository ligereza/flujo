"""Bounded SQLite federation for MAK knowledge sources.

This module records database identity, schema and semantic links without
copying source rows or reading source payloads.  Source databases remain
authoritative for their own records; the federation is an index of where
those records live and how a consumer should reach them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ._contract_helpers import compact_json as _json
from ._io_helpers import utc_now_iso as _now


SCHEMA = "mak-catalog-federation-v1"


@dataclass(frozen=True)
class SourceInspection:
    source_id: str
    path: str
    source_kind: str
    size_bytes: int
    mtime_ns: int
    schema_fingerprint: str
    tables: tuple[dict[str, Any], ...]
    table_count: int
    row_count: int


def _source_kind(path: Path) -> str:
    folded = str(path).casefold()
    if "fondart" in folded or "fondos" in folded:
        return "funding_corpus"
    if "intake" in folded or "postul" in folded:
        return "application_intake"
    if "archivo_index" in folded or "portable-ssd" in folded or "portable_ssd" in folded:
        return "asset_index"
    if "mak_knowledge" in folded or path.name.casefold() == "mak_knowledge.db":
        return "mak_master"
    if "dimensiones" in folded or "catalog.sqlite" in path.name.casefold():
        return "physical_catalog"
    if "archaeology" in folded or "claude-codex" in folded:
        return "history_corpus"
    if "jardines" in folded:
        return "research_corpus"
    return "unknown_sqlite"


def _semantic_kind(table_name: str) -> str:
    name = table_name.casefold()
    if "fondart" in name or name in {"fund_targets", "funding_opportunities"}:
        return "funding"
    if "application" in name or "postul" in name or name == "intake_projects":
        return "application"
    if "event" in name or "deadline" in name or "calendar" in name:
        return "calendar"
    if "repo" in name or "repository" in name:
        return "repository"
    if "tool" in name or "capabil" in name or "consumer" in name:
        return "capability"
    if "project" in name or "idea" in name:
        return "project"
    if "asset" in name or "file" in name or "family" in name:
        return "asset_catalog"
    if "entity" in name or "relation" in name:
        return "knowledge_graph"
    if "learning" in name or "episode" in name or "rule" in name:
        return "learning_ledger"
    return "other"


def _connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"sqlite_source_not_found: {path}")
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def inspect_database(path: str | Path, source_kind: str | None = None) -> SourceInspection:
    """Inspect SQLite metadata only; never writes and never reads row bodies."""
    source = Path(path).expanduser().resolve()
    stat = source.stat()
    tables: list[dict[str, Any]] = []
    row_count = 0
    with _connect_readonly(source) as connection:
        objects = connection.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for obj in objects:
            table_name = str(obj["name"])
            columns = [dict(row) for row in connection.execute(
                f'PRAGMA table_info("{table_name.replace(chr(34), chr(34) * 2)}")'
            )]
            count: int | None = None
            if obj["type"] == "table":
                try:
                    count = int(connection.execute(
                        f'SELECT COUNT(*) FROM "{table_name.replace(chr(34), chr(34) * 2)}"'
                    ).fetchone()[0])
                    row_count += count
                except sqlite3.DatabaseError:
                    count = None
            tables.append({
                "name": table_name,
                "object_type": str(obj["type"]),
                "columns": columns,
                "row_count": count,
                "semantic_kind": _semantic_kind(table_name),
                "sql": obj["sql"] or "",
            })
    schema_fingerprint = hashlib.sha256(_json(tables).encode("utf-8")).hexdigest()
    kind = source_kind or _source_kind(source)
    # The path is the stable identity. Size, mtime and schema fingerprint are
    # mutable observations; using them in source_id would orphan old table
    # rows every time a source database is refreshed.
    identity = str(source)
    source_id = "source_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    return SourceInspection(
        source_id=source_id, path=str(source), source_kind=kind,
        size_bytes=int(stat.st_size), mtime_ns=int(stat.st_mtime_ns),
        schema_fingerprint=schema_fingerprint, tables=tuple(tables),
        table_count=len(tables), row_count=row_count,
    )


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS catalog_sources (
            source_id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            source_kind TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            schema_fingerprint TEXT NOT NULL,
            table_count INTEGER NOT NULL,
            row_count INTEGER NOT NULL,
            read_only INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'observed',
            observed_at TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS catalog_tables (
            source_id TEXT NOT NULL REFERENCES catalog_sources(source_id),
            table_name TEXT NOT NULL,
            object_type TEXT NOT NULL,
            semantic_kind TEXT NOT NULL,
            row_count INTEGER,
            columns_json TEXT NOT NULL,
            sql_text TEXT NOT NULL,
            PRIMARY KEY(source_id, table_name)
        );
        CREATE TABLE IF NOT EXISTS catalog_links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL REFERENCES catalog_sources(source_id),
            source_table TEXT NOT NULL,
            target_kind TEXT NOT NULL,
            relation TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'structural',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(source_id, source_table, target_kind, relation)
        );
        CREATE INDEX IF NOT EXISTS idx_catalog_tables_semantic
            ON catalog_tables(semantic_kind, source_id);
        CREATE INDEX IF NOT EXISTS idx_catalog_links_target
            ON catalog_links(target_kind, relation);
        """
    )


def federate(inspections: Iterable[SourceInspection], target: str | Path) -> dict[str, Any]:
    """Upsert metadata into an explicitly selected writable catalog target."""
    destination = Path(target).expanduser().resolve()
    rows = list(inspections)
    if any(Path(item.path).resolve() == destination for item in rows):
        raise ValueError("target_must_not_be_source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(destination) as connection:
        connection.row_factory = sqlite3.Row
        create_schema(connection)
        for item in rows:
            connection.execute(
                """INSERT INTO catalog_sources
                (source_id,path,source_kind,size_bytes,mtime_ns,schema_fingerprint,
                 table_count,row_count,read_only,status,observed_at,evidence_json)
                VALUES (?,?,?,?,?,?,?,?,1,'observed',?,?)
                ON CONFLICT(path) DO UPDATE SET
                  source_id=excluded.source_id, source_kind=excluded.source_kind,
                  size_bytes=excluded.size_bytes, mtime_ns=excluded.mtime_ns,
                  schema_fingerprint=excluded.schema_fingerprint,
                  table_count=excluded.table_count, row_count=excluded.row_count,
                  read_only=1, status='observed', observed_at=excluded.observed_at,
                  evidence_json=excluded.evidence_json""",
                (item.source_id, item.path, item.source_kind, item.size_bytes,
                 item.mtime_ns, item.schema_fingerprint, item.table_count,
                 item.row_count, _now(), _json({"schema": SCHEMA, "source_preserved": True})),
            )
            connection.execute("DELETE FROM catalog_tables WHERE source_id=?", (item.source_id,))
            for table in item.tables:
                connection.execute(
                    """INSERT INTO catalog_tables
                    (source_id,table_name,object_type,semantic_kind,row_count,columns_json,sql_text)
                    VALUES (?,?,?,?,?,?,?)""",
                    (item.source_id, table["name"], table["object_type"],
                     table["semantic_kind"], table["row_count"], _json(table["columns"]),
                     table["sql"]),
                )
                connection.execute(
                    """INSERT OR IGNORE INTO catalog_links
                    (source_id,source_table,target_kind,relation,confidence,evidence_json)
                    VALUES (?,?,?,?,?,?)""",
                    (item.source_id, table["name"], table["semantic_kind"],
                     "contains_structured_records", "structural",
                     _json({"schema": SCHEMA, "source_read_only": True})),
                )
        connection.commit()
    return {
        "schema": SCHEMA, "target": str(destination), "sources": len(rows),
        "tables": sum(item.table_count for item in rows),
        "rows_observed": sum(item.row_count for item in rows),
        "source_rows_copied": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    inspections = [inspect_database(path) for path in args.source]
    result = federate(inspections, args.target)
    result["source_details"] = [
        {"source_id": item.source_id, "path": item.path, "source_kind": item.source_kind,
         "table_count": item.table_count, "row_count": item.row_count}
        for item in inspections
    ]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
