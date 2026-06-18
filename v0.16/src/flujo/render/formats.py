"""Índice de formatos/plantillas y sugerencia automática."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


INDEX_PATHS = [
    "tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json",
]


@dataclass
class FormatInfo:
    id: str
    tipo: str
    template: Path
    width_cm: float
    height_cm: float
    canvas_width: int
    canvas_height: int
    descripcion: str = ""

    @property
    def ratio(self) -> float:
        return self.width_cm / max(self.height_cm, 0.01)

    def __str__(self) -> str:
        return (
            f"{self.id} ({self.tipo}): {self.width_cm:g}x{self.height_cm:g}cm → "
            f"{self.canvas_width}x{self.canvas_height}px"
        )


def _find_index() -> Optional[Path]:
    """Busca el INDEX_FORMATOS.json en ubicaciones conocidas."""
    from ..paths import repo_root

    repo = repo_root()
    for rel in INDEX_PATHS:
        p = repo / rel
        if p.exists():
            return p
    return None


def load_index() -> List[FormatInfo]:
    """Carga el índice de formatos. Lista vacía si no existe."""
    idx = _find_index()
    if not idx:
        return []
    data = json.loads(idx.read_text(encoding="utf-8"))
    formatos = data.get("formatos", [])
    result: List[FormatInfo] = []
    for f in formatos:
        try:
            result.append(FormatInfo(
                id=f["id"],
                tipo=f.get("tipo", ""),
                template=Path(f["template"]),
                width_cm=float(f["real_size_cm"]["width"]),
                height_cm=float(f["real_size_cm"]["height"]),
                canvas_width=int(f["canvas"]["width"]),
                canvas_height=int(f["canvas"]["height"]),
                descripcion=f.get("descripcion", ""),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return result


def list_formats() -> List[FormatInfo]:
    """Devuelve todos los formatos disponibles."""
    return load_index()


def suggest_format(
    width_cm: Optional[float] = None,
    height_cm: Optional[float] = None,
    tipo: str = "",
) -> List[FormatInfo]:
    """Sugiere los formatos más apropiados para unas medidas/tipo dados.

    Si width_cm/height_cm son None, devuelve por coincidencia de tipo.
    Retorna hasta 5 sugerencias ordenadas por score.
    """
    formats = load_index()
    if not formats:
        return []

    if not width_cm or not height_cm:
        # Solo por tipo
        if tipo:
            tipo_lower = tipo.lower()
            return [f for f in formats if tipo_lower in f.tipo.lower() or tipo_lower.replace("-", "_") in f.id.lower()][:5]
        return formats[:5]

    target_ratio = width_cm / max(height_cm, 0.01)
    tipo_lower = tipo.lower() if tipo else ""

    def score(f: FormatInfo) -> float:
        ratio_diff = abs(f.ratio - target_ratio)
        size_diff = abs(f.width_cm - width_cm) + abs(f.height_cm - height_cm)
        type_bonus = 0.0
        if tipo_lower:
            if tipo_lower in f.tipo.lower() or tipo_lower.replace("-", "_") in f.id.lower():
                type_bonus = 0.0
            else:
                type_bonus = 5.0
        return ratio_diff * 10 + size_diff + type_bonus

    return sorted(formats, key=score)[:5]


def find_format_by_id(fmt_id: str) -> Optional[FormatInfo]:
    """Encuentra un formato por su id."""
    for f in load_index():
        if f.id == fmt_id:
            return f
    return None
