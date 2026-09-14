"""Materialize the smallest operational join across MAK databases.

The source databases remain authoritative and are opened read-only.  This
module copies only normalized operational fields into the existing master
database, preserving source path/table/key and a deterministic record hash.
It is a bridge for the DB -> research -> curation -> application pipeline, not
a second raw archive or a semantic truth engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from ._contract_helpers import compact_json as _json
from ._io_helpers import utc_now_iso as _now


SCHEMA = "mak-operational-bridge-v1"
DEFAULT_TARGET = Path(__file__).resolve().parents[3] / "data" / "mak_knowledge.db"
DEFAULT_RD = Path(__file__).resolve().parents[3] / "data" / "rd.db"
# `parents[3]` is the repository root, which is right for `data/` above. It is
# WRONG for these two: `research/` is not in the repository, it is a sibling of
# it under MAK's home. Written with [3] on 2026-08-20, both paths resolved to
# `flujo/research/...`, a directory that has never existed, so the bridge has
# been silently reading nothing since it was written. `parents[4]` is MAK.
MAK_HOME = Path(__file__).resolve().parents[4]
DEFAULT_INTAKE = MAK_HOME / "research" / "intake" / "portable-ssd-20260813-scd-r4" / "intake.sqlite"
# The run was `..._v5`, retired on 2026-08-29 for being byte-identical to a
# surviving one (it kept 0 captures of its own). `_v3` is the richest run still
# live in the corpus: 5215 rows in `fondart_applications` against v5's copy.
DEFAULT_FONDART = MAK_HOME / "research" / "corpus" / "fondart_annual_2015_2025_20260813_v3" / "sources.sqlite"


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _slug(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return "".join(ch if ch.isalnum() else "-" for ch in text).strip("-") or "unknown"


def _date_iso(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", text) else None


def _source_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def _read_rows(path: str | Path, table: str) -> list[dict[str, Any]]:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"source_database_not_found: {source}")
    with sqlite3.connect(f"file:{source}?mode=ro&immutable=1", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists is None:
            return []
        return [dict(row) for row in connection.execute(f"SELECT * FROM {_quote(table)}")]


def _record(
    *, domain: str, source: str, table: str, key: Any, title: Any = "",
    date_iso: str | None = None, producer_key: Any = None,
    producer_name: Any = None, venue_key: Any = None, venue_name: Any = None,
    status: Any = "observed", payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_ref = _source_path(source)
    source_key = str(key)
    record_id = f"{domain}:{source_key}"
    safe_payload = payload or {}
    fingerprint = hashlib.sha256(_json({
        "record_id": record_id, "domain": domain, "source": source_ref,
        "table": table, "key": source_key, "title": str(title or ""),
        "date_iso": date_iso, "producer_key": producer_key,
        "producer_name": producer_name, "venue_key": venue_key,
        "venue_name": venue_name, "status": str(status or ""),
        "payload": safe_payload,
    }).encode("utf-8")).hexdigest()
    return {
        "record_id": record_id, "domain": domain, "source_path": source_ref,
        "source_table": table, "source_key": source_key,
        "title": str(title or ""), "date_iso": date_iso,
        "producer_key": str(producer_key) if producer_key is not None else None,
        "producer_name": str(producer_name or "") or None,
        "venue_key": str(venue_key) if venue_key is not None else None,
        "venue_name": str(venue_name or "") or None,
        "status": str(status or "observed"), "payload_json": _json(safe_payload),
        "record_hash": fingerprint, "observed_at": _now(),
    }


def _rd_records(path: str | Path) -> tuple[list[dict[str, Any]], list[tuple[str, str, str, str]]]:
    source = _source_path(path)
    producers = {
        str(row.get("slug")): row for row in _read_rows(source, "productoras")
    }
    venue_specs: dict[str, tuple[str, str, dict[str, Any]]] = {}
    venue_ids: dict[str, str] = {}
    for row in _read_rows(source, "venues"):
        name = str(row.get("nombre") or "").strip()
        key = _slug(name)
        if name and key not in venue_specs:
            venue_specs[key] = ("venues", str(row.get("id")), row)
        if row.get("id") is not None and key:
            venue_ids[str(row.get("id"))] = f"rd_venue:{key}"
    for row in _read_rows(source, "productora_venues"):
        name = str(row.get("venue_nombre") or "").strip()
        key = _slug(name)
        if name and key not in venue_specs:
            venue_specs[key] = ("productora_venues", str(row.get("venue_id") or key), row)
        if row.get("venue_id") is not None and key:
            venue_ids[str(row.get("venue_id"))] = f"rd_venue:{key}"
    venue_names = {
        f"rd_venue:{key}": str(row.get("nombre") or row.get("venue_nombre") or "")
        for key, (_table, _source_key, row) in venue_specs.items()
    }
    records: list[dict[str, Any]] = []
    links: list[tuple[str, str, str, str]] = []
    for row in _read_rows(source, "productoras"):
        key = row.get("slug")
        records.append(_record(
            domain="rd_producer", source=source, table="productoras", key=key,
            title=row.get("nombre"), status="confirmed" if row.get("confirmado") else "observed",
            payload={k: v for k, v in row.items() if k != "aliases"},
        ))
    for key, (table, source_key, row) in venue_specs.items():
        records.append(_record(
            domain="rd_venue", source=source, table=table, key=key,
            title=row.get("nombre") or row.get("venue_nombre"), venue_key=source_key,
            venue_name=row.get("nombre") or row.get("venue_nombre"),
            payload=row,
        ))
    for row in _read_rows(source, "productora_eventos"):
        event_key = row.get("id")
        producer_key = row.get("productora_slug")
        venue_raw = row.get("venue")
        producer = producers.get(str(producer_key), {})
        event_id = f"rd_event:{event_key}"
        venue_record_id = venue_ids.get(str(venue_raw))
        venue_confidence = "source_venue_key"
        if venue_record_id is None:
            venue_text = _slug(venue_raw)
            matches = [key for key in venue_specs if len(key) >= 5 and (key in venue_text or venue_text in key)]
            if len(matches) == 1:
                venue_record_id = f"rd_venue:{matches[0]}"
                venue_confidence = "candidate_name_match"
        venue_name = venue_names.get(venue_record_id or "") or str(venue_raw or "") or None
        records.append(_record(
            domain="rd_event", source=source, table="productora_eventos", key=event_key,
            title=row.get("nombre") or producer.get("nombre"), date_iso=_date_iso(row.get("fecha")),
            producer_key=producer_key, producer_name=producer.get("nombre") or producer_key,
            venue_key=venue_record_id, venue_name=venue_name,
            status=row.get("estado"), payload={**row, "date_raw": row.get("fecha")},
        ))
        if producer_key:
            links.append((event_id, "produced_by", f"rd_producer:{producer_key}", "exact_source_key"))
        if venue_record_id:
            links.append((event_id, "held_at", venue_record_id, venue_confidence))
    return records, links


def _fondart_records(path: str | Path) -> list[dict[str, Any]]:
    source = _source_path(path)
    records: list[dict[str, Any]] = []
    for row in _read_rows(source, "fondart_applications"):
        key = row.get("application_id")
        payload = {
            "capture_id": row.get("capture_id"), "source_folio": row.get("source_folio"),
            "reported_year": row.get("reported_year"), "source_url_year": row.get("source_url_year"),
            "region": row.get("region"), "area_or_modality": row.get("area_or_modality"),
            "responsible": row.get("responsible"), "amount_raw": row.get("amount_raw"),
            "amount_clp": row.get("amount_clp"), "selected_status": row.get("selected_status"),
            "partial": row.get("partial"), "source_url": row.get("source_url"),
        }
        records.append(_record(
            domain="fondart_application", source=source, table="fondart_applications", key=key,
            title=row.get("project_title"), producer_key=row.get("responsible"),
            producer_name=row.get("responsible"), status=row.get("selected_status"),
            payload=payload,
        ))
    return records


def _intake_records(
    path: str | Path,
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str, str]], list[dict[str, Any]]]:
    source = _source_path(path)
    records: list[dict[str, Any]] = []
    links: list[tuple[str, str, str, str]] = []
    curation_links: list[dict[str, Any]] = []
    for row in _read_rows(source, "intake_projects"):
        key = f"{row.get('run_id')}:{row.get('project_id')}"
        records.append(_record(
            domain="intake_project", source=source, table="intake_projects", key=key,
            title=row.get("title"), status=row.get("status"), payload=row,
        ))
    for row in _read_rows(source, "fund_targets"):
        key = f"{row.get('run_id')}:{row.get('fund_id')}"
        records.append(_record(
            domain="fund_target", source=source, table="fund_targets", key=key,
            title=row.get("name"), status=row.get("status"), payload=row,
        ))
    for row in _read_rows(source, "application_packages"):
        key = str(row.get("application_id"))
        records.append(_record(
            domain="application_package", source=source, table="application_packages", key=key,
            title=row.get("title"), status=row.get("status"), payload=row,
        ))
        project_id = f"intake_project:{row.get('run_id')}:{row.get('project_id')}"
        fund_id = f"fund_target:{row.get('run_id')}:{row.get('fund_id')}"
        links.append((f"application_package:{key}", "targets_project", project_id, "exact_intake_key"))
        links.append((f"application_package:{key}", "targets_fund", fund_id, "exact_intake_key"))
    for row in _read_rows(source, "mak_links"):
        curation_links.append({
            "source_path": source,
            "project_record_id": f"intake_project:{row.get('run_id')}:{row.get('project_id')}",
            "relation": row.get("relation") or "curated_link",
            "mak_path": row.get("mak_path") or "",
            "artifact_id": row.get("artifact_id"),
            "entity_kind": row.get("entity_kind") or "",
            "confidence": row.get("confidence") or "unknown",
            "evidence_json": row.get("evidence_json") or "{}",
        })
    return records, links, curation_links


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS operational_runs (
            run_id TEXT PRIMARY KEY,
            schema_name TEXT NOT NULL,
            status TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            record_count INTEGER NOT NULL,
            link_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            next_action TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS operational_records (
            record_id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_key TEXT NOT NULL,
            title TEXT NOT NULL,
            date_iso TEXT,
            producer_key TEXT,
            producer_name TEXT,
            venue_key TEXT,
            venue_name TEXT,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            record_hash TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            UNIQUE(source_path, source_table, source_key)
        );
        CREATE TABLE IF NOT EXISTS operational_links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_record_id TEXT NOT NULL REFERENCES operational_records(record_id),
            relation TEXT NOT NULL,
            target_record_id TEXT NOT NULL REFERENCES operational_records(record_id),
            confidence TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(source_record_id, relation, target_record_id)
        );
        CREATE TABLE IF NOT EXISTS operational_curation_links (
            curation_link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path TEXT NOT NULL,
            project_record_id TEXT NOT NULL REFERENCES operational_records(record_id),
            relation TEXT NOT NULL,
            mak_path TEXT NOT NULL,
            artifact_id INTEGER,
            entity_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(source_path, project_record_id, relation, mak_path, artifact_id)
        );
        CREATE INDEX IF NOT EXISTS idx_operational_records_domain
            ON operational_records(domain, status);
        CREATE INDEX IF NOT EXISTS idx_operational_records_date
            ON operational_records(date_iso);
        CREATE INDEX IF NOT EXISTS idx_operational_records_producer
            ON operational_records(producer_key, producer_name);
        CREATE INDEX IF NOT EXISTS idx_operational_records_title
            ON operational_records(title);
        CREATE INDEX IF NOT EXISTS idx_operational_links_relation
            ON operational_links(relation, confidence);
        CREATE INDEX IF NOT EXISTS idx_operational_curation_project
            ON operational_curation_links(project_record_id, confidence);
        """
    )


def _replace_source_records(
    connection: sqlite3.Connection, source_paths: Iterable[str],
    records: list[dict[str, Any]], links: list[tuple[str, str, str, str]],
    curation_links: list[dict[str, Any]],
) -> None:
    source_paths = tuple(_source_path(path) for path in source_paths)
    placeholders = ",".join("?" for _ in source_paths)
    old_ids = [row[0] for row in connection.execute(
        f"SELECT record_id FROM operational_records WHERE source_path IN ({placeholders})",
        source_paths,
    )]
    connection.execute(
        f"DELETE FROM operational_curation_links WHERE source_path IN ({placeholders})",
        source_paths,
    )
    if old_ids:
        old_placeholders = ",".join("?" for _ in old_ids)
        connection.execute(
            f"DELETE FROM operational_links WHERE source_record_id IN ({old_placeholders}) "
            f"OR target_record_id IN ({old_placeholders})", old_ids + old_ids
        )
        connection.execute(
            f"DELETE FROM operational_records WHERE record_id IN ({old_placeholders})", old_ids
        )
    for item in records:
        connection.execute(
            """INSERT INTO operational_records
            (record_id,domain,source_path,source_table,source_key,title,date_iso,
             producer_key,producer_name,venue_key,venue_name,status,payload_json,
             record_hash,observed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            tuple(item[field] for field in (
                "record_id", "domain", "source_path", "source_table", "source_key",
                "title", "date_iso", "producer_key", "producer_name", "venue_key",
                "venue_name", "status", "payload_json", "record_hash", "observed_at",
            )),
        )
    known = {row[0] for row in connection.execute("SELECT record_id FROM operational_records")}
    for source_id, relation, target_id, confidence in links:
        if source_id not in known or target_id not in known:
            continue
        connection.execute(
            """INSERT OR IGNORE INTO operational_links
            (source_record_id,relation,target_record_id,confidence,evidence_json)
            VALUES (?,?,?,?,?)""",
            (source_id, relation, target_id, confidence,
             _json({"schema": SCHEMA, "source_rows_copied": "normalized_fields_only"})),
        )
    for item in curation_links:
        if item["project_record_id"] not in known:
            continue
        connection.execute(
            """INSERT OR IGNORE INTO operational_curation_links
            (source_path,project_record_id,relation,mak_path,artifact_id,entity_kind,confidence,evidence_json)
            VALUES (?,?,?,?,?,?,?,?)""",
            (item["source_path"], item["project_record_id"], item["relation"],
             item["mak_path"], item["artifact_id"], item["entity_kind"],
             item["confidence"], item["evidence_json"]),
        )


def refresh_operational_bridge(
    target: str | Path = DEFAULT_TARGET,
    rd_db: str | Path = DEFAULT_RD,
    intake_db: str | Path = DEFAULT_INTAKE,
    fondart_db: str | Path = DEFAULT_FONDART,
) -> dict[str, Any]:
    """Refresh known operational records once, replacing only derived rows."""
    rd_records, rd_links = _rd_records(rd_db)
    fondart_records = _fondart_records(fondart_db)
    intake_records, intake_links, curation_links = _intake_records(intake_db)
    records = rd_records + fondart_records + intake_records
    links = rd_links + intake_links
    source_paths = (_source_path(rd_db), _source_path(fondart_db), _source_path(intake_db))
    run_id = "bridge_" + hashlib.sha256(_json({
        "schema": SCHEMA, "sources": source_paths,
        "records": [(row["record_id"], row["record_hash"]) for row in records],
    }).encode("utf-8")).hexdigest()[:20]
    destination = Path(target).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(destination) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        create_schema(connection)
        _replace_source_records(connection, source_paths, records, links, curation_links)
        connection.execute(
            """INSERT OR REPLACE INTO operational_runs
            (run_id,schema_name,status,source_count,record_count,link_count,created_at,next_action)
            VALUES (?,?,?,?,?,?,?,?)""",
            (run_id, SCHEMA, "verified_projection", len(source_paths), len(records),
             connection.execute("SELECT COUNT(*) FROM operational_links").fetchone()[0],
             _now(), "query operational_records before adding new relations"),
        )
        connection.commit()
    return {
        "schema": SCHEMA, "run_id": run_id, "target": str(destination),
        "source_count": len(source_paths), "record_count": len(records),
        "link_count": len(links), "curation_link_count": len(curation_links),
        "source_rows_copied": 0,
        "normalized_records_written": len(records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--rd-db", type=Path, default=DEFAULT_RD)
    parser.add_argument("--intake-db", type=Path, default=DEFAULT_INTAKE)
    parser.add_argument("--fondart-db", type=Path, default=DEFAULT_FONDART)
    args = parser.parse_args(argv)
    result = refresh_operational_bridge(args.target, args.rd_db, args.intake_db, args.fondart_db)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
