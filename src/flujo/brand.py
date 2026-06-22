"""Carga central de la identidad visual 'flujo' (BRAND ENFORCED).

Fuente de verdad: projects/flujo/flujo.json
Colores EXACTOS: ink, accent, paper (print-SVG only), support, alert.
Usado por hub.py /api/load-flujo-brand, visualizers, tapiz, renders.

Uso:
    from flujo.brand import load_styles, get_color

    styles = load_styles()
    accent = get_color("accent")

Todos los outputs visuales (HTML pro + SVGs) deben derivar de aquí + pasar Brand Validator JS.
NO hardcode neon/light fuera de paper.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .paths import asset_root, repo_root


def load_styles() -> Dict[str, Any]:
    """Devuelve colores + tipografía + tono de flujo.json."""
    path = asset_root() / "projects" / "flujo" / "flujo.json"
    if not path.exists():
        return _defaults()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        colors = data.get("colors", {})
        typography = data.get("typography", {})
        tone = data.get("tone", {})
        return {**colors, **typography, "tone": tone}
    except Exception:
        return _defaults()


def get_color(name: str, default: str = "#000000") -> str:
    """Acceso rápido a un color."""
    return load_styles().get(name, default)


def _defaults() -> Dict[str, Any]:
    return {
        "ink": "#1f2a24",
        "accent": "#2d5a4a",
        "paper": "#f8f1e3",
        "support": "#675f55",
        "alert": "#c2410f",
        "tone": {"voice": "directo, útil, humano"}
    }
