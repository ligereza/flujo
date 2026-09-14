#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera la tabla de comandos de MAPA.md preguntandole al CLI, no a la memoria.

Por que existe (2026-07-25): tres auditorias seguidas se equivocaron sobre lo
que el repo tiene porque leyeron prosa vieja en vez de medir. La tabla de
comandos de MAPA.md no se escribe a mano: se genera desde `flujo --help`, asi
un comando nuevo aparece solo y uno retirado desaparece solo.

Uso:
    py tools/gen_mapa_comandos.py            # reescribe el bloque en MAPA.md
    py tools/gen_mapa_comandos.py --check    # falla si MAPA.md quedo desfasado

El bloque vive entre los marcadores INICIO/FIN; el resto de MAPA.md se escribe
a mano y este script no lo toca.

Retiro: cuando el CLI exponga su propio `flujo mapa` y este script sea el que
lo llame.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MAPA = RAIZ / "MAPA.md"
INICIO = "<!-- COMANDOS:INICIO -- generado por tools/gen_mapa_comandos.py, no editar a mano -->"
FIN = "<!-- COMANDOS:FIN -->"

# Que necesita cada comando ANTES de funcionar. Vacio = nada, se corre y anda.
# Se escribe a mano a proposito: es la unica columna que el --help no sabe.
COMANDOS = MAPA.parent / "context" / "comandos.json"

REQUISITOS: dict[str, str] = {
    "index": "`FLUJO_RD_ROOT` apuntando al arbol de material",
    "hub index": "`FLUJO_RD_ROOT` apuntando al arbol de material",
    "hub route": "`FLUJO_RD_ROOT` apuntando al arbol de material",
    "flyer-import": "casilla de correo: `FLUJO_IMAP_HOST`, `FLUJO_IMAP_USER`, "
                    "`FLUJO_IMAP_PASSWORD`, `FLUJO_IMAP_ALLOWED_SENDERS`",
    "eventos flyer-auto": "`pip install parth-dl`; para render tambien Blender",
    "ig-redownload": "`pip install parth-dl`",
    "render run": "Blender instalado",
    "render bridge": "Adobe Illustrator (solo Windows/macOS)",
    "render illustrator": "Adobe Illustrator (solo Windows/macOS)",
    "suplementos illustrator": "Adobe Illustrator (solo Windows/macOS)",
    "resolume automatizar": "Chataigne y Resolume abiertos en la maquina del show",
    "package": "solo Windows; empaqueta un .exe",
    "rd-db build": "fuentes de datos en `data/` (la DB se regenera, no se versiona)",
    "rd-datos ingest": "un CSV de campo; la DB privacy-first se crea sola",
    "autonomia run": "La ejecucion remota esta fuera de este entorno; "
                     "`--executor local` solo para pruebas/dry-run con "
                     "autoridad explicita",
}
# `tapiz` used to sit in the table above with the requirement "nada; el
# instrumento vive en `tools/compete_engine.py`" -- prose that says there is NO
# requirement, sitting in the field that means "this is missing". The generator
# does what it is told and emitted `estado: "falta: nada; ..."`, so a button
# would announce that the command lacks nothing. A requirement of "nada" is an
# empty requirement; where the instrument lives belongs in the description.


def _help(path: list[str]) -> str:
    # encoding/errors are explicit ON PURPOSE. With plain `text=True`, Python on
    # Windows decodes the child's stdout using the locale codepage (cp1252), and
    # the CLI help contains bytes cp1252 cannot map. The reader thread then dies,
    # `r.stdout` comes back as None, and the caller crashes three frames away
    # with "'NoneType' object has no attribute 'splitlines'" -- which points
    # nowhere near the real cause. Found 2026-07-26: this tool had been silently
    # broken, so the command table could not be regenerated or checked.
    entorno = {
        **os.environ,
        "COLUMNS": "400",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    # El checkout es portable y puede convivir con artefactos historicos del
    # mismo proyecto. El mapa debe interrogar ESTE src/, no el paquete que casualmente gane en
    # sys.path del entorno global.
    raiz_src = str(RAIZ / "src")
    pythonpath = entorno.get("PYTHONPATH", "")
    entorno["PYTHONPATH"] = raiz_src + (os.pathsep + pythonpath if pythonpath else "")
    r = subprocess.run(
        [sys.executable, "-m", "flujo", *path, "--help"],
        capture_output=True, env=entorno, cwd=RAIZ,
        encoding="utf-8", errors="replace",
    )
    return r.stdout or ""


def _parse(texto: str) -> list[tuple[str, str]]:
    """Saca (comando, descripcion) del panel Commands de typer/rich."""
    filas: list[list[str]] = []
    dentro = False
    for linea in texto.splitlines():
        if "─ Commands ─" in linea:
            dentro = True
            continue
        if dentro and linea.startswith("╰"):
            break
        if not dentro or not linea.startswith("│"):
            continue
        cuerpo = linea[1:-1].rstrip()
        m = re.match(r"^\s*(\S+)\s\s+(.*)$", cuerpo)
        if m and not m.group(1).startswith("-"):
            filas.append([m.group(1), m.group(2).strip()])
        elif filas and cuerpo.strip():
            # descripcion que sigue en la linea de abajo
            filas[-1][1] = (filas[-1][1] + " " + cuerpo.strip()).strip()
    return [(a, b) for a, b in filas]


def arbol_cli() -> dict[str, dict]:
    arbol: dict[str, dict] = {}
    for nombre, desc in _parse(_help([])):
        arbol[nombre] = {"desc": desc, "sub": _parse(_help([nombre]))}
    return arbol


def invocables(arbol: dict[str, dict]) -> list[str]:
    """Todo lo que un humano puede tipear y que hace algo."""
    out = []
    for nombre, datos in arbol.items():
        if datos["sub"]:
            out += [f"{nombre} {sub}" for sub, _ in datos["sub"]]
        else:
            out.append(nombre)
    return out


# Comandos que CAMBIAN algo fuera del repo o que no se deshacen solos. Un boton
# que borra no puede verse igual que uno que lista.
#
# Es una lista DECLARADA, no adivinada. La primera version los deducia buscando
# verbos dentro del nombre ("delete", "push", "aplicar"...), que es precisamente
# la lista escrita a mano que se queda vieja y descarta en silencio -- el defecto
# que este repo encontro tres veces en un dia. Un nombre no dice lo que un
# comando hace.
#
# Y lo que NO esta declarado sale como `null`, no como `false`: "nadie lo
# declaro" no es lo mismo que "es seguro". Rellenar esa ausencia con un valor
# plausible es como un campo de atribucion se vuelve inutil.
DESTRUCTIVOS: frozenset[str] = frozenset({
    "datadrop prepare",
    "index",
    "hub index",
    "resolume automatizar",
    "render run",
    "render bridge",
    "render illustrator",
    "eventos flyer-auto",
    "flyer-import",
    "ig-redownload",
})


def manifiesto(arbol: dict[str, dict]) -> dict:
    """El CLI como DATOS, no como prosa.

    `MAPA.md` ya se genera de la introspeccion real del CLI, pero sale a
    markdown: para usarlo hay que copiar y pegar. Un boton no puede leer prosa,
    y un agente gratuito al que se le habla en abstracto tampoco. Esto es la
    misma verdad en la forma que consume una maquina, y se regenera del mismo
    lugar -- si el CLI cambia y esto no, el mismo `--check` que cuida la tabla
    lo va a decir.

    Cada entrada trae `estado`, que es lo que permite presentar OBJETIVOS en vez
    de comandos: `listo` cuando no necesita nada, o lo que le falta.
    """
    salida = []
    for cmd in invocables(arbol):
        raiz = cmd.split(" ")[0]
        datos = arbol[raiz]
        desc = dict(datos["sub"]).get(cmd.split(" ", 1)[1], "") if datos["sub"] else datos["desc"]
        req = REQUISITOS.get(cmd, "")
        salida.append({
            "cmd": cmd,
            "invocacion": "py -m flujo " + cmd,
            "grupo": raiz if datos["sub"] else "",
            "desc": (desc or "").strip(),
            "requiere": req,
            "estado": "listo" if not req else "falta: " + req,
            # null = nadie lo declaro. Ver el comentario de DESTRUCTIVOS.
            "destructivo": True if cmd in DESTRUCTIVOS else None,
        })
    return {
        "formato": "comandos/1",
        "total": len(salida),
        "grupos": sorted({e["grupo"] for e in salida if e["grupo"]}),
        "comandos": salida,
    }


def _fila(cmd: str, desc: str) -> str:
    req = REQUISITOS.get(cmd, "")
    desc = desc.replace("|", "\\|").strip() or "(sin descripcion en el --help)"
    if len(desc) > 200:
        desc = desc[:197].rstrip() + "..."
    return f"| `py -m flujo {cmd}` | {desc} | {req or 'nada'} |"


def render(arbol: dict[str, dict]) -> str:
    L = [INICIO, ""]
    L.append(f"Medido sobre el CLI real: **{len(invocables(arbol))} comandos** "
             f"({sum(1 for d in arbol.values() if not d['sub'])} sueltos + "
             f"{sum(len(d['sub']) for d in arbol.values())} dentro de "
             f"{sum(1 for d in arbol.values() if d['sub'])} grupos).")
    L.append("")
    sueltos = [(n, d["desc"]) for n, d in arbol.items() if not d["sub"]]
    if sueltos:
        L += ["### Comandos sueltos", "",
              "| Comando | Que hace | Que necesita antes |", "|---|---|---|"]
        L += [_fila(n, d) for n, d in sorted(sueltos)]
        L.append("")
    for nombre in sorted(n for n, d in arbol.items() if d["sub"]):
        datos = arbol[nombre]
        L += [f"### Grupo `{nombre}` -- {datos['desc']}", "",
              "| Comando | Que hace | Que necesita antes |", "|---|---|---|"]
        L += [_fila(f"{nombre} {sub}", desc) for sub, desc in datos["sub"]]
        L.append("")
    L.append(FIN)
    return "\n".join(L)


def aplicar(bloque: str) -> str:
    texto = MAPA.read_text(encoding="utf-8")
    if INICIO not in texto or FIN not in texto:
        raise SystemExit("MAPA.md no tiene los marcadores COMANDOS:INICIO/FIN")
    antes = texto[: texto.index(INICIO)]
    despues = texto[texto.index(FIN) + len(FIN):]
    return antes + bloque + despues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="no escribe: falla si MAPA.md quedo desfasado del CLI")
    args = ap.parse_args()

    arbol = arbol_cli()
    nuevo = aplicar(render(arbol))

    # El manifiesto sale SIEMPRE que se regenere la tabla, del mismo arbol: dos
    # generadores separados es como una lista escrita a mano se queda vieja.
    man = json.dumps(manifiesto(arbol), ensure_ascii=False, indent=1) + chr(10)
    man_actual = COMANDOS.read_text(encoding="utf-8") if COMANDOS.exists() else ""

    actual = MAPA.read_text(encoding="utf-8")
    if nuevo == actual and man == man_actual:
        print("MAPA.md y context/comandos.json al dia con el CLI.")
        return 0
    if args.check:
        print("MAPA.md o context/comandos.json DESFASADO del CLI. Corre: "
              "py tools/gen_mapa_comandos.py", file=sys.stderr)
        return 1
    if man != man_actual:
        COMANDOS.parent.mkdir(parents=True, exist_ok=True)
        COMANDOS.write_text(man, encoding="utf-8")
        print("context/comandos.json actualizado (%d comandos)."
              % manifiesto(arbol)["total"])
    if nuevo == actual:
        return 0
    MAPA.write_text(nuevo, encoding="utf-8")
    print("MAPA.md actualizado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
