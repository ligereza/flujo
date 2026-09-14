#!/usr/bin/env python3
"""Compare two materialized output manifests against an opportunity delta."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.flujo.knowledge.opportunity_delta import validate_opportunity_delta  # noqa: E402
from src.flujo.knowledge.selective_recompute_receipt import (  # noqa: E402
    SelectiveRecomputeReceiptError,
    build_selective_recompute_receipt,
    stable_json,
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_outputs(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or not isinstance(value.get("outputs"), list):
        raise SelectiveRecomputeReceiptError("manifest_outputs_missing")
    rows = value["outputs"]
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not isinstance(row.get("sha256"), str):
            raise SelectiveRecomputeReceiptError("manifest_output_invalid")
        if row["name"] in result:
            raise SelectiveRecomputeReceiptError("manifest_output_duplicate")
        result[row["name"]] = row["sha256"]
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-constraints", required=True, type=Path)
    parser.add_argument("--current-constraints", required=True, type=Path)
    parser.add_argument("--delta", required=True, type=Path)
    parser.add_argument("--before-manifest", required=True, type=Path)
    parser.add_argument("--after-manifest", required=True, type=Path)
    parser.add_argument("--output", default="-", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        previous = _load(args.previous_constraints)
        current = _load(args.current_constraints)
        delta = _load(args.delta)
        payload = build_selective_recompute_receipt(
            previous, current, delta,
            _manifest_outputs(_load(args.before_manifest)),
            _manifest_outputs(_load(args.after_manifest)),
        )
        encoded = stable_json(payload) + "\n"
        if str(args.output) == "-":
            sys.stdout.write(encoded)
        else:
            args.output.write_text(encoded, encoding="utf-8")
        return 0
    except (OSError, json.JSONDecodeError, SelectiveRecomputeReceiptError, KeyError) as exc:
        sys.stderr.write(json.dumps({"schema": "mak-selective-recompute-receipt-error-v1", "error": str(exc)}, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
