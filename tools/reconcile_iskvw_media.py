#!/usr/bin/env python3
"""Reconcile curated ISKVW records with local portfolio media by numeric ID.

The archive and the media tree are different surfaces. This tool joins only
the stable numeric ID in a filename and reports collisions instead of merging
them. Contact sheets are derivatives, not duplicate works. The command is
read-only unless an explicit output path is supplied; even then it writes only
the report, never either source.

Usage:
    python tools/reconcile_iskvw_media.py
    python tools/reconcile_iskvw_media.py --archive path/archivo.json \
        --media-root /path/to/portfolio_media/media --output report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

CONTRACT = "mak-iskvw-media-reconciliation-v1"
ID_RE = re.compile(r"^[0-9]+$")
MONTH_RE = re.compile(r"^[0-9]{6}$")


class ReconciliationError(ValueError):
    """Raised when a source cannot be read as the declared input."""


def _numeric_id(value: str) -> str | None:
    """Return a media ID from a plain or contact-sheet filename."""
    stem = Path(value).stem
    if stem.endswith(".contact"):
        stem = stem[:-8]
    if ID_RE.fullmatch(stem):
        return stem
    suffix = re.search(r"(?:^|[-_])([0-9]{10,})$", stem)
    return suffix.group(1) if suffix else None


def _archive_ids(path: Path) -> tuple[set[str], int, int]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconciliationError(f"archive_unreadable: {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("piezas"), list):
        raise ReconciliationError("archive_missing_piezas")
    ids: set[str] = set()
    with_id = 0
    without_id = 0
    for item in payload["piezas"]:
        if not isinstance(item, dict):
            continue
        medium = item.get("medio")
        candidates = []
        if isinstance(medium, dict):
            candidates.append(str(medium.get("src") or ""))
        extra = item.get("extra")
        if isinstance(extra, dict):
            original = extra.get("fuente_original")
            if isinstance(original, dict):
                candidates.append(str(original.get("ruta") or ""))
        candidates.append(str(item.get("id") or ""))
        media_id = next((_numeric_id(value) for value in candidates if value), None)
        if media_id:
            with_id += 1
            ids.add(media_id)
        else:
            without_id += 1
    return ids, with_id, without_id


def _media_rows(root: Path, wanted: set[str]) -> Iterable[dict[str, Any]]:
    if not root.is_dir():
        raise ReconciliationError(f"media_root_missing: {root}")
    for current, _dirs, files in os.walk(root, followlinks=False):
        for name in sorted(files):
            media_id = _numeric_id(name)
            if media_id not in wanted:
                continue
            path = Path(current) / name
            relative = path.relative_to(root)
            parts = relative.parts
            surface = parts[0] if parts else "root"
            month = parts[1] if len(parts) > 2 and MONTH_RE.fullmatch(parts[1]) else None
            yield {
                "id": media_id,
                "path": relative.as_posix(),
                "surface": surface,
                "yyyymm": month,
                "filename": name,
                "derivative": surface == "_contact_sheets",
            }


def reconcile(archive: Path, media_root: Path) -> dict[str, Any]:
    """Build a deterministic join report without changing either source."""
    wanted, with_id, without_id = _archive_ids(archive)
    matches: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _media_rows(media_root, wanted):
        matches[row["id"]].append(row)

    orphan = sorted(wanted - set(matches))
    cross_surface = []
    same_surface = []
    unique_surface = []
    for media_id in sorted(matches):
        rows = sorted(matches[media_id], key=lambda row: row["path"])
        surfaces = {row["surface"] for row in rows}
        if len(surfaces) > 1:
            cross_surface.append({"id": media_id, "matches": rows})
        else:
            unique_surface.append(media_id)
            if len(rows) > 1:
                same_surface.append({"id": media_id, "matches": rows})

    surface_counts = Counter(
        rows[0]["surface"] for media_id, rows in matches.items()
        if media_id in unique_surface
    )
    return {
        "schema": CONTRACT,
        "read_only": True,
        "sources": {"archive": str(archive), "media_root": str(media_root)},
        "summary": {
            "archive_numeric_ids": len(wanted),
            "archive_records_with_numeric_id": with_id,
            "archive_records_without_numeric_id": without_id,
            "ids_with_one_surface": len(unique_surface),
            "ids_with_cross_surface_collision": len(cross_surface),
            "orphan_ids": len(orphan),
            "ids_with_same_surface_multiple_files": len(same_surface),
            "matched_files": sum(len(rows) for rows in matches.values()),
            "surface_counts": dict(sorted(surface_counts.items())),
        },
        "orphan_ids": orphan,
        "cross_surface_collisions": cross_surface,
        "same_surface_multiple_files": same_surface,
        "matches": {key: sorted(value, key=lambda row: row["path"])
                    for key, value in sorted(matches.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--archive", type=Path,
                        default=root / "iskvw" / "datos" / "archivo.json")
    parser.add_argument("--media-root", type=Path,
                        default=Path("/home/mak/portfolio_media/media"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    report = reconcile(args.archive, args.media_root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({"schema": CONTRACT, "read_only": True,
                      **report["summary"]}, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
