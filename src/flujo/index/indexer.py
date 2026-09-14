#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flujo.index.indexer  -  Indexador REAL del arbol de material para agentes/IA

La raiz del material NO esta cableada: sale de la variable de entorno
FLUJO_RD_ROOT. Si no esta definida cae a C:\\rd, que es donde vivia
historicamente en la maquina de trabajo original. Documentado en MAPA.md.

NO mueve, NO borra, NO renombra. Solo LEE el disco y produce un indice JSON
que cualquier agente puede consultar antes de actuar, para saber:
  - que archivos hay, donde, cuanto pesan, cuando se modificaron
  - a que AREA (eventos/suplementos) y PIEZA pertenece cada uno
  - que versiones existen de una misma pieza (v01, v02, copia, final...)
  - duplicados exactos (mismo hash) y "casi-duplicados" (mismo nombre base)
  - que es candidato a limpieza (autosaves, frames, builds, backups)
  - estadisticas por area/pieza/extension

Comandos:
  py -m flujo index build            # escanea $FLUJO_RD_ROOT -> index_rd.json (+ hash opcional)
  py -m flujo index build --from-inventory inv.txt   # construye desde un inventario .txt
  py -m flujo index stats            # resumen del indice
  py -m flujo index find "creatina etiqueta"         # buscar (orden por relevancia+fecha)
  py -m flujo index versions "post fiesta"           # ver versiones de una pieza
  py -m flujo index dupes            # duplicados exactos / casi-duplicados
  py -m flujo index cleanup          # candidatos a liberar espacio (no borra)
  py -m flujo index agent-brief "necesito la etiqueta final de creatina"

Diseno: el JSON es la "fuente de verdad" para agentes. Reconstruir es barato.
"""

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(AQUI, "index_rd.json")

# --- clasificacion por contenido (eventos/suplementos) y pieza ---
AREA_HINT = {
    "eventos": ["febrero", "creamfields", "flyer", "flyernuevo", "historias",
                "sundeck", "piknic", "klang", "creamfield"],
    "suplementos": ["suplemento", "etiqueta", "gotario", "prep", "pendon",
                    "creatina", "magnesio", "hongos", "impulso", "post fiesta",
                    "prefiesta", "pre fiesta", "reactivo", "marquis", "mecke"],
}
PIEZA_HINT = {
    "etiqueta": ["etiqueta", "magnesio", "creatina", "hongos", "impulso",
                 "post fiesta", "prefiesta", "pre fiesta"],
    "gotario": ["gotario", "gota3d", "marquis", "mecke", "ehrlich", "froehde"],
    "pendon": ["pendon", "banner", "stand-banner", "stand"],
    "tabla": ["tabla_rd", "tabla"],
    "bandera": ["bandera"],
    "flyer": ["flyer", "cartelera"],
    "historia": ["historia", "his."],
    "post": ["post", "carrusel"],
    "render": ["render", "preview", "comp ", "frame"],
    "comercial": ["comercial", "fincomercial"],
    "logo": ["logo", "sello"],
    "paleta": ["paleta"],
    "render3d": [".blend", ".obj"],
}
LIMPIEZA = {
    "autosave_blender": lambda p: p.lower().endswith(".blend1"),
    "autosave_ae": lambda p: "almacenamiento autom" in p.lower(),
    "backup_temporal": lambda p: p.rstrip().endswith("~") or "[recuperado]" in p.lower(),
    "frames_video": lambda p: any(s in p.lower() for s in ("\\flyervideo\\", "/flyervideo/",
                                  "\\out\\motion\\", "/out/motion/", "\\out\\pasti\\", "/out/pasti/")),
    "build_cache": lambda p: any(s in p.lower() for s in ("__pycache__", "\\build\\automatizadorflyers",
                                  "/build/automatizadorflyers")) or os.path.splitext(p)[1].lower() in (".pyc", ".toc", ".pyz", ".pkg"),
}


def _classify(path):
    p = path.lower().replace("\\", "/")
    area = None
    # Prioridad fuerte por carpeta raiz real (gana sobre keywords sueltas)
    if "/suplementos/" in p or "/gotario/" in p or "/prep/" in p:
        area = "suplementos"
    elif any(("/" + k + "/") in p for k in ("febrero", "creamfields", "flyer",
              "flyernuevo", "historias")):
        area = "eventos"
    if area is None:
        for a, kws in AREA_HINT.items():
            if any(k in p for k in kws):
                area = a
                break
    pieza = None
    for pz, kws in PIEZA_HINT.items():
        if any(k.replace("\\", "/") in p for k in kws):
            pieza = pz
            break
    limpieza = None
    for tag, fn in LIMPIEZA.items():
        if fn(path):  # LIMPIEZA usa path original (tolera \\ y /)
            limpieza = tag
            break
    return area, pieza, limpieza


def _basekey(name):
    """Nombre base sin version/sufijos, para agrupar 'versiones' de una pieza.
    creatina_v03.ai, creatina copia.ai, creatina final.ai -> 'creatina'."""
    n = name.lower()
    n = os.path.splitext(n)[0]
    # Normalize separators before token removal.  With the old order,
    # ``creatina_final.svg`` kept ``final`` because ``_`` is a word character
    # and therefore prevented the token-boundary match.  That made exact
    # duplicate/version grouping depend on whether the filename used a space
    # or an underscore.
    n = re.sub(r"[-_]+", " ", n)
    n = re.sub(r"\b(v\d{1,3}|copia|copy|final|wip|rev|nuevo|ok|def|"
               r"\d{1,2}|recuperado|ultima|ultimo|\[recuperado\])\b", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n or name.lower()


# ---------------- construccion del indice ----------------

def build_from_walk(base, do_hash=False):
    items = []
    for root, _dirs, files in os.walk(base):
        for fn in files:
            full = os.path.join(root, fn)
            try:
                st = os.stat(full)
            except OSError:
                continue
            items.append(_make_item(full, st.st_size, st.st_mtime, do_hash))
    return items


def _basename_any(full):
    """basename robusto a separadores Windows (\\) y Unix (/)."""
    return re.split(r"[\\/]", full)[-1]


def _make_item(full, size, mtime, do_hash):
    area, pieza, limpieza = _classify(full)
    name = _basename_any(full)
    item = {
        "path": full,
        "name": name,
        "ext": os.path.splitext(name)[1].lower(),
        "size": int(size),
        "mtime": _dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M") if mtime else None,
        "area": area,
        "pieza": pieza,
        "basekey": _basekey(name),
        "limpieza": limpieza,
    }
    if do_hash:
        item["md5"] = _md5(full)
    return item


def _md5(full):
    try:
        h = hashlib.md5()
        with open(full, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


_INV_RE = re.compile(r"^\s+([\d\.,]+\s*[KMGB]+B?|[\d\.,]+\s*B)\s+"
                     r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+(.+)$")


def _bytes_from_human(s):
    s = s.strip().replace(".", "").replace(",", ".")
    m = re.match(r"([\d\.]+)\s*([KMG]?B)", s)
    if not m:
        return 0
    v = float(m.group(1))
    return int(v * {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[m.group(2)])


def build_from_inventory(inv_path):
    """Construye el indice desde un inventario .txt (el que ya generamos).
    Util cuando no se corre sobre el disco real (no calcula hash)."""
    items = []
    started = False
    for line in open(inv_path, encoding="utf-8", errors="replace").read().splitlines():
        if "LISTADO COMPLETO DE ARCHIVOS" in line:
            started = True
            continue
        if not started:
            continue
        m = _INV_RE.match(line)
        if not m:
            continue
        size = _bytes_from_human(m.group(1))
        mt = m.group(2)
        full = m.group(3).strip()
        it = _make_item(full, size, None, do_hash=False)
        it["mtime"] = mt
        items.append(it)
    return items


def save_index(items, base, path=INDEX_PATH, source="walk"):
    total = sum(i["size"] for i in items)
    idx = {
        "_meta": {
            "base": base,
            "generado": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": source,
            "n_archivos": len(items),
            "peso_total_bytes": total,
            "peso_total_human": human(total),
            "para": "indice real del arbol de material para agentes/IA. No mover/borrar; solo consultar.",
        },
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=True, indent=1)
    return idx


def human(b):
    for u, d in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if b >= d:
            return "%.1f %s" % (b / d, u)
    return "%d B" % b


# ---------------- consultas (lo que usa el agente) ----------------

def load_index(path=INDEX_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find(idx, query, limit=15):
    """Busca por tokens en path/name. Ordena por (coincidencias, fecha desc)."""
    toks = [t for t in re.split(r"\s+", query.lower()) if t]
    res = []
    for it in idx["items"]:
        hay = (it["path"] + " " + (it["area"] or "") + " " + (it["pieza"] or "")).lower()
        score = sum(1 for t in toks if t in hay)
        if score:
            res.append((score, it["mtime"] or "", it))
    res.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [r[2] for r in res[:limit]]


def versions(idx, query):
    """Agrupa por basekey los archivos que matchean, para ver el historial de versiones."""
    hits = find(idx, query, limit=10**6)
    groups = {}
    for it in hits:
        groups.setdefault(it["basekey"], []).append(it)
    for k in groups:
        groups[k].sort(key=lambda x: x["mtime"] or "", reverse=True)
    return groups


def dupes(idx):
    """Duplicados exactos (md5 si existe) y casi-duplicados (mismo name+size)."""
    exact, near = {}, {}
    for it in idx["items"]:
        if it.get("md5"):
            exact.setdefault(it["md5"], []).append(it)
        near.setdefault((it["name"].lower(), it["size"]), []).append(it)
    exact = {k: v for k, v in exact.items() if len(v) > 1}
    near = {k: v for k, v in near.items() if len(v) > 1}
    return exact, near


def cleanup(idx):
    by = {}
    for it in idx["items"]:
        if it["limpieza"]:
            by.setdefault(it["limpieza"], {"n": 0, "bytes": 0, "items": []})
            by[it["limpieza"]]["n"] += 1
            by[it["limpieza"]]["bytes"] += it["size"]
            by[it["limpieza"]]["items"].append(it["path"])
    return by


def stats(idx):
    items = idx["items"]
    by_area, by_pieza, by_ext = {}, {}, {}
    for it in items:
        for d, key in ((by_area, it["area"] or "(sin area)"),
                       (by_pieza, it["pieza"] or "(sin pieza)"),
                       (by_ext, it["ext"] or "(sin)")):
            d.setdefault(key, {"n": 0, "b": 0})
            d[key]["n"] += 1
            d[key]["b"] += it["size"]
    return by_area, by_pieza, by_ext



# Raiz del material. Universal: se configura por entorno, no se cablea.
# Causa (2026-07-25): "C:\\rd" estaba escrito a mano en el codigo y en los
# textos de ayuda; cualquiera que no fuera la maquina original quedaba afuera.
# Retiro: cuando el workspace tenga un archivo de config unico y este helper
# lo lea de ahi.
RD_ROOT_ENV = "FLUJO_RD_ROOT"
RD_ROOT_FALLBACK = "C:\\rd"


def raiz_material() -> str:
    """Raiz del arbol de material real (fotos, piezas, entregas).

    Orden: $FLUJO_RD_ROOT -> C:\\rd (valor historico, se conserva para no
    romper la instalacion existente).
    """
    return os.environ.get(RD_ROOT_ENV) or RD_ROOT_FALLBACK


# ---------------- CLI ----------------

def cmd_build(args):
    if args.from_inventory:
        items = build_from_inventory(args.from_inventory)
        base = raiz_material()
        src = "inventory:" + os.path.basename(args.from_inventory)
    else:
        base = args.base or raiz_material()
        items = build_from_walk(base, do_hash=args.hash)
        src = "walk" + ("+md5" if args.hash else "")
    idx = save_index(items, base, args.out, source=src)
    print("Indice generado:", args.out)
    print("  archivos:", idx["_meta"]["n_archivos"],
          "| peso:", idx["_meta"]["peso_total_human"],
          "| source:", src)
    return 0


def cmd_stats(args):
    idx = load_index(args.out)
    print("INDICE:", idx["_meta"]["base"], "|", idx["_meta"]["n_archivos"],
          "archivos |", idx["_meta"]["peso_total_human"], "\n")
    by_area, by_pieza, by_ext = stats(idx)
    def show(title, d, top=10):
        print(title)
        for k, v in sorted(d.items(), key=lambda x: -x[1]["b"])[:top]:
            print("   %-18s %5d arch  %s" % (k, v["n"], human(v["b"])))
        print()
    show("POR AREA:", by_area)
    show("POR PIEZA:", by_pieza)
    show("POR EXTENSION:", by_ext)
    return 0


def cmd_find(args):
    idx = load_index(args.out)
    res = find(idx, args.query, args.limit)
    print("Resultados para '%s' (%d):\n" % (args.query, len(res)))
    for it in res:
        print("  %-10s %-16s [%s/%s] %s"
              % (human(it["size"]), it["mtime"], it["area"] or "-",
                 it["pieza"] or "-", it["path"]))
    if args.json:
        print("\nJSON:"); print(json.dumps(res, ensure_ascii=True, indent=1))
    return 0


def cmd_versions(args):
    idx = load_index(args.out)
    groups = versions(idx, args.query)
    if not groups:
        print("Sin coincidencias para:", args.query); return 0
    for base, lst in sorted(groups.items(), key=lambda x: -len(x[1])):
        print("PIEZA BASE: '%s'  (%d versiones)" % (base, len(lst)))
        for it in lst:
            print("   %-16s %-10s %s" % (it["mtime"], human(it["size"]), it["path"]))
        print()
    return 0


def cmd_dupes(args):
    idx = load_index(args.out)
    exact, near = dupes(idx)
    if exact:
        print("DUPLICADOS EXACTOS (md5):")
        for h, lst in exact.items():
            print("  [%dx] %s (%s c/u)" % (len(lst), lst[0]["name"], human(lst[0]["size"])))
            for it in lst:
                print("      ", it["path"])
    else:
        print("(sin hash en el indice: usa 'build --hash' para duplicados exactos)")
    print("\nCASI-DUPLICADOS (mismo nombre+peso):")
    ahorro = 0
    for (name, size), lst in sorted(near.items(), key=lambda x: -x[0][1] * (len(x[1]) - 1)):
        ahorro += size * (len(lst) - 1)
        print("  [%dx] %s (%s c/u)" % (len(lst), name, human(size)))
        for it in lst:
            print("      ", it["path"])
    print("\nAhorro potencial si dejas 1 de cada casi-duplicado:", human(ahorro))
    return 0


def cmd_cleanup(args):
    idx = load_index(args.out)
    by = cleanup(idx)
    total = 0
    print("CANDIDATOS A LIMPIEZA (no se borra nada):\n")
    for tag, d in sorted(by.items(), key=lambda x: -x[1]["bytes"]):
        total += d["bytes"]
        print("  %-18s %5d arch  %s" % (tag, d["n"], human(d["bytes"])))
    print("\nTotal recuperable estimado:", human(total))
    return 0


def cmd_agent_brief(args):
    """Resumen compacto para que un AGENTE entienda con que lidia y proponga camino."""
    idx = load_index(args.out)
    by_area, by_pieza, _ = stats(idx)
    exact, near = dupes(idx)
    clean = cleanup(idx)
    res = find(idx, args.query, 5) if args.query else []

    brief = {
        "base": idx["_meta"]["base"],
        "n_archivos": idx["_meta"]["n_archivos"],
        "peso_total": idx["_meta"]["peso_total_human"],
        "areas": {k: {"n": v["n"], "peso": human(v["b"])} for k, v in by_area.items()},
        "limpieza_recuperable": {k: {"n": v["n"], "peso": human(v["bytes"])} for k, v in clean.items()},
        "duplicados_exactos_grupos": len(exact),
        "casi_duplicados_grupos": len(near),
        "consulta": args.query,
        "mejores_coincidencias": [
            {"path": it["path"], "peso": human(it["size"]), "mtime": it["mtime"],
             "area": it["area"], "pieza": it["pieza"]} for it in res
        ],
        "recomendaciones_para_agente": [
            "No mover .blend/.psd: rompe enlaces. Trabajar in-place.",
            "AUTOMATIZACION es la cuna del pipeline (input_ig/droplet/cartelera.blend).",
            "Para liberar espacio, empezar por autosaves y frames (ver limpieza).",
            "Antes de editar un 'final', duplicar como nueva version.",
        ],
    }
    print(json.dumps(brief, ensure_ascii=True, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flujo index",
                                 description="Indexador real del arbol de material para agentes (no mueve/borra). Raiz: $FLUJO_RD_ROOT")
    ap.add_argument("--out", default=INDEX_PATH, help="ruta del index_rd.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="escanear disco o inventario -> index_rd.json")
    b.add_argument("--base", default=None,
                   help="Raiz a escanear. Default: $FLUJO_RD_ROOT (ver MAPA.md).")
    b.add_argument("--hash", action="store_true", help="calcular md5 (duplicados exactos)")
    b.add_argument("--from-inventory", default="", help="construir desde un inventario .txt")
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("stats"); s.set_defaults(func=cmd_stats)

    f = sub.add_parser("find"); f.add_argument("query")
    f.add_argument("--limit", type=int, default=15); f.add_argument("--json", action="store_true")
    f.set_defaults(func=cmd_find)

    v = sub.add_parser("versions"); v.add_argument("query"); v.set_defaults(func=cmd_versions)
    d = sub.add_parser("dupes"); d.set_defaults(func=cmd_dupes)
    c = sub.add_parser("cleanup"); c.set_defaults(func=cmd_cleanup)
    a = sub.add_parser("agent-brief"); a.add_argument("query", nargs="?", default="")
    a.set_defaults(func=cmd_agent_brief)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
