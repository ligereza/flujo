#!/usr/bin/env python3
"""Compile Vigia discoveries into bounded capture plans without fetching."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.flujo.knowledge.vigia_capture_bridge import (  # noqa: E402
    VigiaCaptureBridgeError,
    build_vigia_capture_plans,
    capture_vigia_plans,
    stable_json,
    validate_vigia_capture_receipts,
)
from tools.research_source_capture import capture_one  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--root", required=True)
    parser.add_argument("--backend", default="auto")
    parser.add_argument("--max-plans", type=int, default=20)
    parser.add_argument("--record", action="store_true", help="execute bounded plans through capture_one(record=True)")
    parser.add_argument("--max-captures", type=int)
    parser.add_argument("--output", default="-", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        discoveries = json.loads(args.input.read_text(encoding="utf-8"))
        plans = build_vigia_capture_plans(discoveries, root=args.root, backend=args.backend, max_plans=args.max_plans)
        payload = (
            capture_vigia_plans(
                plans,
                capture_executor=capture_one,
                max_captures=args.max_captures,
            )
            if args.record else plans
        )
        if args.record and not validate_vigia_capture_receipts(plans, payload):
            raise VigiaCaptureBridgeError("capture_receipts_invalid")
        encoded = stable_json(payload) + "\n"
        if str(args.output) == "-":
            sys.stdout.write(encoded)
        else:
            args.output.write_text(encoded, encoding="utf-8")
        return 0
    except (OSError, json.JSONDecodeError, VigiaCaptureBridgeError) as exc:
        sys.stderr.write(json.dumps({"schema": "mak-vigia-capture-plans-error-v1", "error": type(exc).__name__, "reason": str(exc)}, ensure_ascii=False, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
