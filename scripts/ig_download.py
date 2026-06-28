#!/usr/bin/env python3
"""Shim compat – usa flujo.ig.download"""
import sys
# Evitar shadow: quitar scripts/ del path antes de importar flujo
try:
    from pathlib import Path
    _script_dir = Path(__file__).resolve().parent
    sys.path = [p for p in sys.path if Path(p).resolve() != _script_dir]
except Exception:
    pass

try:
    from flujo.ig.download import download_post, extract_shortcode
except ImportError as e:
    print(f"ERROR: instala con py -m pip install -e . ({e})", file=sys.stderr)
    sys.exit(1)

# re-export para tests legacy
__all__ = ["download_post", "extract_shortcode"]

def main():
    if len(sys.argv) < 3:
        print("Uso: py scripts/ig_download.py <url> <output_dir>")
        sys.exit(1)
    from pathlib import Path
    url, out = sys.argv[1], Path(sys.argv[2])
    res = download_post(url, out)
    print(res)
    sys.exit(0 if res.get("status") == "downloaded" else 1)

if __name__ == "__main__":
    main()
