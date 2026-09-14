"""
sobrevivencia-01 -- survival-of-marks: pieza SVG estatica del corpus tilde_log.

Render target definido en projects/tilde/SPEC.md. Lee el corpus JSONL que
acumula desktop/tilde_meter.py (una compresion por linea) y lo vuelve un
nucleo de sedimento: una banda horizontal por muestra, un tick vertical por
marca que ENTRO a la compresion. Tick en color acento = la marca sobrevivio;
tick en trazo fantasma = la marca se perdio (erosion visible, no ausencia).

Puro stdlib, sin red, sin LLM, salida determinista para el mismo archivo.

REGLA DE PRIVACIDAD (vinculante, SPEC seccion 2): este renderer NUNCA copia
los campos `original` ni `compressed` al SVG. Solo usa conteos, pares
per_mark y pares de palabras degradadas (vocabulario publico del
instrumento). El corpus es material del usuario y queda gitignored.

Uso:
    py projects/tilde/sobrevivencia.py desktop/tilde_log.jsonl \
        --svg projects/tilde/out/sobrevivencia_01.svg
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

# Paleta flujo real: la misma familia que el exportador SVG del tapiz
# (tilde es pieza hermana, SPEC criterio 8). Se importa del modulo real;
# si el script corre fuera del repo, se usan los mismos hex copiados
# textualmente de projects/tapiz/vibecode/svg_export.py.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
try:
    from projects.tapiz.vibecode.svg_export import (  # type: ignore
        FLUJO_HEX,
        GHOST_COLOR,
        LOOM_VOID_HEX,
    )
except ImportError:
    # Valores exactos de projects/tapiz/vibecode/svg_export.py (paleta flujo
    # real, hex de projects/flujo/flujo.json).
    FLUJO_HEX = {
        "ink": "#1f2a24",
        "accent": "#2d5a4a",
        "support": "#675f55",
        "alert": "#c2410f",
        "paper": "#f8f1e3",
    }
    GHOST_COLOR = "#4a554e"
    LOOM_VOID_HEX = "#28332c"

SURVIVOR_COLOR = FLUJO_HEX["accent"]   # marca que sobrevivio
LOST_COLOR = GHOST_COLOR               # marca perdida: trazo fantasma
BAND_BG_COLOR = LOOM_VOID_HEX          # lecho de la banda, apenas sobre el ink
BACKGROUND = FLUJO_HEX["ink"]
LABEL_COLOR = FLUJO_HEX["paper"]
CAPTION_COLOR = FLUJO_HEX["support"]
FOOTER_COLOR = FLUJO_HEX["alert"]

# Geometria (constantes: misma entrada -> mismos bytes)
MARGIN = 24
TITLE_H = 44
BAND_H = 14
BAND_GAP = 6
TICK_STEP = 6
TICK_W = 2
MIN_CONTENT_W = 260
LABEL_W = 72
CAPTION_LINE_H = 15
FOOTER_H = 40

TITLE = "sobrevivencia-01"

# Pares minimos canonicos, verbatim del dossier tilde (SPEC seccion 1):
# perder la marca SI cambia el significado.
MINIMAL_PAIRS = [
    "año / ano",
    "papá / papa",
    "él / el",
    "sólo / solo",
]


def load_corpus(path: str) -> List[Dict]:
    """Lee el corpus JSONL (una muestra por linea, lineas vacias ignoradas)."""
    samples: List[Dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def aggregate(samples: List[Dict]) -> Dict:
    """
    Linea agregada del pie: misma semantica que summarize() en
    desktop/tilde_meter.py (muestras, sobrevivencia media, marcas mas
    perdidas), calculada sobre las muestras ya parseadas y con orden
    determinista (mas perdidas primero, empate por marca).
    """
    survivals = [s["survival"] for s in samples if s.get("survival") is not None]
    lost: Dict[str, int] = {}
    for s in samples:
        for mark, pair in (s.get("per_mark") or {}).items():
            n_in, n_out = int(pair[0]), int(pair[1])
            if n_in > n_out:
                lost[mark] = lost.get(mark, 0) + (n_in - n_out)
    ranking = sorted(lost.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    return {
        "samples": len(samples),
        "avg_survival": round(sum(survivals) / len(survivals), 3) if survivals else None,
        "marks_most_lost": ranking,
    }


def _band_ticks(per_mark: Dict[str, List[int]]) -> List[bool]:
    """
    Lista de ticks de la banda en orden determinista (marcas ordenadas):
    True = sobrevivio, False = se perdio. Por cada marca se dibujan
    count_in ticks, primero los sobrevivientes y despues los perdidos.
    """
    ticks: List[bool] = []
    for mark in sorted(per_mark):
        pair = per_mark[mark]
        n_in, n_out = int(pair[0]), int(pair[1])
        survivors = min(n_out, n_in)
        ticks.extend([True] * survivors)
        ticks.extend([False] * (n_in - survivors))
    return ticks


def _text(x: float, y: float, content: str, fill: str, size: int = 10) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="monospace" font-size="{size}" '
        f'fill="{fill}" xml:space="preserve">{html.escape(content)}</text>'
    )


def _svg_document(width: int, height: int, body: str, desc: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f"  <title>{html.escape(TITLE)}</title>\n"
        f"  <desc>{html.escape(desc)}</desc>\n"
        f'  <rect width="{width}" height="{height}" fill="{BACKGROUND}"/>\n'
        f"{body}"
        f"</svg>\n"
    )


def render_placeholder() -> str:
    """
    Corpus vacio o inexistente: pieza sobre la ausencia, no un error
    (SPEC criterio 5). Sale bien formada y con la misma paleta.
    """
    width = MARGIN * 2 + MIN_CONTENT_W + LABEL_W
    height = 160
    lines = [
        f"  {_text(MARGIN, 36, TITLE, LABEL_COLOR, 14)}\n",
        f'  <rect x="{MARGIN}" y="58" width="{MIN_CONTENT_W}" height="{BAND_H}" '
        f'fill="{BAND_BG_COLOR}"/>\n',
        f"  {_text(MARGIN, 96, 'el corpus no tiene muestras todavia', CAPTION_COLOR, 11)}\n",
        f"  {_text(MARGIN, 114, 'ninguna marca ha entrado a la compresion', CAPTION_COLOR, 11)}\n",
        f"  {_text(MARGIN, 140, '0 muestras', FOOTER_COLOR, 10)}\n",
    ]
    return _svg_document(
        width,
        height,
        "".join(lines),
        "sobrevivencia-01 sin corpus: una banda vacia, nada en juego aun.",
    )


def render_svg(samples: List[Dict]) -> str:
    """Nucleo de sedimento: una banda por muestra, en orden de archivo."""
    if not samples:
        return render_placeholder()

    max_marks = max(int(s.get("marks_in") or 0) for s in samples)
    content_w = max(MIN_CONTENT_W, max_marks * TICK_STEP)
    label_x = MARGIN + content_w + 14
    width = label_x + LABEL_W + MARGIN

    caption_h = CAPTION_LINE_H * (len(MINIMAL_PAIRS) + 1) + 12
    bands_h = len(samples) * (BAND_H + BAND_GAP)
    height = TITLE_H + bands_h + caption_h + FOOTER_H + MARGIN

    parts: List[str] = [f"  {_text(MARGIN, 30, TITLE, LABEL_COLOR, 14)}\n"]

    # Bandas: estratos cronologicos, mas marcas = banda mas ancha.
    for i, sample in enumerate(samples):
        y = TITLE_H + i * (BAND_H + BAND_GAP)
        marks_in = int(sample.get("marks_in") or 0)
        survival = sample.get("survival")
        band_w = max(marks_in * TICK_STEP, 3)  # nula/sin marcas: hilo minimo
        band: List[str] = [
            f'  <g class="band">\n'
            f'    <rect class="band-bg" x="{MARGIN}" y="{y}" width="{band_w}" '
            f'height="{BAND_H}" fill="{BAND_BG_COLOR}"/>\n'
        ]
        if survival is not None:
            for j, survived in enumerate(_band_ticks(sample.get("per_mark") or {})):
                color = SURVIVOR_COLOR if survived else LOST_COLOR
                x = MARGIN + 2 + j * TICK_STEP
                band.append(
                    f'    <rect class="tick" x="{x}" y="{y + 2}" width="{TICK_W}" '
                    f'height="{BAND_H - 4}" fill="{color}"/>\n'
                )
            band.append(
                f'    {_text(label_x, y + BAND_H - 3, f"{float(survival):.3f}", LABEL_COLOR)}\n'
            )
        # survival null: banda vacia, una linea de espanol sin nada en juego.
        band.append("  </g>\n")
        parts.extend(band)

    # Caption: pares minimos canonicos del dossier, verbatim.
    cap_y = TITLE_H + bands_h + 18
    parts.append(f"  {_text(MARGIN, cap_y, 'pares minimos (perder la marca cambia el sentido):', CAPTION_COLOR)}\n")
    for k, pair in enumerate(MINIMAL_PAIRS):
        parts.append(f"  {_text(MARGIN, cap_y + (k + 1) * CAPTION_LINE_H, pair, CAPTION_COLOR)}\n")

    # Pie: linea agregada (semantica de summarize() del instrumento).
    agg = aggregate(samples)
    avg = "s/d" if agg["avg_survival"] is None else f"{agg['avg_survival']:.3f}"
    if agg["marks_most_lost"]:
        ranking = " ".join(f"{mark}:{n}" for mark, n in agg["marks_most_lost"])
    else:
        ranking = "ninguna"
    footer = (
        f"{agg['samples']} muestras | sobrevivencia media {avg} | "
        f"mas perdidas: {ranking}"
    )
    parts.append(f"  {_text(MARGIN, height - MARGIN, footer, FOOTER_COLOR)}\n")

    return _svg_document(
        width,
        height,
        "".join(parts),
        "sobrevivencia-01: una banda por compresion registrada; tick acento = "
        "marca sobreviviente, tick fantasma = marca perdida. Solo agregados y "
        "conteos: el texto crudo del corpus nunca entra a la pieza.",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sobrevivencia",
        description="Renderiza el corpus tilde_log como pieza SVG sobrevivencia-01.",
    )
    parser.add_argument("corpus", help="ruta al corpus JSONL de tilde_meter")
    default_svg = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out", "sobrevivencia_01.svg"
    )
    parser.add_argument("--svg", default=default_svg, help="ruta del SVG de salida")
    args = parser.parse_args(argv)

    if os.path.isfile(args.corpus):
        samples = load_corpus(args.corpus)
    else:
        samples = []  # corpus inexistente: pieza sobre la ausencia, exit 0

    svg = render_svg(samples)

    out_dir = os.path.dirname(os.path.abspath(args.svg))
    os.makedirs(out_dir, exist_ok=True)  # projects/tilde/out/ se crea perezoso
    with open(args.svg, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)

    # Consola Windows cp1252: solo ASCII en stdout.
    print(f"OK: {len(samples)} muestras -> {args.svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
