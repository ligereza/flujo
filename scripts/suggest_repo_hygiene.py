#!/usr/bin/env python3
"""
suggest_repo_hygiene.py — Non-destructive suggestions for repo cleanup.

Run: py scripts/suggest_repo_hygiene.py

This only prints recommendations. It never deletes or moves files.
See docs/HIGIENE_REPO.md and context/README.md for policy.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUGGESTIONS = [
    "Root clutter: consider moving old checkpoints/ and _archive/ subdirs to .archive/ or git-annex if size is issue.",
    "Check _airdrop_backups/ — these are safe to prune after review (they are backups).",
    "Review docs/ for duplicates: AGENT_GUIDE.md vs AGENT_OPERATING_MANUAL.md, multiple CLEANUP/HIGIENE files.",
    "projects/*/salida_generada/ and working/ should stay ignored (already in .gitignore).",
    "context/DAILY.md and dashboard.html are ignored — use flujo_hub.html instead.",
    "Update any remaining references to old commands (flyer-import, analyze) to point to hub intake.",
    "For agents: always start with context/flujo_hub.html + context/LAST_HANDOFF.md.",
]

def main():
    print("=== Non-destructive repo hygiene suggestions ===")
    print(f"Scanning from {ROOT}\n")

    # Check obvious clutter
    clutter = ["_archive", "checkpoints", "_airdrop_backups", "reference_old", "_logs"]
    for d in clutter:
        p = ROOT / d
        if p.exists():
            count = sum(1 for _ in p.rglob("*"))
            print(f"⚠️  {d}/ exists with ~{count} items — candidate for archive or prune (see .archive policy).")

    print("\nRecommendations (no action taken):")
    for s in SUGGESTIONS:
        print(f" - {s}")

    print("\nRun 'py -m flujo health' and review docs/HIGIENE_REPO.md for more.")
    print("To actually clean, use existing scripts/cleanup_* with --dry-run first.")

if __name__ == "__main__":
    main()
