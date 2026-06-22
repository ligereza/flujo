#!/usr/bin/env python3
"""plano_stands.py — wrapper local del motor de planos de flujo.

Este script sigue siendo autónomo, pero ahora delega la lógica en
`flujo.plano` para que el mismo motor se pueda usar desde la CLI (`flujo plano`)
y testear como módulo Python.

Uso:
    python plano_stands.py ejemplos/evento_ejemplo.json > plano.svg
    python plano_stands.py ejemplos/evento_ejemplo.json --rider  # rider de texto
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permite ejecutar el script sin tener instalado el paquete editable
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from flujo.plano import load_evento, render_svg, render_rider


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print(__doc__)
        return 0
    path = argv[0]
    ev = load_evento(Path(path))
    if "--rider" in argv:
        print(render_rider(ev))
    else:
        print(render_svg(ev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
