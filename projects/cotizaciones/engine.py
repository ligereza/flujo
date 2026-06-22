"""Cotizaciones duales integradas con aistetic y planos.

Genera 2 versiones:
- productora: branded, infográfico (usa aistetic + formatos)
- interno (ong/empresa): desglose detallado
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.flujo.plano import load_evento, resumen_costos
from src.flujo.aistetic import load_styles, get_color  # ← nuevo loader central

def generar_cotizacion(evento_path: Path, audiencia: str = "productora", output_dir: Path | None = None) -> dict:
    """Genera cotización real (archivos) según audiencia, usando aistetic."""
    ev = load_evento(evento_path)
    styles = load_styles()
    costos = resumen_costos(ev)

    if output_dir is None:
        output_dir = Path("exports") / f"cotizacion_{ev.get('nombre','evento').lower().replace(' ','_')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    ink, accent, paper = styles.get("ink"), styles.get("accent"), styles.get("paper")

    if audiencia == "productora":
        # Branded infographic style for productoras (diseñador ONG)
        content = f"""COTIZACIÓN — {ev.get('nombre', 'Evento')} | Reduciendo Daño

Estilo: aistetic (ink={ink} accent={accent} paper={paper})
Formato: infografía lista para Illustrator/Photoshop (ver catálogo)

{ev.get('notas', '')}

{costos}

Entrega lista. Usa aistetic para consistencia de marca.
"""
        (output_dir / "cotizacion_productora.txt").write_text(content, encoding="utf-8")
        # Simple HTML infographic using aistetic
        html = f"""<html><body style="background:{paper};color:{ink};font-family:sans-serif">
<h1 style="color:{accent}">COTIZACIÓN — Reduciendo Daño</h1>
<pre>{costos}</pre>
<p>Estilo aistetic aplicado. Abre en navegador o convierte a imagen.</p>
</body></html>"""
        (output_dir / "cotizacion_productora.html").write_text(html, encoding="utf-8")
        return {"files": [str(output_dir / "cotizacion_productora.txt"), str(output_dir / "cotizacion_productora.html")], "estilo": "aistetic"}

    else:
        # Detallado interno para ONG/empresa
        content = f"""COTIZACIÓN INTERNA — {ev.get('nombre', 'Evento')}
Para: ONG / trabajador / empresa

{costos}

Notas internas: ajustar precios reales.
Referencia aistetic para tono en comunicaciones.
"""
        (output_dir / "cotizacion_interno.txt").write_text(content, encoding="utf-8")
        return {"files": [str(output_dir / "cotizacion_interno.txt")], "estilo": "interno"}

if __name__ == "__main__":
    print(generar_cotizacion(Path("projects/plano/ejemplos/evento_ejemplo.json"), "productora"))
