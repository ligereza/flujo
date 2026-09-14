"""Packs de servicio RD: precio plano CLP, voluntarios fijos.

Fuente de verdad: web/src/rdBrand.ts (PACKS). Este modulo es el espejo Python
--mismos ids/precio/voluntarios/proporciones-- para que engine.py y costs.py
dejen de depender del viejo modelo de presets por tamano de evento
(under/base/mainstream, src/flujo/eventos/presets.py) al armar plano/rider/
costos comerciales de RD.

RECONCILIADO 2026-07-17 con la tarifa real del area (C:/RD/packs_servicios_rd
.json, "jefe area eventos 2026-07-02"): el Pack 1 estaba stale como "Testeo o
Informativo (a eleccion)" 2 voluntarios $100.000; el real es "Informativo"
6 voluntarios $250.000. Packs 2 y 3 ya coincidian. rdBrand.ts actualizado en
paralelo. Nota: INFO y TESTEO comparten 6 voluntarios, asi que el conteo de
voluntarios ya no distingue Pack 1 de Pack 2 (lo hace incluye_testeo).

`precio` es el UNICO valor absoluto editable por pack. El monto de cada
proporcion del desglose (solo Pack COMPLETO) se deriva SIEMPRE como
precio*pct/100 en vez de guardarse como numero aparte, para que no quede
desincronizado si el precio cambia (misma regla que proporcionMonto en
rdBrand.ts).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

PackId = str  # "INFO" | "TESTEO" | "COMPLETO"

# CONFIGURABLE desde 2026-07-26 (orden del usuario: "los precios que sean
# configurables, son de la parte del rider"). La tarifa vive en
# `data/rd_packs.json`, editable a mano, y este modulo la LEE. Antes estaba
# cableada aca y otra vez en `web/src/rdBrand.ts`: dos copias del mismo precio
# que podian desincronizarse sin que nadie se enterara.
#
# Si el archivo falta o esta roto, se usa el diccionario de abajo como respaldo
# y se avisa por stderr -- el rider y la cotizacion no pueden quedarse sin
# tarifa a mitad de un evento, pero tampoco deben mentir en silencio.
_PACKS_JSON_REL = "data/rd_packs.json"

_PACKS_RESPALDO: Dict[str, Dict[str, Any]] = {
    "INFO": {
        "id": "INFO",
        "nombre": "Informativo",
        "label": "Pack 1 · Informativo",
        "desc": "6 voluntarios · 1 stand 3×3 (9 m²)",
        "precio": 250_000,
        "voluntarios": 6,
        "m2": 9,
        "stands": 1,
        "inclusiones": [
            "Stand informativo atendido",
            "Material educativo + insumos preventivos",
            "Protectores auditivos, abanicos, suplementos",
            "Tests de un solo uso (opcional)",
        ],
    },
    "TESTEO": {
        "id": "TESTEO",
        "nombre": "Testeo y Informativo (ambos)",
        "label": "Pack 2 · Testeo y Informativo",
        "desc": "6 voluntarios · 2 stands 3×3 (18 m²)",
        "precio": 300_000,
        "voluntarios": 6,
        "m2": 18,
        "stands": 2,
        "inclusiones": [
            "Stand informativo y stand de testeo, ambos atendidos",
            "Módulo de testeo de sustancias",
            "Análisis colorimétrico gratuito",
            "Reactivos incluidos",
        ],
    },
    "COMPLETO": {
        "id": "COMPLETO",
        "nombre": "Servicio Completo (masivo)",
        "label": "Pack 3 · Servicio Completo",
        "desc": "15 voluntarios · 2 stands + zona (~27 m²)",
        "precio": 500_000,
        "voluntarios": 15,
        "m2": 27,
        "stands": 2,
        "inclusiones": [
            "Informativo + testeo",
            "Intervención y contención psicológica",
            "Zona de descanso baja estimulación",
            "Coordinación operativa en terreno",
        ],
        "proporciones": [
            {"label": "Equipo en terreno", "pct": 60},
            {"label": "Módulo de testeo", "pct": 14},
            {"label": "Stand informativo", "pct": 10},
            {"label": "Intervención y contención", "pct": 9},
            {"label": "Coordinación operativa", "pct": 7},
        ],
    },
}

def _cargar_tarifa() -> tuple[Dict[str, Dict[str, Any]], List[str], str]:
    """Read the editable tariff. Falls back to the built-in copy, loudly."""
    import json
    import sys
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    ruta = raiz / _PACKS_JSON_REL
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        packs = datos["packs"]
        orden = datos.get("orden") or list(packs.keys())
        default = datos.get("default_pack") or orden[0]
        if not packs:
            raise ValueError("sin packs")
        return packs, list(orden), str(default)
    except Exception as e:  # noqa: BLE001 - se reporta, no se traga
        print(
            "AVISO: no se pudo leer %s (%s). Se usa la tarifa de respaldo del "
            "codigo, que puede estar desactualizada." % (_PACKS_JSON_REL, e),
            file=sys.stderr,
        )
        return _PACKS_RESPALDO, ["INFO", "TESTEO", "COMPLETO"], "TESTEO"


PACKS, ALL_PACKS, DEFAULT_PACK = _cargar_tarifa()


def recargar_tarifa() -> Dict[str, Dict[str, Any]]:
    """Relee data/rd_packs.json y actualiza PACKS/ALL_PACKS/DEFAULT_PACK.

    Existe porque la tarifa se lee al importar el modulo, y un proceso largo
    -- el hub -- se quedaba con la copia del arranque: editar el archivo no
    cambiaba nada hasta reiniciar, que es lo mismo que no ser configurable.
    El endpoint /api/rd-packs la llama en cada consulta.

    PACKS se muta EN SU SITIO porque otros modulos la tienen referenciada.
    """
    global ALL_PACKS, DEFAULT_PACK
    packs, orden, default = _cargar_tarifa()
    PACKS.clear()
    PACKS.update(packs)
    ALL_PACKS = orden
    DEFAULT_PACK = default
    return PACKS

# Alias legacy: los presets de tamano de evento (under/base/mainstream, de
# src/flujo/eventos/presets.py) ya no alimentan plano/costos, pero se aceptan
# como sinonimo de pack para no romper eventos/JSON viejos que los usaban.
_ALIASES = {
    "under": "INFO", "base": "TESTEO", "mainstream": "COMPLETO",
    "info": "INFO", "testeo": "TESTEO", "completo": "COMPLETO",
}


def normalize_pack_id(value: Any) -> str:
    """Normaliza un id de pack; acepta mayus/minus y alias legacy under/base/mainstream."""
    key = str(value or "").strip()
    if key in PACKS:
        return key
    return _ALIASES.get(key.lower(), DEFAULT_PACK)


def get_pack(pack_id: Any) -> Dict[str, Any]:
    """Copia del pack normalizado (no muta PACKS)."""
    return deepcopy(PACKS[normalize_pack_id(pack_id)])


def proporcion_monto(precio: int, pct: float) -> int:
    """Monto de un item de desglose: SIEMPRE precio*pct/100, nunca guardado aparte."""
    return round(precio * pct / 100)


def desglose_pack(pack_id: Any) -> List[Dict[str, Any]]:
    """Desglose de proporciones del pack (vacio si el pack no tiene, ej. INFO/TESTEO)."""
    pack = get_pack(pack_id)
    return [
        {"label": p["label"], "pct": p["pct"], "monto": proporcion_monto(pack["precio"], p["pct"])}
        for p in pack.get("proporciones", [])
    ]


def ev_desde_pack(pack_id: Any, **overrides: Any) -> Dict[str, Any]:
    """Evento base derivado de un pack RD, listo para engine.py (plano/rider/QA).

    El pack fija voluntarios/incluye_testeo/masivo (datos del SERVICIO
    contratado); nombre/duracion_horas/asistentes_estimados/layout_mode son
    propios del evento concreto y se pasan por overrides.
    """
    pack = get_pack(pack_id)
    ev: Dict[str, Any] = {
        "nombre": "Evento",
        "duracion_horas": 0,
        "asistentes_estimados": 0,
        "layout_mode": "grid_2x",
        "voluntarios": pack["voluntarios"],
        "incluye_testeo": pack["id"] in ("TESTEO", "COMPLETO"),
        "masivo": pack["id"] == "COMPLETO",
        "pack": pack["id"],
        "pack_label": pack["label"],
    }
    ev.update(overrides)
    return ev
