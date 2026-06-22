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
    "Root clutter: DONE - moved to .archive/ (checkpoints, _archive, reference_old). Keep .archive clean too.",
    "Check _airdrop_backups/ — these are safe to prune after review (they are backups).",
    "Review docs/ for duplicates: many AGENT_*, CLEANUP, HIGIENE, MANTENIMIENTO files overlap.",
    "projects/*/salida_generada/ and working/ should stay ignored.",
    "context/DAILY.md and dashboard.html are ignored — use flujo_hub.html + visualizers instead.",
    "For agents: always start with context/flujo_hub.html + context/LAST_HANDOFF.md + docs/AGENT_OPERATING_MANUAL.md.",
    "Update remaining references to old docs (AGENT_GUIDE.md, CLI.md) to point to hub + OPERATING_MANUAL.",
    "Add deprecation notes to legacy scripts in scripts/ and reference_old/.",
]

def scan_outdated_refs():
    outdated = []
    patterns = ["AGENT_GUIDE.md", "CLI.md", "flujo flyer-import", "flujo analyze"]
    for root, _, files in os.walk(ROOT):
        if any(x in root for x in ["_archive", "checkpoints", ".git"]):
            continue
        for f in files:
            if f.endswith((".md", ".txt", ".py")):
                path = Path(root) / f
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    for pat in patterns:
                        if pat in content:
                            outdated.append(str(path.relative_to(ROOT)))
                            break
                except:
                    pass
    return set(outdated)

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

    print("\nScanning for outdated references (non-destructive):")
    bad = scan_outdated_refs()
    if bad:
        print("Found files still mentioning old docs/commands:")
        for b in sorted(bad):
            print(f"  - {b}")
        print("Suggestion: update them to point to context/flujo_hub.html + visualizers + AGENT_OPERATING_MANUAL.md")
    else:
        print("No obvious outdated refs found in active files.")

    print("\nRun 'py -m flujo health' and review docs/HIGIENE_REPO.md for more.")
    print("To actually clean, use existing scripts/cleanup_* with --dry-run first.")

if __name__ == "__main__":
    main()
