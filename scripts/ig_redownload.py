#!/usr/bin/env python3
"""Shim compat – usa flujo.cli ig-redownload"""
import sys
try:
    from pathlib import Path
    _script_dir = Path(__file__).resolve().parent
    sys.path = [p for p in sys.path if Path(p).resolve() != _script_dir]
except Exception:
    pass

try:
    from flujo.cli import app
    import sys as _sys
    _sys.argv = ["flujo", "ig-redownload"] + sys.argv[1:]
    app()
except ImportError as e:
    print(f"ERROR: instala con py -m pip install -e . ({e})", file=sys.stderr)
    sys.exit(1)
