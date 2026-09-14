#!/usr/bin/env python3
"""CLI wrapper for MAK's verified-episode learning policy."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.learning_policy import _cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
