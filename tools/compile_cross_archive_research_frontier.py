#!/usr/bin/env python3
"""Compile cross-archive relation evidence gaps into non-dispatched Research jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.cross_archive_research_frontier import (  # noqa: E402
    CrossArchiveResearchFrontierError,
    compile_cross_archive_research_frontier,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(args.relations.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("relations_not_object")
        frontier = compile_cross_archive_research_frontier(payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(frontier, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "schema": frontier["schema"],
            "job_count": frontier["reconciliation"]["job_count"],
            "dispatch_count": frontier["reconciliation"]["dispatch_count"],
            "output": str(args.output),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, ValueError, CrossArchiveResearchFrontierError) as exc:
        print(json.dumps({"schema": "mak-cross-archive-research-error-v1", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
