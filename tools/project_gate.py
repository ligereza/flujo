#!/usr/bin/env python3
"""Route and optionally record one Project IR consumer probe.

Default mode is read-only.  ``--record`` appends one episode to the explicit
learning database; it still never executes the selected consumer.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.episode_runner import probe_declared_consumer, record_probe  # noqa: E402
from flujo.knowledge.project_api import promoted_rules  # noqa: E402
from flujo.knowledge.project_router import route_project  # noqa: E402
from flujo.knowledge.project_ir import LearningStore  # noqa: E402


def load_project(database: Path, project_id: str) -> dict:
    if not database.is_file():
        raise FileNotFoundError(f"learning_database_missing: {database}")
    with sqlite3.connect("file:" + str(database) + "?mode=ro", uri=True) as con:
        row = con.execute("SELECT ir_json FROM project_records WHERE project_id=?", (project_id,)).fetchone()
    if not row:
        raise ValueError(f"project_not_found: {project_id}")
    project = json.loads(row[0])
    if not isinstance(project, dict):
        raise ValueError("project_ir_not_object")
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--record", action="store_true", help="append the probe episode")
    parser.add_argument("--episode-id", default=None)
    args = parser.parse_args(argv)
    project = load_project(args.db, args.project_id)
    decision = route_project(project, rules=promoted_rules(args.db))
    probe = probe_declared_consumer(project, decision, repo_root=ROOT)
    episode_id = None
    if args.record:
        episode_id = record_probe(
            LearningStore(args.db), project, decision, probe,
            episode_id=args.episode_id,
        )
    print(json.dumps({
        "project_id": args.project_id,
        "decision": decision,
        "probe": probe,
        "recorded": bool(args.record),
        "episode_id": episode_id,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
