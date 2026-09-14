#!/usr/bin/env python3
"""Persist and attach an evidence-aware artist/project context graph.

The command consumes a versioned JSON package.  It never fetches URLs, copies
source trees or changes Project IR state.  Web facts must arrive with their
source locator and independence group; this makes the result auditable.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from flujo.knowledge.project_context import (
    ProjectContextError,
    build_report,
    link_context_to_project_ir,
    load_context,
    persist_context,
)
from flujo.knowledge.project_router import route_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-json", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true",
                        help="attach a compact context block to matching Project IR records")
    args = parser.parse_args(argv)
    try:
        payload = load_context(args.context_json)
        result = persist_context(args.db, payload)
        updates = link_context_to_project_ir(args.db, payload) if args.apply else []
        report = build_report(result, updates)
    except (ProjectContextError, OSError, ValueError) as exc:
        print(f"context_error: {exc}", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.apply and updates:
        project_ids = [str(item["project_id"]) for item in updates]
        placeholders = ",".join("?" for _ in project_ids)
        with sqlite3.connect(f"file:{Path(args.db).expanduser().resolve()}?mode=ro", uri=True) as con:
            rows = con.execute(
                f"SELECT ir_json FROM project_records WHERE project_id IN ({placeholders}) ORDER BY title,project_id",
                project_ids,
            ).fetchall()
        enriched_records = [json.loads(row[0]) for row in rows]
        ir_path = args.out_dir / "project_ir.jsonl"
        routes_path = args.out_dir / "routes.jsonl"
        with ir_path.open("w", encoding="utf-8") as handle:
            for record in enriched_records:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        with routes_path.open("w", encoding="utf-8") as handle:
            for record in enriched_records:
                handle.write(json.dumps(route_project(record), ensure_ascii=False, sort_keys=True) + "\n")
        report["derived_outputs"] = {
            "project_ir": str(ir_path), "routes": str(routes_path),
            "records": len(enriched_records),
        }
    report_path = args.out_dir / "triangulation.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "schema": report["schema"],
        "context_id": report["context_id"],
        "entity_count": report["entity_count"],
        "source_count": report["source_count"],
        "relation_count": report["relation_count"],
        "relation_statuses": report["relation_statuses"],
        "project_ir_updates": len(report["project_ir_updates"]),
        "state_changes": report["state_changes"],
        "postulations_created": report["postulations_created"],
        "report": str(report_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
