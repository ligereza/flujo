"""Renderizador SVG liviano para PREVIEW en el editor web.

NO reemplaza al generador oficial (`tools/piezas_vectoriales/scripts/generar_desde_json.py`),
que produce el SVG editable + vectorizado de calidad de producción usando fuentes
del sistema (matplotlib TextPath).

Este módulo genera un SVG rápido, sin dependencias externas, suficiente para
visualizar un `config.json` mientras se editan datos/proporción en Gradio.
El texto se deja "vivo" (<text>), con word-wrap aproximado por conteo de glifos.

Mantiene el mismo "contrato" de config que el generador oficial:
  canvas {width,height,real_size_cm,safe_margin_px}
  palette {nombre: "#hex"}
  background, global_elements[], documents[].elements[]
Tipos soportados: rect, panel, circle, line, text, paragraph, image, group.
"""

from __future__ import annotations

import html
from typing import Dict, List, Optional


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _color(value, palette: Dict) -> str:
    if value in (None, "", "none"):
        return "none"
    if isinstance(value, str) and value.startswith("#"):
        return value
    return palette.get(value, value)


def _avg_char_width(size: float) -> float:
    # Aproximación: ancho medio de glifo ~0.52 * tamaño para sans-serif.
    return size * 0.52


def _wrap(text: str, max_width: Optional[float], size: float) -> List[str]:
    if not max_width or max_width <= 0:
        return text.split("\n")
    cpl = max(1, int(max_width / _avg_char_width(size)))
    out: List[str] = []
    for raw in text.split("\n"):
        words = raw.split()
        if not words:
            out.append("")
            continue
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if len(test) <= cpl or not cur:
                cur = test
            else:
                out.append(cur)
                cur = w
        if cur:
            out.append(cur)
    return out


def _render_element(out: List[str], el: Dict, palette: Dict) -> None:
    t = el.get("type", "")
    op = el.get("opacity")
    op_attr = f' opacity="{op}"' if op is not None else ""

    if t in ("rect", "panel"):
        fill = _color(el.get("fill", "white"), palette)
        stroke = el.get("stroke")
        stroke_attr = (
            f' stroke="{_color(stroke, palette)}" stroke-width="{el.get("stroke_width", 1)}"'
            if stroke else ""
        )
        out.append(
            f'<rect x="{el.get("x",0)}" y="{el.get("y",0)}" '
            f'width="{el.get("w",100)}" height="{el.get("h",100)}" '
            f'rx="{el.get("radius",0)}" fill="{fill}"{stroke_attr}{op_attr}/>'
        )
    elif t == "circle":
        fill = _color(el.get("fill", "white"), palette)
        out.append(
            f'<circle cx="{el.get("cx",0)}" cy="{el.get("cy",0)}" r="{el.get("r",50)}" '
            f'fill="{fill}"{op_attr}/>'
        )
    elif t == "line":
        out.append(
            f'<line x1="{el.get("x1",0)}" y1="{el.get("y1",0)}" '
            f'x2="{el.get("x2",0)}" y2="{el.get("y2",0)}" '
            f'stroke="{_color(el.get("stroke","ink"), palette)}" '
            f'stroke-width="{el.get("stroke_width",1)}"{op_attr}/>'
        )
    elif t == "image":
        # imagen enlazada (href). Para Illustrator conviene ENLAZADA, no incrustada.
        href = el.get("src") or el.get("href") or ""
        x, y = el.get("x", 0), el.get("y", 0)
        w, h = el.get("w", 200), el.get("h", 200)
        if href:
            out.append(
                f'<image href="{_esc(href)}" x="{x}" y="{y}" width="{w}" height="{h}" '
                f'preserveAspectRatio="xMidYMid slice"{op_attr}/>'
            )
        else:
            # placeholder visible cuando aún no hay imagen
            out.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#cccccc" '
                f'stroke="#999999" stroke-width="2"{op_attr}/>'
                f'<text x="{x + w/2}" y="{y + h/2}" fill="#666666" font-size="{max(14, h*0.08)}" '
                f'text-anchor="middle" font-family="sans-serif">IMAGEN</text>'
            )
    elif t in ("text", "paragraph"):
        _render_text(out, el, palette)
    elif t == "group":
        for sub in el.get("elements", []) or el.get("items", []) or []:
            if isinstance(sub, dict):
                _render_element(out, sub, palette)


def _render_text(out: List[str], el: Dict, palette: Dict) -> None:
    # Auto-fit: ajusta el size/line_height si el elemento lo pide (autofit + max_width)
    try:
        from ..render.autofit import autofit_element, approx_measure
        el = autofit_element(el, approx_measure)
    except Exception:
        pass
    fill = _color(el.get("fill", "ink"), palette)
    size = float(el.get("size", 40))
    weight_raw = el.get("weight")
    weight = "700" if weight_raw == "bold" else "400"
    line_height = float(el.get("line_height", size * 1.28))
    max_width = el.get("max_width")
    x = el.get("x", 0)
    y = el.get("y", 0)
    content = str(el.get("content", ""))
    lines = _wrap(content, float(max_width) if max_width else None, size)
    cy = y
    for line in lines:
        if line == "":
            cy += line_height * 0.55
            continue
        out.append(
            f'<text x="{x}" y="{cy + size}" fill="{fill}" '
            f'font-family="Inter, Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}">{_esc(line)}</text>'
        )
        cy += line_height


def render_svg(config: Dict, doc_index: int = 0, show_safe_area: bool = False,
               responsive: bool = False) -> str:
    """Genera el SVG (string) de un documento del config para preview.

    doc_index: cuál documento de config["documents"] renderizar.
    show_safe_area: dibuja el margen seguro (guía, no se exporta).
    """
    canvas = config.get("canvas", {})
    w = canvas.get("width", 1000) or 1000
    h = canvas.get("height", 1000) or 1000
    palette = config.get("palette", {})
    docs = config.get("documents", [])
    # En modo responsive el SVG se escala al contenedor (no se sale de pantalla):
    # width=100%, height=auto y el viewBox hace el trabajo. En modo archivo
    # (export) se mantienen los px reales.
    if responsive:
        dim = 'width="100%" height="auto" preserveAspectRatio="xMidYMid meet" ' \
              f'style="max-height:80vh;display:block" viewBox="0 0 {w} {h}"'
    else:
        dim = f'width="{w}px" height="{h}px" viewBox="0 0 {w} {h}"'

    if not docs:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" {dim}>'
                f'<rect width="{w}" height="{h}" fill="#eee"/>'
                f'<text x="{w/2}" y="{h/2}" text-anchor="middle" font-size="40" fill="#999">'
                f'sin documentos</text></svg>')
    doc_index = max(0, min(doc_index, len(docs) - 1))
    doc = docs[doc_index]

    out: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" {dim}>'
    ]
    bg = doc.get("background", config.get("background", "white"))
    out.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="{_color(bg, palette)}"/>')

    for el in config.get("global_elements", []) or []:
        if isinstance(el, dict):
            _render_element(out, el, palette)
    for el in doc.get("elements", []) or []:
        if isinstance(el, dict):
            _render_element(out, el, palette)

    if show_safe_area:
        m = canvas.get("safe_margin_px", 0) or 0
        if m:
            out.append(
                f'<rect x="{m}" y="{m}" width="{w-2*m}" height="{h-2*m}" '
                f'fill="none" stroke="#ff00aa" stroke-width="2" stroke-dasharray="20 12" opacity="0.6"/>'
            )

    out.append("</svg>")
    return "\n".join(out)
