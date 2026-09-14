#!/usr/bin/env python3
"""Compile a read-only evidence-first order from the existing SSD projections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.ssd_order_foundation import (  # noqa: E402
    SSDOrderFoundationError,
    compile_ssd_order_foundation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--order-projection", type=Path, required=True)
    parser.add_argument("--intake-db", type=Path, required=True)
    parser.add_argument("--knowledge-db", type=Path, required=True)
    parser.add_argument("--research-authority", type=Path, required=True)
    parser.add_argument("--reconstruction-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument(
        "--research-corpus-dir", type=Path,
        default=ROOT.parent / "research" / "corpus",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compile_ssd_order_foundation(
            index_path=args.index,
            order_projection_path=args.order_projection,
            intake_db=args.intake_db,
            knowledge_db=args.knowledge_db,
            research_authority_path=args.research_authority,
            reconstruction_dir=args.reconstruction_dir,
            archive_path=args.archive,
            research_corpus_dir=args.research_corpus_dir,
        )
    except (OSError, SSDOrderFoundationError) as exc:
        print(json.dumps({"schema": "mak-ssd-order-foundation-v1", "status": "abstain", "reason": str(exc)}, ensure_ascii=False))
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "semantic_hash": result["semantic_hash"],
        "inventory": result["inventory"],
        "bucket_counts": result["order"]["bucket_counts"],
        "crosswalk_to_iskvw": result["crosswalk_to_iskvw"],
        "out": str(args.out),
    }, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
