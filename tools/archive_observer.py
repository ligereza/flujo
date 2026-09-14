#!/usr/bin/env python3
"""Thin stdout-oriented CLI for the physical archive observer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from flujo.knowledge.archive_observer import (  # noqa: E402
    ArchiveObservationError,
    observe_archive,
    serialize_batch,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe an explicit archive without modifying it")
    parser.add_argument("root", nargs="?", help="explicit directory or SSD root")
    parser.add_argument("--root", dest="root_option", help="explicit directory or SSD root")
    parser.add_argument("--archive-id", required=True, help="tenant/archive identifier")
    parser.add_argument("--prior", help="prior observation batch JSON path")
    parser.add_argument("--include", action="append", default=[], help="relative glob to include; repeatable")
    parser.add_argument("--exclude", action="append", default=[], help="relative glob to exclude; repeatable")
    parser.add_argument("--max-files", type=int, help="maximum number of file-like entries to hash/observe")
    parser.add_argument("--follow-symlinks", action="store_true", help="follow symlinks during traversal")
    parser.add_argument("--output", help="write JSON to this path; stdout is used when omitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.root and args.root_option and Path(args.root) != Path(args.root_option):
        parser.error("root positional and --root disagree")
    root = args.root_option or args.root
    if not root:
        parser.error("an explicit root is required")
    try:
        batch = observe_archive(
            root,
            args.archive_id,
            prior=args.prior,
            include=args.include,
            exclude=args.exclude,
            max_files=args.max_files,
            follow_symlinks=args.follow_symlinks,
        )
        payload = serialize_batch(batch, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        return 0
    except (ArchiveObservationError, OSError) as error:
        print(f"archive observer error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
