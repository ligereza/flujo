"""Auto-fit de texto: ajusta el tamaño de fuente para que un texto quepa en una caja.

Resuelve el caso "misma medida, distinto texto": dos etiquetas del mismo formato
donde una tiene más ingredientes que la otra. En vez de que el texto se desborde,
el sistema reduce (o limita) el tamaño de fuente hasta que entra en el alto/ancho
disponible — respetando un tamaño mínimo legible.

Diseño:
  - Es **independiente del motor de medición**: recibe una función `measure(text,
    size, weight) -> ancho_px`. Así el generador oficial puede pasar la medición
    exacta (matplotlib TextPath) y el preview una aproximación, reusando la misma
    lógica de ajuste.
  - Funciones puras y testeables. Sin dependencias externas.

Campos que lee de un elemento de texto (config.json):
  size, weight, max_width, line_height, content
  autofit (bool)        -> activar el ajuste
  max_height            -> alto disponible de la caja (px); si falta, no limita por alto
  min_size              -> tamaño mínimo de fuente (default 50% del size)
  locked (bool)         -> si True, NUNCA se reescala (datos exactos: gramaje, lote...)
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

# measure(text, size, weight) -> ancho en px
MeasureFn = Callable[[str, float, str], float]


def approx_measure(text: str, size: float, weight: str = "regular") -> float:
    """Medición aproximada (sin fuentes): ~0.52*size por glifo. Para preview."""
    factor = 0.52 if weight != "bold" else 0.56
    return len(text) * size * factor


def wrap_text(text: str, max_width: float, size: float, weight: str, measure: MeasureFn) -> List[str]:
    """Parte el texto en líneas que quepan en max_width, respetando saltos \\n."""
    if not max_width or max_width <= 0:
        return str(text).split("\n")
    out: List[str] = []
    for para in str(text).split("\n"):
        words = para.split()
        if not words:
            out.append("")
            continue
        cur = ""
        for word in words:
            test = word if not cur else cur + " " + word
            if measure(test, size, weight) <= max_width or not cur:
                cur = test
            else:
                out.append(cur)
                cur = word
        if cur:
            out.append(cur)
    return out


def measured_height(text: str, size: float, weight: str, max_width: float,
                    line_height: float, measure: MeasureFn) -> float:
    """Alto total (px) que ocuparía el texto envuelto a un tamaño dado."""
    lines = wrap_text(text, max_width, size, weight, measure)
    # cuenta líneas vacías como medio salto (igual que el generador)
    total = 0.0
    for ln in lines:
        total += line_height if ln != "" else line_height * 0.55
    return total


def fit_font_size(
    text: str,
    *,
    size: float,
    max_width: float,
    max_height: float | None = None,
    weight: str = "regular",
    line_height_ratio: float = 1.28,
    min_size: float | None = None,
    measure: MeasureFn = approx_measure,
    step: float = 2.0,
) -> Tuple[float, List[str]]:
    """Devuelve (tamaño_ajustado, lineas) para que el texto quepa.

    - Si no hay max_height, solo asegura que cada palabra/linea no exceda el ancho
      (reduce si una sola palabra no cabe).
    - Si hay max_height, reduce el tamaño hasta que el alto envuelto entre, sin
      bajar de min_size.
    """
    size = float(size)
    min_size = float(min_size) if min_size else max(8.0, size * 0.5)
    cur = size

    def line_h(s: float) -> float:
        return s * line_height_ratio

    # 1) asegurar que el ancho no se rompa (si una palabra sola no cabe)
    def longest_word_fits(s: float) -> bool:
        for word in str(text).replace("\n", " ").split():
            if measure(word, s, weight) > max_width and max_width > 0:
                return False
        return True

    while cur > min_size and not longest_word_fits(cur):
        cur -= step

    # 2) si hay límite de alto, reducir hasta entrar
    if max_height and max_height > 0:
        while cur > min_size:
            h = measured_height(text, cur, weight, max_width, line_h(cur), measure)
            if h <= max_height:
                break
            cur -= step
        cur = max(cur, min_size)

    lines = wrap_text(text, max_width, cur, weight, measure)
    return round(cur, 2), lines


def autofit_element(el: Dict, measure: MeasureFn = approx_measure) -> Dict:
    """Devuelve una COPIA del elemento con `size`/`line_height` ajustados.

    Solo actúa si el elemento es de texto, tiene `autofit: true` y NO está
    `locked`. Caso contrario devuelve el elemento sin cambios.
    """
    if el.get("type") not in ("text", "paragraph"):
        return el
    if el.get("locked") or not el.get("autofit"):
        return el
    max_width = el.get("max_width")
    if not max_width:
        return el

    size = float(el.get("size", 40))
    weight = el.get("weight", "regular")
    lh_ratio = (el["line_height"] / size) if el.get("line_height") and size else 1.28
    new_size, _ = fit_font_size(
        str(el.get("content", "")),
        size=size,
        max_width=float(max_width),
        max_height=el.get("max_height"),
        weight=weight,
        line_height_ratio=lh_ratio,
        min_size=el.get("min_size"),
        measure=measure,
    )
    out = dict(el)
    out["size"] = new_size
    out["line_height"] = round(new_size * lh_ratio, 2)
    return out


def autofit_config(config: Dict, measure: MeasureFn = approx_measure) -> Dict:
    """Aplica autofit a todos los elementos de texto de un config (copia)."""
    import copy

    cfg = copy.deepcopy(config)
    for el in cfg.get("global_elements", []) or []:
        if isinstance(el, dict):
            el.update(autofit_element(el, measure))
    for doc in cfg.get("documents", []) or []:
        if not isinstance(doc, dict):
            continue
        new_elements = []
        for el in doc.get("elements", []) or []:
            new_elements.append(autofit_element(el, measure) if isinstance(el, dict) else el)
        doc["elements"] = new_elements
    return cfg
