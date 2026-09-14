#!/usr/bin/env python3
"""plano_stands.py — wrapper local del motor de planos de flujo.

Este script sigue siendo autónomo, pero delega la lógica en
`flujo.plano` para que el mismo motor se pueda usar desde la CLI (`flujo plano`)
y testear como módulo Python.

Uso:
    python plano_stands.py ejemplos/evento_ejemplo.json > plano.svg
    python plano_stands.py ejemplos/evento_ejemplo.json --rider  # rider de texto
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _configure_io() -> None:
    """Asegura UTF-8 en stdout/stderr para evitar errores de encoding en Windows."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def _add_src_to_path() -> None:
    """Asegura que src/ del repo esté en sys.path para poder importar flujo."""
    try:
        root = Path(__file__).resolve().parents[2]
    except Exception:
        # fallback si __file__ no está disponible
        root = Path.cwd()
    src = root / "src"
    if src.exists():
        src_str = str(src)
        src_posix = src.as_posix()
        if src_str not in sys.path and src_posix not in sys.path:
            sys.path.insert(0, src_str)
    # también respetar PYTHONPATH si existe
    for p in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if p and p not in sys.path:
            sys.path.insert(0, p)


_configure_io()
_add_src_to_path()

try:
    from flujo.plano import load_evento, render_svg, render_rider
except Exception as exc:
    print(f"ERROR: no se pudo importar flujo.plano: {exc}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise SystemExit(1)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print(__doc__)
        return 0
    try:
        path = argv[0]
        ev = load_evento(Path(path))
        if "--rider" in argv:
            print(render_rider(ev))
        else:
            print(render_svg(ev))
    except Exception as exc:
        print(f"ERROR al generar plano: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
