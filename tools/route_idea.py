#!/usr/bin/env python3
"""Route one idea to the smallest context packet for an external agent."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo.diagnostics import render_route_markdown, route_idea  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("idea", help="Idea or incident in natural language.")
    parser.add_argument("--area", default="auto", help="core|rd|portfolio|cultura|research|auto")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    route = route_idea(args.idea, area=args.area, root=ROOT)
    if args.format == "json":
        print(json.dumps(route, ensure_ascii=False, indent=2))
    else:
        print(render_route_markdown(route), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
