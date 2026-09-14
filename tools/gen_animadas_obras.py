#!/usr/bin/env python3
"""Cada obra curada del artista genera su pieza animada por el motor semantico.

El ensayo rave fue la DEMO del mecanismo (spec cerrada -> compilar -> svg
animado); el sistema existe para las obras reales: la carpeta de material que
el artista mando a curar y que MAK percibio. Este generador lee el campo
medido (`iskvw/datos/campo.json`, ya bajo el filtro que el usuario configuro)
y deriva para cada obra UNA spec del vocabulario cerrado del motor:

- semantica donde lo percibido alcanza: los COLORES medidos eligen el tono
  (naranja -> atardecer, azul -> blueprint...), la TILDE late, lo reactivo
  tiembla, y una figura o un tono nombrados por el estilo/percibido de la
  obra se usan tal cual;
- sembrada por el id donde no: mismo id -> misma spec -> misma pieza,
  sin reloj y sin random (la tesis del timecode como semilla).

    py tools/gen_animadas_obras.py            # escribe svg + manifiesto

Salidas:
    iskvw/piel/animadas/<obra_id>.svg
    iskvw/datos/animadas.json   (manifiesto que lee contrato_archivo)

La pieza entra al archivo como `pieza_grafica` vinculada a su obra via
`contrato_archivo.desde_animadas()`, y la piel la presenta al quedarse
quieto (mismo mecanismo que los iconos de ensayo).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "cultura" / "mak_codex"))
from motor_semantico.compilador import (  # noqa: E402
    COMPOSICIONES, FIGURAS, GESTOS, RITMOS, TONOS, compilar, validar_spec,
)

CAMPO = RAIZ / "iskvw" / "datos" / "campo.json"
SALIDA_SVG = RAIZ / "iskvw" / "piel" / "animadas"
MANIFIESTO = RAIZ / "iskvw" / "datos" / "animadas.json"

GESTOS_VIVOS = sorted(g for g in GESTOS if g != "quieto")

# Color MEDIDO por la percepcion -> tono del motor. Mapeo declarado, no
# adivinado: cada entrada es discutible a la vista y por eso vive aca arriba.
TONO_POR_COLOR = {
    "naranja": "atardecer",
    "rojo": "atardecer",
    "amarillo": "acido",
    "verde": "campo",
    "azul": "blueprint",
    "celeste": "blueprint",
    "morado": "subterraneo",
    "violeta": "subterraneo",
    "rosa": "vitral",
    "rosado": "vitral",
    "negro": "subterraneo",
    "gris": "concreto",
    "blanco": "papel",
    "cafe": "documento",
    "marron": "documento",
}

# Palabra percibida -> gesto, SOLO donde el mapeo significa algo: la tilde
# late (la senal del proyecto tilde), lo psicodelico deriva, lo reactivo
# tiembla. Orden = prioridad semantica. Lo demas cae a la semilla.
GESTO_POR_PALABRA = {
    "tilde": "latir",
    "psicodelia": "derivar",
    "psicodelico": "derivar",
    "psicodelica": "derivar",
    "surrealismo": "derivar",
    "reactiva": "temblar",
    "reactivo": "temblar",
    "glitch": "temblar",
    "proyeccion": "emanar",
    "projection": "emanar",
    "geometrico": "girar",
    "geometrica": "girar",
}


def _ascii(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def _semilla(obra_id: str) -> "list[int]":
    return list(hashlib.sha256(obra_id.encode("utf-8")).digest())


def _palabras(obra: dict) -> "list[str]":
    crudo = " ".join([
        obra.get("tipo") or "", obra.get("estilo") or "",
        obra.get("percibido") or "",
    ])
    limpio = "".join(c if c.isalnum() else " " for c in crudo)
    return [_ascii(p) for p in limpio.split() if len(p) > 2]


def derivar_spec(obra: dict) -> dict:
    """Una spec valida del vocabulario cerrado, derivada de lo percibido.

    Prioridad: la tilde medida > palabra semantica declarada > coincidencia
    literal (figura/tono que el percibido nombra) > color medido (tono) >
    semilla del id. Nunca reloj, nunca random.
    """
    s = _semilla(obra.get("id") or "obra")
    palabras = _palabras(obra)
    presentes = set(palabras)

    # gesto: la tilde medida manda; despues la palabra; despues la semilla
    marcas = (obra.get("tilde") or {}).get("marcas") or 0
    if marcas > 0:
        gesto = "latir"
    else:
        gesto = next((g for p, g in GESTO_POR_PALABRA.items()
                      if p in presentes), None) \
            or GESTOS_VIVOS[s[3] % len(GESTOS_VIVOS)]

    # tono: nombrado > color medido > semilla
    tonos_dichos = [p for p in palabras if p in TONOS]
    tono = tonos_dichos[0] if tonos_dichos else None
    if not tono:
        for color in obra.get("colores") or []:
            tono = TONO_POR_COLOR.get(_ascii(color))
            if tono:
                break
    if not tono:
        tono = sorted(TONOS)[s[1] % len(TONOS)]

    figs = sorted(FIGURAS)
    figuras_dichas = [p for p in palabras if p in FIGURAS]
    fig_prota = figuras_dichas[0] if figuras_dichas else figs[s[2] % len(figs)]

    comps = sorted(COMPOSICIONES)
    comp = comps[s[0] % len(comps)]
    ranuras = sorted(COMPOSICIONES[comp])
    ritmos = sorted(RITMOS)

    capas = [{
        "rol": "protagonista",
        "figura": fig_prota,
        "gesto": gesto,
        "ritmo": ritmos[s[4] % len(ritmos)],
    }]
    otros = [r for r in ranuras if r != "protagonista"]
    if otros:
        capas.append({
            "rol": otros[s[5] % len(otros)],
            "figura": figs[s[6] % len(figs)],
            "gesto": "quieto",
        })
    return {"composicion": comp, "tono": tono, "capas": capas}


def generar() -> "list[dict]":
    campo = json.loads(CAMPO.read_text(encoding="utf-8"))
    obras = campo.get("piezas") or []
    SALIDA_SVG.mkdir(parents=True, exist_ok=True)
    filas = []
    for obra in obras:
        oid = obra.get("id")
        if not oid:
            continue
        spec = derivar_spec(obra)
        fallos = validar_spec(spec)
        if fallos:
            raise SystemExit(f"spec invalida para '{oid}': {fallos}")
        svg, _avisos = compilar(spec, slug=oid)
        destino = SALIDA_SVG / f"{oid}.svg"
        destino.write_text(svg, encoding="utf-8", newline="\n")
        filas.append({
            "obra_id": oid,
            # titulo = id: el percibido es texto de maquina y no titula
            # (regla de la VOZ); el artista no titulo estas piezas.
            "titulo": oid,
            "src": destino.relative_to(RAIZ).as_posix(),
            "spec": spec,
            "declara_animacion": any(
                (c.get("gesto") or "quieto") != "quieto" for c in spec["capas"]),
        })
    return filas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args()
    filas = generar()
    MANIFIESTO.write_text(
        json.dumps({"version": 1, "piezas": filas}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    animadas = sum(1 for f in filas if f["declara_animacion"])
    total = sum(f.stat().st_size for f in SALIDA_SVG.glob("*.svg"))
    print(f"{len(filas)} piezas ({animadas} animadas) -> "
          f"{SALIDA_SVG.relative_to(RAIZ)} ({total/1024:.0f} KB)")
    print(f"manifiesto -> {MANIFIESTO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
