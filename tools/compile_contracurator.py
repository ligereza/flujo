#!/usr/bin/env python3
"""Compile a read-only MAK Contracurador exhibition from an existing view."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.contracurator import (  # noqa: E402
    ContracuratorError,
    compile_contracurator_exhibition,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_view", type=Path, help="existing mak-archive-portfolio-view-v1 JSON")
    parser.add_argument("--output", "-o", default="-", help="output JSON path, or - for stdout")
    args = parser.parse_args(argv)
    try:
        archive_view = json.loads(args.archive_view.read_text(encoding="utf-8"))
        output = compile_contracurator_exhibition(archive_view)
        rendered = json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.output == "-":
            sys.stdout.write(rendered)
        else:
            Path(args.output).write_text(rendered, encoding="utf-8")
        return 0
    except (OSError, json.JSONDecodeError, ContracuratorError) as error:
        sys.stderr.write(json.dumps({
            "schema": "mak-contracurator-error-v1",
            "error": type(error).__name__,
            "reason": str(error),
        }, ensure_ascii=False, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
