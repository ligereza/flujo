#!/usr/bin/env python3
"""Compile a portable mak-portfolio-dossier-v1 JSON draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flujo.knowledge.portfolio_dossier import (  # noqa: E402
    PortfolioDossierError,
    compile_portfolio_dossier,
    stable_json,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_input", nargs="?", help="plan JSON path, or - for stdin")
    parser.add_argument("practice_input", nargs="?", help="practice-state JSON path")
    parser.add_argument("--plan", dest="plan_flag", help="mak-product-plan-v1 JSON")
    parser.add_argument("--practice", dest="practice_flag", help="mak-practice-evidence-state-v1 JSON")
    parser.add_argument(
        "--technical-context",
        dest="technical_context_flag",
        help="optional mak-project-context-v1 technical evidence JSON",
    )
    parser.add_argument("--output", help="write JSON here; stdout is the default")
    return parser


def _read(path: str) -> object:
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan_path = args.plan_flag or args.plan_input
        practice_path = args.practice_flag or args.practice_input
        if not plan_path or not practice_path:
            raise PortfolioDossierError("plan_and_practice_inputs_required")
        technical_context = (
            _read(args.technical_context_flag)
            if args.technical_context_flag
            else None
        )
        dossier = compile_portfolio_dossier(
            _read(plan_path), _read(practice_path), technical_context
        )
        encoded = stable_json(dossier) + "\n"
        if args.output:
            Path(args.output).write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError, PortfolioDossierError) as error:
        print(f"portfolio_dossier_error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
