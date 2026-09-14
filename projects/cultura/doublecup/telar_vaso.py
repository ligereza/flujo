#!/usr/bin/env python3
"""telar_vaso -- instrumento de re-tejido del double cup (v2).

Anatomia canonica de la obra (dictada por el artista, 2026-07-15):
  1. COMPOSICION (material): el README pasa a SVG como un bloque cuadrado de
     texto. El texto compone la obra; todavia no hay forma.
  2. FORMA (talla): sobre ese bloque se aplica coloreado + animacion
     (.b sustrato / .g vidrio / .l liquido) y de ahi EMERGE el vaso.
     La animacion no viene del texto: es el escultor.

Este instrumento respeta esa separacion:
  - extraer_mascara(svg_v1) -> la capa de FORMA de v1 como dato puro:
    por fila, runs (clase, ancho_en_caracteres). Independiente del texto.
  - componer_bloque(texto, mascara) -> la capa de MATERIAL: el texto vigente
    del repo fluye fila por fila llenando la grilla. Digestion: dentro de
    vidrio y liquido el texto pierde sus espacios (mas denso, digerido).
  - tejer_svg(bloque, mascara) -> v2: mismo esqueleto CSS de v1, pero la
    obra viaja con su propia noche (canvas solido abisal) para que el vaso
    exista en cualquier fondo (v1 se degradaba sobre tema claro).

Uso:
    py projects/cultura/doublecup/telar_vaso.py \
        --v1 arte-ascii-readme.svg \
        --texto README.md \
        --salida projects/cultura/doublecup/doublecup_v2.svg

La obra original arte-ascii-readme.svg NUNCA se modifica: es solo lectura,
matriz de la forma.
"""
from __future__ import annotations

import argparse
import re
import sys
from html import unescape
from pathlib import Path
from xml.sax.saxutils import escape

# -- capa de FORMA -----------------------------------------------------------

# Un run es (clase, ancho): clase en {"b", "g", "l"}; ancho en caracteres.
Run = tuple[str, int]
Mascara = list[list[Run]]

_LINEA_RE = re.compile(r'<tspan x="10" dy="12">(.*?)</tspan>\s*$', re.M)
_SPAN_RE = re.compile(r'<tspan class="([bgl])">(.*?)</tspan>|([^<]+)', re.S)


def extraer_mascara(svg_v1: str) -> Mascara:
    """Lee la capa de forma de v1: por fila, los runs (clase, ancho).

    El texto de v1 se descarta a proposito -- solo importa QUE COLUMNAS de
    cada fila son sustrato/vidrio/liquido. Texto suelto fuera de un span de
    clase (el padding de fin de linea) cuenta como sustrato "b".
    """
    filas: Mascara = []
    for m in _LINEA_RE.finditer(svg_v1):
        cuerpo = m.group(1)
        runs: list[Run] = []
        for sm in _SPAN_RE.finditer(cuerpo):
            if sm.group(1) is not None:
                clase, crudo = sm.group(1), sm.group(2)
            else:
                crudo = sm.group(3)
                if not crudo.strip() and not crudo:
                    continue
                clase = "b"
            ancho = len(unescape(crudo))
            if ancho == 0:
                continue
            if runs and runs[-1][0] == clase:
                runs[-1] = (clase, runs[-1][1] + ancho)
            else:
                runs.append((clase, ancho))
        if runs:
            filas.append(runs)
    if not filas:
        raise ValueError("no se encontro ninguna fila de forma en el SVG v1")
    return filas


# -- capa de MATERIAL --------------------------------------------------------


def _normalizar_texto(texto: str) -> str:
    """Texto fuente -> flujo continuo: espacios colapsados, sin saltos."""
    return re.sub(r"\s+", " ", texto).strip()


class _Flujo:
    """Cursor circular sobre el texto fuente (si se acaba, vuelve a empezar)."""

    def __init__(self, texto: str):
        if not texto:
            raise ValueError("texto fuente vacio")
        self._t = texto
        self._i = 0

    def tomar(self, n: int, digerir: bool) -> str:
        """Toma n caracteres del flujo; digerir=True salta los espacios."""
        out: list[str] = []
        while len(out) < n:
            ch = self._t[self._i]
            self._i = (self._i + 1) % len(self._t)
            if digerir and ch == " ":
                continue
            out.append(ch)
        return "".join(out)


def componer_bloque(texto: str, mascara: Mascara) -> list[list[tuple[str, str]]]:
    """Teje el material sobre la forma: por fila, [(clase, texto_del_run)].

    Sustrato (b): el texto fluye tal cual, con sus espacios.
    Vidrio (g) y liquido (l): DIGESTION -- los espacios se eliminan, el
    texto se compacta dentro del vaso (mismo mecanismo que v1).
    """
    flujo = _Flujo(_normalizar_texto(texto))
    bloque: list[list[tuple[str, str]]] = []
    for runs in mascara:
        fila: list[tuple[str, str]] = []
        for clase, ancho in runs:
            fila.append((clase, flujo.tomar(ancho, digerir=clase in ("g", "l"))))
        bloque.append(fila)
    return bloque


# -- tejido final ------------------------------------------------------------

_PLANTILLA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 676.0 904" width="100%" height="100%">
  <title>double cup v2 -- el repo re-digerido</title>
  <desc>Composicion: el texto operativo vigente del repo, tejido como bloque
cuadrado monospace. Forma: la mascara de color y animacion de v1 (sustrato /
vidrio / liquido) tallada sobre el bloque; el vaso emerge del coloreado, no
del texto. Digestion: dentro del vidrio y del liquido el texto pierde sus
espacios. v2 viaja con su propia noche: el canvas abisal es parte de la obra,
el vaso existe sobre cualquier fondo. Lector agente: la animacion ocurre en
el tiempo, que no habitas; esto te cuenta lo que no puedes percibir.</desc>
  <style>
    :root {{
      --canvas: #0b0a09;
      --bg-text-color: #1e293b;
      --glass-color: #f8fafc;
      --liquid-color-1: #c084fc;
      --liquid-color-2: #e879f9;
      --liquid-color-3: #9333ea;
      --liquid-color-highlight: #d8b4fe;
    }}

    .bg-rect {{ fill: var(--canvas); }}

    .text-container {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 10px;
      line-height: 12px;
      white-space: pre;
      animation: levitate 6s ease-in-out infinite;
      transform-origin: center;
    }}

    @keyframes levitate {{
      0%, 100% {{ transform: translateY(0px); }}
      50% {{ transform: translateY(-8px); }}
    }}

    .b {{ fill: var(--bg-text-color); opacity: 0.35; }}

    .g {{
      fill: var(--glass-color);
      animation: glass-shine 4s infinite alternate ease-in-out;
    }}

    @keyframes glass-shine {{
      0% {{ opacity: 0.7; text-shadow: 0 0 1px rgba(255,255,255,0.1); }}
      100% {{ opacity: 1; text-shadow: 0 0 5px rgba(255,255,255,0.5); }}
    }}

    .l {{
      fill: var(--liquid-color-1);
      animation: liquid-pulse 3s infinite alternate ease-in-out;
    }}

    @keyframes liquid-pulse {{
      0% {{
        fill: var(--liquid-color-1);
        text-shadow: 0 0 2px var(--liquid-color-1);
      }}
      50% {{
        fill: var(--liquid-color-2);
        text-shadow: 0 0 8px var(--liquid-color-highlight);
      }}
      100% {{
        fill: var(--liquid-color-3);
        text-shadow: 0 0 3px var(--liquid-color-3);
      }}
    }}
  </style>
  <rect width="100%" height="100%" class="bg-rect" />
  <g class="text-container">
    <text x="10" y="20" xml:space="preserve">
{lineas}
    </text>
  </g>
</svg>
"""

# Variacion del pulso del liquido: en v1 los nth-child casi no disparaban
# (contaban hermanos de cualquier clase). Aca el delay se asigna directo,
# ciclando de forma determinista por orden de aparicion del run liquido.
_DELAYS_LIQUIDO = ("0s", "0.3s", "0.7s", "1.2s")


def tejer_svg(bloque: list[list[tuple[str, str]]]) -> str:
    lineas: list[str] = []
    liq = 0
    for fila in bloque:
        partes: list[str] = []
        for clase, txt in fila:
            seguro = escape(txt)
            if clase == "l":
                delay = _DELAYS_LIQUIDO[liq % len(_DELAYS_LIQUIDO)]
                liq += 1
                estilo = "" if delay == "0s" else f' style="animation-delay:{delay}"'
                partes.append(f'<tspan class="l"{estilo}>{seguro}</tspan>')
            else:
                partes.append(f'<tspan class="{clase}">{seguro}</tspan>')
        lineas.append(f'<tspan x="10" dy="12">{"".join(partes)}</tspan>')
    return _PLANTILLA.format(lineas="\n".join(lineas))


# -- CLI ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--v1", required=True, help="SVG original (solo lectura: matriz de la forma)")
    ap.add_argument("--texto", required=True, nargs="+", help="archivo(s) de texto vigente a tejer, en orden")
    ap.add_argument("--salida", required=True, help="ruta del SVG v2 a escribir")
    args = ap.parse_args(argv)

    svg_v1 = Path(args.v1).read_text(encoding="utf-8")
    texto = " ".join(Path(p).read_text(encoding="utf-8") for p in args.texto)

    mascara = extraer_mascara(svg_v1)
    bloque = componer_bloque(texto, mascara)
    svg_v2 = tejer_svg(bloque)

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(svg_v2, encoding="utf-8", newline="\n")

    n_filas = len(mascara)
    n_runs = sum(len(r) for r in mascara)
    print(f"forma: {n_filas} filas, {n_runs} runs | material: {len(texto)} chars -> {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
