"""
Exportador SVG del telar: convierte el render de espacios en una pieza SVG
autocontenida (imprimible, proyectable, o animada con SMIL).

El terminal usa aproximaciones ANSI-256; aqui se usa la paleta flujo REAL
(projects/flujo/flujo.json). Sin dependencias externas: SVG a mano.
"""

from __future__ import annotations

import html
from typing import List, Optional

from .ansi import tokenize
from .cauce import CAUCE_MODE, render_svg_cauce
from .loom import LOOM_MODES, MOTIF_CITATIONS, block_segments, canvas_size
from .void_shapes import VOID_SHAPE_MODES, render_svg_void_shapes

# Paleta flujo real (hex de projects/flujo/flujo.json). El orden replica la
# intencion de la paleta ANSI "flujo" de spaces.py: tinta -> acento -> soporte
# -> alerta -> papel, para que -m void/length elijan colores coherentes.
FLUJO_HEX = {
    "ink": "#1f2a24",
    "accent": "#2d5a4a",
    "support": "#675f55",
    "alert": "#c2410f",
    "paper": "#f8f1e3",
}
SPACE_COLORS: List[str] = [
    FLUJO_HEX["accent"],
    FLUJO_HEX["support"],
    FLUJO_HEX["alert"],
    FLUJO_HEX["accent"],
    FLUJO_HEX["support"],
]
GHOST_COLOR = "#4a554e"   # texto fantasma: gris verdoso tenue sobre ink
LOOM_VOID_HEX = "#28332c"  # vacio compositivo loom: apenas sobre el ink, umbral

CHAR_W = 9.6   # ancho de celda para font-size 16 monospace
LINE_H = 20


def _space_color(length: int, mode: str) -> str:
    if mode == "length":
        idx = min(length, len(SPACE_COLORS)) - 1
    else:  # void / blocks
        idx = length % len(SPACE_COLORS)
    return SPACE_COLORS[idx]


def render_svg(
    text: str,
    mode: str = "void",
    fill_char: str = "·",
    ghost: bool = True,
    animate: bool = False,
    background: str = FLUJO_HEX["ink"],
    title: str = "tapiz",
) -> str:
    """
    Renderiza el texto como pieza SVG: espacios coloreados con la paleta flujo,
    texto en gris fantasma (o ausente con ghost=False). Con animate=True cada
    fila respira en cascada (SMIL, lento, estetica de umbral).

    Modos loom (field/border/medallion/mihrab): el color depende de la
    posicion de la celda en el canvas (composicion de alfombra, ver loom.py);
    la pieza incrusta un <desc> con la cita curatorial del motivo.

    Modo cauce: el patron se deriva de la recurrencia de los tokens y los
    rios de espacios (ver cauce.py); con animate=True la pieza lleva SMIL
    (formacion, digestion, respiracion; las marcas nunca decaen).

    Morfologias del vacio animado (espaciado, zigzag_vertical, raices; ver
    void_shapes.py, direccion del artista 2026-07-12): con animate=True la
    pieza lleva SMIL (respiracion de huecos, hilo de color, crecimiento de
    raiz); sin animate, un frame estatico representativo.
    """
    if mode == CAUCE_MODE:
        return render_svg_cauce(
            text,
            animate=animate,
            title=title,
            background=background,
            char_w=CHAR_W,
            line_h=LINE_H,
        )
    if mode in VOID_SHAPE_MODES:
        return render_svg_void_shapes(
            text,
            mode,
            animate=animate,
            title=title,
            background=background,
            char_w=CHAR_W,
            line_h=LINE_H,
            fill_char=fill_char,
        )
    lines = text.splitlines() or [""]
    is_loom = mode in LOOM_MODES
    n_cols, n_rows = canvas_size(lines)
    width = int(n_cols * CHAR_W + 48)
    height = int(len(lines) * LINE_H + 48)

    rows: List[str] = []
    for y, line in enumerate(lines):
        spans: List[str] = []
        x = 0
        for kind, part in tokenize(line):
            if kind == "space":
                if is_loom:
                    for seg_len, idx in block_segments(
                        mode, x, y, len(part), n_cols, n_rows, len(SPACE_COLORS)
                    ):
                        color = LOOM_VOID_HEX if idx is None else SPACE_COLORS[idx]
                        spans.append(
                            f'<tspan fill="{color}">'
                            f"{html.escape(fill_char * seg_len)}</tspan>"
                        )
                else:
                    color = _space_color(len(part), mode)
                    spans.append(
                        f'<tspan fill="{color}">{html.escape(fill_char * len(part))}</tspan>'
                    )
            elif ghost:
                spans.append(f'<tspan fill="{GHOST_COLOR}">{html.escape(part)}</tspan>')
            else:
                # sin ghost: la palabra ocupa su lugar pero no se ve (espacio en negativo)
                spans.append(f'<tspan fill="{background}">{html.escape(part)}</tspan>')
            x += len(part)
        anim = ""
        if animate:
            # cascada de digestion: cada fila respira desfasada, ciclo largo
            begin = -(y * 7)
            anim = (
                f'<animate attributeName="opacity" values="1;0.35;1" dur="90s" '
                f'begin="{begin}s" repeatCount="indefinite"/>'
            )
        rows.append(
            f'<text x="24" y="{40 + y * LINE_H}" xml:space="preserve">'
            f"{''.join(spans)}{anim}</text>"
        )

    body = "\n  ".join(rows)
    desc = ""
    if is_loom:
        # Regla curatorial (projects/cultura/dossiers/tapiz.md): toda pieza
        # que usa un motivo cita su significado real. El <desc> es la ficha.
        desc = f"  <desc>{html.escape(MOTIF_CITATIONS[mode])}</desc>\n"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f"  <title>{html.escape(title)}</title>\n"
        f"{desc}"
        f'  <rect width="{width}" height="{height}" fill="{background}"/>\n'
        f'  <g font-family="monospace" font-size="16">\n  {body}\n  </g>\n'
        f"</svg>\n"
    )


def export_svg(
    text: str,
    path: str,
    mode: str = "void",
    fill_char: str = "·",
    ghost: bool = True,
    animate: bool = False,
    title: Optional[str] = None,
) -> str:
    """Escribe la pieza SVG a disco y devuelve la ruta."""
    svg = render_svg(
        text,
        mode=mode,
        fill_char=fill_char,
        ghost=ghost,
        animate=animate,
        title=title or "tapiz",
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path
