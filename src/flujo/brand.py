"""Reads the default palette. It is a starting point, not a rule.

User's words, 2026-07-26: "como info sirve, como limitante o restriccion no".
Any caller may ignore what this returns, and any event or config may override
it -- one day a post goes out in a different aesthetic, or the flyers change,
and the app must not push back. See projects/cotizaciones/engine.py for the
resolution order (caller > event > this palette).

Source: projects/flujo/flujo.json (colors), with a mirrored fallback below for
when the package runs outside the repo.

History, because it explains why get_color still exists: this module was once
emptied ("migrado a knowledge/logos") while its callers still imported
load_styles/get_color. `flujo cotizaciones` died with ImportError and
render/piezas.py swallowed it in a try/except pass. Restored 2026-07-16.

The `flujo brand` CLI group was removed on 2026-07-26; it did nothing but print
that it had been retired.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# Valores espejo de projects/flujo/flujo.json (colors) -- fallback si el
# JSON no esta (p. ej. paquete instalado fuera del repo). Si cambias la
# identidad, cambia el JSON; esto es solo red de seguridad.
_DEFAULT_COLORS: dict[str, str] = {
    "ink": "#1f2a24",
    "accent": "#2d5a4a",
    "paper": "#f8f1e3",
    "support": "#675f55",
    "alert": "#c2410f",
}

_FLUJO_JSON = Path(__file__).resolve().parents[2] / "projects" / "flujo" / "flujo.json"


@lru_cache(maxsize=1)
def load_styles() -> dict[str, str]:
    """Colores de identidad flujo como dict plano {ink, accent, paper, ...}.

    Lee projects/flujo/flujo.json (seccion colors); si no existe o esta
    corrupto cae a los defaults espejo. Nunca lanza.
    """
    try:
        data: Any = json.loads(_FLUJO_JSON.read_text(encoding="utf-8"))
        colors = data.get("colors")
        if isinstance(colors, dict) and colors:
            return {str(k): str(v) for k, v in colors.items()}
    except (OSError, ValueError):
        pass
    return dict(_DEFAULT_COLORS)


def get_color(key: str, default: str = "#000000") -> str:
    """Un color de la identidad por nombre (ink/accent/paper/support/alert)."""
    return load_styles().get(key, default)
