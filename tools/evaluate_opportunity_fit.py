#!/usr/bin/env python3
"""Read-only CLI for evaluating the opportunity-practice link."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.opportunity_fit import evaluate_opportunity_fit, load_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("opportunity")
    parser.add_argument("practice")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_opportunity_fit(load_json(args.opportunity), load_json(args.practice))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"schema": "mak-opportunity-fit-v1", "decision": "abstain", "validation": {"valid": False, "errors": [f"input_read_error:{exc.__class__.__name__}"]}}
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result.get("validation", {}).get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
