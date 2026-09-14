#!/usr/bin/env python3
"""Adapt explicit C04-C06 receipt files using caller-supplied bindings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flujo.knowledge.practice_receipt_adapter import (  # noqa: E402
    PracticeReceiptAdapterError,
    adapt_practice_receipts,
    serialize_practice_receipt_evidence,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c04", default="experiments/cycles/C04/real_evidence.json")
    parser.add_argument("--c05", default="experiments/cycles/C05/real_export_witness.json")
    parser.add_argument("--c06", default="experiments/cycles/C06/real_export_graph.json")
    parser.add_argument("--bindings", required=True, help="mak-practice-receipt-bindings-v1 JSON")
    parser.add_argument("--output", help="Output JSON path; stdout is the default")
    return parser


def _read(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = adapt_practice_receipts(
            _read(args.c04), _read(args.c05), _read(args.c06), _read(args.bindings)
        )
        encoded = serialize_practice_receipt_evidence(result) + "\n"
        if args.output:
            Path(args.output).write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0
    except (OSError, json.JSONDecodeError, PracticeReceiptAdapterError) as error:
        print(f"practice_receipt_adapter_error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
