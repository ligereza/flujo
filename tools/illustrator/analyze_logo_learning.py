#!/usr/bin/env python3
"""Resume resultados de logo_clean_results.jsonl.

Uso:
  py tools/illustrator/analyze_logo_learning.py projects/logo_clean_lab/learning/logo_clean_results.jsonl

No requiere dependencias externas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"WARN line {line_no}: JSON invalido: {exc}")
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("Uso: py tools/illustrator/analyze_logo_learning.py <logo_clean_results.jsonl>")
        return 2

    path = Path(args[0])
    if not path.exists():
        print(f"No existe: {path}")
        return 1

    rows = load_jsonl(path)
    total = len(rows)
    approved = sum(1 for r in rows if bool(r.get("approved")))
    failed = total - approved

    print("Logo Clean Learning Summary")
    print("=" * 32)
    print(f"Archivo: {path}")
    print(f"Total: {total}")
    print(f"Aprobados: {approved}")
    print(f"Fallidos: {failed}")

    by_mode: dict[str, int] = {}
    for r in rows:
        mode = str(r.get("mode", "?")).upper()
        by_mode[mode] = by_mode.get(mode, 0) + 1

    if by_mode:
        print("\nPor modo:")
        for mode, count in sorted(by_mode.items()):
            print(f"  {mode}: {count}")

    bad_notes = [str(r.get("note", "")).strip() for r in rows if not bool(r.get("approved"))]
    bad_notes = [n for n in bad_notes if n]
    if bad_notes:
        print("\nNotas de fallos:")
        for note in bad_notes[:20]:
            print(f"  - {note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
