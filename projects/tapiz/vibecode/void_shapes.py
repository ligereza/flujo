"""
Tres morfologias del vacio ANIMADO (direccion del artista, 2026-07-12): a
diferencia de los modos loom/cauce (posicion pura, deterministicos), estas
tres dependen tambien del tiempo `t` -- el vacio se mueve, el texto se queda
fantasma. Modulo separado (no se infla render_frame) para que spaces.py y
svg_export.py importen solo lo que necesitan.

  - espaciado:       el hueco entre caracteres respira -- abre y cierra; el
                      hueco mismo es la figura que se mueve.
  - zigzag_vertical: hilos en zigzag verticales tejen el vacio negativo
                      hacia abajo (adapta motifs/zigzag.py -- ahi el chevron
                      es diagonal (x+y); aca es vertical, funcion de y); el
                      color fluye por el hilo fijo (misma tecnica que "drift").
  - raices:          formas rectangulares -- raiz de circuito impreso, en
                      angulo recto, no organica -- crecen y se ramifican
                      hacia abajo por el vacio (crecimiento revelado por t).

Terminal (ANSI, spaces.py) y SVG/SMIL (svg_export.py, GitHub-safe, sin JS)
comparten la misma geometria; SVG anima con <animate> igual que cauce.py
(grupos con offsets de fase), terminal recalcula color/segmentos por frame.
"""

from __future__ import annotations

import html
import math
import random
from typing import Dict, List, Optional, Tuple

from .ansi import tokenize
from .cauce import river_runs
from .loom import canvas_size

VOID_SHAPE_MODES: Tuple[str, ...] = ("espaciado", "zigzag_vertical", "raices")

# Cita curatorial de cada morfologia (misma regla que MOTIF_CITATIONS del
# loom y CAUCE_CITATION: toda pieza que usa un patron cita su sentido real).
VOID_SHAPE_CITATIONS: Dict[str, str] = {
    "espaciado": (
        "espaciado: el hueco entre caracteres respira -- abre y cierra; "
        "el vacio mismo es la figura que se mueve (direccion tapiz 2026-07-12)"
    ),
    "zigzag_vertical": (
        "zigzag_vertical: hilos en zigzag tejen el vacio hacia abajo; el "
        "color fluye por el hilo fijo, no el hilo (direccion tapiz 2026-07-12)"
    ),
    "raices": (
        "raices: formas rectangulares -- raiz de circuito, angulo recto, "
        "no organica -- crecen y se ramifican hacia abajo (direccion tapiz 2026-07-12)"
    ),
}

# Paleta hex local (misma fuente que svg_export.FLUJO_HEX / projects/flujo/
# flujo.json). Duplicada a proposito: mismo patron que cauce.py, que no
# importa de svg_export para no crear un ciclo entre los dos exportadores.
_HEX_ACCENT = "#2d5a4a"
_HEX_SUPPORT = "#675f55"
_HEX_ALERT = "#c2410f"
_HEX_PAPER = "#f8f1e3"
_HEX_INK = "#1f2a24"
_GHOST_HEX = "#4a554e"
_VOID_SVG_PALETTE: List[str] = [_HEX_ACCENT, _HEX_SUPPORT, _HEX_ALERT, _HEX_PAPER]

_CHAR_W = 9.6
_LINE_H = 20.0
_MARGIN_X = 24.0
_BASELINE_Y = 40.0


def _segments_from_index_fn(length: int, index_fn) -> List[Tuple[int, Optional[int]]]:
    """Agrupa `length` celdas consecutivas en corridas del mismo indice
    (o None); index_fn(i) recibe el offset 0..length-1 dentro del bloque."""
    segments: List[Tuple[int, Optional[int]]] = []
    for i in range(length):
        idx = index_fn(i)
        if segments and segments[-1][1] == idx:
            segments[-1] = (segments[-1][0] + 1, idx)
        else:
            segments.append((1, idx))
    return segments


# ---------------------------------------------------------------------------
# espaciado: el hueco respira
# ---------------------------------------------------------------------------
def espaciado_frame(x: int, y: int, t: int, length: int, speed: float = 0.12) -> Tuple[int, float]:
    """
    Ancho efectivo (caracteres) y "apertura" (0..1) de un bloque de espacios
    de largo original `length`, en el frame `t`. Oscila entre ~0.2x y ~1.8x
    del ancho original; la fase depende de la posicion para que el respiro
    no sea uniforme en toda la pieza (algunos huecos abren mientras otros
    cierran, como una respiracion colectiva desincronizada).
    """
    phase = x * 0.35 + y * 0.9 + t * speed * 10
    intensity = (math.sin(phase) + 1) * 0.5  # 0..1
    factor = 0.2 + 1.6 * intensity
    width = max(0, round(length * factor))
    return width, intensity


# ---------------------------------------------------------------------------
# zigzag_vertical: hilos que tejen el vacio hacia abajo
# ---------------------------------------------------------------------------
_ZIGZAG_PERIOD = 10
_ZIGZAG_AMPLITUDE = 3
_ZIGZAG_SPACING = 14


def _thread_offset(y: int, phase_shift: int, period: int, amplitude: int) -> float:
    """Onda triangular en x: -amplitude..+amplitude segun la fila y."""
    m = (y + phase_shift) % (2 * period)
    tri = m if m <= period else 2 * period - m  # 0..period
    return (tri / period) * (2 * amplitude) - amplitude


def zigzag_thread_at(
    x: int,
    y: int,
    n_cols: int,
    period: int = _ZIGZAG_PERIOD,
    amplitude: int = _ZIGZAG_AMPLITUDE,
    spacing: int = _ZIGZAG_SPACING,
) -> Optional[int]:
    """
    Indice de hilo (0..num_threads-1) si la celda (x, y) cae sobre un hilo
    en zigzag vertical, o None si cae en el vacio entre hilos. Puramente
    posicional y deterministico -- la FORMA no depende de t, solo el color
    que corre sobre ella (ver zigzag_vertical_frame_segments).
    """
    n_cols = max(n_cols, 1)
    num_threads = max(1, n_cols // spacing)
    for i in range(num_threads):
        base = (i + 0.5) * n_cols / num_threads
        target = base + _thread_offset(y, i * 3, period, amplitude)
        if abs(x - target) < 0.75:
            return i
    return None


def zigzag_vertical_color_bucket(y: int, thread_index: int, n_colors: int) -> int:
    """Bucket de color estructural de un hilo (sin tiempo)."""
    return (y + thread_index * 2) % max(n_colors, 1)


def zigzag_vertical_frame_segments(
    x0: int, y: int, length: int, t: int, n_cols: int, n_colors: int
) -> List[Tuple[int, Optional[int]]]:
    """Segmentos (largo, indice_o_None) de un bloque de espacios: el color
    del hilo fluye hacia abajo con `t` (misma tecnica que el modo drift,
    aplicada solo sobre las celdas que caen en un hilo)."""

    def index_fn(i: int) -> Optional[int]:
        thread = zigzag_thread_at(x0 + i, y, n_cols)
        if thread is None:
            return None
        return (zigzag_vertical_color_bucket(y, thread, n_colors) - t) % max(n_colors, 1)

    return _segments_from_index_fn(length, index_fn)


# ---------------------------------------------------------------------------
# raices: circuito rectangular que crece y ramifica hacia abajo
# ---------------------------------------------------------------------------
# Cache keyed por el texto EXACTO (no por tamano de canvas): el tronco se
# ancla en los rios reales de espacio (cauce.river_runs), asi que depende
# del contenido, no solo de las dimensiones.
_ROOT_CACHE: Dict[str, Tuple[Dict[Tuple[int, int], Tuple[int, int]], int]] = {}
_ROOT_MAX_TRUNKS = 10
_ROOT_MIN_TRUNK_SPACING = 3
_ROOT_MIN_RIVER = 3


def generate_roots(text: str, seed: int = 1337) -> Tuple[Dict[Tuple[int, int], Tuple[int, int]], int]:
    """
    Raices rectangulares (angulo recto -- raiz de circuito, no organica)
    ancladas en los rios reales de espacio del texto (ver cauce.river_runs):
    el tronco crece exactamente por una corrida vertical de espacio real,
    asi que SIEMPRE atraviesa vacio real del archivo -- no una grilla
    arbitraria que podria caer entera sobre codigo y quedar invisible. Las
    ramas horizontales a los pies del tronco pueden o no caer en espacio
    real; la mascara la aplica el llamador (misma regla que loom/cauce: solo
    se recolorean caracteres que ya son espacio en la fuente).

    Devuelve {(x, y): (orden_de_nacimiento, profundidad)} y el total de
    celdas (define el ciclo de crecimiento). Cacheado por texto exacto:
    corre una vez por pieza, no por frame ni por caracter.
    """
    cached = _ROOT_CACHE.get(text)
    if cached is not None:
        return cached

    lines = text.splitlines() or [""]
    n_cols, n_rows = canvas_size(lines)
    rng = random.Random(seed ^ (len(text) * 1_000_003 + n_rows))

    # Rios mas largos primero; se descartan los que caen pegados a un
    # tronco ya elegido (evita una pared de troncos identicos cuando la
    # sangria repite la misma columna muchas filas seguidas).
    rivers = sorted(river_runs(lines, min_run=_ROOT_MIN_RIVER), key=lambda r: r[2] - r[1], reverse=True)
    trunks: List[Tuple[int, int, int]] = []
    used_cols: List[int] = []
    for col, r0, r1 in rivers:
        if any(abs(col - c) < _ROOT_MIN_TRUNK_SPACING for c in used_cols):
            continue
        trunks.append((col, r0, r1))
        used_cols.append(col)
        if len(trunks) >= _ROOT_MAX_TRUNKS:
            break

    if not trunks:
        # Sin rios (texto muy compacto o de una sola linea): red minima de
        # respaldo para que la morfologia nunca quede completamente vacia.
        fallback_cols = sorted({0, n_cols // 2, max(n_cols - 1, 0)})
        trunks = [(c, 0, n_rows - 1) for c in fallback_cols]

    cells: Dict[Tuple[int, int], Tuple[int, int]] = {}
    order = 0
    for col, r0, r1 in trunks:
        for y in range(r0, r1 + 1):
            if (col, y) not in cells:
                cells[(col, y)] = (order, 0)
                order += 1
        # 1-2 ramas rectangulares a los pies del tronco.
        n_branches = rng.randint(1, 2)
        for depth, by in enumerate((r1 + 1 + k for k in range(n_branches)), start=1):
            if by >= n_rows:
                continue
            branch_len = rng.randint(2, 6)
            direction = rng.choice((-1, 1))
            bx = col
            for _ in range(branch_len):
                nbx = bx + direction
                if not (0 <= nbx < n_cols) or (nbx, by) in cells:
                    break
                cells[(nbx, by)] = (order, depth)
                order += 1
                bx = nbx

    total = max(order, 1)
    result = (cells, total)
    _ROOT_CACHE[text] = result
    return result


def raices_frame_index(
    x: int,
    y: int,
    t: int,
    cells: Dict[Tuple[int, int], Tuple[int, int]],
    total: int,
    n_colors: int,
    cycle_pause: int = 20,
) -> Optional[int]:
    """Indice animado de terminal: la raiz crece con `t` (revela celdas por
    orden de nacimiento), se sostiene, y vuelve a crecer en loop. La punta
    en crecimiento brilla (ultimo color de paleta); lo ya asentado toma el
    color de su profundidad de rama."""
    info = cells.get((x, y))
    if info is None:
        return None
    birth, depth = info
    cycle = total + cycle_pause
    progress = t % cycle
    if birth > progress:
        return None  # todavia no crecio hasta aca en este ciclo
    age = progress - birth
    if age < 4:
        return max(n_colors - 1, 0)  # punta creciendo: color mas vivo
    return depth % max(n_colors, 1)


def raices_frame_segments(
    x0: int,
    y: int,
    length: int,
    t: int,
    cells: Dict[Tuple[int, int], Tuple[int, int]],
    total: int,
    n_colors: int,
) -> List[Tuple[int, Optional[int]]]:
    """Segmentos (largo, indice_o_None) de un bloque de espacios para el
    modo raices en el frame `t`. `cells`/`total` vienen de generate_roots(text),
    calculado una vez por el llamador (no por caracter)."""

    def index_fn(i: int) -> Optional[int]:
        return raices_frame_index(x0 + i, y, t, cells, total, n_colors)

    return _segments_from_index_fn(length, index_fn)


# ---------------------------------------------------------------------------
# Export SVG (GitHub-safe: SMIL puro, sin JS)
# ---------------------------------------------------------------------------
def _svg_espaciado(
    text: str, animate: bool, title: str, background: str, char_w: float, line_h: float
) -> str:
    lines = text.splitlines() or [""]
    n_cols, n_rows = canvas_size(lines)
    width = int(n_cols * char_w + 48)
    height = int(len(lines) * line_h + 48)
    bar_colors = [_HEX_ACCENT, _HEX_SUPPORT, _HEX_ALERT]

    rects: List[str] = []
    texts: List[str] = []
    for y, line in enumerate(lines):
        x = 0
        ty = _BASELINE_Y + y * line_h
        for kind, part in tokenize(line):
            length = len(part)
            if kind == "space":
                if length > 0:
                    color = bar_colors[length % len(bar_colors)]
                    rx = _MARGIN_X + x * char_w
                    rw = length * char_w
                    ry = ty - line_h * 0.72
                    rh = line_h * 0.8
                    anim = ""
                    if animate:
                        w_min, w_max = rw * 0.18, rw * 1.7
                        cx = rx + rw / 2.0
                        x_min, x_max = cx - w_min / 2.0, cx - w_max / 2.0
                        dur = 5.0 + ((x * 7 + y * 13) % 5)
                        begin = -((x * 0.35 + y * 0.9) % dur)
                        anim = (
                            f'<animate attributeName="width" '
                            f'values="{rw:.1f};{w_max:.1f};{w_min:.1f};{rw:.1f}" '
                            f'dur="{dur:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite"/>'
                            f'<animate attributeName="x" '
                            f'values="{rx:.1f};{x_max:.1f};{x_min:.1f};{rx:.1f}" '
                            f'dur="{dur:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite"/>'
                        )
                    rects.append(
                        f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
                        f'fill="{color}" opacity="0.85">{anim}</rect>'
                    )
            else:
                tx = _MARGIN_X + x * char_w
                texts.append(
                    f'<text x="{tx:.1f}" y="{ty:.1f}" xml:space="preserve" '
                    f'fill="{_GHOST_HEX}">{html.escape(part)}</text>'
                )
            x += length

    citation = VOID_SHAPE_CITATIONS["espaciado"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f"  <title>{html.escape(title)}</title>\n"
        f"  <desc>{html.escape(citation)}</desc>\n"
        f'  <rect width="{width}" height="{height}" fill="{background}"/>\n'
        f'  <g>\n    ' + "\n    ".join(rects) + '\n  </g>\n'
        f'  <g font-family="monospace" font-size="16" opacity="0.55">\n    '
        + "\n    ".join(texts) + '\n  </g>\n'
        f"</svg>\n"
    )


def _svg_zigzag_vertical(
    text: str,
    animate: bool,
    title: str,
    background: str,
    char_w: float,
    line_h: float,
    fill_char: str,
) -> str:
    lines = text.splitlines() or [""]
    n_cols, n_rows = canvas_size(lines)
    n_colors = len(_VOID_SVG_PALETTE)
    width = int(n_cols * char_w + 48)
    height = int(len(lines) * line_h + 48)
    void_hex = "#28332c"

    groups: Dict[Optional[int], List[Tuple[int, int, int]]] = {}
    for y, line in enumerate(lines):
        x = 0
        for kind, part in tokenize(line):
            length = len(part)
            if kind == "space":
                offset = 0
                for seg_len, thread in _segments_from_index_fn(
                    length, lambda i: zigzag_thread_at(x + i, y, n_cols)
                ):
                    bucket = None if thread is None else zigzag_vertical_color_bucket(y, thread, n_colors)
                    groups.setdefault(bucket, []).append((x + offset, y, seg_len))
                    offset += seg_len
            x += length

    group_svgs: List[str] = []
    for bucket in sorted(groups.keys(), key=lambda b: (b is None, b)):
        items = groups[bucket]
        color = void_hex if bucket is None else _VOID_SVG_PALETTE[bucket]
        opacity = 0.16 if bucket is None else 1.0
        texts = [
            f'<text x="{_MARGIN_X + x * char_w:.1f}" y="{_BASELINE_Y + y * line_h:.1f}" '
            f'xml:space="preserve">{html.escape(fill_char * seg_len)}</text>'
            for x, y, seg_len in items
        ]
        anim = ""
        if animate and bucket is not None:
            # El color fluye por el hilo fijo (el hilo no se mueve, el
            # color corre sobre el) -- misma logica de respiracion de cauce.
            seq = _VOID_SVG_PALETTE[bucket:] + _VOID_SVG_PALETTE[:bucket] + [_VOID_SVG_PALETTE[bucket]]
            dur = 6 + (bucket % 4) * 2
            anim = (
                f'<animate attributeName="fill" values="{";".join(seq)}" '
                f'dur="{dur}s" repeatCount="indefinite"/>'
            )
        children = texts + ([anim] if anim else [])
        group_svgs.append(
            f'<g fill="{color}" opacity="{opacity}">\n      ' + "\n      ".join(children) + "\n    </g>"
        )

    body = "\n    ".join(group_svgs)
    citation = VOID_SHAPE_CITATIONS["zigzag_vertical"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f"  <title>{html.escape(title)}</title>\n"
        f"  <desc>{html.escape(citation)}</desc>\n"
        f'  <rect width="{width}" height="{height}" fill="{background}"/>\n'
        f'  <g font-family="monospace" font-size="16">\n    {body}\n  </g>\n'
        f"</svg>\n"
    )


def _svg_raices(
    text: str,
    animate: bool,
    title: str,
    background: str,
    char_w: float,
    line_h: float,
    fill_char: str,
) -> str:
    lines = text.splitlines() or [""]
    n_colors = len(_VOID_SVG_PALETTE)
    n_cols_geom, _ = canvas_size(lines)
    width = int(n_cols_geom * char_w + 48)
    height = int(len(lines) * line_h + 48)
    cycle_s = 14.0
    n_buckets = 24

    cells, total = generate_roots(text)
    items: List[Tuple[int, int, int, int]] = []  # x, y, birth, depth
    for y, line in enumerate(lines):
        x = 0
        for kind, part in tokenize(line):
            length = len(part)
            if kind == "space":
                for i in range(length):
                    info = cells.get((x + i, y))
                    if info is not None:
                        birth, depth = info
                        items.append((x + i, y, birth, depth))
            x += length

    groups: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    for x, y, birth, depth in items:
        bucket = min(int((birth / max(total, 1)) * n_buckets), n_buckets - 1)
        groups.setdefault((bucket, depth), []).append((x, y))

    group_svgs: List[str] = []
    for (bucket, depth) in sorted(groups.keys()):
        group_cells = groups[(bucket, depth)]
        color = _VOID_SVG_PALETTE[depth % n_colors]
        texts = [
            f'<text x="{_MARGIN_X + x * char_w:.1f}" y="{_BASELINE_Y + y * line_h:.1f}" '
            f'xml:space="preserve">{html.escape(fill_char)}</text>'
            for x, y in group_cells
        ]
        if animate:
            begin = -(bucket / n_buckets) * cycle_s
            anim = (
                f'<animate attributeName="opacity" values="0;1;1;0.35;0.35" '
                f'keyTimes="0;0.04;0.5;0.7;1" dur="{cycle_s:.0f}s" '
                f'begin="{begin:.2f}s" repeatCount="indefinite"/>'
            )
            attrs = f' fill="{color}"'
        else:
            anim = ""
            attrs = f' fill="{color}" opacity="0.85"'
        children = texts + ([anim] if anim else [])
        group_svgs.append(f"<g{attrs}>\n      " + "\n      ".join(children) + "\n    </g>")

    body = "\n    ".join(group_svgs) if group_svgs else ""
    citation = VOID_SHAPE_CITATIONS["raices"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f"  <title>{html.escape(title)}</title>\n"
        f"  <desc>{html.escape(citation)}</desc>\n"
        f'  <rect width="{width}" height="{height}" fill="{background}"/>\n'
        f'  <g font-family="monospace" font-size="16">\n    {body}\n  </g>\n'
        f"</svg>\n"
    )


def render_svg_void_shapes(
    text: str,
    mode: str,
    animate: bool = False,
    title: str = "tapiz",
    background: str = _HEX_INK,
    char_w: float = _CHAR_W,
    line_h: float = _LINE_H,
    fill_char: str = "·",
) -> str:
    """Punto de entrada unico para svg_export.py: despacha a la morfologia
    pedida. Cada una es autocontenida (SMIL puro, sin JS -- GitHub-safe)."""
    if mode == "espaciado":
        return _svg_espaciado(text, animate, title, background, char_w, line_h)
    if mode == "zigzag_vertical":
        return _svg_zigzag_vertical(text, animate, title, background, char_w, line_h, fill_char)
    if mode == "raices":
        return _svg_raices(text, animate, title, background, char_w, line_h, fill_char)
    raise ValueError(f"modo de vacio animado desconocido: {mode!r}")
