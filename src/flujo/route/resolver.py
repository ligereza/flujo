#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flujo.route.resolver  -  Router de rutas de RD (NO mueve nada)

Problema que resuelve:
  El repo flujo recibe pedidos (EVENTOS / SUPLEMENTOS) pero no sabe DONDE en
  el arbol de material ($FLUJO_RD_ROOT) estan los archivos ni donde dejar lo
  nuevo. Mover romperia proyectos
  de Blender/Photoshop (enlaces). Asi que este router solo RESUELVE rutas
  leyendo un indice (rutas_rd.json) sobre la estructura REAL existente.

Uso como herramienta del repo:
    py -m flujo hub route where --area eventos --pieza flyer
    py -m flujo hub route where --area suplementos --pieza etiqueta --que entregar
    py -m flujo hub route where --pieza logo            # transversal, sin area
    py -m flujo hub route cuna                           # muestra el pipeline AUTOMATIZACION
    py -m flujo hub route doctor                         # verifica que las rutas existan

Tambien corre suelto:
    py resolver.py where --area eventos --pieza flyer

En Linux, `FLUJO_RD_ROOT` o `--base-dir` adapta la raiz historica `C:\\rd`
al arbol local sin modificar el indice ni mover archivos.

Reglas (del repo): Windows + py, ASCII-only, no mueve archivos, no borra.
"""

import argparse
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
INDICE = os.path.join(AQUI, "rutas_rd.json")


def cargar_indice(path=INDICE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _match_pieza(piezas_dict, pieza):
    """Busca la clave de pieza por substring (flyer en 'flyer fiesta')."""
    p = (pieza or "").lower()
    for clave in piezas_dict:
        if clave in p:
            return clave
    return None


def _adapt_path(path, base_dir, source_base=None):
    """Translate the historical Windows root without touching the index."""
    if not path or not base_dir or not source_base:
        return path
    raw = str(path)
    prefix = str(source_base).replace("/", "\\").rstrip("\\")
    candidate = raw.replace("/", "\\")
    if candidate.lower() == prefix.lower():
        suffix = ""
    elif candidate.lower().startswith(prefix.lower() + "\\"):
        suffix = candidate[len(prefix) + 1:]
    else:
        return path
    return os.path.join(str(base_dir), *suffix.split("\\")) if suffix else str(base_dir)


def _adapt_result(result, base_dir, source_base):
    """Return a copy with configured local paths; the JSON index stays intact."""
    if not base_dir or "error" in result:
        return result
    adapted = dict(result)
    for key in ("buscar_en",):
        adapted[key] = [_adapt_path(p, base_dir, source_base)
                        for p in result.get(key, [])]
    for key in ("trabajar_en", "entregar_en", "cuna"):
        if result.get(key):
            adapted[key] = _adapt_path(result[key], base_dir, source_base)
    return adapted


def resolver_ruta(idx, area=None, pieza=None, que="trabajar", base_dir=None):
    """
    Devuelve dict con la resolucion. NO toca el disco.
    que: 'buscar' | 'trabajar' | 'entregar'
    """
    # 1) transversal (logo/paleta/textura/propuesta) - no necesita area
    for tkey, tv in idx["transversales"].items():
        if _match_pieza({k: 1 for k in tv["piezas"]}, pieza):
            return _adapt_result({
                "ambito": "transversal",
                "grupo": tkey,
                "buscar_en": tv.get("buscar_en", []),
                "trabajar_en": tv.get("trabajar_en"),
                "entregar_en": tv.get("trabajar_en"),
                "nota": "Pieza transversal (sirve a EVENTOS y SUPLEMENTOS).",
            }, base_dir, idx.get("_meta", {}).get("base"))

    # 2) area de negocio
    if not area:
        return {"error": "Falta --area (EVENTOS o SUPLEMENTOS). "
                         "Un flyer/pendon es de una u otra segun su CONTENIDO."}
    a = area.upper()
    if a not in idx["areas"]:
        return {"error": "Area invalida: %s. Usa EVENTOS o SUPLEMENTOS." % area}

    piezas = idx["areas"][a]["piezas"]
    clave = _match_pieza(piezas, pieza)
    if not clave:
        return {"error": "Pieza '%s' no reconocida en %s. Validas: %s"
                         % (pieza, a, ", ".join(sorted(piezas.keys())))}

    info = piezas[clave]
    return _adapt_result({
        "ambito": "area",
        "area": a,
        "pieza": clave,
        "buscar_en": info.get("buscar_en", []),
        "trabajar_en": info.get("trabajar_en"),
        "entregar_en": info.get("entregar_en"),
        "cuna": idx["cuna"]["ruta"],
    }, base_dir, idx.get("_meta", {}).get("base"))


# ----------------------- CLI -----------------------

def _print_resol(r, que):
    if "error" in r:
        print("ERROR:", r["error"])
        return 1
    print("Ambito        :", r["ambito"])
    if r["ambito"] == "area":
        print("Area          :", r["area"], "| pieza:", r["pieza"])
        print("Cuna (origen) :", r["cuna"])
    else:
        print("Grupo         :", r["grupo"], "-", r.get("nota", ""))
    print("Buscar en     :")
    for b in r.get("buscar_en", []):
        print("   -", b)
    print("Trabajar en   :", r.get("trabajar_en"))
    print("Entregar en   :", r.get("entregar_en"))
    # destacado segun lo pedido
    destino = {"buscar": None, "trabajar": r.get("trabajar_en"),
               "entregar": r.get("entregar_en")}.get(que)
    if que == "buscar":
        print("\n>>> RUTAS DONDE BUSCAR (ver lista arriba)")
    else:
        print("\n>>> RUTA (%s): %s" % (que.upper(), destino))
    return 0


def cmd_where(args):
    idx = cargar_indice(args.indice)
    base_dir = args.base_dir or os.environ.get("FLUJO_RD_ROOT")
    r = resolver_ruta(idx, area=args.area, pieza=args.pieza, que=args.que,
                      base_dir=base_dir)
    rc = _print_resol(r, args.que)
    if args.json:
        print("\nJSON:")
        print(json.dumps(r, ensure_ascii=True, indent=2))
    return rc


def cmd_cuna(args):
    idx = cargar_indice(args.indice)
    c = idx["cuna"]
    print("CUNA DEL REPO:", c["carpeta"], "->", c["ruta"])
    print(c["descripcion"], "\n")
    print("Pipeline (rutas que el repo ya usa):")
    for k, v in c["archivos_pipeline"].items():
        print("  %-18s %s" % (k, v))
    return 0


def cmd_doctor(args):
    """Verifica si las rutas del indice existen en disco (solo lectura)."""
    idx = cargar_indice(args.indice)
    base = args.base_dir or os.environ.get("FLUJO_RD_ROOT") or idx["_meta"]["base"]
    source_base = idx["_meta"].get("base")
    rutas = set()
    rutas.add(_adapt_path(idx["cuna"]["ruta"], args.base_dir or os.environ.get("FLUJO_RD_ROOT"), source_base))
    for v in idx["cuna"]["archivos_pipeline"].values():
        rutas.add(_adapt_path(v, args.base_dir or os.environ.get("FLUJO_RD_ROOT"), source_base))
    for area in idx["areas"].values():
        for info in area["piezas"].values():
            rutas.update(_adapt_path(p, args.base_dir or os.environ.get("FLUJO_RD_ROOT"), source_base)
                         for p in info.get("buscar_en", []))
            for k in ("trabajar_en", "entregar_en"):
                if info.get(k):
                    rutas.add(_adapt_path(info[k], args.base_dir or os.environ.get("FLUJO_RD_ROOT"), source_base))
    for tv in idx["transversales"].values():
        rutas.update(_adapt_path(p, args.base_dir or os.environ.get("FLUJO_RD_ROOT"), source_base)
                     for p in tv.get("buscar_en", []))
        if tv.get("trabajar_en"):
            rutas.add(_adapt_path(tv["trabajar_en"], args.base_dir or os.environ.get("FLUJO_RD_ROOT"), source_base))

    print("DOCTOR - verificando", len(rutas), "rutas bajo", base)
    print("(solo lectura, no se toca nada)\n")
    faltan = 0
    for ruta in sorted(rutas):
        existe = os.path.exists(ruta)
        if not existe:
            faltan += 1
        print(("  OK   " if existe else "  FALTA") + "  " + ruta)
    print("\nResumen: %d rutas, %d faltan." % (len(rutas), faltan))
    if faltan:
        print("Las que 'FALTAN' pueden ser archivos del pipeline aun no generados")
        print("(input_ig.jpg, preview_cartelera.png) o carpetas con otro nombre.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flujo route",
                                 description="Router de rutas de RD (no mueve archivos)")
    ap.add_argument("--indice", default=INDICE, help="ruta a rutas_rd.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("where", help="resolver donde esta / donde va una pieza")
    w.add_argument("--area", default="", help="EVENTOS o SUPLEMENTOS")
    w.add_argument("--pieza", default="", help="flyer/pendon/etiqueta/logo/post/render...")
    w.add_argument("--que", choices=["buscar", "trabajar", "entregar"],
                   default="trabajar", help="que ruta quieres")
    w.add_argument("--json", action="store_true", help="imprimir tambien el JSON")
    w.add_argument("--base-dir", default="", help="raiz local que reemplaza la raiz historica (o FLUJO_RD_ROOT)")
    w.set_defaults(func=cmd_where)

    c = sub.add_parser("cuna", help="mostrar AUTOMATIZACION (cuna) y su pipeline")
    c.set_defaults(func=cmd_cuna)

    d = sub.add_parser("doctor", help="verificar que las rutas existan (solo lectura)")
    d.add_argument("--base-dir", default="", help="raiz local que reemplaza la raiz historica (o FLUJO_RD_ROOT)")
    d.set_defaults(func=cmd_doctor)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
