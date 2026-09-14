#!/usr/bin/env python3
"""Compatibility entrypoint for the canonical Flujo daily report."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from _common import repo_root


ROOT = repo_root()


def main() -> int:
    """Delegate all scoring and rendering to ``python -m flujo daily``."""
    src = str(ROOT / "src")
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src + (os.pathsep + current if current else "")
    command = [sys.executable, "-m", "flujo", "daily", *sys.argv[1:]]
    return subprocess.run(command, cwd=str(ROOT), env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
