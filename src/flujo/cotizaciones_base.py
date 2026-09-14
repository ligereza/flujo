"""Cotizacion base local para demo operativa.

No reemplaza una cotizacion final revisada; entrega una base editable y explicable
para productora/jefatura a partir del preset de evento.
"""
from __future__ import annotations

from typing import Any, Dict

from .eventos.presets import apply_event_preset


def clp(value: float | int) -> str:
    return "$" + f"{int(round(float(value))):,}".replace(",", ".")


UNITARIOS = {
    "hora_voluntario": 10_000,
    "mesa": 8_000,
    "silla": 2_000,
    "stand_base": 80_000,
    "testeo": 120_000,
    "contencion": 80_000,
    "coordinacion_mainstream": 90_000,
    "alimentacion": 7_000,
    "diseno_rider_plano": 65_000,
    "cartelera_digital": 90_000,
    "flyer_impreso_10x14": 75_000,
}


def generar_cotizacion_base(evento: Dict[str, Any] | None = None, *, incluir_cartelera: bool = True, incluir_flyer_impreso: bool = False) -> Dict[str, Any]:
    ev = apply_event_preset(evento or {})
    preset = ev.get("preset_operativo", {})
    horas = float(ev.get("duracion_horas", preset.get("duracion_horas", 6)))
    voluntarios = int(ev.get("voluntarios", preset.get("voluntarios", 4)))
    mesas = int(preset.get("mesas", 1 + max(0, voluntarios - 1) // 5))
    sillas = int(preset.get("sillas", max(2, voluntarios)))
    testeo = bool(ev.get("incluye_testeo", preset.get("incluye_testeo", False)))
    masivo = bool(ev.get("masivo", preset.get("masivo", False)))

    items = []
    def add(code: str, label: str, qty: float, unit: float, notes: str = "") -> None:
        subtotal = qty * unit
        items.append({"code": code, "label": label, "qty": qty, "unit": unit, "subtotal": subtotal, "notes": notes})

    add("equipo", f"Equipo RD ({voluntarios} voluntarios x {horas:g}h)", voluntarios * horas, UNITARIOS["hora_voluntario"], "Base operativa; ajustar segun convocatoria final.")
    add("stand", "Stand base informativo", 1, UNITARIOS["stand_base"], preset.get("electricidad", "Electricidad basica"))
    add("mesas", "Mesas operativas", mesas, UNITARIOS["mesa"], f"Preset {ev.get('preset_label')}")
    add("sillas", "Sillas", sillas, UNITARIOS["silla"], "Cantidad inicial editable")
    if horas > 5:
        add("alimentacion", "Alimentacion/colacion equipo", voluntarios, UNITARIOS["alimentacion"], "Recomendada por jornada larga")
    if testeo:
        add("testeo", "Modulo testeo quimico", 1, UNITARIOS["testeo"], "Incluye preparacion y mesa dedicada")
    if masivo:
        add("contencion", "Zona contencion/descanso", 1, UNITARIOS["contencion"], "Recomendado para alto flujo")
        add("coordinacion", "Coordinacion evento masivo", 1, UNITARIOS["coordinacion_mainstream"], "Briefing, montaje, coordinacion con produccion")
    add("rider_plano", "Sistema rider + plano operativo", 1, UNITARIOS["diseno_rider_plano"], "Documento y plano base editable")
    if incluir_cartelera:
        add("cartelera", "Flyer/cartelera digital", 1, UNITARIOS["cartelera_digital"], "Photoshop/Blender si aplica")
    if incluir_flyer_impreso:
        add("flyer_impreso", "Flyer impreso vertical 10x14 cm", 1, UNITARIOS["flyer_impreso_10x14"], "Illustrator/SVG print-ready")

    subtotal = sum(item["subtotal"] for item in items)
    contingencia = round(subtotal * 0.10)
    total = subtotal + contingencia

    markdown = [
        f"# Cotizacion base - {ev.get('nombre', 'Evento')}",
        "",
        f"Preset operativo: **{ev.get('preset_label', 'Evento BASE')}**",
        f"Asistentes estimados: {ev.get('asistentes_estimados', '')}",
        f"Voluntarios: {voluntarios}",
        f"Duracion: {horas:g}h",
        "",
        "| Item | Cantidad | Unitario | Subtotal | Notas |",
        "|---|---:|---:|---:|---|",
    ]
    for item in items:
        markdown.append(f"| {item['label']} | {item['qty']:g} | {clp(item['unit'])} | {clp(item['subtotal'])} | {item['notes']} |")
    markdown.extend([
        f"| Contingencia / ajustes | 1 | {clp(contingencia)} | {clp(contingencia)} | 10% base editable |",
        "",
        f"**TOTAL REFERENCIAL: {clp(total)}**",
        "",
        "Nota: valores referenciales para conversar. Ajustar antes de enviar cotizacion final.",
    ])

    return {
        "evento": ev,
        "items": items,
        "subtotal": subtotal,
        "contingencia": contingencia,
        "total": total,
        "total_clp": clp(total),
        "markdown": "\n".join(markdown),
        "unitarios": UNITARIOS,
    }
