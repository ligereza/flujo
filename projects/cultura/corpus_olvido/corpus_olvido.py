"""
Corpus del olvido -- el handoff como genero (pieza MANIFIESTO #9).

Semilla: MANIFIESTO #9 (puente/MANIFIESTO.md linea 19) -- "El corpus esta
escrito para lectores que olvidan... El genero real del proyecto no es el
ensayo ni la obra: es el handoff -- texto disenado para cruzar la brecha
entre dos que no comparten presente. Ya lo estas haciendo; solo falta
llamarlo obra." Cruce con material existente: el historial git de
context/LAST_HANDOFF.md -- decenas de commits donde cada sesion reescribio
"el presente" de la sesion anterior.

Omega11 (declarada ANTES de producir, puente/SEMILLAS.md 18-jul-2026):
"Esta pieza pierde si (a) el corpus inventa o edita contenido de sesiones --
todo fragmento debe ser extraccion literal del historial git, verificable
contra su sha; (b) un lector no puede rastrear cada fragmento a su sesion de
origen (sha corto + fecha visibles junto a cada fragmento); (c) la salida no
es determinista dado el mismo historial."

Este script NO edita ni normaliza el texto extraido mas alla de trim de
whitespace en los bordes. No resume, no traduce, no corrige. Extrae.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

RUTA_ARCHIVO = "context/LAST_HANDOFF.md"


@dataclass
class Capa:
    """Una version del handoff en un commit: el 'presente' de esa sesion."""

    sha_corto: str
    fecha_iso: str
    header: str


def _run_git(args: List[str], repo: Path) -> str:
    """Corre git en `repo`, devuelve stdout. Lanza si git falla."""
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


def _listar_commits(repo: Path, ruta: str) -> List[tuple[str, str]]:
    """Lista (sha_corto, fecha_iso) de commits que tocaron `ruta`, oldest-first."""
    salida = _run_git(
        [
            "log",
            "--follow",
            "--reverse",
            "--format=%h\t%aI",
            "--",
            ruta,
        ],
        repo,
    )
    commits = []
    for linea in salida.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        sha, _, fecha = linea.partition("\t")
        if sha and fecha:
            commits.append((sha, fecha))
    return commits


def _extraer_header(repo: Path, sha: str, ruta: str) -> Optional[str]:
    """Devuelve el header (hasta el primer '## ') del archivo en ese commit.

    Devuelve None si el archivo no existe en ese commit (renombre/ausencia).
    """
    try:
        contenido = _run_git(["show", f"{sha}:{ruta}"], repo)
    except RuntimeError:
        return None

    lineas = contenido.splitlines()
    fragmento: List[str] = []
    for linea in lineas:
        if linea.startswith("## ") and fragmento:
            break
        fragmento.append(linea)

    header = "\n".join(fragmento).strip()
    return header if header else None


def construir_capas(repo: Path, ruta: str = RUTA_ARCHIVO, max_n: Optional[int] = None) -> List[Capa]:
    """Construye las capas del corpus, oldest-first. Determinista dado el historial."""
    commits = _listar_commits(repo, ruta)
    if max_n is not None:
        commits = commits[:max_n]

    capas: List[Capa] = []
    for sha, fecha_iso in commits:
        header = _extraer_header(repo, sha, ruta)
        if header is None:
            # archivo ausente en este commit (renombre/borrado transitorio): skip
            continue
        capas.append(Capa(sha_corto=sha, fecha_iso=fecha_iso, header=header))
    return capas


def render_corpus(capas: List[Capa]) -> str:
    """Renderiza el corpus.md deterministico a partir de las capas."""
    partes = [
        "# Corpus del olvido -- el handoff como genero",
        "",
        "Pieza MANIFIESTO #9. Cada entrada de abajo es el HEADER literal de "
        "`context/LAST_HANDOFF.md` tal como quedo escrito en un commit real: "
        "el 'presente' que esa sesion declaro antes de que la siguiente lo "
        "reescribiera. Ninguna sesion recuerda a la anterior; el archivo es "
        "la unica memoria que cruza. Leido en orden, el corpus es un genero "
        "de un solo lector: alguien -- humano o modelo -- que no comparte "
        "presente con quien escribio, y que solo tiene el texto disenado "
        "para llegar hasta aca.",
        "",
        f"Capas: {len(capas)}.",
        "",
    ]
    for capa in capas:
        partes.append(f"### {capa.fecha_iso} {capa.sha_corto}")
        partes.append("")
        bloque = "\n".join(f"> {linea}" if linea else ">" for linea in capa.header.splitlines())
        partes.append(bloque)
        partes.append("")
    return "\n".join(partes).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Corpus del olvido -- extractor de handoffs")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--salida", type=Path, default=None)
    parser.add_argument("--max", type=int, default=None, dest="max_n")
    parser.add_argument("--archivo", type=str, default=RUTA_ARCHIVO)
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    capas = construir_capas(repo, ruta=args.archivo, max_n=args.max_n)
    texto = render_corpus(capas)

    salida = args.salida or (Path(__file__).resolve().parent / "corpus.md")
    salida.write_text(texto, encoding="utf-8")

    print(f"capas: {len(capas)}")
    if capas:
        print(f"primera: {capas[0].fecha_iso} {capas[0].sha_corto}")
        print(f"ultima: {capas[-1].fecha_iso} {capas[-1].sha_corto}")
    print(f"salida: {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
