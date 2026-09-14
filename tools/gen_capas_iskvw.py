#!/usr/bin/env python3
"""Las capas del archivo de iskvw: cada una MIDE algo y lo deja en el campo.

La idea es del usuario y es la del micelio de MAK: que esto crezca en vez de
rehacerse. Sumar una capa es una entrada en `data/iskvw_capas.json` y una
funcion aca; no hay que tocar la piel, ni volver a proyectar, ni regenerar nada
mas. Una piel que no conoce una capa la ignora, y una que la conoce la usa.

Por eso las capas dan DATOS, no estetica. Que se hace con el dato lo decide
cada piel. Y por eso tampoco se inventan instrumentos: las dos que vienen usan
lo que este repo ya tiene -- `tools/tilde_meter.py` (proyecto tilde) y los SVG
que MAK vectorizo.

    py tools/gen_capas_iskvw.py
    py tools/gen_capas_iskvw.py --listar
    py tools/gen_capas_iskvw.py --solo tilde
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

CAMPO = RAIZ / "iskvw" / "datos" / "campo.json"
MANIFIESTO = RAIZ / "data" / "iskvw_capas.json"
TRAZOS = RAIZ / "iskvw" / "piel" / "trazos"


# ---------------------------------------------------------------------------
# Las capas. Una funcion por capa: recibe la pieza, devuelve el dato o None.
# Devolver None significa "esta obra no tiene este dato", y entonces el campo
# NO lo escribe: un cero fingido seria una medicion que nadie hizo.
# ---------------------------------------------------------------------------

def capa_tilde(pieza: dict, ctx: dict):
    """El residuo diacritico de lo que la percepcion escribio de la obra.

    Es la medida del proyecto tilde aplicada al archivo: cuantas marcas que
    construyen significado en espanol hay en ese texto, y cuantas por cada cien
    caracteres. Dicho de otro modo, cuanto se pierde si ese texto se degrada a
    ASCII -- que es exactamente el defecto que en este repo llego a un producto
    impreso ("reduciendo ano" por "reduciendo dano").
    """
    texto = (pieza.get("percibido") or "").strip()
    if not texto:
        return None
    marcas = ctx["tilde"].count_marks(texto)
    total = sum(marcas.values())
    return {
        "marcas": total,
        "por_cien": round(total * 100 / len(texto), 2),
        "cuales": marcas or None,
    }


def capa_trazo(pieza: dict, ctx: dict):
    """La densidad del vector: subtrazos y puntos.

    Un contorno limpio y una marana pesan distinto y hasta ahora eso no se sabia
    sin abrir el archivo. `subtrazos` cuenta los `M` de los paths; `puntos`
    cuenta las coordenadas.
    """
    corto = str(pieza.get("id") or "").split("-")[0]
    ruta = ctx["trazos"] / f"{corto}.svg"
    if not corto or not ruta.is_file() or ruta.stat().st_size == 0:
        return None
    svg = ruta.read_text(encoding="utf-8", errors="replace")
    d = " ".join(re.findall(r'\sd="([^"]*)"', svg))
    if not d:
        return None
    return {
        "subtrazos": d.count("M"),
        "puntos": len(re.findall(r"[-+]?\d*\.?\d+\s+[-+]?\d*\.?\d+", d)),
        "bytes": ruta.stat().st_size,
    }


CAPAS = {"tilde": capa_tilde, "trazo": capa_trazo}


# ---------------------------------------------------------------------------

def leer_manifiesto(ruta: Path = MANIFIESTO) -> list[dict]:
    d = json.loads(ruta.read_text(encoding="utf-8"))
    capas = d.get("capas") or []
    for i, c in enumerate(capas):
        faltan = [k for k in ("nombre", "escribe", "para") if not c.get(k)]
        if faltan:
            raise ValueError(f"{ruta.name}: capa {i} sin {', '.join(faltan)}. "
                             f"Si no se puede escribir para que sirve, no entra")
        if c["nombre"] not in CAPAS:
            raise ValueError(f"{ruta.name}: la capa '{c['nombre']}' no tiene "
                             f"funcion en {Path(__file__).name}. Declaradas: "
                             + ", ".join(sorted(CAPAS)))
    return capas


def aplicar(campo: dict, capas: list[dict], ctx: dict) -> dict:
    """Escribe el dato de cada capa activa en cada pieza. Devuelve el recuento."""
    cuenta = {}
    for c in capas:
        if not c.get("activa", True):
            continue
        fn, clave = CAPAS[c["nombre"]], c["escribe"]
        n = 0
        for p in campo["piezas"]:
            valor = fn(p, ctx)
            if valor is None:
                p.pop(clave, None)   # nada medido, nada escrito
                continue
            p[clave] = valor
            n += 1
        cuenta[c["nombre"]] = n
    return cuenta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campo", type=Path, default=CAMPO)
    ap.add_argument("--manifiesto", type=Path, default=MANIFIESTO)
    ap.add_argument("--trazos", type=Path, default=TRAZOS)
    ap.add_argument("--solo", default=None, help="una capa del manifiesto")
    ap.add_argument("--listar", action="store_true")
    args = ap.parse_args()

    try:
        capas = leer_manifiesto(args.manifiesto)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.listar:
        for c in capas:
            estado = "activa" if c.get("activa", True) else "apagada"
            print(f"  {c['nombre']:<8} {estado:<8} -> campo '{c['escribe']}'")
            print(f"           {c['para'][:96]}")
        return 0

    if args.solo:
        capas = [c for c in capas if c["nombre"] == args.solo]
        if not capas:
            print(f"error: '{args.solo}' no esta en el manifiesto", file=sys.stderr)
            return 1

    try:
        campo = json.loads(args.campo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"error: no puedo leer el campo ({e})", file=sys.stderr)
        return 1

    import tilde_meter  # noqa: E402  (instrumento real del repo)
    ctx = {"tilde": tilde_meter, "trazos": args.trazos}

    antes = args.campo.stat().st_size
    cuenta = aplicar(campo, capas, ctx)
    campo.setdefault("meta", {})["capas"] = cuenta
    args.campo.write_text(json.dumps(campo, ensure_ascii=False), encoding="utf-8")
    despues = args.campo.stat().st_size

    total = len(campo["piezas"])
    for nombre, n in cuenta.items():
        print(f"  {nombre:<8} {n}/{total} obras medidas")
    print(f"{args.campo.name}: {antes / 1024:.0f} KB -> {despues / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
