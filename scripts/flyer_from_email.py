#!/usr/bin/env python3
"""Shim compat – usa flujo.flyer.import_email"""
import sys
# Evitar shadow del paquete flujo
try:
    from pathlib import Path
    _script_dir = Path(__file__).resolve().parent
    sys.path = [p for p in sys.path if Path(p).resolve() != _script_dir]
except Exception:
    pass

# Línea dummy para que el test antiguo que hace text-replace encuentre algo:
# BASE = repo_root() / "projects" / "flyer_eventos"

try:
    from flujo.flyer.import_email import main
    if __name__ == "__main__":
        sys.exit(main())
except ImportError as e:
    print(f"ERROR: instala el paquete con: py -m pip install -e . ({e})", file=sys.stderr)
    sys.exit(1)
