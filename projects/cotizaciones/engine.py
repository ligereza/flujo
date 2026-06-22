"""Cotizaciones duales integradas con aistetic y planos.

Genera 2 versiones:
- productora: branded, infográfico (usa aistetic + formatos)
- interno (ong/empresa): desglose detallado
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.flujo.plano import load_evento, resumen_costos  # reuse existing

def _load_aistetic() -> Dict[str, Any]:
    p = Path("projects/aistetic/aistetic.json")
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}

def generar_cotizacion(evento_path: Path, audiencia: str = "productora") -> str:
    """Genera cotización según audiencia, usando aistetic para estilo."""
    ev = load_evento(evento_path)
    aistetic = _load_aistetic()
    costos = resumen_costos(ev)
    c = aistetic.get("colors", {})
    ink, accent, paper = c.get("ink", "#1f2a24"), c.get("accent", "#2d5a4a"), c.get("paper", "#f8f1e3")

    if audiencia == "productora":
        # Versión externa: branded para productoras (como diseñador ONG)
        return f"""COTIZACIÓN — {ev.get('nombre', 'Evento')} | Reduciendo Daño
Estilo: aistetic (ink:{ink} accent:{accent} paper:{paper})
Formato recomendado: rider A4 o infografía del catálogo.

{ev.get('notas', '')}

{costos}

Entrega lista. Usa aistetic para consistencia visual.
"""
    else:
        # Interno: detallado para ONG/trabajador/empresa
        return f"""COTIZACIÓN INTERNA (ONG / empresa)
{ev.get('nombre', 'Evento')}

{costos}

Notas internas: ajustar precios reales.
No enviar a productoras. Referencia aistetic para tono.
"""

if __name__ == "__main__":
    print(generar_cotizacion(Path("projects/plano/ejemplos/evento_ejemplo.json"), "productora"))