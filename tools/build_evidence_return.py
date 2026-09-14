#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from flujo.knowledge.evidence_return import build_evidence_return, load_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in ("opportunity", "practice", "fit", "frontier", "triangulation"):
        parser.add_argument(name)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = build_evidence_return(*(load_json(getattr(args, name)) for name in ("opportunity", "practice", "fit", "frontier", "triangulation")))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
