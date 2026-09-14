#!/usr/bin/env python3
"""
suggest_repo_hygiene.py — Non-destructive suggestions for repo cleanup.

Run: py scripts/suggest_repo_hygiene.py

Two parts:
1. Doc/reference hygiene: flags files that still point at dead docs or
   dead code paths (instaloader, AGENT_GUIDE.md, etc -- the class of bug
   fixed 2026-07-20).
2. Test-quality signal: runs the suite with coverage and prints the
   worst-covered live source files, so "how many tests" stops being the
   proxy for "how tested" -- see .claude/skills/godspeed/SKILL.md point 6.

This only prints recommendations. It never deletes, moves, or edits files.
See the current checkout and its automated tests for policy.

Invoked by hand only -- no cron, Makefile target, or workflow calls this
(verified 2026-07-30). It stays in scripts/ as a manual coverage signal, not
as automation.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUGGESTIONS = [
    "Root clutter: DONE - moved to .archive/ (checkpoints, _archive, reference_old). Keep .archive clean too.",
    "Check _airdrop_backups/ — these are safe to prune after review (they are backups).",
    "Review docs/ for duplicates: many AGENT_*, CLEANUP, HIGIENE, MANTENIMIENTO files overlap.",
    "projects/*/salida_generada/ and working/ should stay ignored.",
    "context/DAILY.md and dashboard.html are ignored — use flujo_hub.html + visualizers instead.",
    "Verify the current checkout and runtime before acting; do not infer authority from archived notes.",
    "Add deprecation notes to legacy scripts in scripts/ and reference_old/.",
    "Test count is not a quality signal: a test mocking a module the source no longer imports is false coverage (real case: instaloader in ig/download.py, fixed 2026-07-20). Prune those when found, don't just add more beside them.",
]

# patterns that mean a file still points at something dead
STALE_PATTERNS = [
    "AGENT_GUIDE.md",
    "AGENT_OPERATING_MANUAL.md",
    "docs/AI_OPERATING_LAYER.md",
    "docs/AI_PROVIDER_ROUTING.md",
    "docs/REPO_MAP.md",
    "instaloader",
    "yt-dlp",
]


def scan_outdated_refs():
    outdated = {}
    for root, _, files in os.walk(ROOT):
        if any(x in root for x in ["_archive", ".archive", "checkpoints", ".git", "node_modules"]):
            continue
        for f in files:
            if f.endswith((".md", ".txt", ".py")):
                path = Path(root) / f
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                hits = [pat for pat in STALE_PATTERNS if pat in content]
                if hits:
                    outdated[str(path.relative_to(ROOT))] = hits
    return outdated


def coverage_lowlights(threshold=60, top_n=8):
    """Run the suite with coverage, return the worst-covered live files.

    Best-effort: if pytest-cov isn't installed or the run fails, returns
    None instead of raising -- this is a suggestion tool, not a gate.
    """
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "coverage.json"
        cmd = [
            sys.executable, "-m", "pytest", "tests/", "-q",
            "--cov=src/flujo", f"--cov-report=json:{report}",
        ]
        try:
            subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=600, check=False)
            data = json.loads(report.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 -- best-effort, never blocks
            return None, f"coverage run skipped: {exc}"

        total_pct = data.get("totals", {}).get("percent_covered", 0.0)
        files = data.get("files", {})
        rows = [
            (path, info["summary"]["percent_covered"], info["summary"]["num_statements"])
            for path, info in files.items()
        ]
        # weight by size too: a 20-line file at 0% matters less than a
        # 1000-line one at 20%
        rows.sort(key=lambda r: (r[1], -r[2]))
        worst = [r for r in rows if r[1] < threshold][:top_n]
        return (total_pct, worst), None


def main():
    print("=== Non-destructive repo hygiene suggestions ===")
    print(f"Scanning from {ROOT}\n")

    clutter = ["_archive", "checkpoints", "_airdrop_backups", "reference_old", "_logs"]
    for d in clutter:
        p = ROOT / d
        if p.exists():
            count = sum(1 for _ in p.rglob("*"))
            print(f"[!] {d}/ exists with ~{count} items — candidate for archive or prune (see .archive policy).")

    print("\nRecommendations (no action taken):")
    for s in SUGGESTIONS:
        print(f" - {s}")

    print("\nScanning for stale doc/code references (non-destructive):")
    bad = scan_outdated_refs()
    if bad:
        print("Found files still mentioning dead docs/commands:")
        for path, hits in sorted(bad.items()):
            print(f"  - {path}: {', '.join(hits)}")
        print("Suggestion: remove or replace each dead reference with a measured source.")
    else:
        print("No stale references found in active files.")

    print("\nCoverage signal (worst-covered live files, best-effort):")
    result, err = coverage_lowlights()
    if err:
        print(f"  ({err})")
    else:
        total_pct, worst = result
        print(f"  TOTAL coverage: {total_pct:.0f}%")
        if worst:
            for path, pct, stmts in worst:
                print(f"  - {path}: {pct:.0f}% covered ({stmts} statements)")
        else:
            print("  No file under threshold.")

    print("\nRun 'python -m fluxo health' and review the measured output.")
    print("To actually clean, use existing scripts/cleanup_* with --dry-run first.")


if __name__ == "__main__":
    main()
