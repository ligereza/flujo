#!/usr/bin/env python3
"""Cambia la paleta de un SVG RD entre dark / blanco / gris (aproximado).

Uso: py tools/svg/recolor_svg.py IN.svg OUT.svg --to blanco|dark|gris
Detecta la paleta origen por los hex presentes y mapea rol->rol. Revisa el
resultado: no adivina colores fuera de la paleta canonica.
"""
import sys, re
from pathlib import Path

DARK   = {"bg": "#0A0A0A", "ink": "#F2F2F2", "accent": "#C800C8", "high": "#FFD21F", "muted": "#A79FA8", "panel": "#161318", "line": "#3A2F3D"}
BLANCO = {"bg": "#FFFFFF", "ink": "#141414", "accent": "#141414", "high": "#141414", "muted": "#6B7280", "panel": "#FFFFFF", "line": "#E5E7EB"}
GRIS   = {"bg": "#0E0E0E", "ink": "#F2F2F2", "accent": "#B8B8B8", "high": "#EDEDED", "muted": "#9C9C9C", "panel": "#1B1B1B", "line": "#4A4A4A"}
PAL = {"dark": DARK, "blanco": BLANCO, "gris": GRIS}

def main():
    if len(sys.argv) < 3 or "--to" not in sys.argv:
        raise SystemExit(__doc__)
    inp, out = sys.argv[1], sys.argv[2]
    to = sys.argv[sys.argv.index("--to") + 1]
    if to not in PAL:
        raise SystemExit("--to debe ser blanco|dark|gris")
    s = Path(inp).read_text(encoding="utf-8")
    # paleta origen = la que mas hex coincide
    best, bestn = "dark", -1
    for name, pal in PAL.items():
        n = sum(1 for v in pal.values() if v.lower() in s.lower())
        if n > bestn:
            best, bestn = name, n
    src, dst = PAL[best], PAL[to]
    for role in src:
        s = re.sub(re.escape(src[role]), dst[role], s, flags=re.I)
    Path(out).write_text(s, encoding="utf-8")
    print(f"{best} -> {to}: {out}  ({bestn} colores de origen detectados)")

if __name__ == "__main__":
    main()
