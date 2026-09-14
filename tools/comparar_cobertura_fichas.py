#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Two perception passes, compared over the SAME files, per field.

Why this exists as a tool and not as a one-off: on 2026-07-31 the perception
pipeline changed engine (one local model to another) and the only
honest way to say it improved was to count what each pass actually filled. A
sentence like "now it sees better" is not measurable; "descripcion went from 0%
to 100% over the same 902 files" is.

Three rules baked in, each of them a defect this repo already paid for:

1. **The same files, or nothing.** Coverage over different sets is not a
   comparison. Only ids present in BOTH passes are counted, and the tool prints
   how many it dropped for that reason.
2. **Attribution filter.** `--motor <label>` keeps only the rows that the
   selected engine actually measured. A run with a fallback in it would
   otherwise credit one engine for what another answered.
3. **Empty is not missing.** A key present with "" is a different fact from a
   key that never arrived, and they are counted separately -- collapsing them is
   how a silent discard looks like a success.

Usage:
    py tools/comparar_cobertura_fichas.py ANTES.jsonl DESPUES.jsonl
    py tools/comparar_cobertura_fichas.py a.jsonl b.jsonl --motor ollama
    py tools/comparar_cobertura_fichas.py a.jsonl b.jsonl --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Vision keys the pipeline knows how to place. Kept as a list only to give the
# table a stable order: anything else a pass emitted is added at the end, never
# dropped in silence.
ORDEN = ["tipo_obra", "descripcion", "conceptos", "tecnica", "materiales",
         "colores", "linea_investigacion", "texto_visible", "datos_extraibles",
         "oportunidad_codigo"]


def cargar(ruta: Path) -> dict[str, dict]:
    """id -> ficha. A later row for the same id wins: a retry writes a new row
    and the retry is the outcome that counts."""
    fichas: dict[str, dict] = {}
    malas = 0
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                malas += 1
                continue
            if d.get("id"):
                fichas[d["id"]] = d
    if malas:
        print("  aviso: %d lineas ilegibles en %s" % (malas, ruta.name),
              file=sys.stderr)
    return fichas


def motor_de(ficha: dict) -> str:
    """Who answered. `sin_atribucion` is what the pipeline writes when nobody
    signed -- it is reported as itself, never folded into a default."""
    med = (ficha.get("medicion") or {}).get("vision") or {}
    return med.get("motor") or "sin_atribucion"


def lleno(valor) -> bool:
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, (list, dict, tuple)):
        return bool(valor)
    return True


def heredados_de(ficha: dict) -> dict:
    """Fields this ficha did NOT measure: it keeps them from an earlier pass.

    `tools/consolidar_fichas.py` writes them when it merges. Without reading
    them, this tool credits the row's engine with what another one answered --
    measured on 2026-08-01 over the merged archive: `oportunidad_codigo` came
    out at 100% for watsonx when the real figure is 77,9% and the other 291
    were ollama's. It is exactly the lie this file exists to prevent, walking
    in through the side door.
    """
    h = (((ficha.get("medicion") or {}).get("vision") or {}).get("heredado")
         or {})
    if isinstance(h, dict):
        return h
    # Old format: a flat list with no engine. What was inherited is known;
    # from whom is not -- and that is said, not guessed.
    return {c: "sin_atribucion" for c in h} if isinstance(h, list) else {}


def contar(fichas: dict[str, dict], ids: list[str], claves: list[str]) -> dict:
    """Per key: how many of `ids` have it filled, empty, absent or inherited.

    `heredado` is NOT `lleno`: the field has a value, but this pass did not
    produce it. Counting it as filled is how a merge quietly inflates the
    coverage of whichever engine happens to sign the row.
    """
    out = {}
    for k in claves:
        llenos = vacios = ausentes = heredados = 0
        for i in ids:
            ficha = fichas[i]
            vision = ficha.get("vision") or {}
            if ("vision." + k) in heredados_de(ficha):
                heredados += 1
            elif k not in vision:
                ausentes += 1
            elif lleno(vision[k]):
                llenos += 1
            else:
                vacios += 1
        out[k] = {"lleno": llenos, "vacio": vacios, "ausente": ausentes,
                  "heredado": heredados}
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("antes", type=Path)
    p.add_argument("despues", type=Path)
    p.add_argument("--motor", default="",
                   help="quedarse solo con las fichas que ESE motor midio en "
                        "la pasada nueva (p.ej. ollama)")
    p.add_argument("--json", action="store_true", dest="como_json")
    a = p.parse_args()

    for ruta in (a.antes, a.despues):
        if not ruta.exists():
            print("no existe: %s" % ruta, file=sys.stderr)
            return 2

    antes, despues = cargar(a.antes), cargar(a.despues)

    ids_despues = list(despues)
    motores: dict[str, int] = {}
    for i in ids_despues:
        m = motor_de(despues[i])
        motores[m] = motores.get(m, 0) + 1
    if a.motor:
        ids_despues = [i for i in ids_despues if motor_de(despues[i]) == a.motor]

    comunes = sorted(i for i in ids_despues if i in antes)
    solo_despues = len(ids_despues) - len(comunes)

    claves = list(ORDEN)
    for fuente in (antes, despues):
        for f in fuente.values():
            for k in (f.get("vision") or {}):
                if k not in claves and not k.startswith("_"):
                    claves.append(k)

    ca = contar(antes, comunes, claves)
    cd = contar(despues, comunes, claves)
    n = len(comunes)

    datos = {
        "antes": str(a.antes), "despues": str(a.despues),
        "motor_filtrado": a.motor or None,
        "motores_en_la_pasada_nueva": motores,
        "fichas_antes": len(antes), "fichas_despues": len(despues),
        "comparadas": n, "solo_en_la_nueva": solo_despues,
        "campos": {k: {"antes": ca[k], "despues": cd[k]} for k in claves},
    }
    if a.como_json:
        print(json.dumps(datos, ensure_ascii=False, indent=1))
        return 0

    print("antes:   %s (%d fichas)" % (a.antes, len(antes)))
    print("despues: %s (%d fichas)" % (a.despues, len(despues)))
    print("motores en la pasada nueva: %s" % ", ".join(
        "%s=%d" % kv for kv in sorted(motores.items())))
    if a.motor:
        print("filtrado a motor=%s" % a.motor)
    print("comparadas sobre los MISMOS archivos: %d" % n)
    if solo_despues:
        print("  (%d fichas nuevas no estaban en la pasada vieja: no se cuentan)"
              % solo_despues)
    if not n:
        print("nada en comun: no hay comparacion que hacer")
        return 1

    print()
    print("%-22s %12s %12s   %s" % ("campo", "antes", "despues", "delta"))
    for k in claves:
        pa = 100.0 * ca[k]["lleno"] / n
        pd = 100.0 * cd[k]["lleno"] / n
        marca = "" if abs(pd - pa) < 0.05 else ("  <<<" if pd > pa else "  !!!")
        # `heredado` is reported apart and NEVER added to `lleno`: the field
        # has a value, but this pass did not produce it.
        her = cd[k].get("heredado", 0)
        print("%-22s %6d %5.1f%% %6d %5.1f%%  %+6.1f%s%s"
              % (k, ca[k]["lleno"], pa, cd[k]["lleno"], pd, pd - pa, marca,
                 ("   (+%d heredados, no cuentan)" % her) if her else ""))
    print()
    print("!!! = la pasada nueva llena MENOS que la vieja")
    heredados_tot = sum(cd[k].get("heredado", 0) for k in claves)
    if heredados_tot:
        print("heredados = campos que la ficha CONSERVA de una pasada anterior. "
              "No se cuentan como llenos:")
        print("el motor que firma la fila no los midio, y acreditarselos es la "
              "mentira que este archivo evita.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
