"""Project a local Match Charting CSV into conservative MAK JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from flujo.tennis.mcp import write_jsonl


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        rows = write_jsonl(args.source, args.destination)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"status": "passed", "rows": rows, "destination": str(args.destination)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
