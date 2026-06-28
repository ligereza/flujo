#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "sample",
    "mode",
    "word",
    "before_points",
    "after_points",
    "removed",
    "moved",
    "collapsed",
    "round_fixed",
    "approved",
    "note",
    "script_version",
}

ALLOWED_MODES = {"A", "W", "O", "R", "M"}


def validate_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    entries: list[dict[str, Any]] = []
    errors: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - exercised via CLI
                errors.append(f"line {line_number}: invalid JSON ({exc})")
                continue

            if not isinstance(payload, dict):
                errors.append(f"line {line_number}: expected a JSON object")
                continue

            missing_fields = sorted(REQUIRED_FIELDS - set(payload))
            if missing_fields:
                errors.append(
                    f"line {line_number}: missing required field(s): {', '.join(missing_fields)}"
                )
                continue

            if payload["mode"] not in ALLOWED_MODES:
                errors.append(
                    f"line {line_number}: mode must be one of {sorted(ALLOWED_MODES)}"
                )

            if not isinstance(payload["approved"], bool):
                errors.append(f"line {line_number}: approved must be a boolean")

            for field in [
                "sample",
                "word",
                "note",
                "script_version",
            ]:
                if not isinstance(payload[field], str) or not payload[field].strip():
                    errors.append(f"line {line_number}: {field} must be a non-empty string")

            for field in [
                "before_points",
                "after_points",
                "removed",
                "moved",
                "collapsed",
                "round_fixed",
            ]:
                value = payload[field]
                if not isinstance(value, int) or value < 0:
                    errors.append(f"line {line_number}: {field} must be a non-negative integer")

            entries.append(payload)

    if errors:
        raise ValueError("\n".join(errors))

    return entries


def build_summary(entries: list[dict[str, Any]]) -> str:
    approved = sum(1 for item in entries if item["approved"])
    rejected = len(entries) - approved
    average_reduction = 0.0
    if entries:
        average_reduction = sum(
            item["before_points"] - item["after_points"] for item in entries
        ) / len(entries)

    return (
        f"Validated {len(entries)} entries. "
        f"Approved={approved}, Rejected={rejected}, "
        f"Average reduction={average_reduction:.1f} points"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a logo_clean_lab JSONL dataset")
    parser.add_argument("dataset", type=Path, help="Path to the JSONL dataset to validate")
    args = parser.parse_args()

    try:
        entries = validate_dataset(args.dataset)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(build_summary(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
