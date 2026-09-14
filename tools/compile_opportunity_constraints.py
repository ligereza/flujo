#!/usr/bin/env python3
"""Compile one local opportunity evidence package to JSON constraints.

The command reads JSON from a file or stdin and writes only the derived JSON
to stdout or the requested output file.  It never fetches sources or mutates a
database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.flujo.knowledge.opportunity_constraints import (  # noqa: E402
    OpportunityConstraintsError,
    compile_opportunity_constraints,
    stable_json,
)


def _read(path: str) -> object:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="-", help="JSON package path, or - for stdin")
    parser.add_argument("--output", default="-", help="JSON output path, or - for stdout")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        package = _read(args.input)
        payload = compile_opportunity_constraints(package)
        encoded = stable_json(payload) + "\n"
        if args.output == "-":
            sys.stdout.write(encoded)
        else:
            Path(args.output).write_text(encoded, encoding="utf-8")
        return 0
    except (OSError, json.JSONDecodeError, OpportunityConstraintsError) as exc:
        sys.stderr.write(json.dumps({
            "schema": "mak-opportunity-constraints-error-v1",
            "error": type(exc).__name__,
            "reason": str(exc),
        }, ensure_ascii=False, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
