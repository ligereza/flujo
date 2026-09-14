#!/usr/bin/env python3
"""Compile a Project IR JSON file (or stdin) to practice evidence state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flujo.knowledge.practice_evidence_state import (  # noqa: E402
    PracticeEvidenceStateError,
    build_practice_evidence_state,
    serialize_practice_evidence_state,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="JSON input path, or - for stdin")
    parser.add_argument("--output", help="JSON output path; stdout is the default")
    parser.add_argument("--tenant", default=None, help="Optional explicit tenant")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(args.input).read_text(encoding="utf-8")
        source = json.loads(raw)
        state = build_practice_evidence_state(source, tenant=args.tenant)
        encoded = serialize_practice_evidence_state(state)
        if args.output:
            Path(args.output).write_text(encoded + "\n", encoding="utf-8")
        else:
            sys.stdout.write(encoded + "\n")
        return 0
    except (OSError, json.JSONDecodeError, PracticeEvidenceStateError) as error:
        print(f"practice_evidence_state_error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
