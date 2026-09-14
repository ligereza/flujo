#!/usr/bin/env python3
"""Pure CLI for building the possibility field."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.possibility_field import build_possibility_field, load_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates")
    parser.add_argument("evaluations")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = build_possibility_field(load_json(args.candidates), load_json(args.evaluations))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 1 if result.get("provenance", {}).get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
