#!/usr/bin/env python3
"""Analiza flyer: colores dominantes + OCR opcional
Uso:
  py scripts/flyer_analyze.py                 # último proyecto
  py scripts/flyer_analyze.py projects/flyer_eventos/2026-06-16_ig_XXXX
  py scripts/flyer_analyze.py --all
"""
import sys
# Evitar shadow del paquete flujo
try:
    from pathlib import Path
    _script_dir = Path(__file__).resolve().parent
    sys.path = [p for p in sys.path if Path(p).resolve() != _script_dir]
except Exception:
    pass

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Analizar flyer – colores + OCR")
    ap.add_argument("project", nargs="?", help="ruta al proyecto flyer")
    ap.add_argument("--all", action="store_true", help="analizar todos los proyectos")
    args = ap.parse_args(argv)

    try:
        from flujo.analyze.run import analyze_project, find_latest_flyer
        from flujo.paths import flyer_base
    except ImportError as e:
        print(f"ERROR: instala con py -m pip install -e . ({e})", file=sys.stderr)
        return 1

    targets = []
    if args.all:
        base = flyer_base()
        targets = sorted([p for p in base.glob("*") if (p / "manifest.json").exists()]) if base.exists() else []
    elif args.project:
        targets = [Path(args.project)]
    else:
        latest = find_latest_flyer()
        if not latest:
            print("No se encontró ningún proyecto flyer")
            return 1
        targets = [latest]

    ok = 0
    for proj in targets:
        print(f"→ {proj.name}")
        res = analyze_project(proj)
        if res.get("status") == "ok":
            colors = [c["hex"] for c in res.get("palette", {}).get("colors", [])]
            print(f"  colores: {' '.join(colors)}")
            if res.get("ocr", {}).get("available"):
                print(f"  OCR: {res['ocr'].get('chars',0)} chars")
            else:
                print("  OCR: no disponible (instala pytesseract para activar)")
            ok += 1
        else:
            print(f"  FAIL: {res.get('error', res)}")
    print(f"\nAnalizados OK: {ok}/{len(targets)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
