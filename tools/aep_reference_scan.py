#!/usr/bin/env python3
"""Read-only inventory of structured references in After Effects projects."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from flujo.substrate.aepfile import CONTRACT, read_references  # noqa: E402

SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "trash", "$recycle.bin"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(root: Path):
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
        for name in sorted(names):
            if name.lower().endswith(".aep"):
                yield Path(current) / name


def scan(roots: list[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for root in roots:
        root = root.expanduser().resolve()
        for path in _files(root):
            parsed = read_references(path)
            relative = str(path.relative_to(root))
            entry = {
                "root": str(root),
                "relative_path": relative,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "autosave": "almacenamiento automático" in str(path).lower(),
                "parser_contract": CONTRACT,
                "completeness": parsed.completeness,
                "chunks_seen": parsed.chunks_seen,
                "reference_count": len(parsed.declared),
                "references": parsed.declared,
            }
            if parsed.header:
                entry["header"] = {
                    "declared_size": parsed.header.declared_size,
                    "form": parsed.header.form,
                    "trailing_bytes": parsed.header.trailing_bytes,
                }
            if parsed.error:
                entry["error"] = parsed.error
            files.append(entry)
    unique_paths = {
        reference["declared_path"]
        for entry in files
        for reference in entry["references"]
    }
    return {
        "schema": "mak-aep-reference-scan-v1",
        "parser_contract": CONTRACT,
        "read_only": True,
        "emits_renders_to": False,
        "roots": [str(root.expanduser().resolve()) for root in roots],
        "file_count": len(files),
        "files_with_references": sum(bool(entry["references"]) for entry in files),
        "reference_count": sum(entry["reference_count"] for entry in files),
        "unique_declared_paths": len(unique_paths),
        "decoder_limit_files": sum(entry["completeness"] != "exhaustive" for entry in files),
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = scan(args.root)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
