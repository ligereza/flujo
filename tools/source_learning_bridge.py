#!/usr/bin/env python3
"""CLI for traceable source-memory ingestion into MAK Project IR."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.source_learning import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
