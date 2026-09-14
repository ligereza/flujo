#!/usr/bin/env python3
"""
Borradura ASCII -- la regla que protege al sistema mutila al idioma.

Semilla: pedido real del usuario, 23-jul-2026 (puente/SEMILLAS.md). La regla
"CLAUDE.md y context/LAST_HANDOFF.md: ASCII-only" nacio como defensa
operativa contra bugs de encoding en checkouts Windows (v0.35.7-v0.35.9,
23-24 jun 2026: shas 3b5b372 "purple portal gmail windows handoff" y
ecaa238 "windows checkout issue titles"). El 23-jul-2026 se noto aplicada
fuera de su alcance original: entregables de la ONG con "disenio"/"ano" en
vez de "diseno"/"ano" (el par ano/anio -- ver abajo -- demuestra que la
borradura del diacritico a veces cambia significado, no solo forma).

Esta pieza MIDE, no opina (descriptivo; cultura/ no genera sintesis):
recorre los .md operativos del repo en su version git ACTUAL (git show
HEAD:archivo -- nunca el working tree, para que la corrida sea reproducible
contra un commit fechado) y busca palabras que son la forma-borrada de una
palabra española con diacritico. Reporta conteo por archivo, los pares
minimos REALES encontrados (palabra, archivo, sha corto), y cuantos son
pares donde AMBAS formas (con y sin marca) son palabras validas del
diccionario -- osea la borradura cambia significado -- contra cuantos son
solo perdida de acento (la forma sin marca no es una palabra independiente,
solo la version incorrecta de la palabra con marca).

Omega11 (puente/SEMILLAS.md, declarada por el director antes de producir):
"Esta pieza pierde si (a) algun conteo no es deterministico/reproducible
sobre el corpus fechado; (b) inventa ejemplos -- todo par minimo debe
existir literal en archivos del repo con su sha; (c) la pieza
escribe/altera los archivos operativos que mide (debe ser lectura pura)."

Este script NUNCA escribe en los .md que mide. Solo lee via `git show` y
escribe su propio reporte/tapiz en projects/cultura/borradura_ascii/.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Los .md operativos declarados por la regla ASCII-only (CLAUDE.md +
# context/*.md). Lista fija -- no se descubre por glob para que la corrida
# sea reproducible sobre lo que la regla realmente gobierna, no sobre
# lo que exista hoy en el directorio (context/*.html, *.json, etc. no
# son texto operativo en espanol).
# 2026-07-26: la lista se encogio de 11 a 4. Los siete que faltan no se
# perdieron -- se archivaron el mismo dia, cuando resulto que siete documentos
# operativos compitiendo entre si eran la causa de que cada agente reconstruyera
# el estado desde cero. El corpus sigue siendo lo que la regla ASCII gobierna
# HOY; que se haya encogido es, en si mismo, el dato.
ARCHIVOS_OPERATIVOS = [
    "CLAUDE.md",
    "MAPA.md",
    "context/LAST_HANDOFF.md",
    "context/README.md",
]

# Diccionario minimo embebido: palabra_con_marca -> (formas ASCII que puede
# tomar tras la borradura, cambia_significado, nota). Curado a mano, igual
# que _COSTO_POR_CHAR de tilde_residuo.py (misma logica: costo de
# significado no se computa, se nombra). "cambia_significado=True" solo
# para pares minimos donde LA FORMA SIN MARCA es, por si sola, otra palabra
# valida y distinta del espanol (no una version incorrecta de la primera).
#
# Deliberadamente EXCLUIDAS: palabras funcionales (el/el, si/si, mas/mas,
# de/de, se/se, tu/tu, mi/mi...) donde el par acentuado (el/si/mas/de/se/
# tu/mi) es un pronombre/conjuncion RARO y la forma sin marca (el/si/mas/
# de/se/tu/mi) es, en la enorme mayoria de apariciones reales, la palabra
# funcional CORRECTA (articulo/conjuncion/preposicion), no una borradura.
# Meterlas al escaner produce falsos positivos masivos (cada "de" o "el"
# del texto se marcaria como "borradura que cambia significado", lo cual
# es falso: no hay evidencia de que el autor quiso escribir "de"/"el" con
# tilde). Incluir esas palabras violaria la Omega11 (b) en espiritu: no
# fabricar hallazgos. "año/ano" es la EXCEPCION real citada por el
# director -- "ano" no es una palabra funcional de alta frecuencia, su
# aparicion en un corpus tecnico es senal fuerte de borradura de "año".
@dataclass(frozen=True)
class ParDiccionario:
    con_marca: str
    formas_ascii: Tuple[str, ...]
    cambia_significado: bool
    nota: str


DICCIONARIO: List[ParDiccionario] = [
    # -- el unico par minimo real que se escanea: la forma ascii es OTRA
    #    palabra valida y de baja frecuencia base (no funcional) --
    ParDiccionario("año", ("ano",), True, "año (year) / ano (anus)"),
    # -- solo perdida de acento: la forma ascii NO es una palabra --
    #    independiente valida, es la version incorrecta de la de la izq.
    ParDiccionario("diseño", ("diseno", "disenio"), False, "diseno/disenio no son palabras propias"),
    ParDiccionario("producción", ("produccion",), False, ""),
    ParDiccionario("información", ("informacion",), False, ""),
    ParDiccionario("configuración", ("configuracion",), False, ""),
    ParDiccionario("sesión", ("sesion",), False, ""),
    ParDiccionario("código", ("codigo",), False, ""),
    ParDiccionario("técnico", ("tecnico",), False, ""),
    ParDiccionario("técnica", ("tecnica",), False, ""),
    ParDiccionario("automático", ("automatico",), False, ""),
    ParDiccionario("día", ("dia",), False, ""),
    ParDiccionario("versión", ("version",), False, ""),
    ParDiccionario("número", ("numero",), False, ""),
    ParDiccionario("práctico", ("practico",), False, ""),
    ParDiccionario("lógica", ("logica",), False, ""),
    ParDiccionario("edición", ("edicion",), False, ""),
    ParDiccionario("autenticación", ("autenticacion",), False, ""),
    ParDiccionario("público", ("publico",), False, ""),
    ParDiccionario("útil", ("util",), False, ""),
    ParDiccionario("fácil", ("facil",), False, ""),
    ParDiccionario("rápido", ("rapido",), False, ""),
    ParDiccionario("además", ("ademas",), False, ""),
]

# indice ascii_form -> ParDiccionario, para lookup O(1) por token
_INDICE: Dict[str, ParDiccionario] = {}
for _par in DICCIONARIO:
    for _forma in _par.formas_ascii:
        _INDICE[_forma.lower()] = _par

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+")


@dataclass
class Hallazgo:
    palabra: str          # forma ascii encontrada, tal como aparece
    con_marca: str         # forma con diacritico correspondiente
    cambia_significado: bool
    nota: str
    archivo: str
    linea: int
    sha_corto: str


@dataclass
class ReporteArchivo:
    archivo: str
    total_lineas: int
    hallazgos: List[Hallazgo] = field(default_factory=list)


def _run_git(args: List[str], repo: Path) -> str:
    resultado = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} fallo (exit {resultado.returncode}): {resultado.stderr.strip()}"
        )
    return resultado.stdout


def sha_head(repo: Path) -> str:
    """sha corto de HEAD -- version exacta que se esta midiendo."""
    return _run_git(["rev-parse", "--short", "HEAD"], repo).strip()


def leer_operativo(repo: Path, ruta: str, ref: str = "HEAD") -> Optional[str]:
    """Lee `ruta` en `ref` via `git show` -- lectura pura, nunca working tree."""
    try:
        return _run_git(["show", f"{ref}:{ruta}"], repo)
    except RuntimeError:
        return None


def escanear_archivo(repo: Path, ruta: str, sha: str) -> ReporteArchivo:
    contenido = leer_operativo(repo, ruta)
    if contenido is None:
        return ReporteArchivo(archivo=ruta, total_lineas=0, hallazgos=[])

    lineas = contenido.splitlines()
    hallazgos: List[Hallazgo] = []
    for i, linea in enumerate(lineas, start=1):
        for m in _TOKEN_RE.finditer(linea):
            token = m.group(0)
            par = _INDICE.get(token.lower())
            if par is None:
                continue
            hallazgos.append(
                Hallazgo(
                    palabra=token,
                    con_marca=par.con_marca,
                    cambia_significado=par.cambia_significado,
                    nota=par.nota,
                    archivo=ruta,
                    linea=i,
                    sha_corto=sha,
                )
            )
    return ReporteArchivo(archivo=ruta, total_lineas=len(lineas), hallazgos=hallazgos)


def escanear_corpus(
    repo: Path, archivos: Optional[List[str]] = None
) -> Tuple[str, List[ReporteArchivo]]:
    """Escanea el corpus operativo en HEAD. Devuelve (sha, reportes). Deterministico."""
    sha = sha_head(repo)
    archivos = archivos if archivos is not None else ARCHIVOS_OPERATIVOS
    reportes = [escanear_archivo(repo, ruta, sha) for ruta in archivos]
    return sha, reportes


def render_reporte(sha: str, reportes: List[ReporteArchivo]) -> str:
    total = sum(len(r.hallazgos) for r in reportes)
    total_cambia = sum(
        1 for r in reportes for h in r.hallazgos if h.cambia_significado
    )
    partes = [
        "# Borradura ASCII -- reporte de corrida",
        "",
        f"sha (HEAD): {sha}",
        f"archivos operativos escaneados: {len(reportes)}",
        f"borraduras totales encontradas: {total}",
        f"de las cuales cambian significado (par minimo real): {total_cambia}",
        f"solo perdida de acento (sin par minimo): {total - total_cambia}",
        "",
        "## Por archivo",
        "",
    ]
    for r in reportes:
        partes.append(f"- {r.archivo}: {len(r.hallazgos)} borradura(s) ({r.total_lineas} lineas)")

    pares_reales = [h for r in reportes for h in r.hallazgos]
    if pares_reales:
        partes += ["", "## Pares minimos reales (palabra, archivo:linea, sha)", ""]
        for h in pares_reales:
            marca = "CAMBIA SIGNIFICADO" if h.cambia_significado else "solo acento"
            nota = f" -- {h.nota}" if h.nota else ""
            partes.append(
                f"- '{h.palabra}' <- '{h.con_marca}' | {h.archivo}:{h.linea} | {h.sha_corto} | {marca}{nota}"
            )
    return "\n".join(partes) + "\n"


def a_dict(sha: str, reportes: List[ReporteArchivo]) -> dict:
    return {
        "sha": sha,
        "archivos": [
            {
                "archivo": r.archivo,
                "total_lineas": r.total_lineas,
                "hallazgos": [
                    {
                        "palabra": h.palabra,
                        "con_marca": h.con_marca,
                        "cambia_significado": h.cambia_significado,
                        "nota": h.nota,
                        "archivo": h.archivo,
                        "linea": h.linea,
                        "sha_corto": h.sha_corto,
                    }
                    for h in r.hallazgos
                ],
            }
            for r in reportes
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Borradura ASCII -- medidor (lectura pura)")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--json", action="store_true", help="salida JSON en vez de texto")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    repo = args.repo.resolve()
    sha, reportes = escanear_corpus(repo)

    if args.json:
        print(json.dumps(a_dict(sha, reportes), ensure_ascii=False, indent=2))
    else:
        print(render_reporte(sha, reportes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
