"""Índice de formatos/plantillas y sugerencia automática."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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
    # --- metadata v2.0 (opcional, retrocompatible) ---
    area: str = ""            # eventos | suplementos | comun
    medio: str = ""           # impresion | digital | mixto
    herramienta: str = ""     # illustrator | photoshop | blender | svg | pipeline 'a+b'
    parametrico: bool = False  # medida la define cada pedido (pendones, banderas)
    origen_info: str = ""     # correo | whatsapp
    inferir: List[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return self.width_cm / max(self.height_cm, 0.01)

    @property
    def has_template(self) -> bool:
        return bool(str(self.template)) and str(self.template) not in ("", "None", ".")

    def __str__(self) -> str:
        extra = []
        if self.area:
            extra.append(self.area)
        if self.medio:
            extra.append(self.medio)
        if self.herramienta:
            extra.append(self.herramienta)
        if self.parametrico:
            extra.append("paramétrico")
        tail = f"  [{' · '.join(extra)}]" if extra else ""
        size = "paramétrico" if self.parametrico else f"{self.width_cm:g}x{self.height_cm:g}cm → {self.canvas_width}x{self.canvas_height}px"
        return f"{self.id} ({self.tipo}): {size}{tail}"



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
            tmpl = f.get("template")
            result.append(FormatInfo(
                id=f["id"],
                tipo=f.get("tipo", ""),
                template=Path(tmpl) if tmpl else Path(""),
                width_cm=float(f["real_size_cm"]["width"]),
                height_cm=float(f["real_size_cm"]["height"]),
                canvas_width=int(f.get("canvas", {}).get("width", 0)),
                canvas_height=int(f.get("canvas", {}).get("height", 0)),
                descripcion=f.get("descripcion", ""),
                area=f.get("area", ""),
                medio=f.get("medio", ""),
                herramienta=f.get("herramienta", ""),
                parametrico=bool(f.get("parametrico", False)),
                origen_info=f.get("origen_info", ""),
                inferir=list(f.get("inferir", []) or []),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return result


def list_formats(
    area: str = "",
    medio: str = "",
    herramienta: str = "",
) -> List[FormatInfo]:
    """Devuelve los formatos disponibles, opcionalmente filtrados.

    Filtros (subcadena, case-insensitive): area (eventos/suplementos),
    medio (impresion/digital), herramienta (illustrator/photoshop/blender).
    """
    formats = load_index()
    if area:
        a = area.lower()
        formats = [f for f in formats if a in f.area.lower()]
    if medio:
        m = medio.lower()
        formats = [f for f in formats if m in f.medio.lower()]
    if herramienta:
        h = herramienta.lower()
        formats = [f for f in formats if h in f.herramienta.lower()]
    return formats


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
