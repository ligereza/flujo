#!/usr/bin/env python3
"""
Tapiz de la borradura -- salida ASCII de la pieza borradura_ascii.

El texto del corpus operativo sobrevive tal cual (es ASCII, la regla lo
exige). Debajo de cada linea con una borradura real, una segunda linea
marca con '^' el hueco: la posicion exacta donde el diacritico vivia antes
de que el plegado a ASCII lo borrara. El mismo ASCII que en la base de
datos historica del repo fue la HERIDA (el bug de encoding que origino la
regla) es aca el MEDIO del tapiz -- esa tension es la pieza.

Determinista: dado el mismo commit (HEAD), la misma corrida de
borradura.escanear_corpus() produce el mismo tapiz, byte a byte. Lectura
pura -- este script no toca los .md que mide, solo lee (via borradura.py,
que a su vez usa `git show`) y escribe su propio tapiz.txt.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from borradura import (  # noqa: E402
    ARCHIVOS_OPERATIVOS,
    Hallazgo,
    ReporteArchivo,
    escanear_corpus,
    leer_operativo,
)

ANCHO_SEPARADOR = 78


def _huecos_de_palabra(con_marca: str, ascii_forma: str) -> List[int]:
    """
    Indices (dentro de la forma ascii) donde vivia un diacritico borrado.

    Compara con_marca (con tilde) contra su forma ascii char a char via NFD:
    si un caracter de con_marca se descompone en base+marca combinante, esa
    posicion es un hueco. Solo funciona si ambas formas tienen igual
    longitud (el plegado 1:1 -- ver tilde_residuo.plegar). Si difieren en
    longitud (p.ej. "disenio", variante informal con 'i' insertada en vez
    de tilde borrada), no hay mapeo posicion-a-posicion confiable: se
    marca la palabra entera como hueco (mas honesto que adivinar el indice).
    """
    if len(con_marca) != len(ascii_forma):
        return list(range(len(ascii_forma)))
    huecos = []
    for i, ch in enumerate(con_marca):
        descompuesto = unicodedata.normalize("NFD", ch)
        tiene_marca = any(unicodedata.combining(c) for c in descompuesto)
        if tiene_marca:
            huecos.append(i)
    return huecos


def _linea_huecos(linea: str, hallazgos_en_linea: List[Hallazgo]) -> str:
    """Construye la linea de huecos ('^' bajo cada diacritico borrado)."""
    marcador = [" "] * len(linea)
    cursor = 0
    for h in hallazgos_en_linea:
        # ubicar la palabra en la linea empezando desde donde quedamos
        idx = linea.find(h.palabra, cursor)
        if idx == -1:
            idx = linea.find(h.palabra)  # fallback: primera ocurrencia
        if idx == -1:
            continue
        for off in _huecos_de_palabra(h.con_marca, h.palabra):
            pos = idx + off
            if 0 <= pos < len(marcador):
                marcador[pos] = "^"
        cursor = idx + len(h.palabra)
    return "".join(marcador).rstrip()


def render_tapiz(repo: Path, reportes: List[ReporteArchivo], sha: str) -> str:
    partes = [
        "TAPIZ DE LA BORRADURA -- pieza cultural, lectura pura",
        f"sha (HEAD): {sha}",
        "cada caracter del texto sobrevive tal como esta (ASCII, por regla);",
        "cada '^' debajo marca donde vivia un diacritico que la regla borro.",
        "=" * ANCHO_SEPARADOR,
        "",
    ]
    cache_contenido: Dict[str, Optional[str]] = {}
    for r in reportes:
        if not r.hallazgos:
            continue
        if r.archivo not in cache_contenido:
            cache_contenido[r.archivo] = leer_operativo(repo, r.archivo)
        contenido = cache_contenido[r.archivo]
        if contenido is None:
            continue
        lineas = contenido.splitlines()

        por_linea: Dict[int, List[Hallazgo]] = {}
        for h in r.hallazgos:
            por_linea.setdefault(h.linea, []).append(h)

        partes.append(f"--- {r.archivo} ({len(r.hallazgos)} hueco(s)) ---")
        for num_linea in sorted(por_linea):
            texto = lineas[num_linea - 1] if num_linea - 1 < len(lineas) else ""
            huecos = _linea_huecos(texto, por_linea[num_linea])
            partes.append(f"{num_linea:>5} | {texto}")
            partes.append(f"      | {huecos}")
        partes.append("")

    return "\n".join(partes).rstrip() + "\n"


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    sha, reportes = escanear_corpus(repo, ARCHIVOS_OPERATIVOS)
    texto = render_tapiz(repo, reportes, sha)
    salida = Path(__file__).resolve().parent / "tapiz.txt"
    salida.write_text(texto, encoding="ascii", errors="replace")
    print(f"tapiz escrito: {salida} ({len(texto.splitlines())} lineas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
