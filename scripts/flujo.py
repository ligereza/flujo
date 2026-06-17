#!/usr/bin/env python3
"""flujo CLI – compat shim"""
import sys
# Evitar que scripts/ haga shadow al paquete flujo
try:
    _script_dir = __import__('pathlib').Path(__file__).resolve().parent
    sys.path = [p for p in sys.path if __import__('pathlib').Path(p).resolve() != _script_dir]
except Exception:
    pass

if len(sys.argv) == 1:
    print("Comandos disponibles")
    print("  health  clean  new-flyer  daily  app  ig-redownload  flyer-import")
    print("")
    print("Ejemplos:")
    print("  py scripts/flujo.py health")
    print("  py scripts/flujo.py new-flyer \"fiesta techno\"")
    sys.exit(1)

try:
    from flujo.cli import app
    app()
except ModuleNotFoundError:
    print("Instala el paquete: py -m pip install -e .", file=sys.stderr)
    sys.exit(1)
