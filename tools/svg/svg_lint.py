#!/usr/bin/env python3
"""Valida un SVG contra las reglas RD antes de entregar (atrapa el problema temprano).

Uso: py tools/svg/svg_lint.py <archivo.svg>... [--flyer|--brief]
Reglas: canvas, fuente Arial (no DejaVu), capas nombradas, logo vectorial (no raster),
texto editable presente. Exit != 0 si hay algun FAIL.
"""
import sys, re
from pathlib import Path

def lint(path, kind):
    s = Path(path).read_text(encoding="utf-8", errors="replace")
    out = []
    vb = re.search(r'viewBox="([\d.\s]+)"', s)
    w = h = "?"
    if vb:
        n = vb.group(1).split()
        if len(n) == 4:
            w, h = n[2].split(".")[0], n[3].split(".")[0]
    if kind == "flyer" and (w, h) != ("2000", "2800"):
        out.append(("WARN", f"canvas {w}x{h} (flyer esperado 2000x2800)"))
    if "DejaVu" in s:
        out.append(("FAIL", "fuente DejaVu (Illustrator no la tiene) -> usa Arial/Helvetica"))
    if "<text" in s and "Arial" not in s and "Helvetica" not in s:
        out.append(("WARN", "no se ve Arial/Helvetica en font-family"))
    ids = re.findall(r'<g id="([^"]+)"', s)
    if not ids:
        out.append(("WARN", "sin <g id> (capas sin nombre) -> nombra las capas"))
    gen = [i for i in ids if re.match(r'(Layer|Group|Capa)[_ ]?\d', i, re.I)]
    if gen:
        out.append(("WARN", f"capas con nombre generico: {gen[:3]}"))
    if "data:image/png;base64" in s or re.search(r'<image[^>]+base64', s):
        out.append(("WARN", "logo/imagen raster embebida (se rompe al zoom) -> usa vector inline"))
    if "<text" not in s:
        out.append(("WARN", "sin <text> (todo vectorizado?) -> no editable como texto"))
    return out

def main():
    kind = "flyer" if "--flyer" in sys.argv else "brief" if "--brief" in sys.argv else "flyer"
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not files:
        print("uso: py tools/svg/svg_lint.py <archivo.svg>... [--flyer|--brief]"); return
    fails = 0
    for f in files:
        iss = lint(f, kind)
        print(f"\n== {f} ==")
        if not iss:
            print("  PASS")
        for lvl, msg in iss:
            print(f"  [{lvl}] {msg}")
            if lvl == "FAIL":
                fails += 1
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
