#!/usr/bin/env python3
"""Hornea los datos de RD dentro del bundle que se entrega sin servidor.

Por que existe: el panel de la base de datos pide `/api/rd-db`, y en un HTML
suelto no hay a quien pedirle. Sin esto, quien abre el archivo ve un error
justo en el panel que mas informacion tiene.

Lo que escribe sale de `flujo.rd.panel.datos_panel`, LA MISMA funcion que sirve
el hub. No hay una segunda version: si hubiera dos, la allowlist de privacidad
existiria dos veces y un campo de contacto agregado manana entraria por la copia
que nadie recuerda.

Uso:
    py tools/gen_rd_standalone.py
    py tools/gen_rd_standalone.py --salida web/src/data/rdDbEmbebida.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "web" / "src" / "data" / "rdDbEmbebida.json"

# Campos que NUNCA deben viajar en un archivo que se entrega. La allowlist real
# esta en flujo.rd.panel; esto es una segunda red, porque este archivo sale del
# repo y llega a manos de terceros.
PROHIBIDOS = ("instagram", "contacto", "contactos", "telefono", "email",
              "mail", "rut", "direccion")


def revisar(datos: dict) -> list[str]:
    """Devuelve los campos prohibidos que aparecieron. Vacio = limpio."""
    encontrados = []

    def mirar(nodo, ruta=""):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                if k.lower() in PROHIBIDOS and v not in ("", [], {}, None):
                    encontrados.append(f"{ruta}.{k}")
                mirar(v, f"{ruta}.{k}")
        elif isinstance(nodo, list):
            for i, v in enumerate(nodo):
                mirar(v, f"{ruta}[{i}]")

    mirar(datos)
    return encontrados


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", type=Path, default=SALIDA)
    args = ap.parse_args()

    sys.path.insert(0, str(RAIZ / "src"))
    from flujo.rd.panel import datos_panel

    datos = datos_panel(RAIZ)
    datos["horneado"] = True          # el panel lo usa para decir de donde salio

    # Los logos tambien viajan. El panel los pedia a /api/rd-db/logo y en el
    # archivo suelto eso da 404: el recuadro quedaba roto justo en las
    # productoras que SI tienen logo, que es al reves de lo que se quiere
    # mostrar. Solo los vectoriales, que son livianos y escalan.
    from flujo.rd.panel import _candidatos_logo

    dir_logos = RAIZ / "knowledge" / "logos"
    horneados = 0
    for prod in datos["productoras"]:
        if not prod.get("logo", {}).get("archivo"):
            continue
        for cand in _candidatos_logo(dir_logos, prod["slug"], ""):
            if cand.is_file() and cand.suffix.lower() == ".svg":
                svg = cand.read_text(encoding="utf-8", errors="replace")
                # Lo mismo que se hace con un simbolo del plano: nada de script
                # ni manejadores en un archivo que se entrega.
                svg = re.sub(r"<script[\s\S]*?</script\s*>", "", svg, flags=re.I)
                svg = re.sub(r"\son[a-z]+\s*=\s*(\"[\s\S]*?\"|'[\s\S]*?')", "", svg, flags=re.I)
                prod["logo_svg"] = svg.strip()
                horneados += 1
                break

    fugas = revisar(datos)
    if fugas:
        print("ABORTADO: datos que no pueden salir del repo:", ", ".join(fugas[:6]),
              file=sys.stderr)
        return 1

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    kb = args.salida.stat().st_size / 1024
    try:
        display_path = args.salida.relative_to(RAIZ)
    except ValueError:
        display_path = args.salida
    print(f"{display_path}: "
          f"{len(datos['productoras'])} productoras, {len(datos['venues'])} venues, "
          f"{horneados} logos ({kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
