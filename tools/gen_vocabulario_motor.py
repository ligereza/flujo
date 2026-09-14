#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exporta el vocabulario del motor semantico como DATOS, para el navegador.

    py tools/gen_vocabulario_motor.py [--salida docs/cultura/lib/vocabulario.json]

Por que existe: el mismo spec tiene que poder compilarse en dos lados -- en la
caja (Python, dentro de codex) y en el navegador (la galeria de un ensayo, sin
Python y sin PC, que es el norte del repo). Portar 22 figuras y 12 gestos a
mano seria DOS fuentes de verdad divergiendo, que es el defecto que ya costo
caro en este repo (los ids del micelio y los del campo se formaban en dos
lugares: 1004 piezas, 0 posiciones).

Asi que la geometria no se porta: se EXPORTA. Las funciones de figura reciben
un dict de roles de color y devuelven el fragmento SVG; llamandolas con
`@@principal@@` en vez de un hex se obtiene el fragmento con marcadores, y el
compilador del navegador solo sustituye. La fuente sigue siendo
`cultura/mak_codex/motor_semantico/vocabulario.py`.

`tests/test_vocabulario_motor_json.py` exige que el JSON en disco coincida con
el vocabulario vivo: si alguien agrega una figura y no reexporta, CI lo dice.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "cultura" / "lib" / "vocabulario.json"

sys.path.insert(0, str(RAIZ / "cultura" / "mak_codex"))

from motor_semantico import compilador, vocabulario  # noqa: E402

# Los roles de color, con marcador en vez de hex. El compilador del navegador
# reemplaza cada marcador por el color del tono elegido.
ROLES_COLOR = ("fondo", "principal", "acento", "apoyo", "tinta")
MARCADORES = {rol: "@@%s@@" % rol for rol in ROLES_COLOR}


def construir() -> dict:
    figuras = {}
    for nombre, (fn, desc) in sorted(vocabulario.FIGURAS.items()):
        figuras[nombre] = {"fragmento": fn(dict(MARCADORES)), "que_dice": desc}
    gestos = {n: {"css": plantilla, "que_dice": desc}
              for n, (plantilla, desc) in sorted(vocabulario.GESTOS.items())}
    return {
        "_leeme": (
            "GENERADO por tools/gen_vocabulario_motor.py desde "
            "cultura/mak_codex/motor_semantico/vocabulario.py. No se edita a "
            "mano: se reexporta. Los colores viajan como @@rol@@ y los sustituye "
            "el compilador del navegador."),
        "invariantes": {
            "zona_min": compilador.ZONA_MIN,
            "zona_max": compilador.ZONA_MAX,
            "contraste_min": compilador.CONTRASTE_MIN,
            "ancho_char": compilador.ANCHO_CHAR,
            "vista": "0 0 120 120",
        },
        "roles_color": list(ROLES_COLOR),
        "figuras": figuras,
        "gestos": gestos,
        "tonos": {n: dict(p) for n, p in sorted(vocabulario.TONOS.items())},
        "composiciones": {n: {rol: list(v) for rol, v in sorted(ranuras.items())}
                          for n, ranuras in sorted(vocabulario.COMPOSICIONES.items())},
        "roles": list(vocabulario.ROLES),
        "ritmos": dict(sorted(compilador.RITMOS.items())),
        "atenuados": ["fondo_amplio", "cielo"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", type=Path, default=SALIDA)
    ap.add_argument("--verificar", action="store_true",
                    help="no escribe: falla si el archivo en disco quedo viejo")
    a = ap.parse_args()

    datos = construir()
    # ensure_ascii=False: los 'que_dice' son texto que lee un humano en la
    # galeria («recursion, trance, vortice») y conservan sus tildes.
    texto = json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n"

    if a.verificar:
        if not a.salida.is_file():
            print("falta %s: corre el generador" % a.salida, file=sys.stderr)
            return 1
        if a.salida.read_text(encoding="utf-8") != texto:
            print("%s quedo viejo respecto de vocabulario.py: reexporta"
                  % a.salida, file=sys.stderr)
            return 1
        print("al dia: %s" % a.salida)
        return 0

    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(texto, encoding="utf-8")
    print("OK %s (%d figuras, %d gestos, %d tonos, %d composiciones, %.1f KB)"
          % (a.salida, len(datos["figuras"]), len(datos["gestos"]),
             len(datos["tonos"]), len(datos["composiciones"]),
             len(texto.encode("utf-8")) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
