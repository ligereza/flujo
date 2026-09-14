#!/usr/bin/env python3
"""Read and rebuild one archive's operational membership view."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.flujo.knowledge.operational_memberships import (  # noqa: E402
    OperationalMembershipError,
    project_archive_capabilities,
    project_store_memberships,
)
from src.flujo.knowledge.project_ir import LearningStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--archive-id", required=True)
    parser.add_argument(
        "--projection",
        type=Path,
        help="optional Stage 2A JSON projection for read-only capability availability",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = project_store_memberships(LearningStore(args.db), args.archive_id)
        if args.projection:
            projection = json.loads(args.projection.read_text(encoding="utf-8"))
            if projection.get("archive_id") != args.archive_id:
                raise OperationalMembershipError("capability_archive_isolation_invalid")
            capability_payload = project_archive_capabilities(projection)
            payload = dict(payload)
            payload["capability_projection"] = capability_payload
    except (OperationalMembershipError, OSError, ValueError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
