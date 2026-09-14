"""Genera reporte de privacidad legible para humanos."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .scan import ScanResult


def write_report(output: Path, scan: ScanResult, source_name: str = "") -> Path:
    """Escribe el reporte de privacidad en formato markdown."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    title = source_name or scan.source or "archivo"
    lines.append(f"# Reporte privacidad: {title}")
    lines.append("")
    lines.append(f"- riesgo_privacidad: {scan.risk}")
    lines.append(f"- requiere_sanitizacion: {str(scan.requiere_sanitizacion).lower()}")
    lines.append(f"- requiere_revision_humana: {str(scan.requiere_revision_humana).lower()}")
    lines.append(f"- aprobado_para_ia_externa: {str(scan.aprobado_para_ia_externa).lower()}")
    lines.append(f"- total_pii_encontrados: {scan.total_pii}")
    lines.append("")
    lines.append("## Patrones detectados")
    lines.append("")
    if not scan.matches:
        lines.append("- (ninguno)")
    else:
        for name, matches in scan.matches.items():
            sample = ", ".join(matches[:3])
            lines.append(f"- **{name}** ({len(matches)}): {sample}")
    lines.append("")
    lines.append("## Palabras sensibles / contexto")
    lines.append("")
    if not scan.sensitive_keywords:
        lines.append("- (ninguna)")
    else:
        lines.append("- detectadas: " + ", ".join(scan.sensitive_keywords[:20]))
    lines.append("")
    lines.append("## Recomendaciones")
    lines.append("")
    if scan.requiere_sanitizacion:
        lines.append("- Ejecutar `flujo privacy-sanitize` antes de pasar el texto a IAs externas.")
    if scan.requiere_revision_humana:
        lines.append("- **Requiere revisión humana** antes de cualquier uso.")
    if scan.aprobado_para_ia_externa:
        lines.append("- OK para enviar a IAs externas después de sanitizar.")
    lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    return output
