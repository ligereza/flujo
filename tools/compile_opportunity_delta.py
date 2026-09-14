#!/usr/bin/env python3
"""Compile a semantic diff between two local opportunity-constraint versions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.flujo.knowledge.opportunity_delta import (  # noqa: E402
    OpportunityDeltaError,
    compare_opportunity_constraints,
    stable_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--output", default="-", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        previous = json.loads(args.previous.read_text(encoding="utf-8"))
        current = json.loads(args.current.read_text(encoding="utf-8"))
        payload = compare_opportunity_constraints(previous, current)
        encoded = stable_json(payload) + "\n"
        if str(args.output) == "-":
            sys.stdout.write(encoded)
        else:
            args.output.write_text(encoded, encoding="utf-8")
        return 0
    except (OSError, json.JSONDecodeError, OpportunityDeltaError) as exc:
        sys.stderr.write(json.dumps({
            "schema": "mak-opportunity-delta-error-v1",
            "error": type(exc).__name__,
            "reason": str(exc),
        }, ensure_ascii=False, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
