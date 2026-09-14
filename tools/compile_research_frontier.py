#!/usr/bin/env python3
"""Compile a possibility field into planned, non-dispatched Research jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.flujo.knowledge.research_frontier_bridge import (  # noqa: E402
    ResearchFrontierBridgeError,
    compile_research_frontier,
    stable_json,
)


def _load(path: str) -> object:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("possibility", help="mak-possibility-field-v1 JSON")
    parser.add_argument("fit", help="mak-opportunity-fit-v1 JSON")
    parser.add_argument("opportunity", help="mak-opportunity-constraints-v1 JSON")
    parser.add_argument("--output", "-o", default="-", help="output path, or - for stdout")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        payload = compile_research_frontier(
            _load(args.possibility), _load(args.fit), _load(args.opportunity)
        )
        encoded = stable_json(payload) + "\n"
        if args.output == "-":
            sys.stdout.write(encoded)
        else:
            Path(args.output).write_text(encoded, encoding="utf-8")
        return 0
    except (OSError, json.JSONDecodeError, ResearchFrontierBridgeError) as exc:
        sys.stderr.write(json.dumps({
            "schema": "mak-research-frontier-jobs-error-v1",
            "error": type(exc).__name__,
            "reason": str(exc),
        }, ensure_ascii=False, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
