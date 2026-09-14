"""Reescalado de proporción y resolución (DPI) de un config.json de pieza.

Resuelve dos pedidos de modificación frecuentes:

  A) "Cambiar la proporción / medida" (ej. de 16.5x6.5 cm a 14x10 cm).
     -> set_real_size(): cambia `real_size_cm` y recalcula `canvas` px.

  B) "Se ve pixelado / sube la resolución" (misma medida, más px).
     -> set_dpi(): mantiene `real_size_cm` y recalcula `canvas` px al DPI pedido.

Filosofía:
  - El canvas en px y la medida física en cm están ligados por el DPI:
        px = cm / 2.54 * dpi
  - Reescalar la resolución (DPI) NO mueve los elementos en proporción: solo
    cambia el lienzo. Para mantener el diseño visualmente idéntico al subir DPI,
    se ofrece `scale_elements=True`, que multiplica coordenadas/tamaños por el
    factor de escala.
  - Cambiar la PROPORCIÓN sí deforma el encuadre: por eso `set_real_size` NO
    reescala elementos por defecto (avisa que hay que reposicionar a mano /
    en Illustrator). Es un cambio de formato, no de resolución.

Todas las funciones son puras sobre el dict del config (no tocan disco salvo
las envolturas *_file). Esto las hace fáciles de testear.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CM_PER_INCH = 2.54

# Claves de elementos que representan posición/tamaño y deben escalar con el px.
_SCALABLE_KEYS = (
    "x", "y", "w", "h", "cx", "cy", "r", "radius",
    "x1", "y1", "x2", "y2", "size", "max_width",
    "line_height", "stroke_width", "indent", "gap",
)


def cm_to_px(cm: float, dpi: float) -> int:
    """Convierte centímetros a píxeles a un DPI dado."""
    return int(round(cm / CM_PER_INCH * dpi))


def px_to_dpi(px: float, cm: float) -> float:
    """DPI implícito de un lado: px de canvas sobre cm reales."""
    if cm <= 0:
        return 0.0
    return px / cm * CM_PER_INCH


def current_dpi(config: Dict) -> Optional[float]:
    """DPI actual estimado (promedio de ancho y alto). None si faltan datos."""
    canvas = config.get("canvas", {})
    real = canvas.get("real_size_cm", {})
    try:
        w_px, h_px = float(canvas["width"]), float(canvas["height"])
        w_cm, h_cm = float(real["width"]), float(real["height"])
    except (KeyError, TypeError, ValueError):
        return None
    dps = [d for d in (px_to_dpi(w_px, w_cm), px_to_dpi(h_px, h_cm)) if d > 0]
    if not dps:
        return None
    return sum(dps) / len(dps)


def _scale_element(el: Dict, factor: float) -> None:
    """Escala in-place las claves numéricas de posición/tamaño de un elemento."""
    for k in _SCALABLE_KEYS:
        if k in el and isinstance(el[k], (int, float)):
            el[k] = int(round(el[k] * factor)) if k not in ("size", "line_height") else round(el[k] * factor, 2)
    # recursivo para grupos (items con sub-elementos)
    for sub_key in ("elements", "items"):
        if isinstance(el.get(sub_key), list):
            for sub in el[sub_key]:
                if isinstance(sub, dict):
                    _scale_element(sub, factor)


def _scale_all_elements(config: Dict, factor: float) -> None:
    for el in config.get("global_elements", []) or []:
        if isinstance(el, dict):
            _scale_element(el, factor)
    for doc in config.get("documents", []) or []:
        if not isinstance(doc, dict):
            continue
        for el in doc.get("elements", []) or []:
            if isinstance(el, dict):
                _scale_element(el, factor)
    # safe_margin_px también escala
    canvas = config.get("canvas", {})
    if isinstance(canvas.get("safe_margin_px"), (int, float)):
        canvas["safe_margin_px"] = int(round(canvas["safe_margin_px"] * factor))


def set_dpi(
    config: Dict,
    dpi: float,
    scale_elements: bool = True,
) -> Tuple[Dict, Dict]:
    """Cambia la RESOLUCIÓN manteniendo la medida física (cm).

    Retorna (nuevo_config, info). info incluye dpi_antes/después y px nuevos.
    Si scale_elements=True (recomendado), reposiciona los elementos para que el
    diseño se vea idéntico al nuevo DPI.
    """
    if dpi <= 0:
        raise ValueError("dpi debe ser > 0")
    cfg = copy.deepcopy(config)
    canvas = cfg.setdefault("canvas", {})
    real = canvas.get("real_size_cm")
    if not real or "width" not in real or "height" not in real:
        raise ValueError("canvas.real_size_cm con width/height es obligatorio para set_dpi")

    old_w = float(canvas.get("width", 0)) or 1.0
    w_cm, h_cm = float(real["width"]), float(real["height"])
    new_w = cm_to_px(w_cm, dpi)
    new_h = cm_to_px(h_cm, dpi)
    factor = new_w / old_w if old_w else 1.0

    info = {
        "modo": "dpi",
        "dpi_antes": current_dpi(config),
        "dpi_despues": float(dpi),
        "canvas_antes": [config.get("canvas", {}).get("width"), config.get("canvas", {}).get("height")],
        "canvas_despues": [new_w, new_h],
        "factor": round(factor, 4),
        "elementos_reescalados": bool(scale_elements),
    }

    canvas["width"] = new_w
    canvas["height"] = new_h
    if scale_elements and abs(factor - 1.0) > 1e-9:
        _scale_all_elements(cfg, factor)
    return cfg, info


def set_real_size(
    config: Dict,
    width_cm: float,
    height_cm: float,
    dpi: Optional[float] = None,
    scale_elements: bool = False,
) -> Tuple[Dict, Dict]:
    """Cambia la PROPORCIÓN/medida física y recalcula el canvas px.

    Por defecto NO reescala elementos (cambiar proporción deforma el encuadre;
    conviene reposicionar a mano). dpi: si None, conserva el DPI actual.
    """
    if width_cm <= 0 or height_cm <= 0:
        raise ValueError("width_cm y height_cm deben ser > 0")
    cfg = copy.deepcopy(config)
    canvas = cfg.setdefault("canvas", {})

    use_dpi = dpi if dpi and dpi > 0 else (current_dpi(config) or 300.0)
    old_w = float(canvas.get("width", 0)) or 1.0
    new_w = cm_to_px(width_cm, use_dpi)
    new_h = cm_to_px(height_cm, use_dpi)
    factor = new_w / old_w if old_w else 1.0

    info = {
        "modo": "proporcion",
        "real_antes": [
            config.get("canvas", {}).get("real_size_cm", {}).get("width"),
            config.get("canvas", {}).get("real_size_cm", {}).get("height"),
        ],
        "real_despues": [width_cm, height_cm],
        "dpi_usado": round(use_dpi, 1),
        "canvas_antes": [config.get("canvas", {}).get("width"), config.get("canvas", {}).get("height")],
        "canvas_despues": [new_w, new_h],
        "elementos_reescalados": bool(scale_elements),
        "aviso": None if scale_elements else (
            "Los elementos NO se reposicionaron: cambiar proporción deforma el "
            "encuadre. Revisa/reacomoda en Illustrator o regenera desde plantilla."
        ),
    }

    canvas["width"] = new_w
    canvas["height"] = new_h
    canvas["real_size_cm"] = {"width": width_cm, "height": height_cm}
    if scale_elements and abs(factor - 1.0) > 1e-9:
        _scale_all_elements(cfg, factor)
    return cfg, info


# --- Envolturas sobre archivos -------------------------------------------------

def load_config(path: Path) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_config(config: Dict, path: Path) -> None:
    Path(path).write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def rescale_file(
    path: Path,
    *,
    dpi: Optional[float] = None,
    width_cm: Optional[float] = None,
    height_cm: Optional[float] = None,
    scale_elements: Optional[bool] = None,
    out: Optional[Path] = None,
) -> Dict:
    """Aplica rescale a un config.json en disco.

    - Si se dan width_cm y height_cm -> cambio de proporción (set_real_size).
    - Si solo se da dpi -> cambio de resolución (set_dpi).
    Devuelve el dict `info`. Escribe en `out` (o sobre el mismo archivo).
    """
    config = load_config(path)
    if width_cm is not None and height_cm is not None:
        se = bool(scale_elements) if scale_elements is not None else False
        new_cfg, info = set_real_size(config, width_cm, height_cm, dpi=dpi, scale_elements=se)
    elif dpi is not None:
        se = bool(scale_elements) if scale_elements is not None else True
        new_cfg, info = set_dpi(config, dpi, scale_elements=se)
    else:
        raise ValueError("Indica dpi, o width_cm+height_cm")

    target = Path(out) if out else Path(path)
    save_config(new_cfg, target)
    info["archivo"] = str(target)
    return info
