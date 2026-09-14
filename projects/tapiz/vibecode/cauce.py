"""
Modo cauce del telar: el patron se deriva de los tokens, no se impone.

A diferencia de los modos loom (gramatica impuesta por posicion), cauce
reconoce la recurrencia del texto fuente y la vuelve hilo: cada token con
el mismo texto lleva el mismo color en toda la pieza. El espacio en blanco
deja de ser fondo: los corredores verticales de vacio se leen como rios
(el cauce) detras del tejido.

Tres capas:

1. RECONOCIMIENTO: mapa de frecuencia del texto normalizado de cada token.
   Clases: structural (>= 8 apariciones), recurrent (3-7), rare (2),
   hapax (1). Cada clase es una banda de tono; el hash estable del token
   elige el tono exacto dentro de la banda. Mismo token = mismo hilo.

2. RIOS: corridas verticales de espacio/vacio de largo >= 3 se dibujan
   como trazos redondeados, muy tenues, DETRAS del tejido de tokens.

3. MARCAS (puente tilde): todo caracter fuera de [a-zA-Z0-9_ ] --
   diacriticos, enie, puntuacion -- es canal de marcas: lo mas brillante
   de la pieza y, en la version animada, NUNCA decae. Las marcas son la
   carga cultural de baja entropia que sobrevive el canal con perdida.

Animacion (SMIL, solo con animate=True): onda de formacion por orden de
escritura, digestion tardia de hapax/rare, respiracion de tono en
structural/recurrent, pulso suave en marcas. Sin animate, la pieza es el
estado final ya digerido (hapax apagado, marcas brillantes).
"""

from __future__ import annotations

import hashlib
import html
import re
from typing import Dict, List, Optional, Tuple

from .ansi import RESET, fg256, tokenize
from .loom import canvas_size

CAUCE_MODE = "cauce"

# Cita curatorial de la pieza (misma regla que MOTIF_CITATIONS del loom):
# el <desc> del SVG y el header de terminal la citan literal.
CAUCE_CITATION = (
    "cauce: los rios entre espacios; la recurrencia se reconoce, "
    "no se impone; las marcas sobreviven la digestion (puente tilde)"
)

# Clases de frecuencia, de mas tejida a mas fugaz.
CAUCE_CLASSES: Tuple[str, ...] = ("structural", "recurrent", "rare", "hapax")

# Umbrales de clase por cantidad de apariciones del texto normalizado.
STRUCTURAL_MIN = 8
RECURRENT_MIN = 3
RARE_MIN = 2

# Bandas de color por clase: (hue_min, hue_max, sat, light) en HSL.
# structural: verdes profundos del telar alrededor de #3f6b54.
# recurrent: verdes medios hacia #b7ffd9.
# rare: mas calido y brillante.
# hapax: brasa apagada hacia #c2410f desaturado.
_BANDS: Dict[str, Tuple[float, float, float, float]] = {
    "structural": (140.0, 162.0, 0.28, 0.35),
    "recurrent": (140.0, 166.0, 0.58, 0.58),
    "rare": (36.0, 70.0, 0.66, 0.62),
    "hapax": (12.0, 28.0, 0.38, 0.44),
}

# Tonos discretos por banda: acota la cantidad de grupos (clase, tono) y
# por lo tanto la cantidad de <animate> de la pieza.
HUE_STEPS = 6

# Canal de marcas: lo mas brillante de la pieza, cerca del verde luz.
MARKS_HEX = "#b7ffd9"

# Rios: trazo tenue detras del tejido.
RIVER_HEX = "#b7ffd9"
RIVER_OPACITY = 0.10
RIVER_MIN_RUN = 3

# Estado estatico post-digestion (sin animacion): hapax apagado,
# rare a media luz, el resto entero.
STATIC_OPACITY = {
    "structural": 1.0,
    "recurrent": 1.0,
    "rare": 0.6,
    "hapax": 0.3,
    "marks": 1.0,
}

# Ciclo de la onda de formacion/digestion.
CYCLE_S = 12.0

# Tope de <animate> por token individual; por encima, la onda de
# formacion se anima a nivel de grupo (clase, tono) para que la pieza
# siga siendo liviana.
MAX_TOKEN_ANIMATES = 400

# Curvas de opacidad por clase para el ciclo animado: formacion temprana,
# digestion tardia. hapax decae casi a nada; rare decae menos;
# structural/recurrent no decaen (respiran por tono, no por opacidad).
_OPACITY_CURVES: Dict[str, Tuple[str, str]] = {
    "hapax": ("0;1;1;0.12;0.12", "0;0.08;0.55;0.8;1"),
    "rare": ("0;1;1;0.45;0.45", "0;0.08;0.6;0.85;1"),
    "recurrent": ("0;1;1", "0;0.08;1"),
    "structural": ("0;1;1", "0;0.08;1"),
}

# Geometria por defecto: identica a svg_export (celda monospace 16px).
_CHAR_W = 9.6
_LINE_H = 20.0
_MARGIN_X = 24.0
_BASELINE_Y = 40.0
_INK_HEX = "#1f2a24"

_IDENT_RUN = re.compile(r"[A-Za-z0-9_]+")


# ---------------------------------------------------------------------------
# Capa 1: reconocimiento
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    """Texto normalizado para frecuencia y hash: mismo hilo, mismo color."""
    return text.casefold()


def _stable_hash(text: str) -> int:
    """Hash deterministico entre procesos (hash() de Python esta salteado)."""
    digest = hashlib.md5(_normalize(text).encode("utf-8")).hexdigest()
    return int(digest, 16)


def subtokens(part: str) -> List[Tuple[str, str]]:
    """
    Divide un token de palabra en corridas ('ident' | 'mark', texto).

    'ident' son corridas de [A-Za-z0-9_]; todo lo demas (diacriticos,
    enie, puntuacion) es 'mark' y pertenece al canal de marcas.
    """
    out: List[Tuple[str, str]] = []
    pos = 0
    for m in _IDENT_RUN.finditer(part):
        if m.start() > pos:
            out.append(("mark", part[pos:m.start()]))
        out.append(("ident", m.group()))
        pos = m.end()
    if pos < len(part):
        out.append(("mark", part[pos:]))
    return out


def token_frequencies(text: str) -> Dict[str, int]:
    """Mapa de frecuencia del texto normalizado de cada subtoken."""
    freq: Dict[str, int] = {}
    for line in text.splitlines():
        for kind, part in tokenize(line):
            if kind != "word":
                continue
            for _, sub in subtokens(part):
                key = _normalize(sub)
                freq[key] = freq.get(key, 0) + 1
    return freq


def freq_class(count: int) -> str:
    """Clase de frecuencia de un token segun sus apariciones."""
    if count >= STRUCTURAL_MIN:
        return "structural"
    if count >= RECURRENT_MIN:
        return "recurrent"
    if count >= RARE_MIN:
        return "rare"
    return "hapax"


def _hsl_to_hex(h: float, s: float, light: float) -> str:
    """HSL (h en grados, s/l en 0..1) a hex #rrggbb."""
    h = (h % 360.0) / 360.0
    if s == 0:
        r = g = b = light
    else:
        q = light * (1 + s) if light < 0.5 else light + s - light * s
        p = 2 * light - q

        def channel(t: float) -> float:
            t = t % 1.0
            if t < 1 / 6:
                return p + (q - p) * 6 * t
            if t < 1 / 2:
                return q
            if t < 2 / 3:
                return p + (q - p) * (2 / 3 - t) * 6
            return p

        r = channel(h + 1 / 3)
        g = channel(h)
        b = channel(h - 1 / 3)
    return "#{:02x}{:02x}{:02x}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )


def band_hues(cls: str) -> List[str]:
    """Los HUE_STEPS tonos hex discretos de la banda de una clase."""
    h_min, h_max, sat, light = _BANDS[cls]
    step = (h_max - h_min) / max(HUE_STEPS - 1, 1)
    return [_hsl_to_hex(h_min + i * step, sat, light) for i in range(HUE_STEPS)]


def token_color(text: str, cls: str) -> str:
    """
    Color hex de un token: la clase da la banda, el hash estable del texto
    elige el tono. INVARIANTE: mismo texto -> mismo color en toda la pieza.
    """
    if cls == "marks":
        return MARKS_HEX
    hues = band_hues(cls)
    return hues[_stable_hash(text) % len(hues)]


# ---------------------------------------------------------------------------
# Capa 2: rios
# ---------------------------------------------------------------------------
def river_runs(lines: List[str], min_run: int = RIVER_MIN_RUN) -> List[Tuple[int, int, int]]:
    """
    Corridas verticales de espacio/vacio: (col, fila_inicio, fila_fin).

    Una celda es cauce si es un espacio real de la linea, o si la linea
    entera esta en blanco (el rio cruza las lineas vacias). Solo corridas
    de largo >= min_run se vuelven rio.
    """
    n_cols, n_rows = canvas_size(lines)
    blank = [not line.strip() for line in lines]

    def eligible(col: int, row: int) -> bool:
        line = lines[row]
        if col < len(line):
            return line[col].isspace()
        return blank[row]

    runs: List[Tuple[int, int, int]] = []
    for col in range(n_cols):
        row = 0
        while row < n_rows:
            if eligible(col, row):
                start = row
                while row < n_rows and eligible(col, row):
                    row += 1
                if row - start >= min_run:
                    runs.append((col, start, row - 1))
            else:
                row += 1
    return runs


def river_cells(lines: List[str], min_run: int = RIVER_MIN_RUN) -> set:
    """Set de celdas (col, fila) que pertenecen a algun rio."""
    cells = set()
    for col, r0, r1 in river_runs(lines, min_run):
        for row in range(r0, r1 + 1):
            cells.add((col, row))
    return cells


# ---------------------------------------------------------------------------
# Recoleccion de tokens con posicion y orden de escritura
# ---------------------------------------------------------------------------
def _collect_tokens(lines: List[str], freq: Dict[str, int]):
    """
    Lista de (indice_escritura, fila, col, texto, clase) para cada subtoken.
    La clase de las marcas es 'marks' sin importar su frecuencia.
    """
    tokens = []
    idx = 0
    for y, line in enumerate(lines):
        x = 0
        for kind, part in tokenize(line):
            if kind == "word":
                for channel, sub in subtokens(part):
                    if channel == "mark":
                        cls = "marks"
                    else:
                        cls = freq_class(freq[_normalize(sub)])
                    tokens.append((idx, y, x, sub, cls))
                    idx += 1
                    x += len(sub)
            else:
                x += len(part)
    return tokens


# ---------------------------------------------------------------------------
# Export SVG
# ---------------------------------------------------------------------------
def render_svg_cauce(
    text: str,
    animate: bool = False,
    title: str = "tapiz",
    background: str = _INK_HEX,
    char_w: float = _CHAR_W,
    line_h: float = _LINE_H,
) -> str:
    """
    Pieza SVG del modo cauce. Con animate=True agrega SMIL (onda de
    formacion, digestion, respiracion de tono, pulso de marcas); sin
    animate, el estado final digerido.
    """
    lines = text.splitlines() or [""]
    n_cols, n_rows = canvas_size(lines)
    width = int(n_cols * char_w + 48)
    height = int(len(lines) * line_h + 48)

    freq = token_frequencies(text)
    tokens = _collect_tokens(lines, freq)
    total = max(len(tokens), 1)

    # Rios detras del tejido: un path redondeado por corrida.
    river_parts: List[str] = []
    for col, r0, r1 in river_runs(lines):
        rx = _MARGIN_X + (col + 0.5) * char_w
        y0 = _BASELINE_Y + r0 * line_h - line_h * 0.6
        y1 = _BASELINE_Y + r1 * line_h + line_h * 0.1
        river_parts.append(
            f'<path class="cauce-river" d="M{rx:.1f} {y0:.1f}L{rx:.1f} {y1:.1f}"/>'
        )
    rivers = ""
    if river_parts:
        rivers = (
            f'  <g stroke="{RIVER_HEX}" stroke-opacity="{RIVER_OPACITY}" '
            f'stroke-width="{char_w * 1.25:.1f}" stroke-linecap="round" '
            f'fill="none">\n    ' + "\n    ".join(river_parts) + "\n  </g>\n"
        )

    # Tejido: tokens agrupados por (clase, color) para compartir fill y
    # acotar la cantidad de <animate>.
    groups: Dict[Tuple[str, str], List[Tuple[int, int, int, str]]] = {}
    for idx, y, x, sub, cls in tokens:
        color = token_color(sub, cls)
        groups.setdefault((cls, color), []).append((idx, y, x, sub))

    per_token_anim = animate and len(tokens) <= MAX_TOKEN_ANIMATES

    group_parts: List[str] = []
    for (cls, color) in sorted(groups.keys()):
        members = groups[(cls, color)]
        attrs = f' class="cauce-{cls}" fill="{color}"'
        group_animates: List[str] = []
        if not animate:
            opacity = STATIC_OPACITY[cls]
            if opacity < 1.0:
                attrs += f' opacity="{opacity}"'
        elif cls == "marks":
            # Canal de marcas: NUNCA decae; a lo sumo un pulso suave.
            group_animates.append(
                '<animate attributeName="opacity" values="1;0.85;1" '
                'dur="10s" repeatCount="indefinite"/>'
            )
        else:
            values, key_times = _OPACITY_CURVES[cls]
            if not per_token_anim:
                # Pieza grande: la onda de formacion/digestion se anima por
                # grupo, desfasada por el primer token del grupo.
                begin = -(members[0][0] / total) * CYCLE_S
                group_animates.append(
                    f'<animate attributeName="opacity" values="{values}" '
                    f'keyTimes="{key_times}" dur="{CYCLE_S:.0f}s" '
                    f'begin="{begin:.2f}s" repeatCount="indefinite"/>'
                )
            if cls in ("recurrent", "structural"):
                # Respiracion: deriva lenta entre 3 tonos de la banda,
                # desfasada por hash para que el campo titile sin parpadear.
                hues = band_hues(cls)
                i = hues.index(color) if color in hues else 0
                c1 = hues[(i + 1) % len(hues)]
                c2 = hues[(i - 1) % len(hues)]
                seed = _stable_hash(cls + color)
                dur = 8 + (seed % 9)  # 8..16s
                offset = seed % dur
                group_animates.append(
                    f'<animate attributeName="fill" '
                    f'values="{color};{c1};{c2};{color}" dur="{dur}s" '
                    f'begin="-{offset}s" repeatCount="indefinite"/>'
                )

        texts: List[str] = []
        for idx, y, x, sub in members:
            tx = _MARGIN_X + x * char_w
            ty = _BASELINE_Y + y * line_h
            anim = ""
            if per_token_anim and cls != "marks":
                values, key_times = _OPACITY_CURVES[cls]
                begin = -(idx / total) * CYCLE_S
                anim = (
                    f'<animate attributeName="opacity" values="{values}" '
                    f'keyTimes="{key_times}" dur="{CYCLE_S:.0f}s" '
                    f'begin="{begin:.2f}s" repeatCount="indefinite"/>'
                )
            texts.append(
                f'<text x="{tx:.1f}" y="{ty:.1f}" xml:space="preserve">'
                f"{html.escape(sub)}{anim}</text>"
            )
        group_parts.append(
            f"<g{attrs}>\n      "
            + "\n      ".join(texts + group_animates)
            + "\n    </g>"
        )

    weave = "\n    ".join(group_parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f"  <title>{html.escape(title)}</title>\n"
        f"  <desc>{html.escape(CAUCE_CITATION)}</desc>\n"
        f'  <rect width="{width}" height="{height}" fill="{background}"/>\n'
        f"{rivers}"
        f'  <g font-family="monospace" font-size="16">\n'
        f"    {weave}\n"
        f"  </g>\n"
        f"</svg>\n"
    )


# ---------------------------------------------------------------------------
# Render de terminal (estatico)
# ---------------------------------------------------------------------------
# Aproximaciones ANSI-256 de las bandas hex (mismo orden de tonos).
_ANSI_BANDS: Dict[str, Tuple[int, ...]] = {
    "structural": (22, 23, 29, 65, 66, 72),
    "recurrent": (29, 35, 36, 42, 78, 79),
    "rare": (94, 130, 136, 172, 178, 214),
    "hapax": (52, 88, 95, 130, 131, 137),
}
_ANSI_MARKS = 158   # cerca de #b7ffd9: brillante
_ANSI_RIVER = 22    # verde apagado para las barras del cauce
_RIVER_GLYPH = "│"  # barra vertical fina


def token_ansi_color(text: str, cls: str) -> str:
    """Color ANSI del token: misma regla que token_color, en 256 colores."""
    if cls == "marks":
        return fg256(_ANSI_MARKS)
    band = _ANSI_BANDS[cls]
    return fg256(band[_stable_hash(text) % len(band)])


def render_ansi_cauce(text: str) -> str:
    """
    Render estatico de terminal del modo cauce: colores de reconocimiento
    en los tokens, rios como barras verticales tenues, marcas brillantes.
    """
    lines = text.splitlines()
    freq = token_frequencies(text)
    rivers = river_cells(lines)

    out_lines: List[str] = []
    for y, line in enumerate(lines):
        rendered: List[str] = []
        x = 0
        for kind, part in tokenize(line):
            if kind == "space":
                cells: List[str] = []
                for i, ch in enumerate(part):
                    if (x + i, y) in rivers:
                        cells.append(f"{fg256(_ANSI_RIVER)}{_RIVER_GLYPH}{RESET}")
                    else:
                        cells.append(" " if ch.isspace() else ch)
                rendered.append("".join(cells))
                x += len(part)
            else:
                for channel, sub in subtokens(part):
                    cls = "marks" if channel == "mark" else freq_class(
                        freq[_normalize(sub)]
                    )
                    rendered.append(f"{token_ansi_color(sub, cls)}{sub}{RESET}")
                    x += len(sub)
        out_lines.append("".join(rendered))
    return "\n".join(out_lines)
