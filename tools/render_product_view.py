#!/usr/bin/env python3
"""Render the common product outputs as JSON or a human-readable Markdown view."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flujo.knowledge.product_view import (  # noqa: E402
    ProductViewError,
    project_archive_portfolio_view,
    project_product_view,
    render_archive_portfolio_markdown,
    render_product_markdown,
    stable_json,
    validate_archive_portfolio_view,
    validate_product_view,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*")
    parser.add_argument("--archive", help="iskvw/datos/archivo.json for the general archive view")
    parser.add_argument("--max-items-per-format", type=int, default=24)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.archive:
            if args.inputs:
                raise ProductViewError("archive_mode_does_not_accept_product_inputs")
            archive = json.loads(Path(args.archive).read_text(encoding="utf-8"))
            view = project_archive_portfolio_view(
                archive,
                max_items_per_format=args.max_items_per_format,
            )
            validate_archive_portfolio_view(view)
            encoded = stable_json(view, pretty=True) + "\n" if args.format == "json" else render_archive_portfolio_markdown(view)
        else:
            if len(args.inputs) != 3:
                raise ProductViewError("product_mode_requires_three_inputs")
            values = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.inputs]
            view = project_product_view(*values)
            validate_product_view(view)
            encoded = stable_json(view, pretty=True) + "\n" if args.format == "json" else render_product_markdown(view)
        if args.output:
            Path(args.output).write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError, ProductViewError) as error:
        sys.stderr.write(f"product_view_error: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
