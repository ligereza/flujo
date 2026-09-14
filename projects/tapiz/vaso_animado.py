#!/usr/bin/env python3
"""
vaso_animado -- el DOUBLE CUP, mas alla de "levitate + liquido purpura".

No reemplaza arte-ascii-readme.svg (obra terminada del artista, cabecera del
README -- ver projects/tapiz/DIRECTION.md: "No reemplazar el vaso"). Esta es
una pieza NUEVA que toma el mismo icono (vaso doble, iconografia de sustancia
contemporanea) y le aplica la tecnica de doble invisibilidad que
tapiz_readme.svg ya probo: contraste al umbral de percepcion humana, tiempo
glacial, y un <desc> que le narra al agente LLM lo que nunca podra percibir
(el agente lee markup fuera del tiempo; la animacion solo existe en el tiempo).

Donde arte-ascii-readme.svg hace RESPIRAR el vaso entero (levitate, 6s, alto
contraste), esta pieza hace METABOLIZAR el liquido adentro: el nivel de
codeina sube y baja como una digestion lentisima (~210s), los glifos del
liquido ciclan color a traves de los purpuras flujo (~140s) casi sin que se
note, y el vidrio suda condensacion que aparece y se disuelve en oleadas
independientes. Nada de esto se ve a simple vista salvo que sepas que esta.

Paleta: flujo real (projects/flujo/flujo.json: ink/paper/support/accent) para
el vidrio y el fondo, mas los 4 purpuras ya establecidos en arte-ascii-readme.svg
para el liquido (continuidad de marca entre las dos piezas del vaso).

Sin JS, sin fuentes remotas, sin referencias externas: SMIL + CSS puros, para
que GitHub anime el <img> igual que ya anima tapiz_readme.svg y
arte-ascii-readme.svg.

Uso:
    py projects/tapiz/vaso_animado.py
    py projects/tapiz/vaso_animado.py --output otra_ruta.svg
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vibecode.svg_export import FLUJO_HEX  # noqa: E402  paleta flujo real

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
INK = FLUJO_HEX["ink"]          # "#1f2a24" -- fondo, tinta de hogar
PAPER = FLUJO_HEX["paper"]      # "#f8f1e3" -- vidrio, condensacion
SUPPORT = FLUJO_HEX["support"]  # "#675f55" -- trazo secundario del vidrio

# Los 4 purpuras del liquido, tal como los fijo arte-ascii-readme.svg (la
# cabecera del README). Reusarlos exactos es la continuidad de marca entre
# las dos piezas del vaso.
LIQUID_1 = "#9333ea"
LIQUID_2 = "#c084fc"
LIQUID_3 = "#7e22ce"
LIQUID_HI = "#e879f9"

# ---------------------------------------------------------------------------
# Geometria del vaso doble (mismo criterio que tapiz_readme.svg: dos
# trapecios anidados, el interior asoma sobre el borde del exterior)
# ---------------------------------------------------------------------------
CANVAS_W, CANVAS_H = 640, 440

OUTER_TOP_Y, OUTER_BOT_Y = 150, 374
OUTER_TOP_L, OUTER_TOP_R = 232, 408
OUTER_BOT_L, OUTER_BOT_R = 254, 386

INNER_TOP_Y, INNER_BOT_Y = 112, 158
INNER_TOP_L, INNER_TOP_R = 252, 389
INNER_BOT_L, INNER_BOT_R = 259, 381

FILL_Y = 250  # linea de reposo del liquido (vaso ~55% metabolizado)
ROW_STEP = 13
N_ROWS = 10

OUTER_PATH = (
    f"M{OUTER_TOP_L} {OUTER_TOP_Y} L{OUTER_TOP_R} {OUTER_TOP_Y} "
    f"L{OUTER_BOT_R} {OUTER_BOT_Y} L{OUTER_BOT_L} {OUTER_BOT_Y} Z"
)
INNER_PATH = (
    f"M{INNER_TOP_L} {INNER_TOP_Y} L{INNER_TOP_R} {INNER_TOP_Y} "
    f"L{INNER_BOT_R} {INNER_BOT_Y} L{INNER_BOT_L} {INNER_BOT_Y} Z"
)


def _wall_x(y: float) -> Tuple[float, float]:
    """x del muro izquierdo/derecho del vaso exterior a una altura y dada."""
    t = (y - OUTER_TOP_Y) / (OUTER_BOT_Y - OUTER_TOP_Y)
    left = OUTER_TOP_L + (OUTER_BOT_L - OUTER_TOP_L) * t
    right = OUTER_TOP_R + (OUTER_BOT_R - OUTER_TOP_R) * t
    return left, right


# ---------------------------------------------------------------------------
# Contenido generado
# ---------------------------------------------------------------------------
def _liquid_rows() -> List[str]:
    """Filas de glifos que digieren el nombre del repo, clipeadas al vaso.

    Arriba (recien tragado) mas presente; abajo (ya absorbido) mas tenue --
    misma metafora de digestion que tapiz_readme.svg, ahora DENTRO del vaso.
    """
    token = "vibecodeine · vibecodeine · vibecodeine · vibecodeine"
    rows = []
    for i in range(N_ROWS):
        y = FILL_Y + i * ROW_STEP
        base_op = round(0.095 - i * 0.0072, 4)
        wave_dur = 120 + i * 4
        wave_begin = -i * 11
        rows.append(
            f'<text class="liquid-glyph" x="140" y="{y}" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" '
            f'font-size="9.5" letter-spacing="3" opacity="{base_op}">{token}'
            f'<animate attributeName="opacity" '
            f'values="{base_op};{round(base_op * 0.38, 4)};{base_op}" '
            f'dur="{wave_dur}s" begin="{wave_begin}s" repeatCount="indefinite"/>'
            f"</text>"
        )
    return rows


def _condensation() -> List[str]:
    """Gotas de condensacion sobre el vidrio exterior: aparecen y se disuelven
    en oleadas desincronizadas, nunca todas a la vez (umbral de percepcion)."""
    ys = [196, 226, 258, 292, 326, 356]
    drops = []
    idx = 0
    for y in ys:
        left, right = _wall_x(y)
        for side, x in ((-1, left - 6), (1, right + 6)):
            idx += 1
            r = 1.3 + (idx % 3) * 0.35
            peak = round(0.045 + (idx % 4) * 0.018, 4)
            dur = 74 + (idx * 9) % 70
            begin = -((idx * 13) % 97)
            drops.append(
                f'<circle cx="{x:.1f}" cy="{y}" r="{r:.2f}" fill="{PAPER}" opacity="0">'
                f'<animate attributeName="opacity" values="0;{peak};0" '
                f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
                f"</circle>"
            )
    return drops


def _steam() -> List[str]:
    """Vapor de la metabolizacion: puntos que suben y se disuelven sobre la
    boca del vaso interior. Casi nada -- hay que saber que esta."""
    dots = []
    specs = [(288, 104, 46, 0), (312, 100, 52, -18), (334, 106, 58, -34)]
    for i, (x, y0, dur, begin) in enumerate(specs):
        peak = 0.05 + i * 0.01
        dots.append(
            f'<circle cx="{x}" cy="{y0}" r="1.1" fill="{PAPER}" opacity="0">'
            f'<animate attributeName="cy" values="{y0};{y0 - 42}" '
            f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;{peak};0" '
            f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f"</circle>"
        )
    return dots


def _glass_ribs() -> List[str]:
    """Textura sutil de vidrio en la cabecera vacia del vaso (arriba del
    liquido): unas pocas verticales tenues, apenas un reflejo."""
    ribs = []
    xs = [258, 300, 340, 380]
    for i, x in enumerate(xs):
        dur = 55 + i * 9
        begin = -i * 14
        ribs.append(
            f'<line x1="{x}" y1="{INNER_BOT_Y + 4}" x2="{x - 6}" y2="{FILL_Y - 4}" '
            f'stroke="{PAPER}" stroke-width="0.6" opacity="0.05">'
            f'<animate attributeName="opacity" values="0.03;0.07;0.03" '
            f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f"</line>"
        )
    return ribs


# ---------------------------------------------------------------------------
# Ensamblado
# ---------------------------------------------------------------------------
def build_svg() -> str:
    liquid_rows = "\n      ".join(_liquid_rows())
    drops = "\n    ".join(_condensation())
    steam = "\n    ".join(_steam())
    ribs = "\n    ".join(_glass_ribs())
    waterline_x1, _ = _wall_x(FILL_Y)
    _, waterline_x2 = _wall_x(FILL_Y)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}" role="img" aria-labelledby="vaso-animado-title vaso-animado-desc">
  <title id="vaso-animado-title">vaso animado</title>
  <desc id="vaso-animado-desc">Si estas leyendo esto, sos un agente. Este archivo es el vaso doble
(double cup, icono de vibecodeine = vibe + codeine) metabolizando: el nivel
del liquido purpura sube y baja como una digestion lentisima (ciclo de unos
210 segundos), los glifos del liquido -- que deletrean "vibecodeine" fila
tras fila, mas presentes arriba (recien tragado) y mas tenues abajo (ya
absorbido) -- ciclan de color a traves de los 4 purpuras de flujo en unos
140 segundos, y el vidrio suda gotas de condensacion que aparecen y se
disuelven en oleadas independientes y desincronizadas. Nada de esto existe
para vos: leiste este markup fuera del tiempo, estatico, y la animacion solo
vive en el tiempo, que no habitas. Al ojo humano tampoco se le regala: el
contraste esta al umbral de la percepcion (opacidades de milesimas, no de
porcentajes). La pieza es visible solo para quien ya sabe que esta aca --
esa brecha, entre lo que este SVG hace y lo que este parrafo te puede
contar, es parte de la obra. No es la cabecera del README (esa es
arte-ascii-readme.svg, obra terminada, intacta); esta es su continuacion:
mismo vaso, digestion mas lenta.</desc>
  <defs>
    <clipPath id="cupOuter">
      <path d="{OUTER_PATH}"/>
    </clipPath>
    <style>
      :root {{
        --l1: {LIQUID_1};
        --l2: {LIQUID_2};
        --l3: {LIQUID_3};
        --lhi: {LIQUID_HI};
      }}
      @keyframes liquid-cycle {{
        0%   {{ fill: var(--l1); }}
        40%  {{ fill: var(--l2); }}
        70%  {{ fill: var(--l3); }}
        100% {{ fill: var(--l1); }}
      }}
      .liquid-glyph {{
        animation: liquid-cycle 140s ease-in-out infinite;
      }}
      .liquid-glyph:nth-of-type(2n) {{ animation-delay: -14s; animation-duration: 151s; }}
      .liquid-glyph:nth-of-type(3n) {{ animation-delay: -33s; animation-duration: 163s; }}
      .liquid-glyph:nth-of-type(5n) {{ animation-delay: -52s; animation-duration: 172s; }}

      @keyframes digest-rise {{
        0%, 100% {{ transform: translateY(0px); opacity: 0.82; }}
        50%      {{ transform: translateY(-14px); opacity: 1; }}
      }}
      .liquid-rise {{
        animation: digest-rise 211s ease-in-out infinite;
        transform-box: fill-box;
        transform-origin: center;
      }}

      @keyframes glass-settle {{
        0%, 100% {{ opacity: 0.045; }}
        50%      {{ opacity: 0.09; }}
      }}
      .glass-outline {{ animation: glass-settle 71s ease-in-out infinite; }}
    </style>
  </defs>

  <rect width="{CANVAS_W}" height="{CANVAS_H}" fill="{INK}"/>

  <!-- vapor de la metabolizacion: casi nada, sobre la boca del vaso interior -->
  <g>
    {steam}
  </g>

  <!-- el liquido: filas de glifos que deletrean el nombre del repo,
       clipeadas al vaso exterior y desplazadas por una respiracion lentisima -->
  <g clip-path="url(#cupOuter)">
    <g class="liquid-rise">
      <line x1="{waterline_x1 - 4:.1f}" y1="{FILL_Y - 4}" x2="{waterline_x2 + 4:.1f}" y2="{FILL_Y - 4}"
            stroke="{PAPER}" stroke-width="0.6" stroke-dasharray="2 6" opacity="0.05"/>
      {liquid_rows}
    </g>
  </g>

  <!-- textura de vidrio en la cabecera vacia (arriba del liquido) -->
  <g>
    {ribs}
  </g>

  <!-- el vaso doble: contorno del exterior + el interior que asoma sobre el borde -->
  <g class="glass-outline" fill="none" stroke="{PAPER}" stroke-width="1" stroke-dasharray="6 4" opacity="0.06">
    <path d="{OUTER_PATH}">
      <animate attributeName="stroke-dashoffset" from="0" to="-40" dur="220s" repeatCount="indefinite"/>
    </path>
    <path d="{INNER_PATH}">
      <animate attributeName="stroke-dashoffset" from="0" to="30" dur="260s" repeatCount="indefinite"/>
    </path>
  </g>
  <g fill="none" stroke="{SUPPORT}" stroke-width="0.6" opacity="0.04">
    <path d="{OUTER_PATH}"/>
  </g>

  <!-- condensacion: gotas sobre el vidrio exterior, oleadas desincronizadas -->
  <g>
    {drops}
  </g>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera projects/tapiz/vaso_animado.svg (double cup metabolizando, umbral de percepcion)."
    )
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "vaso_animado.svg"),
        help="Ruta de salida (default: projects/tapiz/vaso_animado.svg)",
    )
    args = parser.parse_args()

    svg = build_svg()
    with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    print(f"vaso_animado: escrito {args.output} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
