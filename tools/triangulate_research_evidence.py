#!/usr/bin/env python3
"""Normalize and triangulate bounded Research/Curatoria evidence packets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flujo.knowledge.research_evidence_triangulation import (  # noqa: E402
    adapt_execute_research_report,
    stable_json,
    triangulate_research_evidence,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontier", required=True, help="mak-research-frontier-jobs-v1 JSON")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--results", nargs="+", help="one or more mak-research-result-batch-v1 JSON files")
    group.add_argument("--execute-report", help="execute_research_job report JSON")
    parser.add_argument("--requirement-id", help="explicit requirement for an execute report adapter")
    parser.add_argument("--independent-source-groups", type=int, default=2)
    parser.add_argument("--output", help="write report here; stdout is the default")
    return parser


def _read(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        frontier = _read(args.frontier)
        if args.execute_report:
            batches = adapt_execute_research_report(
                _read(args.execute_report),
                requirement_id=args.requirement_id,
                independent_source_groups_required=args.independent_source_groups,
            )
        else:
            batches = [_read(path) for path in args.results]
        report = triangulate_research_evidence(frontier, batches)
        encoded = stable_json(report) + "\n"
        if args.output:
            Path(args.output).write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0 if report.get("valid") else 2
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"research_triangulation_error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
