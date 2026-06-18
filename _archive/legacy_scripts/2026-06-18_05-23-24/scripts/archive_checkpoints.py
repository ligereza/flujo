#!/usr/bin/env python3
"""Mueve checkpoints antiguos a _archive/checkpoints, conservando los últimos N."""
import shutil
import sys
from pathlib import Path
from datetime import datetime

from _common import repo_root

ROOT = repo_root()
CHECKPOINTS = ROOT / "checkpoints"
ARCHIVE = ROOT / "_archive" / "checkpoints"
KEEP = 15


def main():
    if not CHECKPOINTS.exists():
        print("No existe carpeta checkpoints")
        sys.exit(0)

    files = sorted(CHECKPOINTS.glob("*.md"))
    if len(files) <= KEEP:
        print(f"Solo hay {len(files)} checkpoints; no se archiva nada.")
        sys.exit(0)

    ARCHIVE.mkdir(parents=True, exist_ok=True)

    moved = 0
    for cp in files[:-KEEP]:
        dest = ARCHIVE / cp.name
        shutil.move(str(cp), str(dest))
        moved += 1

    print(f"Archivados: {moved}")
    print(f"Conservados en checkpoints/: {KEEP}")
    print(f"Destino: {ARCHIVE}")


if __name__ == "__main__":
    main()
