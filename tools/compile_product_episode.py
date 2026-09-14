#!/usr/bin/env python3
"""Compile a pure MAK product episode candidate; never writes the ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.product_episode import (  # noqa: E402
    ProductEpisodeError,
    compile_product_episode,
    stable_json,
)


def _load(path: str) -> object:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product_plan", help="mak-product-plan-v1 JSON")
    parser.add_argument("portfolio_dossier", help="mak-portfolio-dossier-v1 JSON")
    parser.add_argument("application_package", help="mak-application-research-package-v1 JSON")
    parser.add_argument("--outcome", help="optional mak-product-outcome-receipt-v1 JSON")
    parser.add_argument("--output", "-o", default="-", help="output path, or - for stdout")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        outcome = _load(args.outcome) if args.outcome else None
        payload = compile_product_episode(
            _load(args.product_plan),
            _load(args.portfolio_dossier),
            _load(args.application_package),
            outcome,
        )
        rendered = stable_json(payload) + "\n"
        if args.output == "-":
            sys.stdout.write(rendered)
        else:
            Path(args.output).write_text(rendered, encoding="utf-8")
        return 0
    except (OSError, json.JSONDecodeError, ProductEpisodeError) as exc:
        sys.stderr.write(json.dumps({
            "schema": "mak-product-episode-error-v1",
            "error": type(exc).__name__,
            "reason": str(exc),
        }, ensure_ascii=False, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
