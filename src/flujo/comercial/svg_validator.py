"""Validacion tecnica liviana para SVGs de suplementos RD."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List
from xml.etree import ElementTree as ET

EXPECTED_CONTRAPORTADA_SIZE = (2000, 2800)
_PLACEHOLDERS = [
    "NOMBRE DEL",
    "SUPLEMENTO",
    "DESCRIPCION",
    "DESCRIPCIÓN",
    "Beneficio principal o idea de campaña",
    "idea de campana",
    "Texto breve y claro para acompañar",
    "para acompanar",
    "Ingredientes o perfil principal",
    "Indicaciones de uso",
    "Recomendación de seguimiento",
    "Recomendacion de seguimiento",
    "texto o QR",
    "espacio editable",
]


def validate_svg_file(path: Path, *, expected_size: tuple[int, int] | None = None) -> Dict[str, Any]:
    """Valida un SVG editable generado por flujo.

    La funcion no intenta reemplazar QA visual en Illustrator. Detecta problemas
    mecanicos: XML invalido, tamano inesperado, placeholders sin reemplazar y
    ausencia de grupos/textos editables.
    """
    path = Path(path)
    errors: List[str] = []
    warnings: List[str] = []
    summary: Dict[str, Any] = {"path": str(path)}

    if not path.exists():
        return {"ok": False, "errors": [f"No existe: {path}"], "warnings": [], "summary": summary}

    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return {"ok": False, "errors": [f"SVG/XML invalido: {exc}"], "warnings": [], "summary": summary}

    width = _number(root.get("width"))
    height = _number(root.get("height"))
    viewbox = root.get("viewBox", "")

    # Un SVG puede declarar su tamano SOLO con viewBox, sin width/height: es lo
    # que exporta Illustrator y es SVG valido. Las contraportadas aprobadas
    # vienen asi, y el validador las reportaba como "no se pudo leer
    # width/height" -- avisando de un defecto que no existia sobre las unicas
    # piezas que se imprimieron.
    if (width is None or height is None) and viewbox:
        partes = viewbox.replace(",", " ").split()
        if len(partes) == 4:
            vb_w, vb_h = _number(partes[2]), _number(partes[3])
            if vb_w and vb_h:
                width = width if width is not None else vb_w
                height = height if height is not None else vb_h

    summary.update({"width": width, "height": height, "viewBox": viewbox})

    if expected_size and width is not None and height is not None:
        exp_w, exp_h = expected_size
        if abs(width - exp_w) > 2 or abs(height - exp_h) > 2:
            errors.append(f"Tamano inesperado: {width:g}x{height:g}px; esperado {exp_w}x{exp_h}px.")
    elif width is None or height is None:
        warnings.append("El SVG no declara tamano: ni width/height ni viewBox.")

    text_elements = _count_local(root, "text")
    group_elements = _count_local(root, "g")
    if text_elements == 0:
        warnings.append("No se detectan elementos <text>; revisar que siga siendo editable en Illustrator.")
    if group_elements == 0:
        warnings.append("No se detectan grupos <g>; revisar estructura editable.")

    leftovers = [token for token in _PLACEHOLDERS if token in text]
    if leftovers:
        errors.append("Placeholders sin reemplazar: " + ", ".join(leftovers[:6]))

    summary["text_elements"] = text_elements
    summary["group_elements"] = group_elements
    summary["bytes"] = len(text.encode("utf-8"))
    return {"ok": not errors, "errors": errors, "warnings": warnings, "summary": summary}


def validate_svg_files(paths: Iterable[Path], *, expected_size: tuple[int, int] | None = None) -> Dict[str, Any]:
    items = [validate_svg_file(path, expected_size=expected_size) for path in paths]
    errors = [f"{item['summary'].get('path')}: {err}" for item in items for err in item["errors"]]
    warnings = [f"{item['summary'].get('path')}: {warn}" for item in items for warn in item["warnings"]]
    return {"ok": not errors, "errors": errors, "warnings": warnings, "items": items}


def render_svg_validation_report(report: Dict[str, Any]) -> str:
    lines = ["VALIDACION SVG SUPLEMENTOS RD", "=" * 34, f"Estado: {'OK' if report['ok'] else 'ERROR'}"]
    if "items" in report:
        lines.append(f"Archivos: {len(report['items'])}")
        for item in report["items"]:
            s = item["summary"]
            lines.append(f"  - {s.get('path')} | {s.get('width', '?')}x{s.get('height', '?')}px | {'OK' if item['ok'] else 'ERROR'}")
    else:
        s = report["summary"]
        lines.append(f"Archivo: {s.get('path')}")
        lines.append(f"Tamano: {s.get('width', '?')}x{s.get('height', '?')}px")
    if report.get("errors"):
        lines.append("")
        lines.append("Errores:")
        lines.extend(f"  - {err}" for err in report["errors"])
    if report.get("warnings"):
        lines.append("")
        lines.append("Advertencias:")
        lines.extend(f"  - {warn}" for warn in report["warnings"])
    if not report.get("errors") and not report.get("warnings"):
        lines.append("")
        lines.append("Sin hallazgos mecanicos. Abrir en Illustrator para QA visual final.")
    return "\n".join(lines)


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None
    return float(match.group(0))


def _count_local(root: ET.Element, name: str) -> int:
    return sum(1 for elem in root.iter() if elem.tag.rsplit("}", 1)[-1] == name)
