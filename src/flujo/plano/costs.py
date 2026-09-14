"""Costeo de eventos RD segun el modelo de PACKS (precio plano por servicio).

Fuente de verdad: web/src/rdBrand.ts (PACKS) via .packs (espejo Python). Ya
no hay formula por hora/voluntario ($8.000/hora, etc.): el precio de cada
pack es el UNICO valor absoluto, y el desglose (solo Pack COMPLETO) se
deriva como proporcion del precio, nunca como numero guardado aparte.
"""
from __future__ import annotations

from typing import Any, Dict

from .packs import desglose_pack, get_pack, normalize_pack_id


def calcular_costos(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Devuelve el costeo del pack RD contratado por el evento.

    `ev["pack"]` (o `ev["preset"]` legacy) selecciona el pack; sin ese dato
    se usa el pack por defecto (packs.DEFAULT_PACK).
    """
    pack_id = normalize_pack_id(ev.get("pack") or ev.get("preset"))
    pack = get_pack(pack_id)
    desglose = desglose_pack(pack_id)

    return {
        "pack": pack["id"],
        "pack_label": pack["label"],
        "precio": pack["precio"],
        "voluntarios": pack["voluntarios"],
        "m2": pack["m2"],
        "stands": pack["stands"],
        "inclusiones": pack["inclusiones"],
        "desglose": desglose,
        "total": pack["precio"],
        "detalle": {
            "pack": pack["id"],
            "voluntarios": pack["voluntarios"],
            "stands": pack["stands"],
        },
    }


def resumen_costos(ev: Dict[str, Any]) -> str:
    """Genera un texto legible del pack contratado y su desglose."""
    c = calcular_costos(ev)
    lines = [f"COTIZACIÓN — {ev.get('nombre','Evento')}", "=" * 40, ""]
    lines.append(f"{c['pack_label']}:                         ${c['precio']:,.0f}")
    lines.append(f"Voluntarios: {c['voluntarios']} · Stands: {c['stands']} · {c['m2']} m²")
    lines.append("")
    if c["desglose"]:
        lines.append("Desglose (proporcion del precio):")
        for item in c["desglose"]:
            lines.append(f"  {item['label']} ({item['pct']}%):                ${item['monto']:,.0f}")
        lines.append("")
    lines.append("Inclusiones:")
    for inc in c["inclusiones"]:
        lines.append(f"  • {inc}")
    lines.append("")
    lines.append(f"TOTAL: ${c['total']:,.0f}")
    lines.append("")
    lines.append("Nota: precio plano por pack de servicio RD (no por hora/voluntario).")
    return "\n".join(lines)
