"""Cálculo de costos operativos derivado de las reglas del evento.

El objetivo es dar un desglose rápido que aumente con cada cambio de reglas,
para usarlo como base de cotización.
"""
from __future__ import annotations

from typing import Any, Dict, List


def calcular_costos(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Devuelve un desglose de costos a partir de los parámetros del evento.

    Valores son referenciales; el dueño debe ajustar los precios unitarios.
    """
    horas = float(ev.get("duracion_horas", 0))
    voluntarios = int(ev.get("voluntarios", 0))
    asistentes = int(ev.get("asistentes_estimados", 0))
    testeo = bool(ev.get("incluye_testeo", False))
    masivo = asistentes >= 2000 or bool(ev.get("masivo", False))

    # Precios unitarios referenciales (CLP)
    precio_hora_persona = 8_000
    precio_alimentacion = 6_000
    precio_colacion = 3_500
    precio_stand = 35_000
    precio_mesa = 4_000
    precio_testeo = 45_000
    precio_contencion = 25_000

    personal = voluntarios * horas * precio_hora_persona
    alimentacion = 0.0
    if horas > 5:
        alimentacion = voluntarios * precio_alimentacion
    elif horas > 4:
        alimentacion = voluntarios * precio_colacion

    mesas = 1 + max(0, (voluntarios - 1)) // 5
    if testeo:
        mesas += 1
    mobiliario = mesas * precio_mesa

    stands = 1
    if testeo:
        stands += 1
    if masivo:
        stands += 1
    infraestructura = stands * precio_stand

    extras = 0.0
    if testeo:
        extras += precio_testeo
    if masivo:
        extras += precio_contencion

    total = personal + alimentacion + mobiliario + infraestructura + extras

    return {
        "personal": personal,
        "alimentacion": alimentacion,
        "mobiliario": mobiliario,
        "infraestructura": infraestructura,
        "extras": extras,
        "total": total,
        "detalle": {
            "voluntarios": voluntarios,
            "horas": horas,
            "mesas": mesas,
            "stands": stands,
            "testeo": testeo,
            "masivo": masivo,
        },
    }


def resumen_costos(ev: Dict[str, Any]) -> str:
    """Genera un texto legible del desglose de costos."""
    c = calcular_costos(ev)
    d = c["detalle"]
    lines = [f"COTIZACIÓN REFERENCIAL — {ev.get('nombre','Evento')}", "=" * 40, ""]
    lines.append(f"Personal ({d['voluntarios']} voluntarios × {d['horas']} h):       ${c['personal']:,.0f}")
    lines.append(f"Alimentación / colación:                       ${c['alimentacion']:,.0f}")
    lines.append(f"Mobiliario ({d['mesas']} mesas):                         ${c['mobiliario']:,.0f}")
    lines.append(f"Infraestructura ({d['stands']} stands):                    ${c['infraestructura']:,.0f}")
    lines.append(f"Extras (testeo + contención):                  ${c['extras']:,.0f}")
    lines.append("")
    lines.append(f"TOTAL REFERENCIAL:                             ${c['total']:,.0f}")
    lines.append("")
    lines.append("Nota: valores referenciales. Ajustar precios unitarios con el dueño.")
    return "\n".join(lines)
