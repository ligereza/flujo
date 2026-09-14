#!/usr/bin/env python3
"""Evaluate product episode candidates without training or persistence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flujo.knowledge.product_learning import (  # noqa: E402
    ProductLearningError,
    evaluate_product_learning,
    stable_json,
)


def _read(path: str) -> object:
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="episode-list JSON path, or - for stdin")
    parser.add_argument("--input", "--episodes", dest="input_flag", help="episode-list JSON path, or - for stdin")
    parser.add_argument("--output", help="write the report here; stdout is the default")
    args = parser.parse_args(argv)
    input_path = args.input_flag or args.input
    try:
        if not input_path:
            raise ProductLearningError("episodes_input_required")
        value = _read(input_path)
        report = evaluate_product_learning(value)
        encoded = stable_json(report) + "\n"
        if args.output:
            Path(args.output).write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0 if report.get("valid") is True else 2
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ProductLearningError) as error:
        print(f"product_learning_error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
