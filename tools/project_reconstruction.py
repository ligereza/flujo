#!/usr/bin/env python3
"""Reconstruct and persist one creative project scope from a MAK SSD index."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from flujo.knowledge.project_reconstruction import (
    baseline_view,
    reconstruct,
    write_payload,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--attestations",
        type=Path,
        help="Optional JSON with explicit operator attestations.",
    )
    args = parser.parse_args(argv)
    attestations = {}
    if args.attestations:
        attestations = json.loads(args.attestations.read_text(encoding="utf-8"))
    result = reconstruct(args.index, args.scope, attestations=attestations)
    paths = write_payload(result, args.out_dir)
    output = {
        "status": "passed",
        "schema": result.contract,
        "scope": result.scope,
        "baseline": baseline_view(args.index, args.scope),
        "summary": result.summary(),
        "outputs": paths,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
