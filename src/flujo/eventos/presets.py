"""Presets operativos para estimar rider/plano de eventos.

La informacion fina viene del flyer/post (fecha, venue, productora, horario).
Estos presets solo cubren dimensionamiento operativo inicial cuando el jefe aun
no define cambios: equipo, mobiliario, electricidad/luz y escala.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

EVENT_PRESETS: Dict[str, Dict[str, Any]] = {
    "under": {
        "id": "under",
        "label": "Evento UNDER",
        "description": "Evento chico/club: presencia ligera RD, bajo flujo, setup minimo.",
        "duracion_horas": 4,
        "voluntarios": 2,
        "asistentes_estimados": 350,
        "incluye_testeo": False,
        "masivo": False,
        "mesas": 1,
        "sillas": 2,
        "electricidad": "1 punto electrico basico",
        "luz": "luz ambiente o 1 foco simple",
        "zonas": ["stand_informativo"],
        "notas": "Preset inicial: 2 voluntarios, 1 mesa, 2 sillas, electricidad/luz basica.",
    },
    "base": {
        "id": "base",
        "label": "Evento BASE",
        "description": "Evento mediano: stand informativo + testeo, flujo moderado.",
        "duracion_horas": 6,
        "voluntarios": 4,
        "asistentes_estimados": 1200,
        "incluye_testeo": True,
        "masivo": False,
        "mesas": 2,
        "sillas": 4,
        "electricidad": "1 punto electrico estable + alargador/zapatilla",
        "luz": "iluminacion de mesa para testeo + luz stand",
        "zonas": ["stand_informativo", "testeo"],
        "notas": "Preset base: 4 voluntarios, 2 mesas, 4 sillas, punto electrico estable e iluminacion para testeo.",
    },
    "mainstream": {
        "id": "mainstream",
        "label": "Evento MAINSTREAM",
        "description": "Evento masivo tipo Espacio Riesco/festival: alto flujo, coordinacion y contencion.",
        "duracion_horas": 8,
        "voluntarios": 8,
        "asistentes_estimados": 6000,
        "incluye_testeo": True,
        "masivo": True,
        "mesas": 3,
        "sillas": 8,
        "electricidad": "2 puntos electricos o circuito dedicado + alargadores/zapatillas",
        "luz": "iluminacion dedicada para stand, testeo y lectura nocturna",
        "zonas": ["stand_informativo", "testeo", "contencion", "coordinacion", "descanso"],
        "notas": "Preset mainstream: 8 voluntarios, 3 mesas, 8 sillas, electricidad/luz dedicada, zona de contencion y coordinacion.",
    },
}


def normalize_preset_id(value: str | None) -> str:
    key = (value or "").strip().lower().replace("evento_", "")
    aliases = {
        "underground": "under",
        "club": "under",
        "small": "under",
        "medio": "base",
        "mediano": "base",
        "standard": "base",
        "main": "mainstream",
        "masivo": "mainstream",
        "festival": "mainstream",
        "espacio_riesco": "mainstream",
        "espacio riesco": "mainstream",
    }
    return aliases.get(key, key if key in EVENT_PRESETS else "base")


def infer_event_preset(text: str) -> str:
    low = (text or "").lower()
    if "espacio riesco" in low or "mainstream" in low or "festival" in low or "masivo" in low:
        return "mainstream"
    if "under" in low or "underground" in low or "club" in low:
        return "under"
    return "base"


def get_event_preset(value: str | None) -> Dict[str, Any]:
    return deepcopy(EVENT_PRESETS[normalize_preset_id(value)])


def apply_event_preset(evento: Dict[str, Any] | None) -> Dict[str, Any]:
    ev = dict(evento or {})
    preset_id = normalize_preset_id(ev.get("preset") or ev.get("event_preset") or ev.get("tipo_evento"))
    preset = get_event_preset(preset_id)
    for key in ("duracion_horas", "voluntarios", "asistentes_estimados", "incluye_testeo", "masivo"):
        if key not in ev or ev.get(key) in (None, ""):
            ev[key] = preset[key]
    ev["preset"] = preset_id
    ev["preset_label"] = preset["label"]
    ev.setdefault("notas", preset["notas"])
    ev["preset_operativo"] = preset
    return ev


def list_event_presets() -> Dict[str, Dict[str, Any]]:
    return deepcopy(EVENT_PRESETS)
