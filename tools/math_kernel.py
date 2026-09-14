#!/usr/bin/env python3
"""Bounded metadata-only Math Kernel scheduler for MAK."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.knowledge.math_kernel import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
