#!/usr/bin/env python3
"""Evaluate provisional artistic-program candidates against Piso 1 inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flujo.knowledge.artistic_program_evaluator import (  # noqa: E402
    ArtisticProgramEvaluationError,
    evaluate_artistic_program_payload,
    stable_json,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity", required=True, help="mak-opportunity-constraints-v1 JSON")
    parser.add_argument("--practice", required=True, help="mak-practice-evidence-state-v1 JSON")
    parser.add_argument("--fit", required=True, help="mak-opportunity-fit-v1 JSON")
    parser.add_argument("--candidates", required=True, help="mak-artistic-program-candidates-v1 JSON")
    parser.add_argument("--output", help="write report here; stdout is the default")
    return parser


def _read(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = evaluate_artistic_program_payload(
            _read(args.opportunity), _read(args.practice), _read(args.fit), _read(args.candidates)
        )
        encoded = stable_json(report) + "\n"
        if args.output:
            Path(args.output).write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0 if report.get("valid") else 2
    except (OSError, json.JSONDecodeError, ArtisticProgramEvaluationError, TypeError, ValueError) as error:
        print(f"artistic_program_evaluation_error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
