#!/usr/bin/env python3
"""Build the current exact-duplicate decision matrix from the canonical map."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path("/home/mak")
MAP_PATH = ROOT / "indexes" / "mak-canonical-20260829" / "mak-canonical-map.json"
OUTPUT_DIR = ROOT / "indexes" / "mak-consolidation-20260829"
CSV_PATH = OUTPUT_DIR / "exact-duplicate-candidates-v2.csv"
SUMMARY_PATH = OUTPUT_DIR / "exact-duplicate-decision-summary-v2.json"
RETIREMENT_MAP_PATH = ROOT / "_archive" / "orden-limpieza-20260828" / "mapa-de-retiro.csv"

PROTECTED_TOPS = {"WIN", "curatoria_inbox", "GoogleDrive", "OneDrive"}
TECHNICAL_TOPS = {
    "_archive",
    "backups",
    "go",
    "opt",
    "apps",
    "models",
    "venv-providers",
    "venvs",
    "searxng",
    "codex",
    "xio_puente",
    "blender",
    "portfolio_media",
    "renders",
    "state",
    "labs",
    "actions-runner",
    "bin",
    "WhiteSur-icon-theme",
    "src",
    "bucle",
}
HIDDEN_PREFIXES = (
    ".cache/",
    ".config/",
    ".local/",
    ".claude/",
    ".codex/",
    ".venvs/",
    ".ssh/",
    ".gnupg/",
    ".ollama/",
    ".lmstudio/",
    ".mozilla/",
    ".npm/",
    ".vscode/",
    ".continue/",
    ".crawl4ai/",
    ".gemini/",
    ".idlerc/",
    ".ipython/",
    ".wine/",
    ".pki/",
    ".themes/",
    ".icons/",
    ".dotnet/",
    ".nv/",
    ".aws/",
)


def top(path: str) -> str:
    return path.split("/", 1)[0]


def excluded(path: str, repo_roots: list[str]) -> bool:
    first = top(path)
    return (
        first in PROTECTED_TOPS
        or first in TECHNICAL_TOPS
        or path == ".git"
        or path.startswith(".git/")
        or any(path == root or path.startswith(root + "/") for root in repo_roots)
        or path.startswith(HIDDEN_PREFIXES)
        or path.endswith((".lock", ".wal", ".shm", ".log", "-wal", "-shm"))
        or "/logs/" in path
    )


def classify(paths: list[str]) -> tuple[str, str, str]:
    roots = {top(path) for path in paths}
    if any(path.startswith("research/") or path.startswith("plataforma/") for path in paths):
        return (
            "live_runtime",
            "defer_live_runtime",
            "same bytes can belong to different run databases or inputs; service was live during measurement",
        )
    if any(path.startswith("trazos/") for path in paths):
        return (
            "trazos",
            "preserve_semantic_path",
            "the filename is an ID consumed as a locator; identical SVG bytes do not erase that relation",
        )
    if any(path.startswith("RD/") for path in paths):
        return (
            "rd",
            "preserve_semantic_path",
            "path separates source, version, export, evidence, delivery or production role",
        )
    if any("historia git" in path.lower() or "repos-y-herramientas" in path.lower() for path in paths):
        return (
            "git_artifact",
            "out_of_scope_git",
            "Git history/document artifact is outside this consolidation write set",
        )
    if any(path.startswith("tools/") for path in paths):
        return (
            "tool_fixture",
            "preserve_semantic_path",
            "tool test fixture paths are part of the tool tree and were not merged",
        )
    return (
        "other",
        "preserve_semantic_path",
        "no safe semantic authority was established from the current evidence",
    )


def retirement_summary() -> tuple[int, dict[str, int]]:
    if not RETIREMENT_MAP_PATH.is_file():
        return 0, {}
    with RETIREMENT_MAP_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    counts = Counter(row.get("razon", "") for row in rows)
    return len(rows), dict(sorted(counts.items()))


def main() -> int:
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    repo_roots = [entry["relative_path"][:-5] for entry in data["entries"] if entry["relative_path"].endswith("/.git")]
    files = [
        entry
        for entry in data["entries"]
        if entry.get("kind") == "file"
        and entry.get("sha256")
        and not excluded(entry["relative_path"], repo_roots)
    ]
    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in files:
        groups[entry["sha256"]].append(entry)

    rows: list[dict] = []
    categories = Counter()
    decisions = Counter()
    duplicate_groups = [(sha, items) for sha, items in groups.items() if len(items) > 1]
    duplicate_groups.sort(key=lambda pair: (min(entry["relative_path"] for entry in pair[1]), pair[0]))
    for number, (sha, items) in enumerate(duplicate_groups, 1):
        paths = [entry["relative_path"] for entry in items]
        category, decision, reason = classify(paths)
        categories[category] += 1
        decisions[decision] += 1
        group_id = f"D{number:03d}"
        group_roots = "|".join(sorted({top(path) for path in paths}))
        for entry in sorted(items, key=lambda item: item["relative_path"]):
            rows.append(
                {
                    "group_id": group_id,
                    "sha256": sha,
                    "size_bytes": entry["size_bytes"],
                    "path": entry["path"],
                    "relative_path": entry["relative_path"],
                    "category": category,
                    "decision": decision,
                    "reason": reason,
                    "group_roots": group_roots,
                }
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])) if rows else None
        if writer:
            writer.writeheader()
            writer.writerows(rows)

    retirement_rows, retirement_reasons = retirement_summary()
    summary = {
        "schema": "mak-exact-duplicate-decision-summary-v2",
        "map_path": str(MAP_PATH),
        "map_generated_at": data["generated_at"],
        "scope": "regular files only; protected roots, Git trees, runtime metadata, technical trees, locks, WAL/SHM and logs excluded",
        "current_groups": len(duplicate_groups),
        "current_rows": len(rows),
        "current_extra_regular_paths": sum(len(items) - 1 for _, items in duplicate_groups),
        "current_repeated_bytes": sum((len(items) - 1) * items[0]["size_bytes"] for _, items in duplicate_groups),
        "prechange_groups": 128,
        "initial_write_set": {
            "consolidated_groups": 15,
            "consolidated_archive_files": 15,
            "canonical_files_selected": 6,
            "compatibility_symlinks_selected": 20,
        },
        "retirement_map_rows": retirement_rows,
        "retirement_map_reason_counts": retirement_reasons,
        "categories": dict(sorted(categories.items())),
        "decisions": dict(sorted(decisions.items())),
        "csv_path": str(CSV_PATH),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
