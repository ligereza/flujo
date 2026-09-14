#!/usr/bin/env python3
"""Bridge a persisted SSD reconstruction into Project IR and routing.

This command reads the reconstruction and its SQLite index. It writes a small
derived JSONL package and route decisions. The optional ``--db`` is the only
switch that persists records into the existing MAK learning store.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from flujo.knowledge.project_router import route_project
from flujo.knowledge.reconstruction_adapter import ADAPTER_SCHEMA, adapt_reconstruction


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconstruction", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=None,
                        help="existing LearningStore SQLite; omit for derived files only")
    args = parser.parse_args(argv)

    records = adapt_reconstruction(args.reconstruction)
    routes = [route_project(record) for record in records]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ir_path = args.out_dir / "project_ir.jsonl"
    route_path = args.out_dir / "routes.jsonl"
    with ir_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    with route_path.open("w", encoding="utf-8") as handle:
        for route in routes:
            handle.write(json.dumps(route, ensure_ascii=False, sort_keys=True) + "\n")

    saved = []
    if args.db is not None:
        from flujo.knowledge.project_ir import LearningStore

        store = LearningStore(args.db)
        for record in records:
            saved.append({
                "project_id": record["project_id"],
                "fingerprint": store.save_project(record),
            })

    manifest = {
        "schema": ADAPTER_SCHEMA,
        "source_reconstruction": str(args.reconstruction.expanduser().resolve()),
        "records": len(records),
        "routes": {
            "abstain": sum(route.get("decision") == "abstain" for route in routes),
            "select": sum(route.get("decision") == "select" for route in routes),
        },
        "saved_to_learning_store": str(args.db.expanduser().resolve()) if args.db else "",
        "saved": saved,
        "outputs": {"project_ir": str(ir_path), "routes": str(route_path)},
    }
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
