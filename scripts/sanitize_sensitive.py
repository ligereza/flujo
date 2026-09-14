#!/usr/bin/env python3
"""sanitize_sensitive.py — Reemplaza información sensible por placeholders"""

import re
from pathlib import Path

PATTERNS = [
    (r'password\s*=\s*["\'][^"\']+["\']', 'password = "REDACTED"'),
    (r'api_key\s*=\s*["\'][^"\']+["\']', 'api_key = "REDACTED"'),
    (r'token\s*=\s*["\'][^"\']+["\']', 'token = "REDACTED"'),
    (r'C:\\\\Users\\\\[^\\\\]+', 'C:\\\\Users\\\\USER'),
    (r'/home/[^/]+', '/home/USER'),
]


def sanitize_text(text: str) -> str:
    for pattern, replacement in PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def sanitize_file(path: Path, output: Path | None = None) -> Path:
    text = path.read_text(encoding="utf-8", errors="ignore")
    cleaned = sanitize_text(text)
    out = output or path.with_suffix(".sanitized" + path.suffix)
    out.write_text(cleaned, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    import sys
    args = argv or sys.argv[1:]
    if not args:
        print("Uso: sanitize_sensitive.py <archivo> [salida]")
        return 1
    src = Path(args[0])
    dst = Path(args[1]) if len(args) > 1 else None
    out = sanitize_file(src, dst)
    print(f"Sanitizado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
