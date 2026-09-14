"""Vocabulario controlado de RD: tipos de fecha (evento).

El tipo de fecha condiciona el preset operativo, el rider y el tono de la pieza.
Es un vocabulario CERRADO con normalizador de alias -- una fecha se etiqueta con
uno o mas tipos de esta lista; lo que no matchea cae a OTRO (nunca se pierde).
"""
from __future__ import annotations

# Tipos canonicos. Orden = de mas masivo/mainstream a mas de nicho + los transversales.
TIPOS_FECHA: tuple[str, ...] = (
    "FESTIVAL",      # gran formato, multi-escenario, aire libre o recinto grande
    "HEADLINERS",    # fecha armada alrededor de un artista cabeza de cartel
    "RAVE",          # electronica de pista, larga duracion, alto flujo
    "OPEN_AIR",      # al aire libre (day/sunset)
    "CLUB",          # club/discoteca, capacidad media
    "AFTER",         # after party, horario extendido de madrugada
    "UNDERGROUND",   # nicho, difusion cerrada, sello/colectivo
    "INFORMATIVO",   # foco preventivo/educativo (no necesariamente fiesta)
    "PRIVADO",       # evento cerrado / corporativo
    "OTRO",          # fallback: no encaja en los anteriores
)

# Alias -> tipo canonico. Case-insensitive; el input se normaliza (lower, sin
# tildes basicas, espacios/guiones a "_") antes de buscar aca.
_ALIASES: dict[str, str] = {
    "festival": "FESTIVAL",
    "fest": "FESTIVAL",
    "headliner": "HEADLINERS",
    "headliners": "HEADLINERS",
    "cabeza_de_cartel": "HEADLINERS",
    "rave": "RAVE",
    "warehouse": "RAVE",
    "open_air": "OPEN_AIR",
    "openair": "OPEN_AIR",
    "aire_libre": "OPEN_AIR",
    "sunset": "OPEN_AIR",
    "day": "OPEN_AIR",
    "club": "CLUB",
    "discoteca": "CLUB",
    "after": "AFTER",
    "afterparty": "AFTER",
    "after_party": "AFTER",
    "madrugada": "AFTER",
    "underground": "UNDERGROUND",
    "under": "UNDERGROUND",
    "subte": "UNDERGROUND",
    "informativo": "INFORMATIVO",
    "preventivo": "INFORMATIVO",
    "educativo": "INFORMATIVO",
    "privado": "PRIVADO",
    "corporativo": "PRIVADO",
    "cerrado": "PRIVADO",
}


def _slug(value: str) -> str:
    out = (value or "").strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        out = out.replace(a, b)
    for ch in (" ", "-", "/"):
        out = out.replace(ch, "_")
    return out.strip("_")


def normalize_tipo(value: str) -> str:
    """Un valor de tipo de fecha a su forma canonica. Lo que no matchea -> OTRO."""
    key = _slug(value)
    if key.upper() in TIPOS_FECHA:
        return key.upper()
    return _ALIASES.get(key, "OTRO")


def normalize_tipos(values: object) -> list[str]:
    """Lista de tipos (o un string) a tipos canonicos, sin duplicados, en el
    orden de TIPOS_FECHA (deterministico)."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    vistos = {normalize_tipo(str(v)) for v in values}
    return [t for t in TIPOS_FECHA if t in vistos]
