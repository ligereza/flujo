"""Validate and list MAK's cultural-research-first project lanes.

This is a read-only navigation contract. It does not promote a lane, run a
model, acquire a dataset or turn a cross-domain analogy into evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from flujo.knowledge.lane_registry import (
    SCHEMA,
    LaneRegistryError,
    load_registry,
    summary,
    validate_registry,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "summary"))
    parser.add_argument("--registry", type=Path, default=Path("knowledge/lane_registry/mak_cross_domain_registry_2026-08-20.json"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        registry = load_registry(args.registry)
        errors = validate_registry(registry)
        if args.command == "validate":
            result = {"schema": SCHEMA, "status": "passed" if not errors else "failed", "errors": errors}
        else:
            result = summary(registry)
            result["status"] = "passed" if not errors else "failed"
            result["errors"] = errors
    except LaneRegistryError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
