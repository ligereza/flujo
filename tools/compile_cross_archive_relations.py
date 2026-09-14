#!/usr/bin/env python3
"""Compile explicit catalogue-based relation candidates across archive states."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.cross_archive_relations import (  # noqa: E402
    CrossArchiveRelationError,
    compile_cross_archive_relations,
    project_cross_archive_context,
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"not_object:{path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--practice", type=Path, action="append", required=True)
    parser.add_argument("--descriptor", type=Path, action="append", required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-output", type=Path)
    args = parser.parse_args()
    if len(args.practice) != len(args.descriptor):
        print("cross_archive_error:practice_descriptor_count_mismatch", file=sys.stderr)
        return 2
    try:
        catalog = _load(args.catalog)
        archives = []
        for practice_path, descriptor_path in zip(args.practice, args.descriptor):
            descriptor = _load(descriptor_path)
            descriptor["source_ref"] = descriptor.get("source_ref") or str(descriptor_path)
            archives.append({"practice": _load(practice_path), **descriptor})
        payload = compile_cross_archive_relations(
            archives, catalog, catalog_source_ref=str(args.catalog)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.context_output:
            context = project_cross_archive_context(payload)
            args.context_output.parent.mkdir(parents=True, exist_ok=True)
            args.context_output.write_text(json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "schema": payload["schema"],
            "archive_count": payload["reconciliation"]["archive_count"],
            "relation_count": payload["reconciliation"]["cross_archive_relation_count"],
            "context_output": str(args.context_output) if args.context_output else None,
            "output": str(args.output),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, ValueError, CrossArchiveRelationError) as exc:
        print(json.dumps({"schema": "mak-cross-archive-error-v1", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
